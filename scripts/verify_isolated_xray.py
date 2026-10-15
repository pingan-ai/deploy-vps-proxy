#!/usr/bin/env python3
"""Verify one interface-bound Xray proxy without changing system VPN settings."""
import argparse
import copy
import datetime
import ipaddress
import json
import os
from pathlib import Path
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.parse


def prepare_config(raw, interface, port):
    outbounds = raw.get('outbounds', [])
    if len(outbounds) != 1 or outbounds[0].get('protocol') not in {'vless', 'trojan'}:
        raise ValueError('Provide exactly one VLESS or Trojan proxy outbound.')
    outbound = copy.deepcopy(outbounds[0])
    stream = outbound.get('streamSettings', {})
    if stream.get('network', 'tcp') not in {'tcp', 'raw'}:
        raise ValueError('This helper supports TCP/RAW transport only.')
    if stream.get('security') not in {'tls', 'reality'}:
        raise ValueError('TLS or REALITY security is required.')
    if stream.get('tlsSettings', {}).get('allowInsecure'):
        raise ValueError('Certificate validation must remain enabled.')
    sockopt = stream.setdefault('sockopt', {})
    if outbound.get('proxySettings') or sockopt.get('dialerProxy'):
        raise ValueError('Proxy chains cannot establish a direct interface-bound test.')
    sockopt['interface'] = interface
    return {
        'log': {'loglevel': 'warning'},
        'inbounds': [{'tag': 'isolated-socks', 'listen': '127.0.0.1', 'port': port,
                      'protocol': 'socks', 'settings': {'auth': 'noauth', 'udp': False}}],
        'outbounds': [outbound],
    }


def request(url, port=None):
    command = ['curl', '-sS', '--connect-timeout', '8', '--max-time', '20',
               '-w', '\n%{http_code} %{time_total}']
    command += (['--noproxy', '*'] if port is None else
                ['--noproxy', '', '--proxy', f'socks5h://127.0.0.1:{port}'])
    result = subprocess.run(command + [url], capture_output=True)
    if result.returncode:
        raise RuntimeError(f'curl failed with exit code {result.returncode}.')
    body, metrics = result.stdout.rsplit(b'\n', 1)
    status, elapsed = metrics.decode().split()
    if int(status) not in {200, 204}:
        raise RuntimeError(f'Unexpected HTTP status {status}.')
    parsed = urllib.parse.urlsplit(url)
    if (parsed.hostname in {'www.gstatic.com', 'www.google.com'}
            and parsed.path == '/generate_204' and int(status) != 204):
        raise RuntimeError(f'The generate_204 target returned HTTP {status}, expected 204.')
    safe_url = urllib.parse.urlunsplit((parsed.scheme, parsed.netloc, parsed.path, '', ''))
    return body, {'url': safe_url, 'http_status': int(status), 'seconds': float(elapsed)}


def exit_info(body):
    fields = dict(line.split('=', 1) for line in body.decode().splitlines() if '=' in line)
    return {'ip': str(ipaddress.ip_address(fields['ip'])), 'country': fields.get('loc')}


def free_port():
    with socket.socket() as listener:
        listener.bind(('127.0.0.1', 0))
        return listener.getsockname()[1]


def wait_listener(process, port):
    deadline = time.monotonic() + 8
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError('Temporary Xray exited before its listener became ready.')
        try:
            with socket.create_connection(('127.0.0.1', port), timeout=0.2):
                return
        except OSError:
            time.sleep(0.1)
    raise RuntimeError('Temporary Xray listener did not become ready.')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--xray', type=Path, required=True)
    parser.add_argument('--config', type=Path, required=True)
    parser.add_argument('--interface', required=True)
    parser.add_argument('--expected-exit')
    parser.add_argument('--expect-baseline-country')
    parser.add_argument('--trace-url', default='https://www.cloudflare.com/cdn-cgi/trace')
    parser.add_argument('--url', action='append', help='Repeat to replace the default target URLs.')
    parser.add_argument('--output', type=Path)
    parser.add_argument('--check-config', action='store_true')
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('This helper requires macOS interface binding.')
    if not args.check_config and (not args.expected_exit or not args.output):
        parser.error('--expected-exit and --output are required for network verification.')
    urls = args.url or ['http://www.gstatic.com/generate_204',
                        'https://www.google.com/generate_204', 'https://www.google.com/']
    for url in [args.trace_url, *urls]:
        parts = urllib.parse.urlsplit(url)
        if parts.scheme not in {'http', 'https'} or not parts.hostname or parts.username or parts.password:
            parser.error('Test URLs must be HTTP(S) URLs without embedded credentials.')

    os.umask(0o077)
    def interrupt(signum, frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupt)
    report = {'tested_at_utc': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'bound_interface': args.interface, 'checks': [], 'success': False}
    try:
        socket.if_nametoindex(args.interface)
        expected = str(ipaddress.ip_address(args.expected_exit)) if args.expected_exit else None
        raw = json.loads(args.config.read_text())
        port = free_port()
        config = prepare_config(raw, args.interface, port)
        report['temporary_socks_port'] = port
        report['protocol'] = config['outbounds'][0]['protocol']
        with tempfile.TemporaryDirectory(prefix='isolated-xray-') as work:
            config_path = Path(work) / 'client.json'
            config_path.write_text(json.dumps(config))
            checked = subprocess.run([str(args.xray.resolve()), 'run', '-test', '-config', str(config_path)],
                                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=15)
            if checked.returncode:
                raise RuntimeError('Xray rejected the temporary client configuration.')
            if args.check_config:
                print('Configuration accepted; no VPN settings or network connections changed.')
                return 0

            before = exit_info(request(args.trace_url)[0])
            report['default_exit_before'] = before
            if args.expect_baseline_country and before['country'] != args.expect_baseline_country.upper():
                raise RuntimeError('Default-route baseline is not in the required country; proxy test stopped.')
            process = None
            try:
                with (Path(work) / 'client.log').open('w') as log:
                    process = subprocess.Popen([str(args.xray.resolve()), 'run', '-config', str(config_path)],
                                               stdout=log, stderr=subprocess.STDOUT)
                    wait_listener(process, port)
                    body, check = request(args.trace_url, port)
                    check['exit'] = exit_info(body)
                    report['checks'].append(check)
                    if check['exit']['ip'] != expected:
                        raise RuntimeError('Proxy exit does not match the expected VPS exit.')
                    for url in urls:
                        _, check = request(url, port)
                        report['checks'].append(check)
            finally:
                if process is not None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait(timeout=5)
                try:
                    report['default_exit_after'] = exit_info(request(args.trace_url)[0])
                    report['default_exit_unchanged'] = report['default_exit_after'] == before
                except Exception:
                    report['default_exit_unchanged'] = None
                    report['default_exit_after_error'] = 'Could not read the default-route exit.'
            if report['default_exit_unchanged'] is not True:
                raise RuntimeError('Cannot confirm that the default-route exit remained unchanged.')
            report['success'] = True
    except (Exception, KeyboardInterrupt) as exc:
        report['error'] = str(exc) or 'Interrupted.'
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
        args.output.write_text(json.dumps(report, ensure_ascii=False, indent=2))
        args.output.chmod(0o600)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report['success'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
