"""Marquee interval and animation frame time."""
from homeassistant.components.number import NumberEntity, NumberMode
from homeassistant.helpers.restore_state import RestoreEntity

from . import const as _const

from .const import DOMAIN
from .manager import async_show_text


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WallScrollInterval(hass, data), WallFrameTime(hass, data)])


class WallScrollInterval(NumberEntity):
    _attr_name = "Scroll frame interval"
    _attr_native_min_value = 0.04
    _attr_native_max_value = 1.0
    _attr_native_step = 0.02
    _attr_native_unit_of_measurement = "s"
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:speedometer"

    def __init__(self, hass, data):
        self.hass = hass
        self.data = data
        self._attr_unique_id = "ipixel_wall_scroll_interval"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "three_panel_wall")},
            "name": "iPIXEL Wall",
        }

    @property
    def native_value(self):
        return self.data["scroll_interval"]

    async def async_set_native_value(self, value):
        self.data["scroll_interval"] = value
        if self.data["mode"] == "scroll" and self.data["text"]:
            await async_show_text(self.hass, self.data)
        self.async_write_ha_state()


class WallFrameTime(NumberEntity, RestoreEntity):
    """Minimum time per frame when streaming GIFs and transitions."""

    _attr_name = "Frametijd animaties"
    _attr_native_min_value = 50
    _attr_native_max_value = 500
    _attr_native_step = 10
    _attr_native_unit_of_measurement = "ms"
    _attr_mode = NumberMode.SLIDER
    _attr_icon = "mdi:timer-cog-outline"

    def __init__(self, hass, data):
        self.hass = hass
        self.data = data
        self._attr_unique_id = "ipixel_wall_min_frame_ms"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "three_panel_wall")},
            "name": "iPIXEL Wall",
        }

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last is not None:
            try:
                self.data["min_frame_ms"] = int(float(last.state))
            except (TypeError, ValueError):
                pass

    @property
    def native_value(self):
        return self.data.get("min_frame_ms") or getattr(_const, "STREAM_MIN_FRAME_MS", 150)

    async def async_set_native_value(self, value):
        # takes effect from the next GIF or transition
        self.data["min_frame_ms"] = int(value)
        self.async_write_ha_state()
