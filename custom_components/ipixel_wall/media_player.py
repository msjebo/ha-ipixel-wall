"""Media player for PNG and GIF playback on the combined wall."""
from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from urllib.parse import urlparse

from aiohttp import ClientError, ClientTimeout

from homeassistant.components import media_source
from homeassistant.components.media_player import (
    MediaPlayerEntity,
    MediaPlayerEntityFeature,
    MediaPlayerState,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.exceptions import HomeAssistantError

from . import device_info
from .const import DOMAIN, MAX_MEDIA_BYTES
from .manager import async_show_image, async_clear_wall

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(hass, entry, async_add_entities):
    async_add_entities([IPixelWallMediaPlayer(hass, entry, hass.data[DOMAIN][entry.entry_id])])


class IPixelWallMediaPlayer(MediaPlayerEntity):
    _attr_name = "Media"
    _attr_icon = "mdi:dots-grid"
    _attr_supported_features = (
        MediaPlayerEntityFeature.PLAY_MEDIA
        | MediaPlayerEntityFeature.STOP
        | MediaPlayerEntityFeature.BROWSE_MEDIA
    )

    def __init__(self, hass, entry, data):
        self.hass = hass
        self.data = data
        self._attr_unique_id = f"{entry.entry_id}_media"
        self._attr_device_info = device_info(data)
        self._state = MediaPlayerState.IDLE

    @property
    def state(self):
        return MediaPlayerState.PLAYING if self.data.get("media_type") else MediaPlayerState.IDLE

    @property
    def media_title(self):
        return self.data.get("media_title")

    @property
    def media_content_type(self):
        return self.data.get("media_type")

    async def async_browse_media(self, media_content_type=None, media_content_id=None):
        return await media_source.async_browse_media(
            self.hass,
            media_content_id,
        )

    async def async_play_media(self, media_type, media_id, **kwargs):
        """Load local Media Source files or external HTTP(S) URLs."""
        extra = kwargs.get("extra") or {}
        self._wall_source = None
        try:
            raw, title = await self._load_media(media_id)
            await async_show_image(
                self.hass,
                self.data,
                raw,
                resize_mode=extra.get("resize_mode", kwargs.get("resize_mode", "fit")),
                stream=extra.get("stream"),
                source=self._wall_source,
                transition=extra.get("transition"),
                media_title=title,
                crop=extra.get("crop"),
                panel=extra.get("panel"),
                text=extra.get("text"),
            )
            self._state = MediaPlayerState.PLAYING
            self.async_write_ha_state()
        except Exception as err:
            _LOGGER.exception("Could not play media on iPIXEL Wall")
            raise HomeAssistantError(f"iPIXEL Wall could not load media: {err}") from err

    async def _load_media(self, media_id: str) -> tuple[bytes, str]:
        """Resolve a camera entity, a media-source ID or a remote URL."""
        if media_id in ("clock", "clock:big"):
            from homeassistant.util import dt as dt_util
            from .render import render_clock_gif

            now, tc, bg, big = dt_util.now(), self.data["text_color"], self.data["background_color"], media_id == "clock:big"
            self._wall_source = lambda w: render_clock_gif(now, w, tc, bg, big)
            raw = await self.hass.async_add_executor_job(self._wall_source, self.data["width"])
            return raw, "Klok"
        if media_id.startswith("weather."):
            from .weather_render import render_weather_png

            state = self.hass.states.get(media_id)
            if state is None:
                raise ValueError(f"{media_id} not found")
            response = await self.hass.services.async_call(
                "weather", "get_forecasts",
                {"entity_id": media_id, "type": "daily"},
                blocking=True, return_response=True,
            )
            forecast = (response or {}).get(media_id, {}).get("forecast", [])
            from homeassistant.util import dt as dt_util

            today = dt_util.now().date()
            days = ["MA", "DI", "WO", "DO", "VR", "ZA", "ZO"]
            upcoming = []
            for item in forecast:
                parsed = dt_util.parse_datetime(str(item.get("datetime", "")))
                if parsed is None:
                    continue
                local = dt_util.as_local(parsed)
                if local.date() <= today:
                    continue
                upcoming.append({**item, "day": days[local.weekday()]})
            forecast = upcoming
            cond, temp = state.state, state.attributes.get("temperature")
            self._wall_source = lambda w: render_weather_png(cond, temp, forecast, w)
            raw = await self.hass.async_add_executor_job(self._wall_source, self.data["width"])
            return raw, media_id
        if media_id.startswith("camera.") or media_id.startswith("media-source://camera/"):
            from homeassistant.components.camera import async_get_image

            entity_id = media_id.rsplit("/", 1)[-1]
            image = await async_get_image(self.hass, entity_id, timeout=30)
            return self._check_size(image.content), entity_id
        if media_source.is_media_source_id(media_id):
            resolved = await media_source.async_resolve_media(
                self.hass, media_id, self.entity_id
            )
            if resolved.path:
                path = Path(resolved.path)
                raw = await self.hass.async_add_executor_job(path.read_bytes)
                return self._check_size(raw), path.name
            media_id = resolved.url

        parsed = urlparse(media_id)
        if parsed.scheme not in ("http", "https"):
            raise ValueError(
                "Use a media-source:// ID from Home Assistant's Media browser or an http(s) URL."
            )

        session = async_get_clientsession(self.hass)
        timeout = ClientTimeout(total=30)
        async with session.get(media_id, timeout=timeout) as response:
            response.raise_for_status()
            content_length = response.headers.get("Content-Length")
            if content_length and int(content_length) > MAX_MEDIA_BYTES:
                raise ValueError("Image/GIF exceeds the 10 MB limit")
            # read until the end: content.read(n) only returns what has arrived so far
            chunks, size = [], 0
            async for chunk in response.content.iter_chunked(65536):
                chunks.append(chunk)
                size += len(chunk)
                if size > MAX_MEDIA_BYTES:
                    break
            raw = b"".join(chunks)
            raw = self._check_size(raw)
            title = Path(parsed.path).name or parsed.netloc
            return raw, title

    @staticmethod
    def _check_size(raw: bytes) -> bytes:
        if not raw:
            raise ValueError("The selected media file is empty")
        if len(raw) > MAX_MEDIA_BYTES:
            raise ValueError("Image/GIF exceeds the 10 MB limit")
        return raw

    async def async_media_stop(self):
        from .manager import _stop_stream
        await _stop_stream(self.data)
        await async_clear_wall(self.data)
        self._state = MediaPlayerState.IDLE
        self.data["media_title"] = None
        self.data["media_type"] = None
        self.async_write_ha_state()
