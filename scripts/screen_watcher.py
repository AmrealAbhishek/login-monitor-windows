#!/usr/bin/env python3
"""
Login Monitor PRO - Windows Edition
Screen/Login Event Watcher

Monitors Windows Event Log for:
- Event ID 4624: Successful logon
- Event ID 4625: Failed logon (intruder detection)
- Event ID 4800: Workstation locked
- Event ID 4801: Workstation unlocked
- Event ID 4802: Screen saver invoked
- Event ID 4803: Screen saver dismissed
"""

import sys
import os
import json
import time
import socket
import logging
import subprocess
from datetime import datetime, timedelta
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import win32evtlog
    import win32con
    import win32api
    import win32security
    import pywintypes
except ImportError:
    print("Installing pywin32...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "pywin32", "-q"])
    import win32evtlog
    import win32con
    import win32api
    import win32security
    import pywintypes

try:
    from supabase import create_client, Client
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "supabase", "-q"])
    from supabase import create_client, Client

from config import (
    SUPABASE_URL, SUPABASE_ANON_KEY, CONFIG_FILE, LOG_DIR,
    MAX_FAILED_ATTEMPTS, FAILED_ATTEMPT_WINDOW
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'screen_watcher.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class WindowsEventWatcher:
    def __init__(self):
        self.supabase: Client = None
        self.device_id = None
        self.user_id = None
        self.last_event_time = datetime.now()
        self.failed_attempts = []
        self.load_config()
        self.init_supabase()

    def load_config(self):
        """Load configuration from file"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.device_id = config.get('device_id')
                    self.user_id = config.get('user_id')
                    logger.info(f"Loaded config: device_id={self.device_id}")
            else:
                logger.warning("No config file found. Run installer first.")
        except Exception as e:
            logger.error(f"Error loading config: {e}")

    def init_supabase(self):
        """Initialize Supabase client"""
        try:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
            logger.info("Supabase client initialized")
        except Exception as e:
            logger.error(f"Failed to initialize Supabase: {e}")

    def get_hostname(self):
        """Get Windows hostname"""
        return socket.gethostname()

    def get_username(self):
        """Get current Windows username"""
        return os.environ.get('USERNAME', 'Unknown')

    def check_intruder(self) -> bool:
        """Check if too many failed login attempts"""
        now = datetime.now()
        # Remove old attempts outside the window
        self.failed_attempts = [
            t for t in self.failed_attempts
            if (now - t).total_seconds() < FAILED_ATTEMPT_WINDOW
        ]
        return len(self.failed_attempts) >= MAX_FAILED_ATTEMPTS

    def send_event(self, event_type: str, extra_data: dict = None):
        """Send event to Supabase"""
        if not self.device_id:
            logger.warning("No device_id configured, skipping event")
            return

        try:
            event_data = {
                'device_id': self.device_id,
                'event_type': event_type,
                'timestamp': datetime.utcnow().isoformat(),
                'username': self.get_username(),
                'hostname': self.get_hostname(),
                'is_read': False,
            }

            if extra_data:
                event_data['extra_data'] = json.dumps(extra_data)

            result = self.supabase.table('events').insert(event_data).execute()
            logger.info(f"Event sent: {event_type}")

            # Trigger pro_monitor for photo/location capture
            if event_type in ['Login', 'Unlock', 'Intruder']:
                self.trigger_capture(event_type)

        except Exception as e:
            logger.error(f"Failed to send event: {e}")

    def trigger_capture(self, event_type: str):
        """Trigger photo and location capture"""
        try:
            script_dir = Path(__file__).parent
            pro_monitor = script_dir / 'pro_monitor.py'
            if pro_monitor.exists():
                subprocess.Popen(
                    [sys.executable, str(pro_monitor), event_type],
                    creationflags=subprocess.CREATE_NO_WINDOW
                )
                logger.info(f"Triggered pro_monitor for {event_type}")
        except Exception as e:
            logger.error(f"Failed to trigger capture: {e}")

    def process_security_event(self, event):
        """Process a Windows Security event"""
        try:
            event_id = event.EventID & 0xFFFF  # Mask to get actual event ID
            time_generated = event.TimeGenerated

            # Convert to datetime
            event_time = datetime(
                time_generated.year, time_generated.month, time_generated.day,
                time_generated.hour, time_generated.minute, time_generated.second
            )

            # Skip old events
            if event_time <= self.last_event_time:
                return

            self.last_event_time = event_time

            if event_id == 4624:
                # Successful logon
                logon_type = None
                try:
                    # Parse logon type from event data
                    if event.StringInserts and len(event.StringInserts) > 8:
                        logon_type = event.StringInserts[8]
                except:
                    pass

                # Logon type 2 = Interactive, 7 = Unlock
                if logon_type == '2':
                    logger.info("Detected: Interactive Login")
                    self.send_event('Login')
                elif logon_type == '7':
                    logger.info("Detected: Unlock")
                    self.send_event('Unlock')

            elif event_id == 4625:
                # Failed logon attempt
                logger.warning("Detected: Failed login attempt")
                self.failed_attempts.append(datetime.now())

                if self.check_intruder():
                    logger.warning("INTRUDER DETECTED!")
                    self.send_event('Intruder', {
                        'failed_attempts': len(self.failed_attempts),
                        'window_minutes': FAILED_ATTEMPT_WINDOW // 60
                    })
                    self.failed_attempts = []  # Reset after alert

            elif event_id == 4800:
                # Workstation locked
                logger.info("Detected: Workstation locked")
                self.send_event('Lock')

            elif event_id == 4801:
                # Workstation unlocked
                logger.info("Detected: Workstation unlocked")
                self.send_event('Unlock')

            elif event_id == 4802:
                # Screen saver started
                logger.info("Detected: Screen saver started")

            elif event_id == 4803:
                # Screen saver stopped
                logger.info("Detected: Screen saver stopped")
                self.send_event('Wake')

        except Exception as e:
            logger.error(f"Error processing event: {e}")

    def watch_events(self):
        """Watch Windows Security Event Log"""
        logger.info("Starting Windows Event Log watcher...")

        # Set initial time to now to avoid processing old events
        self.last_event_time = datetime.now()

        while True:
            try:
                # Open Security event log
                handle = win32evtlog.OpenEventLog(None, "Security")

                flags = win32evtlog.EVENTLOG_BACKWARDS_READ | win32evtlog.EVENTLOG_SEQUENTIAL_READ

                events = win32evtlog.ReadEventLog(handle, flags, 0)

                for event in events:
                    event_id = event.EventID & 0xFFFF
                    if event_id in [4624, 4625, 4800, 4801, 4802, 4803]:
                        self.process_security_event(event)

                win32evtlog.CloseEventLog(handle)

            except pywintypes.error as e:
                if e.winerror == 5:  # Access denied
                    logger.error("Access denied. Run as Administrator to read Security log.")
                else:
                    logger.error(f"Windows error: {e}")
            except Exception as e:
                logger.error(f"Error reading event log: {e}")

            # Poll every 2 seconds
            time.sleep(2)

    def watch_session_changes(self):
        """Alternative: Watch for session changes using WTS API"""
        logger.info("Starting session change watcher...")

        try:
            import ctypes
            from ctypes import wintypes

            # Session change notifications via message loop
            WTS_SESSION_LOCK = 0x7
            WTS_SESSION_UNLOCK = 0x8
            WTS_SESSION_LOGON = 0x5
            WTS_SESSION_LOGOFF = 0x6

            # For a service, we'd register with WTSRegisterSessionNotification
            # For now, use polling approach

        except Exception as e:
            logger.error(f"Session watcher error: {e}")

    def run(self):
        """Main run loop"""
        if not self.device_id:
            logger.error("No device configured. Please run the installer first.")
            return

        logger.info(f"Login Monitor PRO - Windows Edition")
        logger.info(f"Device ID: {self.device_id}")
        logger.info(f"Hostname: {self.get_hostname()}")
        logger.info(f"Username: {self.get_username()}")

        # Try event log watching (requires admin)
        # Falls back to session polling if needed
        try:
            self.watch_events()
        except Exception as e:
            logger.error(f"Event log watcher failed: {e}")
            logger.info("Falling back to session polling...")
            self.session_polling()

    def session_polling(self):
        """Fallback: Poll for session state changes"""
        logger.info("Using session polling mode...")

        try:
            import ctypes
            user32 = ctypes.windll.user32
        except:
            logger.error("Cannot load user32.dll")
            return

        last_locked = None

        while True:
            try:
                # Check if workstation is locked
                # This is a workaround - check if foreground window is lock screen
                hwnd = user32.GetForegroundWindow()

                # Simple check - if we can interact, probably not locked
                # For more reliable detection, we'd need a Windows service

                time.sleep(5)

            except Exception as e:
                logger.error(f"Polling error: {e}")
                time.sleep(5)


def main():
    watcher = WindowsEventWatcher()
    watcher.run()


if __name__ == '__main__':
    main()
