"""DataUpdateCoordinator for the Looop Denki integration."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import LooopDenkiApiClient, LooopDenkiApiError
from .const import DOMAIN, UPDATE_INTERVAL_SECONDS

_LOGGER = logging.getLogger(__name__)


class LooopDenkiCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinator to manage Looop Denki data updates."""

    def __init__(self, hass: HomeAssistant, client: LooopDenkiApiClient) -> None:
        """Initialize the coordinator."""
        self.client = client
        
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL_SECONDS),
        )

    async def _async_update_data(self) -> dict[str, Any]:
        """Fetch data from Looop Denki API."""
        try:
            raw_data = await self.client.async_get_prices()
            current_info = self.client.get_current_price_info(raw_data)
            next_info = self.client.get_next_price_info(raw_data)
            tomorrow_info = self.client.get_tomorrow_forecast_info(raw_data)
            historical_data = self.client.get_historical_data(raw_data)

            return {
                "raw_data": raw_data,
                "current_info": current_info,
                "next_info": next_info,
                "tomorrow_info": tomorrow_info,
                "historical_data": historical_data,
            }
        except LooopDenkiApiError as err:
            raise UpdateFailed(f"Error communicating with Looop Denki API: {err}") from err