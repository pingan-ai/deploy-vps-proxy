#!/usr/bin/env python3
"""Forward SSH stdio over one macOS IPv4 socket bound to an interface."""
import argparse
import ipaddress
import os
import select
import socket
import sys


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--interface', required=True)
    parser.add_argument('--connect-timeout', type=float, default=15)
    parser.add_argument('host', help='Numeric IPv4 endpoint; SSH handles authentication.')
    parser.add_argument('port', type=int)
    args = parser.parse_args()
    if sys.platform != 'darwin':
        parser.error('This transport requires macOS IP_BOUND_IF.')
    try:
        address = ipaddress.IPv4Address(args.host)
        interface_index = socket.if_nametoindex(args.interface)
        if not 1 <= args.port <= 65535 or args.connect_timeout <= 0:
            raise ValueError('Invalid port or timeout.')
    except (ValueError, OSError) as exc:
        parser.error(str(exc))

    try:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as connection:
            # Darwin IP_BOUND_IF; constrain this socket, not the system route.
            connection.setsockopt(socket.IPPROTO_IP, 25, interface_index)
            connection.settimeout(args.connect_timeout)
            connection.connect((str(address), args.port))
            connection.settimeout(None)
            readers = [sys.stdin.fileno(), connection]
            while readers:
                ready, _, _ = select.select(readers, [], [])
                for source in ready:
                    if source == sys.stdin.fileno():
                        data = os.read(source, 65536)
                        if not data:
                            connection.shutdown(socket.SHUT_WR)
                            readers.remove(source)
                        else:
                            connection.sendall(data)
                    else:
                        data = connection.recv(65536)
                        if not data:
                            return 0
                        offset = 0
                        while offset < len(data):
                            offset += os.write(sys.stdout.fileno(), data[offset:])
    except (OSError, KeyboardInterrupt) as exc:
        print(f'Interface-bound SSH transport stopped: {exc}', file=sys.stderr)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
