#!/usr/bin/env python3
"""Test if our current system has any missing slots"""

import sqlite3
from app.utils import decrypt_token
from app.api_clients import AmberAPIClient
from app.tariff_converter import AmberTariffConverter

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

print("=" * 80)
print("CHECKING FOR MISSING SLOTS IN TESLA TOU TARIFF")
print("=" * 80)

missing_slots = []
all_slots = []

# Tesla requires exactly 48 slots for 30-minute intervals
for hour in range(24):
    for minute in [0, 30]:
        period_key = f"PERIOD_{hour:02d}_{minute:02d}"
        all_slots.append(period_key)

        if period_key not in our_prices:
            missing_slots.append(period_key)

print(f"Total slots required: {len(all_slots)}")
print(f"Total slots filled: {len(our_prices)}")
print(f"Missing slots: {len(missing_slots)}")

if missing_slots:
    print("\n⚠️  MISSING SLOTS FOUND:")
    for slot in missing_slots:
        print(f"  - {slot}")
else:
    print("\n✅ All 48 slots are filled!")

# Check for any prices that are exactly 0 (might indicate fallback issues)
zero_price_slots = [k for k, v in our_prices.items() if v == 0]
if zero_price_slots:
    print(f"\n⚠️  {len(zero_price_slots)} slots have ZERO price (may need carry-forward):")
    for slot in zero_price_slots[:10]:  # Show first 10
        print(f"  - {slot}: ${our_prices[slot]:.4f}")
else:
    print("\n✅ No zero-price slots!")

# Show price range
prices = list(our_prices.values())
print(f"\nPrice range:")
print(f"  Min: ${min(prices):.4f}")
print(f"  Max: ${max(prices):.4f}")
print(f"  Avg: ${sum(prices)/len(prices):.4f}")
