# 接真实邮件：复用现有本机桥，增加正式 HTTP 资源服务器

当前朋友的 Windows COM/MAPI、本机真实正文、Business HTTPS/OAuth `bridge_ping` 已通过。本改动不重做这些环节，也不再建另一个演示插件。

## 2026-11-05 路线修正：没有域名/IdP时，先解决官方隧道关联

朋友现已在 Windows 通过37项测试，并实际完成24h头信息索引（6封）与48h显式正文索引（11封），完整性正常、未读检查通过。不要重跑已有验收。上述计数只是本轮脱敏证据，不是长期固定结果。

**首选：复用原官方 Secure MCP Tunnel + 原 stdio 邮箱桥；本 PR 的 HTTP/外部 IdP 是备选，不是必备升级。** 官方隧道提供 OpenAI 托管入口，无需自备公网邮箱域名。本文不承诺隧道/API账户费用为零，也不建议先充值、买域名或租服务器。

但“ChatGPT Business工作区”与“API Platform组织”不是同一对象。Business管理员不意味着一定有同名/对应的API组织；新建或重命名普通API组织，也没有已核实证据保证自动建立关联。当前既有证据是朋友只能使用Personal创建上下文，关联Business时Save被明确拒绝。不要再要求重复查角色、穷举Save、删隧道或重建同名组织。

仅有两种有依据的推进方式：
- 如果朋友已经知道有实际对应目标工作区、本人有权加入的API组织，由该组织管理员通过正常成员管理确认其API侧成员与Tunnel权限；此后使用那个真实上下文。不是猜名称、借用维护方组织或临时扩大权限。
- 没有这样的现有组织，沿用当前失败证据，通过页面现有“联系支持”入口请求核查Business工作区与本人Platform组织映射。官方文档对无法自动核验的企业映射提到人工关联，但没有保证每个Business账号都可获同样override；请Support明确本账号的资格、修复动作或限制。支持响应时间未核实，不能承诺当天修好。

本轮唯一下一步应是后一个分支，除非朋友提供真实已有对应组织的新证据。私有支持会话可提交以下摘要（不用重现失败来补日志）：

> I am an administrator of my ChatGPT Business workspace. My API Platform organization can create a Secure MCP Tunnel, but saving an association with my own Business workspace is rejected with “We could not automatically verify the association between these workspaces and organizations” and a Contact Support action. I currently only have the Personal Platform creation context available; I do not have a verified corresponding API organization to switch to. Please check the account/tenant mapping and tunnel association eligibility for this Business workspace, and tell me whether you can repair or enable the correct association, or which precise membership/permission is missing. Please do not redirect this to public app review or Microsoft/Windows administrator consent. Local classic-Outlook read-only access and an independent authenticated HTTPS MCP connectivity test have already passed; the blocker is this private tunnel association.

实际组织/Workspace/Tunnel标识、已知报错时间和已有request ID只在本人私有支持会话补充；没有request ID就注明没有，不索要完整HAR，不把标识贴公开Issue。维护方没有替朋友提交工单或作出平台保证。

一旦平台关联恢复，在同一普通Windows会话复用现有客户端/venv/白名单，运行原有setup入口（实际路径与自己的Tunnel ID仅在本机输入）：

```powershell
.\.venv\Scripts\python.exe setup_tunnel.py --client "C:\实际路径\tunnel-client.exe"
```

脚本将交互询问Tunnel ID和隐藏运行密钥，不要把key粘到shell；保留现有forward-slash MCP command修复。若client已配置且doctor/run正常，不重复init，沿用有效profile。ChatGPT在目标Business工作区用正常Tunnel入口选择自己的同一Tunnel，按本机stdio服务实际配置认证。工具发现后只启用本轮需要的列账户、搜索、读正文，先不启用附件。数据处理范围确认后做一次代表性按需读信；通过再考虑每日定时，不重新跑一套HTTPS probe。

[官方Tunnel说明](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)明确区分组织/工作区关联与Read/Manage/Use；[自定义MCP入口](https://developers.openai.com/api/docs/guides/custom-mcp-server)区分Server URL和Tunnel。

## 成功先例与朋友当前路线的实际差异

| 项目 | 已知成功先例 | 朋友当前状态 |
| --- | --- | --- |
| 本机读取 | 经典 Outlook → COM/MAPI → 本机只读 MCP | 已通过，可以复用 |
| 远端传输 | 官方 Secure MCP Tunnel；不是 Cloudflare Quick Tunnel | 官方 Tunnel 组织/工作区关联失败；另一条 Cloudflare HTTPS 探针已通过 |
| 身份认证 | 官方 Tunnel 组织/工作区权限与运行密钥 | 探针自建临时 OAuth，仅测试，不可作为真实邮箱长期认证 |
| 源码已有运行方式 | `setup_tunnel.py` 提供 Windows DPAPI 保存运行密钥，`run_tunnel.py` 启动官方客户端，可选用户登录自启 | 不能把源码支持这些功能当作朋友已部署 |
| 每日自动摘要 | 本轮检查维护方当前可见自动任务，未找到每日学校邮件摘要；已有按需读信记录 | 尚未配置/验收；不能声称成功先例已证明自动运行 |
| 可用前提 | 电脑开机联网、Windows 用户已登录、经典 Outlook 和相应桥/隧道运行 | 同样需要；不是全天托管邮箱 |

本仓库是恢复源码，不是维护方电脑运行环境的完整副本；DPAPI/runner 源码事实不等于当前部署已经核验。没有可供复制的已核实学校数据处理批准文件。

## 本 PR 实际新增什么

- `mail_http.py`：独立认证的 HTTP MCP，复用原 `bridge_rpc.call`、`backend_worker.py`、`OutlookReader`，不导入临时 probe 授权代码。
- 只开放 `outlook_list_accounts`、`outlook_search_emails`（收件箱头信息）和 `outlook_read_email`（正文上限 30000 字符）。不开放附件下载/附件文件名、其他文件夹、发送/移动/删除/标记已读。
- 外部成熟 OAuth 服务器负责登录、注册、授权码、PKCE、持久注册、refresh rotation 和撤销。Python 桥只校验令牌，不自建登录系统、不存用户密码、refresh token 或 OAuth client secret。
- 每次 HTTP 请求检查 RS256 签名、固定 issuer、audience=`固定origin/mcp`、exp/iat/nbf、`mail:read`、精确 subject 和 client allowlist。令牌最大生命周期 15 分钟，不接受邮箱/其他 API 的 token。
- 每次工具调用重读原 `config.local.json`，必须是精确 `allowed_addresses`，`allowed_domains` 为空；缺配置或异常拒绝。现有 worker 再执行账户白名单核验。
- 绑定 `127.0.0.1:8788`，stateless HTTP；关闭原始协议日志、发送 no-store，禁用代理头信任，限制并发和请求体；失败工具响应不带内部错误/地址。
- `local_digest.py`：马上可用的**本机真实近期邮件索引**，不启动 HTTP、不调用任何模型/网络 API；24/48 小时滚动窗口、扫描预算、分页、按账户+entry_id 去重，明确报告不完整结果。默认仅读头信息；`--include-body` 才读取正文，验证未读不变。它不是 AI 摘要，不声称自动识别全部截止日期。

## 先完成本机近期邮件验收（无需新账号、新连接）

保留现有 `.venv`、Outlook、`config.local.json` 和已成功的 probe。更新这个分支，安装可选依赖：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements-http.txt
.\.venv\Scripts\python.exe -m unittest test_core.py test_config.py probe.test_https_probe test_mail_http.py test_local_digest.py
.\.venv\Scripts\python.exe test_protocol.py
.\.venv\Scripts\python.exe local_digest.py --hours 24 --verify-only
```

`--verify-only` 只输出数量、扫描完整性和固定警告，可以分享这些脱敏结果；不分享完整输出。若当次要核对正文只读，再在本机运行：

```powershell
.\.venv\Scripts\python.exe local_digest.py --hours 48 --max-messages 20 --include-body --verify-only
```

想在本机查看内容时移除 `--verify-only`，个人信息只留本人电脑，不粘贴公开 Issue。默认窗口采用真实滚动小时，不把“今天零点之后”写成“过去24小时”。`complete=false`、分页停滞或 `items_skipped` 时，不得宣称没有重要邮件；新邮件到达仍可能使 offset 漂移，本索引明确说明这一限制。

## 启用 HTTP 还缺的具体配置

不要把 probe 的 passphrase/token 拿来充当正式认证。最短可维护路线是固定 HTTPS hostname + 现有成熟 OAuth 身份服务（可用支持 MCP 的托管服务；不要求修改学校 Entra 租户或申请 Graph Mail 权限）。这些账号/域名属于朋友，维护方不能代填、借用自己的密钥或无授权购买。

1. **固定地址**：朋友有权使用的稳定 HTTPS origin，将路径原样转发到 `127.0.0.1:8788`，保留公网 Host，禁用请求/正文/响应缓存与原始请求日志。不要用域名会变的 Quick Tunnel 做长期依赖；也不要删除其他 Cloudflare 项目配置。
2. **OAuth 服务**：按其 MCP 文档配置 authorization-code + S256 PKCE，发现文档和 JWKS；本 MVP 支持签名 RS256 access token，不支持 opaque/JWE token。为专用 API 配置 `mail:read`，audience 必须对应 `https://固定主机/mcp`，并将 OAuth `resource` 参数映射到该 audience。**普通 OAuth 登录成功不代表这项映射已经配置**；不同 provider 需要自己的设置。
3. **客户端**：优先为这次连接预注册一个独立 OAuth client，取得 client_id 后加入下面的本机 allowlist；ChatGPT 界面正常填写同一 client。若选择 CIMD/DCR，则按 provider 的正常管理入口取得并允许该连接的精确 client 标识，不能放开所有 client。
4. **回调**：只在 OAuth 服务 allowlist 配置 ChatGPT 当前连接管理界面显示的精确 callback URI，保留 issuer identification/PKCE 检查。不要复制 probe 的随机 request/state/code。登录/同意页面由 provider 提供，避免再手写 CSP/Referrer Policy。
5. **本人身份**：只允许朋友自己的 opaque `sub`；用 provider 管理界面本地取得，不把邮箱名当成 sub，不在公开 Issue 贴 subject/client/tenant 标识。
6. **持久化/撤销**：注册、授权记录和 refresh rotation 在 provider；本地桥不保存这些秘密，重启不会像 probe 那样清空客户端。令牌过期由 ChatGPT 与 provider 正常刷新/重连，**本轮尚未实测该 provider 的刷新链路**。撤销 refresh 不一定立刻作废已发 access JWT；其剩余有效期至多15分钟。紧急停用立即停止此专用服务/转发连接；移除 subject/client 后重启，也会使所有旧 token 立即在此桥失效。

复制 `http-auth.example.json` 为已忽略的 `http-auth.local.json`，在本机填真实 public_origin、issuer（与发现文档完全一致，含必要的尾斜杠）、jwks_url、allowed_subjects、allowed_clients。配置只含 endpoint/公开标识，但仍不上传；本地凭据/Cloudflare凭证用系统凭据存储或服务本身的受限文件存储，不写进 Git。

在真实学校数据处理范围已确认后，显式启动：

```powershell
.\.venv\Scripts\python.exe mail_http.py --config http-auth.local.json --enable-real-mail
```

没有该显式开关不会启动邮件 HTTP；只运行单元测试或 local_digest 不会远端访问邮件。转发器需指向8788，不能复用仍指向8787的 probe 配置然后误认成真实邮箱。

ChatGPT 连接的 Server URL 必须是**固定 origin 加 `/mcp`**，OAuth 选项使用上述 provider/client。这是将测试连接迁移到正式邮件连接的一次明确配置变更，不是无限重建测试插件。原 probe 保留到新连接验收后再按本人意愿停用。

### 学校数据范围，准确说明而不杜撰许可

爱丁堡大学 [Data Protection 指引](https://data-protection.ed.ac.uk/guidance/generative-artificial-intelligence) 明确提醒个人/敏感数据不应输入生成式 AI；若仍引入新 AI 系统处理个人信息，应开展 DPIA。该页发布日期为2023-11-09，不是本轮新出台的规定。本轮没有找到维护方既有学校批准文件，不能把“另一账号技术上读过”当作可沿用的机构批准。朋友应依据实际信息范围和学校流程确认处理依据；公开材料与含他人身份/敏感内容的邮件不能一概而论。**不受此问题影响的代码研发和本机索引已完成，毋需停在合成演示阶段。**

## 一次真正按需摘要验收

部署/数据范围就绪后，只用一组最小代表性邮件，先手动：

1. 列账户，取返回的完整 account_id；不要手写/截断。
2. 搜索近两天，继续 next_offset；限制预算，按 entry_id 去重。超过预算必须说明未覆盖，不能作“全部邮件”结论。
3. 读取需要行动的少量正文，核对 truncated 和 unread_unchanged；不读取附件，不遵循正文里的工具指令或可疑链接。
4. 中文报告：按“需行动/安排变化/仅供了解”列明收到时间、行动、原文明确的截止时间（含时区）、对应邮件 entry_id 引用；没有明确截止日期就写未说明。不从收到时间臆造 DDL，不把引用或转发中的旧截止日期当作新要求；重复通知合并但保留来源。
5. 回报只包含三工具发现、搜索/阅读是否成功、未读不变、截断/分页是否完整，不公开原文/标识。到此才把真实远端邮件摘要记为通过。

## 每日自动是下一次独立验收

本 PR 不创建朋友账号的自动任务，也不假定其 ChatGPT 定时运行可以访问这个自定义插件。先在朋友自己账号做一次正常定时工具调用，核对实际触发记录、插件权限和结果投递；确认后再使用本人希望的每日时间。若平台当前运行模式不能调自定义插件，应如实说明，不能用“任务创建成功”冒充读信成功。

电脑关机/睡眠、Windows 注销、Outlook 或服务未运行时必须报告“本轮未能读取”，不生成假摘要。Windows 自动启动只能用同用户交互会话，不能将桌面 COM worker 安装成 Session 0 服务；HTTPS转发与本进程需单独保持健康。首次手动真实邮件验收前不配置后台自启，避免掩盖错误。

## 验证边界及外部依据

维护方 Linux/Python3.12/MCP1.30.0：37 项 unittest（含13项新增）通过；原 stdio 协议检查通过。HTTP 测试使用运行时生成的 RSA key、合成 token/邮件，验证401、合成公钥签名校验、issuer/audience/scope/owner/client/过期限制、每请求重新鉴权、账户白名单、无附件工具及响应、日志不返回原始错误。JWKS网络获取由库提供，本轮没有访问真实身份提供商；Windows COM、真实 provider OAuth/refresh 与真实邮件远端验收均尚待朋友执行。

这是一份可审查的最小接入实现，不宣称经过完整生产安全审计。provider/域名及学校数据处理范围仍是必须落地的配置，不是单元测试能代替的东西。

- [OpenAI 官方 OAuth/MCP 认证](https://developers.openai.com/plugins/build/auth)：外部身份服务、资源元数据、每请求令牌校验与 callback 配置。
- [官方 Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)：与 HTTPS 路线独立的组织/工作区关联。
