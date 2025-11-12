"""The Tesla Sync integration."""
from __future__ import annotations

import aiohttp
import asyncio
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.event import async_track_utc_time_change

from .const import (
    DOMAIN,
    CONF_AMBER_API_TOKEN,
    CONF_AMBER_FORECAST_TYPE,
    CONF_AUTO_SYNC_ENABLED,
    CONF_TESLEMETRY_API_TOKEN,
    CONF_TESLA_SITE_ID,
    SERVICE_SYNC_TOU,
    SERVICE_SYNC_NOW,
    TESLEMETRY_API_BASE_URL,
)
from .coordinator import (
    AmberPriceCoordinator,
    TeslaEnergyCoordinator,
)

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def send_tariff_to_tesla(
    hass: HomeAssistant,
    site_id: str,
    tariff_data: dict[str, Any],
    api_token: str,
    max_retries: int = 3,
    timeout_seconds: int = 60,
) -> bool:
    """Send tariff data to Tesla via Teslemetry API with retry logic.

    Args:
        hass: HomeAssistant instance
        site_id: Tesla energy site ID
        tariff_data: Tariff data to send
        api_token: Teslemetry API token
        max_retries: Maximum number of retry attempts (default: 3)
        timeout_seconds: Request timeout in seconds (default: 60)

    Returns:
        True if successful, False otherwise
    """
    session = async_get_clientsession(hass)
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    payload = {
        "tou_settings": {
            "tariff_content_v2": tariff_data
        }
    }

    url = f"{TESLEMETRY_API_BASE_URL}/api/1/energy_sites/{site_id}/time_of_use_settings"
    last_error = None

    for attempt in range(max_retries):
        try:
            # Exponential backoff: 2^attempt seconds (1s, 2s, 4s)
            if attempt > 0:
                wait_time = 2 ** attempt
                _LOGGER.info(
                    "TOU sync retry attempt %d/%d after %ds delay",
                    attempt + 1,
                    max_retries,
                    wait_time
                )
                await asyncio.sleep(wait_time)

            _LOGGER.debug(
                "Sending TOU schedule to Teslemetry API for site %s (attempt %d/%d)",
                site_id,
                attempt + 1,
                max_retries
            )

            async with session.post(
                url,
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=timeout_seconds),
            ) as response:
                if response.status == 200:
                    result = await response.json()
                    _LOGGER.info(
                        "Successfully synced TOU schedule to Tesla (attempt %d/%d)",
                        attempt + 1,
                        max_retries
                    )
                    _LOGGER.debug("Tesla API response: %s", result)
                    return True

                # Log error and potentially retry
                error_text = await response.text()

                if response.status >= 500:
                    # Server error - retry
                    _LOGGER.warning(
                        "Failed to sync TOU schedule: %s - %s (attempt %d/%d, will retry)",
                        response.status,
                        error_text[:200],
                        attempt + 1,
                        max_retries
                    )
                    last_error = f"Server error {response.status}"
                    continue  # Retry on 5xx errors
                else:
                    # Client error - don't retry
                    _LOGGER.error(
                        "Failed to sync TOU schedule: %s - %s (client error, not retrying)",
                        response.status,
                        error_text
                    )
                    return False

        except aiohttp.ClientError as err:
            _LOGGER.warning(
                "Error communicating with Teslemetry API (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                err
            )
            last_error = f"Network error: {err}"
            continue  # Retry on network errors

        except asyncio.TimeoutError:
            _LOGGER.warning(
                "Teslemetry API timeout after %ds (attempt %d/%d)",
                timeout_seconds,
                attempt + 1,
                max_retries
            )
            last_error = f"Timeout after {timeout_seconds}s"
            continue  # Retry on timeout

        except Exception as err:
            _LOGGER.exception(
                "Unexpected error syncing TOU schedule (attempt %d/%d): %s",
                attempt + 1,
                max_retries,
                err
            )
            last_error = f"Unexpected error: {err}"
            # Don't continue - unexpected errors might indicate a bug
            return False

    # All retries failed
    _LOGGER.error(
        "Failed to sync TOU schedule after %d attempts. Last error: %s",
        max_retries,
        last_error
    )
    return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tesla Sync from a config entry."""
    _LOGGER.info("Setting up Tesla Sync integration")

    # Initialize coordinators for data fetching
    amber_coordinator = AmberPriceCoordinator(
        hass,
        entry.data[CONF_AMBER_API_TOKEN],
        entry.data.get("amber_site_id"),
    )

    tesla_coordinator = TeslaEnergyCoordinator(
        hass,
        entry.data[CONF_TESLA_SITE_ID],
        entry.data[CONF_TESLEMETRY_API_TOKEN],
    )

    # Fetch initial data
    await amber_coordinator.async_config_entry_first_refresh()
    await tesla_coordinator.async_config_entry_first_refresh()

    # Store coordinators in hass.data
    hass.data.setdefault(DOMAIN, {})
    hass.data[DOMAIN][entry.entry_id] = {
        "amber_coordinator": amber_coordinator,
        "tesla_coordinator": tesla_coordinator,
        "entry": entry,
        "auto_sync_cancel": None,  # Will store the timer cancel function
    }

    # Set up platforms
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    # Register services
    async def handle_sync_tou(call: ServiceCall) -> None:
        """Handle the sync TOU schedule service call."""
        _LOGGER.info("Manual TOU sync requested")

        # Get latest Amber prices
        await amber_coordinator.async_request_refresh()

        if not amber_coordinator.data:
            _LOGGER.error("No Amber price data available")
            return

        # Import tariff converter from existing code
        from .tariff_converter import convert_amber_to_tesla_tariff

        # Get forecast type from options (if set) or data (from initial config)
        forecast_type = entry.options.get(
            CONF_AMBER_FORECAST_TYPE,
            entry.data.get(CONF_AMBER_FORECAST_TYPE, "predicted")
        )
        _LOGGER.info(f"Using Amber forecast type: {forecast_type}")

        # Fetch Powerwall timezone from site_info
        # This ensures correct timezone handling for TOU schedule alignment
        powerwall_timezone = None
        site_info = await tesla_coordinator.async_get_site_info()
        if site_info:
            powerwall_timezone = site_info.get("installation_time_zone")
            if powerwall_timezone:
                _LOGGER.info(f"Using Powerwall timezone: {powerwall_timezone}")
            else:
                _LOGGER.warning("No installation_time_zone in site_info, will auto-detect from Amber data")
        else:
            _LOGGER.warning("Failed to fetch site_info, will auto-detect timezone from Amber data")

        # Convert prices to Tesla tariff format
        tariff = convert_amber_to_tesla_tariff(
            amber_coordinator.data.get("forecast", []),
            tesla_site_id=entry.data[CONF_TESLA_SITE_ID],
            forecast_type=forecast_type,
            powerwall_timezone=powerwall_timezone,
        )

        if not tariff:
            _LOGGER.error("Failed to convert Amber prices to Tesla tariff")
            return

        # Send tariff to Tesla via Teslemetry API
        success = await send_tariff_to_tesla(
            hass,
            entry.data[CONF_TESLA_SITE_ID],
            tariff,
            entry.data[CONF_TESLEMETRY_API_TOKEN],
        )

        if success:
            _LOGGER.info("TOU schedule synced successfully")
        else:
            _LOGGER.error("Failed to sync TOU schedule")

    async def handle_sync_now(call: ServiceCall) -> None:
        """Handle the sync now service call."""
        _LOGGER.info("Immediate data refresh requested")
        await amber_coordinator.async_request_refresh()
        await tesla_coordinator.async_request_refresh()

    hass.services.async_register(DOMAIN, SERVICE_SYNC_TOU, handle_sync_tou)
    hass.services.async_register(DOMAIN, SERVICE_SYNC_NOW, handle_sync_now)

    # Set up automatic TOU sync every 5 minutes if auto-sync is enabled
    async def auto_sync_tou(now):
        """Automatically sync TOU schedule if enabled."""
        # Check if auto-sync is enabled in the config entry options
        auto_sync_enabled = entry.options.get(
            CONF_AUTO_SYNC_ENABLED,
            entry.data.get(CONF_AUTO_SYNC_ENABLED, True)
        )

        _LOGGER.debug(
            "Auto-sync check: options=%s, data=%s, enabled=%s",
            entry.options.get(CONF_AUTO_SYNC_ENABLED),
            entry.data.get(CONF_AUTO_SYNC_ENABLED),
            auto_sync_enabled
        )

        if auto_sync_enabled:
            _LOGGER.debug("Auto-sync enabled, triggering TOU sync")
            await handle_sync_tou(None)
        else:
            _LOGGER.debug("Auto-sync disabled, skipping TOU sync")

    # Perform initial TOU sync if auto-sync is enabled
    auto_sync_enabled = entry.options.get(
        CONF_AUTO_SYNC_ENABLED,
        entry.data.get(CONF_AUTO_SYNC_ENABLED, True)
    )

    if auto_sync_enabled:
        _LOGGER.info("Performing initial TOU sync")
        await handle_sync_tou(None)

    # Start the automatic sync timer (every 5 minutes, aligned to clock)
    # Triggers at :00, :05, :10, :15, :20, :25, :30, :35, :40, :45, :50, :55
    cancel_timer = async_track_utc_time_change(
        hass,
        auto_sync_tou,
        minute=[0, 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 55],
        second=0,
    )

    # Store the cancel function so we can clean it up later
    hass.data[DOMAIN][entry.entry_id]["auto_sync_cancel"] = cancel_timer

    _LOGGER.info("Tesla Sync integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Tesla Sync integration")

    # Cancel the auto-sync timer if it exists
    entry_data = hass.data[DOMAIN].get(entry.entry_id, {})
    if cancel_timer := entry_data.get("auto_sync_cancel"):
        cancel_timer()
        _LOGGER.debug("Cancelled auto-sync timer")

    # Unload platforms
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)

    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id)

    # Remove services if this is the last entry
    if not hass.data[DOMAIN]:
        hass.services.async_remove(DOMAIN, SERVICE_SYNC_TOU)
        hass.services.async_remove(DOMAIN, SERVICE_SYNC_NOW)

    return unload_ok


async def async_reload_entry(hass: HomeAssistant, entry: ConfigEntry) -> None:
    """Reload config entry."""
    await async_unload_entry(hass, entry)
    await async_setup_entry(hass, entry)
