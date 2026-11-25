# How it works

[← Back to the README](../../README.md) · [Nederlands](../nl/techniek.md) | **English**

## Structure

```
custom_components/ipixel_wall/
├── __init__.py        load the configuration, attach the panels to the iPIXEL Color API
├── config_flow.py     setup and options (3 or 4 panels)
├── const.py           settings (see below)
├── manager.py         uploading, streaming, transitions, preview, boot memory
├── render.py          render and split text, images, GIFs, clock and transitions
├── dmd_font.py        DMD pixel font
├── weather_render.py  weather view with pixel-art icons
├── text.py / media_player.py / select.py / number.py / light.py / camera.py / button.py
└── translations/      Dutch and English
```

The integration reuses the existing connections of **iPIXEL Color** and sends each panel its own
32x32 image.

## The synchronisation problem

Every iPIXEL panel plays a GIF on its **own clock**, and Home Assistant has no control over it.
If you upload three parts of a GIF, the panels drift out of step. This was investigated, with
these findings:

| Attempt | Result |
|---|---|
| Make the uploads finish together (last packet at the same time) | Better, but the panels still start offset |
| Give every panel exactly the same frame structure | Needed, but not enough |
| Power all panels off and on after the upload | Power-on commands arrive within 250 ms, but the panels start seconds apart |
| **Stream the frames from Home Assistant** | **Always in sync**: there's only one clock |

That's why GIFs are **streamed** by default. Home Assistant plays the animation and sends each
frame as a PNG tile to the panels. Only panels whose image changes receive a new frame.

### Bluetooth limits

- The minimum frame time is `STREAM_MIN_FRAME_MS = 150`, roughly 6-7 frames per second. Each panel
  confirms every image before it gets the next one, so a frame that takes longer only arrives late.
  Only panels whose image changes are sent a new frame, so calm GIFs need less time than busy ones. Shorter frames are merged, so fast
  GIFs keep their duration but have fewer frames.
- When streaming, iPIXEL Color's regular `send_command` is bypassed. That one toggles
  notifications off and on for every packet and waits up to 2 seconds for a reply. Instead, data
  is written directly to the write characteristic.
- For regular uploads (text in scroll mode, `stream: false`) the packets go to the panels in turn,
  so the final packets arrive at the same time.

### Re-encoding by pypixelcolor

The `pypixelcolor` library re-encodes every image, even when it's already 32x32. In doing so it
merges identical frames, and a panel with a single frame even makes it crash. The integration
therefore replaces `pypixelcolor.commands.send_image._resize_image` at load time with a version
that passes exact 32x32 images through unchanged.

## Storage on the panels

| Slot | Contents |
|---|---|
| 0 | What the wall sends: displayed, not stored |
| 1 and up | Stored images, for example from the iPIXEL app; these are shown after powering on |

- **Opstartbeeld zwart maken** erases slots 1-16 with `delete(n)` and stores a black image in
  slot 1.
- **Paneelgeheugen volledig wissen** uses `clear()`. That erases everything, including the panel
  settings.

## Settings in `const.py`

| Constant | Default | |
|---|---|---|
| `MAX_GIF_FRAMES` | 2500 | Maximum number of frames per GIF |
| `MAX_MEDIA_BYTES` | 10 MB | Maximum file size |
| `STREAM_GIFS` | `True` | Stream GIFs by default |
| `STREAM_MIN_FRAME_MS` | 150 | Default for the **Frametijd animaties** slider (minimum frame time when streaming); raise to 200 or 250 if frames are often late (`te laat` in the log) |
| `STREAM_WRITE_MODE` | `chunked_noack` | How stream frames are written: `chunked_noack` (fastest), `chunked` (response per 244-byte chunk) or `single` (one long write) |
| `STREAM_ACK_TIMEOUT` | 1.0 | Max. seconds to wait for a panel to confirm an image while streaming |
| `PANEL_START_OFFSETS_MS` | `(0, 0, 0, 0)` | Delay per panel for the resync after a regular GIF upload |

Restart Home Assistant after a change. These files are overwritten by an update.

## Log

With log level `info` (see [Installation](installation.md)) you'll see, among other things:

- `Synced upload: … packets per panel … failed: none`: a regular upload;
- `Streaming start: N frames` and `Stream loop: N frames in X s (doel Y s), te laat: Z`: the stream
  ("doel" = target, "te laat" = late). If X is far above Y, Bluetooth can't keep up;
- `Panel N: stored slots cleared, black boot screen saved`: the boot screen has been set.
