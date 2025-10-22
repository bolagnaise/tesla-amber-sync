# app/tariff_converter.py
"""Convert Amber Electric pricing to Tesla tariff format"""
import logging
from datetime import datetime, timedelta
from typing import List, Dict

logger = logging.getLogger(__name__)


class AmberTariffConverter:
    """Converts Amber Electric price forecasts to Tesla-compatible tariff structure"""

    def __init__(self):
        logger.info("AmberTariffConverter initialized")

    def convert_amber_to_tesla_tariff(self, forecast_data: List[Dict], manual_override: str = None) -> Dict:
        """
        Convert Amber price forecast to Tesla tariff format

        Implements rolling 24-hour window: periods that have passed today get tomorrow's prices,
        future periods get today's prices. This gives Tesla a full 24-hour lookahead.

        Args:
            forecast_data: List of price forecast points from Amber API
            manual_override: 'charge' or 'discharge' to force battery behavior, None for normal

        Returns:
            Tesla-compatible tariff structure
        """
        if not forecast_data:
            logger.warning("No forecast data provided")
            return None

        logger.info(f"Converting {len(forecast_data)} Amber forecast points to Tesla tariff (manual_override={manual_override})")

        # Build timestamp-indexed price lookup: (date, hour, minute) -> price
        general_lookup = {}  # (date_str, hour, minute) -> [prices]
        feedin_lookup = {}

        for point in forecast_data:
            try:
                nem_time = point.get('nemTime', '')
                timestamp = datetime.fromisoformat(nem_time.replace('Z', '+00:00'))
                channel_type = point.get('channelType', '')

                # Use advancedPrice (includes spot + retailer margin, excludes network/environmental)
                # Convert cents/kWh to dollars/kWh for Tesla
                per_kwh_cents = point.get('advancedPrice', 0)
                per_kwh_dollars = per_kwh_cents / 100

                # Round down to nearest 30-minute interval
                minute_bucket = 0 if timestamp.minute < 30 else 30

                # Key by date, hour, minute for lookup
                date_str = timestamp.date().isoformat()
                lookup_key = (date_str, timestamp.hour, minute_bucket)

                if channel_type == 'general':
                    if lookup_key not in general_lookup:
                        general_lookup[lookup_key] = []
                    general_lookup[lookup_key].append(per_kwh_dollars)
                elif channel_type == 'feedIn':
                    if lookup_key not in feedin_lookup:
                        feedin_lookup[lookup_key] = []
                    # Keep the actual value - will handle Tesla restrictions in _build_rolling_24h_tariff
                    feedin_lookup[lookup_key].append(per_kwh_dollars)

            except Exception as e:
                logger.error(f"Error processing price point: {e}")
                continue

        # Now build the rolling 24-hour tariff
        general_prices, feedin_prices = self._build_rolling_24h_tariff(
            general_lookup, feedin_lookup
        )

        logger.info(f"Built rolling 24h tariff with {len(general_prices)} general and {len(feedin_prices)} feed-in periods")

        # Apply manual override if specified
        if manual_override:
            general_prices, feedin_prices = self._apply_manual_override(
                general_prices, feedin_prices, manual_override
            )

        # Create the Tesla tariff structure
        tariff = self._build_tariff_structure(general_prices, feedin_prices, manual_override)

        return tariff

    def _build_rolling_24h_tariff(self, general_lookup: Dict, feedin_lookup: Dict) -> tuple:
        """
        Build a rolling 24-hour tariff where past periods use tomorrow's prices

        If it's 12:00 PM now:
        - PERIOD_12_00 to PERIOD_23_30 → today's prices
        - PERIOD_00_00 to PERIOD_11_30 → tomorrow's prices

        Returns:
            (general_prices, feedin_prices) as dicts mapping PERIOD_XX_XX to price
        """
        from datetime import datetime, timedelta

        now = datetime.now()
        today = now.date()
        tomorrow = today + timedelta(days=1)

        current_hour = now.hour
        current_minute = 0 if now.minute < 30 else 30

        general_prices = {}
        feedin_prices = {}

        # Build all 48 half-hour periods in a day
        for hour in range(24):
            for minute in [0, 30]:
                period_key = f"PERIOD_{hour:02d}_{minute:02d}"

                # Determine if this period has already passed today
                if (hour < current_hour) or (hour == current_hour and minute < current_minute):
                    # Past period - use tomorrow's price
                    date_to_use = tomorrow
                else:
                    # Future period - use today's price
                    date_to_use = today

                date_str = date_to_use.isoformat()
                lookup_key = (date_str, hour, minute)

                # Get general price (buy price)
                if lookup_key in general_lookup:
                    prices = general_lookup[lookup_key]
                    buy_price = sum(prices) / len(prices)
                    # Tesla doesn't support negative prices - clamp to 0
                    if buy_price < 0:
                        logger.debug(f"{period_key}: Clamping negative buy price {buy_price:.4f} -> 0.0000")
                        general_prices[period_key] = 0
                    else:
                        general_prices[period_key] = buy_price
                else:
                    # If no data available, use a default or skip
                    logger.warning(f"No general price data for {period_key} on {date_str}")

                # Get feedin price (sell price)
                if lookup_key in feedin_lookup:
                    prices = feedin_lookup[lookup_key]
                    sell_price = sum(prices) / len(prices)
                    original_sell = sell_price

                    # Tesla doesn't support negative prices - clamp to 0
                    sell_price = max(0, sell_price)

                    # Tesla restriction: sell price cannot exceed buy price
                    # If necessary, adjust sell price downward to comply
                    if period_key in general_prices:
                        if sell_price > general_prices[period_key]:
                            logger.debug(f"{period_key}: Adjusting sell price {sell_price:.4f} -> {general_prices[period_key]:.4f} (cannot exceed buy)")
                            sell_price = general_prices[period_key]

                    if original_sell != sell_price:
                        logger.debug(f"{period_key}: Sell price adjusted from {original_sell:.4f} to {sell_price:.4f}")

                    feedin_prices[period_key] = sell_price
                else:
                    logger.warning(f"No feed-in price data for {period_key} on {date_str}")

        logger.info(f"Rolling 24h window: {len([k for k in general_prices.keys()])} periods from {today} and {tomorrow}")

        return general_prices, feedin_prices

    def _build_tariff_structure(self, general_prices: Dict[str, float],
                                feedin_prices: Dict[str, float],
                                manual_override: str = None) -> Dict:
        """Build the complete Tesla tariff structure"""

        # Build TOU periods for Summer season (covers whole year for Amber)
        tou_periods = self._build_tou_periods(general_prices.keys())

        # Change code and name based on manual override to force Tesla app refresh
        if manual_override == 'charge':
            code = "TESLA_SYNC:MANUAL:CHARGE"
            name = "MANUAL CHARGE MODE (Tesla Sync)"
            utility = "Tesla Sync - Manual Control"
        elif manual_override == 'discharge':
            code = "TESLA_SYNC:MANUAL:DISCHARGE"
            name = "MANUAL DISCHARGE MODE (Tesla Sync)"
            utility = "Tesla Sync - Manual Control"
        else:
            code = "TESLA_SYNC:AMBER:AMBER"
            name = "Amber Electric (Tesla Sync)"
            utility = "Amber Electric"

        tariff = {
            "version": 1,
            "code": code,
            "name": name,
            "utility": utility,
            "currency": "AUD",
            "daily_charges": [
                {
                    "name": "Charge",
                    "amount": 0
                }
            ],
            "demand_charges": {
                "ALL": {
                    "rates": {
                        "ALL": 0
                    }
                },
                "Summer": {},
                "Winter": {}
            },
            "energy_charges": {
                "ALL": {
                    "rates": {
                        "ALL": 0
                    }
                },
                "Summer": {
                    "rates": general_prices
                },
                "Winter": {}
            },
            "seasons": {
                "Summer": {
                    "fromMonth": 1,
                    "toMonth": 12,
                    "fromDay": 1,
                    "toDay": 31,
                    "tou_periods": tou_periods
                },
                "Winter": {
                    "fromDay": 0,
                    "toDay": 0,
                    "fromMonth": 0,
                    "toMonth": 0,
                    "tou_periods": {}
                }
            },
            "sell_tariff": {
                "name": "Amber Electric (managed by Tesla Sync, do not edit)",
                "utility": "Amber Electric",
                "daily_charges": [
                    {
                        "name": "Charge",
                        "amount": 0
                    }
                ],
                "demand_charges": {
                    "ALL": {
                        "rates": {
                            "ALL": 0
                        }
                    },
                    "Summer": {},
                    "Winter": {}
                },
                "energy_charges": {
                    "ALL": {
                        "rates": {
                            "ALL": 0
                        }
                    },
                    "Summer": {
                        "rates": feedin_prices
                    },
                    "Winter": {}
                },
                "seasons": {
                    "Summer": {
                        "fromMonth": 1,
                        "toMonth": 12,
                        "fromDay": 1,
                        "toDay": 31,
                        "tou_periods": tou_periods
                    },
                    "Winter": {
                        "fromDay": 0,
                        "toDay": 0,
                        "fromMonth": 0,
                        "toMonth": 0,
                        "tou_periods": {}
                    }
                }
            }
        }

        logger.info("Built Tesla tariff structure")
        return tariff

    def _build_tou_periods(self, period_keys) -> Dict:
        """
        Build TOU period definitions for all time slots
        Matches NetZero's format exactly - omitting fields when they're 0

        Args:
            period_keys: Set of period keys like "PERIOD_14_30"

        Returns:
            Dictionary mapping period keys to time slot definitions
        """
        tou_periods = {}

        for period_key in period_keys:
            # Extract hour and minute from period key
            # PERIOD_14_30 -> hour=14, minute=30
            try:
                parts = period_key.split('_')
                from_hour = int(parts[1])
                from_minute = int(parts[2])

                # Calculate end time (30 minutes later)
                to_hour = from_hour
                to_minute = from_minute + 30

                if to_minute >= 60:
                    to_minute = 0
                    to_hour += 1

                # Build period definition, omitting fields when they're 0
                # This matches NetZero's format exactly
                period_def = {
                    "toDayOfWeek": 6  # Saturday (covers all days with implicit fromDayOfWeek=0)
                }

                # Only include fromHour if non-zero
                if from_hour > 0:
                    period_def["fromHour"] = from_hour

                # Only include fromMinute if non-zero
                if from_minute > 0:
                    period_def["fromMinute"] = from_minute

                # Only include toHour if it's not same as fromHour or if it's non-zero
                if to_hour != from_hour or to_hour > 0:
                    period_def["toHour"] = to_hour

                # Only include toMinute if non-zero
                if to_minute > 0:
                    period_def["toMinute"] = to_minute

                tou_periods[period_key] = {
                    "periods": [period_def]
                }

            except (IndexError, ValueError) as e:
                logger.error(f"Error parsing period key {period_key}: {e}")
                continue

        logger.debug(f"Built {len(tou_periods)} TOU period definitions")
        return tou_periods

    def _apply_manual_override(self, general_prices: Dict[str, float],
                               feedin_prices: Dict[str, float],
                               mode: str) -> tuple:
        """
        Apply manual override to force charging or discharging

        Uses actual min/max prices from the 24h period to make the override more realistic

        Args:
            general_prices: Buy prices (what you pay to import from grid)
            feedin_prices: Sell prices (what you get paid to export to grid)
            mode: 'charge' or 'discharge'

        Returns:
            (modified_general_prices, modified_feedin_prices)
        """
        # Calculate min/max prices from the actual 24h period
        buy_prices = [p for p in general_prices.values() if p > 0]
        sell_prices = [p for p in feedin_prices.values() if p > 0]

        min_buy = min(buy_prices) if buy_prices else 0.05
        max_buy = max(buy_prices) if buy_prices else 0.30
        min_sell = min(sell_prices) if sell_prices else 0.02
        max_sell = max(sell_prices) if sell_prices else 0.20

        if mode == 'charge':
            # Force charging: set buy price to minimum (makes grid charging appear cheapest)
            # and sell price to maximum (makes exporting appear expensive/wasteful)
            logger.info(f"Applying CHARGE override - setting buy={min_buy:.4f}, sell={max_sell:.4f}")
            for period_key in general_prices:
                general_prices[period_key] = min_buy
            for period_key in feedin_prices:
                feedin_prices[period_key] = max_sell

        elif mode == 'discharge':
            # Force discharging: set sell price to maximum (makes exporting very profitable)
            # and keep buy prices at maximum (makes importing expensive)
            logger.info(f"Applying DISCHARGE override - setting sell={max_sell:.4f}, buy={max_buy:.4f}")
            for period_key in feedin_prices:
                feedin_prices[period_key] = max_sell
            for period_key in general_prices:
                general_prices[period_key] = max_buy

        return general_prices, feedin_prices
