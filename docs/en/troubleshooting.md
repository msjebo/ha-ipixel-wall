# Troubleshooting

[← Back to the README](../../README.md) · [Nederlands](../nl/problemen.md) | **English**

| Symptom | Cause | Fix |
|---|---|---|
| **iPIXEL Wall** isn't listed under *Add integration* | Integration not copied correctly, or browser cache | Check that `custom_components/ipixel_wall/manifest.json` exists, restart Home Assistant, Ctrl+F5 |
| The log mentions the integration several times | Backup folders inside `custom_components` | Move `ipixel_wall_backup*` outside `custom_components` |
| *Setup failed* | A panel isn't loaded in iPIXEL Color | Check the panels in iPIXEL Color, then reload iPIXEL Wall |
| Panels sometimes stay empty or show half-loaded images | Several automations write to the wall or to the individual panels at once | Use **one** automation for the wall |
| Animations aren't in sync | A GIF isn't streamed (`stream: false`) or `STREAM_GIFS = False` | Keep streaming enabled |
| Animations stutter or run slower | Bluetooth can't keep up (`te laat:` in the log) | Raise `STREAM_MIN_FRAME_MS` (e.g. to 200 or 250) and use fewer colours and frames. Bluetooth proxies only help with range: with 4 streaming panels an ESP32 proxy can keep dropping connections, and the built-in adapter is often more stable |
| *GIF has N frames; maximum is …* | GIF too long | Shorten the GIF or raise `MAX_GIF_FRAMES` |
| *weather.… not found* | Wrong entity name | Look it up with `{{ states.weather \| map(attribute='entity_id') \| list }}` |
| `[vast]` is shown literally | Space or line break before the prefix | Use `-%}` in the template, or put `[vast]` at the very start of the value |
| Old images appear after powering on | Stored slots on the panels | Button **Opstartbeeld zwart maken**, then **Paneelgeheugen volledig wissen** if needed |
| *Bluetooth send failed for panel N* | Connection briefly lost | Usually recovers by itself; if it keeps happening, reload the panel in iPIXEL Color or power-cycle it |
| Casting to the TV fails (*requires HTTPS*) | Home Assistant isn't reachable over https | Use a dashboard app on the TV (see [Dashboard](dashboard.md)) |

## Useful commands (Umbrel)

```bash
# Version
grep '"version"' /home/umbrel/umbrel/app-data/home-assistant/data/custom_components/ipixel_wall/manifest.json

# Messages from the wall
sudo docker logs --since 10m home-assistant_server_1 2>&1 | grep -iA15 "ipixel_wall" | grep -v "has not been tested"

# Restart Home Assistant
sudo docker restart home-assistant_server_1
```
