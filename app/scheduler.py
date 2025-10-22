# app/scheduler.py
"""Time-of-Use scheduling based on Amber Electric price forecasts"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Optional

logger = logging.getLogger(__name__)


class TOUScheduler:
    """Creates optimal charge/discharge schedules based on electricity price forecasts"""

    def __init__(self, battery_capacity_kwh=13.5, min_soc=20, max_soc=100):
        """
        Initialize the TOU scheduler

        Args:
            battery_capacity_kwh: Total battery capacity in kWh (default: 13.5 for Powerwall 2)
            min_soc: Minimum state of charge percentage (default: 20%)
            max_soc: Maximum state of charge percentage (default: 100%)
        """
        self.battery_capacity_kwh = battery_capacity_kwh
        self.min_soc = min_soc
        self.max_soc = max_soc
        logger.info(f"TOUScheduler initialized: {battery_capacity_kwh}kWh, SOC range {min_soc}-{max_soc}%")

    def analyze_forecast(self, forecast_data: List[Dict]) -> Dict:
        """
        Analyze Amber price forecast to determine optimal charge/discharge windows

        Args:
            forecast_data: List of price forecast data points from Amber API

        Returns:
            Dict containing charge windows, discharge windows, and statistics
        """
        if not forecast_data:
            logger.warning("No forecast data provided")
            return {
                'charge_windows': [],
                'discharge_windows': [],
                'stats': {}
            }

        # Separate general (buy) and feedIn (sell) prices
        general_prices = []
        feedin_prices = []

        for point in forecast_data:
            timestamp = datetime.fromisoformat(point.get('nemTime', '').replace('Z', '+00:00'))
            channel_type = point.get('channelType', '')
            per_kwh = point.get('perKwh', 0)

            if channel_type == 'general':
                general_prices.append({
                    'timestamp': timestamp,
                    'price': per_kwh,
                    'spike_status': point.get('spikeStatus', 'none')
                })
            elif channel_type == 'feedIn':
                feedin_prices.append({
                    'timestamp': timestamp,
                    'price': per_kwh  # Note: This is typically negative (you get paid)
                })

        logger.info(f"Analyzed {len(general_prices)} general and {len(feedin_prices)} feed-in price points")

        # Find optimal windows
        charge_windows = self._find_charge_windows(general_prices)
        discharge_windows = self._find_discharge_windows(general_prices, feedin_prices)

        # Calculate statistics
        stats = self._calculate_stats(general_prices, feedin_prices, charge_windows, discharge_windows)

        return {
            'charge_windows': charge_windows,
            'discharge_windows': discharge_windows,
            'stats': stats,
            'general_prices': general_prices,
            'feedin_prices': feedin_prices
        }

    def _find_charge_windows(self, general_prices: List[Dict], num_windows=3) -> List[Dict]:
        """Find the cheapest time windows to charge the battery"""
        if not general_prices:
            return []

        # Sort by price (ascending) to find cheapest periods
        sorted_prices = sorted(general_prices, key=lambda x: x['price'])

        # Take the cheapest periods, but group consecutive periods
        charge_windows = []
        selected_times = sorted_prices[:min(num_windows * 2, len(sorted_prices))]

        # Group consecutive time periods
        current_window = None
        for price_point in sorted(selected_times, key=lambda x: x['timestamp']):
            if current_window is None:
                current_window = {
                    'start': price_point['timestamp'],
                    'end': price_point['timestamp'] + timedelta(minutes=30),
                    'avg_price': price_point['price'],
                    'min_price': price_point['price'],
                    'action': 'charge'
                }
            elif (price_point['timestamp'] - current_window['end']).total_seconds() <= 1800:  # 30 min gap
                # Extend current window
                current_window['end'] = price_point['timestamp'] + timedelta(minutes=30)
                current_window['avg_price'] = (current_window['avg_price'] + price_point['price']) / 2
                current_window['min_price'] = min(current_window['min_price'], price_point['price'])
            else:
                # Start new window
                charge_windows.append(current_window)
                current_window = {
                    'start': price_point['timestamp'],
                    'end': price_point['timestamp'] + timedelta(minutes=30),
                    'avg_price': price_point['price'],
                    'min_price': price_point['price'],
                    'action': 'charge'
                }

        if current_window:
            charge_windows.append(current_window)

        logger.info(f"Found {len(charge_windows)} charge windows")
        return charge_windows[:num_windows]

    def _find_discharge_windows(self, general_prices: List[Dict], feedin_prices: List[Dict],
                                 num_windows=3) -> List[Dict]:
        """Find the best time windows to discharge (sell back to grid)"""
        if not general_prices or not feedin_prices:
            return []

        # Calculate the spread (general - feedin) to find best export times
        spreads = []
        for gen in general_prices:
            # Find corresponding feed-in price
            feedin = next((f for f in feedin_prices
                          if abs((f['timestamp'] - gen['timestamp']).total_seconds()) < 300), None)
            if feedin:
                # Higher general price + better (less negative) feed-in = good time to discharge
                spread = gen['price'] - abs(feedin['price'])  # feedin is typically negative
                spreads.append({
                    'timestamp': gen['timestamp'],
                    'general_price': gen['price'],
                    'feedin_price': feedin['price'],
                    'spread': spread,
                    'spike_status': gen['spike_status']
                })

        # Sort by spread (descending) - best times to sell
        sorted_spreads = sorted(spreads, key=lambda x: x['general_price'], reverse=True)

        # Take the most expensive periods
        discharge_windows = []
        selected_times = sorted_spreads[:min(num_windows * 2, len(sorted_spreads))]

        # Group consecutive time periods
        current_window = None
        for price_point in sorted(selected_times, key=lambda x: x['timestamp']):
            if current_window is None:
                current_window = {
                    'start': price_point['timestamp'],
                    'end': price_point['timestamp'] + timedelta(minutes=30),
                    'avg_price': price_point['general_price'],
                    'max_price': price_point['general_price'],
                    'action': 'discharge',
                    'spike': price_point['spike_status'] != 'none'
                }
            elif (price_point['timestamp'] - current_window['end']).total_seconds() <= 1800:
                # Extend current window
                current_window['end'] = price_point['timestamp'] + timedelta(minutes=30)
                current_window['avg_price'] = (current_window['avg_price'] + price_point['general_price']) / 2
                current_window['max_price'] = max(current_window['max_price'], price_point['general_price'])
                if price_point['spike_status'] != 'none':
                    current_window['spike'] = True
            else:
                discharge_windows.append(current_window)
                current_window = {
                    'start': price_point['timestamp'],
                    'end': price_point['timestamp'] + timedelta(minutes=30),
                    'avg_price': price_point['general_price'],
                    'max_price': price_point['general_price'],
                    'action': 'discharge',
                    'spike': price_point['spike_status'] != 'none'
                }

        if current_window:
            discharge_windows.append(current_window)

        logger.info(f"Found {len(discharge_windows)} discharge windows")
        return discharge_windows[:num_windows]

    def _calculate_stats(self, general_prices: List[Dict], feedin_prices: List[Dict],
                        charge_windows: List[Dict], discharge_windows: List[Dict]) -> Dict:
        """Calculate statistics about the forecast and recommended actions"""
        if not general_prices:
            return {}

        general_values = [p['price'] for p in general_prices]
        feedin_values = [p['price'] for p in feedin_prices] if feedin_prices else []

        stats = {
            'general': {
                'min': min(general_values) if general_values else 0,
                'max': max(general_values) if general_values else 0,
                'avg': sum(general_values) / len(general_values) if general_values else 0,
            },
            'feedin': {
                'min': min(feedin_values) if feedin_values else 0,
                'max': max(feedin_values) if feedin_values else 0,
                'avg': sum(feedin_values) / len(feedin_values) if feedin_values else 0,
            },
            'spike_periods': len([p for p in general_prices if p.get('spike_status') != 'none']),
            'charge_windows_count': len(charge_windows),
            'discharge_windows_count': len(discharge_windows),
        }

        # Calculate potential savings
        if charge_windows and discharge_windows:
            avg_charge_price = sum(w['avg_price'] for w in charge_windows) / len(charge_windows)
            avg_discharge_price = sum(w['avg_price'] for w in discharge_windows) / len(discharge_windows)
            stats['potential_arbitrage'] = avg_discharge_price - avg_charge_price
            stats['estimated_daily_savings'] = stats['potential_arbitrage'] * (self.battery_capacity_kwh * 0.8) / 100  # Rough estimate

        return stats

    def generate_schedule_summary(self, analysis: Dict) -> str:
        """Generate a human-readable summary of the recommended schedule"""
        lines = []
        lines.append("=== TOU Schedule Recommendation ===\n")

        stats = analysis.get('stats', {})
        if stats:
            lines.append(f"Price Range: {stats['general']['min']:.1f}¢ - {stats['general']['max']:.1f}¢ per kWh")
            lines.append(f"Average Price: {stats['general']['avg']:.1f}¢ per kWh")
            if stats.get('spike_periods', 0) > 0:
                lines.append(f"⚠️  {stats['spike_periods']} price spike periods detected")
            if 'potential_arbitrage' in stats:
                lines.append(f"\n💰 Potential arbitrage: {stats['potential_arbitrage']:.1f}¢/kWh")
                lines.append(f"💵 Estimated daily savings: ${stats.get('estimated_daily_savings', 0):.2f}")
            lines.append("")

        charge_windows = analysis.get('charge_windows', [])
        if charge_windows:
            lines.append(f"🔋 CHARGE WINDOWS ({len(charge_windows)}):")
            for i, window in enumerate(charge_windows, 1):
                duration = (window['end'] - window['start']).total_seconds() / 3600
                lines.append(f"  {i}. {window['start'].strftime('%H:%M')} - {window['end'].strftime('%H:%M')} "
                           f"({duration:.1f}h) @ avg {window['avg_price']:.1f}¢/kWh")
            lines.append("")

        discharge_windows = analysis.get('discharge_windows', [])
        if discharge_windows:
            lines.append(f"⚡ DISCHARGE WINDOWS ({len(discharge_windows)}):")
            for i, window in enumerate(discharge_windows, 1):
                duration = (window['end'] - window['start']).total_seconds() / 3600
                spike_indicator = " 🔥 SPIKE" if window.get('spike') else ""
                lines.append(f"  {i}. {window['start'].strftime('%H:%M')} - {window['end'].strftime('%H:%M')} "
                           f"({duration:.1f}h) @ avg {window['avg_price']:.1f}¢/kWh{spike_indicator}")

        return "\n".join(lines)

    def convert_to_tesla_schedule(self, analysis: Dict) -> Dict:
        """
        Convert TOU analysis to Tesla time-based control format

        Returns a Tesla-compatible TOU schedule
        """
        charge_windows = analysis.get('charge_windows', [])
        discharge_windows = analysis.get('discharge_windows', [])

        # Build Tesla schedule format
        # Tesla uses a weekly schedule with time periods
        # For now, we'll create a daily schedule that repeats every day

        tou_periods = []

        # Add charge periods (Off-Peak)
        for window in charge_windows:
            # Convert to minutes from start of day
            start_minutes = window['start'].hour * 60 + window['start'].minute
            end_minutes = window['end'].hour * 60 + window['end'].minute

            # Handle periods that cross midnight
            if end_minutes < start_minutes:
                end_minutes += 24 * 60

            tou_periods.append({
                "fromDayOfWeek": 0,  # Sunday
                "toDayOfWeek": 6,    # Saturday (all days)
                "fromHour": window['start'].hour,
                "fromMinute": window['start'].minute,
                "toHour": window['end'].hour,
                "toMinute": window['end'].minute,
                "target": "charge"
            })

        # Add discharge periods (Peak)
        for window in discharge_windows:
            tou_periods.append({
                "fromDayOfWeek": 0,
                "toDayOfWeek": 6,
                "fromHour": window['start'].hour,
                "fromMinute": window['start'].minute,
                "toHour": window['end'].hour,
                "toMinute": window['end'].minute,
                "target": "discharge"
            })

        # Create the full TOU settings payload
        tou_settings = {
            "tou_settings": {
                "optimization_strategy": "economics",  # or "balanced"
                "schedule": tou_periods
            },
            "name": "TESLA SYNC (DO NOT EDIT)"
        }

        logger.info(f"Converted to Tesla schedule with {len(tou_periods)} periods")
        return tou_settings
