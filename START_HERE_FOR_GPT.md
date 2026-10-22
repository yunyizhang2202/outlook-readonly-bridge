# 给接手 GPT：从朋友现有进度继续

目标：让用户自己的 ChatGPT 能按需只读检索 Windows 经典 Outlook 中明确允许的邮箱。你与本仓库维护方通过 GitHub Issue 异步交接。不要假设你能主动联系另一聊天中的 GPT，或 Issue 发布就会自动唤醒它。

## 先确认这一件事

用户说卡在“管理员权限”。收集**提示所在产品、提示原文中通用错误语句、失败步骤**，去掉组织、账号、租户/对象标识和凭证。然后按 `docs/ADMIN_PERMISSIONS.md` 分类。尚无朋友实际报错证据，不能宣布已定位。

- 微软登录页的“需要管理员批准”：微软租户 OAuth 同意。Windows 管理员运行无法解决。
- Windows UAC / Access denied：本机权限或进程会话。先普通用户、同一会话，不笼统提权。
- Platform 的 Tunnels access required：OpenAI 组织 RBAC。不是微软管理员。
- COM 未连接/Outlook 未运行：本机检查，不是运行密钥问题。

## 恢复现状，逐层推进

1. 盘点朋友已装的经典 Outlook、Python 和当前桥源码，复用能用的部分。无需重复安装另一套。
2. 先读 README 和配置说明。保持显式邮箱白名单，不把这里的合成测试地址当成朋友账户。
3. 普通 Windows PowerShell 5.1 运行诊断；与 Outlook 同用户、同交互会话、相同提权状态。不要运行 Windows 服务/Session 0 来连接桌面 Outlook。
4. 本机 `check.py` 通过后才排隧道，运行密钥只在本地输入。没有权限就说明是哪个组织的哪个权限。
5. 使用用户自己的 Secure MCP Tunnel 和 ChatGPT 工作区。以当前官方文档与 `help quickstart` 核对 CLI，不复用维护方的隧道或密钥。
6. 隧道健康后，在 ChatGPT 测五工具发现；实时取完整 `account_id`，按 list_accounts → list_folders → search_emails → read_email。ID 不可截断或凭邮箱手写。
7. 对比本机/远端正文长度与 SHA256；确认未读状态和截断；不要把正文发布到 Issue。先验证最新一封的代表性读取，不批量导出。

## 每次交接格式

在同一个 Issue 回复，避免多开重复线程：

```text
MESSAGE_ID: 自己生成唯一值
IN_REPLY_TO: 上一条消息ID（首次填 initial）
阶段: 微软登录 / 本机COM / Python / MCP / OpenAI权限 / 隧道 / ChatGPT
已执行: 仅写实际执行的脱敏步骤
结果: 成功/失败/未执行 + 固定错误分类
证据: 退出码、布尔状态、版本；不附账号、标识或密钥
下一步: 一个明确动作
需要维护方答复: 一个具体问题；无则写无
```

每次只在实际状态变化时回复。不能把“程序在运行”“已安装”“doctor 成功”“已列出账户”分别等同于远程读信成功。不根据历史测试替朋友的新电脑背书。可提交 PR，但先读 AGENTS.md。
