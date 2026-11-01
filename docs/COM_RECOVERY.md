# Outlook COM 0x800401E3 恢复与预防

## 已观察到的故障
远程 MCP 能到达本机 Outlook worker，但附着经典 Outlook 的 COM 对象失败，错误码 `0x800401E3 (MK_E_UNAVAILABLE)`。这个 HRESULT 表示运行对象不可用，不代表学校账号失效或 Tunnel 完全断线。Outlook 进程可见并不保证它已经注册到 Running Object Table (ROT)。

可能原因是 ROT 注册时序、Outlook 前台未失焦、worker 与 Outlook 的 Windows 用户/会话/提权状态不同；不能仅凭错误码选定单一原因。

## 安全恢复步骤
1. 解锁 Windows，确认经典 Outlook 已登录且邮件正常同步；新版 Outlook 不能替代。
2. 单击经典 Outlook 窗口，然后切回浏览器或普通 PowerShell，让 Outlook 失去焦点。几秒后再执行 `outlook_list_accounts`。
3. 仍报错时，在 Outlook 所在 Windows 登录会话下以普通权限运行 `Run-Outlook-Diagnostics.cmd`。只记录 `com_connected`、`mapi_connected`、`session_match`、`elevated`、`com_hresult` 等非隐私结果。
4. 如果本机普通 PowerShell 可以连接 Outlook，而 ChatGPT 读信失败，检查隧道/worker 是否被 Windows 服务、另一个 Windows 用户、提升权限的终端或“无论用户是否登录都运行”的任务启动。使用当前登录用户的交互会话和原有配置重启 **本项目** 的 runner；不要重建账号或密钥。
5. 如果本机诊断也失败，请先处理 Outlook 未完成的登录/安全提示，再在保存工作后正常关闭并重新打开经典 Outlook，复测。不强制结束 Outlook 进程、不修改用户配置文件、不关闭 UAC。
6. 最终验收必须完成 `list_accounts` → `search_emails` → `read_email`，并确认未读状态不变。

## 长期预防
- 保持 Outlook 和 bridge worker 为相同 Windows 用户、会话、提权级别；使用当前用户登录后的启动项，而非 Session 0 / Windows Service。
- `com_attach.py` 对短暂 ROT 不可用有界重试，不会自动启动 Outlook。连续失败仍需本机检查，重试本身不保证解决长期会话隔离。
- 电脑睡眠、关机、退出登录会中断这种依赖桌面 Outlook 的连接。需要跨会话长期服务时应申请学校 IT 许可，并在许可范围内使用受管 Graph/OAuth；不要绕过组织限制。
- 如部署中存在本机 `connection_last_error.json`，只在用户电脑本地检查，避免公开包含路径或运行环境信息的原日志。

## 验证边界
此仓库不等于用户实际部署的版本。仓库修改和 Linux 模拟测试不能证明用户 Windows 侧已恢复。只有远程真实读信成功才算修复完成。

参考：Microsoft KB 238610（Office ROT 注册与窗口焦点）；Windows MK_E_UNAVAILABLE 错误定义。
