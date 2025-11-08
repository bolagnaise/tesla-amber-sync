"""Config flow for Tesla Amber Sync integration."""
from __future__ import annotations

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import HomeAssistant, callback
from homeassistant.data_entry_flow import FlowResult
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .const import (
    DOMAIN,
    CONF_AMBER_API_TOKEN,
    CONF_AMBER_SITE_ID,
    CONF_TESLEMETRY_API_TOKEN,
    CONF_TESLA_SITE_ID,
    CONF_AUTO_SYNC_ENABLED,
    CONF_DEMAND_CHARGE_ENABLED,
    CONF_DEMAND_CHARGE_RATE,
    CONF_DEMAND_CHARGE_START_TIME,
    CONF_DEMAND_CHARGE_END_TIME,
    CONF_DEMAND_CHARGE_DAYS,
    CONF_DEMAND_CHARGE_BILLING_DAY,
    AMBER_API_BASE_URL,
    TESLEMETRY_API_BASE_URL,
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


async def validate_teslemetry_token(
    hass: HomeAssistant, api_token: str
) -> dict[str, Any]:
    """Validate the Teslemetry API token and get sites."""
    session = async_get_clientsession(hass)
    headers = {
        "Authorization": f"Bearer {api_token}",
        "Content-Type": "application/json",
    }

    try:
        async with session.get(
            f"{TESLEMETRY_API_BASE_URL}/api/1/products",
            headers=headers,
            timeout=aiohttp.ClientTimeout(total=30),
        ) as response:
            if response.status == 200:
                data = await response.json()
                products = data.get("response", [])

                # Filter for energy sites
                energy_sites = [
                    p for p in products
                    if "energy_site_id" in p
                ]

                if energy_sites:
                    return {
                        "success": True,
                        "sites": energy_sites,
                    }
                else:
                    return {"success": False, "error": "no_energy_sites"}
            elif response.status == 401:
                return {"success": False, "error": "invalid_auth"}
            else:
                error_text = await response.text()
                _LOGGER.error("Teslemetry API error %s: %s", response.status, error_text)
                return {"success": False, "error": "cannot_connect"}
    except aiohttp.ClientError as err:
        _LOGGER.exception("Error connecting to Teslemetry API: %s", err)
        return {"success": False, "error": "cannot_connect"}
    except Exception as err:
        _LOGGER.exception("Unexpected error validating Teslemetry token: %s", err)
        return {"success": False, "error": "unknown"}


class TeslaAmberSyncConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Tesla Amber Sync."""

    VERSION = 1

    def __init__(self) -> None:
        """Initialize the config flow."""
        self._amber_data: dict[str, Any] = {}
        self._amber_sites: list[dict[str, Any]] = []
        self._teslemetry_data: dict[str, Any] = {}
        self._tesla_sites: list[dict[str, Any]] = []
        self._site_data: dict[str, Any] = {}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle the initial step."""
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
                return await self.async_step_teslemetry()
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

    async def async_step_teslemetry(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle Teslemetry API token entry."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # Validate Teslemetry API token
            validation_result = await validate_teslemetry_token(
                self.hass, user_input[CONF_TESLEMETRY_API_TOKEN]
            )

            if validation_result["success"]:
                self._teslemetry_data = user_input
                self._tesla_sites = validation_result.get("sites", [])
                return await self.async_step_site_selection()
            else:
                errors["base"] = validation_result.get("error", "unknown")

        data_schema = vol.Schema(
            {
                vol.Required(CONF_TESLEMETRY_API_TOKEN): str,
            }
        )

        return self.async_show_form(
            step_id="teslemetry",
            data_schema=data_schema,
            errors=errors,
            description_placeholders={
                "teslemetry_url": "https://teslemetry.com",
            },
        )

    async def async_step_site_selection(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle site selection for both Amber and Tesla."""
        errors: dict[str, str] = {}

        if user_input is not None:
            # If only one Amber site, use it automatically
            amber_site_id = user_input.get(CONF_AMBER_SITE_ID)
            if not amber_site_id and len(self._amber_sites) == 1:
                amber_site_id = self._amber_sites[0]["id"]
                _LOGGER.info(f"Auto-selected single Amber site: {amber_site_id}")

            # Store site selection data
            self._site_data = {
                CONF_AMBER_SITE_ID: amber_site_id,
                CONF_TESLA_SITE_ID: user_input[CONF_TESLA_SITE_ID],
                CONF_AUTO_SYNC_ENABLED: user_input.get(CONF_AUTO_SYNC_ENABLED, True),
            }

            # Go to optional demand charge configuration
            return await self.async_step_demand_charges()

        # Build selection options
        amber_site_options = {
            site["id"]: site.get("nmi", site["id"])
            for site in self._amber_sites
        }

        data_schema_dict: dict[vol.Marker, Any] = {}

        if self._tesla_sites:
            # Build Tesla site options from Teslemetry API response
            tesla_site_options = {}
            for site in self._tesla_sites:
                site_id = str(site.get("energy_site_id"))
                site_name = site.get("site_name", f"Tesla Energy Site {site_id}")
                tesla_site_options[site_id] = f"{site_name} ({site_id})"

            data_schema_dict[vol.Required(CONF_TESLA_SITE_ID)] = vol.In(tesla_site_options)
        else:
            # No sites found - should not happen if validation worked
            _LOGGER.error("No Tesla energy sites found in Teslemetry account")
            return self.async_abort(reason="no_energy_sites")

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

    async def async_step_demand_charges(
        self, user_input: dict[str, Any] | None = None
    ) -> FlowResult:
        """Handle optional demand charge configuration."""
        if user_input is not None:
            # Combine all data
            data = {
                **self._amber_data,
                **self._teslemetry_data,
                **self._site_data,
            }

            # Add demand charge configuration if enabled
            if user_input.get(CONF_DEMAND_CHARGE_ENABLED, False):
                data.update({
                    CONF_DEMAND_CHARGE_ENABLED: True,
                    CONF_DEMAND_CHARGE_RATE: user_input[CONF_DEMAND_CHARGE_RATE],
                    CONF_DEMAND_CHARGE_START_TIME: user_input[CONF_DEMAND_CHARGE_START_TIME],
                    CONF_DEMAND_CHARGE_END_TIME: user_input[CONF_DEMAND_CHARGE_END_TIME],
                    CONF_DEMAND_CHARGE_DAYS: user_input[CONF_DEMAND_CHARGE_DAYS],
                    CONF_DEMAND_CHARGE_BILLING_DAY: user_input[CONF_DEMAND_CHARGE_BILLING_DAY],
                })
            else:
                data[CONF_DEMAND_CHARGE_ENABLED] = False

            return self.async_create_entry(title="Tesla Amber Sync", data=data)

        # Build the form schema
        data_schema = vol.Schema(
            {
                vol.Optional(CONF_DEMAND_CHARGE_ENABLED, default=False): bool,
                vol.Optional(CONF_DEMAND_CHARGE_RATE, default=0.2162): vol.All(
                    vol.Coerce(float), vol.Range(min=0.0, max=50.0)
                ),
                vol.Optional(CONF_DEMAND_CHARGE_START_TIME, default="16:00:00"): str,
                vol.Optional(CONF_DEMAND_CHARGE_END_TIME, default="23:00:00"): str,
                vol.Optional(CONF_DEMAND_CHARGE_DAYS, default="All Days"): vol.In(
                    ["All Days", "Weekdays Only", "Weekends Only"]
                ),
                vol.Optional(CONF_DEMAND_CHARGE_BILLING_DAY, default=1): vol.All(
                    vol.Coerce(int), vol.Range(min=1, max=28)
                ),
            }
        )

        return self.async_show_form(
            step_id="demand_charges",
            data_schema=data_schema,
            description_placeholders={
                "example_rate": "0.2162",
                "example_time": "16:00:00",
            },
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
