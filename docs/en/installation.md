# Installation and updating

[← Back to the README](../../README.md) · [Nederlands](../nl/installatie.md) | **English**

## Before you start

1. Install **[iPIXEL Color](https://github.com/cagcoach/ha-ipixel-color)** and add every panel.
   Check that you can show text on each panel through that integration.
2. Note the **text entity** of each panel (for example `text.led_ble_387bc42d_display`) and which
   panel hangs on the left, in the middle and on the right.

## Method 1: HACS (public repository only)

HACS **cannot install private GitHub repositories**. If this repository is public:

1. **HACS → ⋮ → Custom repositories**
2. URL: `https://github.com/msjebo/ha-ipixel-wall`, type **Integration**
3. Search for **iPIXEL Wall**, choose **Download** and restart Home Assistant.

After that, updates show up in HACS automatically.

## Method 2: manual (always works, also for a private repository)

Copy the folder `custom_components/ipixel_wall` into the `custom_components` folder of your
Home Assistant configuration and restart Home Assistant.

### On Umbrel

On Umbrel the Home Assistant configuration lives in
`/home/umbrel/umbrel/app-data/home-assistant/data/` (`/config` inside the container).

1. Download the repository as a zip (**Code → Download ZIP**) and upload it to your home folder
   with the Umbrel file browser.
2. Install or update with:

```bash
ZIP=/home/umbrel/umbrel/home/ha-ipixel-wall-main.zip      # adjust the name if needed
CC=/home/umbrel/umbrel/app-data/home-assistant/data/custom_components

rm -rf /tmp/ipw && python3 -m zipfile -e "$ZIP" /tmp/ipw
sudo rm -rf /home/umbrel/umbrel/home/ipixel_wall_backup_vorige
[ -d "$CC/ipixel_wall" ] && sudo mv "$CC/ipixel_wall" /home/umbrel/umbrel/home/ipixel_wall_backup_vorige
sudo cp -r /tmp/ipw/*/custom_components/ipixel_wall "$CC/"
sudo chown -R root:root "$CC/ipixel_wall"
grep '"version"' "$CC/ipixel_wall/manifest.json"
sudo docker restart home-assistant_server_1
```

> **Important:** **never** keep backups inside `custom_components` itself (for example
> `ipixel_wall_backup`). Home Assistant then sees two integrations with the same name and may
> load the wrong one.

### Rolling back

```bash
CC=/home/umbrel/umbrel/app-data/home-assistant/data/custom_components
sudo rm -r "$CC/ipixel_wall" && sudo mv /home/umbrel/umbrel/home/ipixel_wall_backup_vorige "$CC/ipixel_wall"
sudo docker restart home-assistant_server_1
```

## Setting up the wall

**Settings → Devices & services → Add integration → iPIXEL Wall**

| Field | |
|---|---|
| Panel 1 (left) | Text entity of the left panel |
| Panel 2 | Middle or second panel |
| Panel 3 | Third panel |
| Panel 4 (right, optional) | Leave empty for a 3-panel wall |

### Adding (or removing) a 4th panel later

1. Add the panel in **iPIXEL Color**.
2. **iPIXEL Wall → ⚙ Configure** and fill in **Panel 4**, or clear the field.
3. The wall reloads as 128x32 (or 96x32). Entities and automations keep working.

## Log level for troubleshooting

```yaml
action: logger.set_level
data:
  custom_components.ipixel_wall: info
```

Then:

```bash
sudo docker logs --since 10m home-assistant_server_1 2>&1 | grep -i ipixel_wall
```
