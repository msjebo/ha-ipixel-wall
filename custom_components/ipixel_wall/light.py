"""RGB controls for wall text and background colors."""
from homeassistant.components.light import LightEntity, ColorMode, ATTR_RGB_COLOR

from .const import DOMAIN
from .manager import async_show_text


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        WallColor(hass, data, "text_color", "Text color", (255, 255, 255)),
        WallColor(hass, data, "background_color", "Background color", (0, 0, 0)),
    ])


class WallColor(LightEntity):
    _attr_color_mode = ColorMode.RGB
    _attr_supported_color_modes = {ColorMode.RGB}
    _attr_is_on = True

    def __init__(self, hass, data, key, name, default):
        self.hass = hass
        self.data = data
        self.key = key
        self._attr_name = name
        self._attr_unique_id = f"ipixel_wall_{key}"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "three_panel_wall")},
            "name": "iPIXEL Wall",
        }
        self.data.setdefault(key, default)

    @property
    def rgb_color(self):
        return self.data[self.key]

    async def async_turn_on(self, **kwargs):
        if ATTR_RGB_COLOR in kwargs:
            self.data[self.key] = tuple(int(c) for c in kwargs[ATTR_RGB_COLOR])
        await self._refresh()
        self.async_write_ha_state()

    async def async_turn_off(self, **kwargs):
        self.data[self.key] = (0, 0, 0)
        await self._refresh()
        self.async_write_ha_state()

    async def _refresh(self):
        if self.data["text"]:
            await async_show_text(self.hass, self.data)
