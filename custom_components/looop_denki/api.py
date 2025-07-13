"""API client for Looop Denki electricity pricing."""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone, timedelta
from typing import Any

import aiohttp
from aiohttp import ClientSession

_LOGGER = logging.getLogger(__name__)

API_BASE_URL = "https://looop-denki.com/api/prices"
REQUEST_TIMEOUT = 10


class LooopDenkiApiError(Exception):
    """Base exception for Looop Denki API errors."""


class LooopDenkiApiClient:
    """Client for Looop Denki API."""

    def __init__(self, area_code: str, session: ClientSession | None = None) -> None:
        """Initialize the API client.

        Args:
            area_code: The electricity area code (01-10)
            session: Optional aiohttp session

        """
        self._area_code = area_code
        self._session = session
        self._close_session = False

    async def _get_session(self) -> ClientSession:
        """Get aiohttp session."""
        if self._session is None:
            self._session = aiohttp.ClientSession()
            self._close_session = True
        return self._session

    async def close(self) -> None:
        """Close aiohttp session."""
        if self._close_session and self._session:
            await self._session.close()

    async def async_get_prices(self) -> dict[str, Any]:
        """Get electricity prices for the configured area.

        Returns:
            Dict containing price data with current, historical pricing info

        Raises:
            LooopDenkiApiError: If API request fails

        """
        session = await self._get_session()
        url = f"{API_BASE_URL}?select_area={self._area_code}"

        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with session.get(url) as response:
                    response.raise_for_status()
                    data = await response.json()
        except TimeoutError as err:
            raise LooopDenkiApiError("Request timeout") from err
        except aiohttp.ClientError as err:
            raise LooopDenkiApiError(f"HTTP error: {err}") from err
        except Exception as err:
            raise LooopDenkiApiError(f"Unexpected error: {err}") from err
        else:
            _LOGGER.debug("Retrieved price data for area %s", self._area_code)
            return data

    def get_current_price_info(self, price_data: dict[str, Any]) -> dict[str, Any]:
        """Extract current price information from API response.

        Args:
            price_data: Raw API response data containing keys:
                - "0": Yesterday's pricing data
                - "1": Today's pricing data (current)
                - "2": Tomorrow's pricing data

        Returns:
            Dict with current price, level, and forecast info

        """
        # Get current time in JST (Japan Standard Time)
        jst = timezone(timedelta(hours=9))
        current_time = datetime.now(jst)
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_30min_slot = current_hour * 2 + (1 if current_minute >= 30 else 0)

        _LOGGER.debug("Current time: %s:%02d", current_hour, current_minute)
        _LOGGER.debug("Calculated time slot: %s (should be 0-47)", current_30min_slot)
        _LOGGER.debug("Price data keys: %s", list(price_data.keys()))
        
        # Debug: Show timelist if available
        if "timelist" in price_data:
            timelist = price_data["timelist"]
            if current_30min_slot < len(timelist):
                expected_time = timelist[current_30min_slot]
                _LOGGER.debug("Expected time for slot %s: %s", current_30min_slot, expected_time)

        # Get today's data (key "1" is today, "0" is yesterday, "2" is tomorrow)
        today_data = price_data.get("1", {})

        if not today_data:
            _LOGGER.warning("No data found for today (key '1')")
            return {}

        price_list = today_data.get("price_data", [])
        level_list = today_data.get("level", [])
        text_dict = today_data.get("text", {})

        _LOGGER.debug("Data lengths - price: %s, level: %s, text: %s",
                     len(price_list) if isinstance(price_list, list) else "N/A",
                     len(level_list) if isinstance(level_list, list) else "N/A",
                     len(text_dict) if isinstance(text_dict, dict) else "N/A")
        _LOGGER.debug("Text data type: %s, available keys: %s", type(text_dict).__name__, list(text_dict.keys()) if isinstance(text_dict, dict) else "N/A")
        
        # Debug: Show some price data around current slot
        if isinstance(price_list, list) and len(price_list) > current_30min_slot:
            start_idx = max(0, current_30min_slot - 2)
            end_idx = min(len(price_list), current_30min_slot + 3)
            price_sample = price_list[start_idx:end_idx]
            _LOGGER.debug("Price data around slot %s (indices %s-%s): %s", 
                         current_30min_slot, start_idx, end_idx-1, price_sample)
            
            # Look for 14.05 in the data
            if 14.05 in price_list:
                found_index = price_list.index(14.05)
                _LOGGER.debug("Found 14.05 at index %s (expected around %s)", found_index, current_30min_slot)

        # Ensure we have valid data structures
        if not isinstance(price_list, list):
            price_list = []
        if not isinstance(level_list, list):
            level_list = []
        if not isinstance(text_dict, dict):
            text_dict = {}

        if current_30min_slot < len(price_list):
            current_price = price_list[current_30min_slot]

            # Handle level_list safely
            current_level = None
            if current_30min_slot < len(level_list):
                current_level = level_list[current_30min_slot]

            # Handle text_dict safely (it's a dictionary)
            # NOTE: text dict uses 1-based indexing (1-48) while price_data uses 0-based (0-47)
            current_text = ""
            current_text_price = None
            text_slot_key = str(current_30min_slot + 1)  # Convert to 1-based indexing
            if text_slot_key in text_dict:
                text_data = text_dict[text_slot_key]
                if isinstance(text_data, dict):
                    current_text_price = text_data.get("price")
                    current_text = f"Price: {current_text_price}, Level: {text_data.get('level', 'N/A')}"
                else:
                    current_text = str(text_data)

            # Debug: Compare price_data vs text price
            _LOGGER.debug("Slot %s: price_data[%s]=%s, text['%s'].price=%s", 
                         current_30min_slot, current_30min_slot, current_price, 
                         text_slot_key, current_text_price)

            # Map level to meaningful status
            status = self._get_price_status(current_level, current_text_price or current_price)

            return {
                "current_price": current_text_price or current_price,
                "current_level": current_level,
                "current_text": current_text,
                "status": status,
                "time_slot": current_30min_slot,
                "hour": current_hour,
                "minute_range": "30-59" if current_time.minute >= 30 else "00-29",
            }

        return {}

    def get_next_price_info(self, price_data: dict[str, Any]) -> dict[str, Any]:
        """Get next hour's price information for seamless transitions.

        Returns:
            Dict with next price info or empty dict if not available

        """
        # Get current time in JST
        jst = timezone(timedelta(hours=9))
        current_time = datetime.now(jst)
        current_hour = current_time.hour
        current_minute = current_time.minute
        current_30min_slot = current_hour * 2 + (1 if current_minute >= 30 else 0)
        next_30min_slot = current_30min_slot + 1

        # Check if next slot is within today (0-47)
        if next_30min_slot < 48:
            # Next slot is still today
            today_data = price_data.get("1", {})
            if not today_data:
                return {}

            price_list = today_data.get("price_data", [])
            level_list = today_data.get("level", [])
            text_dict = today_data.get("text", {})

            if next_30min_slot < len(price_list):
                next_price = price_list[next_30min_slot]
                next_level = level_list[next_30min_slot] if next_30min_slot < len(level_list) else None

                # Get text data (1-based indexing)
                text_slot_key = str(next_30min_slot + 1)
                next_text_price = None
                if text_slot_key in text_dict and isinstance(text_dict[text_slot_key], dict):
                    next_text_price = text_dict[text_slot_key].get("price")

                return {
                    "next_price": next_text_price or next_price,
                    "next_level": next_level,
                    "next_status": self._get_price_status(next_level, next_text_price or next_price),
                    "next_time_slot": next_30min_slot,
                }
        else:
            # Next slot is tomorrow (slot 0)
            tomorrow_data = price_data.get("2", {})
            if not tomorrow_data:
                return {}

            price_list = tomorrow_data.get("price_data", [])
            level_list = tomorrow_data.get("level", [])
            text_dict = tomorrow_data.get("text", {})

            if len(price_list) > 0:
                next_price = price_list[0]
                next_level = level_list[0] if len(level_list) > 0 else None

                # Get text data for slot 1 (1-based indexing)
                next_text_price = None
                if "1" in text_dict and isinstance(text_dict["1"], dict):
                    next_text_price = text_dict["1"].get("price")

                return {
                    "next_price": next_text_price or next_price,
                    "next_level": next_level,
                    "next_status": self._get_price_status(next_level, next_text_price or next_price),
                    "next_time_slot": 0,
                    "is_tomorrow": True,
                }

        return {}

    def get_tomorrow_forecast_info(self, price_data: dict[str, Any]) -> dict[str, Any]:
        """Extract tomorrow's forecast information from API response.

        Returns:
            Dict with tomorrow's average, min, max prices and time ranges

        """
        tomorrow_data = price_data.get("2", {})
        if not tomorrow_data:
            return {}

        price_list = tomorrow_data.get("price_data", [])
        level_list = tomorrow_data.get("level", [])
        text_dict = tomorrow_data.get("text", {})

        if not price_list:
            return {}

        # Use text prices when available (more accurate)
        effective_prices = []
        for i in range(len(price_list)):
            text_slot_key = str(i + 1)  # 1-based indexing for text
            if text_slot_key in text_dict and isinstance(text_dict[text_slot_key], dict):
                text_price = text_dict[text_slot_key].get("price")
                if text_price is not None:
                    effective_prices.append(text_price)
                    continue
            effective_prices.append(price_list[i])

        if not effective_prices:
            return {}

        # Calculate statistics
        min_price = min(effective_prices)
        max_price = max(effective_prices)
        avg_price = sum(effective_prices) / len(effective_prices)

        # Find time ranges for min/max prices
        min_idx = effective_prices.index(min_price)
        max_idx = effective_prices.index(max_price)

        # Convert slot index to time range
        def slot_to_time_range(slot: int) -> dict[str, str]:
            hour = slot // 2
            minute_start = 30 if slot % 2 == 1 else 0
            minute_end = 29 if slot % 2 == 0 else 59
            return {
                "start": f"{hour:02d}:{minute_start:02d}",
                "end": f"{hour:02d}:{minute_end:02d}"
            }

        return {
            "tomorrow_average": round(avg_price, 2),
            "tomorrow_min": min_price,
            "tomorrow_max": max_price,
            "tomorrow_min_time": slot_to_time_range(min_idx),
            "tomorrow_max_time": slot_to_time_range(max_idx),
            "data_available": True,
        }

    def get_historical_data(self, price_data: dict[str, Any]) -> dict[str, dict[str, Any]]:
        """Get historical and forecast pricing data.

        Args:
            price_data: Raw API response data

        Returns:
            Dict containing yesterday, today, and tomorrow pricing data

        """
        return {
            "yesterday": price_data.get("0", {}),
            "today": price_data.get("1", {}),
            "tomorrow": price_data.get("2", {}),
        }

    def _get_price_status(self, level: float | None, price: float | None) -> str:
        """Determine price status based on level and price.

        Args:
            level: Price level from API (-0.5, 0, etc.)
            price: Current price in yen/kWh

        Returns:
            String status: でんき日和, でんき注意報, or でんき警報

        """
        if price is None:
            return "不明"

        # でんき警報: 100円を超える場合
        if price >= 100:
            return "でんき警報"

        # レベルに基づく判定
        if level is not None:
            if level < 0:  # 負の値は安い時間帯（でんき日和）
                return "でんき日和"
            if level > 0:  # 正の値は高い時間帯（でんき注意報）
                return "でんき注意報"

        # レベルが0または不明の場合、価格で判断
        if price < 15:  # 比較的安い価格
            return "でんき日和"
        if price > 25:  # 比較的高い価格
            return "でんき注意報"
        return "通常"

    @staticmethod
    def get_area_codes() -> dict[str, str]:
        """Get available electricity area codes.

        Returns:
            Dict mapping area codes to area names

        """
        return {
            "01": "北海道電力",
            "02": "東北電力",
            "03": "東京電力",
            "04": "中部電力",
            "05": "北陸電力",
            "06": "関西電力",
            "07": "中国電力",
            "08": "四国電力",
            "09": "九州電力",
            "10": "沖縄電力",
        }

    async def test_connection(self) -> bool:
        """Test if we can connect to the API.

        Returns:
            True if connection successful, False otherwise

        """
        try:
            data = await self.async_get_prices()
            return bool(data)
        except LooopDenkiApiError:
            return False
