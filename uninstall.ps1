# Login Monitor PRO - Windows Edition
# Uninstaller
# Run: irm https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-windows/main/uninstall.ps1 | iex

$ErrorActionPreference = "SilentlyContinue"

$InstallDir = "$env:APPDATA\LoginMonitorPRO"

Write-Host ""
Write-Host "  ╔═══════════════════════════════════════════════╗" -ForegroundColor Red
Write-Host "  ║                                               ║" -ForegroundColor Red
Write-Host "  ║     LOGIN MONITOR PRO - UNINSTALLER           ║" -ForegroundColor Red
Write-Host "  ║                                               ║" -ForegroundColor Red
Write-Host "  ╚═══════════════════════════════════════════════╝" -ForegroundColor Red
Write-Host ""

Write-Host "[*] Stopping services..." -ForegroundColor Yellow

# Kill Python processes
Get-Process -Name "python*" -ErrorAction SilentlyContinue | Where-Object {
    $_.CommandLine -like "*LoginMonitorPRO*"
} | Stop-Process -Force -ErrorAction SilentlyContinue

# Stop scheduled tasks
Stop-ScheduledTask -TaskName "LoginMonitorPRO_Commands" -ErrorAction SilentlyContinue
Stop-ScheduledTask -TaskName "LoginMonitorPRO_Watcher" -ErrorAction SilentlyContinue

Write-Host "[*] Removing scheduled tasks..." -ForegroundColor Yellow
Unregister-ScheduledTask -TaskName "LoginMonitorPRO_Commands" -Confirm:$false -ErrorAction SilentlyContinue
Unregister-ScheduledTask -TaskName "LoginMonitorPRO_Watcher" -Confirm:$false -ErrorAction SilentlyContinue

Write-Host "[*] Removing files..." -ForegroundColor Yellow
if (Test-Path $InstallDir) {
    Remove-Item -Path $InstallDir -Recurse -Force -ErrorAction SilentlyContinue
}

Write-Host ""
Write-Host "[+] Login Monitor PRO has been uninstalled" -ForegroundColor Green
Write-Host ""
Write-Host "Note: Python and pip packages were NOT removed." -ForegroundColor Gray
Write-Host "To remove them manually, run:" -ForegroundColor Gray
Write-Host "  pip uninstall supabase pillow opencv-python sounddevice scipy psutil wmi pywin32" -ForegroundColor Gray
Write-Host ""
