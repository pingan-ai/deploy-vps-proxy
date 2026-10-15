# 3X-UI 部署与配置细节

## SSH、备份和下载

- 用户提供密钥 ZIP 时先列出条目，只提取需要的密钥到私有目录，防止路径穿越；识别密钥类型并设权限 600。不要把密钥内容打印出来。
- 明确 SSH 用户/端口，保留主机密钥验证。已记录的主机密钥变化时核实身份，不用关闭校验来消除错误。
- 若经过既有 VPN 的 SSH 在 banner/key exchange 前反复超时，可用指定物理接口的传输做对照；这不等同于身份认证失败。工具用法见 [隔离测试](macos-isolation.md)。
- 记录现有服务、数据库、Xray 模板、监听端口、证书路径及现有入站。SQLite 活跃数据库优先用 SQLite backup API 保存一致快照。
- 官方来源：[3X-UI](https://github.com/MHSanaei/3x-ui/releases)、[Xray](https://github.com/XTLS/Xray-core/releases)。对照所选发布的校验信息；执行前阅读安装脚本，确认其端口、证书和既有安装处理方式。
- 安装服务端和客户端版本需要当前文档验证，不盲用 latest；文章发布时间与实际版本差异可能影响兼容性。

## 面板 API 的易错点

以下路径是在 3X-UI 3.10.0 验证过的例子，执行前核对所安装版本的源码/API。基址为面板自己的随机路径，不能把示例基址硬编码为根目录。

```text
GET  csrf-token
POST login                          # username/password，cookie jar，CSRF header
GET  csrf-token                     # 登录后刷新 token
GET  panel/api/inbounds/list
GET  panel/api/inbounds/get/{id}
POST panel/api/inbounds/add
POST panel/api/inbounds/update/{id}
GET  panel/api/clients/links/{email}
POST panel/api/setting/all
POST panel/api/setting/update
POST panel/api/xray/
POST panel/api/xray/update
POST panel/api/server/restartXrayService
```

- 使用 cookie jar 和 `X-CSRF-Token`；HTTPS 校验开启。检查 JSON 的 `success`，但错误日志不要转储包含授权的整个响应。
- 当时 `setting/update` 需要先读取完整设置、只修改目标字段、再提交完整对象；发局部对象可能把其他字段写成默认零值。
- 当时 `xray/update` 使用表单编码的 `xraySetting` JSON 字符串和 `outboundTestUrl`。嵌套的 settings/streamSettings 可能是字符串或对象，先识别再处理。
- 当时面板 Trojan 入站客户端用 `clients[].password/email`；不要直接用 Xray 文档里另一个版本的运行时 users schema 替代面板 schema。
- 普通 3X-UI 指纹枚举与 Shadowrocket 命名不同。只有面板 schema 支持的值才能写入该字段。
- 修改后比较实际生成的运行时配置并执行所安装 Xray 的配置校验，再验证服务和新旧入站。保存非敏感状态摘要及最终数据库备份。
- 需要握手证据时限定目标端口、时间和记录量，并及时停止采集。REALITY 的 show/debug 可能打印认证密钥片段；原始日志留在私有位置，分析和交付前脱敏，结束后恢复诊断设置。

## TLS、REALITY 和出网

- REALITY 服务端 privateKey 留在服务器；客户端只交付对应公开材料。实际客户端字段名以该版本为准：例如旧版 publicKey 和新版 password 不能机械互换。
- 核对客户端的协议、UUID/密码、flow、端口、SNI、公钥和 short ID。目标站点应满足所选版本的 TLS 条件，从服务器验证可达性。
- 标准 TLS 用受信任证书，并使证书身份匹配客户端校验名称；IP 证书需要 IP SAN，只有域名证书不能直接当作 IP 证书使用。不要设置 allowInsecure 或关闭主机名校验来获得“成功”。
- IP 证书可能很短期：检查实际 notBefore/notAfter、ACME renewal 配置和 cron。确认签发挑战需要的端口可达、续期后代理服务加载新证书；仅看到首次签发成功不足以证明未来续期。
- 对现有有效证书优先复用正确证书路径并核对续期钩子。不要通过反复强制签发来测试自动续期。
- 如要固定 IPv4 出口，核对当前 Xray 官方配置位置。本案例版本用 freedom 出站的 `streamSettings.sockopt.domainStrategy: UseIPv4`，旧位置可能弃用；不是所有用户都需要禁用 IPv6。
- 面板/订阅和代理端口是否能从用户路径访问分别验证。一个管理端口失败不等于代理端口失败。

## 最小交付

根据实际客户端生成 QR/原生分享链接、必要的订阅和私有管理说明。包括当前主要节点、证书校验、启动方式、续期配置、已测客户端、管理/SSH 入口和备份位置。只生成用户需要的其他客户端格式。

原节点未解决时保留并标明状态；是否删除它由任务范围和用户意图决定。新节点确认成功后更新默认资料，避免旧二维码与新说明混用。

升级前重新核对：[Xray 配置文档](https://xtls.github.io/config/)、[3X-UI 官方源码](https://github.com/MHSanaei/3x-ui)、[acme.sh](https://github.com/acmesh-official/acme.sh)。链接或 schema 变化时从官方文档入口查找。
