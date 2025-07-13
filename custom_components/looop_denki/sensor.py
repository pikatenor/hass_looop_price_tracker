"""Sensor platform for the Looop Denki integration."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorEntityDescription,
    SensorStateClass,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from . import LooopDenkiConfigEntry
from .const import (
    ATTR_CURRENT_LEVEL,
    ATTR_CURRENT_TEXT,
    ATTR_HOUR,
    ATTR_MINUTE_RANGE,
    ATTR_STATUS,
    ATTR_TIME_SLOT,
    DOMAIN,
)
from .coordinator import LooopDenkiCoordinator


@dataclass(frozen=True, kw_only=True)
class LooopDenkiSensorEntityDescription(SensorEntityDescription):
    """Describes Looop Denki sensor entity."""

    value_fn: Callable[[LooopDenkiSensor], float | str | None]
    extra_fn: Callable[[LooopDenkiSensor], dict[str, Any] | None] | None = None


SENSOR_TYPES: tuple[LooopDenkiSensorEntityDescription, ...] = (
    LooopDenkiSensorEntityDescription(
        key="current_price",
        translation_key="current_price",
        name="Current Price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="円/kWh",
        value_fn=lambda sensor: sensor.coordinator.data.get("current_info", {}).get(
            "current_price"
        )
        if sensor.coordinator.data
        else None,
    ),
    LooopDenkiSensorEntityDescription(
        key="next_price",
        translation_key="next_price",
        name="Next Price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="円/kWh",
        value_fn=lambda sensor: sensor.coordinator.data.get("next_info", {}).get(
            "next_price"
        )
        if sensor.coordinator.data
        else None,
        extra_fn=lambda sensor: {
            "next_status": sensor.coordinator.data.get("next_info", {}).get(
                "next_status"
            ),
            "next_time_slot": sensor.coordinator.data.get("next_info", {}).get(
                "next_time_slot"
            ),
            "is_tomorrow": sensor.coordinator.data.get("next_info", {}).get(
                "is_tomorrow", False
            ),
        }
        if sensor.coordinator.data and sensor.coordinator.data.get("next_info")
        else None,
    ),
    LooopDenkiSensorEntityDescription(
        key="tomorrow_average",
        translation_key="tomorrow_average_price",
        name="Tomorrow Average Price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="円/kWh",
        value_fn=lambda sensor: sensor.coordinator.data.get("tomorrow_info", {}).get(
            "tomorrow_average"
        )
        if sensor.coordinator.data
        else None,
        extra_fn=lambda sensor: {
            "data_available": sensor.coordinator.data.get("tomorrow_info", {}).get(
                "data_available", False
            ),
        }
        if sensor.coordinator.data and sensor.coordinator.data.get("tomorrow_info")
        else None,
    ),
    LooopDenkiSensorEntityDescription(
        key="tomorrow_min",
        translation_key="tomorrow_min_price",
        name="Tomorrow Minimum Price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="円/kWh",
        value_fn=lambda sensor: sensor.coordinator.data.get("tomorrow_info", {}).get(
            "tomorrow_min"
        )
        if sensor.coordinator.data
        else None,
        extra_fn=lambda sensor: sensor.coordinator.data.get("tomorrow_info", {}).get(
            "tomorrow_min_time"
        )
        if sensor.coordinator.data and sensor.coordinator.data.get("tomorrow_info")
        else None,
    ),
    LooopDenkiSensorEntityDescription(
        key="tomorrow_max",
        translation_key="tomorrow_max_price",
        name="Tomorrow Maximum Price",
        device_class=SensorDeviceClass.MONETARY,
        state_class=SensorStateClass.MEASUREMENT,
        native_unit_of_measurement="円/kWh",
        value_fn=lambda sensor: sensor.coordinator.data.get("tomorrow_info", {}).get(
            "tomorrow_max"
        )
        if sensor.coordinator.data
        else None,
        extra_fn=lambda sensor: sensor.coordinator.data.get("tomorrow_info", {}).get(
            "tomorrow_max_time"
        )
        if sensor.coordinator.data and sensor.coordinator.data.get("tomorrow_info")
        else None,
    ),
)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: LooopDenkiConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Looop Denki sensor entities."""
    coordinator = entry.runtime_data

    entities = [
        LooopDenkiSensor(coordinator, entry, description)
        for description in SENSOR_TYPES
    ]

    async_add_entities(entities)


class LooopDenkiSensor(CoordinatorEntity[LooopDenkiCoordinator], SensorEntity):
    """Sensor for Looop Denki electricity pricing data."""

    entity_description: LooopDenkiSensorEntityDescription

    def __init__(
        self,
        coordinator: LooopDenkiCoordinator,
        entry: LooopDenkiConfigEntry,
        description: LooopDenkiSensorEntityDescription,
    ) -> None:
        """Initialize the sensor."""
        super().__init__(coordinator)
        self.entity_description = description

        self._area_code = entry.data["area_code"]
        area_names = coordinator.client.get_area_codes()
        area_name = area_names.get(self._area_code, f"Area {self._area_code}")

        self._attr_unique_id = f"{DOMAIN}_{self._area_code}_{description.key}"
        self._attr_translation_key = description.translation_key

        self._attr_device_info = {
            "identifiers": {(DOMAIN, self._area_code)},
            "name": f"Looop でんき - {area_name}",
            "manufacturer": "株式会社Looop",
            "model": "でんき予報",
            "sw_version": "1.0",
        }

    @property
    def native_value(self) -> float | str | None:
        """Return the sensor value."""
        return self.entity_description.value_fn(self)

    @property
    def extra_state_attributes(self) -> dict[str, Any] | None:
        """Return additional state attributes."""
        if not self.coordinator.data:
            return None

        # Start with basic attributes for current_price sensor
        attrs = {}
        if self.entity_description.key == "current_price":
            current_info = self.coordinator.data.get("current_info", {})
            if current_info:
                attrs.update(
                    {
                        ATTR_CURRENT_LEVEL: current_info.get("current_level"),
                        ATTR_CURRENT_TEXT: current_info.get("current_text"),
                        ATTR_STATUS: current_info.get("status"),
                        ATTR_TIME_SLOT: current_info.get("time_slot"),
                        ATTR_HOUR: current_info.get("hour"),
                        ATTR_MINUTE_RANGE: current_info.get("minute_range"),
                    }
                )

        # Add sensor-specific attributes
        if self.entity_description.extra_fn:
            extra_attrs = self.entity_description.extra_fn(self)
            if extra_attrs:
                attrs.update(extra_attrs)

        return attrs if attrs else None

    @property
    def available(self) -> bool:
        """Return if entity is available."""
        if not self.coordinator.last_update_success or not self.coordinator.data:
            return False

        # Different availability logic for different sensors
        if self.entity_description.key == "current_price":
            return bool(self.coordinator.data.get("current_info"))
        if self.entity_description.key == "next_price":
            return bool(self.coordinator.data.get("next_info"))
        if self.entity_description.key.startswith("tomorrow_"):
            tomorrow_info = self.coordinator.data.get("tomorrow_info", {})
            return tomorrow_info.get("data_available", False)

        return True
