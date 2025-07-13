"""Test the Looop Denki sensor platform."""

from unittest.mock import AsyncMock, patch

import pytest

from custom_components.looop_denki.const import DOMAIN
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

from . import setup_integration


@pytest.fixture
def mock_api_data():
    """Mock API data for testing."""
    return {
        "0": {  # Yesterday's data
            "price_data": [9.8, 11.2, 7.9, 14.5] * 12,  # 48 entries for 24 hours
            "level": [0, -0.5, 0, 0.5] * 12,
            "text": {
                str(i + 1): {
                    "price": (9.8, 11.2, 7.9, 14.5)[i % 4],
                    "level": (0, -0.5, 0, 0.5)[i % 4],
                }
                for i in range(48)
            },  # 1-based indexing
        },
        "1": {  # Today's data
            "price_data": [10.5, 12.3, 8.7, 15.2] * 12,  # 48 entries for 24 hours
            "level": [0, -0.5, 0, 0.5] * 12,
            "text": {
                str(i + 1): {
                    "price": (10.5, 12.3, 8.7, 15.2)[i % 4],
                    "level": (0, -0.5, 0, 0.5)[i % 4],
                }
                for i in range(48)
            },  # 1-based indexing
        },
        "2": {  # Tomorrow's data
            "price_data": [11.2, 13.1, 9.4, 16.0] * 12,
            "level": [0, -0.5, 0, 0.5] * 12,
            "text": {
                str(i + 1): {
                    "price": (11.2, 13.1, 9.4, 16.0)[i % 4],
                    "level": (0, -0.5, 0, 0.5)[i % 4],
                }
                for i in range(48)
            },  # 1-based indexing
        },
    }


async def test_sensor_setup(hass: HomeAssistant, mock_api_data) -> None:
    """Test sensor setup."""
    with (
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.async_get_prices",
            return_value=mock_api_data,
        ),
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.get_current_price_info",
            return_value={"current_price": 12.3},
        ),
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.get_next_price_info",
            return_value={"next_price": 13.1},
        ),
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.get_tomorrow_forecast_info",
            return_value={"data_available": True, "tomorrow_average": 14.5},
        ),
    ):
        await setup_integration(hass)

    entity_registry = er.async_get(hass)

    # Test current price sensor
    current_entity = entity_registry.async_get("sensor.current_price")
    assert current_entity
    assert current_entity.unique_id == "looop_denki_03_current_price"

    # Test additional sensors exist
    next_entity = entity_registry.async_get("sensor.next_price")
    assert next_entity
    assert next_entity.unique_id == "looop_denki_03_next_price"

    tomorrow_avg_entity = entity_registry.async_get("sensor.tomorrow_average_price")
    assert tomorrow_avg_entity
    assert tomorrow_avg_entity.unique_id == "looop_denki_03_tomorrow_average"


async def test_sensor_state(hass: HomeAssistant, mock_api_data) -> None:
    """Test sensor state."""
    with (
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.async_get_prices",
            return_value=mock_api_data,
        ),
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.get_current_price_info",
            return_value={
                "current_price": 12.3,
                "current_level": -0.5,
                "current_text": "Price: 12.3, Level: -0.5",
                "status": "でんき日和",
                "time_slot": 24,
                "hour": 12,
                "minute_range": "00-29",
            },
        ),
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.get_next_price_info",
            return_value={
                "next_price": 13.1,
                "next_status": "でんき注意報",
                "next_time_slot": 25,
            },
        ),
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.get_tomorrow_forecast_info",
            return_value={
                "data_available": True,
                "tomorrow_average": 14.5,
                "tomorrow_min": 8.7,
                "tomorrow_max": 20.2,
                "tomorrow_min_time": {"start": "03:00", "end": "03:29"},
                "tomorrow_max_time": {"start": "19:00", "end": "19:29"},
            },
        ),
    ):
        await setup_integration(hass)

    # Test current price sensor
    current_state = hass.states.get("sensor.current_price")
    assert current_state
    assert current_state.state == "12.3"
    assert current_state.attributes["current_level"] == -0.5
    assert current_state.attributes["current_text"] == "Price: 12.3, Level: -0.5"
    assert current_state.attributes["status"] == "でんき日和"
    assert current_state.attributes["time_slot"] == 24
    assert current_state.attributes["hour"] == 12
    assert current_state.attributes["minute_range"] == "00-29"

    # Test next price sensor
    next_state = hass.states.get("sensor.next_price")
    assert next_state
    assert next_state.state == "13.1"
    assert next_state.attributes["next_status"] == "でんき注意報"
    assert next_state.attributes["next_time_slot"] == 25

    # Test tomorrow average price sensor
    tomorrow_avg_state = hass.states.get("sensor.tomorrow_average_price")
    assert tomorrow_avg_state
    assert tomorrow_avg_state.state == "14.5"
    assert tomorrow_avg_state.attributes["data_available"] is True

    # Test tomorrow min price sensor
    tomorrow_min_state = hass.states.get("sensor.tomorrow_minimum_price")
    assert tomorrow_min_state
    assert tomorrow_min_state.state == "8.7"
    assert tomorrow_min_state.attributes["start"] == "03:00"
    assert tomorrow_min_state.attributes["end"] == "03:29"

    # Test tomorrow max price sensor
    tomorrow_max_state = hass.states.get("sensor.tomorrow_maximum_price")
    assert tomorrow_max_state
    assert tomorrow_max_state.state == "20.2"
    assert tomorrow_max_state.attributes["start"] == "19:00"
    assert tomorrow_max_state.attributes["end"] == "19:29"


async def test_sensor_unavailable_when_no_data(hass: HomeAssistant) -> None:
    """Test sensor is unavailable when no data is available."""
    with (
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.async_get_prices",
            return_value={},
        ),
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.get_current_price_info",
            return_value={},
        ),
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.get_next_price_info",
            return_value={},
        ),
        patch(
            "custom_components.looop_denki.api.LooopDenkiApiClient.get_tomorrow_forecast_info",
            return_value={},
        ),
    ):
        await setup_integration(hass)

    # Current price sensor should be unavailable
    current_state = hass.states.get("sensor.current_price")
    assert current_state
    assert current_state.state == STATE_UNAVAILABLE

    # Next price sensor should be unavailable
    next_state = hass.states.get("sensor.next_price")
    assert next_state
    assert next_state.state == STATE_UNAVAILABLE

    # Tomorrow sensors should be unavailable
    tomorrow_avg_state = hass.states.get("sensor.tomorrow_average_price")
    assert tomorrow_avg_state
    assert tomorrow_avg_state.state == STATE_UNAVAILABLE


async def test_sensor_update_failure(hass: HomeAssistant) -> None:
    """Test sensor handles update failures gracefully."""
    with patch(
        "custom_components.looop_denki.api.LooopDenkiApiClient.async_get_prices",
        side_effect=Exception("API Error"),
    ):
        config_entry = await setup_integration(hass)

    # When API fails during initial setup, the integration should be in setup retry state
    assert config_entry.state == ConfigEntryState.SETUP_RETRY
