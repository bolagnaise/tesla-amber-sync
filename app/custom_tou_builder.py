# app/custom_tou_builder.py
"""Build Tesla-compatible tariff structures from custom TOU schedules"""
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class CustomTOUBuilder:
    """Converts custom TOU schedules to Tesla-compatible tariff format"""

    def __init__(self):
        logger.info("CustomTOUBuilder initialized")

    def build_tesla_tariff(self, schedule) -> Dict:
        """
        Convert a CustomTOUSchedule to Tesla tariff format

        Args:
            schedule: CustomTOUSchedule object with seasons and periods

        Returns:
            Tesla-compatible tariff structure ready for API submission
        """
        logger.info(f"Building Tesla tariff for schedule: {schedule.name}")

        # Build seasons structure
        seasons_data = {}
        energy_charges = {"ALL": {"rates": {"ALL": 0}}}
        demand_charges = {"ALL": {"rates": {"ALL": 0}}}
        sell_energy_charges = {"ALL": {"rates": {"ALL": 0}}}
        sell_demand_charges = {"ALL": {"rates": {"ALL": 0}}}

        for season in schedule.seasons:
            logger.info(f"Processing season: {season.name}")

            # Build TOU periods and rates for this season
            tou_periods = {}
            energy_rates = {}
            sell_rates = {}
            demand_rates = {}

            periods_list = season.periods.order_by('display_order').all()

            for period in periods_list:
                # Generate all 30-minute slots covered by this period
                slots = self._generate_time_slots(
                    period.from_hour, period.from_minute,
                    period.to_hour, period.to_minute,
                    period.from_day_of_week, period.to_day_of_week
                )

                for slot in slots:
                    period_key = slot['period_key']

                    # Add TOU period definition
                    if period_key not in tou_periods:
                        tou_periods[period_key] = {
                            "periods": [self._build_period_def(slot)]
                        }

                    # Set rates for this slot
                    energy_rates[period_key] = float(period.energy_rate)
                    sell_rates[period_key] = float(period.sell_rate)

                    if period.demand_rate and period.demand_rate > 0:
                        demand_rates[period_key] = float(period.demand_rate)

            # Validate Tesla restrictions
            self._validate_rates(energy_rates, sell_rates, season.name)

            # Add season to structure
            seasons_data[season.name] = {
                "fromMonth": season.from_month,
                "toMonth": season.to_month,
                "fromDay": season.from_day,
                "toDay": season.to_day,
                "tou_periods": tou_periods
            }

            energy_charges[season.name] = {"rates": energy_rates}
            sell_energy_charges[season.name] = {"rates": sell_rates}

            if demand_rates:
                demand_charges[season.name] = {"rates": demand_rates}
                sell_demand_charges[season.name] = {"rates": demand_rates}
            else:
                demand_charges[season.name] = {}
                sell_demand_charges[season.name] = {}

        # Build complete tariff structure
        tariff = {
            "version": 1,
            "code": schedule.code or f"CUSTOM:{schedule.id}",
            "name": schedule.name,
            "utility": schedule.utility,
            "currency": schedule.currency,
            "daily_charges": [
                {
                    "name": "Supply Charge",
                    "amount": float(schedule.daily_charge) if schedule.daily_charge else 0
                }
            ],
            "monthly_charges": float(schedule.monthly_charge) if schedule.monthly_charge else 0,
            "demand_charges": demand_charges,
            "energy_charges": energy_charges,
            "seasons": seasons_data,
            "sell_tariff": {
                "name": f"{schedule.name} (Feed-in)",
                "utility": schedule.utility,
                "daily_charges": [{"name": "Supply Charge"}],
                "demand_charges": sell_demand_charges,
                "energy_charges": sell_energy_charges,
                "seasons": seasons_data
            }
        }

        logger.info(f"Built tariff with {len(seasons_data)} seasons")
        return tariff

    def _generate_time_slots(self, from_hour: int, from_minute: int,
                            to_hour: int, to_minute: int,
                            from_day: int, to_day: int) -> List[Dict]:
        """
        Generate all 30-minute time slots covered by a period

        Args:
            from_hour, from_minute: Start time
            to_hour, to_minute: End time
            from_day, to_day: Day of week range (0=Mon, 6=Sun)

        Returns:
            List of slot definitions with period_key and time bounds
        """
        slots = []

        # Convert to minutes since midnight
        start_minutes = from_hour * 60 + from_minute
        end_minutes = to_hour * 60 + to_minute

        # Handle overnight periods (e.g., 22:00 to 06:00)
        if end_minutes <= start_minutes:
            end_minutes += 24 * 60  # Add 24 hours

        # Generate 30-minute slots
        current = start_minutes
        while current < end_minutes:
            hour = (current // 60) % 24
            minute = current % 60

            # Create slot
            slot = {
                'period_key': f"PERIOD_{hour:02d}_{minute:02d}",
                'from_hour': hour,
                'from_minute': minute,
                'to_hour': ((current + 30) // 60) % 24,
                'to_minute': (current + 30) % 60,
                'from_day_of_week': from_day,
                'to_day_of_week': to_day
            }

            slots.append(slot)
            current += 30

        return slots

    def _build_period_def(self, slot: Dict) -> Dict:
        """
        Build a Tesla period definition from a slot

        Omits fields when they're 0 to match Tesla's expected format
        """
        period_def = {}

        # Day of week range
        if slot['from_day_of_week'] > 0:
            period_def['fromDayOfWeek'] = slot['from_day_of_week']
        if slot['to_day_of_week'] < 6:
            period_def['toDayOfWeek'] = slot['to_day_of_week']
        elif slot['to_day_of_week'] == 6 and slot['from_day_of_week'] == 0:
            # All week (Mon-Sun), include toDayOfWeek
            period_def['toDayOfWeek'] = 6

        # Time range - only include non-zero values
        if slot['from_hour'] > 0:
            period_def['fromHour'] = slot['from_hour']
        if slot['from_minute'] > 0:
            period_def['fromMinute'] = slot['from_minute']
        if slot['to_hour'] > 0:
            period_def['toHour'] = slot['to_hour']
        if slot['to_minute'] > 0:
            period_def['toMinute'] = slot['to_minute']

        return period_def

    def _validate_rates(self, energy_rates: Dict[str, float],
                       sell_rates: Dict[str, float], season_name: str):
        """
        Validate rates comply with Tesla restrictions:
        1. No negative prices
        2. Buy rate >= Sell rate for every period
        """
        violations = []

        for period_key in energy_rates.keys():
            buy_rate = energy_rates[period_key]
            sell_rate = sell_rates.get(period_key, 0)

            # Check for negative prices
            if buy_rate < 0:
                violations.append(f"{period_key}: Buy rate is negative: ${buy_rate:.4f}")
            if sell_rate < 0:
                violations.append(f"{period_key}: Sell rate is negative: ${sell_rate:.4f}")

            # Check that buy >= sell
            if sell_rate > buy_rate:
                violations.append(
                    f"{period_key}: Sell rate (${sell_rate:.4f}) > Buy rate (${buy_rate:.4f}) "
                    f"- Tesla will reject this!"
                )

        if violations:
            logger.error(f"Season '{season_name}' validation FAILED:")
            for violation in violations:
                logger.error(f"  - {violation}")
            raise ValueError(f"Tariff validation failed: {len(violations)} violations")
        else:
            logger.info(f"Season '{season_name}' validation PASSED")

    def preview_schedule(self, schedule) -> Dict:
        """
        Generate a human-readable preview of a TOU schedule

        Returns:
            Dictionary with schedule details for display
        """
        preview = {
            'name': schedule.name,
            'utility': schedule.utility,
            'code': schedule.code,
            'currency': schedule.currency,
            'daily_charge': schedule.daily_charge,
            'monthly_charge': schedule.monthly_charge,
            'seasons': []
        }

        for season in schedule.seasons:
            season_data = {
                'name': season.name,
                'date_range': f"{season.from_month}/{season.from_day} - {season.to_month}/{season.to_day}",
                'periods': []
            }

            for period in season.periods.order_by('display_order').all():
                period_data = {
                    'name': period.name,
                    'time': f"{period.from_hour:02d}:{period.from_minute:02d} - "
                           f"{period.to_hour:02d}:{period.to_minute:02d}",
                    'days': self._format_days(period.from_day_of_week, period.to_day_of_week),
                    'energy_rate': f"${period.energy_rate:.4f}/kWh",
                    'sell_rate': f"${period.sell_rate:.4f}/kWh",
                    'demand_rate': f"${period.demand_rate:.2f}/kW" if period.demand_rate else "None"
                }
                season_data['periods'].append(period_data)

            preview['seasons'].append(season_data)

        return preview

    def _format_days(self, from_day: int, to_day: int) -> str:
        """Format day of week range as human-readable string"""
        days = ['Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun']

        if from_day == 0 and to_day == 6:
            return "All week"
        elif from_day == 0 and to_day == 4:
            return "Weekdays"
        elif from_day == 5 and to_day == 6:
            return "Weekends"
        elif from_day == to_day:
            return days[from_day]
        else:
            return f"{days[from_day]}-{days[to_day]}"
