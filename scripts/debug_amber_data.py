#!/usr/bin/env python3
"""
Debug script to fetch raw Amber API data for comparison with Netzero pricing.
This script bypasses Flask authentication and directly queries the Amber API.
"""

import sys
import json
from datetime import datetime
from app import create_app, db
from app.models import User
from app.api_clients import get_amber_client

def main():
    # Create Flask app context
    app = create_app()

    with app.app_context():
        # Get the first user (single-user mode)
        user = User.query.first()

        if not user:
            print("ERROR: No user found in database")
            return 1

        print(f"Fetching Amber data for user: {user.email}")

        # Get Amber client
        amber_client = get_amber_client(user)
        if not amber_client:
            print("ERROR: No Amber API client configured")
            return 1

        # Fetch 48 hours of forecast data
        print("\nFetching 48-hour price forecast from Amber API...")
        forecast = amber_client.get_price_forecast(next_hours=48)

        if not forecast:
            print("ERROR: Failed to fetch price forecast")
            return 1

        print(f"SUCCESS: Fetched {len(forecast)} intervals\n")

        # Organize data by channel type
        general_intervals = [i for i in forecast if i.get('channelType') == 'general']
        feedin_intervals = [i for i in forecast if i.get('channelType') == 'feedIn']

        print("=" * 80)
        print(f"SUMMARY")
        print("=" * 80)
        print(f"Total intervals: {len(forecast)}")
        print(f"General (buy) intervals: {len(general_intervals)}")
        print(f"Feed-in (sell) intervals: {len(feedin_intervals)}")
        print(f"Fetch time: {datetime.utcnow().isoformat()}")

        # Show available fields from first interval
        if forecast:
            print(f"\nAvailable fields: {', '.join(forecast[0].keys())}")

        # Show detailed data for first few intervals of each type
        print("\n" + "=" * 80)
        print(f"GENERAL (BUY) PRICE SAMPLES - First 5 intervals")
        print("=" * 80)
        for i, interval in enumerate(general_intervals[:5]):
            print(f"\n--- Interval {i+1} ---")
            print(f"Time: {interval.get('startTime')} to {interval.get('endTime')}")
            print(f"  perKwh:            ${interval.get('perKwh', 0):.4f}")
            print(f"  spotPerKwh:        ${interval.get('spotPerKwh', 0):.4f}")
            print(f"  wholesaleKWHPrice: ${interval.get('wholesaleKWHPrice', 0):.4f}")
            print(f"  networkKWHPrice:   ${interval.get('networkKWHPrice', 0):.4f}")
            print(f"  marketKWHPrice:    ${interval.get('marketKWHPrice', 0):.4f}")
            print(f"  greenKWHPrice:     ${interval.get('greenKWHPrice', 0):.4f}")
            print(f"  lossFactor:        {interval.get('lossFactor', 0):.4f}")
            print(f"  descriptor:        {interval.get('descriptor')}")
            print(f"  spikeStatus:       {interval.get('spikeStatus')}")
            print(f"  forecast:          {interval.get('forecast')}")

        print("\n" + "=" * 80)
        print(f"FEED-IN (SELL) PRICE SAMPLES - First 5 intervals")
        print("=" * 80)
        for i, interval in enumerate(feedin_intervals[:5]):
            print(f"\n--- Interval {i+1} ---")
            print(f"Time: {interval.get('startTime')} to {interval.get('endTime')}")
            print(f"  perKwh:            ${interval.get('perKwh', 0):.4f}")
            print(f"  spotPerKwh:        ${interval.get('spotPerKwh', 0):.4f}")
            print(f"  wholesaleKWHPrice: ${interval.get('wholesaleKWHPrice', 0):.4f}")
            print(f"  networkKWHPrice:   ${interval.get('networkKWHPrice', 0):.4f}")
            print(f"  marketKWHPrice:    ${interval.get('marketKWHPrice', 0):.4f}")
            print(f"  greenKWHPrice:     ${interval.get('greenKWHPrice', 0):.4f}")
            print(f"  lossFactor:        {interval.get('lossFactor', 0):.4f}")
            print(f"  descriptor:        {interval.get('descriptor')}")
            print(f"  spikeStatus:       {interval.get('spikeStatus')}")
            print(f"  forecast:          {interval.get('forecast')}")

        # Save full data to JSON file for detailed analysis
        output_file = 'amber_raw_data.json'
        output_data = {
            'fetch_time': datetime.utcnow().isoformat(),
            'total_intervals': len(forecast),
            'general_count': len(general_intervals),
            'feedin_count': len(feedin_intervals),
            'general_intervals': general_intervals,
            'feedin_intervals': feedin_intervals
        }

        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)

        print(f"\n" + "=" * 80)
        print(f"Full data saved to: {output_file}")
        print("=" * 80)

        return 0

if __name__ == '__main__':
    sys.exit(main())
