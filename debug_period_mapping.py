#!/usr/bin/env python3
"""Debug period mapping to understand Amber's time labels"""

import sqlite3
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from app.utils import decrypt_token
from app.api_clients import AmberAPIClient
from collections import defaultdict

# Get user from database
db_path = 'app.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT amber_api_token_encrypted FROM user LIMIT 1")
encrypted_token = cursor.fetchone()[0]
conn.close()

# Decrypt token
api_token = decrypt_token(encrypted_token)

# Fetch forecast
print("Fetching Amber forecast data...")
client = AmberAPIClient(api_token)
forecast = client.get_price_forecast(next_hours=48)

# Filter for feedIn (solar export)
feedin_data = [p for p in forecast if p.get('channelType') == 'feedIn']

print(f"\n{'='*120}")
print("AMBER FEED-IN (SOLAR EXPORT) PRICE MAPPING")
print(f"{'='*120}\n")

# Group by 30-minute periods using BOTH conventions
brisbane_tz = ZoneInfo('Australia/Brisbane')
now = datetime.now(brisbane_tz)

# Method 1: Our current method (START time convention)
period_data_start = defaultdict(list)
# Method 2: END time convention (what Amber might use)
period_data_end = defaultdict(list)

for point in feedin_data:
    nem_time = point.get('nemTime', '')
    duration = point.get('duration', 30)
    timestamp = datetime.fromisoformat(nem_time.replace('Z', '+00:00'))

    # Get price
    advanced_price = point.get('advancedPrice', {})
    if isinstance(advanced_price, dict):
        price_cents = advanced_price.get('high', point.get('perKwh', 0))
    else:
        price_cents = point.get('perKwh', 0)

    # Amber convention: negative = you get paid
    # Tesla convention: positive = you get paid
    # So negate for Tesla
    price_tesla_cents = -price_cents

    # Method 1: START time (our current method)
    interval_start = timestamp - timedelta(minutes=duration)
    minute_bucket = 0 if interval_start.minute < 30 else 30
    hour = interval_start.hour
    date_str = interval_start.date().isoformat()

    period_key_start = f"{date_str} {hour:02d}:{minute_bucket:02d}"
    period_data_start[period_key_start].append({
        'nemTime': nem_time,
        'duration': duration,
        'interval_start': interval_start.strftime('%H:%M:%S'),
        'price_tesla': price_tesla_cents,
    })

    # Method 2: END time (round nemTime itself)
    minute_bucket_end = 0 if timestamp.minute < 30 else 30
    hour_end = timestamp.hour
    date_str_end = timestamp.date().isoformat()

    period_key_end = f"{date_str_end} {hour_end:02d}:{minute_bucket_end:02d}"
    period_data_end[period_key_end].append({
        'nemTime': nem_time,
        'duration': duration,
        'interval_start': interval_start.strftime('%H:%M:%S'),
        'price_tesla': price_tesla_cents,
    })

# Show comparison for key periods around 17:30-18:30
print(f"Current time: {now}")
print(f"\n{'-'*120}\n")

for time_label in ['17:00', '17:30', '18:00', '18:30']:
    print(f"\n{'='*120}")
    print(f"TIME LABEL: {time_label}")
    print(f"{'='*120}\n")

    today = now.date().isoformat()

    # Method 1: START time convention (our current method)
    period_key_start = f"{today} {time_label}"
    if period_key_start in period_data_start:
        intervals = period_data_start[period_key_start]
        avg_start = sum(i['price_tesla'] for i in intervals) / len(intervals)
        print(f"METHOD 1 (START TIME) - Period {time_label}-{(datetime.strptime(time_label, '%H:%M') + timedelta(minutes=30)).strftime('%H:%M')}:")
        print(f"  Intervals included: {len(intervals)}")
        for i in sorted(intervals, key=lambda x: x['interval_start']):
            print(f"    {i['nemTime']:<30} interval {i['interval_start']}-{(datetime.strptime(i['interval_start'], '%H:%M:%S') + timedelta(minutes=i['duration'])).strftime('%H:%M')}: {i['price_tesla']:+.2f}¢")
        print(f"  → 30-min AVERAGE: {avg_start:+.2f}¢")

    print()

    # Method 2: END time convention (what Amber might use)
    period_key_end = f"{today} {time_label}"
    if period_key_end in period_data_end:
        intervals = period_data_end[period_key_end]
        avg_end = sum(i['price_tesla'] for i in intervals) / len(intervals)
        start_time = (datetime.strptime(time_label, '%H:%M') - timedelta(minutes=30)).strftime('%H:%M')
        print(f"METHOD 2 (END TIME) - Period {start_time}-{time_label}:")
        print(f"  Intervals included: {len(intervals)}")
        for i in sorted(intervals, key=lambda x: x['interval_start']):
            print(f"    {i['nemTime']:<30} interval {i['interval_start']}-{(datetime.strptime(i['interval_start'], '%H:%M:%S') + timedelta(minutes=i['duration'])).strftime('%H:%M')}: {i['price_tesla']:+.2f}¢")
        print(f"  → 30-min AVERAGE: {avg_end:+.2f}¢")

print(f"\n{'='*120}")
print("KEY QUESTION")
print(f"{'='*120}")
print("\nWhich method matches what you see in the Amber app?")
print("If METHOD 2 matches Amber, we have a period labeling mismatch!")
print("\nExpected from Amber app screenshot:")
print("  17:30 forecast: -1¢ (negative)")
print("  18:00 forecast: +13¢ (positive)")
