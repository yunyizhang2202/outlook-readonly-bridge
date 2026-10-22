# Run in normal Windows PowerShell 5.1, under the same user as classic Outlook.
# Does not install, change policy, read mail bodies, or collect credentials.
$ErrorActionPreference = 'Stop'
$identity = [Security.Principal.WindowsIdentity]::GetCurrent()
$principal = New-Object Security.Principal.WindowsPrincipal($identity)
$report = [ordered]@{
    powershell_version = $PSVersionTable.PSVersion.ToString()
    elevated = $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
    classic_outlook_running = (@(Get-Process OUTLOOK -ErrorAction SilentlyContinue).Count -gt 0)
    com_connected = $false
    mapi_connected = $false
    account_count = $null
    error_stage = $null
}
$app = $null
$namespace = $null
try {
    $app = [Runtime.InteropServices.Marshal]::GetActiveObject('Outlook.Application')
    $report.com_connected = $true
    $namespace = $app.GetNamespace('MAPI')
    $report.account_count = [int]$namespace.Accounts.Count
    $report.mapi_connected = $true
} catch {
    $report.error_stage = if ($report.com_connected) {'MAPI_FAILED'} else {'COM_ATTACH_FAILED'}
} finally {
    $namespace = $null
    $app = $null
}
$report | ConvertTo-Json
