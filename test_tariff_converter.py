#!/usr/bin/env python3
"""Test script for refactored tariff converter."""

import json
from datetime import datetime, timedelta, timezone
from app.tariff_converter import AmberTariffConverter

# Sample Amber forecast data representing a few time intervals
# Using realistic prices and times
sample_forecast = [
    {
        "type": "ActualInterval",
        "duration": 30,
        "startTime": "2025-11-12T06:30:00+11:00",
        "endTime": "2025-11-12T07:00:00+11:00",
        "nemTime": "2025-11-12T07:00:00+11:00",
        "perKwh": 0.15,
        "spotPerKwh": 0.10,
        "channelType": "general",
        "renewables": 60.5,
        "spikeStatus": "none",
        "tariffInformation": {
            "period": "offPeak",
            "season": "default",
            "demandCharges": []
        }
    },
    {
        "type": "ForecastInterval",
        "duration": 30,
        "startTime": "2025-11-12T17:00:00+11:00",
        "endTime": "2025-11-12T17:30:00+11:00",
        "nemTime": "2025-11-12T17:30:00+11:00",
        "perKwh": 0.35,
        "spotPerKwh": 0.28,
        "channelType": "general",
        "renewables": 35.2,
        "spikeStatus": "none",
        "tariffInformation": {
            "period": "peak",
            "season": "default",
            "demandCharges": []
        }
    },
    {
        "type": "ForecastInterval",
        "duration": 30,
        "startTime": "2025-11-12T17:30:00+11:00",
        "endTime": "2025-11-12T18:00:00+11:00",
        "nemTime": "2025-11-12T18:00:00+11:00",
        "perKwh": 0.42,
        "spotPerKwh": 0.35,
        "channelType": "general",
        "renewables": 28.7,
        "spikeStatus": "potential",
        "tariffInformation": {
            "period": "peak",
            "season": "default",
            "demandCharges": []
        }
    },
    {
        "type": "ForecastInterval",
        "duration": 30,
        "startTime": "2025-11-12T18:00:00+11:00",
        "endTime": "2025-11-12T18:30:00+11:00",
        "nemTime": "2025-11-12T18:30:00+11:00",
        "perKwh": 0.38,
        "spotPerKwh": 0.32,
        "channelType": "general",
        "renewables": 22.1,
        "spikeStatus": "none",
        "tariffInformation": {
            "period": "peak",
            "season": "default",
            "demandCharges": []
        }
    },
    # Feed-in data
    {
        "type": "ForecastInterval",
        "duration": 30,
        "startTime": "2025-11-12T17:30:00+11:00",
        "endTime": "2025-11-12T18:00:00+11:00",
        "nemTime": "2025-11-12T18:00:00+11:00",
        "perKwh": 0.05,
        "spotPerKwh": 0.03,
        "channelType": "feedIn",
        "renewables": 28.7,
        "spikeStatus": "none",
        "tariffInformation": {
            "period": "offPeak",
            "season": "default",
            "demandCharges": []
        }
    }
]

def test_tariff_converter():
    """Test the refactored tariff converter."""
    print("=" * 80)
    print("Testing Refactored Tariff Converter")
    print("=" * 80)

    # Convert Amber data to Tesla tariff
    converter = AmberTariffConverter()
    result = converter.convert_amber_to_tesla_tariff(
        forecast_data=sample_forecast,
        user=None
    )

    if not result:
        print("\n❌ ERROR: Tariff converter returned None!")
        return

    print("\n✅ Tariff conversion successful!\n")

    # Display key information
    print("Provider:", result.get("utility_id"))
    daily_charges = result.get("daily_charges", 0)
    if isinstance(daily_charges, list):
        print("Daily Charges:", daily_charges)
    else:
        print("Daily Charges: $%.4f" % daily_charges)

    # Don't print the full energy_charges as it's too verbose
    print("\nTariff structure created successfully")

    # Check specific periods to verify START time bucketing
    print("\n" + "=" * 80)
    print("Verification: Checking if START time bucketing works correctly")
    print("=" * 80)

    # With the START time approach:
    # - Amber 17:30-18:00 interval (nemTime=18:00, startTime=17:30)
    # - Should bucket as PERIOD_17_30
    # - Should have price of 0.42 (the perKwh for nemTime 18:00)

    energy_charges = result.get("energy_charges", {})
    seasons = energy_charges.get("seasons", [])

    if seasons:
        print("\nSeason:", seasons[0].get("season"))
        tou_periods = seasons[0].get("tou_periods", [])

        # Find PERIOD_17_30
        period_17_30 = next((p for p in tou_periods if p["tou_period_id"] == "PERIOD_17_30"), None)

        if period_17_30:
            print("\n✅ Found PERIOD_17_30:")
            print(f"   Start: {period_17_30['from_hour']}:{period_17_30['from_minute']:02d}")
            print(f"   End: {period_17_30['to_hour']}:{period_17_30['to_minute']:02d}")
            print(f"   Buy Rate: ${period_17_30['energy_rate']:.4f}/kWh")
            print(f"   Sell Rate: ${period_17_30.get('energy_rate_sellback', 0):.4f}/kWh")

            # Expected: 0.42 for buy (nemTime 18:00 price)
            # Expected: 0.05 for sell (nemTime 18:00 feedIn price)
            expected_buy = 0.42
            expected_sell = 0.05

            if abs(period_17_30['energy_rate'] - expected_buy) < 0.001:
                print(f"\n   ✅ Buy rate matches expected: ${expected_buy:.4f}/kWh")
            else:
                print(f"\n   ❌ Buy rate mismatch! Expected ${expected_buy:.4f}, got ${period_17_30['energy_rate']:.4f}")

            if abs(period_17_30.get('energy_rate_sellback', 0) - expected_sell) < 0.001:
                print(f"   ✅ Sell rate matches expected: ${expected_sell:.4f}/kWh")
            else:
                print(f"   ❌ Sell rate mismatch! Expected ${expected_sell:.4f}, got ${period_17_30.get('energy_rate_sellback', 0):.4f}")
        else:
            print("\n❌ ERROR: PERIOD_17_30 not found in tariff!")

    print("\n" + "=" * 80)
    print("Test Complete")
    print("=" * 80)

if __name__ == "__main__":
    test_tariff_converter()
