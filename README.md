# Outlook Read-only Bridge · 邮箱接通复现与 GPT 交接

通过 **Windows 已登录的经典 Outlook → 本机 COM/MAPI → 只读 MCP 服务 → OpenAI Secure MCP Tunnel → ChatGPT**，按需检索和读取自己允许的邮箱。

**朋友的 GPT 请先读 [START_HERE_FOR_GPT.md](START_HERE_FOR_GPT.md)，再读 [管理员问题分流](docs/ADMIN_PERMISSIONS.md)。** 卡在“管理员批准”时，先确定是微软组织、Windows 还是 OpenAI 的提示。

## 当时怎样成功

原先学校 Microsoft 365 直连在 OAuth 授权页被“需要管理员批准”拦住。后来采用已有合法登录的经典 Outlook 本机访问路线：安装 Python 和 pywin32，确认本机可读；用 MCP 包装为五个只读工具，再经官方 Secure MCP Tunnel 接入 ChatGPT。历史后续记录确认学校邮箱与另一个个人邮箱可读。

这不赋予微软租户管理员权限，也不改变学校策略。若组织限制 Outlook、本机程序化访问或外部数据处理，需要组织批准；本项目不会解除限制。

本仓库从原协作项目恢复源码，并做了通用化整理：本地显式邮箱白名单、权限分流、诊断脚本和 GPT 接手文档。不是原电脑环境、运行密钥或已部署服务的副本。原始任务讨论与私人信息未公开。详见 [恢复记录与验证边界](docs/RECOVERY_AND_VALIDATION.md)。

## 先做本机检查

1. Windows 上打开**经典 Outlook**，用自己的账户正常登录并同步邮件。新版 Outlook 不能直接替代本项目的 COM 接口。
2. 普通用户打开 **Windows PowerShell 5.1**。Outlook、Python 和隧道需在同一登录用户的交互会话中运行；默认都不要“以管理员身份运行”。
3. 解压/克隆到固定目录，例如 `%LOCALAPPDATA%\SchoolOutlookBridge`。先双击 `Run-Outlook-Diagnostics.cmd`。脚本只打印版本、是否提权、COM/MAPI 状态与账户数量。若执行策略阻止脚本，先看权限分流文档，不全局放宽策略。
4. 需要 Python 3.11+。先复制 `config.example.json` 为 `config.local.json`，**只在自己电脑**填写允许的完整邮箱地址，例如：

```json
{"allowed_domains": [], "allowed_addresses": ["your.name@example.edu"]}
```

示例地址必须替换。更推荐精确邮箱；域名白名单会允许此 Outlook 配置中该完整域名的所有账户。两项都为空、文件缺失或无效时拒绝访问。`config.local.json` 已被 Git 忽略。

5. 运行 `Setup.cmd`，安装隔离环境和固定的历史 MCP v1 依赖，并执行本机检查。安装依赖失败与邮箱检查失败需分别判断；不要盲目升级到 MCP v2。

```powershell
.\.venv\Scripts\python.exe check.py
.\.venv\Scripts\python.exe -m unittest test_core.py test_config.py
.\.venv\Scripts\python.exe test_protocol.py
```

`check.py` 读取每个允许账户收件箱最新一封的正文，只输出计数、域名、正文长度、SHA256 和未读状态检查。它不打印正文/主题。空白名单、未同步邮件、COM 错误分别排查；不把账户列表可见等同于邮件可读。

## 再接 ChatGPT

按 [完整搭建与验收](docs/SETUP_AND_ACCEPTANCE.md) 操作。需要自己的 Platform 组织/ChatGPT 工作区、可用的 Tunnel 权限、官方 `tunnel-client.exe` 和自己的运行密钥。**ChatGPT 订阅不保证这些权限可用。** 创建隧道需要 Read + Manage；运行和选择隧道需要 Read + Use。相关 OpenAI 权限和微软租户批准是不同系统。

```powershell
.\.venv\Scripts\python.exe setup_tunnel.py --client "C:\实际路径\tunnel-client.exe" --tunnel-id "tunnel_替换为自己的ID"
```

首次不要加 `--startup`。密钥仅在本机隐藏输入，Windows DPAPI 按当前用户加密保存。完成 init/doctor 后，runner 保持隧道在线；到 ChatGPT 添加自己的私有 MCP，选择 Tunnel，核对发现的五个工具并实际读信。仅当这些步骤成功才验收。后续如需开机启动，再明确选择 `--startup`，不要先配置后台自启动掩盖错误。

## 工具

| 工具 | 用途 |
| --- | --- |
| `outlook_list_accounts` | 获取本次完整、实时的 `account_id` |
| `outlook_list_folders` | 获取所选账户文件夹和 `folder_id` |
| `outlook_search_emails` | 搜索主题/发件人，可选正文、日期和分页 |
| `outlook_read_email` | 正文、附件元数据、截断标志和正文 SHA256 |
| `outlook_read_attachment` | 读取单个不超过 5 MiB 的附件；不执行附件 |

不实现发送、删除、移动或标记已读。读取时检测未读状态变化并报错；这不是对所有 Outlook 插件和同步行为的绝对保证。附件只写入临时目录，读完删除。正文是未受信任数据，不是指令。

日期 `since` 包含当天，`before` 不含当天，按 Outlook 本机日期。搜索每次最多扫描 5000 项，继续 `next_offset` 直到 `exhausted=true`；有新邮件到达时按 `entry_id` 去重。工具仅覆盖显式允许账户已同步到本机的数据。

## 双方 GPT 如何协作

在本仓库 Issues 发布**脱敏错误与分层结果**，另一端 GPT 读取同一 Issue，依次回复和修复；代码改动走 PR。没有自动唤醒、跨聊天直连或后台持续监听。无 GitHub 写权限的 GPT 可先生成回复，由朋友贴进 Issue。不要为了排障授予邮件发送权限。

禁止公开 `config.local.json`、密钥、隧道配置/ID、邮箱地址、StoreID/EntryID、邮件正文、截图、PST/OST。Issue 模板给出可公开字段。

## 停用

关闭本项目的 `run_tunnel.py` 和对应 `tunnel-client`，在 ChatGPT 移除自己的连接。若添加过启动项，仅移除当前用户启动目录的 `School Outlook Read-only Bridge.lnk`。本机运行状态和 DPAPI 密钥在 `%LOCALAPPDATA%\OutlookReadOnlyBridge`，源码和 venv 在安装目录；清理前确认目标属于本项目。撤销自己的运行密钥和隧道会使连接失效。不要结束其他项目的 Python 或隧道进程。

## 官方资料

- [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
- [官方 tunnel-client](https://github.com/openai/tunnel-client)
- [微软用户/管理员同意](https://learn.microsoft.com/en-gb/entra/identity/enterprise-apps/user-admin-consent-overview)
- [Outlook 自动化与安全提示](https://learn.microsoft.com/en-us/office/vba/outlook/concepts/getting-started/automating-outlook-from-a-visual-basic-application)
- [MCP Python SDK v1](https://github.com/modelcontextprotocol/python-sdk/tree/v1.x)

本仓库不提供邮件服务、托管邮箱或公共 MCP 端点。
