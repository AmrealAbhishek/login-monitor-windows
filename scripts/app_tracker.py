#!/usr/bin/env python3
"""
Login Monitor PRO - Windows Edition
App Tracker - Tracks running applications and foreground window
"""

import sys
import os
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path
from collections import defaultdict

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    import psutil
    import win32gui
    import win32process
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil", "pywin32", "-q"])
    import psutil
    import win32gui
    import win32process

from config import LOG_DIR

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'app_tracker.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AppTracker:
    def __init__(self):
        self.app_times = defaultdict(int)  # app_name -> seconds
        self.current_app = None
        self.last_update = time.time()

    def get_active_window_info(self) -> dict:
        """Get info about the currently active window"""
        try:
            hwnd = win32gui.GetForegroundWindow()
            if not hwnd:
                return None

            # Get window title
            window_title = win32gui.GetWindowText(hwnd)

            # Get process ID
            _, pid = win32process.GetWindowThreadProcessId(hwnd)

            # Get process name
            try:
                process = psutil.Process(pid)
                process_name = process.name()
                exe_path = process.exe()
            except:
                process_name = "Unknown"
                exe_path = ""

            return {
                'hwnd': hwnd,
                'title': window_title,
                'pid': pid,
                'process': process_name,
                'exe': exe_path,
            }
        except Exception as e:
            logger.error(f"Error getting window info: {e}")
            return None

    def get_running_apps(self) -> list:
        """Get list of running applications with visible windows"""
        apps = []
        seen = set()

        def enum_callback(hwnd, _):
            if win32gui.IsWindowVisible(hwnd) and win32gui.GetWindowText(hwnd):
                try:
                    _, pid = win32process.GetWindowThreadProcessId(hwnd)
                    if pid not in seen:
                        seen.add(pid)
                        try:
                            proc = psutil.Process(pid)
                            apps.append({
                                'name': proc.name(),
                                'pid': pid,
                                'title': win32gui.GetWindowText(hwnd),
                                'memory': proc.memory_info().rss // (1024 * 1024),  # MB
                                'cpu': proc.cpu_percent(),
                            })
                        except:
                            pass
                except:
                    pass
            return True

        win32gui.EnumWindows(enum_callback, None)
        return sorted(apps, key=lambda x: x['memory'], reverse=True)

    def update_tracking(self):
        """Update time tracking for current app"""
        now = time.time()
        elapsed = now - self.last_update

        if self.current_app:
            self.app_times[self.current_app] += int(elapsed)

        active = self.get_active_window_info()
        if active:
            self.current_app = active['process']
        else:
            self.current_app = None

        self.last_update = now

    def get_app_usage_stats(self) -> dict:
        """Get app usage statistics"""
        total = sum(self.app_times.values())
        if total == 0:
            total = 1

        stats = []
        for app, seconds in sorted(self.app_times.items(), key=lambda x: x[1], reverse=True):
            stats.append({
                'app': app,
                'seconds': seconds,
                'minutes': seconds // 60,
                'percent': round(seconds / total * 100, 1),
            })

        return {
            'total_seconds': total,
            'apps': stats[:20],  # Top 20
        }

    def save_stats(self, filepath: Path):
        """Save stats to file"""
        stats = self.get_app_usage_stats()
        stats['timestamp'] = datetime.now().isoformat()

        with open(filepath, 'w') as f:
            json.dump(stats, f, indent=2)

    def run(self, interval: int = 5):
        """Main tracking loop"""
        logger.info("Starting app tracker...")

        stats_file = LOG_DIR / 'app_usage.json'

        while True:
            try:
                self.update_tracking()

                # Save stats every minute
                if int(time.time()) % 60 == 0:
                    self.save_stats(stats_file)

            except Exception as e:
                logger.error(f"Tracking error: {e}")

            time.sleep(interval)


def main():
    tracker = AppTracker()

    if len(sys.argv) > 1 and sys.argv[1] == 'list':
        # Just list running apps
        apps = tracker.get_running_apps()
        for app in apps:
            print(f"{app['name']}: {app['memory']}MB - {app['title'][:50]}")
    else:
        # Run continuous tracking
        tracker.run()


if __name__ == '__main__':
    main()
