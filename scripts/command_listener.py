#!/usr/bin/env python3
"""
Login Monitor PRO - Windows Edition
Command Listener

Listens for commands from the Flutter app via Supabase and executes them.
"""

import sys
import os
import json
import time
import socket
import logging
import subprocess
import threading
import base64
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

# Install dependencies
def install_deps():
    deps = ['supabase', 'pillow', 'opencv-python', 'sounddevice', 'scipy', 'psutil', 'requests', 'wmi']
    for dep in deps:
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "-q"])
        except:
            pass

try:
    from supabase import create_client, Client
    from supabase._async.client import create_client as create_async_client
    import asyncio
    import psutil
    from PIL import ImageGrab
    import cv2
    import sounddevice as sd
    from scipy.io.wavfile import write as wav_write
    import requests
    import wmi
    REALTIME_AVAILABLE = True
except ImportError:
    print("Installing dependencies...")
    install_deps()
    from supabase import create_client, Client
    try:
        from supabase._async.client import create_client as create_async_client
        import asyncio
        REALTIME_AVAILABLE = True
    except:
        REALTIME_AVAILABLE = False
    import psutil
    from PIL import ImageGrab
    import cv2
    import sounddevice as sd
    from scipy.io.wavfile import write as wav_write
    import requests
    import wmi

from config import (
    SUPABASE_URL, SUPABASE_ANON_KEY, CONFIG_FILE, LOG_DIR,
    CAPTURE_DIR, AUDIO_DIR
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'command_listener.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class CommandListener:
    def __init__(self):
        self.supabase: Client = None
        self.device_id = None
        self.user_id = None
        self.wmi_client = None
        self.running_commands = {}  # Track running commands
        self.load_config()
        self.init_supabase()
        self.init_wmi()

        # Command handlers
        self.handlers = {
            'status': self.cmd_status,
            'screenshot': self.cmd_screenshot,
            'photo': self.cmd_photo,
            'location': self.cmd_location,
            'battery': self.cmd_battery,
            'wifiinfo': self.cmd_wifiinfo,
            'sysinfo': self.cmd_sysinfo,
            'audio': self.cmd_audio,
            'alarm': self.cmd_alarm,
            'findme': self.cmd_findme,
            'stopfind': self.cmd_stopfind,
            'stop': self.cmd_stop,
            'listnetworks': self.cmd_listnetworks,
            'appusage': self.cmd_appusage,
            'processes': self.cmd_processes,
            'lockscreen': self.cmd_lockscreen,
            'shutdown': self.cmd_shutdown,
            'restart': self.cmd_restart,
        }

    def load_config(self):
        """Load configuration"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.device_id = config.get('device_id')
                    self.user_id = config.get('user_id')
                    logger.info(f"Loaded config: device_id={self.device_id}")
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    def init_supabase(self):
        """Initialize Supabase"""
        try:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            logger.info("Supabase initialized")
        except Exception as e:
            logger.error(f"Supabase init failed: {e}")

    def init_wmi(self):
        """Initialize WMI for system info"""
        try:
            self.wmi_client = wmi.WMI()
        except Exception as e:
            logger.warning(f"WMI init failed: {e}")

    # ==================== COMMAND HANDLERS ====================

    def cmd_status(self, args: dict) -> dict:
        """Get system status"""
        try:
            hostname = socket.gethostname()
            username = os.environ.get('USERNAME', 'Unknown')

            # Uptime
            boot_time = datetime.fromtimestamp(psutil.boot_time())
            uptime = datetime.now() - boot_time
            uptime_str = f"{uptime.days}d {uptime.seconds // 3600}h {(uptime.seconds % 3600) // 60}m"

            # Memory
            mem = psutil.virtual_memory()

            # Disk
            disk = psutil.disk_usage('C:\\')

            return {
                'success': True,
                'hostname': hostname,
                'username': username,
                'os': 'Windows',
                'os_version': self.get_windows_version(),
                'uptime': uptime_str,
                'memory_total': f"{mem.total // (1024**3)} GB",
                'memory_used': f"{mem.used // (1024**3)} GB",
                'memory_percent': f"{mem.percent}%",
                'disk_total': f"{disk.total // (1024**3)} GB",
                'disk_used': f"{disk.used // (1024**3)} GB",
                'disk_percent': f"{disk.percent}%",
                'cpu_percent': f"{psutil.cpu_percent()}%",
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def get_windows_version(self) -> str:
        """Get Windows version string"""
        try:
            import platform
            return platform.platform()
        except:
            return "Windows"

    def cmd_screenshot(self, args: dict) -> dict:
        """Capture screenshot"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"screenshot_{timestamp}.png"
            filepath = CAPTURE_DIR / filename

            # Capture screenshot using Pillow
            screenshot = ImageGrab.grab()
            screenshot.save(filepath, 'PNG')

            # Upload to Supabase Storage
            url = self.upload_file(filepath, 'screenshots', filename)

            return {
                'success': True,
                'message': 'Screenshot captured',
                'filename': filename,
                'url': url,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_photo(self, args: dict) -> dict:
        """Capture photo from webcam"""
        try:
            count = min(int(args.get('count', 1)), 5)
            photos = []

            # Open webcam
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                return {'success': False, 'error': 'No webcam found'}

            # Wait for camera to warm up
            time.sleep(0.5)

            for i in range(count):
                ret, frame = cap.read()
                if ret:
                    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                    filename = f"photo_{timestamp}_{i+1}.jpg"
                    filepath = CAPTURE_DIR / filename

                    cv2.imwrite(str(filepath), frame)
                    url = self.upload_file(filepath, 'photos', filename)
                    photos.append({'filename': filename, 'url': url})

                time.sleep(0.3)

            cap.release()

            return {
                'success': True,
                'message': f'Captured {len(photos)} photo(s)',
                'photos': photos,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_location(self, args: dict) -> dict:
        """Get location (IP-based for Windows)"""
        try:
            # Use IP geolocation service
            response = requests.get('http://ip-api.com/json/', timeout=10)
            data = response.json()

            if data.get('status') == 'success':
                return {
                    'success': True,
                    'latitude': data.get('lat'),
                    'longitude': data.get('lon'),
                    'city': data.get('city'),
                    'region': data.get('regionName'),
                    'country': data.get('country'),
                    'isp': data.get('isp'),
                    'ip': data.get('query'),
                    'source': 'IP Geolocation',
                }
            else:
                return {'success': False, 'error': 'Could not determine location'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_battery(self, args: dict) -> dict:
        """Get battery status"""
        try:
            battery = psutil.sensors_battery()
            if battery:
                return {
                    'success': True,
                    'percent': battery.percent,
                    'plugged': battery.power_plugged,
                    'status': 'Charging' if battery.power_plugged else 'Discharging',
                    'time_left': str(battery.secsleft // 60) + ' minutes' if battery.secsleft > 0 else 'N/A',
                }
            else:
                return {
                    'success': True,
                    'percent': 100,
                    'plugged': True,
                    'status': 'Desktop (No Battery)',
                }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_wifiinfo(self, args: dict) -> dict:
        """Get WiFi information"""
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'interfaces'],
                capture_output=True,
                text=True
            )

            info = {}
            for line in result.stdout.split('\n'):
                if ':' in line:
                    key, value = line.split(':', 1)
                    info[key.strip()] = value.strip()

            return {
                'success': True,
                'ssid': info.get('SSID', 'Not connected'),
                'bssid': info.get('BSSID', 'N/A'),
                'signal': info.get('Signal', 'N/A'),
                'radio_type': info.get('Radio type', 'N/A'),
                'authentication': info.get('Authentication', 'N/A'),
                'channel': info.get('Channel', 'N/A'),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_sysinfo(self, args: dict) -> dict:
        """Get detailed system information"""
        try:
            info = self.cmd_status({})

            # Add more details via WMI
            if self.wmi_client:
                for os_info in self.wmi_client.Win32_OperatingSystem():
                    info['os_name'] = os_info.Caption
                    info['os_arch'] = os_info.OSArchitecture

                for cpu in self.wmi_client.Win32_Processor():
                    info['cpu'] = cpu.Name
                    info['cpu_cores'] = cpu.NumberOfCores

            return info
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_audio(self, args: dict) -> dict:
        """Record audio"""
        try:
            duration = min(int(args.get('duration', 10)), 120)
            sample_rate = 44100

            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"audio_{timestamp}.wav"
            filepath = AUDIO_DIR / filename

            logger.info(f"Recording audio for {duration} seconds...")

            # Record
            recording = sd.rec(
                int(duration * sample_rate),
                samplerate=sample_rate,
                channels=1,
                dtype='int16'
            )
            sd.wait()

            # Save
            wav_write(filepath, sample_rate, recording)

            # Upload
            url = self.upload_file(filepath, 'audio', filename)

            return {
                'success': True,
                'message': f'Recorded {duration} seconds of audio',
                'filename': filename,
                'url': url,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_alarm(self, args: dict) -> dict:
        """Play alarm sound"""
        try:
            duration = min(int(args.get('duration', 10)), 60)

            # Track this command
            self.running_commands['alarm'] = True

            def play_alarm():
                import winsound
                start = time.time()
                while time.time() - start < duration:
                    if not self.running_commands.get('alarm'):
                        break
                    winsound.Beep(1000, 500)  # 1000 Hz for 500ms
                    time.sleep(0.1)
                self.running_commands['alarm'] = False

            thread = threading.Thread(target=play_alarm)
            thread.start()

            return {
                'success': True,
                'message': f'Playing alarm for {duration} seconds',
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_findme(self, args: dict) -> dict:
        """Find my device - play sound and report location"""
        try:
            duration = min(int(args.get('duration', 60)), 300)

            self.running_commands['findme'] = True

            def find_loop():
                import winsound
                start = time.time()
                while time.time() - start < duration:
                    if not self.running_commands.get('findme'):
                        break
                    # Play beep
                    winsound.Beep(2000, 200)
                    time.sleep(1)

                    # Report location every 10 seconds
                    if int(time.time() - start) % 10 == 0:
                        loc = self.cmd_location({})
                        if loc.get('success'):
                            self.update_device_location(loc)

                self.running_commands['findme'] = False

            thread = threading.Thread(target=find_loop)
            thread.start()

            # Get initial location
            location = self.cmd_location({})

            return {
                'success': True,
                'message': f'Find Me active for {duration} seconds',
                'location': location,
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_stopfind(self, args: dict) -> dict:
        """Stop find me"""
        self.running_commands['findme'] = False
        return {'success': True, 'message': 'Find Me stopped'}

    def cmd_stop(self, args: dict) -> dict:
        """Universal stop - stop all running commands"""
        try:
            stopped = []

            # Stop alarm
            if self.running_commands.get('alarm'):
                self.running_commands['alarm'] = False
                stopped.append('alarm')

            # Stop findme
            if self.running_commands.get('findme'):
                self.running_commands['findme'] = False
                stopped.append('findme')

            # Stop any audio recording (sounddevice)
            try:
                sd.stop()
                stopped.append('audio')
            except:
                pass

            message = f"Stopped: {', '.join(stopped)}" if stopped else "No active commands to stop"
            return {'success': True, 'stopped': stopped, 'message': message}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_listnetworks(self, args: dict) -> dict:
        """List saved WiFi networks"""
        try:
            result = subprocess.run(
                ['netsh', 'wlan', 'show', 'profiles'],
                capture_output=True,
                text=True
            )

            networks = []
            for line in result.stdout.split('\n'):
                if 'All User Profile' in line:
                    name = line.split(':')[1].strip()
                    networks.append(name)

            return {
                'success': True,
                'networks': networks,
                'count': len(networks),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_appusage(self, args: dict) -> dict:
        """Get running applications"""
        try:
            apps = []
            for proc in psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']):
                try:
                    info = proc.info
                    if info['memory_percent'] > 0.1:  # Filter out tiny processes
                        apps.append({
                            'name': info['name'],
                            'pid': info['pid'],
                            'memory': f"{info['memory_percent']:.1f}%",
                            'cpu': f"{info['cpu_percent']:.1f}%",
                        })
                except:
                    pass

            # Sort by memory usage
            apps.sort(key=lambda x: float(x['memory'].replace('%', '')), reverse=True)

            return {
                'success': True,
                'apps': apps[:20],  # Top 20
                'total': len(apps),
            }
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_processes(self, args: dict) -> dict:
        """Get detailed process list"""
        return self.cmd_appusage(args)

    def cmd_lockscreen(self, args: dict) -> dict:
        """Lock the workstation"""
        try:
            import ctypes
            ctypes.windll.user32.LockWorkStation()
            return {'success': True, 'message': 'Workstation locked'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_shutdown(self, args: dict) -> dict:
        """Shutdown the computer"""
        try:
            delay = int(args.get('delay', 60))
            subprocess.run(['shutdown', '/s', '/t', str(delay)])
            return {'success': True, 'message': f'Shutdown scheduled in {delay} seconds'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def cmd_restart(self, args: dict) -> dict:
        """Restart the computer"""
        try:
            delay = int(args.get('delay', 60))
            subprocess.run(['shutdown', '/r', '/t', str(delay)])
            return {'success': True, 'message': f'Restart scheduled in {delay} seconds'}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ==================== HELPER METHODS ====================

    def upload_file(self, filepath: Path, bucket: str, filename: str) -> Optional[str]:
        """Upload file to Supabase Storage"""
        try:
            with open(filepath, 'rb') as f:
                data = f.read()

            path = f"{self.device_id}/{filename}"
            self.supabase.storage.from_(bucket).upload(path, data)

            # Get public URL
            url = self.supabase.storage.from_(bucket).get_public_url(path)
            return url
        except Exception as e:
            logger.error(f"Upload failed: {e}")
            return None

    def update_device_location(self, location: dict):
        """Update device location in database"""
        try:
            self.supabase.table('devices').update({
                'last_location_lat': location.get('latitude'),
                'last_location_lon': location.get('longitude'),
                'last_location_city': location.get('city'),
            }).eq('id', self.device_id).execute()
        except Exception as e:
            logger.error(f"Failed to update location: {e}")

    def update_command_result(self, command_id: str, result: dict):
        """Update command result in database"""
        try:
            self.supabase.table('commands').update({
                'status': 'completed',
                'result': json.dumps(result),
                'completed_at': datetime.utcnow().isoformat(),
            }).eq('id', command_id).execute()
        except Exception as e:
            logger.error(f"Failed to update command result: {e}")

    def process_command(self, command: dict):
        """Process a single command"""
        try:
            cmd_id = command['id']
            cmd_name = command['command'].lower()
            cmd_args = command.get('args', {})

            if isinstance(cmd_args, str):
                try:
                    cmd_args = json.loads(cmd_args)
                except:
                    cmd_args = {}

            logger.info(f"Processing command: {cmd_name}")

            handler = self.handlers.get(cmd_name)
            if handler:
                result = handler(cmd_args)
            else:
                result = {'success': False, 'error': f'Unknown command: {cmd_name}'}

            self.update_command_result(cmd_id, result)
            logger.info(f"Command {cmd_name} completed: {result.get('success')}")

        except Exception as e:
            logger.error(f"Error processing command: {e}")

    def on_command_received(self, payload):
        """Callback when a new command is received via Realtime"""
        try:
            logger.info(f"Realtime event: {payload.get('eventType')}")

            if payload.get('eventType') == 'INSERT':
                record = payload.get('new', {})

                # Check if this command is for our device and pending
                if (record.get('device_id') == self.device_id and
                    record.get('status') == 'pending'):
                    logger.info(f"New command received: {record.get('command')}")
                    self.process_command(record)

        except Exception as e:
            logger.error(f"Error handling realtime event: {e}")

    def heartbeat_loop(self):
        """Background thread to update device heartbeat"""
        while self.running:
            try:
                self.supabase.table('devices').update({
                    'last_seen': datetime.utcnow().isoformat(),
                    'is_online': True,
                }).eq('id', self.device_id).execute()
            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
            time.sleep(30)  # Update every 30 seconds

    def process_pending_commands(self):
        """Process any pending commands (on startup or reconnect)"""
        try:
            result = self.supabase.table('commands').select('*').eq(
                'device_id', self.device_id
            ).eq('status', 'pending').execute()

            for command in result.data:
                self.process_command(command)

            if result.data:
                logger.info(f"Processed {len(result.data)} pending commands")
        except Exception as e:
            logger.error(f"Error processing pending commands: {e}")

    def listen(self):
        """Main listen loop using Supabase Realtime"""
        logger.info("Starting command listener...")

        if not self.device_id:
            logger.error("No device configured. Run installer first.")
            return

        logger.info(f"Device ID: {self.device_id}")
        self.running = True

        # Process any pending commands first
        self.process_pending_commands()

        # Start heartbeat in background thread
        heartbeat_thread = threading.Thread(target=self.heartbeat_loop, daemon=True)
        heartbeat_thread.start()
        logger.info("Heartbeat thread started")

        # Try Realtime mode first
        if REALTIME_AVAILABLE:
            try:
                asyncio.run(self.listen_realtime())
            except KeyboardInterrupt:
                logger.info("Command listener stopped by user")
                self.running = False
            except Exception as e:
                logger.error(f"Realtime failed: {e}")
                logger.info("Falling back to polling mode...")
                self.listen_polling()
        else:
            logger.info("Realtime not available, using polling mode")
            self.listen_polling()

    async def listen_realtime(self):
        """Async Realtime listener"""
        # Create async client
        realtime_client = await create_async_client(SUPABASE_URL, SUPABASE_ANON_KEY)

        # Subscribe to commands channel
        channel = realtime_client.channel('commands-channel')

        def handle_insert(payload):
            """Handle INSERT event"""
            self.on_command_received(payload)

        channel.on_postgres_changes(
            event='INSERT',
            schema='public',
            table='commands',
            filter=f'device_id=eq.{self.device_id}',
            callback=handle_insert
        )

        await channel.subscribe()

        logger.info("=" * 50)
        logger.info("REALTIME MODE - Commands execute INSTANTLY!")
        logger.info("=" * 50)

        # Keep alive
        while self.running:
            await asyncio.sleep(1)

    def listen_polling(self):
        """Fallback polling mode if Realtime fails"""
        logger.info("Using polling mode (fallback)...")

        while self.running:
            try:
                # Fetch pending commands
                result = self.supabase.table('commands').select('*').eq(
                    'device_id', self.device_id
                ).eq('status', 'pending').execute()

                for command in result.data:
                    self.process_command(command)

                # Update device heartbeat
                self.supabase.table('devices').update({
                    'last_seen': datetime.utcnow().isoformat(),
                    'is_online': True,
                }).eq('id', self.device_id).execute()

            except Exception as e:
                logger.error(f"Listen loop error: {e}")

            time.sleep(3)


def main():
    listener = CommandListener()
    listener.listen()


if __name__ == '__main__':
    main()
