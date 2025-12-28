#!/usr/bin/env python3
"""
Login Monitor PRO - Windows Edition
Pro Monitor - Captures photo, screenshot, and location on events
"""

import sys
import os
import json
import time
import logging
import subprocess
from datetime import datetime
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from supabase import create_client, Client
    import cv2
    from PIL import ImageGrab
    import requests
except ImportError:
    print("Installing dependencies...")
    subprocess.check_call([sys.executable, "-m", "pip", "install",
                          "supabase", "opencv-python", "pillow", "requests", "-q"])
    from supabase import create_client, Client
    import cv2
    from PIL import ImageGrab
    import requests

from config import (
    SUPABASE_URL, SUPABASE_ANON_KEY, CONFIG_FILE, LOG_DIR, CAPTURE_DIR
)

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOG_DIR / 'pro_monitor.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class ProMonitor:
    def __init__(self):
        self.supabase: Client = None
        self.device_id = None
        self.user_id = None
        self.load_config()
        self.init_supabase()

    def load_config(self):
        """Load configuration"""
        try:
            if CONFIG_FILE.exists():
                with open(CONFIG_FILE, 'r') as f:
                    config = json.load(f)
                    self.device_id = config.get('device_id')
                    self.user_id = config.get('user_id')
        except Exception as e:
            logger.error(f"Config error: {e}")

    def init_supabase(self):
        """Initialize Supabase"""
        try:
            self.supabase = create_client(SUPABASE_URL, SUPABASE_ANON_KEY)
        except Exception as e:
            logger.error(f"Supabase error: {e}")

    def capture_photo(self) -> str:
        """Capture photo from webcam"""
        try:
            cap = cv2.VideoCapture(0)
            if not cap.isOpened():
                logger.warning("No webcam available")
                return None

            time.sleep(0.5)  # Camera warmup
            ret, frame = cap.read()
            cap.release()

            if ret:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"event_photo_{timestamp}.jpg"
                filepath = CAPTURE_DIR / filename
                cv2.imwrite(str(filepath), frame)
                return str(filepath)
        except Exception as e:
            logger.error(f"Photo capture error: {e}")
        return None

    def capture_screenshot(self) -> str:
        """Capture screenshot"""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"event_screenshot_{timestamp}.png"
            filepath = CAPTURE_DIR / filename

            screenshot = ImageGrab.grab()
            screenshot.save(filepath, 'PNG')
            return str(filepath)
        except Exception as e:
            logger.error(f"Screenshot error: {e}")
        return None

    def get_location(self) -> dict:
        """Get location via IP geolocation"""
        try:
            response = requests.get('http://ip-api.com/json/', timeout=10)
            data = response.json()

            if data.get('status') == 'success':
                return {
                    'latitude': data.get('lat'),
                    'longitude': data.get('lon'),
                    'city': data.get('city'),
                    'region': data.get('regionName'),
                    'country': data.get('country'),
                    'ip': data.get('query'),
                }
        except Exception as e:
            logger.error(f"Location error: {e}")
        return None

    def upload_file(self, filepath: str, bucket: str) -> str:
        """Upload file to Supabase Storage"""
        try:
            filename = Path(filepath).name
            with open(filepath, 'rb') as f:
                data = f.read()

            path = f"{self.device_id}/{filename}"
            self.supabase.storage.from_(bucket).upload(path, data)
            url = self.supabase.storage.from_(bucket).get_public_url(path)
            return url
        except Exception as e:
            logger.error(f"Upload error: {e}")
        return None

    def update_event(self, event_type: str, photo_url: str = None,
                     screenshot_url: str = None, location: dict = None):
        """Update latest event with captured data"""
        try:
            # Get the most recent event of this type
            result = self.supabase.table('events').select('*').eq(
                'device_id', self.device_id
            ).eq('event_type', event_type).order(
                'timestamp', desc=True
            ).limit(1).execute()

            if result.data:
                event = result.data[0]
                update_data = {}

                if photo_url:
                    update_data['photo_url'] = photo_url
                if screenshot_url:
                    update_data['screenshot_url'] = screenshot_url
                if location:
                    update_data['location_lat'] = location.get('latitude')
                    update_data['location_lon'] = location.get('longitude')
                    update_data['location_city'] = location.get('city')

                if update_data:
                    self.supabase.table('events').update(update_data).eq(
                        'id', event['id']
                    ).execute()
                    logger.info(f"Updated event {event['id']}")
        except Exception as e:
            logger.error(f"Update event error: {e}")

    def process_event(self, event_type: str):
        """Process an event - capture and upload"""
        logger.info(f"Processing event: {event_type}")

        if not self.device_id:
            logger.error("No device configured")
            return

        photo_url = None
        screenshot_url = None
        location = None

        # Capture photo
        photo_path = self.capture_photo()
        if photo_path:
            photo_url = self.upload_file(photo_path, 'photos')
            logger.info(f"Photo uploaded: {photo_url}")

        # Capture screenshot (only for Intruder events)
        if event_type == 'Intruder':
            screenshot_path = self.capture_screenshot()
            if screenshot_path:
                screenshot_url = self.upload_file(screenshot_path, 'screenshots')
                logger.info(f"Screenshot uploaded: {screenshot_url}")

        # Get location
        location = self.get_location()
        if location:
            logger.info(f"Location: {location.get('city')}")

        # Update the event
        self.update_event(event_type, photo_url, screenshot_url, location)


def main():
    if len(sys.argv) < 2:
        print("Usage: pro_monitor.py <event_type>")
        print("Event types: Login, Unlock, Intruder, Wake")
        return

    event_type = sys.argv[1]
    monitor = ProMonitor()
    monitor.process_event(event_type)


if __name__ == '__main__':
    main()
