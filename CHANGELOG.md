# Changelog

[Nederlands](CHANGELOG.nl.md) | **English**

## 0.8.0 (2026-11-25)
- New option `extra.panel` for `play_media`: places an image (with `fit`) on one panel instead of in the middle, e.g. an artist photo on panel 2

## 0.7.9 (2026-11-25)
- Fix: images that miss a few bytes at the end (such as some Deezer artist photos) gave "image file is truncated"; they are now shown

## 0.7.8 (2026-11-25)
- New slider `number.ipixel_wall_frametijd_animaties` to set the minimum time per animation frame (50-500 ms) from the dashboard; the value is kept after a restart

## 0.7.7 (2026-11-19)
- Faster animations: the minimum frame time when streaming is now 150 ms instead of 250 ms (`STREAM_MIN_FRAME_MS`). Thanks to the panel acknowledgements from 0.7.6 this no longer causes black panels

## 0.7.6 (2026-11-18)
- Fix: a panel could go black for a moment during a GIF. While streaming, the next image is only sent after the panel confirms it received the previous one (`STREAM_ACK_TIMEOUT`)

## 0.7.5 (2026-11-18)
- Fix: panels could keep showing parts of the previous animation. A running stream is now stopped between two frames instead of in the middle of a write

## 0.7.4 (2026-11-17)
- Fix: after a transition a panel could keep showing the previous item. The final image is now sent with acknowledgements, and streams refresh every panel once per loop

## 0.7.3 (2026-11-17)
- Faster streaming: frames are written in 244-byte chunks without a response per chunk (`STREAM_WRITE_MODE`), with automatic fallback per panel

## 0.7.2 (2026-11-17)
- Battery glyph `🔋` in the DMD font

## 0.7.1 (2026-11-13)
- Preparation for the HACS default list: brand icon, validation workflow (HACS + hassfest), `ipixel_color` as `after_dependencies`

## 0.7.0 (2026-11-13)
- TV view `camera.ipixel_wall_preview_tv` (16:9): clock on top, the wall in the middle, weather below

## 0.6.3 (2026-11-13)
- Fix: a panel could stay black after a transition. Transitions now respect the panels' minimum frame time and resend the final image once

## 0.6.2 (2026-11-13)
- Lightning glyph `⚡` in the DMD font (e.g. for charging)

## 0.6.1 (2026-11-13)
- Documentation in English and Dutch

## 0.6.0 (2026-11-13)
- First version in this repository, with HACS support and documentation
- Default transition is now `dissolve`

## 0.5.2
- Button **Paneelgeheugen volledig wissen** (factory reset of the panel memory)

## 0.5.1
- Button **Opstartbeeld zwart maken**: erases the stored slots and stores a black boot screen

## 0.5.0
- Transitions: `wipe`, `slide`, `dissolve`, `drop`; selector and `extra.transition`
- The wall tracks what's on each panel, so unchanged panels aren't sent again

## 0.4.3
- Preview cameras follow the actual position of the stream

## 0.4.2
- Preview cameras for 3 and 4 panels, independent of the configuration

## 0.4.1
- DMD clock (`clock`, `clock:big`) with blinking colon
- Improved letter V

## 0.4.0
- DMD pixel font for all text; automatic size plus `[fs=N]` and `[ttf]`
- DMD-style marquee

## 0.3.x
- Support for 3 or 4 panels, with an options screen to add or remove panel 4
- `[vast]` text with a fixed font size, and two lines with `|`
- Camera entities as a source, cropping with `extra.crop`, `extra.resize_mode`
- Weather forecast with pixel-art icons
- Preview camera for the dashboard
- Streaming GIFs for synchronised playback
- Identical frame structure per panel; re-encoding by pypixelcolor bypassed
- Uploads that finish in sync, retries and connection recovery

## 0.2.0
- Experimental first version (3 panels, 96x32)
