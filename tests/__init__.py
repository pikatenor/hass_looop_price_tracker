"""Tests for the Looop Denki integration."""

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.looop_denki.const import CONF_AREA_CODE, DOMAIN


async def setup_integration(hass: HomeAssistant) -> ConfigEntry:
    """Set up the Looop Denki integration for testing."""
    config_entry = MockConfigEntry(
        domain=DOMAIN,
        data={CONF_AREA_CODE: "03"},
        title="Looop でんき - 東京電力",
    )
    config_entry.add_to_hass(hass)

    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    return config_entry
