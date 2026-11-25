"""Operations that render and send content to the 3 or 4 iPIXEL panels."""
from __future__ import annotations

import asyncio
import logging

from PIL import Image

from custom_components.ipixel_color.device.image import make_image_command

from .const import PANEL_WIDTH, PANEL_HEIGHT
from .render import (
    render_static_text,
    render_scrolling_text_gif,
    split_png,
    split_gif,
)

_LOGGER = logging.getLogger(__name__)

# --- Skip pypixelcolor's re-encode when a tile is already panel-sized ---
import io as _io
import pypixelcolor.commands.send_image as _pp_send_image

_orig_resize_image = _pp_send_image._resize_image


def _resize_passthrough(file_bytes, is_gif, width, height, *args, **kwargs):
    try:
        with Image.open(_io.BytesIO(file_bytes)) as _im:
            if _im.size == (width, height):
                return file_bytes
    except Exception:
        pass
    return _orig_resize_image(file_bytes, is_gif, width, height, *args, **kwargs)


if getattr(_pp_send_image._resize_image, "__name__", "") != "_resize_passthrough":
    _pp_send_image._resize_image = _resize_passthrough
# -------------------------------------------------------------------------


async def _prepare_panel(panel_index: int, api, image_bytes: bytes, extension: str) -> list[bytes]:
    """Connect, validate and build the upload commands for one panel."""
    if not api.is_connected:
        await api.connect()
    info = await api.get_device_info()
    if not info or info.get("width") != PANEL_WIDTH or info.get("height") != PANEL_HEIGHT:
        raise ValueError(
            f"Panel {panel_index} must report 32x32; got "
            f"{info.get('width') if info else 'unknown'}x"
            f"{info.get('height') if info else 'unknown'}"
        )
    return make_image_command(
        image_bytes=image_bytes,
        file_extension=extension,
        resize_method="fit",
        device_info_dict=info,
    )


async def _send_commands(panel_index: int, api, commands: list[bytes]) -> None:
    """Send a list of commands to one panel in order."""
    api._wall_ack_client = None  # send_command replaces the notify handler
    for command in commands:
        success = await api._bluetooth.send_command(command)
        if not success:
            raise RuntimeError(f"Bluetooth send failed for panel {panel_index}")


async def _reset_connection(api) -> None:
    """Force a clean Bluetooth state so the next attempt builds a fresh connection."""
    bt = api._bluetooth
    client = getattr(bt, "_client", None)
    if client is not None:
        try:
            await client.disconnect()
        except Exception:
            pass
    bt._connected = False
    bt._client = None


async def _prepare_with_retry(i: int, api, tile: bytes, extension: str) -> list[bytes]:
    """Connect and build commands for one panel, with retry."""
    for attempt in range(1, 4):
        try:
            return await _prepare_panel(i, api, tile, extension)
        except Exception as err:
            _LOGGER.warning("Panel %s prepare attempt %s failed: %s", i, attempt, err)
            await _reset_connection(api)
            await asyncio.sleep(2)
    raise RuntimeError(f"Panel {i} prepare failed after 3 attempts")


async def _full_upload(i: int, api, tile: bytes, extension: str) -> None:
    """Complete, unsynchronized upload as fallback."""
    for attempt in range(1, 4):
        try:
            cmds = await _prepare_panel(i, api, tile, extension)
            await _send_commands(i, api, cmds)
            _LOGGER.info("Panel %s: fallback upload ok (attempt %s)", i, attempt)
            return
        except Exception as err:
            _LOGGER.warning("Panel %s fallback attempt %s failed: %s", i, attempt, err)
            await _reset_connection(api)
            await asyncio.sleep(2)
    _LOGGER.error("Panel %s: giving up after 3 fallback attempts", i)


async def _resync_start(apis: list) -> None:
    """Power-cycle all panels; power-on per panel delayed by a calibrated offset."""
    from . import const as _const
    offsets = getattr(_const, "PANEL_START_OFFSETS_MS", ())

    await asyncio.gather(*(api.set_power(False) for api in apis), return_exceptions=True)
    await asyncio.sleep(2)

    loop = asyncio.get_running_loop()
    t0 = loop.time() + 0.05
    timings = {}

    async def _on(i: int, api, offset_ms: int) -> None:
        await asyncio.sleep(max(0.0, t0 + offset_ms / 1000 - loop.time()))
        sent = (loop.time() - t0) * 1000
        try:
            await api.set_power(True)
        except Exception as err:
            _LOGGER.warning("Panel %s power-on failed: %s", i, err)
        timings[i] = (round(sent), round((loop.time() - t0) * 1000))

    await asyncio.gather(
        *(_on(i, api, offsets[i - 1] if i - 1 < len(offsets) else 0)
          for i, api in enumerate(apis, start=1))
    )
    _LOGGER.info("Resync power-on (verzonden ms, klaar ms): %s", dict(sorted(timings.items())))


async def _send_tiles(data: dict, tiles: list[bytes], extension: str) -> None:
    """Round-robin upload, end-aligned so all panels receive their final packet together."""
    async with data["lock"]:
        panels = list(enumerate(data["apis"], start=1))
        prepared = await asyncio.gather(
            *(_prepare_with_retry(i, api, tile, extension) for (i, api), tile in zip(panels, tiles))
        )
        total = max(len(c) for c in prepared)
        failed: set[int] = set()
        loop = asyncio.get_running_loop()
        started = loop.time()

        for step in range(total):
            jobs, owners = [], []
            for (i, api), cmds in zip(panels, prepared):
                offset = total - len(cmds)
                if i not in failed and step >= offset:
                    jobs.append(_send_commands(i, api, [cmds[step - offset]]))
                    owners.append(i)
            results = await asyncio.gather(*jobs, return_exceptions=True)
            for i, result in zip(owners, results):
                if isinstance(result, Exception):
                    _LOGGER.warning("Panel %s packet %s failed: %s", i, step, result)
                    failed.add(i)

        _LOGGER.info(
            "Synced upload: %s packets per panel %s in %.1fs, failed: %s",
            total, [len(c) for c in prepared], loop.time() - started, sorted(failed) or "none",
        )

        for (i, api), tile in zip(panels, tiles):
            if i in failed:
                await _reset_connection(api)
                await _full_upload(i, api, tile, extension)

        if extension == ".gif":
            await _resync_start(data["apis"])
        data["panel_png"] = list(tiles) if extension == ".png" else [None] * len(tiles)


async def async_show_text(hass, data: dict) -> None:
    """Display text using static PNG or device-native GIF marquee."""
    await _stop_stream(data)

    data["media_type"] = None
    data["media_title"] = None
    if not data["text"]:
        return

    if data["mode"] == "scroll":
        frames, durations, loop = await hass.async_add_executor_job(
            render_scrolling_text_gif,
            data["text"],
            data["text_color"],
            data["background_color"],
            data["scroll_interval"],
            data["width"],
        )
        _set_preview(data, frames, durations)
        _text, _tc, _bg, _iv = data["text"], data["text_color"], data["background_color"], data["scroll_interval"]
        _set_preview_src(data, lambda w: render_scrolling_text_gif(_text, _tc, _bg, _iv, w)[:2])
        tiles = await hass.async_add_executor_job(split_gif, frames, durations, loop)
        await _send_tiles(data, tiles, ".gif")
        data["wall_canvas"] = None
        return

    png = await hass.async_add_executor_job(
        render_static_text,
        data["text"],
        data["text_color"],
        data["background_color"],
        data["width"],
    )
    from PIL import Image
    import io
    canvas = Image.open(io.BytesIO(png)).convert("RGB")
    shown = await _play_transition(hass, data, canvas)
    _set_preview(data, [canvas])
    _text, _tc, _bg = data["text"], data["text_color"], data["background_color"]
    _set_preview_src(data, lambda w: ([Image.open(io.BytesIO(render_static_text(_text, _tc, _bg, w))).convert("RGB")], None))
    if not shown:
        tiles = await hass.async_add_executor_job(split_png, canvas)
        await _send_tiles(data, tiles, ".png")
    data["wall_canvas"] = canvas


async def async_show_image(
    hass,
    data: dict,
    raw: bytes,
    resize_mode: str = "fit",
    media_title: str | None = None,
    stream: bool | None = None,
    crop=None,
    source=None,
    transition=None,
    panel=None,
) -> None:
    """Display an uploaded or downloaded image/GIF over the whole wall."""
    from .render import prepare_image_frames

    frames, durations, loop, is_gif = await hass.async_add_executor_job(
        prepare_image_frames,
        raw,
        resize_mode,
        data["background_color"],
        data["width"],
        crop,
        panel,
    )
    await _stop_stream(data)
    shown = await _play_transition(hass, data, frames[0], transition)
    _set_preview(data, frames, durations if is_gif else None)
    _src, _bg = source or (lambda w: raw), data["background_color"]
    _set_preview_src(data, lambda w: prepare_image_frames(_src(w), resize_mode, _bg, w, crop, panel)[:2])
    if stream is None:
        stream = getattr(_const, "STREAM_GIFS", False)
    if is_gif and stream:
        await async_stream_frames(hass, data, frames, durations)
        data["media_type"] = "image/gif"
        data["media_title"] = media_title or "iPIXEL Wall image"
        data["text"] = ""
        return
    await _stop_stream(data)
    if is_gif:
        tiles = await hass.async_add_executor_job(split_gif, frames, durations, loop)
        await _send_tiles(data, tiles, ".gif")
        data["wall_canvas"] = frames[0]
        data["media_type"] = "image/gif"
    else:
        if not shown:
            tiles = await hass.async_add_executor_job(split_png, frames[0])
            await _send_tiles(data, tiles, ".png")
        data["wall_canvas"] = frames[0]
        data["media_type"] = "image/png"

    data["media_title"] = media_title or "iPIXEL Wall image"
    data["text"] = ""
    await _stop_stream(data)


async def async_clear_wall(data: dict) -> None:
    """Clear all panels with a black PNG."""
    canvas = Image.new("RGB", (data["width"], PANEL_HEIGHT), (0, 0, 0))
    _set_preview(data, [canvas])
    _set_preview_src(data, lambda w: ([Image.new("RGB", (w, PANEL_HEIGHT), (0, 0, 0))], None))
    await _send_tiles(data, split_png(canvas), ".png")
    data["wall_canvas"] = canvas


# ===================== Streaming mode =====================
from custom_components.ipixel_color.bluetooth import client as _bt_client
from . import const as _const


def _merge_min(frames, durations, min_ms):
    out_f, out_d = [], []
    for f, d in zip(frames, durations):
        if out_d and out_d[-1] < min_ms:
            out_d[-1] += d
        else:
            out_f.append(f)
            out_d.append(d)
    return out_f, out_d


def _build_stream_commands(frames, infos):
    cache = {}
    per_frame = []
    for frame in frames:
        row = []
        for i, png in enumerate(split_png(frame)):
            key = (i, png)
            if key not in cache:
                cache[key] = make_image_command(
                    image_bytes=png, file_extension=".png",
                    resize_method="fit", device_info_dict=infos[i],
                )
            row.append((png, cache[key]))
        per_frame.append(row)
    return per_frame


async def _fast_write(api, commands) -> None:
    """Write without the notify/response dance of send_command.

    STREAM_WRITE_MODE (const.py):
      "chunked_noack" – 244-byte chunks without a GATT response per chunk (fastest)
      "chunked"       – 244-byte chunks with a response per chunk (as pypixelcolor does)
      "single"        – one long write per command (the original behaviour)
    A panel that fails in "chunked_noack" falls back to "chunked" automatically.
    """
    if not api.is_connected:
        await api.connect()
    client = api._bluetooth._client
    mode = getattr(api, "_wall_write_mode", None) or getattr(_const, "STREAM_WRITE_MODE", "chunked_noack")
    if mode == "single":
        for cmd in commands:
            await client.write_gatt_char(_bt_client.WRITE_UUID, cmd)
        return
    listening = await _ensure_ack_listener(api, client)
    try:
        for cmd in commands:
            if listening:
                api._wall_ack.clear()
            for pos in range(0, len(cmd), 244):
                await client.write_gatt_char(
                    _bt_client.WRITE_UUID, cmd[pos:pos + 244], response=(mode != "chunked_noack")
                )
            if listening:
                # the panel reports when it has the whole image; sending the next one
                # earlier makes it drop the image and show black
                try:
                    await asyncio.wait_for(
                        api._wall_ack.wait(), getattr(_const, "STREAM_ACK_TIMEOUT", 1.0)
                    )
                except asyncio.TimeoutError:
                    _LOGGER.debug("No ack from panel within timeout")
    except Exception:
        if mode == "chunked_noack":
            _LOGGER.warning("Write without response failed; this panel falls back to chunked writes")
            api._wall_write_mode = "chunked"
        raise


def _min_frame_ms(data) -> int:
    """Minimum frame time: the dashboard setting, else the constant."""
    value = data.get("min_frame_ms")
    return int(value) if value else getattr(_const, "STREAM_MIN_FRAME_MS", 150)


async def _stream_loop(data, per_frame, durations, key=None, frames=None, stop=None) -> None:
    apis = data["apis"]
    last = list(data.get("panel_png") or [None] * len(apis))
    ev = asyncio.get_running_loop()
    try:
        loops = 0
        while True:
            if loops:
                last = [None] * len(apis)  # keyframe: refresh every panel once per loop
            loops += 1
            start = ev.time()
            t = start
            late = 0
            pos = 0.0
            for idx, (row, dur) in enumerate(zip(per_frame, durations)):
                if stop is not None and stop.is_set():
                    return
                jobs, owners = [], []
                for i, (api, (png, cmds)) in enumerate(zip(apis, row)):
                    if png != last[i]:
                        jobs.append(_fast_write(api, cmds))
                        owners.append(i)
                if jobs:
                    async with data["lock"]:
                        results = await asyncio.gather(*jobs, return_exceptions=True)
                    for i, res in zip(owners, results):
                        if isinstance(res, Exception):
                            _LOGGER.warning("Stream panel %s failed: %s", i + 1, res)
                            last[i] = None
                            await _reset_connection(apis[i])
                        else:
                            last[i] = row[i][0]
                data["preview_anchor"] = (key, ev.time() - pos / 1000)
                if frames is not None:
                    data["wall_canvas"] = frames[idx]
                data["panel_png"] = list(last)
                pos += dur
                t += dur / 1000
                wait = t - ev.time()
                if wait > 0:
                    if stop is not None:
                        try:
                            await asyncio.wait_for(stop.wait(), timeout=wait)
                            return
                        except asyncio.TimeoutError:
                            pass
                    else:
                        await asyncio.sleep(wait)
                else:
                    late += 1
                    t = ev.time()
            _LOGGER.info(
                "Stream loop: %s frames in %.1fs (doel %.1fs), te laat: %s",
                len(per_frame), ev.time() - start, sum(durations) / 1000, late,
            )
    except asyncio.CancelledError:
        raise
    except Exception:
        _LOGGER.exception("Stream stopped")


async def async_stream_frames(hass, data, frames, durations) -> None:
    await _stop_stream(data)
    min_ms = _min_frame_ms(data)
    frames, durations = _merge_min(frames, durations, min_ms)
    infos = []
    for api in data["apis"]:
        if not api.is_connected:
            await api.connect()
        infos.append(await api.get_device_info())
    per_frame = await hass.async_add_executor_job(_build_stream_commands, frames, infos)
    _LOGGER.info("Streaming start: %s frames, min %s ms", len(per_frame), min_ms)
    stop = asyncio.Event()
    data["stream_stop"] = stop
    data["task"] = hass.async_create_background_task(
        _stream_loop(data, per_frame, durations, (data.get("preview") or (None, None, None))[2], frames, stop),
        "ipixel_wall_stream"
    )


# ===================== Dashboard preview =====================
import time as _time


def _set_preview(data, frames, durations=None) -> None:
    """Remember what the wall shows, for the preview camera."""
    data["preview"] = (list(frames), list(durations or [1000] * len(frames)), _time.monotonic())


def _set_preview_src(data, render) -> None:
    """Remember how to re-render the current content at another wall width."""
    data["preview_src"] = (render, data["preview"][2])


# ===================== Transitions =====================
from .render import transition_frames as _transition_frames


async def _device_infos(data) -> list:
    infos = []
    for api in data["apis"]:
        if not api.is_connected:
            await api.connect()
        infos.append(await api.get_device_info())
    return infos


async def _play_transition(hass, data, new_frame, kind=None) -> bool:
    """Animate from what the wall shows to new_frame. True when new_frame is now on all panels."""
    kind = (kind or data.get("transition") or "none").lower()
    old = data.get("wall_canvas")
    new_frame = new_frame.convert("RGB")
    if kind == "none" or old is None or old.size != new_frame.size:
        return False
    try:
        frames, frame_ms = await hass.async_add_executor_job(_transition_frames, old, new_frame, kind)
        if not frames:
            return False
        infos = await _device_infos(data)
        per_frame = await hass.async_add_executor_job(_build_stream_commands, frames, infos)
    except Exception as err:
        _LOGGER.warning("Transition skipped: %s", err)
        return False

    apis = data["apis"]
    last = list(data.get("panel_png") or [None] * len(apis))
    ev = asyncio.get_running_loop()
    # never faster than the panels can decode; too-fast frames get dropped (black panel)
    frame_ms = max(frame_ms, _min_frame_ms(data))
    t = ev.time()
    for frame, row in zip(frames, per_frame):
        jobs, owners = [], []
        for i, (api, (png, cmds)) in enumerate(zip(apis, row)):
            if png != last[i]:
                jobs.append(_fast_write(api, cmds))
                owners.append(i)
        if jobs:
            async with data["lock"]:
                results = await asyncio.gather(*jobs, return_exceptions=True)
            for i, res in zip(owners, results):
                if isinstance(res, Exception):
                    _LOGGER.warning("Transition panel %s failed: %s", i + 1, res)
                    last[i] = None
                    await _reset_connection(apis[i])
                else:
                    last[i] = row[i][0]
        data["wall_canvas"] = frame
        t += frame_ms / 1000
        wait = t - ev.time()
        if wait > 0:
            await asyncio.sleep(wait)
        else:
            t = ev.time()
    # settle: send the final image once more WITH acknowledgements, so a panel that
    # dropped a fast (unacknowledged) frame is guaranteed to show the right picture
    await asyncio.sleep(0.2)
    data["panel_png"] = last
    try:
        await _send_tiles(data, [png for png, _ in per_frame[-1]], ".png")
    except Exception as err:
        _LOGGER.warning("Transition settle failed: %s", err)
        return False
    return True


# ===================== Boot screen =====================
BOOT_SLOTS_TO_CLEAR = 16


def _plan_bytes(plan) -> list[bytes]:
    return [window.data for window in plan.windows]


def _delete_slot_cmds(slot: int) -> list[bytes]:
    from pypixelcolor.commands.delete import delete
    return _plan_bytes(delete(slot))


def _black_slot_cmds(info: dict, slot: int = 1) -> list[bytes]:
    """Commands that store a black image in `slot` (shown when the panel boots)."""
    from pypixelcolor.commands.send_image import send_image_hex
    from pypixelcolor.lib.device_info import DeviceInfo

    buffer = _io.BytesIO()
    Image.new("RGB", (PANEL_WIDTH, PANEL_HEIGHT), (0, 0, 0)).save(buffer, format="PNG")
    device_info = DeviceInfo(
        device_type=info.get("device_type", 0),
        mcu_version=info.get("mcu_version", "Unknown"),
        wifi_version=info.get("wifi_version", "Unknown"),
        width=info["width"],
        height=info["height"],
        has_wifi=info.get("has_wifi", False),
        password_flag=info.get("password_flag", 255),
        led_type=info.get("led_type", None),
    )
    plan = send_image_hex(
        hex_string=buffer.getvalue().hex(), file_extension=".png",
        resize_method="fit", device_info=device_info, save_slot=slot,
    )
    return _plan_bytes(plan)


async def async_reset_boot_memory(hass, data) -> None:
    """Delete stored slots on every panel, store black in slot 1, then restore the wall."""
    await _stop_stream(data)

    async def _one(i, api, info):
        for slot in range(1, BOOT_SLOTS_TO_CLEAR + 1):
            await _send_commands(i, api, _delete_slot_cmds(slot))
        cmds = await hass.async_add_executor_job(_black_slot_cmds, info)
        await _send_commands(i, api, cmds)

    async with data["lock"]:
        infos = await _device_infos(data)
        results = await asyncio.gather(
            *(_one(i, api, info) for i, (api, info) in enumerate(zip(data["apis"], infos), start=1)),
            return_exceptions=True,
        )
    for i, result in enumerate(results, start=1):
        if isinstance(result, Exception):
            _LOGGER.warning("Boot memory reset failed for panel %s: %s", i, result)
        else:
            _LOGGER.info("Panel %s: stored slots cleared, black boot screen saved", i)

    # show what belongs on the wall again
    data["panel_png"] = [None] * len(data["apis"])
    canvas = data.get("wall_canvas")
    if canvas is None:
        canvas = Image.new("RGB", (data["width"], PANEL_HEIGHT), (0, 0, 0))
    await _send_tiles(data, split_png(canvas), ".png")



def _clear_cmds() -> list[bytes]:
    from pypixelcolor.commands.clear import clear
    return _plan_bytes(clear())


async def async_factory_reset(hass, data) -> None:
    """Wipe ALL stored content (and device settings), then store a black boot screen."""
    await _stop_stream(data)

    async with data["lock"]:
        infos = await _device_infos(data)

        async def _wipe(i, api):
            await _send_commands(i, api, _clear_cmds())

        results = await asyncio.gather(
            *(_wipe(i, api) for i, api in enumerate(data["apis"], start=1)), return_exceptions=True
        )
        for i, result in enumerate(results, start=1):
            if isinstance(result, Exception):
                _LOGGER.warning("Factory wipe failed for panel %s: %s", i, result)
            else:
                _LOGGER.info("Panel %s: memory wiped", i)

        # panels may restart after a wipe: reconnect cleanly before continuing
        await asyncio.sleep(5)
        for api in data["apis"]:
            await _reset_connection(api)

        async def _black(i, api, info):
            for attempt in range(1, 4):
                try:
                    if not api.is_connected:
                        await api.connect()
                    cmds = await hass.async_add_executor_job(_black_slot_cmds, info)
                    await _send_commands(i, api, cmds)
                    _LOGGER.info("Panel %s: black boot screen saved", i)
                    return
                except Exception as err:
                    _LOGGER.warning("Panel %s boot screen attempt %s failed: %s", i, attempt, err)
                    await _reset_connection(api)
                    await asyncio.sleep(3)

        await asyncio.gather(
            *(_black(i, api, info) for i, (api, info) in enumerate(zip(data["apis"], infos), start=1))
        )

    data["panel_png"] = [None] * len(data["apis"])
    canvas = data.get("wall_canvas")
    if canvas is None:
        canvas = Image.new("RGB", (data["width"], PANEL_HEIGHT), (0, 0, 0))
    await _send_tiles(data, split_png(canvas), ".png")


async def _stop_stream(data) -> None:
    """Stop a running stream between two frames, never in the middle of a write.

    Cutting a write off half-way leaves a panel waiting for the rest of the image;
    it then misreads the next image and keeps showing the old one.
    """
    task = data.get("task")
    data["task"] = None
    if task is None or task.done():
        return
    stop = data.get("stream_stop")
    if stop is not None:
        stop.set()
    try:
        await asyncio.wait_for(asyncio.shield(task), timeout=5)
    except asyncio.TimeoutError:
        _LOGGER.warning("Stream did not stop in time; cancelling it")
        task.cancel()
        try:
            await task
        except (asyncio.CancelledError, Exception):
            pass
    except Exception:
        pass


def _ack_handler(api):
    """Notification handler that flags panel acks and still feeds the original handler."""
    original = getattr(api, "_notification_handler", None)

    def handler(sender, data):
        try:
            if data and len(data) > 4 and data[0] == 0x05 and data[4] in (0, 1, 3):
                event = getattr(api, "_wall_ack", None)
                if event is not None:
                    event.set()
        finally:
            if original is not None:
                try:
                    original(sender, data)
                except Exception:
                    pass

    return handler


async def _ensure_ack_listener(api, client) -> bool:
    """Make sure panel acknowledgements reach us (once per connection)."""
    if getattr(api, "_wall_ack_client", None) is client and getattr(api, "_wall_ack", None):
        return True
    try:
        try:
            await client.stop_notify(_bt_client.NOTIFY_UUID)
        except Exception:
            pass
        api._wall_ack = asyncio.Event()
        await client.start_notify(_bt_client.NOTIFY_UUID, _ack_handler(api))
        api._wall_ack_client = client
        return True
    except Exception as err:
        _LOGGER.debug("Could not listen for panel acks: %s", err)
        api._wall_ack_client = None
        return False
