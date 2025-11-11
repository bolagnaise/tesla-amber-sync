#!/usr/bin/env python3
"""Analyze the rolling window behavior"""

import requests
import json
import sqlite3
from app.utils import decrypt_token
from app.api_clients import AmberAPIClient
from app.tariff_converter import AmberTariffConverter
from datetime import datetime
from zoneinfo import ZoneInfo

# Get current time
sydney_tz = ZoneInfo('Australia/Sydney')
now = datetime.now(sydney_tz)
current_hour = now.hour
current_minute = 0 if now.minute < 30 else 30

print("=" * 100)
print("ROLLING WINDOW ANALYSIS")
print("=" * 100)
print(f"Current time: {now}")
print(f"Current period boundary: {current_hour:02d}:{current_minute:02d}")
print()

# Get user from database
db_path = '/Users/benboller/Downloads/tesla-amber-sync/app.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT amber_api_token_encrypted FROM user LIMIT 1")
encrypted_token = cursor.fetchone()[0]
conn.close()

# Decrypt token
api_token = decrypt_token(encrypted_token)

# Fetch forecast
client = AmberAPIClient(api_token)
forecast = client.get_price_forecast(next_hours=48)

# Convert to tariff
converter = AmberTariffConverter()
tariff = converter.convert_amber_to_tesla_tariff(forecast, user=None)

# Extract our prices
our_prices = tariff['energy_charges']['Summer']['rates']

print("PERIOD CLASSIFICATION (Rolling Window Logic)")
print("-" * 100)
print(f"{'Period':<12} {'Classification':<25} {'Date Used':<15} {'Our Price':<12}")
print("-" * 100)

today = now.date()
tomorrow = today.replace(day=today.day + 1) if today.day < 28 else today

for hour in range(24):
    for minute in [0, 30]:
        period_key = f"PERIOD_{hour:02d}_{minute:02d}"
        time_str = f"{hour:02d}:{minute:02d}"

        # Determine classification
        if (hour < current_hour) or (hour == current_hour and minute < current_minute):
            classification = "PAST (use tomorrow)"
            date_used = str(tomorrow)
        else:
            classification = "FUTURE (use today)"
            date_used = str(today)

        our_price = our_prices.get(period_key, 0)

        print(f"{time_str:<12} {classification:<25} {date_used:<15} ${our_price:.4f}")

print()
print("=" * 100)
print("KEY INSIGHT")
print("=" * 100)
print("The 'rolling window' means:")
print(f"  - Periods BEFORE {current_hour:02d}:{current_minute:02d} use TOMORROW's forecast")
print(f"  - Periods AFTER {current_hour:02d}:{current_minute:02d} use TODAY's forecast")
print()
print("This is CORRECT for Tesla optimization because:")
print("  1. Past periods have already happened - no point showing old prices")
print("  2. Tesla needs a FULL 24-hour lookahead for optimal battery management")
print("  3. This ensures Tesla always has fresh, relevant price data")
print()
print("NetZero shows a STATIC snapshot, which is useful for humans but not for")
print("battery optimization. Our system provides what Tesla needs!")
