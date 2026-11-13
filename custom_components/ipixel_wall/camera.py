"""Virtual preview of what the iPIXEL wall is currently showing."""
from __future__ import annotations

import asyncio
import io
import time

from PIL import Image, ImageChops, ImageDraw

from homeassistant.components.camera import Camera

from . import device_info
from .const import DOMAIN

SCALE = 8                    # each LED becomes an 8x8 block
UNLIT = (28, 28, 28)         # colour of an LED that is off
MAX_CACHED_FRAMES = 400

_masks: dict[tuple[int, int], Image.Image] = {}


async def async_setup_entry(hass, entry, async_add_entities):
    data = hass.data[DOMAIN][entry.entry_id]
    async_add_entities([
        IPixelWallPreview(entry, data),                                   # as configured
        IPixelWallPreview(entry, data, 96, "preview_96", "Preview 3 panelen"),
        IPixelWallPreview(entry, data, 128, "preview_128", "Preview 4 panelen"),
        IPixelWallTV(entry, data),
    ])


def _dot_mask(size: tuple[int, int], scale: int = SCALE) -> Image.Image:
    key = (size[0], size[1], scale)
    if key not in _masks:
        tile = Image.new("L", (scale, scale), 0)
        inset = 1 if scale >= 5 else 0
        ImageDraw.Draw(tile).ellipse((inset, inset, scale - 1 - inset, scale - 1 - inset), fill=255)
        mask = Image.new("L", (size[0] * scale, size[1] * scale), 0)
        for x in range(0, mask.width, scale):
            for y in range(0, mask.height, scale):
                mask.paste(tile, (x, y))
        _masks[key] = mask
    return _masks[key]


def _led(frame: Image.Image, scale: int = SCALE) -> Image.Image:
    """Upscale a frame to round 'LED' dots on a black board."""
    frame = frame.convert("RGB")
    big = frame.resize((frame.width * scale, frame.height * scale), Image.Resampling.NEAREST)
    lit = ImageChops.lighter(big, Image.new("RGB", big.size, UNLIT))
    return Image.composite(lit, Image.new("RGB", big.size, (0, 0, 0)), _dot_mask(frame.size, scale))


def _render(frame: Image.Image) -> bytes:
    out = _led(frame)
    buffer = io.BytesIO()
    out.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def _frame_index(durations: list[int], start: float) -> int:
    total = sum(durations) or 1
    t = ((time.monotonic() - start) * 1000) % total
    for index, duration in enumerate(durations):
        if t < duration:
            return index
        t -= duration
    return len(durations) - 1


class IPixelWallPreview(Camera):
    """Shows the current wall content; animations play along in live view."""

    _attr_icon = "mdi:monitor-eye"

    def __init__(self, entry, data, width=None, key="preview", name="Preview"):
        super().__init__()
        self.data = data
        self._width = width
        self._attr_name = name
        self._alt = None
        self._alt_lock = asyncio.Lock()
        self.content_type = "image/jpeg"
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = device_info(data)
        self._cache: dict[int, bytes] = {}
        self._cache_key = None

    @property
    def frame_interval(self) -> float:
        return 0.2

    async def _preview(self):
        """Frames for this camera's width; re-rendered when it differs from the wall."""
        own = self._width or self.data["width"]
        preview = self.data.get("preview")
        if own == self.data["width"] or not preview:
            return preview or ([Image.new("RGB", (own, 32))], [1000], 0.0)
        src = self.data.get("preview_src")
        if not src:
            return ([Image.new("RGB", (own, 32))], [1000], 0.0)
        render, start = src
        async with self._alt_lock:
            if self._alt is None or self._alt[2] != start:
                frames, durations = await self.hass.async_add_executor_job(render, own)
                self._alt = (frames, list(durations or [1000] * len(frames)), start)
        return self._alt

    async def async_camera_image(self, width=None, height=None) -> bytes | None:
        frames, durations, start = await self._preview()

        anchor = self.data.get("preview_anchor")
        t0 = anchor[1] if anchor and anchor[0] == start else start  # follow the real stream
        index = _frame_index(durations, t0) if len(frames) > 1 else 0
        if self._cache_key != start:
            self._cache, self._cache_key = {}, start
        if index in self._cache:
            return self._cache[index]
        image = await self.hass.async_add_executor_job(_render, frames[index])
        if len(frames) <= MAX_CACHED_FRAMES:
            self._cache[index] = image
        return image


# ===================== TV view (16:9) =====================
TV_SIZE = (1280, 720)
TV_WALL_WIDTH = 128          # the wall in the middle, as on 4 panels
TV_WALL_SCALE = 10           # 128 x 32 LEDs -> 1280 x 320 px
TV_INFO_SCALE = 6            # info boards: 213 x 32 LEDs -> 1278 x 192 px
TV_WEATHER_REFRESH = 900     # seconds
_DAYS = ["MA", "DI", "WO", "DO", "VR", "ZA", "ZO"]


def _clock_frame(now, color, background, width: int) -> Image.Image:
    from .render import render_clock_gif

    gif = Image.open(io.BytesIO(render_clock_gif(now, width, color, background)))
    gif.seek(0 if now.second % 2 == 0 else 1)
    return gif.convert("RGB")


def _weather_frame(state, forecast, width: int) -> Image.Image:
    from .weather_render import render_weather_png

    columns = width // 32
    img = Image.new("RGB", (width, 32))
    if state is not None:
        inner = Image.open(io.BytesIO(
            render_weather_png(state[0], state[1], forecast, columns * 32)
        )).convert("RGB")
        img.paste(inner, ((width - inner.width) // 2, 0))
    return img


def _compose_tv(top: Image.Image, wall: Image.Image, bottom: Image.Image) -> bytes:
    canvas = Image.new("RGB", TV_SIZE, (0, 0, 0))
    if wall.width != TV_WALL_WIDTH:
        wall = wall.resize((TV_WALL_WIDTH, 32), Image.Resampling.NEAREST)
    boards = [_led(top, TV_INFO_SCALE), _led(wall, TV_WALL_SCALE), _led(bottom, TV_INFO_SCALE)]
    gap = (TV_SIZE[1] - sum(b.height for b in boards)) // 4
    y = gap
    for board in boards:
        canvas.paste(board, ((TV_SIZE[0] - board.width) // 2, y))
        y += board.height + gap
    buffer = io.BytesIO()
    canvas.save(buffer, format="JPEG", quality=85)
    return buffer.getvalue()


class IPixelWallTV(IPixelWallPreview):
    """16:9 view for a TV: clock on top, the wall (4 panels) in the middle, weather below."""

    def __init__(self, entry, data):
        super().__init__(entry, data, TV_WALL_WIDTH, "preview_tv", "Preview TV")
        self._attr_icon = "mdi:television"
        self._weather = None          # (condition, temperature)
        self._forecast: list = []
        self._weather_at = 0.0
        self._last_key = None
        self._last_jpeg = None

    def _weather_entity(self):
        from . import const as _const

        wanted = getattr(_const, "TV_WEATHER_ENTITY", None)
        if wanted:
            return wanted
        states = self.hass.states.async_all("weather")
        return states[0].entity_id if states else None

    async def _refresh_weather(self) -> None:
        if self._weather is not None and time.monotonic() - self._weather_at < TV_WEATHER_REFRESH:
            return
        self._weather_at = time.monotonic()
        entity_id = self._weather_entity()
        state = self.hass.states.get(entity_id) if entity_id else None
        if state is None:
            return
        self._weather = (state.state, state.attributes.get("temperature"))
        try:
            from homeassistant.util import dt as dt_util

            response = await self.hass.services.async_call(
                "weather", "get_forecasts", {"entity_id": entity_id, "type": "daily"},
                blocking=True, return_response=True,
            )
            today = dt_util.now().date()
            upcoming = []
            for item in (response or {}).get(entity_id, {}).get("forecast", []):
                parsed = dt_util.parse_datetime(str(item.get("datetime", "")))
                if parsed is None:
                    continue
                local = dt_util.as_local(parsed)
                if local.date() > today:
                    upcoming.append({**item, "day": _DAYS[local.weekday()]})
            self._forecast = upcoming
        except Exception:  # the forecast is optional
            self._forecast = []

    async def async_camera_image(self, width=None, height=None) -> bytes | None:
        from homeassistant.util import dt as dt_util

        await self._refresh_weather()
        frames, durations, start = await self._preview()
        anchor = self.data.get("preview_anchor")
        t0 = anchor[1] if anchor and anchor[0] == start else start
        index = _frame_index(durations, t0) if len(frames) > 1 else 0

        now = dt_util.now()
        info_width = TV_SIZE[0] // TV_INFO_SCALE
        key = (start, index, now.strftime("%H%M"), now.second % 2, self._weather_at)
        if key == self._last_key and self._last_jpeg:
            return self._last_jpeg

        color, background = self.data["text_color"], self.data["background_color"]
        top = await self.hass.async_add_executor_job(_clock_frame, now, color, background, info_width)
        bottom = await self.hass.async_add_executor_job(
            _weather_frame, self._weather, self._forecast, info_width
        )
        self._last_jpeg = await self.hass.async_add_executor_job(
            _compose_tv, top, frames[index], bottom
        )
        self._last_key = key
        return self._last_jpeg
