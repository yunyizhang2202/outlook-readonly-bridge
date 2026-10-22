# “管理员权限”有四种，先看提示出现在哪里

| 提示/位置 | 实际权限层 | 下一步 |
| --- | --- | --- |
| 微软网页登录：Need admin approval / 需要管理员批准 | 学校/公司 Microsoft Entra 租户的应用同意 | 要求组织批准该 OAuth 应用，或在组织允许情况下使用本机已登录经典 Outlook 的路线。以管理员运行 PowerShell 无法授予租户权限。 |
| Windows：UAC、Access is denied、当前用户安装不能由管理员卸载 | 本机安装范围/文件访问/进程会话 | 确认错误步骤和路径；本项目默认按当前用户安装，普通运行。需要提权的单独系统操作应明确原因，不把整套 Outlook 桥提权。 |
| Outlook：A program is trying to access... | Outlook Object Model Guard/终端安全策略 | 在本地核对可见提示、反病毒状态及组织政策；不要设置 Never warn、改注册表关保护或强行绕过学校限制。 |
| OpenAI Platform：Tunnels access required、无 Manage/Use | OpenAI 组织级 RBAC/工作区关联 | 当前组织的 owner/RBAC 管理员分配 Tunnel 权限；Read + Manage 管创建，Read + Use 管运行和选择。微软学校管理员未必管理这个组织。 |

## 本机 COM 失败

- `Open classic Outlook in the logged-in Windows session first`：确认经典 `OUTLOOK.EXE` 已运行并完成登录。新版 Outlook 不等价。Python 与 Outlook 用同一用户、同会话，默认都普通运行。
- `COM_ATTACH_FAILED`：优先 Windows PowerShell 5.1，核对不是 PowerShell 7 缺少旧 COM 方法；核对 Outlook 与脚本提权状态。不要直接关闭 UAC。
- `worker timed out`：检查 Outlook 本地登录/安全提示与同步。进程存在不证明 MAPI 可用。
- `allowed_account_count=0`：检查 `config.local.json` 的精确地址/域名；域名必须完全相等，子域不会自动匹配。重新同步 Outlook 账户。

## 隧道失败

- 本机 `check.py` 失败时先修本机；setup 在进入密钥提示前运行该检查，不要向失败后的 PowerShell 提示符粘贴 key。
- `setup_tunnel.py` 已保留当时的 Windows 路径修复：给 `--mcp-command` 的 Python/server 路径用正斜杠；含空格需引用。不要回滚成容易丢反斜杠的字符串。
- 找不到隧道：核对 OpenAI 组织、ChatGPT 工作区关联及 Read/Use；这不靠 Windows 管理员解决。
- doctor 成功但 ChatGPT 调用失败：确认 runner/client 持续运行、电脑未睡眠、同一 Tunnel、同一工作区和工具已启用。

尚未取得朋友的实际提示，以上是排障分流，不是对朋友故障的最终判断。
