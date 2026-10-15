# VPS 代理部署与排障 Skill

一个供 Codex 使用的 skill：部署和维护自有 VPS 上的 3X-UI / Xray 代理，排查 Shadowrocket 连接问题，并在保留现有 VPN 的情况下独立验证新节点的真实出口。

## 适合什么任务

- 部署 VLESS REALITY 或使用受信任证书的 Trojan TLS 节点。
- 排查“显示已连接但网页打不开”“TCP 有延迟但 CONNECT 超时”。
- 让 Mac 上已有的 VPN 继续运行，只把测试流量送往新 VPS。
- 核对节点导入参数、生成二维码和连接资料，检查服务自启与证书续期。

## DMIT 注册入口

[DMIT 注册链接](https://www.dmit.io/aff.php?aff=26333)

这是含推荐参数 `aff=26333` 的推广链接，可能产生推荐收益。

## 安装

将本仓库放入 Codex 的用户 skill 目录。例如：

```bash
mkdir -p "$HOME/.agents/skills"
git clone https://github.com/pingan-ai/deploy-vps-proxy.git \
  "$HOME/.agents/skills/deploy-vps-proxy"
```

如果环境使用 `$CODEX_HOME/skills` 或 `~/.codex/skills`，也可放入对应目录。本机已经有同名 skill 时，不要重复安装到另一个目录。

Codex 会发现可用的 skill；如果没有显示，重启 Codex 后再试。目录发现和调用方式见 [OpenAI 官方 skill 文档](https://learn.chatgpt.com/docs/build-skills)。

## 在 Codex 中使用

在对话中直接指定 `$deploy-vps-proxy`，然后说明任务。无需先手动运行辅助脚本。

**检查现有节点：**

```text
使用 $deploy-vps-proxy 检查我的 VPS 节点。
保持当前 VPN 连接，先只做检查，不修改配置。
验证新节点的真实出口，以及 CONNECT 测试和网页是否正常。
```

**部署新节点：**

```text
使用 $deploy-vps-proxy 帮我部署自有 VPS 代理。
服务器 IP：你的服务器地址
SSH 用户和端口：你的 SSH 用户、端口
SSH 密钥文件：本地私钥文件路径
设备：macOS 和 iPhone，客户端为 Shadowrocket。
我依赖当前 VPN 使用 Codex，请保持它连接，用独立进程测试新节点。
```

提供密钥文件路径即可，不要将私钥正文粘贴到仓库或 Issue 中。需要使用原有安装时，提供私有连接资料所在的位置，不要把它们加入这个公开仓库。

## 本次排障沉淀的判断方法

1. **TCP 正常不等于代理可用。** TCP 延迟说明端口可达；CONNECT 和网页测试还涉及握手、认证、服务器出网和目标响应。
2. **客户端开关不等于节点状态。** “已连接”可能只代表本地 VPN 接口已经启动。
3. **保留原 VPN 时，需要隔离测试流量。** 临时 Xray 客户端使用 loopback SOCKS，并把出站绑定到指定物理接口；同时核对默认出口前后和代理出口。
4. **用对照实验缩小范围。** 独立 Xray 成功、Shadowrocket 失败时，继续检查客户端与协议链路，不能直接断言某一个字段就是根因。
5. **如实记录未解决部分。** 本案例改成 Chrome140 后仍超时，标准 TLS 对照节点恢复正常；原 REALITY 的具体失败点没有完全确认。

## 仓库内容

```text
SKILL.md                           技能入口和工作边界
agents/openai.yaml                 Codex 显示名称与默认提示词
references/deployment.md            SSH、3X-UI API、证书和交付细节
references/macos-isolation.md       保留原 VPN 的独立测试方法
references/incident.md              历史实测版本、结果和判断边界
scripts/interface_ssh.py            macOS 按接口绑定的 SSH stdio 传输
scripts/verify_isolated_xray.py     macOS 临时代理、出口与 URL 验证
```

辅助脚本使用 Python 3 标准库；代理验证还需要 curl 和已校验的官方 Xray 可执行文件。接口绑定脚本针对 macOS，不能直接作为 Linux 或 Windows 的接口绑定实现使用。详细命令见 [macOS 隔离测试](references/macos-isolation.md)。

## 资料来源与版本边界

- 原始文章：[gengdaJ 的 VPS 搭建教程](https://x.com/gengdaJ/status/2029570219354845577)。原文介绍 VPS、3X-UI、VLESS REALITY 以及 Windows / Android 客户端的搭建路线。本仓库补充 macOS / iPhone / Shadowrocket 的实际排障与独立测试方法，不转载原文全文。
- [3X-UI 官方发布](https://github.com/MHSanaei/3x-ui/releases)
- [Xray 官方发布](https://github.com/XTLS/Xray-core/releases)与[配置文档](https://xtls.github.io/config/)
- [Xray 官方相似兼容性问题](https://github.com/XTLS/Xray-core/issues/6873)
- [acme.sh](https://github.com/acmesh-official/acme.sh)

案例记录的是 2026-10-14 的版本组合和实测结果。部署时仍需核对当前版本、客户端支持及证书要求，不能机械照搬历史端口、指纹或 API schema。完整案例见 [故障记录](references/incident.md)。
