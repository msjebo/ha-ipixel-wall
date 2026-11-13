"""Pixel-art weather view for the iPIXEL wall: one 32x32 column per panel."""
from __future__ import annotations

import io
from datetime import datetime

from PIL import Image, ImageDraw

# ---------------------------------------------------------------- 3x5 font
_GLYPHS = {
    "0": ["###", "#.#", "#.#", "#.#", "###"],
    "1": [".#.", "##.", ".#.", ".#.", "###"],
    "2": ["###", "..#", "###", "#..", "###"],
    "3": ["###", "..#", ".##", "..#", "###"],
    "4": ["#.#", "#.#", "###", "..#", "..#"],
    "5": ["###", "#..", "###", "..#", "###"],
    "6": ["###", "#..", "###", "#.#", "###"],
    "7": ["###", "..#", "..#", ".#.", ".#."],
    "8": ["###", "#.#", "###", "#.#", "###"],
    "9": ["###", "#.#", "###", "..#", "###"],
    "-": ["...", "...", "###", "...", "..."],
    "°": ["##", "##", "..", "..", ".."],
    " ": ["..", "..", "..", "..", ".."],
    "A": [".#.", "#.#", "###", "#.#", "#.#"],
    "D": ["##.", "#.#", "#.#", "#.#", "##."],
    "I": ["###", ".#.", ".#.", ".#.", "###"],
    "M": ["#...#", "##.##", "#.#.#", "#...#", "#...#"],
    "N": ["#..#", "##.#", "#.##", "#..#", "#..#"],
    "O": ["###", "#.#", "#.#", "#.#", "###"],
    "R": ["##.", "#.#", "##.", "#.#", "#.#"],
    "U": ["#.#", "#.#", "#.#", "#.#", "###"],
    "V": ["#.#", "#.#", "#.#", "#.#", ".#."],
    "W": ["#...#", "#...#", "#.#.#", "##.##", "#...#"],
    "Z": ["###", "..#", ".#.", "#..", "###"],
    "?": ["###", "..#", ".##", "...", ".#."],
}
_DAYS = ["MA", "DI", "WO", "DO", "VR", "ZA", "ZO"]


def _text_width(text: str) -> int:
    return sum(len(_GLYPHS.get(c, _GLYPHS["?"])[0]) + 1 for c in text) - 1


def _draw_text(img: Image.Image, cx: int, y: int, text: str, color) -> None:
    """Draw pixel text horizontally centred on cx."""
    x = cx - _text_width(text) // 2
    px = img.load()
    for ch in text:
        glyph = _GLYPHS.get(ch, _GLYPHS["?"])
        for row, line in enumerate(glyph):
            for col, bit in enumerate(line):
                if bit == "#" and 0 <= x + col < img.width and 0 <= y + row < img.height:
                    px[x + col, y + row] = color
        x += len(glyph[0]) + 1


# ---------------------------------------------------------------- icons
SUN = (255, 190, 0)
MOON = (230, 220, 150)
CLOUD = (170, 170, 180)
DARK_CLOUD = (110, 110, 120)
RAIN = (40, 120, 255)
SNOW = (235, 235, 255)
BOLT = (255, 230, 0)


def _sun(d: ImageDraw.ImageDraw, cx: int, cy: int, r: int = 3) -> None:
    d.ellipse((cx - r, cy - r, cx + r, cy + r), fill=SUN)
    for dx, dy in ((0, -1), (0, 1), (-1, 0), (1, 0), (-1, -1), (1, 1), (-1, 1), (1, -1)):
        k = r + 2 if dx == 0 or dy == 0 else r + 1
        d.point((cx + dx * k, cy + dy * k), fill=SUN)


def _moon(d, cx, cy) -> None:
    d.ellipse((cx - 4, cy - 4, cx + 4, cy + 4), fill=MOON)
    d.ellipse((cx - 1, cy - 6, cx + 6, cy + 2), fill=(0, 0, 0))


def _cloud(d, x, y, color=CLOUD) -> None:
    """Cloud of 13x7 with its top-left at (x, y)."""
    d.ellipse((x + 2, y + 1, x + 7, y + 6), fill=color)
    d.ellipse((x + 5, y, x + 11, y + 6), fill=color)
    d.rectangle((x, y + 4, x + 12, y + 6), fill=color)


def _drops(d, x, y, color, heavy=False) -> None:
    for i, ox in enumerate((1, 5, 9) if not heavy else (0, 3, 6, 9, 12)):
        oy = 0 if i % 2 == 0 else 1
        d.line((x + ox, y + oy, x + ox - 1, y + oy + 2), fill=color)


def _flakes(d, x, y, color=SNOW) -> None:
    for ox, oy in ((1, 0), (6, 1), (11, 0), (3, 3), (9, 3)):
        d.point((x + ox, y + oy), fill=color)


def _bolt(d, x, y) -> None:
    d.line([(x + 7, y), (x + 5, y + 2), (x + 8, y + 2), (x + 6, y + 5)], fill=BOLT)


def _draw_icon(img: Image.Image, cx: int, top: int, condition: str) -> None:
    """Draw a 13x13 icon centred on cx, starting at row `top`."""
    d = ImageDraw.Draw(img)
    x = cx - 6
    c = (condition or "").lower()
    if c == "sunny":
        _sun(d, cx, top + 6)
    elif c == "clear-night":
        _moon(d, cx, top + 6)
    elif c == "partlycloudy":
        _sun(d, cx - 2, top + 4, 3)
        _cloud(d, x + 1, top + 6)
    elif c == "cloudy":
        _cloud(d, x + 2, top + 1, DARK_CLOUD)
        _cloud(d, x, top + 5)
    elif c == "fog":
        for i, (a, b) in enumerate(((1, 11), (0, 9), (3, 12), (1, 10))):
            d.line((x + a, top + 2 + i * 3, x + b, top + 2 + i * 3), fill=CLOUD)
    elif c in ("rainy", "pouring"):
        _cloud(d, x, top)
        _drops(d, x, top + 9, RAIN, heavy=c == "pouring")
    elif c == "snowy":
        _cloud(d, x, top)
        _flakes(d, x, top + 9)
    elif c == "snowy-rainy":
        _cloud(d, x, top)
        _drops(d, x, top + 9, RAIN)
        _flakes(d, x + 2, top + 10)
    elif c == "hail":
        _cloud(d, x, top)
        for ox in (2, 6, 10):
            d.rectangle((x + ox, top + 9, x + ox + 1, top + 10), fill=SNOW)
    elif c in ("lightning", "lightning-rainy"):
        _cloud(d, x, top, DARK_CLOUD)
        _bolt(d, x, top + 7)
        if c == "lightning-rainy":
            _drops(d, x - 1, top + 9, RAIN)
    elif c in ("windy", "windy-variant"):
        for i, (a, b) in enumerate(((0, 9), (2, 12), (0, 7))):
            y = top + 3 + i * 3
            d.line((x + a, y, x + b, y), fill=CLOUD)
            d.point((x + b + 1, y - 1), fill=CLOUD)
    else:
        _draw_text(img, cx, top + 4, "?", CLOUD)


# ---------------------------------------------------------------- view
LABEL = (200, 200, 200)
TEMP_HIGH = (255, 140, 0)
TEMP_LOW = (90, 150, 255)


def _deg(value) -> str:
    try:
        return f"{round(float(value))}°"
    except (TypeError, ValueError):
        return "-"


def _day_label(value) -> str:
    try:
        if isinstance(value, str):
            value = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return _DAYS[value.astimezone().weekday()]
    except Exception:
        return "?"


def render_weather_png(condition, temperature, forecast: list[dict], width: int) -> bytes:
    """Column 1 = now; following columns = daily forecast starting today."""
    columns = max(1, width // 32)
    img = Image.new("RGB", (width, 32), (0, 0, 0))

    cells = [("NU", condition, _deg(temperature), None)]
    for item in forecast[: columns - 1]:
        cells.append((
            item.get("day") or _day_label(item.get("datetime")),
            item.get("condition"),
            _deg(item.get("temperature")),
            _deg(item.get("templow")) if item.get("templow") is not None else None,
        ))

    for i, (label, cond, high, low) in enumerate(cells):
        cx = i * 32 + 16
        _draw_text(img, cx, 1, label, LABEL)
        _draw_icon(img, cx, 7, cond)
        if low is None:
            _draw_text(img, cx, 24, high, TEMP_HIGH)
        else:
            _draw_text(img, cx, 21, high, TEMP_HIGH)
            _draw_text(img, cx, 27, low, TEMP_LOW)

    buffer = io.BytesIO()
    img.save(buffer, format="PNG")
    return buffer.getvalue()
