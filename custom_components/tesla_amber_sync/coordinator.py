"""Data update coordinators for Tesla Sync with improved error handling."""
from __future__ import annotations

from datetime import datetime, timedelta
import logging
from typing import Any
import asyncio

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


async def _fetch_with_retry(
    session: aiohttp.ClientSession,
    url: str,
    headers: dict,
    max_retries: int = 3,
    timeout_seconds: int = 60,
    **kwargs
) -> dict[str, Any]:
    """Fetch data with exponential backoff retry logic.

    Args:
        session: aiohttp client session
        url: URL to fetch
        headers: Request headers
        max_retries: Maximum number of retry attempts (default: 3)
        timeout_seconds: Request timeout in seconds (default: 60)
        **kwargs: Additional arguments to pass to session.get()

    Returns:
        JSON response data

    Raises:
        UpdateFailed: If all retries fail
    """
    last_error = None

    for attempt in range(max_retries):
        try:
            # Exponential backoff: 2^attempt seconds (1s, 2s, 4s)
            if attempt > 0:
                wait_time = 2 ** attempt
                _LOGGER.info(f"Retry attempt {attempt + 1}/{max_retries} after {wait_time}s delay")
                await asyncio.sleep(wait_time)

            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout_seconds),
                **kwargs
            ) as response:
                if response.status == 200:
                    return await response.json()

                # Log the error but continue retrying on 5xx errors
                error_text = await response.text()

                if response.status >= 500:
                    _LOGGER.warning(
                        f"Server error (attempt {attempt + 1}/{max_retries}): {response.status} - {error_text[:200]}"
                    )
                    last_error = UpdateFailed(f"Server error: {response.status}")
                    continue  # Retry on 5xx errors
                else:
                    # Don't retry on 4xx client errors
                    raise UpdateFailed(f"Client error {response.status}: {error_text}")

        except aiohttp.ClientError as err:
            _LOGGER.warning(
                f"Network error (attempt {attempt + 1}/{max_retries}): {err}"
            )
            last_error = UpdateFailed(f"Network error: {err}")
            continue  # Retry on network errors

        except asyncio.TimeoutError:
            _LOGGER.warning(
                f"Timeout error (attempt {attempt + 1}/{max_retries}): Request exceeded {timeout_seconds}s"
            )
            last_error = UpdateFailed(f"Timeout after {timeout_seconds}s")
            continue  # Retry on timeout

    # All retries failed
    raise last_error or UpdateFailed("All retry attempts failed")


class AmberPriceCoordinator(DataUpdateCoordinator):
    """Coordinator to fetch Amber electricity price data."""

    def __init__(
        self,
        hass: HomeAssistant,
        api_token: str,
        site_id: str | None = None,
        ws_client=None,
    ) -> None:
        """Initialize the coordinator."""
        self.api_token = api_token
        self.site_id = site_id
        self.session = async_get_clientsession(hass)
        self.ws_client = ws_client  # WebSocket client for real-time prices

        super().__init__(
            hass,
            _LOGGER,
            name=f"{DOMAIN}_amber_prices",
            update_interval=UPDATE_INTERVAL_PRICES,
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Amber API with WebSocket-first approach."""
        headers = {"Authorization": f"Bearer {self.api_token}"}

        try:
            # Try WebSocket first for current prices (real-time, low latency)
            current_prices = None
            if self.ws_client:
                current_prices = self.ws_client.get_latest_prices(max_age_seconds=360)
                if current_prices:
                    _LOGGER.debug("Using WebSocket prices (fresh)")
                else:
                    _LOGGER.debug("WebSocket prices unavailable or stale, falling back to REST API")

            # Fall back to REST API if WebSocket unavailable
            if not current_prices:
                current_prices = await _fetch_with_retry(
                    self.session,
                    f"{AMBER_API_BASE_URL}/sites/{self.site_id}/prices/current",
                    headers,
                    max_retries=2,  # Less retries for Amber (usually more reliable)
                    timeout_seconds=30,
                )

            # Dual-resolution forecast approach to ensure complete data coverage:
            # 1. Fetch 1 hour at 5-min resolution for CurrentInterval/ActualInterval spike detection
            # 2. Fetch 48 hours at 30-min resolution for complete TOU schedule building
            # (The Amber API doesn't provide 48 hours of 5-min data, causing missing sell prices)

            # Step 1: Get 5-min resolution data for current period spike detection
            forecast_5min = await _fetch_with_retry(
                self.session,
                f"{AMBER_API_BASE_URL}/sites/{self.site_id}/prices",
                headers,
                params={"next": 1, "resolution": 5},
                max_retries=2,
                timeout_seconds=30,
            )

            # Step 2: Get 30-min resolution data for full 48-hour TOU schedule
            forecast_30min = await _fetch_with_retry(
                self.session,
                f"{AMBER_API_BASE_URL}/sites/{self.site_id}/prices",
                headers,
                params={"next": 48, "resolution": 30},
                max_retries=2,
                timeout_seconds=30,
            )

            return {
                "current": current_prices,
                "forecast": forecast_30min,  # Use 30-min forecast for TOU schedule
                "forecast_5min": forecast_5min,  # Keep 5-min for CurrentInterval extraction
                "last_update": dt_util.utcnow(),
            }

        except UpdateFailed:
            raise  # Re-raise UpdateFailed exceptions
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
        self._site_info_cache = None  # Cache site_info since timezone doesn't change

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
            # Get live status from Teslemetry API with retry logic
            # Teslemetry can be slow, so we use more retries and longer timeout
            data = await _fetch_with_retry(
                self.session,
                f"{TESLEMETRY_API_BASE_URL}/api/1/energy_sites/{self.site_id}/live_status",
                headers,
                max_retries=3,  # More retries for Teslemetry (can be unreliable)
                timeout_seconds=60,  # Longer timeout (was 30s)
            )

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

        except UpdateFailed:
            raise  # Re-raise UpdateFailed exceptions
        except Exception as err:
            raise UpdateFailed(f"Unexpected error fetching Tesla energy data: {err}") from err

    async def async_get_site_info(self) -> dict[str, Any] | None:
        """
        Fetch site_info from Teslemetry API.

        Includes installation_time_zone which is critical for correct TOU schedule alignment.
        Results are cached since site info (especially timezone) doesn't change.

        Returns:
            Site info dict containing installation_time_zone, or None if fetch fails
        """
        # Return cached value if available
        if self._site_info_cache:
            _LOGGER.debug("Returning cached site_info")
            return self._site_info_cache

        headers = {
            "Authorization": f"Bearer {self.api_token}",
            "Content-Type": "application/json",
        }

        try:
            _LOGGER.info(f"Fetching site_info for site {self.site_id}")

            data = await _fetch_with_retry(
                self.session,
                f"{TESLEMETRY_API_BASE_URL}/api/1/energy_sites/{self.site_id}/site_info",
                headers,
                max_retries=3,
                timeout_seconds=60,
            )

            site_info = data.get("response", {})

            # Log timezone info for debugging
            installation_tz = site_info.get("installation_time_zone")
            if installation_tz:
                _LOGGER.info(f"Found Powerwall timezone: {installation_tz}")
            else:
                _LOGGER.warning("No installation_time_zone in site_info response")

            # Cache the result
            self._site_info_cache = site_info

            return site_info

        except UpdateFailed as err:
            _LOGGER.error(f"Failed to fetch site_info: {err}")
            return None
        except Exception as err:
            _LOGGER.error(f"Unexpected error fetching site_info: {err}")
            return None
