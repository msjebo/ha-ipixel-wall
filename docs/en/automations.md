# Automations

[← Back to the README](../../README.md) · [Nederlands](../nl/automatiseringen.md) | **English**

## Complete rotation ("attract mode")

**[examples/attract_mode.yaml](../../examples/attract_mode.yaml)** is a complete automation that
rotates every day from 08:00 to 20:00:

1. a random GIF from a folder (GIFs with `_STORY_` in their name for 60 seconds, the rest 30);
2. the clock;
3. the weather forecast;
4. the car's driving range (until 17:00);
5. a new NOS news headline (for 15 minutes);
6. on working days a logo and a team name;
7. the music that's playing, when the home-office speaker is on.

Paste it via **Create automation → ⋮ → Edit in YAML** and adapt the entities. The example uses
Dutch names and texts.

### Why it's built this way

- **`mode: restart`**: the 20:00 trigger stops the running rotation immediately.
- **Everything in one automation.** **Never let several automations write to the wall at the
  same time**, and don't write directly to the individual panels via iPIXEL Color. They overwrite
  each other, and panels stay empty or drift out of step.
- **`continue_on_error: true`**: a broken GIF or an unreachable camera doesn't stop the whole
  rotation.

## Building blocks

### GIFs from a folder, automatically

1. Create a folder, for example `/media/pinball_dmd/rotatie`.
2. Give Home Assistant access in `configuration.yaml`:
   ```yaml
   homeassistant:
     allowlist_external_dirs:
       - /media/pinball_dmd
   ```
3. Add the **Folder** integration with path `/media/pinball_dmd/rotatie` and pattern `*.gif`.
   You get `sensor.rotatie` with the attribute `file_list`.

New GIFs in the folder join the rotation within about a minute.

### Duration based on the file name

```yaml
- delay:
    seconds: "{{ 60 if '_STORY_' in (gif | upper) else 30 }}"
```

### Value with a fallback, on two lines

```yaml
value: >
  {% set r = states('sensor.garage_skoda_050722_actieradius') -%}
  [vast]ELROQ|{{ r | int if is_number(r) else '--' }} km
```

The dash in `-%}` prevents a space before `[vast]`; otherwise the prefix isn't recognised.

### News headline, wrapped on whole words

```yaml
value: >-
  {%- set e = state_attr('sensor.nos_algemeen', 'entries') or [] -%}
  {%- set t = (e[0].title if e else 'Geen nieuws') | trim -%}
  [vast]{{ (t | wordwrap(15, true, '\n')).split('\n')[:2] | join('|') }}
```

To show a headline only when it's new, see the NOS block in the example (with the helper
`input_text.ipixel_laatste_nos`).

### Rain radar: top half only

```yaml
- action: media_player.play_media
  target:
    entity_id: media_player.ipixel_wall_media
  data:
    media_content_id: camera.buienradar
    media_content_type: image/gif
    extra:
      crop: top              # or [0, 0, 1, 0.33] for exactly the 3-panel aspect ratio
      resize_mode: crop      # optional: fill the wall instead of black bars
  continue_on_error: true
- delay: "00:00:20"
```

### A different transition for one item

```yaml
data:
  media_content_id: clock
  media_content_type: image/gif
  extra:
    transition: drop
```

For text, change the selector right before the text step:

```yaml
- action: select.select_option
  target:
    entity_id: select.ipixel_wall_transition
  data:
    option: wipe
```

### Don't stream a GIF

```yaml
extra:
  stream: false
```

The GIF is then uploaded to the panels and they play it themselves. That's smoother, but the
panels may drift slightly out of step (see [How it works](how-it-works.md)).

## Test script

**[examples/gif_testen_script.yaml](../../examples/gif_testen_script.yaml)** is a script that
lets you pick a GIF in the media browser. It pauses the rotation, shows the GIF, reports how long
loading took and then resumes the rotation.
