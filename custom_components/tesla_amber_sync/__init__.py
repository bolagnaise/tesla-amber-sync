"""The Tesla Amber Sync integration."""
from __future__ import annotations

import aiohttp
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_AMBER_API_TOKEN,
    CONF_TESLA_SITE_ID,
    SERVICE_SYNC_TOU,
    SERVICE_SYNC_NOW,
)
from .coordinator import (
    AmberPriceCoordinator,
    TeslaEnergyCoordinator,
)

_LOGGER = logging.getLogger(__name__)

TESLA_API_BASE_URL = "https://fleet-api.prd.na.vn.cloud.tesla.com"

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


async def get_tesla_access_token(hass: HomeAssistant) -> str | None:
    """Get the access token from the Tesla Fleet integration."""
    try:
        # Try to get the Tesla Fleet config entry
        tesla_entries = hass.config_entries.async_entries("tesla_fleet")
        if not tesla_entries:
            _LOGGER.error("No Tesla Fleet integration found")
            return None

        # Get the first entry (assuming single Tesla account)
        tesla_entry = tesla_entries[0]

        # Try to get the access token from the entry data
        if "tesla_fleet" in hass.data and tesla_entry.entry_id in hass.data["tesla_fleet"]:
            tesla_data = hass.data["tesla_fleet"][tesla_entry.entry_id]

            # The token might be in different places depending on implementation
            if hasattr(tesla_data, "coordinator"):
                coordinator = tesla_data.coordinator
                if hasattr(coordinator, "access_token"):
                    return coordinator.access_token
                if hasattr(coordinator, "token"):
                    return coordinator.token

            # Or it might be stored directly
            if isinstance(tesla_data, dict):
                return tesla_data.get("access_token") or tesla_data.get("token")

        _LOGGER.error("Could not find Tesla access token in integration data")
        return None

    except Exception as err:
        _LOGGER.error("Error getting Tesla access token: %s", err)
        return None


async def send_tariff_to_tesla(
    hass: HomeAssistant,
    site_id: str,
    tariff_data: dict[str, Any],
) -> bool:
    """Send tariff data to Tesla Fleet API."""
    access_token = await get_tesla_access_token(hass)
    if not access_token:
        _LOGGER.error("Cannot sync TOU: No Tesla access token available")
        return False

    session = async_get_clientsession(hass)
    url = f"{TESLA_API_BASE_URL}/api/1/energy_sites/{site_id}/time_of_use_settings"

    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    try:
        _LOGGER.debug("Sending TOU tariff to Tesla API: %s", url)
        async with session.post(
            url,
            json=tariff_data,
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 200:
                result = await response.json()
                _LOGGER.info("Successfully synced TOU schedule to Tesla")
                _LOGGER.debug("Tesla API response: %s", result)
                return True
            else:
                error_text = await response.text()
                _LOGGER.error(
                    "Failed to sync TOU schedule. Status: %s, Response: %s",
                    response.status,
                    error_text,
                )
                return False

    except aiohttp.ClientError as err:
        _LOGGER.error("Error communicating with Tesla API: %s", err)
        return False
    except Exception as err:
        _LOGGER.error("Unexpected error syncing TOU schedule: %s", err)
        return False


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Set up Tesla Amber Sync from a config entry."""
    _LOGGER.info("Setting up Tesla Amber Sync integration")

    # Ensure Tesla Fleet integration is available
    if "tesla_fleet" not in hass.config.components:
        _LOGGER.error("Tesla Fleet integration is not set up. Please configure it first.")
        raise ConfigEntryNotReady("Tesla Fleet integration not available")

    # Initialize coordinators for data fetching
    amber_coordinator = AmberPriceCoordinator(
        hass,
        entry.data[CONF_AMBER_API_TOKEN],
        entry.data.get("amber_site_id"),
    )

    tesla_coordinator = TeslaEnergyCoordinator(
        hass,
        entry.data[CONF_TESLA_SITE_ID],
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

        # Convert prices to Tesla tariff format
        tariff = convert_amber_to_tesla_tariff(
            amber_coordinator.data.get("forecast", []),
            tesla_site_id=entry.data[CONF_TESLA_SITE_ID],
        )

        if not tariff:
            _LOGGER.error("Failed to convert Amber prices to Tesla tariff")
            return

        # Send tariff to Tesla via API
        success = await send_tariff_to_tesla(
            hass,
            entry.data[CONF_TESLA_SITE_ID],
            tariff,
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

    _LOGGER.info("Tesla Amber Sync integration setup complete")
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload a config entry."""
    _LOGGER.info("Unloading Tesla Amber Sync integration")

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
