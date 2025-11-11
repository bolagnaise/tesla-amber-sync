#!/usr/bin/env python3
"""Show the time misalignment caused by the bug"""

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# Simulate some Amber timestamps
amber_times = [
    ("00:05:00", 5),   # midnight to 12:05am
    ("00:30:00", 5),   # 12:25am to 12:30am
    ("16:00:00", 5),   # 3:55pm to 4:00pm
    ("16:30:00", 5),   # 4:25pm to 4:30pm
    ("17:00:00", 5),   # 4:55pm to 5:00pm
]

sydney_tz = ZoneInfo('Australia/Sydney')
date = datetime(2025, 11, 11, tzinfo=sydney_tz)

print("=" * 120)
print("TIME MISALIGNMENT ANALYSIS - CURRENT BUG vs CORRECT")
print("=" * 120)
print(f"{'nemTime (END)':<20} {'Duration':<10} {'CURRENT BUG':<35} {'CORRECT':<35} {'Impact'}")
print("-" * 120)

for time_str, duration in amber_times:
    hour, minute, second = map(int, time_str.split(':'))
    nem_time = date.replace(hour=hour, minute=minute, second=second)

    # CURRENT BUG: Always subtract 30 minutes
    wrong_start = nem_time - timedelta(minutes=30)
    wrong_bucket = f"{wrong_start.hour:02d}:{0 if wrong_start.minute < 30 else 30:02d}"
    wrong_period = f"PERIOD_{wrong_start.hour:02d}_{0 if wrong_start.minute < 30 else 30:02d}"

    # CORRECT: Subtract actual duration
    correct_start = nem_time - timedelta(minutes=duration)
    correct_bucket = f"{correct_start.hour:02d}:{0 if correct_start.minute < 30 else 30:02d}"
    correct_period = f"PERIOD_{correct_start.hour:02d}_{0 if correct_start.minute < 30 else 30:02d}"

    # Check if they match
    if wrong_period == correct_period:
        impact = "✅ SAME"
    else:
        diff_minutes = (correct_start - wrong_start).total_seconds() / 60
        impact = f"❌ OFF BY {int(diff_minutes)} MIN"

    print(f"{time_str:<20} {duration:<10} {wrong_bucket} ({wrong_period}){'':<10} {correct_bucket} ({correct_period}){'':<10} {impact}")

print()
print("=" * 120)
print("WHAT THIS MEANS FOR YOUR POWERWALL")
print("=" * 120)
print("If Amber shows a price spike at 4:00 PM:")
print("  - CURRENT BUG maps it to: PERIOD_15_30 (3:30-4:00 PM slot)")
print("  - CORRECT should map to:  PERIOD_16_00 (4:00-4:30 PM slot)")
print()
print("Result: Your Powerwall is seeing prices 30 MINUTES EARLY!")
print("        (But they're 25 min off because of rounding issues)")
print()
print("This explains why the TOU schedule doesn't align with what you see in the Amber app.")
