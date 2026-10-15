# macOS 保留现有 VPN 的独立测试

## 隔离依据

读取当前 VPN 状态、默认路由和物理接口；不要假定 Wi-Fi 永远是 en0。用接口清单、路由信息和相关应用的只读状态识别接口，不打印整个 VPN 进程命令行，那里可能包含令牌。

本案例是 TUN VPN：普通 sockets 的默认出口是日本。`curl --noproxy '*'` 仅移除 HTTP 代理干预，仍会经过 TUN。测试进程必须把向 VPS 发出的套接字绑定物理接口，并让测试请求只使用这个进程的 loopback SOCKS。

在支持该功能的 Xray 版本，测试出站包含：

```json
"streamSettings": {
  "sockopt": {"interface": "en0"}
}
```

这是 macOS 单个 socket 的接口约束，既不改默认路由，也不关闭已有 VPN。以当前版本验证，不把 Linux 的接口绑定实现直接套用 macOS。

- [本案例对应 Xray Darwin 实现](https://github.com/XTLS/Xray-core/blob/v26.10.10/transport/internet/sockopt_darwin.go)：查 `IP_BOUND_IF`。
- 只设置源 IP、仅关闭 HTTP 代理、或只看到 VPS 出口，都不能单独证明没有经过日本 VPN 转发。接口绑定和默认出口对照共同构成证据。

## 运行代理验证工具

准备一个含单个 VLESS 或 Trojan TCP TLS/REALITY 出站的 Xray 客户端 JSON，密码等授权保留在私有文件。使用官方并已校验的本机 Xray 可执行文件。

```bash
python3 scripts/verify_isolated_xray.py \
  --xray /absolute/path/to/xray \
  --config /private/path/client.json \
  --interface en0 \
  --expected-exit VPS_IPV4 \
  --expect-baseline-country JP \
  --output /private/path/verification.json
```

`VPS_IPV4` 换成用户预期的 VPS 公网出口。只有用户确实要求日本出口时才设置 JP，不把这个案例偏好强加给其他用户。

工具不启用系统代理/TUN，不启动 Shadowrocket VPN；仅复制输入的代理出站，建立临时 loopback SOCKS，测试后终止进程并删除含授权的临时配置。会核对：

- 默认出口前后 IP/国家是否一致；
- 代理出口 IP 是否等于预期；
- gstatic HTTP 204 和 Google HTTPS 204 等目标的实际返回。

用 `--url URL` 指定测试目标；多次传入可测试多个网址，并替换默认列表。`--check-config` 只构造临时配置并运行 Xray 配置校验，不联网。`--trace-url` 用于另一个返回 `ip=…`/`loc=…` 格式的出口查询或本地验证夹具。

限制：基线是 curl 直接套接字的默认路由，适合本案例的 TUN VPN。若既有工具只配置 HTTP 系统代理，基线请求不代表该代理出口；应使用相应应用代理地址/专用测试确认，而不是为了让该脚本通过去改变系统网络。VPN 自动换出口时前后 IP 可能自然变化，应报告“无法确认出口保持一致”，不要直接指责脚本关闭了 VPN。

## SSH 也可独立绑定接口

确认需要连接的 IPv4 端点、SSH 用户、密钥和已验证 known_hosts 后：

```bash
ssh -F /dev/null \
  -i /private/path/ssh-key \
  -o IdentitiesOnly=yes -o BatchMode=yes -o ConnectTimeout=15 \
  -o StrictHostKeyChecking=yes \
  -o UserKnownHostsFile=/private/path/known_hosts \
  -o 'ProxyCommand=python3 /absolute/path/to/scripts/interface_ssh.py --interface en0 %h %p' \
  SSH_USER@VPS_IPV4
```

首次连接尚无主机密钥记录时用正常的身份核对流程建立记录，再启用上面命令；不要通过 `StrictHostKeyChecking=no` 绕过。

同样的 SSH 参数可用于 scp。先等传输完成再执行依赖该文件的命令，避免把工具返回的“运行中”误当作上传成功。

## GUI 测试与手机验证

用户依赖现有 VPN 时，不打开 Shadowrocket 整机连接开关，不运行可能自动激活 VPN 的全局 CONNECT 测试，也不退出原 VPN 应用。需要查看导入字段时只操作节点编辑页并确认连接开关仍关闭。

命令行验证后给手机具体 QR/链接，让用户选择该节点、保存、重连，反馈 CONNECT 和网页是否正常。手机可以切换节点，但不能把这理解为允许切断 Mac 上助手通信所依赖的 VPN。
