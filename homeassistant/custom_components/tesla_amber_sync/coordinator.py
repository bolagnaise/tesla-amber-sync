"""Data update coordinators for Tesla Amber Sync."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.util import dt as dt_util

from .const import (
    DOMAIN,
    UPDATE_INTERVAL_PRICES,
    UPDATE_INTERVAL_ENERGY,
    AMBER_API_BASE_URL,
    TESLEMETRY_API_BASE_URL,
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
                f"{AMBER_API_BASE_URL}/sites/{self.site_id}/prices/current",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    raise UpdateFailed(f"Error fetching current prices: {response.status}")
                current_prices = await response.json()

            # Get price forecast (next 48 hours)
            async with self.session.get(
                f"{AMBER_API_BASE_URL}/sites/{self.site_id}/prices",
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
    """Coordinator to fetch Tesla energy data from Teslemetry API."""

    def __init__(
        self,
        hass: HomeAssistant,
        site_id: str,
        api_token: str,
    ) -> None:
        """Initialize the coordinator."""
        self.site_id = site_id
        self.api_token = api_token
        self.session = async_get_clientsession(hass)

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_tesla_energy",
            update_interval=UPDATE_INTERVAL_ENERGY,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Teslemetry API."""
        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            # Get live status from Teslemetry API
            async with self.session.get(
                f"{TESLEMETRY_API_BASE_URL}/api/1/energy_sites/{self.site_id}/live_status",
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise UpdateFailed(
                        f"Error fetching Tesla energy data: {response.status} - {error_text}"
                    )

                data = await response.json()
                live_status = data.get("response", {})

                _LOGGER.debug("Teslemetry live_status response: %s", live_status)

                # Map Teslemetry API response to our data structure
                energy_data = {
                    "solar_power": live_status.get("solar_power", 0) / 1000,  # Convert W to kW
                    "grid_power": live_status.get("grid_power", 0) / 1000,
                    "battery_power": live_status.get("battery_power", 0) / 1000,
                    "load_power": live_status.get("load_power", 0) / 1000,
                    "battery_level": live_status.get("percentage_charged", 0),
                    "last_update": dt_util.utcnow(),
                }

                return energy_data

        except aiohttp.ClientError as err:
            raise UpdateFailed(f"Error communicating with Teslemetry API: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching Tesla energy data: {err}") from err
