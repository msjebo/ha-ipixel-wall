# Automatiseringen

[← Terug naar de README](../../README.nl.md) · **Nederlands** | [English](../en/automations.md)

## Complete rotatie ("attract mode")

In **[examples/attract_mode.yaml](../../examples/attract_mode.yaml)** staat een complete
automatisering die dagelijks van 08:00 tot 20:00 rouleert:

1. een willekeurige GIF uit een map (GIF's met `_STORY_` in de naam 60 seconden, de rest 30);
2. de klok;
3. het weerbericht;
4. de actieradius van de auto (tot 17:00);
5. een nieuwe NOS-kop (15 minuten lang);
6. op werkdagen een logo en een teamnaam;
7. de muziek die speelt, als de thuiswerk-speaker aan staat.

Plak hem via **Automatisering maken → ⋮ → Bewerken in YAML** en pas de entiteiten aan.

### Waarom deze opbouw

- **`mode: restart`**: de trigger van 20:00 breekt de lopende rotatie direct af.
- **Alles in één automatisering.** Laat **nooit meerdere automatiseringen tegelijk** naar de wall
  schrijven, en schrijf ook niet rechtstreeks naar de losse panelen via iPIXEL Color. Ze
  overschrijven elkaar dan, en panelen blijven leeg of lopen uit de pas.
- **`continue_on_error: true`**: een kapotte GIF of een onbereikbare camera stopt niet de hele
  rotatie.

## Bouwblokken

### GIF's automatisch uit een map

1. Maak een map, bijvoorbeeld `/media/pinball_dmd/rotatie`.
2. Geef Home Assistant toegang in `configuration.yaml`:
   ```yaml
   homeassistant:
     allowlist_external_dirs:
       - /media/pinball_dmd
   ```
3. Voeg de **Folder**-integratie toe met pad `/media/pinball_dmd/rotatie` en patroon `*.gif`.
   Je krijgt `sensor.rotatie` met het attribuut `file_list`.

Nieuwe GIF's in de map doen binnen ongeveer een minuut mee.

### Duur afhankelijk van de bestandsnaam

```yaml
- delay:
    seconds: "{{ 60 if '_STORY_' in (gif | upper) else 30 }}"
```

### Waarde met fallback, over twee regels

```yaml
value: >
  {% set r = states('sensor.garage_skoda_050722_actieradius') -%}
  [vast]ELROQ|{{ r | int if is_number(r) else '--' }} km
```

Het streepje in `-%}` voorkomt een spatie vóór `[vast]`; anders wordt het voorvoegsel niet
herkend.

### Nieuwskop, afgebroken op hele woorden

```yaml
value: >-
  {%- set e = state_attr('sensor.nos_algemeen', 'entries') or [] -%}
  {%- set t = (e[0].title if e else 'Geen nieuws') | trim -%}
  [vast]{{ (t | wordwrap(15, true, '\n')).split('\n')[:2] | join('|') }}
```

Wil je een kop alleen tonen als die nieuw is: zie het NOS-blok in het voorbeeld (met de helper
`input_text.ipixel_laatste_nos`).

### Buienradar: alleen de bovenste helft

```yaml
- action: media_player.play_media
  target:
    entity_id: media_player.ipixel_wall_media
  data:
    media_content_id: camera.buienradar
    media_content_type: image/gif
    extra:
      crop: top              # of [0, 0, 1, 0.33] voor precies de verhouding van 3 panelen
      resize_mode: crop      # optioneel: wall vullen in plaats van zwarte randen
  continue_on_error: true
- delay: "00:00:20"
```

### Andere overgang voor één onderdeel

```yaml
data:
  media_content_id: clock
  media_content_type: image/gif
  extra:
    transition: drop
```

Voor tekst zet je de keuzelijst vlak voor de tekststap om:

```yaml
- action: select.select_option
  target:
    entity_id: select.ipixel_wall_transition
  data:
    option: wipe
```

### Een GIF niet streamen

```yaml
extra:
  stream: false
```

Dan wordt de GIF naar de panelen geüpload en spelen ze hem zelf af. Dat is vloeiender, maar de
panelen kunnen iets uit de pas lopen (zie [Hoe het werkt](techniek.md)).

## Testscript

**[examples/gif_testen_script.yaml](../../examples/gif_testen_script.yaml)** is een script waarmee je in
de mediabrowser een GIF kiest. Het zet de rotatie even stil, toont de GIF, meldt hoe lang het
laden duurde en hervat daarna de rotatie.
