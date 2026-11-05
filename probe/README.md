# 仅用于验证 Business 的 HTTPS + OAuth 接入

这是一个独立、可丢弃的**固定字符串探针**。它不导入 Outlook、不读邮箱/文件、不执行命令、不调用 OpenAI 模型 API。唯一工具 `bridge_ping` 返回 `AUTHENTICATED_MCP_PROBE_OK`。

用途：判断 Business 工作区的正常 Server URL 接入是否可用，从而把问题缩小到 Secure MCP Tunnel 的组织关联，或发现另一个具体的 HTTPS/OAuth 错误。**它不是已经部署好的公网服务，也不是生产邮箱 OAuth 服务。**

**2026-11-05 实测更新**：朋友在 Windows + Chrome + ChatGPT Business 的真实连接中调用 `bridge_ping`，取得 `{"ok":true,"message":"AUTHENTICATED_MCP_PROBE_OK","mail_access":false}`（[Issue #1](https://github.com/yunyizhang2202/outlook-readonly-bridge/issues/1) 的 friend-gpt-remote-bridge-ping-pass-20261105-13）。该结果来自 PR #4 旧提交加本机定向 CSP 修改；本分支现已包含相同的正式修复。已通过的是无邮箱 HTTPS/OAuth 工具调用，不是学校邮箱远端读取，也未解决原 Secure MCP Tunnel 组织关联。

## 已有的认证和限制

- MCP `/mcp` 全部要求有效 Bearer token；未登录返回 401 和资源发现信息。
- OAuth authorization-code + PKCE S256；ChatGPT 通过 DCR 注册客户端。不支持 CIMD，请在界面有选择时选 DCR。
- 所有授权都先经过本机用户设置的独立探针口令登录，并明确同意 `probe:read`。口令通过隐藏输入创建，不用真实邮箱/OpenAI/GitHub 密码，也不用任何 API key。
- 回调仅接受官方文档列出的 `chatgpt.com/connector/oauth/{callback_id}` 与旧稳定回调；不允许任意站点回调。ChatGPT 若实际使用不同官方回调，先核对文档再修正，不能直接放开所有 redirect URI。
- 资源 audience、scope、有效期检查；授权码一次性且 60 秒过期，token 15 分钟过期；不发 refresh token，到期需重新连接。
- 登录 CSRF cookie + token、Origin 检查、安全 cookie、防嵌入和不缓存；失败登录限流，内存对象有数量上限。
- 只监听 `127.0.0.1`；DNS rebinding/Host 检查不关闭。
- OAuth 元数据、注册与登录发起端点按协议公开；它们不提供邮箱/工具数据。工具调用始终需要认证。
- 状态只在一个进程内，重启即清空客户端/令牌。没有持久化、多进程部署、生产运维或安全审计保证。**不要把 Outlook 工具接入这个临时授权实现。**

## 1. 取得文件，先本机测试

把整个 `probe/` 文件夹放到现有仓库根目录下，沿用已有 `.venv` 和 `requirements.txt`。不覆盖根目录 `server.py`、邮箱配置或隧道配置。

```powershell
.\.venv\Scripts\python.exe -m unittest probe.test_https_probe
```

当前维护方 Linux/Python 3.12/MCP 1.30.0 已通过 13 项探针测试，连同原有核心/配置共 24 项，stdio 协议检查 PASS。测试包括 HTTP/OAuth、PKCE、Origin/CSRF、pending 审计以及登录页 CSP 的回调许可和其他响应原策略保留。使用真实 ASGI HTTP 路由和合成凭证；维护方未在朋友的 Windows 上独立执行。

同时原有 11 项核心/配置测试与 stdio 协议测试仍可按根 README 执行；已成功的本机邮箱检查不用反复重做。

## 2. 准备一个经本机用户同意的 HTTPS 转发地址

使用朋友已有并认可的 HTTPS 转发/反向代理，目标仅为 `http://127.0.0.1:8787`。公网路径需原样转发，保留公网 Host，允许 GET/POST/OAuth 回调；不配置跨站重定向、公开文件目录、请求正文记录或管理员后台。

一个可选的临时测试办法是官方 `cloudflared` Quick Tunnel。朋友已下载的完整 OpenAI client 包中通常附有 `cloudflared.exe`，先本地核对文件与来源，不要求重新下载另一套程序。若已有获准的转发器，优先复用。

```powershell
& "C:\实际路径\cloudflared.exe" tunnel --url http://127.0.0.1:8787
```

该命令会分配临时 HTTPS 主机名，先保留终端，再启动下一节的探针。服务未启动时暂时 502 不代表 OAuth 失败。不要为修 Quick Tunnel 删除朋友已有的 Cloudflare 配置；若既有配置不兼容，先报告。域名变化后需要用新 origin 重启探针并更新 ChatGPT 连接。

Cloudflare Quick Tunnel 不支持 SSE；本探针明确使用 stateless Streamable HTTP 的 JSON 响应，不要求 SSE 推送。若该转发器/ChatGPT 组合仍要求不支持的长连接，改用支持该模式的已批准 HTTPS 代理，不把 Quick Tunnel 当成生产部署。

本方案走外部 HTTPS 转发；**不使用 OpenAI Secure MCP Tunnel 的 Workspace 关联表单**。它不会授予朋友在 Business 工作区原本没有的权限。

## 3. 启动固定字符串探针

在另一个普通 PowerShell 中，从仓库根目录运行：

```powershell
.\.venv\Scripts\python.exe -m probe.https_probe --public-origin "https://实际分配的主机名" --port 8787
```

`--public-origin` 只填 HTTPS 的协议和主机名，**不要 `/mcp` 路径**。随后在本地隐藏输入中两次填写一个新建的、至少 24 字符的探针专用口令。口令不回显，不存文件，不通过聊天/Issue 传递。

不需要 OpenAI API key、学校密码、管理员 PowerShell 或更改防火墙入站规则。保留探针和转发器两个终端；不要启动根目录邮箱 `server.py` 作为这个转发目标。

## 4. 再到 ChatGPT 使用 Server URL

在朋友实际使用的 Business 工作区中：

1. 添加自定义 MCP，连接方式选 **Server URL**。
2. URL 填 `https://实际主机名/mcp`；认证选 **OAuth**，如问注册方式则选 DCR。不要选 No authentication。
3. 正常的授权页面应是 `Connectivity probe sign-in`，显示只读探针 scope 和 ChatGPT 回调地址。只在本地该 HTTPS 页面填写上一步新建的探针口令并同意。
4. 发现/安装后应只出现 `bridge_ping`。在启用该连接的对话中调用它，预期返回 `AUTHENTICATED_MCP_PROBE_OK` 且 `mail_access: false`。
5. 出现学校登录、OpenAI API key 输入要求、读邮箱工具或不同主机的登录页面时，不继续当作本探针；先核对目标文件/端口/URL。

## “Origin rejected” 的浏览器表单修复（2026-11-04）

**适用现象**：HTTPS 探针授权登录页已打开，提交仅用于测试的口令后，`/probe-login` 返回 `403 Origin rejected`，OAuth 尚未完成。它发生在口令校验之前，不能认定密码错误，也不能单凭此报错认定 Cloudflare 改写了请求头。

**已由朋友的真实浏览器对照支持的原因**：原始 HTML 登录页沿用全局 `Referrer-Policy: no-referrer`。Chrome 实际发送 `Origin: null`；源代码严格要求缺省或 `provider.origin`，会拒绝 `null`。修改登录页策略后同源 Origin 恢复正常，原错误消失。见 [MDN Origin](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Origin) 与 [Referrer Policy 对 Origin 的影响](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Referrer-Policy#effect_on_the_origin_header)。

**最小修复**：仅对 GET `/probe-login` 登录 HTML 响应使用 `Referrer-Policy: origin`，使普通浏览器表单请求携带真实的同源 Origin，且 `Referer` 最多包含 `https://主机名`，不会暴露 `?request=...`。其他页面仍保留原策略。**没有**关闭/放宽服务器对 `Origin`、Host、CSRF、cookie、PKCE、回调目标的校验；`Origin: null` 与其他站点仍被拒。

回归测试覆盖登录页面响应头以及攻击者来源/`null` 均被拒；Python TestClient 不模拟 Chrome 自动生成 Origin 的行为，真实浏览器结论来自朋友在 Issue #1 的实测记录。

朋友更新本分支（合并 main 后再更新 main）并在**旧测试已停止**的情况下，使用既有虚拟环境和相同方法重新运行上述测试、探针和临时隧道。**重启探针会使内存 OAuth 状态失效**，所以需要重新发起 ChatGPT 自定义 MCP 连接的认证流程，不复用旧的登录页链接或 code。建议在 Chrome DevTools → Network 勾选 Preserve log，找到 POST `/probe-login`；仅在本机核对 `Origin` 的**类别**（同源 HTTPS / `null` / 其他域 / 其他协议 / 其他端口）与当前浏览器地址栏的实际主机是否一致。公开 Issue 只给分类和 HTTP 状态，绝不贴具体主机、URL、表单、Cookie、口令、state、code、authorization headers 或完整 HAR。

若仍出现拒绝：先核对浏览器地址栏实际为当前 HTTPS Quick Tunnel 域名、探针的 `--public-origin` 也为这个域名且不包含 `/mcp`。检查浏览器是否是直接 HTTPS 页面、是否存在 iframe/sandbox、扩展或额外代理；**不要**修改请求头伪造来源、将 `null` 加入白名单、移除安全校验或改用公开邮箱服务。只反馈分类证据，再决定后续变更。

## GET 表单正常、POST 却 missing/expired：一次定位（2026-11-05）

Issue #1 最新实测确认：同源 Origin 修正后，重新 Sign in 能显示密码表单，但提交仍返回 `Request missing or expired`。这不是已经确认的“用户输入太慢”，也不是口令错误；该返回发生在口令校验之前。现有证据不足以区分到期、服务实例重建、重复消费或请求参数变化。

本分支提供默认关闭的 `--audit`。在**同一条原有探针启动命令末尾**加上此选项；不要把占位域名作为实际地址。只停止并更新本项目的 Python probe 一次，保留仍有效的 cloudflared。使用原有 venv 先运行：

```powershell
.\.venv\Scripts\python.exe -m unittest test_core.py test_config.py probe.test_https_probe
.\.venv\Scripts\python.exe test_protocol.py
```

探针重启会丢失内存 OAuth 客户端、pending、code 和 token。通过既有测试插件的正常入口重新授权；如果出现 `Client ID not found`，单独报告客户端注册状态失效，不复用旧 URL，也不无限新建插件。获得新表单后，只提交一次，并保留终端从 `startup` 到失败的 `probe_audit` JSON 行。不要开启原始 HTTP/access/debug 日志。

输出只含随机本地服务实例标签、单调时钟相对毫秒、进程内递增 flow 序号、阶段、pending 数、TTL 分档、query 参数是否存在/个数及 cookie 对应关系的布尔值。**instance/flow 不是 OAuth request/client 标识，也不是其哈希。** 不输出 URL、地址、请求标识、OAuth state/code、口令、Cookie 或 token。日志仅写启动终端，不增加诊断 HTTP 端点。

| 同一次尝试的观察 | 能说明什么 |
| --- | --- |
| `authorize_created → get_found → post_found → pending_consumed`，同一 instance/flow | 登录请求找到且已消费；随后继续验收 OAuth 回调和 bridge_ping |
| `get_found` 后出现新 `startup`，instance 改变，随后 `post_missing` | 内存服务实例已重建，旧 pending 不在新实例里；不是仅凭此证明 Windows 重启 |
| `pending_expired` 对应相同 flow，随后 `post_missing` | 服务按原有 300 秒规则清理了请求；比较 elapsed_ms。明显少于 300 秒需排本机墙钟跳变 |
| `pending_consumed` 后再 `post_missing` | 可能重放/重复提交，结合是否已成功回调核对；不能把后一个报错当作第一次也失败 |
| `post_missing` 且 query_present=false | POST 没有非空 request 参数 |
| cookie_matches_live_request=true，但 query_matches_cookie_request=false | Cookie 对应的活动请求与 POST query 不同；检查本机表单目标/多标签页，不公开具体值 |
| pending_count=0，没有 expiry/consume，instance 未变 | 尚不能确定；提供这一小段诊断，由维护方继续定位 |

GET 日志在发新 CSRF cookie **之前**记录，GET 的 cookie 可能来自旧页；cookie 对应关系主要用于 POST。false/null 也可能因 cookie 缺失或过期，不能单独当作 query 被修改的证明。多标签页会覆盖共享 CSRF cookie，本轮只留一个新登录页。

诊断不延长 TTL、不恢复已消费请求、不改变 Origin/CSRF/PKCE/Host/口令校验。此审计后来证实：首次 POST 已消费 pending，第二次失败的 POST 是用户看到页面未跳转后手动再次点击；没有自动重放的证据。真实阻断及修复见下一节。无需对已经通过的无邮箱连接重复这一轮诊断。

## POST 303 后不跳转：登录页 CSP 修复（2026-11-05）

朋友真实 Chrome 记录：首次 POST 返回 303，页面仍留在表单，Console 明确显示 `form-action 'self'` 阻止请求。原登录 HTML 的 CSP 只允许本站，而成功登录会通过 303 跳到白名单允许的 ChatGPT OAuth callback。Chrome 会对这一跳转应用 form-action 策略；相关浏览器差异见 [MDN form-action](https://developer.mozilla.org/en-US/docs/Web/HTTP/Reference/Headers/Content-Security-Policy/form-action)。

正式修复**仅对 GET 登录 HTML**使用 `form-action 'self' https://chatgpt.com`。default-src、frame-ancestors、base-uri 保持原样；其他响应仍保留原 CSP。回调地址继续通过现有 `allowed_callback` 校验具体 HTTPS 主机与路径，未改 Origin/CSRF/PKCE/Host/口令和一次性授权码规则。新增回归测试确认精确 CSP、普通错误/303 响应策略未变、恶意回调域仍被拒。

另一次 `Use the probe resource and probe:read scope` 报错，朋友已确认是新连接 Server URL 漏写 `/mcp`；修正路径后真实 bridge_ping 通过。该案例无需继续追加 scope/resource 审计或放宽校验。以后填写当前 HTTPS origin **加 `/mcp`**。

已连接的探针无需为维护方整理补丁立即重启或再建插件；重启会清空内存 OAuth 状态。后续计划另行迁移稳定地址与持久化认证，不能直接往此临时探针增加 Outlook 工具。

## 5. 验收与交接

| 层 | 需要的实际证据 |
| --- | --- |
| 本机代码 | 6 项 probe 测试通过 |
| 公网/认证发现 | 公网 OAuth 元数据可达，`/mcp` 未认证返回 401（预期） |
| OAuth | 探针口令授权完成，没有 invalid_client / invalid_grant / redirect 等错误 |
| Business MCP | 只发现 `bridge_ping`，实际调用得到固定字符串 |

401 证明认证在起作用，不代表连通失败；DNS/502/错误 Host、发现元数据、回调、令牌交换、工具调用需分别报告。成功列出工具还不等于调用成功。

公开 Issue 只贴各阶段成功/失败、通用错误语句和固定输出；不贴公网临时地址、客户端凭证、授权 URL、state/code/token、cookie、口令、完整日志或截图。不要求上传 HAR。

如果完整固定字符串调用成功，可证明该 Business 工作区在本次配置下能使用 HTTPS/OAuth MCP；**仍不代表真实邮箱集成已经完成**。下一步另行设计生产认证/部署与邮箱授权，不把临时探针直接换成读信服务。

测试后 Ctrl+C 停止探针和转发器，在 ChatGPT 移除测试连接；无需改动已成功的本机邮箱代码或原 Tunnel。

## 依据

- [OpenAI 自定义 MCP：URL、OAuth 与 DCR](https://developers.openai.com/api/docs/guides/custom-mcp-server)
- [OpenAI OAuth、PKCE、回调地址和 audience](https://developers.openai.com/plugins/build/auth)
- [OpenAI 连接和测试](https://developers.openai.com/plugins/deploy/connect-chatgpt)
- [Cloudflare Quick Tunnels](https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/)

