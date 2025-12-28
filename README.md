# Login Monitor PRO - Windows Edition

Monitor your Windows PC from anywhere using the Login Monitor PRO mobile app.

## Features

| Feature | Description |
|---------|-------------|
| **Login Detection** | Get notified when someone logs into your PC |
| **Unlock Detection** | Get notified when your PC is unlocked |
| **Intruder Detection** | Alert after 3 failed login attempts in 5 minutes |
| **Screenshot Capture** | Capture screenshots remotely |
| **Webcam Photo** | Take photos using the webcam |
| **Audio Recording** | Record ambient audio |
| **Location Tracking** | IP-based geolocation |
| **Battery Status** | Check battery level and charging status |
| **WiFi Info** | Get current WiFi network details |
| **System Info** | CPU, memory, disk usage |
| **App Usage** | See running applications |
| **Remote Lock** | Lock the workstation remotely |
| **Find My PC** | Play alarm sound and track location |
| **Remote Shutdown** | Schedule shutdown or restart |

## Quick Install (One-Line)

Open PowerShell and run:

```powershell
irm https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-windows/main/install.ps1 | iex
```

Or with email:

```powershell
irm https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-windows/main/install.ps1 | iex; Install -Email "your@email.com"
```

## Quick Uninstall (One-Line)

```powershell
irm https://raw.githubusercontent.com/AmrealAbhishek/login-monitor-windows/main/uninstall.ps1 | iex
```

## Manual Installation

1. **Download the scripts:**
   ```powershell
   git clone https://github.com/AmrealAbhishek/login-monitor-windows.git
   cd login-monitor-windows
   ```

2. **Install dependencies:**
   ```powershell
   pip install supabase pillow opencv-python sounddevice scipy psutil requests wmi pywin32
   ```

3. **Run the installer:**
   ```powershell
   .\install.ps1 -Email "your@email.com"
   ```

## Requirements

- Windows 10 or 11
- Python 3.8+
- Webcam (optional, for photo capture)
- Microphone (optional, for audio recording)
- Administrator privileges (for login/unlock detection)

## How It Works

1. **Screen Watcher** monitors Windows Event Log for:
   - Event ID 4624: Successful logon
   - Event ID 4625: Failed logon (intruder detection)
   - Event ID 4800: Workstation locked
   - Event ID 4801: Workstation unlocked

2. **Command Listener** polls Supabase for commands from the mobile app

3. **Pro Monitor** captures photos and location on login/unlock events

## Commands

| Command | Description | Options |
|---------|-------------|---------|
| `status` | Get system status | - |
| `screenshot` | Capture screenshot | - |
| `photo` | Take webcam photo | `count`: 1-5 |
| `location` | Get IP-based location | - |
| `battery` | Get battery info | - |
| `wifiinfo` | Get WiFi details | - |
| `sysinfo` | Get system info | - |
| `audio` | Record audio | `duration`: 5-120s |
| `alarm` | Play alarm | `duration`: 10-60s |
| `findme` | Find PC (sound + location) | `duration`: 30-300s |
| `stop` | Stop all running commands | - |
| `lockscreen` | Lock workstation | - |
| `shutdown` | Schedule shutdown | `delay`: seconds |
| `restart` | Schedule restart | `delay`: seconds |
| `appusage` | List running apps | - |
| `listnetworks` | List saved WiFi networks | - |

## Manage Services

**Start:**
```powershell
Start-ScheduledTask -TaskName "LoginMonitorPRO_Commands"
```

**Stop:**
```powershell
Stop-ScheduledTask -TaskName "LoginMonitorPRO_Commands"
```

**Check Status:**
```powershell
Get-ScheduledTask -TaskName "LoginMonitorPRO_*" | Select TaskName, State
```

## Logs

Logs are stored in:
```
%APPDATA%\LoginMonitorPRO\logs\
```

- `screen_watcher.log` - Login/unlock events
- `command_listener.log` - Command processing
- `pro_monitor.log` - Photo/location capture

## Configuration

Config file location:
```
%APPDATA%\LoginMonitorPRO\config.json
```

## Security & Privacy

- All data is transmitted securely via HTTPS to Supabase
- Photos, screenshots, and audio are stored in Supabase Storage
- Only you can access your device's data via the mobile app
- No data is shared with third parties

## Troubleshooting

**"Access denied" when reading Event Log:**
- Run PowerShell as Administrator
- Or run the installer as Administrator

**Webcam not working:**
- Check if another app is using the camera
- Make sure camera drivers are installed

**Commands not executing:**
- Check if Python is in PATH
- Check logs in `%APPDATA%\LoginMonitorPRO\logs\`
- Restart the scheduled tasks

**Device not showing in app:**
- Verify your email matches the account
- Check internet connection
- Check the config.json file

## License

MIT License - Use at your own risk.

## Support

For issues, please open a GitHub issue.
