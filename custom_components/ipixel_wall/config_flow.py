"""Config and options flow for iPIXEL Wall (3 or 4 panels)."""
from __future__ import annotations

import voluptuous as vol

from homeassistant import config_entries
from homeassistant.core import callback
from homeassistant.helpers import entity_registry as er
from homeassistant.helpers import selector

from .const import DOMAIN, CONF_LEFT, CONF_MIDDLE, CONF_RIGHT, CONF_PANEL4, PANEL_KEYS


def _schema(current: dict | None = None) -> vol.Schema:
    current = current or {}
    entity_selector = selector.EntitySelector(
        selector.EntitySelectorConfig(domain="text", integration="ipixel_color")
    )

    def _field(key, required):
        marker = vol.Required if required else vol.Optional
        value = current.get(key)
        if value:
            return marker(key, description={"suggested_value": value})
        return marker(key)

    return vol.Schema({
        _field(CONF_LEFT, True): entity_selector,
        _field(CONF_MIDDLE, True): entity_selector,
        _field(CONF_RIGHT, True): entity_selector,
        _field(CONF_PANEL4, False): entity_selector,
    })


def _validate(hass, user_input: dict) -> tuple[dict, str | None]:
    """Return the cleaned panel mapping and an error key, if any."""
    cleaned = {key: user_input[key] for key in PANEL_KEYS if user_input.get(key)}
    selected = list(cleaned.values())
    if len(set(selected)) != len(selected):
        return cleaned, "duplicate_panel"

    registry = er.async_get(hass)
    for entity_id in selected:
        entity = registry.async_get(entity_id)
        if (
            entity is None
            or entity.platform != "ipixel_color"
            or not entity.unique_id.endswith("_text_display")
        ):
            return cleaned, "invalid_panel"
    return cleaned, None


def _title(cleaned: dict) -> str:
    return f"iPIXEL Wall ({len(cleaned) * 32}x32)"


class IPixelWallConfigFlow(config_entries.ConfigFlow, domain=DOMAIN):
    """Configure a wall from 3 or 4 existing iPIXEL text entities."""

    VERSION = 1

    async def async_step_user(self, user_input=None):
        errors = {}
        if user_input is not None:
            cleaned, error = _validate(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                await self.async_set_unique_id("three_panel_wall")
                self._abort_if_unique_id_configured()
                return self.async_create_entry(title=_title(cleaned), data=cleaned)

        return self.async_show_form(
            step_id="user", data_schema=_schema(user_input), errors=errors
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry):
        return IPixelWallOptionsFlow()


class IPixelWallOptionsFlow(config_entries.OptionsFlow):
    """Change the panels (e.g. add or remove the 4th) without re-creating the wall."""

    async def async_step_init(self, user_input=None):
        errors = {}
        if user_input is not None:
            cleaned, error = _validate(self.hass, user_input)
            if error:
                errors["base"] = error
            else:
                self.hass.config_entries.async_update_entry(
                    self.config_entry, data=cleaned, options={}, title=_title(cleaned)
                )
                return self.async_create_entry(title="", data={})

        current = user_input or {**self.config_entry.data, **self.config_entry.options}
        return self.async_show_form(
            step_id="init", data_schema=_schema(current), errors=errors
        )
