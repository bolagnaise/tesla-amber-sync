"""Sensor platform for Tesla Sync integration."""
from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import (
    CURRENCY_DOLLAR,
    UnitOfEnergy,
    UnitOfPower,
    PERCENTAGE,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import (
    DOMAIN,
    SENSOR_TYPE_CURRENT_PRICE,
    SENSOR_TYPE_SOLAR_POWER,
    SENSOR_TYPE_GRID_POWER,
    SENSOR_TYPE_BATTERY_POWER,
    SENSOR_TYPE_HOME_LOAD,
    SENSOR_TYPE_BATTERY_LEVEL,
    SENSOR_TYPE_DAILY_SOLAR_ENERGY,
    SENSOR_TYPE_DAILY_GRID_IMPORT,
    SENSOR_TYPE_DAILY_GRID_EXPORT,
    SENSOR_TYPE_GRID_IMPORT_POWER,
    SENSOR_TYPE_IN_DEMAND_CHARGE_PERIOD,
    SENSOR_TYPE_PEAK_DEMAND_THIS_CYCLE,
    SENSOR_TYPE_DEMAND_CHARGE_COST,
    SENSOR_TYPE_DAYS_UNTIL_DEMAND_RESET,
    CONF_DEMAND_CHARGE_ENABLED,
    CONF_DEMAND_CHARGE_RATE,
    CONF_DEMAND_CHARGE_START_TIME,
    CONF_DEMAND_CHARGE_END_TIME,
    CONF_DEMAND_CHARGE_DAYS,
    CONF_DEMAND_CHARGE_BILLING_DAY,
    ATTR_PRICE_SPIKE,
    ATTR_WHOLESALE_PRICE,
    ATTR_NETWORK_PRICE,
)
from .coordinator import AmberPriceCoordinator, TeslaEnergyCoordinator

_LOGGER = logging.getLogger(__name__)


@dataclass
class TeslaAmberSensorEntityDescription(SensorEntityDescription):
    """Describes Tesla Sync sensor entity."""

    value_fn: Callable[[Any], Any] | None = None
    attr_fn: Callable[[Any], dict[str, Any]] | None = None


PRICE_SENSORS: tuple[TeslaAmberSensorEntityDescription, ...] = (
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_CURRENT_PRICE,
        name="Current Electricity Price",
        native_unit_of_measurement=f"{CURRENCY_DOLLAR}/{UnitOfEnergy.KILO_WATT_HOUR}",
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=4,
        value_fn=lambda data: (
            data.get("current", [{}])[0].get("perKwh", 0) / 100
            if data and data.get("current")
            else None
        ),
        attr_fn=lambda data: {
            ATTR_PRICE_SPIKE: data.get("current", [{}])[0].get("spikeStatus")
            if data and data.get("current")
            else None,
            ATTR_WHOLESALE_PRICE: data.get("current", [{}])[0].get("wholesaleKWHPrice", 0) / 100
            if data and data.get("current")
            else 0,
            ATTR_NETWORK_PRICE: data.get("current", [{}])[0].get("networkKWHPrice", 0) / 100
            if data and data.get("current")
            else 0,
        },
    ),
)

ENERGY_SENSORS: tuple[TeslaAmberSensorEntityDescription, ...] = (
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_SOLAR_POWER,
        name="Solar Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data.get("solar_power") if data else None,
    ),
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_GRID_POWER,
        name="Grid Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data.get("grid_power") if data else None,
    ),
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_BATTERY_POWER,
        name="Battery Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data.get("battery_power") if data else None,
    ),
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_HOME_LOAD,
        name="Home Load",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: data.get("load_power") if data else None,
    ),
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_BATTERY_LEVEL,
        name="Battery Level",
        native_unit_of_measurement=PERCENTAGE,
        device_class=SensorDeviceClass.BATTERY,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=1,
        value_fn=lambda data: data.get("battery_level") if data else None,
    ),
)

DEMAND_CHARGE_SENSORS: tuple[TeslaAmberSensorEntityDescription, ...] = (
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_GRID_IMPORT_POWER,
        name="Grid Import Power",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=lambda data: max(0, data.get("grid_power", 0)) if data else 0,
    ),
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_IN_DEMAND_CHARGE_PERIOD,
        name="In Demand Charge Period",
        value_fn=None,  # Calculated in sensor class
    ),
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_PEAK_DEMAND_THIS_CYCLE,
        name="Peak Demand This Cycle",
        native_unit_of_measurement=UnitOfPower.KILO_WATT,
        device_class=SensorDeviceClass.POWER,
        state_class=SensorStateClass.MEASUREMENT,
        suggested_display_precision=3,
        value_fn=None,  # Stateful - managed in sensor class
    ),
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_DEMAND_CHARGE_COST,
        name="Demand Charge Cost This Month",
        native_unit_of_measurement=CURRENCY_DOLLAR,
        device_class=SensorDeviceClass.MONETARY,
        suggested_display_precision=2,
        value_fn=None,  # Calculated in sensor class
    ),
    TeslaAmberSensorEntityDescription(
        key=SENSOR_TYPE_DAYS_UNTIL_DEMAND_RESET,
        name="Days Until Demand Reset",
        native_unit_of_measurement="days",
        suggested_display_precision=0,
        value_fn=None,  # Calculated in sensor class
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Tesla Sync sensor entities."""
    domain_data = hass.data[DOMAIN][entry.entry_id]
    amber_coordinator: AmberPriceCoordinator = domain_data["amber_coordinator"]
    tesla_coordinator: TeslaEnergyCoordinator = domain_data["tesla_coordinator"]

    entities: list[SensorEntity] = []

    # Add price sensors
    for description in PRICE_SENSORS:
        entities.append(
            AmberPriceSensor(
                coordinator=amber_coordinator,
                description=description,
                entry=entry,
            )
        )

    # Add energy sensors
    for description in ENERGY_SENSORS:
        entities.append(
            TeslaEnergySensor(
                coordinator=tesla_coordinator,
                description=description,
                entry=entry,
            )
        )

    # Add demand charge sensors if enabled
    if entry.data.get(CONF_DEMAND_CHARGE_ENABLED, False):
        _LOGGER.info("Demand charge tracking enabled - adding sensors")
        for description in DEMAND_CHARGE_SENSORS:
            entities.append(
                DemandChargeSensor(
                    coordinator=tesla_coordinator,
                    description=description,
                    entry=entry,
                    hass=hass,
                )
            )

    async_add_entities(entities)


class AmberPriceSensor(CoordinatorEntity, SensorEntity):
    """Sensor for Amber electricity prices."""

    entity_description: TeslaAmberSensorEntityDescription

    def __init__(
        self,
        coordinator: AmberPriceCoordinator,
        description: TeslaAmberSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.coordinator.data)
        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        if self.entity_description.attr_fn:
            return self.entity_description.attr_fn(self.coordinator.data)
        return {}


class TeslaEnergySensor(CoordinatorEntity, SensorEntity):
    """Sensor for Tesla energy data."""

    entity_description: TeslaAmberSensorEntityDescription

    def __init__(
        self,
        coordinator: TeslaEnergyCoordinator,
        description: TeslaAmberSensorEntityDescription,
        entry: ConfigEntry,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.coordinator.data)
        return None


class DemandChargeSensor(CoordinatorEntity, SensorEntity):
    """Sensor for demand charge tracking."""

    entity_description: TeslaAmberSensorEntityDescription

    def __init__(
        self,
        coordinator: TeslaEnergyCoordinator,
        description: TeslaAmberSensorEntityDescription,
        entry: ConfigEntry,
        hass: HomeAssistant,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description
        self._attr_unique_id = f"{entry.entry_id}_{description.key}"
        self._attr_has_entity_name = True
        self._entry = entry
        self._hass = hass

        # State for peak tracking
        self._peak_demand = 0.0
        self._peak_timestamp = None
        self._last_reset_month = datetime.now().month

    def _is_in_demand_period(self) -> bool:
        """Check if currently in demand charge period."""
        now = datetime.now()
        now_time = now.time()

        # Get config
        start_time_str = self._entry.data.get(CONF_DEMAND_CHARGE_START_TIME, "16:00:00")
        end_time_str = self._entry.data.get(CONF_DEMAND_CHARGE_END_TIME, "23:00:00")
        days_setting = self._entry.data.get(CONF_DEMAND_CHARGE_DAYS, "All Days")

        # Parse times
        start_time = datetime.strptime(start_time_str, "%H:%M:%S").time()
        end_time = datetime.strptime(end_time_str, "%H:%M:%S").time()

        # Check day criteria
        is_weekday = now.weekday() < 5
        if days_setting == "Weekdays Only" and not is_weekday:
            return False
        if days_setting == "Weekends Only" and is_weekday:
            return False

        # Check time criteria
        if start_time < end_time:
            time_match = start_time <= now_time < end_time
        else:
            # Handles periods crossing midnight
            time_match = now_time >= start_time or now_time < end_time

        return time_match

    def _get_days_until_reset(self) -> int:
        """Calculate days until billing cycle reset."""
        billing_day = self._entry.data.get(CONF_DEMAND_CHARGE_BILLING_DAY, 1)
        now = datetime.now()
        today = now.day

        if today < billing_day:
            return billing_day - today
        else:
            # Calculate next month's billing day
            if now.month == 12:
                next_month = now.replace(year=now.year + 1, month=1, day=billing_day)
            else:
                next_month = now.replace(month=now.month + 1, day=billing_day)
            return (next_month.date() - now.date()).days

    def _check_and_reset_peak(self) -> None:
        """Reset peak demand if billing cycle has rolled over."""
        billing_day = self._entry.data.get(CONF_DEMAND_CHARGE_BILLING_DAY, 1)
        now = datetime.now()

        # Reset on billing day or if month changed
        if now.day == billing_day or now.month != self._last_reset_month:
            _LOGGER.info(f"Resetting peak demand (was {self._peak_demand:.2f} kW)")
            self._peak_demand = 0.0
            self._peak_timestamp = None
            self._last_reset_month = now.month

    @property
    def native_value(self) -> Any:
        """Return the state of the sensor."""
        # Handle simple value functions
        if self.entity_description.value_fn:
            return self.entity_description.value_fn(self.coordinator.data)

        # Check for billing cycle reset
        self._check_and_reset_peak()

        # Handle different sensor types
        key = self.entity_description.key

        if key == SENSOR_TYPE_IN_DEMAND_CHARGE_PERIOD:
            return self._is_in_demand_period()

        elif key == SENSOR_TYPE_PEAK_DEMAND_THIS_CYCLE:
            # Update peak if in demand period
            if self._is_in_demand_period():
                grid_power = self.coordinator.data.get("grid_power", 0) if self.coordinator.data else 0
                grid_import = max(0, grid_power)  # Only positive (import) values

                if grid_import > self._peak_demand:
                    self._peak_demand = grid_import
                    self._peak_timestamp = datetime.now()
                    _LOGGER.info(f"New peak demand: {self._peak_demand:.2f} kW")

            return round(self._peak_demand, 3)

        elif key == SENSOR_TYPE_DEMAND_CHARGE_COST:
            rate = self._entry.data.get(CONF_DEMAND_CHARGE_RATE, 0.2162)
            return round(self._peak_demand * rate, 2)

        elif key == SENSOR_TYPE_DAYS_UNTIL_DEMAND_RESET:
            return self._get_days_until_reset()

        return None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Return additional attributes."""
        attributes = {}

        if self.entity_description.key == SENSOR_TYPE_PEAK_DEMAND_THIS_CYCLE:
            if self._peak_timestamp:
                attributes["timestamp"] = self._peak_timestamp.isoformat()
            attributes["peak_kw"] = self._peak_demand

        elif self.entity_description.key == SENSOR_TYPE_DEMAND_CHARGE_COST:
            rate = self._entry.data.get(CONF_DEMAND_CHARGE_RATE, 0.2162)
            attributes["peak_kw"] = self._peak_demand
            attributes["rate"] = rate

        return attributes
