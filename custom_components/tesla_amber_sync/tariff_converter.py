"""Convert Amber Electric pricing to Tesla tariff format."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def convert_amber_to_tesla_tariff(
    forecast_data: list[dict[str, Any]],
    tesla_site_id: str,
    forecast_type: str = "predicted",
) -> dict[str, Any] | None:
    """
    Convert Amber price forecast to Tesla tariff format.

    Implements rolling 24-hour window: periods that have passed today get tomorrow's prices,
    future periods get today's prices. This gives Tesla a full 24-hour lookahead.

    Args:
        forecast_data: List of price forecast points from Amber API
        tesla_site_id: Tesla energy site ID
        forecast_type: Amber forecast type to use ('predicted', 'low', or 'high')

    Returns:
        Tesla-compatible tariff structure or None if conversion fails
    """
    if not forecast_data:
        _LOGGER.warning("No forecast data provided")
        return None

    _LOGGER.info("Converting %d Amber forecast points to Tesla tariff", len(forecast_data))

    # Auto-detect timezone from first Amber timestamp
    # Amber timestamps include timezone info: "2025-11-11T16:05:00+10:00"
    detected_tz = None
    for point in forecast_data:
        nem_time = point.get("nemTime", "")
        if nem_time:
            try:
                timestamp = datetime.fromisoformat(nem_time.replace("Z", "+00:00"))
                detected_tz = timestamp.tzinfo
                _LOGGER.info("Auto-detected timezone from Amber data: %s", detected_tz)
                break
            except Exception:
                continue

    # Build timestamp-indexed price lookup: (date, hour, minute) -> price
    general_lookup: dict[tuple[str, int, int], list[float]] = {}
    feedin_lookup: dict[tuple[str, int, int], list[float]] = {}

    for point in forecast_data:
        try:
            nem_time = point.get("nemTime", "")
            timestamp = datetime.fromisoformat(nem_time.replace("Z", "+00:00"))
            channel_type = point.get("channelType", "")
            duration = point.get("duration", 30)  # Get actual interval duration (usually 5 or 30 minutes)

            # Use advancedPrice with user-selected forecast type (predicted/low/high)
            advanced_price = point.get("advancedPrice")

            if advanced_price and isinstance(advanced_price, dict) and forecast_type in advanced_price:
                per_kwh_cents = advanced_price[forecast_type]
            elif advanced_price and isinstance(advanced_price, (int, float)):
                per_kwh_cents = advanced_price
            else:
                per_kwh_cents = point.get("perKwh", 0)

            # Amber convention: feedIn prices are negative when you get paid
            # Tesla convention: sell prices are positive when you get paid
            # So we negate feedIn prices
            if channel_type == "feedIn":
                per_kwh_cents = -per_kwh_cents

            per_kwh_dollars = per_kwh_cents / 100

            # IMPORTANT: Amber's nemTime represents the END of the interval
            # The 'duration' field tells us the interval length (typically 5 or 30 minutes)
            # Tesla's PERIOD_XX_YY uses START time (PERIOD_00_00 = 00:00-00:30)
            # So we subtract the duration to convert END time to START time
            #
            # Example with 5-min intervals:
            #   nemTime=00:05, duration=5 → interval_start=00:00 → PERIOD_00_00
            #   nemTime=00:30, duration=5 → interval_start=00:25 → PERIOD_00_00
            interval_start = timestamp - timedelta(minutes=duration)

            # Round to nearest 30-minute interval
            minute_bucket = 0 if interval_start.minute < 30 else 30

            date_str = interval_start.date().isoformat()
            lookup_key = (date_str, interval_start.hour, minute_bucket)

            if channel_type == "general":
                if lookup_key not in general_lookup:
                    general_lookup[lookup_key] = []
                general_lookup[lookup_key].append(per_kwh_dollars)
            elif channel_type == "feedIn":
                if lookup_key not in feedin_lookup:
                    feedin_lookup[lookup_key] = []
                feedin_lookup[lookup_key].append(per_kwh_dollars)

        except Exception as err:
            _LOGGER.error("Error processing price point: %s", err)
            continue

    # Build the rolling 24-hour tariff
    general_prices, feedin_prices = _build_rolling_24h_tariff(
        general_lookup, feedin_lookup, detected_tz
    )

    _LOGGER.info(
        "Built rolling 24h tariff with %d general and %d feed-in periods",
        len(general_prices),
        len(feedin_prices),
    )

    # Create the Tesla tariff structure
    tariff = _build_tariff_structure(general_prices, feedin_prices)

    return tariff


def _build_rolling_24h_tariff(
    general_lookup: dict[tuple[str, int, int], list[float]],
    feedin_lookup: dict[tuple[str, int, int], list[float]],
    detected_tz: Any = None,
) -> tuple[dict[str, float], dict[str, float]]:
    """Build a rolling 24-hour tariff where past periods use tomorrow's prices."""
    from zoneinfo import ZoneInfo

    # IMPORTANT: Use the timezone from Amber data (auto-detected from nemTime timestamps)
    # This ensures correct "past vs future" period detection for all Australian locations
    # Falls back to Sydney timezone if detection failed
    if detected_tz:
        aus_tz = detected_tz
        _LOGGER.info("Using auto-detected timezone: %s", aus_tz)
    else:
        aus_tz = ZoneInfo("Australia/Sydney")
        _LOGGER.warning("Timezone detection failed, falling back to Australia/Sydney")

    now = datetime.now(aus_tz)
    today = now.date()
    tomorrow = today + timedelta(days=1)

    current_hour = now.hour
    current_minute = 0 if now.minute < 30 else 30

    general_prices: dict[str, float] = {}
    feedin_prices: dict[str, float] = {}

    # Build all 48 half-hour periods in a day
    for hour in range(24):
        for minute in [0, 30]:
            period_key = f"PERIOD_{hour:02d}_{minute:02d}"

            # No shift - use current period's time (aligned with interval start time)
            # We already converted Amber's nemTime (end time) to interval start time
            next_minute = minute
            next_hour = hour

            # Determine if this period has already passed
            if (hour < current_hour) or (hour == current_hour and minute < current_minute):
                # Past period - use tomorrow's price
                date_to_use = tomorrow
            else:
                # Future period - use today's price
                date_to_use = today

            date_str = date_to_use.isoformat()
            lookup_key = (date_str, next_hour, next_minute)

            # Get general price (buy price)
            if lookup_key in general_lookup:
                prices = general_lookup[lookup_key]
                buy_price = sum(prices) / len(prices)
                # Tesla restriction: No negative prices
                general_prices[period_key] = max(0, buy_price)
            else:
                # Fallback to current slot
                fallback_key = (today.isoformat(), hour, minute)
                if fallback_key in general_lookup:
                    prices = general_lookup[fallback_key]
                    general_prices[period_key] = max(0, sum(prices) / len(prices))
                else:
                    general_prices[period_key] = 0

            # Get feedin price (sell price)
            if lookup_key in feedin_lookup:
                prices = feedin_lookup[lookup_key]
                sell_price = sum(prices) / len(prices)

                # Tesla restriction #1: No negative prices
                sell_price = max(0, sell_price)

                # Tesla restriction #2: Sell price cannot exceed buy price
                if period_key in general_prices:
                    sell_price = min(sell_price, general_prices[period_key])

                feedin_prices[period_key] = sell_price
            else:
                # Fallback to current slot
                fallback_key = (today.isoformat(), hour, minute)
                if fallback_key in feedin_lookup:
                    prices = feedin_lookup[fallback_key]
                    sell_price = max(0, sum(prices) / len(prices))
                    # Tesla restriction: sell price cannot exceed buy price
                    if period_key in general_prices:
                        sell_price = min(sell_price, general_prices[period_key])
                    feedin_prices[period_key] = sell_price
                else:
                    feedin_prices[period_key] = 0

    return general_prices, feedin_prices


def _build_tariff_structure(
    general_prices: dict[str, float],
    feedin_prices: dict[str, float],
) -> dict[str, Any]:
    """Build the complete Tesla tariff structure."""
    # Build TOU periods
    tou_periods = _build_tou_periods(general_prices.keys())

    tariff = {
        "version": 1,
        "code": "TESLA_SYNC:AMBER:AMBER",
        "name": "Amber Electric (Tesla Sync)",
        "utility": "Amber Electric",
        "currency": "AUD",
        "daily_charges": [{"name": "Charge"}],
        "demand_charges": {
            "ALL": {"rates": {"ALL": 0}},
            "Summer": {},
            "Winter": {},
        },
        "energy_charges": {
            "ALL": {"rates": {"ALL": 0}},
            "Summer": {"rates": general_prices},
            "Winter": {},
        },
        "seasons": {
            "Summer": {
                "fromMonth": 1,
                "toMonth": 12,
                "fromDay": 1,
                "toDay": 31,
                "tou_periods": tou_periods,
            },
            "Winter": {
                "fromDay": 0,
                "toDay": 0,
                "fromMonth": 0,
                "toMonth": 0,
                "tou_periods": {},
            },
        },
        "sell_tariff": {
            "name": "Amber Electric (managed by Tesla Sync)",
            "utility": "Amber Electric",
            "daily_charges": [{"name": "Charge"}],
            "demand_charges": {
                "ALL": {"rates": {"ALL": 0}},
                "Summer": {},
                "Winter": {},
            },
            "energy_charges": {
                "ALL": {"rates": {"ALL": 0}},
                "Summer": {"rates": feedin_prices},
                "Winter": {},
            },
            "seasons": {
                "Summer": {
                    "fromMonth": 1,
                    "toMonth": 12,
                    "fromDay": 1,
                    "toDay": 31,
                    "tou_periods": tou_periods,
                },
                "Winter": {
                    "fromDay": 0,
                    "toDay": 0,
                    "fromMonth": 0,
                    "toMonth": 0,
                    "tou_periods": {},
                },
            },
        },
    }

    return tariff


def _build_tou_periods(period_keys: Any) -> dict[str, Any]:
    """Build TOU period definitions for all time slots."""
    tou_periods: dict[str, Any] = {}

    for period_key in period_keys:
        try:
            parts = period_key.split("_")
            from_hour = int(parts[1])
            from_minute = int(parts[2])

            # Calculate end time (30 minutes later)
            to_hour = from_hour
            to_minute = from_minute + 30

            if to_minute >= 60:
                to_minute = 0
                to_hour += 1

            # Build period definition
            period_def: dict[str, int] = {"toDayOfWeek": 6}

            if from_hour > 0:
                period_def["fromHour"] = from_hour
            if from_minute > 0:
                period_def["fromMinute"] = from_minute
            if to_hour != from_hour or to_hour > 0:
                period_def["toHour"] = to_hour
            if to_minute > 0:
                period_def["toMinute"] = to_minute

            tou_periods[period_key] = {"periods": [period_def]}

        except (IndexError, ValueError) as err:
            _LOGGER.error("Error parsing period key %s: %s", period_key, err)
            continue

    return tou_periods
