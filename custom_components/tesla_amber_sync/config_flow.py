"""Config flow for Tesla Amber Sync integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers import selector
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import device_registry as dr
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_AMBER_API_TOKEN,
    CONF_AMBER_SITE_ID,
    CONF_TESLA_SITE_ID,
    CONF_AUTO_SYNC_ENABLED,
    AMBER_API_BASE_URL,
)

_LOGGER = logging.getLogger(__name__)


async def validate_amber_token(hass: HomeAssistant, api_token: str) -> dict[str, Any]:
    """Validate the Amber API token."""
    session = async_get_clientsession(hass)
    headers = {"Authorization": f"Bearer {api_token}"}

    try:
        async with session.get(
            f"{AMBER_API_BASE_URL}/sites",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=10),
        ) as response:
            if response.status == 200:
                sites = await response.json()
                if sites and len(sites) > 0:
                    return {
                        "success": True,
                        "sites": sites,
                    }
                else:
                    return {"success": False, "error": "no_sites"}
            elif response.status == 401:
                return {"success": False, "error": "invalid_auth"}
            else:
                return {"success": False, "error": "cannot_connect"}
    except aiohttp.ClientError:
        return {"success": False, "error": "cannot_connect"}
    except Exception as err:
        _LOGGER.exception("Unexpected error validating Amber token: %s", err)
        return {"success": False, "error": "unknown"}


async def get_tesla_sites(hass: HomeAssistant) -> list[dict[str, Any]]:
    """Get list of Tesla energy sites from the Tesla Fleet integration."""
    tesla_sites = []
    seen_site_ids = set()  # Track by site_id to avoid duplicates

    # Look for Tesla Fleet devices
    device_registry = dr.async_get(hass)
    entity_registry = er.async_get(hass)

    _LOGGER.info("Searching for Tesla Fleet energy sites...")

    # Iterate through all devices
    for device in device_registry.devices.values():
        # Only look at tesla_fleet integration devices
        if not any(integration_domain == "tesla_fleet" for integration_domain, _ in device.identifiers):
            continue

        # Look for energy site identifier
        energy_site_id = None
        for integration_domain, identifier in device.identifiers:
            if integration_domain == "tesla_fleet":
                # The identifier is the site ID for energy sites
                # Check if this device has any energy-related entities
                has_energy_entities = False
                for entity in entity_registry.entities.values():
                    if entity.device_id == device.id and entity.platform == "tesla_fleet":
                        # Check if it's an energy sensor
                        if any(keyword in (entity.unique_id or "").lower() for keyword in [
                            "solar", "battery", "grid", "load", "percentage_charged"
                        ]):
                            has_energy_entities = True
                            energy_site_id = identifier
                            break

                if has_energy_entities:
                    break

        if energy_site_id and energy_site_id not in seen_site_ids:
            device_name = device.name or "Tesla Energy Site"

            _LOGGER.info(f"Found Tesla energy site: {device_name} (ID: {energy_site_id})")

            tesla_sites.append({
                "id": energy_site_id,
                "name": f"{device_name} ({energy_site_id[:12]}...)" if len(energy_site_id) > 12 else f"{device_name} ({energy_site_id})",
            })
            seen_site_ids.add(energy_site_id)

    _LOGGER.info(f"Discovered {len(tesla_sites)} Tesla energy site(s) from Tesla Fleet")
    return tesla_sites


class TeslaAmberSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tesla Amber Sync."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._amber_data: dict[str, Any] = {}
        self._amber_sites: list[dict[str, Any]] = []

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step - check for Tesla Fleet integration."""
        # Check if Tesla Fleet integration is configured
        if "tesla_fleet" not in self.hass.config.components:
            return self.async_abort(reason="tesla_fleet_required")

        # Check if already configured
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return await self.async_step_amber()

    async def async_step_amber(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Amber API token entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate Amber API token
            validation_result = await validate_amber_token(
                self.hass, user_input[CONF_AMBER_API_TOKEN]
            )

            if validation_result["success"]:
                self._amber_data = user_input
                self._amber_sites = validation_result.get("sites", [])
                return await self.async_step_site_selection()
            else:
                errors["base"] = validation_result.get("error", "unknown")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_AMBER_API_TOKEN): str,
            }
        )

        return self.async_show_form(
            step_id="amber",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "amber_url": "https://app.amber.com.au/developers",
            },
        )

    async def async_step_site_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle site selection for both Amber and Tesla."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Combine all data
            data = {
                **self._amber_data,
                CONF_AMBER_SITE_ID: user_input.get(CONF_AMBER_SITE_ID),
                CONF_TESLA_SITE_ID: user_input[CONF_TESLA_SITE_ID],
                CONF_AUTO_SYNC_ENABLED: user_input.get(CONF_AUTO_SYNC_ENABLED, True),
            }

            return self.async_create_entry(title="Tesla Amber Sync", data=data)

        # Get Tesla sites
        tesla_sites = await get_tesla_sites(self.hass)

        # Build selection options
        amber_site_options = {
            site["id"]: site.get("nmi", site["id"])
            for site in self._amber_sites
        }

        data_schema_dict: dict[vol.Marker, Any] = {}

        if tesla_sites:
            # Auto-discovered sites - show dropdown
            tesla_site_options = {site["id"]: site["name"] for site in tesla_sites}
            data_schema_dict[vol.Required(CONF_TESLA_SITE_ID)] = vol.In(tesla_site_options)
        else:
            # No sites found - allow manual entry
            _LOGGER.warning(
                "No Tesla Fleet energy sites auto-discovered. "
                "Please enter your Tesla energy site ID manually. "
                "You can find this in the Tesla Fleet integration or Tesla app."
            )
            data_schema_dict[vol.Required(CONF_TESLA_SITE_ID)] = str

        # Only add Amber site selection if multiple sites
        if len(self._amber_sites) > 1:
            data_schema_dict[vol.Required(CONF_AMBER_SITE_ID)] = vol.In(
                amber_site_options
            )

        data_schema_dict[vol.Optional(CONF_AUTO_SYNC_ENABLED, default=True)] = bool

        data_schema = vol.Schema(data_schema_dict)

        return self.async_show_form(
            step_id="site_selection",
            data_schema=data_schema,
            errors=errors,
        )

    @staticmethod
    @callback
    def async_get_options_flow(
        config_entry: config_entries.ConfigEntry,
    ) -> TeslaAmberSyncOptionsFlow:
        """Get the options flow for this handler."""
        return TeslaAmberSyncOptionsFlow(config_entry)


class TeslaAmberSyncOptionsFlow(config_entries.OptionsFlow):
    """Handle options flow for Tesla Amber Sync."""

    def __init__(self, config_entry: config_entries.ConfigEntry) -> None:
        """Initialize options flow."""
        self.config_entry = config_entry

    async def async_step_init(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Manage the options."""
        if user_input is not None:
            return self.async_create_entry(title="", data=user_input)

        return self.async_show_form(
            step_id="init",
            data_schema=vol.Schema(
                {
                    vol.Optional(
                        CONF_AUTO_SYNC_ENABLED,
                        default=self.config_entry.options.get(
                            CONF_AUTO_SYNC_ENABLED, True
                        ),
                    ): bool,
                }
            ),
        )
