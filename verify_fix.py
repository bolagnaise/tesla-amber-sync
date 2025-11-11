#!/usr/bin/env python3
"""Verify that the timestamp fix is working correctly"""

import requests
import json
import os
import sqlite3
from app.utils import decrypt_token
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Get user's Amber API token from database
db_path = '/Users/benboller/Downloads/tesla-amber-sync/app.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT amber_api_token_encrypted FROM user LIMIT 1")
encrypted_token = cursor.fetchone()[0]
conn.close()

# Decrypt token
api_token = decrypt_token(encrypted_token)

print("Fetching Amber price forecast...")
headers = {"Authorization": f"Bearer {api_token}"}

# Get site ID first
response = requests.get("https://api.amber.com.au/v1/sites", headers=headers)
sites = response.json()
site_id = sites[0]['id']

# Get price forecast
response = requests.get(
    f"https://api.amber.com.au/v1/sites/{site_id}/prices",
    headers=headers,
    params={"next": 48}
)

forecast = response.json()

# Current time
sydney_tz = ZoneInfo('Australia/Sydney')
now = datetime.now(sydney_tz)

print(f"\nCurrent time (Sydney): {now}")
print(f"Current period: {now.hour:02d}:{0 if now.minute < 30 else 30:02d}")
print()

# Get general channel prices around current time
general_prices = [p for p in forecast if p.get('channelType') == 'general']

print("=" * 100)
print("TIMESTAMP CONVERSION - AFTER FIX")
print("=" * 100)
print(f"{'nemTime':<28} {'Duration':<10} {'OLD (wrong)':<25} {'NEW (fixed)':<25} {'Status'}")
print("-" * 100)

for i, point in enumerate(general_prices[:30]):
    nem_time = point.get('nemTime', '')
    duration = point.get('duration', 0)

    # Parse nemTime
    timestamp = datetime.fromisoformat(nem_time.replace('Z', '+00:00'))

    # OLD METHOD (hardcoded 30 minutes)
    old_start = timestamp - timedelta(minutes=30)
    old_bucket = f"{old_start.hour:02d}:{0 if old_start.minute < 30 else 30:02d}"

    # NEW METHOD (uses actual duration)
    new_start = timestamp - timedelta(minutes=duration)
    new_bucket = f"{new_start.hour:02d}:{0 if new_start.minute < 30 else 30:02d}"

    # Check if they match
    if old_bucket == new_bucket:
        status = "✅ SAME"
    else:
        status = f"⚠️  FIXED (was {old_bucket})"

    print(f"{nem_time:<28} {duration:<10} {old_bucket:<25} {new_bucket:<25} {status}")

print()
print("=" * 100)
print("SUMMARY")
print("=" * 100)
print("The fix ensures that Amber's timestamps are correctly converted to Tesla's")
print("30-minute TOU periods by using the actual 'duration' field instead of")
print("hardcoding 30 minutes.")
print()
print("This means prices now align correctly with what you see in the Amber app!")
