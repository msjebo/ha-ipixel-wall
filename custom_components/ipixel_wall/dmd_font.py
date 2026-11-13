"""DMD-style bitmap font for the iPIXEL wall.

Base glyphs (0x21-0x7E): LCD_FONT from luma.core (MIT licence,
(c) 2017-2021 Richard Hull and contributors), with real descenders,
a euro sign, a degree sign and accent support added.
"""
from __future__ import annotations

import unicodedata

# Column-encoded glyphs, bit 0 = top row. Characters 0x21..0x7E in order.
_LCD = "5f 030003 147f147f14 242a7f2a12 2313086462 3649552250 0503 1c2241 41221c 14083e0814 08083e0808 5030 0808080808 6060 2010080402 3e5149453e 427f40 4261514946 2141454b31 1814127f10 2745454539 3c4a494930 0171090503 3649494936 064949291e 3636 5636 08142241 1414141414 41221408 0201510906 324979413e 7e1111117e 7f49494936 3e41414122 7f4141221c 7f49494941 7f09090901 3e4149497a 7f0808087f 417f41 2040413f01 7f08142241 7f40404040 7f020c027f 7f0408107f 3e4141413e 7f09090906 3e4151215e 7f09192946 4649494931 01017f0101 3f4040403f 1f2040201f 3f4038403f 6314081463 0708700807 6151494543 7f4141 0204081020 41417f 0402010204 4040404040 010204 2054545478 7f48444438 3844444420 384444487f 3854545418 087e090102 0c5252523e 7f08040478 447d40 2040443d 7f102844 417f40 7c04180478 7c08040478 3844444438 7c14141408 081414187c 7c08040408 4854545420 043f444020 3c4040207c 1c2040201c 3c4030403c 4428102844 0c5050503c 4464544c44 083641 7f 413608 1008081008".split(" ")
_COLUMNS: dict[str, list[int]] = {
    chr(0x21 + i): [int(g[j:j + 2], 16) for j in range(0, len(g), 2)]
    for i, g in enumerate(_LCD)
}

LINE_HEIGHT = 9      # 7 rows body + 2 rows descender
BODY_HEIGHT = 7
SPACE_WIDTH = 3

# Row-drawn overrides (9 rows: body rows 0-6, descenders 7-8).
_ROWS = {
    "g": [".....", ".....", ".####", "#...#", "#...#", "#...#", ".####", "....#", ".###."],
    "p": [".....", ".....", "####.", "#...#", "#...#", "#...#", "####.", "#....", "#...."],
    "q": [".....", ".....", ".####", "#...#", "#...#", "#...#", ".####", "....#", "....#"],
    "y": [".....", ".....", "#...#", "#...#", "#...#", "#...#", ".####", "....#", ".###."],
    "j": ["...#", "....", "..##", "...#", "...#", "...#", "...#", "#..#", ".##."],
    ",": ["..", "..", "..", "..", "..", "##", "##", ".#", "#."],
    ";": ["..", "..", "##", "##", "..", "##", "##", ".#", "#."],
    "V": ["#...#", "#...#", "#...#", "#...#", "#...#", ".#.#.", "..#.."],
    "⚡": ["...##", "..##.", ".##..", "#####", "..##.", ".##..", "##..."],
    "€": ["..###", ".#...", "####.", ".#...", "####.", ".#...", "..###"],
    "°": [".#.", "#.#", ".#.", "...", "...", "...", "..."],
}
for _ch, _rows in _ROWS.items():
    _COLUMNS[_ch] = [
        sum(1 << y for y, row in enumerate(_rows) if row[x] == "#")
        for x in range(len(_rows[0]))
    ]

_REPLACE = {
    "‘": "'", "’": "'", "‚": ",", "“": '"', "”": '"',
    "„": '"', "–": "-", "—": "-", "…": "...", " ": " ",
    "«": '"', "»": '"', "ß": "ss",
}
# Accent marks drawn on row 0 above lowercase letters (x-height starts at row 2).
_ACCENTS = {
    "̈": [1, 0, 1],      # diaeresis  ë ï ö ü ä
    "́": [0, 0, 1],      # acute      é á ó
    "̀": [1, 0, 0],      # grave      è à
    "̂": [0, 1, 0],      # circumflex ê â (simplified)
    "̃": [0, 1, 1],      # tilde      ñ (simplified)
}


def _glyph(ch: str) -> list[int] | None:
    """Columns for one character; None means a space."""
    if ch == " ":
        return None
    if ch in _COLUMNS:
        return _COLUMNS[ch]
    decomposed = unicodedata.normalize("NFD", ch)
    base, marks = decomposed[0], decomposed[1:]
    columns = list(_COLUMNS.get(base, _COLUMNS["?"]))
    mark = next((_ACCENTS[m] for m in marks if m in _ACCENTS), None)
    if mark and base.islower():
        if base in "ij":
            columns = [c & ~0b11 for c in columns]          # drop the dot
            while len(columns) < len(mark):
                columns = [0] + columns
        start = max(0, (len(columns) - len(mark)) // 2)
        for k, bit in enumerate(mark):
            if bit and start + k < len(columns):
                columns[start + k] |= 1
    return columns


def normalize(text: str) -> str:
    return "".join(_REPLACE.get(ch, ch) for ch in text)


def text_columns(text: str) -> list[int]:
    """Column bitmaps for a line of text, one blank column between glyphs."""
    out: list[int] = []
    for ch in normalize(text):
        glyph = _glyph(ch)
        if glyph is None:
            out.extend([0] * SPACE_WIDTH)
        else:
            out.extend(glyph)
            out.append(0)
    if out and out[-1] == 0:
        out.pop()
    return out


def text_width(text: str, scale: int = 1) -> int:
    return len(text_columns(text)) * scale


def draw_text(img, x: int, y: int, text: str, scale: int, color) -> None:
    """Draw text with its top-left at (x, y); each font pixel becomes scale x scale."""
    px = img.load()
    width, height = img.size
    for cx, bits in enumerate(text_columns(text)):
        if not bits:
            continue
        for row in range(LINE_HEIGHT):
            if bits >> row & 1:
                for dx in range(scale):
                    for dy in range(scale):
                        xx, yy = x + cx * scale + dx, y + row * scale + dy
                        if 0 <= xx < width and 0 <= yy < height:
                            px[xx, yy] = color
