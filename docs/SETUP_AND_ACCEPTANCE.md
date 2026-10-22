# 分层搭建和验收

## 0. 已有进度优先

先确认已有桥、虚拟环境、Tunnel、ChatGPT 连接，避免重复配置。不要运行本仓库的 setup 覆盖另一个仍在使用的 `outlook-school` profile。本套脚本采用固定 profile 和本机目录，一台 Windows 用户下仅面向一套实例；多实例需先改 profile、目录、mutex 和启动项。

## 1. 本机

依 README 配置白名单，保持经典 Outlook 已登录、可同步。本项目不收邮箱密码，不替用户首次登录 Outlook。默认普通 Windows PowerShell；固定目录不放 Program Files，避免无谓提权。

Python 推荐 3.11/3.12 等与历史依赖兼容版本。`Setup.cmd` 使用 `py -3` 或 `python` 创建 `.venv`，如果命中了商店占位别名，先修 Python 安装。不要仅看 `where python` 就认定已安装。

`requirements.txt` 固定 MCP v1 的 1.30.0，避免上游主版本变化。`tested-dependencies.txt` 仅是历史制作环境的参考快照，不是当前全平台锁文件；pywin32 在 Windows 安装，原 Windows 报告为 312。安装失败需记录包名/版本和脱敏错误，不随意去未知源下载。

本机验收：账户允许数大于 0；收件箱有可读邮件；check 返回正文长度/hash 且未读检查 true；核心测试和 MCP 协议测试通过。MCP 协议测试不会代替真实邮箱测试。

## 2. 官方隧道

以当前 [官方文档](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels) 和官方客户端 `help quickstart` 为准。用户在自己的 OpenAI Platform 组织创建/复用私有 Tunnel，并关联目标 ChatGPT 工作区。创建需要 Tunnels Read + Manage，运行密钥和连接操作者需要 Read + Use。

从 Platform 官方入口或 [官方 releases](https://github.com/openai/tunnel-client/releases/latest) 下载匹配 Windows 架构的客户端；核对发布摘要。旧成功记录使用 0.0.16，不据此固定永久旧版。不要把安装 GitHub 源码仓库误当成连接邮箱已完成。

本机运行 README 的 setup 命令，**第一次不加 `--startup`**。只在明确显示 `OpenAI runtime key (local entry only):` 时输入自己的运行密钥，输入字符不回显正常；key 不进聊天/Issue/命令行。脚本调用 init、doctor，保存 DPAPI 密钥后启动 runner。`settings.json`、`runtime-key.dpapi`、`status.json` 位于 `%LOCALAPPDATA%\OutlookReadOnlyBridge`，不公开。

`status.json` 的 `process_started_not_remote_verified` 只证明启动过进程。用 doctor 和本机 client 的健康/就绪检查确认连接。runner 最多重试五次，失败后需本地诊断；不要为排障向公共 Issue 上传未脱敏日志或环境变量。

## 3. ChatGPT

在当前可用的插件/自定义 MCP 界面创建私有连接，方式 Tunnel，选择同一隧道；完成界面要求的授权。界面没有此选项时先核对账户、计划、工作区与权限，不承诺所有用户都能用。

连接名可自行填写，工具必须是五个只读工具。正文会在用户主动调用时交给 ChatGPT 处理；公开的只是源码，MCP/邮件服务保持私有。隧道是传输方式，不能代替界面要求的认证与授权设置。

## 4. 真正的完成条件

| 层 | 通过证据 | 不足以说明通过 |
| --- | --- | --- |
| Outlook | 已登录且数据同步、COM/MAPI 能读允许账户 | 进程存在 |
| Python/本机 | check 实际读一封、未读状态检查 true | pip 安装成功 |
| MCP | 初始化、五工具发现、错误传播正常 | server.py 无语法错误 |
| Tunnel | doctor/ready 和活跃客户端均正常 | 有 Tunnel ID |
| ChatGPT | 远端实际搜索/读信，长度和完整正文 hash 对照本机 | 只列出插件或账户 |

远端每次实时 `outlook_list_accounts`，不要复制旧的、截断的 StoreID；`list_folders` → `search_emails` → `read_email`。需要跨文件夹要显式选择，不把收件箱搜完称为整个邮箱搜完。日期、分页、截断按 README 解释。

通过后可按用户要求增加启动项。电脑睡眠、关机、退出当前用户或关闭 Outlook/runner 都可能中断；这不是免开机的云邮箱服务。
