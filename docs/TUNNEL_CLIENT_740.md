# tunnel-client v0.0.17 Windows WinError 740 排查

适用范围：普通用户通过 Python subprocess 启动官方 Windows amd64 EXE 时，直接收到 WinError 740。该错误发生在本机进程创建阶段，不是微软学校租户 OAuth 批准，也不能证明 OpenAI Tunnel 已连接。

## 本次已核验的官方文件

维护方于 2026-10-23 从官方 Release 下载原始 ZIP，核对 GitHub 发布的 archive digest，并只读分析其中 tunnel-client.exe 的 PE 头；没有在 Windows 执行它。

| 项目 | 本次结果 |
| --- | --- |
| 发布包 | tunnel-client-v0.0.17-windows-amd64.zip |
| ZIP SHA256 | b89074637596262067061308cf174959561a1a8bcffe2db956650dad7303052b |
| 包内 tunnel-client.exe SHA256 | 61a770c759c386845f830a106f7e6d0d3f854b932259744a88b4013c282e64ec |
| PE Machine | 0x8664，AMD64 |
| Subsystem | 3，Windows Console |
| PE Resource directory RVA / Size | 0 / 0 |

**此精确 EXE 没有嵌入的资源目录，因此不存在内嵌的 requireAdministrator 清单。** 这个结论只覆盖上述哈希的官方完整客户端，不覆盖 runtime 变体、同名其他 EXE、本机旁挂 manifest 或本机 Windows 兼容性/组织策略。没有内嵌清单也不能证明任意电脑均不会要求提升。

不要根据另一个项目的 740 报错认定本项目也有同一个打包 bug；不要修改或重签官方 EXE 来规避它。

## 第一轮：只核对身份和本机兼容性

在普通 **64 位 Windows PowerShell 5.1** 运行下面检查。只在本机输入实际 EXE 路径；脚本不启动 EXE、不提权、不改注册表、不读取运行密钥。不要公开输入的本机路径。

```powershell
& {
    $ErrorActionPreference = 'Stop'
    $exe = (Resolve-Path -LiteralPath (Read-Host '本机 tunnel-client.exe 的完整路径')).ProviderPath
    if (-not (Test-Path -LiteralPath $exe -PathType Leaf)) { throw 'EXE not found' }

    $expected = '61a770c759c386845f830a106f7e6d0d3f854b932259744a88b4013c282e64ec'
    $actual = (Get-FileHash -LiteralPath $exe -Algorithm SHA256).Hash.ToLowerInvariant()
    [pscustomobject]@{
        check = 'binary_identity'
        official_full_client_v0017_amd64_match = ($actual -eq $expected)
        exe_sha256 = $actual
        adjacent_manifest_present = (Test-Path -LiteralPath ($exe + '.manifest'))
        environment_requests_admin = ($env:__COMPAT_LAYER -match '(?i)(^|\s)RUNASADMIN(\s|$)')
        environment_layer_present = (-not [string]::IsNullOrWhiteSpace($env:__COMPAT_LAYER))
    } | ConvertTo-Json

    $roots = @(
        @{ label='current_user'; key='HKCU:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers' }
        @{ label='machine_64'; key='HKLM:\Software\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers' }
        @{ label='machine_32'; key='HKLM:\Software\WOW6432Node\Microsoft\Windows NT\CurrentVersion\AppCompatFlags\Layers' }
    )
    foreach ($root in $roots) {
        try {
            $item = Get-ItemProperty -LiteralPath $root.key -Name $exe -ErrorAction Stop
            $value = [string]$item.PSObject.Properties[$exe].Value
            [pscustomobject]@{
                scope = $root.label
                result = 'exact_path_entry_found'
                requests_admin = ($value -match '(?i)(^|\s)RUNASADMIN(\s|$)')
            } | ConvertTo-Json
        } catch {
            [pscustomobject]@{
                scope = $root.label
                result = 'entry_absent_or_unavailable'
                error_type = $_.Exception.GetType().Name
            } | ConvertTo-Json
        }
    }
}
```

该检查只查这一精确路径的常见 Layers 入口，不枚举所有注册表值，也不排除其他兼容性数据库、GPO 或终端策略。

### 按结果继续

- **哈希不匹配**：先核对是否拿错 runtime 变体/同名文件；从同一官方 Release 的完整 client ZIP 解压到新的当前用户目录，对照 ZIP 和 EXE 哈希。不要先改权限。
- **哈希匹配且当前用户路径有 RUNASADMIN**：本地打开该 EXE“属性 → 兼容性”，核对是否勾选“以管理员身份运行此程序”。若确认是本人给此文件设置的兼容性选项，可仅取消这个选项后重试普通启动；不要删除整个 Layers 键或改其他程序。
- **机器级 RUNASADMIN、配置被锁定或组织策略强制**：记录层级，由设备管理员核实。不要自动提权改 HKLM 或取消组织策略。
- **存在旁挂 .manifest**：本地只读查看其 requestedExecutionLevel，公开回复仅给 level 枚举；不要上传全文、删除文件或修改官方二进制。
- **环境中有兼容性层**：先查清是谁为此进程配置，不公开整个环境，也不使用 RunAsInvoker 来压制提升。
- **都未发现原因**：在新的普通 PowerShell 中，用完全相同的 EXE 路径执行朋友已有的 subprocess 探针，保留实际 winerror/returncode、stdout/stderr 字符数。若仍 740，再考虑机器兼容性数据库/策略；此时尚不能断言是官方客户端 bug。

普通 shell 的“立即返回/ExitCode=0”不能替代子进程实际启动的证据。Python CreateProcess 收到 740 时，目标进程未成功创建，不能当成 EXE 运行后返回的退出码。

## 同时确认本机 Outlook 前提

朋友目前只确认过 Outlook 网页界面，未确认经典 Outlook、COM/MAPI。先执行 README 的本机诊断，得到经典 OUTLOOK.EXE、COM 和 MAPI 状态；网页能登录不足以满足本桥的条件。

不要把 Outlook、Python Bridge 或 runner 整体改为管理员运行。修复目标是同一普通用户交互会话中的正常运行；安装范围、微软组织同意、OpenAI Tunnel 权限分别处理。

Python 3.14 + pywin32 安装成功只证明安装结果，尚不能证明历史 MCP 依赖与 COM 工作。若实际依赖报兼容性错误，再使用单独的 Python 3.12 venv 对照；不要先卸载朋友现有 Python。

## 需要下一次回复的最小结果

1. official_full_client_v0017_amd64_match：true/false。
2. 三个 Layers 范围的状态和 requests_admin；旁挂 manifest/环境兼容性层的布尔值。
3. 经典 Outlook 是否已安装登录；本机诊断 COM/MAPI 布尔结果。
4. 如已做了有证据支持的修复，普通启动后的实际结果。没有修复依据则写未修改。

不发本机路径、账号、邮箱、密钥、ID 或原始日志。

## 官方依据

- [官方 v0.0.17 Release](https://github.com/openai/tunnel-client/releases/tag/v0.0.17)
- [微软 740 错误定义](https://learn.microsoft.com/en-us/windows/win32/debug/system-error-codes--500-999-)
- [微软应用清单与执行级别](https://learn.microsoft.com/en-us/windows/win32/sbscs/application-manifests)
- [OpenAI Secure MCP Tunnel](https://developers.openai.com/api/docs/guides/secure-mcp-tunnels)
