# 2026-10-14：Shadowrocket 与新 REALITY 链路的故障案例

这是历史观察，用于指导对照实验，不是当前所有版本的兼容性结论。

起始参考为 [gengdaJ 的 VPS 搭建文章](https://x.com/gengdaJ/status/2029570219354845577)，提供 VPS / 3X-UI / VLESS REALITY 的搭建路线。本案例记录在 macOS、iPhone 和 Shadowrocket 环境中实际发生的兼容性问题及验证结果，不把文章中的建议自动视为已验证结论。

## 实测条件与结果

- 服务端：Debian 13、3X-UI 3.10.0、Xray 26.10.10。
- 原节点：VLESS + REALITY + XTLS Vision，TCP 443，SNI/目标 `www.amazon.com`。
- 客户端：iPhone 与 Mac 上的 Shadowrocket 2.2.92。iPhone 为 5G 网络，全局路由“代理”。
- 手机测试 URL：`http://www.gstatic.com/generate_204`。
- 手机显示连接，TCP 延迟约 261 ms，但 CONNECT 超时且网页打不开。
- 用户把 TLS 指纹从 Chrome 改为 UI 标注支持 X25519MLKEM768 的 Chrome140、保存并重连后，仍超时。
- Mac 独立 Xray 客户端连接原节点成功；gstatic 返回 204，Google 返回 200，出口匹配 VPS。
- 在同一 VPS 新增 Trojan + 标准 TLS，使用受信任的 Let's Encrypt IP 证书，保持证书校验。
- 新节点的独立 Xray 测试通过；用户确认 iPhone 的 CONNECT 和网页均正常。
- 独立测试绑定 macOS 物理接口，测试前后默认出口仍为日本 VPN。Mac Shadowrocket 整机 VPN 保持关闭。

不把真实 VPS IP、UUID、密钥、密码、订阅令牌或面板路径写入此案例。

## 结论的边界

可确认服务器出网和至少两种代理链路可用。原故障范围集中于 Shadowrocket 使用 REALITY 的连接过程；兼容性是主要嫌疑，但没有失败 ClientHello/服务端握手证据证明某一个字段是唯一根因。

这次同时更换了协议、握手方式和入站端口，不能仅凭新节点成功就严格排除针对旧协议或旧端口的网络影响，也不能声称已经修好了原 REALITY。

当时采用的 REALITY 实现要求 ClientHello 中有特定排列的 `X25519MLKEM768` key share。官方相似问题的维护者回复要求浏览器指纹带 ML-KEM。这解释了检查指纹的理由，但不能替代本案例的失败握手证据。

- [Xray 官方相似问题及维护者回复](https://github.com/XTLS/Xray-core/issues/6873)
- [本案例对应 REALITY 实现](https://github.com/XTLS/REALITY/blob/8cdf7bf9c7f0/tls.go)：搜索 `reject outdated/strange Client Hello`。
- [对应 Xray 版本的依赖](https://github.com/XTLS/Xray-core/blob/v26.10.10/go.mod)：核对 REALITY 依赖，而不是引用今天的 main 分支替代当时代码。

旧问题里的 `minClientVer` 修改或降级建议可能针对不同版本。没有当前版本的依据、备份和对照结果时，不直接沿用。

## UI 与导入中的实际陷阱

- Mac Shadowrocket 2.2.92 的首页全局“连通性测试”曾在开关关闭时自动启动 VPN。用户依赖另一 VPN 时，不用该操作进行独立测试。
- 节点菜单中的“复制”实际创建了副本；复制链接应使用编辑页的“复制网址”。操作后读取最新 UI 确认结果。
- 当时 3X-UI 的指纹枚举包含通用 `chrome`，不包含 Shadowrocket 原生的 `Chrome140`。把 UI 专有值塞进面板可能使前端 schema 无法解析、重置相关对象。
- 当时 Shadowrocket 原生 VLESS 分享用 base64 authority 与 `tls`、`peer`、`xtls`、`pbk`、`sid`、`fingerprint` 等字段；通用分享 URI 使用 `security`、`sni`、`flow`、`fp` 等字段。用实际客户端分享格式核对，不凭名称猜测。
- 标准 TLS 节点恢复可用后，应更新默认 QR、链接、说明；旧的 REALITY QR 只作为明确标注的独立资料保留。

## 当时的工具行为

Xray 26.10.10 的配置校验对普通 Trojan 输出弃用提示，但节点在该版本可用。这是升级前应复核的版本信号，不能把该版本的告警写成所有未来版本的永久事实，也不能因为告警就修改已经验证可用的用户配置。
