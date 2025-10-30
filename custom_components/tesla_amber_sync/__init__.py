"""The Tesla Amber Sync integration."""
from __future__ import annotations

import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import device_registry as dr

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

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.SWITCH]


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

        # Call Tesla service to update tariff
        await hass.services.async_call(
            "tesla_fleet",
            "set_scheduled_charging",
            {
                "device_id": entry.data[CONF_TESLA_SITE_ID],
                "tariff": tariff,
            },
            blocking=True,
        )

        _LOGGER.info("TOU schedule synced successfully")

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
