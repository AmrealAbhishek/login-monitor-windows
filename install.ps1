# Login Monitor PRO - Windows Edition
# One-line installer
# Run: irm https://raw.githubusercontent.com/AAbhishekk/login-monitor-windows/main/install.ps1 | iex

param(
    [string]$Email = "",
    [switch]$Uninstall = $false
)

$ErrorActionPreference = "Stop"

# Configuration
$AppName = "LoginMonitorPRO"
$RepoUrl = "https://github.com/AAbhishekk/login-monitor-windows"
$InstallDir = "$env:APPDATA\LoginMonitorPRO"
$ScriptsDir = "$InstallDir\scripts"
$LogDir = "$InstallDir\logs"

# Supabase config
$SupabaseUrl = "https://lrtgcyqngspjstgxhdub.supabase.co"
$SupabaseKey = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxydGdjeXFuZ3NwanN0Z3hoZHViIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzUxMDcwNjAsImV4cCI6MjA1MDY4MzA2MH0.m9M0QFGE8GxTvxpHC75RfmkRJHvo7bAB1xbnWvdykqc"

# Banner
function Show-Banner {
    Write-Host ""
    Write-Host "  ╔═══════════════════════════════════════════════╗" -ForegroundColor Red
    Write-Host "  ║                                               ║" -ForegroundColor Red
    Write-Host "  ║     LOGIN MONITOR PRO - WINDOWS EDITION       ║" -ForegroundColor Red
    Write-Host "  ║                                               ║" -ForegroundColor Red
    Write-Host "  ║     Monitor your PC from anywhere             ║" -ForegroundColor Red
    Write-Host "  ║                                               ║" -ForegroundColor Red
    Write-Host "  ╚═══════════════════════════════════════════════╝" -ForegroundColor Red
    Write-Host ""
}

# Check if running as admin
function Test-Admin {
    $currentUser = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($currentUser)
    return $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
}

# Install Python if needed
function Install-Python {
    Write-Host "[*] Checking Python..." -ForegroundColor Yellow

    try {
        $pythonVersion = python --version 2>&1
        Write-Host "[+] Python found: $pythonVersion" -ForegroundColor Green
        return $true
    }
    catch {
        Write-Host "[!] Python not found. Installing via winget..." -ForegroundColor Yellow

        try {
            winget install Python.Python.3.11 --accept-source-agreements --accept-package-agreements
            $env:Path = [System.Environment]::GetEnvironmentVariable("Path", "Machine") + ";" + [System.Environment]::GetEnvironmentVariable("Path", "User")
            return $true
        }
        catch {
            Write-Host "[!] Please install Python manually from python.org" -ForegroundColor Red
            return $false
        }
    }
}

# Install dependencies
function Install-Dependencies {
    Write-Host "[*] Installing Python dependencies..." -ForegroundColor Yellow

    $deps = @(
        "supabase",
        "pillow",
        "opencv-python",
        "sounddevice",
        "scipy",
        "psutil",
        "requests",
        "wmi",
        "pywin32"
    )

    foreach ($dep in $deps) {
        Write-Host "    Installing $dep..." -ForegroundColor Gray
        python -m pip install $dep -q 2>$null
    }

    Write-Host "[+] Dependencies installed" -ForegroundColor Green
}

# Download scripts
function Download-Scripts {
    Write-Host "[*] Downloading scripts..." -ForegroundColor Yellow

    # Create directories
    New-Item -ItemType Directory -Force -Path $ScriptsDir | Out-Null
    New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
    New-Item -ItemType Directory -Force -Path "$InstallDir\captures" | Out-Null
    New-Item -ItemType Directory -Force -Path "$InstallDir\audio" | Out-Null

    # Download from GitHub
    $files = @(
        "config.py",
        "scripts/screen_watcher.py",
        "scripts/command_listener.py",
        "scripts/pro_monitor.py"
    )

    $baseUrl = "https://raw.githubusercontent.com/AAbhishekk/login-monitor-windows/main"

    foreach ($file in $files) {
        $url = "$baseUrl/$file"
        $dest = "$InstallDir\$file"
        $destDir = Split-Path -Parent $dest

        if (!(Test-Path $destDir)) {
            New-Item -ItemType Directory -Force -Path $destDir | Out-Null
        }

        try {
            Invoke-WebRequest -Uri $url -OutFile $dest -UseBasicParsing
            Write-Host "    Downloaded: $file" -ForegroundColor Gray
        }
        catch {
            Write-Host "    [!] Failed to download: $file" -ForegroundColor Red
        }
    }

    Write-Host "[+] Scripts downloaded" -ForegroundColor Green
}

# Generate device ID
function New-DeviceId {
    $hostname = $env:COMPUTERNAME
    $username = $env:USERNAME
    $machineGuid = (Get-ItemProperty -Path "HKLM:\SOFTWARE\Microsoft\Cryptography" -Name MachineGuid).MachineGuid

    $combined = "$hostname-$username-$machineGuid"
    $bytes = [System.Text.Encoding]::UTF8.GetBytes($combined)
    $hash = [System.Security.Cryptography.SHA256]::Create().ComputeHash($bytes)
    $deviceId = [System.BitConverter]::ToString($hash).Replace("-", "").Substring(0, 32).ToLower()

    return $deviceId
}

# Register device with Supabase
function Register-Device {
    param([string]$Email)

    Write-Host "[*] Registering device..." -ForegroundColor Yellow

    $deviceId = New-DeviceId
    $hostname = $env:COMPUTERNAME
    $username = $env:USERNAME

    # Check if user exists with this email
    $headers = @{
        "apikey" = $SupabaseKey
        "Authorization" = "Bearer $SupabaseKey"
        "Content-Type" = "application/json"
    }

    try {
        # Look up user by email
        $userResponse = Invoke-RestMethod -Uri "$SupabaseUrl/rest/v1/users?email=eq.$Email&select=id" -Headers $headers -Method Get

        if ($userResponse.Count -eq 0) {
            Write-Host "[!] No account found for: $Email" -ForegroundColor Red
            Write-Host "[!] Please create an account in the mobile app first" -ForegroundColor Yellow
            return $null
        }

        $userId = $userResponse[0].id
        Write-Host "[+] Found user: $userId" -ForegroundColor Green

        # Register device
        $deviceData = @{
            id = $deviceId
            user_id = $userId
            hostname = $hostname
            username = $username
            platform = "windows"
            os_version = [System.Environment]::OSVersion.VersionString
            is_online = $true
            last_seen = (Get-Date).ToUniversalTime().ToString("yyyy-MM-ddTHH:mm:ssZ")
        } | ConvertTo-Json

        # Try to insert or update
        try {
            Invoke-RestMethod -Uri "$SupabaseUrl/rest/v1/devices" -Headers $headers -Method Post -Body $deviceData
        }
        catch {
            # Device might exist, try update
            $updateHeaders = $headers.Clone()
            $updateHeaders["Prefer"] = "return=minimal"
            Invoke-RestMethod -Uri "$SupabaseUrl/rest/v1/devices?id=eq.$deviceId" -Headers $updateHeaders -Method Patch -Body $deviceData
        }

        Write-Host "[+] Device registered: $deviceId" -ForegroundColor Green

        # Save config
        $config = @{
            device_id = $deviceId
            user_id = $userId
            email = $Email
            hostname = $hostname
            installed_at = (Get-Date).ToString("yyyy-MM-dd HH:mm:ss")
        } | ConvertTo-Json

        $config | Out-File -FilePath "$InstallDir\config.json" -Encoding UTF8

        return $deviceId
    }
    catch {
        Write-Host "[!] Registration failed: $_" -ForegroundColor Red
        return $null
    }
}

# Create scheduled tasks
function Install-ScheduledTasks {
    Write-Host "[*] Creating scheduled tasks..." -ForegroundColor Yellow

    # Command Listener Task
    $action = New-ScheduledTaskAction -Execute "pythonw.exe" -Argument "`"$ScriptsDir\command_listener.py`"" -WorkingDirectory $InstallDir
    $trigger = New-ScheduledTaskTrigger -AtLogOn
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Highest
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)

    Register-ScheduledTask -TaskName "LoginMonitorPRO_Commands" -Action $action -Trigger $trigger -Principal $principal -Settings $settings -Force | Out-Null
    Write-Host "    Created: LoginMonitorPRO_Commands" -ForegroundColor Gray

    # Screen Watcher Task (needs admin for Security log)
    $action2 = New-ScheduledTaskAction -Execute "pythonw.exe" -Argument "`"$ScriptsDir\screen_watcher.py`"" -WorkingDirectory $InstallDir
    $trigger2 = New-ScheduledTaskTrigger -AtLogOn
    $principal2 = New-ScheduledTaskPrincipal -UserId "SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    $settings2 = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable

    try {
        Register-ScheduledTask -TaskName "LoginMonitorPRO_Watcher" -Action $action2 -Trigger $trigger2 -Principal $principal2 -Settings $settings2 -Force | Out-Null
        Write-Host "    Created: LoginMonitorPRO_Watcher" -ForegroundColor Gray
    }
    catch {
        Write-Host "    [!] Watcher task needs admin. Run as Administrator." -ForegroundColor Yellow
    }

    Write-Host "[+] Scheduled tasks created" -ForegroundColor Green
}

# Start services
function Start-Services {
    Write-Host "[*] Starting services..." -ForegroundColor Yellow

    Start-ScheduledTask -TaskName "LoginMonitorPRO_Commands" -ErrorAction SilentlyContinue
    Start-ScheduledTask -TaskName "LoginMonitorPRO_Watcher" -ErrorAction SilentlyContinue

    Write-Host "[+] Services started" -ForegroundColor Green
}

# Uninstall
function Uninstall-LoginMonitor {
    Write-Host "[*] Uninstalling Login Monitor PRO..." -ForegroundColor Yellow

    # Stop and remove tasks
    Stop-ScheduledTask -TaskName "LoginMonitorPRO_Commands" -ErrorAction SilentlyContinue
    Stop-ScheduledTask -TaskName "LoginMonitorPRO_Watcher" -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName "LoginMonitorPRO_Commands" -Confirm:$false -ErrorAction SilentlyContinue
    Unregister-ScheduledTask -TaskName "LoginMonitorPRO_Watcher" -Confirm:$false -ErrorAction SilentlyContinue

    # Remove files
    if (Test-Path $InstallDir) {
        Remove-Item -Path $InstallDir -Recurse -Force
    }

    Write-Host "[+] Uninstalled successfully" -ForegroundColor Green
}

# Main
function Main {
    Show-Banner

    if ($Uninstall) {
        Uninstall-LoginMonitor
        return
    }

    # Check admin
    if (!(Test-Admin)) {
        Write-Host "[!] Some features require Administrator privileges" -ForegroundColor Yellow
        Write-Host "[!] For full functionality, run as Administrator" -ForegroundColor Yellow
        Write-Host ""
    }

    # Get email
    if ([string]::IsNullOrEmpty($Email)) {
        $Email = Read-Host "Enter your Login Monitor PRO email"
    }

    if ([string]::IsNullOrEmpty($Email)) {
        Write-Host "[!] Email is required" -ForegroundColor Red
        return
    }

    # Install
    if (!(Install-Python)) {
        return
    }

    Install-Dependencies
    Download-Scripts

    $deviceId = Register-Device -Email $Email
    if ($null -eq $deviceId) {
        return
    }

    Install-ScheduledTasks
    Start-Services

    Write-Host ""
    Write-Host "  ╔═══════════════════════════════════════════════╗" -ForegroundColor Green
    Write-Host "  ║                                               ║" -ForegroundColor Green
    Write-Host "  ║     INSTALLATION COMPLETE!                    ║" -ForegroundColor Green
    Write-Host "  ║                                               ║" -ForegroundColor Green
    Write-Host "  ║     Device ID: $($deviceId.Substring(0,8))...                   ║" -ForegroundColor Green
    Write-Host "  ║                                               ║" -ForegroundColor Green
    Write-Host "  ║     Open the mobile app to see your device    ║" -ForegroundColor Green
    Write-Host "  ║                                               ║" -ForegroundColor Green
    Write-Host "  ╚═══════════════════════════════════════════════╝" -ForegroundColor Green
    Write-Host ""
    Write-Host "Commands:" -ForegroundColor Cyan
    Write-Host "  Start:     Start-ScheduledTask -TaskName 'LoginMonitorPRO_Commands'" -ForegroundColor Gray
    Write-Host "  Stop:      Stop-ScheduledTask -TaskName 'LoginMonitorPRO_Commands'" -ForegroundColor Gray
    Write-Host "  Uninstall: irm $RepoUrl/main/install.ps1 | iex -Uninstall" -ForegroundColor Gray
    Write-Host ""
}

Main
