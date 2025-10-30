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


async def get_tesla_api_client(hass: HomeAssistant):
    """Get the Tesla API client from the Tesla Fleet integration."""
    try:
        # Get the Tesla Fleet config entry
        tesla_entries = hass.config_entries.async_entries("tesla_fleet")
        _LOGGER.debug("Found %d Tesla Fleet entries", len(tesla_entries))

        if not tesla_entries:
            _LOGGER.error("No Tesla Fleet integration found")
            return None

        # Get the first entry (assuming single Tesla account)
        tesla_entry = tesla_entries[0]
        _LOGGER.debug("Tesla Fleet entry ID: %s", tesla_entry.entry_id)

        # Log what's in hass.data
        _LOGGER.debug("Keys in hass.data: %s", list(hass.data.keys()))

        # Try to get the API from the Tesla Fleet integration data
        if "tesla_fleet" in hass.data:
            tesla_data = hass.data["tesla_fleet"]
            _LOGGER.debug("Tesla Fleet data keys: %s", list(tesla_data.keys()) if isinstance(tesla_data, dict) else "not a dict")

            # Try different possible storage locations
            if tesla_entry.entry_id in tesla_data:
                entry_data = tesla_data[tesla_entry.entry_id]

                # Log what we found to help debug
                _LOGGER.info("Tesla Fleet entry_data type: %s", type(entry_data))
                if hasattr(entry_data, "__dict__"):
                    _LOGGER.info("Tesla Fleet entry_data dict: %s", entry_data.__dict__.keys())
                _LOGGER.info("Tesla Fleet entry_data attributes: %s", [attr for attr in dir(entry_data) if not attr.startswith("_")])

                # Look for the TeslaFleetApi object
                if hasattr(entry_data, "api"):
                    _LOGGER.info("Found API client at entry_data.api")
                    return entry_data.api
                elif hasattr(entry_data, "coordinator"):
                    coordinator = entry_data.coordinator
                    _LOGGER.info("Found coordinator, type: %s", type(coordinator))
                    if hasattr(coordinator, "api"):
                        _LOGGER.info("Found API client at coordinator.api")
                        return coordinator.api
                elif isinstance(entry_data, dict) and "api" in entry_data:
                    _LOGGER.info("Found API client in dict")
                    return entry_data["api"]
            else:
                _LOGGER.error("Entry ID %s not found in tesla_fleet data", tesla_entry.entry_id)
        else:
            _LOGGER.error("'tesla_fleet' key not found in hass.data")

        _LOGGER.error("Could not find Tesla API client in integration data")
        return None

    except Exception as err:
        _LOGGER.exception("Error getting Tesla API client: %s", err)
        return None


async def send_tariff_to_tesla(
    hass: HomeAssistant,
    site_id: str,
    tariff_data: dict[str, Any],
) -> bool:
    """Send tariff data to Tesla Fleet API."""
    # Try to get the API client from Tesla Fleet integration
    api_client = await get_tesla_api_client(hass)

    if api_client:
        try:
            _LOGGER.debug("Using Tesla Fleet API client to sync TOU schedule")
            _LOGGER.debug("Tariff data: %s", tariff_data)

            # Use the Tesla Fleet API client
            # The api_client should have methods like energy_sites()
            result = await api_client.energy_sites.time_of_use_settings(
                site_id,
                tariff_data
            )

            _LOGGER.info("Successfully synced TOU schedule to Tesla via API client")
            _LOGGER.debug("Tesla API response: %s", result)
            return True

        except AttributeError as err:
            _LOGGER.warning(
                "Tesla API client doesn't have expected structure, falling back to direct HTTP: %s",
                err
            )
            # Fall through to direct HTTP method below
        except Exception as err:
            _LOGGER.error("Error using Tesla API client: %s", err)
            return False

    # Fallback: Direct HTTP API call
    # This requires getting a token somehow - for now, log an error
    _LOGGER.error(
        "Cannot sync TOU: No Tesla API client available. "
        "The Tesla Fleet integration may need to be reconfigured."
    )
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
