from homeassistant.const import Platform

DOMAIN = "ipixel_wall"

# Panel entities, physical left-to-right order. The keys of the first three
# are kept from the original version so existing config entries keep working.
CONF_LEFT = "left_entity"
CONF_MIDDLE = "middle_entity"
CONF_RIGHT = "right_entity"
CONF_PANEL4 = "panel4_entity"
PANEL_KEYS = (CONF_LEFT, CONF_MIDDLE, CONF_RIGHT, CONF_PANEL4)
MIN_PANELS = 3
MAX_PANELS = 4

PLATFORMS = [
    Platform.TEXT,
    Platform.SELECT,
    Platform.NUMBER,
    Platform.LIGHT,
    Platform.MEDIA_PLAYER,
    Platform.CAMERA,
    Platform.BUTTON,
]

DEFAULT_TEXT_COLOR = (255, 255, 255)
DEFAULT_BG_COLOR = (0, 0, 0)

MAX_MEDIA_BYTES = 10 * 1024 * 1024
MAX_GIF_FRAMES = 2500
WALL_HEIGHT = 32
PANEL_WIDTH = 32
PANEL_HEIGHT = 32
WALL_WIDTH = PANEL_WIDTH * MIN_PANELS  # fallback only; real width = panels * 32
PANEL_START_OFFSETS_MS = (0, 0, 0, 0)  # per paneel, links naar rechts

STREAM_GIFS = True
STREAM_MIN_FRAME_MS = 250


def panel_entities(entry) -> list[str]:
    """Configured panel entity IDs in left-to-right order."""
    merged = {**entry.data, **entry.options}
    return [merged[key] for key in PANEL_KEYS if merged.get(key)]

# Weather entity for the TV view (None = first weather entity found)
TV_WEATHER_ENTITY = None

# How stream frames are written: "chunked_noack" (fastest), "chunked" or "single"
STREAM_WRITE_MODE = "chunked_noack"
