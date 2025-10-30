"""Data update coordinators for Tesla Amber Sync."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    UPDATE_INTERVAL_PRICES,
    UPDATE_INTERVAL_ENERGY,
    AMBER_API_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)


class AmberPriceCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Amber electricity price data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_token: str,
        site_id: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        self.api_token = api_token
        self.site_id = site_id
        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_amber_prices",
            update_interval=UPDATE_INTERVAL_PRICES,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Amber API."""
        headers = {"Authorization": f"Bearer {self.api_token}"}

        try:
            # Get current prices
            async with self.session.get(
                f"{AMBER_API_BASE_URL}/sites/{self.site_id or ''}/prices/current",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Error fetching current prices: {response.status}")
                current_prices = await response.json()

            # Get price forecast (next 48 hours)
            async with self.session.get(
                f"{AMBER_API_BASE_URL}/sites/{self.site_id or ''}/prices",
                headers=headers,
                params={"next": 48},
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Error fetching price forecast: {response.status}")
                forecast_prices = await response.json()

            return {
                "current": current_prices,
                "forecast": forecast_prices,
                "last_update": dt_util.utcnow(),
            }

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with Amber API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching Amber data: {err}") from err


class TeslaEnergyCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Tesla energy data from Tesla Fleet integration."""

    def __init__(
        self,
        hass: HomeAssistant,
        site_id: str,
    ) -> None:
        """Initialize the coordinator."""
        self.site_id = site_id

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_tesla_energy",
            update_interval=UPDATE_INTERVAL_ENERGY,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Tesla Fleet integration entities."""
        try:
            # Get entity registry to find Tesla entities
            entity_registry = er.async_get(self.hass)

            energy_data: dict[str, Any] = {}

            _LOGGER.debug("Looking for Tesla Fleet entities for site: %s", self.site_id)

            found_entities = 0
            # Look for Tesla Fleet sensor entities related to this site
            for entity in entity_registry.entities.values():
                if (
                    entity.platform == "tesla_fleet"
                    and entity.domain == "sensor"
                    and self.site_id in entity.unique_id
                ):
                    found_entities += 1
                    _LOGGER.debug(
                        "Found matching entity: %s (unique_id: %s)",
                        entity.entity_id,
                        entity.unique_id
                    )

                    # Get the current state
                    state = self.hass.states.get(entity.entity_id)
                    if state:
                        _LOGGER.debug(
                            "Entity %s state: %s",
                            entity.entity_id,
                            state.state
                        )

                        # Map entity types to our data structure
                        if "solar_power" in entity.unique_id:
                            energy_data["solar_power"] = float(state.state) if state.state not in ("unknown", "unavailable") else 0.0
                        elif "grid_power" in entity.unique_id:
                            energy_data["grid_power"] = float(state.state) if state.state not in ("unknown", "unavailable") else 0.0
                        elif "battery_power" in entity.unique_id:
                            energy_data["battery_power"] = float(state.state) if state.state not in ("unknown", "unavailable") else 0.0
                        elif "load_power" in entity.unique_id or "home_load" in entity.unique_id:
                            energy_data["load_power"] = float(state.state) if state.state not in ("unknown", "unavailable") else 0.0
                        elif "battery_level" in entity.unique_id or "percentage_charged" in entity.unique_id:
                            energy_data["battery_level"] = float(state.state) if state.state not in ("unknown", "unavailable") else 0.0
                    else:
                        _LOGGER.debug("Entity %s has no state", entity.entity_id)

            _LOGGER.debug(
                "Found %d matching Tesla Fleet entities, extracted data: %s",
                found_entities,
                energy_data
            )

            # If we didn't get data from entities, try to get it from the live status
            if not energy_data:
                _LOGGER.warning(
                    "No Tesla Fleet entities found for site %s. Make sure Tesla Fleet integration is configured.",
                    self.site_id,
                )

            energy_data["last_update"] = dt_util.utcnow()
            return energy_data

        except Exception as err:
            raise UpdateFailed(f"Error fetching Tesla energy data: {err}") from err
