# 仅用于验证 Business 的 HTTPS + OAuth 接入

这是一个独立、可丢弃的**固定字符串探针**。它不导入 Outlook、不读邮箱/文件、不执行命令、不调用 OpenAI 模型 API。唯一工具 `bridge_ping` 返回 `AUTHENTICATED_MCP_PROBE_OK`。

用途：判断 Business 工作区的正常 Server URL 接入是否可用，从而把问题缩小到 Secure MCP Tunnel 的组织关联，或发现另一个具体的 HTTPS/OAuth 错误。**它不是已经部署好的公网服务，也不是生产邮箱 OAuth 服务。**

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

本次制作环境 Linux/Python 3.12/MCP 1.30.0 已通过 6 项测试：元数据和未认证拒绝、口令/CSRF/Origin、PKCE/授权码重用拒绝、错误 resource/回调拒绝、带认证 HTTP 工具调用，以及输入验证。使用真实 ASGI HTTP 路由和合成凭证，没有触及朋友的 Windows 或公网。

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
