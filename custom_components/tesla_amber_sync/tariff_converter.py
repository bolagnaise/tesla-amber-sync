"""Convert Amber Electric pricing to Tesla tariff format."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

_LOGGER = logging.getLogger(__name__)


def _round_price(price: float) -> float:
    """
    Round price to 4 decimal places, removing trailing zeros.

    This matches Netzero's behavior:
    - 0.2014191 → 0.2014 (4 decimals)
    - 0.1990000 → 0.199 (3 decimals, trailing zeros removed)
    - 0.1234500 → 0.1235 (4 decimals, rounded)

    Args:
        price: Price in dollars per kWh

    Returns:
        Price rounded to max 4 decimal places with trailing zeros removed
    """
    # Round to 4 decimal places
    rounded = round(price, 4)
    # Python's float naturally drops trailing zeros in JSON serialization
    return rounded


def convert_amber_to_tesla_tariff(
    forecast_data: list[dict[str, Any]],
    tesla_energy_site_id: str,
    forecast_type: str = "predicted",
    powerwall_timezone: str | None = None,
) -> dict[str, Any] | None:
    """
    Convert Amber price forecast to Tesla tariff format.

    Implements rolling 24-hour window: periods that have passed today get tomorrow's prices,
    future periods get today's prices. This gives Tesla a full 24-hour lookahead.

    Args:
        forecast_data: List of price forecast points from Amber API
        tesla_energy_site_id: Tesla energy site ID
        forecast_type: Amber forecast type to use ('predicted', 'low', or 'high')
        powerwall_timezone: Powerwall timezone from site_info (optional)
                           If provided, uses this instead of auto-detecting from Amber data

    Returns:
        Tesla-compatible tariff structure or None if conversion fails
    """
    if not forecast_data:
        _LOGGER.warning("No forecast data provided")
        return None

    _LOGGER.info("Converting %d Amber forecast points to Tesla tariff", len(forecast_data))

    # Timezone handling:
    # 1. Prefer Powerwall timezone from site_info (most accurate)
    # 2. Fall back to auto-detection from Amber data
    detected_tz = None
    if powerwall_timezone:
        from zoneinfo import ZoneInfo
        try:
            detected_tz = ZoneInfo(powerwall_timezone)
            _LOGGER.info("✓ Using Powerwall timezone from site_info: %s", powerwall_timezone)
        except Exception as err:
            _LOGGER.warning(
                "Invalid Powerwall timezone '%s': %s, falling back to auto-detection",
                powerwall_timezone,
                err,
            )

    if not detected_tz:
        # Auto-detect timezone from first Amber timestamp
        # Amber timestamps include timezone info: "2025-11-11T16:05:00+10:00"
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

            # Price extraction logic:
            # - ActualInterval (past): Use perKwh (actual settled price)
            # - CurrentInterval (now): Use perKwh (current actual price)
            # - ForecastInterval (future): Use advancedPrice (forecast with user-selected type)
            #
            # advancedPrice includes complete forecast:
            # - Wholesale price forecast
            # - Network fees
            # - Market fees
            # - Renewable energy certificates
            #
            # User selects: 'predicted' (default), 'low' (conservative), 'high' (optimistic)
            advanced_price = point.get("advancedPrice")
            interval_type = point.get("type", "unknown")

            # For ForecastInterval: REQUIRE advancedPrice (no fallback)
            if interval_type == "ForecastInterval":
                if not advanced_price:
                    error_msg = f"Missing advancedPrice for ForecastInterval at {nem_time}. Amber API may be incomplete."
                    _LOGGER.error(error_msg)
                    raise ValueError(error_msg)

                # Handle dict format (standard: {predicted, low, high})
                if isinstance(advanced_price, dict):
                    if forecast_type not in advanced_price:
                        available = list(advanced_price.keys())
                        error_msg = f"Forecast type '{forecast_type}' not found in advancedPrice. Available: {available}"
                        _LOGGER.error("%s: %s", nem_time, error_msg)
                        raise ValueError(error_msg)

                    per_kwh_cents = advanced_price[forecast_type]
                    _LOGGER.debug("%s [ForecastInterval]: advancedPrice.%s=%.2fc/kWh", nem_time, forecast_type, per_kwh_cents)

                # Handle simple number format (legacy)
                elif isinstance(advanced_price, (int, float)):
                    per_kwh_cents = advanced_price
                    _LOGGER.debug("%s [ForecastInterval]: advancedPrice=%.2fc/kWh (numeric)", nem_time, per_kwh_cents)

                else:
                    error_msg = f"Invalid advancedPrice format at {nem_time}: {type(advanced_price).__name__}"
                    _LOGGER.error(error_msg)
                    raise ValueError(error_msg)

            # For ActualInterval/CurrentInterval: Use perKwh (actual settled prices)
            else:
                per_kwh_cents = point.get("perKwh", 0)
                _LOGGER.debug("%s [%s]: perKwh=%.2fc/kWh (actual)", nem_time, interval_type, per_kwh_cents)

            # Amber convention: feedIn prices are negative when you get paid
            # Tesla convention: sell prices are positive when you get paid
            # So we negate feedIn prices
            if channel_type == "feedIn":
                per_kwh_cents = -per_kwh_cents

            per_kwh_dollars = _round_price(per_kwh_cents / 100)

            # Use interval START time for bucketing
            # Amber's nemTime is the END of the interval, duration tells us the length
            # Calculate startTime = nemTime - duration
            # This gives us direct alignment with Tesla's PERIOD_XX_XX naming
            #
            # Example:
            #   nemTime=18:00, duration=30 → startTime=17:30 → bucket key (17, 30)
            #   Tesla PERIOD_17_30 → looks up key (17, 30) directly
            #   Result: Clean alignment with no shifting needed
            interval_start = timestamp - timedelta(minutes=duration)

            # Round interval start time to nearest 30-minute bucket
            start_minute_bucket = 0 if interval_start.minute < 30 else 30

            date_str = interval_start.date().isoformat()
            lookup_key = (date_str, interval_start.hour, start_minute_bucket)

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

            # Determine if this period has already passed
            if (hour < current_hour) or (hour == current_hour and minute < current_minute):
                # Past period - use tomorrow's price
                date_to_use = tomorrow
            else:
                # Future period - use today's price
                date_to_use = today

            # Direct lookup - no shifting needed with START time bucketing
            # Tesla PERIOD_17_30 (17:30-18:00) directly looks up bucket (17, 30)
            date_str = date_to_use.isoformat()
            lookup_key = (date_str, hour, minute)

            # Get general price (buy price)
            if lookup_key in general_lookup:
                prices = general_lookup[lookup_key]
                buy_price = _round_price(sum(prices) / len(prices))
                # Tesla restriction: No negative prices
                general_prices[period_key] = max(0, buy_price)
            else:
                # Fallback to current slot (no shifting with START time bucketing)
                fallback_key = (today.isoformat(), hour, minute)
                if fallback_key in general_lookup:
                    prices = general_lookup[fallback_key]
                    general_prices[period_key] = max(0, _round_price(sum(prices) / len(prices)))
                else:
                    general_prices[period_key] = 0

            # Get feedin price (sell price)
            if lookup_key in feedin_lookup:
                prices = feedin_lookup[lookup_key]
                sell_price = _round_price(sum(prices) / len(prices))

                # Tesla restriction #1: No negative prices
                sell_price = max(0, sell_price)

                # Tesla restriction #2: Sell price cannot exceed buy price
                if period_key in general_prices:
                    sell_price = min(sell_price, general_prices[period_key])

                feedin_prices[period_key] = sell_price
            else:
                # Fallback to current slot (no shifting with START time bucketing)
                fallback_key = (today.isoformat(), hour, minute)
                if fallback_key in feedin_lookup:
                    prices = feedin_lookup[fallback_key]
                    sell_price = max(0, _round_price(sum(prices) / len(prices)))
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
