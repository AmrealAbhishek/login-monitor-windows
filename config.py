"""
Login Monitor PRO - Windows Edition
Configuration file
"""

import os
from pathlib import Path

# Supabase Configuration (same as macOS version)
SUPABASE_URL = "https://lrtgcyqngspjstgxhdub.supabase.co"
SUPABASE_ANON_KEY = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpc3MiOiJzdXBhYmFzZSIsInJlZiI6ImxydGdjeXFuZ3NwanN0Z3hoZHViIiwicm9sZSI6ImFub24iLCJpYXQiOjE3MzUxMDcwNjAsImV4cCI6MjA1MDY4MzA2MH0.m9M0QFGE8GxTvxpHC75RfmkRJHvo7bAB1xbnWvdykqc"

# Config directory
CONFIG_DIR = Path(os.environ.get('APPDATA', os.path.expanduser('~'))) / 'LoginMonitorPRO'
CONFIG_FILE = CONFIG_DIR / 'config.json'
LOG_DIR = CONFIG_DIR / 'logs'
CAPTURE_DIR = CONFIG_DIR / 'captures'
AUDIO_DIR = CONFIG_DIR / 'audio'

# Ensure directories exist
for d in [CONFIG_DIR, LOG_DIR, CAPTURE_DIR, AUDIO_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# Intruder detection settings
MAX_FAILED_ATTEMPTS = 3
FAILED_ATTEMPT_WINDOW = 300  # 5 minutes in seconds
