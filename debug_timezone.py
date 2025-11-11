#!/usr/bin/env python3
"""Debug timezone handling in tariff conversion"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Current time
sydney_tz = ZoneInfo('Australia/Sydney')
now = datetime.now(sydney_tz)

print("=" * 80)
print("CURRENT TIME ANALYSIS")
print("=" * 80)
print(f"System time (Sydney): {now}")
print(f"Current hour: {now.hour}")
print(f"Current minute: {now.minute}")
print(f"Current 30-min bucket: {0 if now.minute < 30 else 30}")
print()

# Example Amber nemTime from logs
nemTime_example = "2025-11-11T15:55:00+10:00"
print("=" * 80)
print("AMBER API TIMESTAMP ANALYSIS")
print("=" * 80)
print(f"Example nemTime from Amber API: {nemTime_example}")
print(f"This represents the END of the interval")
print()

# Parse it
timestamp = datetime.fromisoformat(nemTime_example.replace('Z', '+00:00'))
print(f"Parsed timestamp: {timestamp}")
print(f"Timestamp timezone: {timestamp.tzinfo}")
print()

# Convert END time to START time (subtract 30 minutes)
interval_start = timestamp - timedelta(minutes=30)
print(f"Interval START time (after -30min): {interval_start}")
print(f"START hour: {interval_start.hour}")
print(f"START minute: {interval_start.minute}")
print()

# Round to 30-minute bucket
minute_bucket = 0 if interval_start.minute < 30 else 30
hour_bucket = interval_start.hour

print(f"Rounded to 30-min bucket: {hour_bucket:02d}:{minute_bucket:02d}")
print(f"This maps to period: PERIOD_{hour_bucket:02d}_{minute_bucket:02d}")
print()

# Convert to date for lookup
interval_start_local = interval_start.astimezone(sydney_tz)
date_str = interval_start_local.date().isoformat()
print(f"Date (in Sydney timezone): {date_str}")
print(f"Lookup key would be: ({date_str}, {hour_bucket}, {minute_bucket})")
print()

print("=" * 80)
print("ROLLING WINDOW LOGIC TEST")
print("=" * 80)
today = now.date()
tomorrow = today + timedelta(days=1)
current_hour = now.hour
current_minute = 0 if now.minute < 30 else 30

print(f"Today: {today}")
print(f"Tomorrow: {tomorrow}")
print(f"Current period: {current_hour:02d}:{current_minute:02d}")
print()

# Test a few periods
test_periods = [
    (15, 0),   # 3:00 PM
    (15, 30),  # 3:30 PM
    (16, 0),   # 4:00 PM
    (16, 30),  # 4:30 PM
    (17, 0),   # 5:00 PM
    (17, 30),  # 5:30 PM
    (18, 0),   # 6:00 PM
]

for hour, minute in test_periods:
    period_key = f"PERIOD_{hour:02d}_{minute:02d}"

    # Check if past or future
    if (hour < current_hour) or (hour == current_hour and minute < current_minute):
        date_to_use = tomorrow
        status = "PAST (use tomorrow)"
    else:
        date_to_use = today
        status = "FUTURE (use today)"

    print(f"{period_key}: {status} -> date={date_to_use}")

print()
print("=" * 80)
print("WHAT NEMTIME REPRESENTS")
print("=" * 80)
print("nemTime: 2025-11-11T15:55:00+10:00")
print("  = 3:55 PM AEDT (INTERVAL END)")
print("  = Price for interval 3:25 PM - 3:55 PM")
print("  = Should map to PERIOD_15_30 (3:30-4:00 PM slot)")
print()
print("NOTE: Amber uses 5-minute intervals, but we need 30-minute")
print("      periods for Tesla. We average multiple 5-min prices.")
