"""Display mode selector."""
from homeassistant.components.select import SelectEntity
from homeassistant.helpers.restore_state import RestoreEntity

from .const import DOMAIN
from .manager import async_show_text


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WallMode(hass, data), WallTransition(data)])


class WallMode(SelectEntity):
    _attr_name = "Display mode"
    _attr_icon = "mdi:animation-play"
    _attr_options = ["static", "scroll"]

    def __init__(self, hass, data):
        self.hass = hass
        self.data = data
        self._attr_unique_id = "ipixel_wall_display_mode"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "three_panel_wall")},
            "name": "iPIXEL Wall",
        }

    @property
    def current_option(self):
        return self.data["mode"]

    async def async_select_option(self, option):
        self.data["mode"] = option
        await async_show_text(self.hass, self.data)
        self.async_write_ha_state()


class WallTransition(SelectEntity, RestoreEntity):
    """Animation used between two items on the wall."""

    _attr_name = "Transition"
    _attr_icon = "mdi:transition"
    _attr_options = ["none", "wipe", "slide", "dissolve", "drop"]

    def __init__(self, data):
        self.data = data
        self.data.setdefault("transition", "dissolve")
        self._attr_unique_id = "ipixel_wall_transition"
        self._attr_device_info = {
            "identifiers": {(DOMAIN, "three_panel_wall")},
            "name": "iPIXEL Wall",
        }

    async def async_added_to_hass(self):
        await super().async_added_to_hass()
        last = await self.async_get_last_state()
        if last and last.state in self._attr_options:
            self.data["transition"] = last.state

    @property
    def current_option(self):
        return self.data.get("transition", "dissolve")

    async def async_select_option(self, option):
        self.data["transition"] = option
        self.async_write_ha_state()
