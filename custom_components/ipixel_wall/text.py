"""Text entity for the combined iPIXEL wall."""
from homeassistant.components.text import TextEntity, TextMode
from homeassistant.helpers.restore_state import RestoreEntity

from . import device_info
from .const import DOMAIN
from .manager import async_show_text


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([IPixelWallText(hass, entry, hass.data[DOMAIN][entry.entry_id])])


class IPixelWallText(TextEntity, RestoreEntity):
    _attr_name = "Display"
    _attr_icon = "mdi:led-strip-variant"
    _attr_mode = TextMode.TEXT
    _attr_native_max = 500

    def __init__(self, hass, entry, data):
        self.hass = hass
        self.data = data
        self._attr_unique_id = f"{entry.entry_id}_text"
        self._attr_device_info = device_info(data)

    @property
    def native_value(self):
        return self.data["text"]

    async def async_set_value(self, value: str):
        self.data["text"] = value
        self.data["media_title"] = None
        await async_show_text(self.hass, self.data)
        self.async_write_ha_state()
