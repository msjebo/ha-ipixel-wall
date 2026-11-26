"""Rendering and splitting for the (panels x 32) x 32 virtual canvas."""
from __future__ import annotations

import io
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont, ImageOps
from PIL import ImageFile

# Some web images (e.g. Deezer artist photos) miss a few trailing bytes; show them anyway
ImageFile.LOAD_TRUNCATED_IMAGES = True

from homeassistant.core import HomeAssistant

from custom_components.ipixel_color.display.text_renderer import render_text_to_png
from custom_components.ipixel_color.fonts import get_font_path

from .const import (
    WALL_WIDTH, WALL_HEIGHT, PANEL_WIDTH, PANEL_HEIGHT,
    MAX_GIF_FRAMES,
)


def _rgb_hex(rgb: tuple[int, int, int]) -> str:
    return "".join(f"{max(0, min(255, int(c))):02x}" for c in rgb)


import re as _re
from functools import lru_cache as _lru_cache

from . import dmd_font as _dmd

_PREFIX_RE = _re.compile(r"^\[(vast|ttf|fs=(\d{1,2}))\]\s?", _re.I)
_FIXED_RE = _PREFIX_RE  # backwards compatible name
LINE_GAP = 1


def strip_fixed_prefix(text: str) -> str:
    return _PREFIX_RE.sub("", text, count=1)


def _split_lines(text: str) -> list[str]:
    """Split on '|' or a newline; at most two lines."""
    lines = [line.strip() for line in _re.split(r"\||\n", text)]
    return lines[:2] if len(lines) > 1 else lines


def _wrap_two(text: str, width: int) -> list[str]:
    """Word-wrap into at most two lines that fit `width` at scale 1."""
    words, lines, current = text.split(), [], ""
    for word in words:
        trial = f"{current} {word}".strip()
        if _dmd.text_width(trial) <= width or not current:
            current = trial
        else:
            lines.append(current)
            current = word
    lines.append(current)
    if len(lines) > 2:
        lines = [lines[0], " ".join(lines[1:])]
    return lines


def _auto_layout(text: str, width: int) -> tuple[list[str], int]:
    lines = _split_lines(text)
    if len(lines) == 1:
        for scale in (3, 2, 1):
            if _dmd.text_width(lines[0], scale) <= width:
                return lines, scale
        return _wrap_two(lines[0], width), 1
    return lines, 1


def _render_dmd(lines, scale, text_color, background_color, width) -> bytes:
    img = Image.new("RGB", (width, WALL_HEIGHT), tuple(background_color))
    color = tuple(text_color)
    if len(lines) == 1:
        y = (WALL_HEIGHT - _dmd.BODY_HEIGHT * scale) // 2
        pitch = 0
    else:
        pitch = (_dmd.LINE_HEIGHT + LINE_GAP) * scale
        total = pitch * len(lines) - LINE_GAP * scale
        y = (WALL_HEIGHT - total) // 2
    for line in lines:
        x = (width - _dmd.text_width(line, scale)) // 2
        _dmd.draw_text(img, max(0, x), y, line, scale, color)
        y += pitch
    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()


def render_static_text(
    text, text_color, background_color, width: int = WALL_WIDTH,
) -> bytes:
    """DMD-style text.

    '[vast]'  -> small font (always the same size), up to 2 lines with '|'
    '[fs=N]'  -> font scale N (1-3)
    '[ttf]'   -> old smooth font renderer
    no prefix -> largest DMD size that fits; wraps to 2 lines when needed
    """
    match = _PREFIX_RE.match(text)
    body = text[match.end():] if match else text
    kind = match.group(1).lower() if match else ""

    if kind == "ttf":
        return render_text_to_png(
            text=body, width=width, height=WALL_HEIGHT, antialias=False,
            font_size=None, font="OpenSans-Light.ttf", line_spacing=0,
            text_color=_rgb_hex(text_color), bg_color=_rgb_hex(background_color),
        )
    if kind == "vast":
        lines, scale = _split_lines(body), 1
    elif kind.startswith("fs="):
        lines, scale = _split_lines(body), max(1, min(3, int(match.group(2))))
        if len(lines) > 1:
            scale = 1
    else:
        lines, scale = _auto_layout(body, width)
    return _render_dmd(lines, scale, text_color, background_color, width)


def _canvas_frame(
    frame: Image.Image,
    resize_mode: str,
    background: tuple[int, int, int],
    width: int = WALL_WIDTH,
    panel=None,
) -> Image.Image:
    frame = frame.convert("RGBA")
    if resize_mode == "crop":
        fitted = ImageOps.fit(frame, (width, WALL_HEIGHT), method=Image.Resampling.NEAREST)
    else:
        fitted = ImageOps.contain(frame, (width, WALL_HEIGHT), method=Image.Resampling.NEAREST)
        canvas = Image.new("RGBA", (width, WALL_HEIGHT), (*background, 255))
        x = (width - fitted.width) // 2
        if panel:
            # centre the image on one panel (1 = leftmost)
            index = min(max(int(panel), 1), width // PANEL_WIDTH) - 1
            x = min(max(index * PANEL_WIDTH + (PANEL_WIDTH - fitted.width) // 2, 0), width - fitted.width)
        canvas.alpha_composite(fitted, (x, (WALL_HEIGHT - fitted.height) // 2))
        fitted = canvas
    background_image = Image.new("RGBA", fitted.size, (*background, 255))
    background_image.alpha_composite(fitted)
    return background_image.convert("RGB")


_CROP_PRESETS = {
    "top": (0, 0, 1, 0.5),
    "bottom": (0, 0.5, 1, 1),
    "left": (0, 0, 0.5, 1),
    "right": (0.5, 0, 1, 1),
}


def _parse_crop(crop, size):
    """'top'/'bottom'/'left'/'right' or [left, top, right, bottom] as fractions 0-1."""
    if not crop:
        return None
    box = _CROP_PRESETS.get(str(crop).lower()) if isinstance(crop, str) else tuple(float(v) for v in crop)
    if not box or len(box) != 4:
        raise ValueError(f"Invalid crop: {crop!r}")
    w, h = size
    left, top, right, bottom = (round(box[0] * w), round(box[1] * h), round(box[2] * w), round(box[3] * h))
    if right <= left or bottom <= top:
        raise ValueError(f"Invalid crop: {crop!r}")
    return left, top, right, bottom


def prepare_image_frames(
    raw: bytes,
    resize_mode: str = "fit",
    background: tuple[int, int, int] = (0, 0, 0),
    width: int = WALL_WIDTH,
    crop=None,
    panel=None,
    text=None,
    text_color=(255, 255, 255),
) -> tuple[list[Image.Image], list[int], int, bool]:
    """Decode, normalize and resize a PNG/GIF to wall-sized frames.

    With `text` the image goes on one panel (`panel`, default 1) and the text
    is drawn on the widest free part of the wall next to it.
    """
    if text and not panel:
        panel = 1
    source = Image.open(io.BytesIO(raw))
    is_gif = source.format == "GIF" and getattr(source, "n_frames", 1) > 1
    frame_count = getattr(source, "n_frames", 1)
    if frame_count > MAX_GIF_FRAMES:
        raise ValueError(f"GIF has {frame_count} frames; maximum is {MAX_GIF_FRAMES}")

    frames: list[Image.Image] = []
    durations: list[int] = []
    for index in range(frame_count):
        source.seek(index)
        frame = source.convert("RGBA")
        box = _parse_crop(crop, frame.size)
        if box:
            frame = frame.crop(box)
        frames.append(_canvas_frame(frame, resize_mode, background, width, panel))
        durations.append(max(20, int(source.info.get("duration", 100))))

    if text:
        index = min(max(int(panel), 1), width // PANEL_WIDTH) - 1
        left_w, right_x = index * PANEL_WIDTH, (index + 1) * PANEL_WIDTH
        x, region = (right_x, width - right_x) if width - right_x >= left_w else (0, left_w)
        if region > 0:
            overlay = Image.open(io.BytesIO(
                render_static_text(str(text), text_color, background, region)
            )).convert("RGB")
            for frame in frames:
                frame.paste(overlay, (x, 0))

    loop = int(source.info.get("loop", 0))
    return frames, durations, loop, is_gif


def split_png(canvas: Image.Image) -> list[bytes]:
    """Split the wall frame into one PNG per 32x32 panel."""
    result = []
    for index in range(canvas.width // PANEL_WIDTH):
        tile = canvas.crop((index * PANEL_WIDTH, 0, (index + 1) * PANEL_WIDTH, PANEL_HEIGHT))
        buffer = io.BytesIO()
        tile.save(buffer, format="PNG", optimize=True)
        result.append(buffer.getvalue())
    return result


MIN_FRAME_MS = 40


def _enforce_min_duration(
    frames: list[Image.Image], durations: list[int]
) -> tuple[list[Image.Image], list[int]]:
    """Merge too-short frames on the full canvas, identically for all panels."""
    out_f: list[Image.Image] = []
    out_d: list[int] = []
    for frame, duration in zip(frames, durations):
        if out_d and out_d[-1] < MIN_FRAME_MS:
            out_d[-1] += duration
        else:
            out_f.append(frame)
            out_d.append(duration)
    return out_f, out_d


def _color_counts(tiles: list[Image.Image]) -> dict:
    counts: dict = {}
    for tile in tiles:
        for n, c in tile.getcolors(PANEL_WIDTH * PANEL_HEIGHT):
            counts[c] = counts.get(c, 0) + n
    return counts


def _encode_tile_gif(tiles: list[Image.Image], durations: list[int], loop: int) -> bytes:
    """Encode one panel GIF with exactly one GIF frame per virtual frame."""
    counts = _color_counts(tiles)
    if len(counts) > 254:
        strip = Image.new("RGB", (PANEL_WIDTH, PANEL_HEIGHT * len(tiles)))
        for i, tile in enumerate(tiles):
            strip.paste(tile, (0, i * PANEL_HEIGHT))
        strip = strip.quantize(
            colors=254, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE
        ).convert("RGB")
        tiles = [
            strip.crop((0, i * PANEL_HEIGHT, PANEL_WIDTH, (i + 1) * PANEL_HEIGHT))
            for i in range(len(tiles))
        ]
        counts = _color_counts(tiles)

    colors = [c for c, _ in sorted(counts.items(), key=lambda kv: -kv[1])]
    index = {c: i for i, c in enumerate(colors)}
    palette = [v for c in colors for v in c]
    dup_of: dict[int, int] = {}

    frames_p: list[Image.Image] = []
    prev: list[int] | None = None
    for tile in tiles:
        data = [index[c] for c in tile.getdata()]
        if prev is not None and data == prev:
            pos = next((k for k, v in enumerate(data) if v in dup_of), None)
            if pos is None and len(colors) + len(dup_of) < 256:
                pos = 0
                base = data[0]
                dup_of[base] = len(colors) + len(dup_of)
                palette.extend(colors[base])
            if pos is not None:
                base = data[pos]
                dup = dup_of[base]
                data[pos] = base if prev[pos] == dup else dup
        prev = data
        im = Image.new("P", (PANEL_WIDTH, PANEL_HEIGHT))
        im.putdata(data)
        frames_p.append(im)

    if len(palette) < 6:
        palette += [0] * (6 - len(palette))
    for im in frames_p:
        im.putpalette(palette)

    buffer = io.BytesIO()
    frames_p[0].save(
        buffer,
        format="GIF",
        save_all=True,
        append_images=frames_p[1:],
        duration=durations,
        loop=loop,
        disposal=2,
        optimize=False,
    )
    return buffer.getvalue()


def split_gif(
    frames: list[Image.Image],
    durations: list[int],
    loop: int,
) -> list[bytes]:
    """Encode one GIF per panel with identical frame counts and timings."""
    frames, durations = _enforce_min_duration(frames, durations)
    result = []
    for panel in range(frames[0].width // PANEL_WIDTH):
        tiles = [
            frame.convert("RGB").crop((panel * PANEL_WIDTH, 0, (panel + 1) * PANEL_WIDTH, PANEL_HEIGHT))
            for frame in frames
        ]
        result.append(_encode_tile_gif(tiles, durations, loop))
    return result


def render_scrolling_text_gif(
    text: str,
    text_color: tuple[int, int, int],
    background_color: tuple[int, int, int],
    frame_interval: float,
    width: int = WALL_WIDTH,
) -> tuple[list[Image.Image], list[int], int]:
    """Render a DMD-style marquee as frames on the wall canvas."""
    text = strip_fixed_prefix(text).replace("|", " ")
    scale = 2
    text_width = max(1, _dmd.text_width(text, scale))
    strip = Image.new("RGB", (text_width + 2 * width, WALL_HEIGHT), tuple(background_color))
    y = (WALL_HEIGHT - _dmd.BODY_HEIGHT * scale) // 2
    _dmd.draw_text(strip, width, y, text, scale, tuple(text_color))

    total_distance = width + text_width
    frame_count = min(240, max(24, total_distance // 2))
    step = max(1, math.ceil(total_distance / frame_count))
    duration = max(40, min(1000, int(frame_interval * 1000)))
    frames = [
        strip.crop((offset, 0, offset + width, WALL_HEIGHT))
        for offset in range(0, total_distance + 1, step)
    ]
    return frames, [duration] * len(frames), 0


# ===================== DMD clock =====================
_CLOCK_DAYS = ["MA", "DI", "WO", "DO", "VR", "ZA", "ZO"]
_CLOCK_MONTHS = ["JAN", "FEB", "MRT", "APR", "MEI", "JUN", "JUL", "AUG", "SEP", "OKT", "NOV", "DEC"]


def render_clock_gif(now, width: int, color, background=(0, 0, 0), big: bool = False) -> bytes:
    """Two-frame GIF (blinking colon): time, optionally with the date below."""
    color = tuple(color)
    dim = tuple(int(c * 0.6) for c in color)
    date = f"{_CLOCK_DAYS[now.weekday()]} {now.day} {_CLOCK_MONTHS[now.month - 1]}"
    frames = []
    for colon in (":", " "):
        time_text = f"{now.hour:02d}{colon}{now.minute:02d}"
        ref_width = _dmd.text_width(f"{now.hour:02d}:{now.minute:02d}", 1)
        img = Image.new("RGB", (width, WALL_HEIGHT), tuple(background))
        if big:
            scale = 3 if ref_width * 3 <= width else 2
            y = (WALL_HEIGHT - _dmd.BODY_HEIGHT * scale) // 2
        else:
            scale = 2
            y = 2
        x = (width - ref_width * scale) // 2
        # draw digits around a fixed-width colon slot so nothing shifts when it blinks
        left, right = f"{now.hour:02d}", f"{now.minute:02d}"
        colon_w = _dmd.text_width(":", scale)
        _dmd.draw_text(img, x, y, left, scale, color)
        cx = x + _dmd.text_width(left, scale) + scale
        if colon == ":":
            _dmd.draw_text(img, cx, y, ":", scale, color)
        _dmd.draw_text(img, cx + colon_w + scale, y, right, scale, color)
        if not big:
            dx = (width - _dmd.text_width(date)) // 2
            _dmd.draw_text(img, dx, y + _dmd.BODY_HEIGHT * scale + 4, date, 1, dim)
        frames.append(img)
    buffer = io.BytesIO()
    frames[0].save(buffer, format="GIF", save_all=True, append_images=frames[1:],
                   duration=[500, 500], loop=0, disposal=2, optimize=False)
    return buffer.getvalue()


# ===================== Transitions =====================
TRANSITIONS = ["none", "wipe", "slide", "dissolve", "drop"]


def transition_frames(old: Image.Image, new: Image.Image, kind: str):
    """Frames that animate from `old` to `new`; the last frame is exactly `new`.

    Returns (frames, milliseconds per frame).
    """
    import random

    old, new = old.convert("RGB"), new.convert("RGB")
    w, h = new.size
    frames: list[Image.Image] = []
    ms = 80
    if kind == "wipe":
        # a bright line sweeps left to right; mostly one panel changes per frame
        for x in range(16, w + 16, 16):
            x = min(x, w)
            frame = old.copy()
            frame.paste(new.crop((0, 0, x, h)), (0, 0))
            if x < w:
                ImageDraw.Draw(frame).line((x, 0, x, h - 1), fill=(255, 255, 255))
            frames.append(frame)
        ms = 70
    elif kind == "slide":
        for s in range(16, w + 16, 16):
            s = min(s, w)
            frame = Image.new("RGB", (w, h))
            frame.paste(old, (-s, 0))
            frame.paste(new, (w - s, 0))
            frames.append(frame)
        ms = 90
    elif kind == "dissolve":
        rng = random.Random(42)
        noise = Image.new("L", (w, h))
        noise.putdata([rng.randrange(256) for _ in range(w * h)])
        for step in range(1, 6):
            threshold = step * 256 // 5
            mask = noise.point(lambda v, t=threshold: 255 if v < t else 0)
            frames.append(Image.composite(new, old, mask))
        ms = 120
    elif kind == "drop":
        for s in range(8, h + 8, 8):
            s = min(s, h)
            frame = old.copy()
            frame.paste(new.crop((0, h - s, w, h)), (0, 0))
            frames.append(frame)
        ms = 90
    if frames:
        frames[-1] = new.copy()
    return frames, ms
