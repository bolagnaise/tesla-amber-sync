#!/usr/bin/env python3
"""Compare our TOU schedule with NetZero data"""

import requests
import json
import sqlite3
from app.utils import decrypt_token
from app.api_clients import AmberAPIClient
from app.tariff_converter import AmberTariffConverter

# NetZero data (from gist)
netzero_buy = {
    "00:00": 0.2539, "00:30": 0.2496, "01:00": 0.2482, "01:30": 0.2471,
    "02:00": 0.2432, "02:30": 0.2403, "03:00": 0.2393, "03:30": 0.2396,
    "04:00": 0.2406, "04:30": 0.2401, "05:00": 0.2406, "05:30": 0.2411,
    "06:00": 0.2463, "06:30": 0.2490, "07:00": 0.2259, "07:30": 0.1798,
    "08:00": 0.1495, "08:30": 0.1385, "09:00": 0.1325, "09:30": 0.1289,
    "10:00": 0.0579, "10:30": 0.0520, "11:00": 0.0466, "11:30": 0.0431,
    "12:00": 0.0417, "12:30": 0.0411, "13:00": 0.0405, "13:30": 0.0395,
    "14:00": 0.1059, "14:30": 0.1053, "15:00": 0.1059, "15:30": 0.1104,
    "16:00": 0.1184, "16:30": 0.1242, "17:00": 0.1300, "17:30": 0.1398,
    "18:00": 0.1592, "18:30": 0.1986, "19:00": 0.2501, "19:30": 0.2769,
    "20:00": 0.2811, "20:30": 0.2811, "21:00": 0.2765, "21:30": 0.2711,
    "22:00": 0.2689, "22:30": 0.2664, "23:00": 0.2648, "23:30": 0.2605,
}

# Get user from database
db_path = '/Users/benboller/Downloads/tesla-amber-sync/app.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()
cursor.execute("SELECT amber_api_token_encrypted FROM user LIMIT 1")
encrypted_token = cursor.fetchone()[0]
conn.close()

# Decrypt token
api_token = decrypt_token(encrypted_token)

print("Fetching Amber forecast...")
client = AmberAPIClient(api_token)
forecast = client.get_price_forecast(next_hours=48)

print(f"Got {len(forecast)} forecast points")

# Convert to tariff
converter = AmberTariffConverter()
tariff = converter.convert_amber_to_tesla_tariff(forecast, user=None)

# Extract our prices
our_prices = tariff['energy_charges']['Summer']['rates']

print("\n" + "=" * 120)
print("COMPARISON: OUR SYSTEM vs NETZERO")
print("=" * 120)
print(f"{'Period':<12} {'Our Price':<15} {'NetZero Price':<15} {'Difference':<15} {'% Diff':<10} {'Status'}")
print("-" * 120)

total_diff = 0
count = 0
max_diff = 0
max_diff_period = ""

for hour in range(24):
    for minute in [0, 30]:
        period_key = f"PERIOD_{hour:02d}_{minute:02d}"
        time_key = f"{hour:02d}:{minute:02d}"

        our_price = our_prices.get(period_key, 0)
        netzero_price = netzero_buy.get(time_key, 0)

        diff = our_price - netzero_price
        pct_diff = (diff / netzero_price * 100) if netzero_price > 0 else 0

        total_diff += abs(diff)
        count += 1

        if abs(diff) > max_diff:
            max_diff = abs(diff)
            max_diff_period = time_key

        # Status emoji
        if abs(diff) < 0.0001:
            status = "✅ EXACT"
        elif abs(pct_diff) < 1:
            status = "✅ CLOSE"
        elif abs(pct_diff) < 5:
            status = "⚠️  SMALL"
        else:
            status = "❌ DIFF"

        print(f"{time_key:<12} ${our_price:<14.4f} ${netzero_price:<14.4f} ${diff:+14.4f} {pct_diff:+9.2f}% {status}")

avg_diff = total_diff / count if count > 0 else 0

print()
print("=" * 120)
print("SUMMARY")
print("=" * 120)
print(f"Total periods compared: {count}")
print(f"Average absolute difference: ${avg_diff:.4f}")
print(f"Maximum difference: ${max_diff:.4f} at {max_diff_period}")
print()
print("Note: Small differences (<1%) are normal due to:")
print("  - Rounding when averaging 5-minute intervals to 30-minute periods")
print("  - Timing differences (NetZero data retrieved 15 mins ago)")
print("  - Different forecast type selections (predicted/low/high)")
