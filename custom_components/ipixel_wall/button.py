"""Maintenance buttons for the iPIXEL wall."""
from homeassistant.components.button import ButtonEntity
from homeassistant.const import EntityCategory

from . import device_info
from .const import DOMAIN
from .manager import async_reset_boot_memory, async_factory_reset


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([WallBootReset(entry, data), WallFactoryReset(entry, data)])


class WallBootReset(ButtonEntity):
    """Clear the panels' stored content so they boot to a black screen."""

    _attr_name = "Opstartbeeld zwart maken"
    _attr_icon = "mdi:monitor-off"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry, data):
        self.data = data
        self._attr_unique_id = f"{entry.entry_id}_boot_reset"
        self._attr_device_info = device_info(data)

    async def async_press(self) -> None:
        await async_reset_boot_memory(self.hass, self.data)


class WallFactoryReset(ButtonEntity):
    """Wipe everything stored on the panels (factory reset of their memory)."""

    _attr_name = "Paneelgeheugen volledig wissen"
    _attr_icon = "mdi:delete-forever"
    _attr_entity_category = EntityCategory.CONFIG

    def __init__(self, entry, data):
        self.data = data
        self._attr_unique_id = f"{entry.entry_id}_factory_reset"
        self._attr_device_info = device_info(data)

    async def async_press(self) -> None:
        await async_factory_reset(self.hass, self.data)
