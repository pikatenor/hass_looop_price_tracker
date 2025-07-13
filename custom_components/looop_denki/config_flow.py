"""Config flow for the Looop Denki integration."""

from __future__ import annotations

import logging
from typing import Any

import voluptuous as vol
from homeassistant.config_entries import ConfigFlow, ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError

from .api import LooopDenkiApiClient, LooopDenkiApiError
from .const import CONF_AREA_CODE, DOMAIN

_LOGGER = logging.getLogger(__name__)

STEP_USER_DATA_SCHEMA = vol.Schema(
    {
        vol.Required(CONF_AREA_CODE): vol.In(LooopDenkiApiClient.get_area_codes()),
    }
)


async def validate_input(hass: HomeAssistant, data: dict[str, Any]) -> dict[str, Any]:
    """
    Validate the user input allows us to connect.

    Data has the keys from STEP_USER_DATA_SCHEMA with values provided by the user.
    """
    area_code = data[CONF_AREA_CODE]

    client = LooopDenkiApiClient(area_code)

    try:
        if not await client.test_connection():
            raise CannotConnectError
    except LooopDenkiApiError as err:
        _LOGGER.exception("Failed to connect to Looop Denki API")
        raise CannotConnectError from err
    finally:
        await client.close()

    area_names = LooopDenkiApiClient.get_area_codes()
    area_name = area_names.get(area_code, f"Area {area_code}")

    return {"title": f"Looop でんき - {area_name}"}


class ConfigFlow(ConfigFlow, domain=DOMAIN):
    """Handle a config flow for Looop Denki."""

    VERSION = 1

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle the initial step."""
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                info = await validate_input(self.hass, user_input)
            except CannotConnectError:
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected exception")
                errors["base"] = "unknown"
            else:
                return self.async_create_entry(title=info["title"], data=user_input)

        return self.async_show_form(
            step_id="user", data_schema=STEP_USER_DATA_SCHEMA, errors=errors
        )


class CannotConnectError(HomeAssistantError):
    """Error to indicate we cannot connect."""
