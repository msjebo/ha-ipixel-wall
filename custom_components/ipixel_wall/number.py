"""Marquee interval control."""
from homeassistant.components.number import NumberEntity, NumberMode

from .const import DOMAIN
from .manager import async_show_text


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([WallScrollInterval(hass, hass.data[DOMAIN][entry.entry_id])])


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
