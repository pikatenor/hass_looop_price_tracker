"""The Looop Denki integration."""

from __future__ import annotations

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import LooopDenkiApiClient
from .const import CONF_AREA_CODE
from .coordinator import LooopDenkiCoordinator

_PLATFORMS: list[Platform] = [Platform.SENSOR]

type LooopDenkiConfigEntry = ConfigEntry[LooopDenkiCoordinator]


async def async_setup_entry(hass: HomeAssistant, entry: LooopDenkiConfigEntry) -> bool:
    """Set up Looop Denki from a config entry."""
    area_code = entry.data[CONF_AREA_CODE]
    session = async_get_clientsession(hass)

    client = LooopDenkiApiClient(area_code, session)
    coordinator = LooopDenkiCoordinator(hass, client)

    await coordinator.async_config_entry_first_refresh()

    entry.runtime_data = coordinator

    await hass.config_entries.async_forward_entry_setups(entry, _PLATFORMS)

    return True


async def async_unload_entry(hass: HomeAssistant, entry: LooopDenkiConfigEntry) -> bool:
    """Unload a config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, _PLATFORMS)

    if unload_ok:
        await entry.runtime_data.client.close()

    return unload_ok
