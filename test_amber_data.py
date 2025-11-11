#!/usr/bin/env python3
"""Test actual Amber API data to understand timestamp handling"""

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

print(f"Site ID: {site_id}")
print()

# Get price forecast (48 hours worth)
response = requests.get(
    f"https://api.amber.com.au/v1/sites/{site_id}/prices",
    headers=headers,
    params={"next": 48}
)

forecast = response.json()

print(f"Total price points: {len(forecast)}")
print()

# Current time
sydney_tz = ZoneInfo('Australia/Sydney')
now = datetime.now(sydney_tz)
print(f"Current time (Sydney): {now}")
print(f"Current hour: {now.hour}:{now.minute:02d}")
print()

# Analyze first 20 general channel prices
print("=" * 100)
print("FIRST 20 GENERAL CHANNEL PRICE POINTS")
print("=" * 100)
print(f"{'#':<4} {'nemTime':<28} {'Duration':<10} {'START (calc)':<28} {'Bucket':<12} {'Type':<18}")
print("-" * 100)

general_prices = [p for p in forecast if p.get('channelType') == 'general']

for i, point in enumerate(general_prices[:20]):
    nem_time = point.get('nemTime', '')
    duration = point.get('duration', 0)
    interval_type = point.get('type', 'unknown')

    # Parse nemTime
    timestamp = datetime.fromisoformat(nem_time.replace('Z', '+00:00'))

    # Calculate interval start (nemTime is END, so subtract duration)
    interval_start = timestamp - timedelta(minutes=duration)

    # Round to 30-min bucket
    minute_bucket = 0 if interval_start.minute < 30 else 30
    bucket_str = f"{interval_start.hour:02d}:{minute_bucket:02d}"

    print(f"{i:<4} {nem_time:<28} {duration:<10} {str(interval_start):<28} {bucket_str:<12} {interval_type:<18}")

print()
print("=" * 100)
print("TIMESTAMP CONVERSION ANALYSIS")
print("=" * 100)

# Pick a specific example
example = general_prices[0]
nem_time = example.get('nemTime', '')
duration = example.get('duration', 0)

print(f"Example price point:")
print(f"  nemTime: {nem_time}")
print(f"  duration: {duration} minutes")
print(f"  type: {example.get('type')}")
print(f"  perKwh: {example.get('perKwh')} cents")
print()

timestamp = datetime.fromisoformat(nem_time.replace('Z', '+00:00'))
print(f"Parsed timestamp (END of interval): {timestamp}")
print()

# Current code subtracts 30 minutes (assumes 30-min intervals)
wrong_start = timestamp - timedelta(minutes=30)
print(f"CURRENT CODE (subtract 30min): {wrong_start}")
print(f"  Rounds to bucket: {wrong_start.hour:02d}:{0 if wrong_start.minute < 30 else 30:02d}")
print()

# Correct calculation (subtract actual duration)
correct_start = timestamp - timedelta(minutes=duration)
print(f"CORRECT (subtract {duration}min): {correct_start}")
print(f"  Rounds to bucket: {correct_start.hour:02d}:{0 if correct_start.minute < 30 else 30:02d}")
print()

print("=" * 100)
print("CONCLUSION")
print("=" * 100)
print(f"The code assumes Amber uses 30-minute intervals, but Amber actually uses")
print(f"{duration}-minute intervals. This causes misalignment!")
