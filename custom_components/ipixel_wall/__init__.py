"""Virtual display of 3 or 4 iPIXEL Color panels side by side."""
from __future__ import annotations

import asyncio
import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import entity_registry as er

from .const import (
    DOMAIN, PLATFORMS, PANEL_WIDTH, MIN_PANELS, MAX_PANELS,
    DEFAULT_TEXT_COLOR, DEFAULT_BG_COLOR, panel_entities,
)

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Attach existing iPIXEL Color devices to one virtual wall."""
    registry = er.async_get(hass)
    entity_ids = panel_entities(entry)
    if not MIN_PANELS <= len(entity_ids) <= MAX_PANELS:
        raise ConfigEntryNotReady(f"Expected 3 or 4 panels, got {len(entity_ids)}")

    apis = []
    for entity_id in entity_ids:
        entity = registry.async_get(entity_id)
        if entity is None or entity.platform != "ipixel_color":
            raise ConfigEntryNotReady(
                f"{entity_id} is not an entity from the ipixel_color integration"
            )

        original_entry = hass.config_entries.async_get_entry(entity.config_entry_id)
        if original_entry is None or original_entry.domain != "ipixel_color":
            raise ConfigEntryNotReady(f"Could not resolve iPIXEL config entry for {entity_id}")

        api = hass.data.get("ipixel_color", {}).get(original_entry.entry_id)
        if api is None:
            raise ConfigEntryNotReady(f"iPIXEL API is not loaded for {entity_id}")
        apis.append(api)

    panels = len(apis)
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "apis": apis,
        "entity_ids": entity_ids,
        "panels": panels,
        "width": panels * PANEL_WIDTH,
        "text": "",
        "mode": "static",
        "scroll_interval": 0.12,
        "text_color": DEFAULT_TEXT_COLOR,
        "background_color": DEFAULT_BG_COLOR,
        "task": None,
        "lock": asyncio.Lock(),
        "media_title": None,
        "media_type": None,
    }
    _LOGGER.info("iPIXEL Wall: %s panels, %sx32", panels, panels * PANEL_WIDTH)

    entry.async_on_unload(entry.add_update_listener(_async_reload))
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_reload(hass: HomeAssistant, entry: ConfigEntry) -> None:
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: ConfigEntry) -> bool:
    """Unload the virtual wall without unloading the physical devices."""
    ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    data = hass.data.get(DOMAIN, {}).pop(entry.entry_id, None)
    if data and data.get("task"):
        data["task"].cancel()
    return ok


def device_info(data: dict) -> dict:
    """Shared device info, sized to the configured number of panels."""
    return {
        "identifiers": {(DOMAIN, "three_panel_wall")},
        "name": "iPIXEL Wall",
        "manufacturer": "iPIXEL",
        "model": f"{data['panels']} x 32x32 LED panels ({data['width']}x32)",
    }
