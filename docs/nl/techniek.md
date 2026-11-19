# Hoe het werkt

[← Terug naar de README](../../README.nl.md) · **Nederlands** | [English](../en/how-it-works.md)

## Opbouw

```
custom_components/ipixel_wall/
├── __init__.py        configuratie laden, panelen koppelen aan de API van iPIXEL Color
├── config_flow.py     instellen en wijzigen (3 of 4 panelen)
├── const.py           instellingen (zie hieronder)
├── manager.py         uploaden, streamen, overgangen, voorbeeld, opstartgeheugen
├── render.py          tekst, plaatjes, GIF's, klok en overgangen renderen en opknippen
├── dmd_font.py        DMD-pixellettertype
├── weather_render.py  weerweergave met pixel-art iconen
├── text.py / media_player.py / select.py / number.py / light.py / camera.py / button.py
└── translations/      Nederlands en Engels
```

De integratie gebruikt de bestaande verbindingen van **iPIXEL Color** en stuurt per paneel een
eigen 32x32-beeld.

## Het synchronisatieprobleem

Elk iPIXEL-paneel speelt een GIF af op zijn **eigen klok**, en Home Assistant heeft daar geen
invloed op. Als je drie stukken van een GIF uploadt, lopen de panelen daardoor uit de pas. Dat is
onderzocht en het volgende bleek:

| Poging | Resultaat |
|---|---|
| Uploads gelijk laten eindigen (laatste pakket tegelijk) | Beter, maar de panelen starten nog steeds verschoven |
| Elk paneel exact dezelfde framestructuur geven | Nodig, maar niet genoeg |
| Na de upload alle panelen uit en weer aan zetten | Aan-commando's komen binnen 250 ms aan, maar de panelen starten seconden uit elkaar |
| **Frames vanuit Home Assistant streamen** | **Altijd synchroon**: er is maar één klok |

Daarom worden GIF's standaard **gestreamd**. Home Assistant speelt de animatie af en stuurt elk
frame als PNG-tegel naar de panelen. Alleen panelen waarvan het beeld verandert, krijgen een
nieuw frame.

### Bluetooth-grenzen

- De ondergrens per frame is `STREAM_MIN_FRAME_MS = 150`, ongeveer 6 à 7 frames per seconde. Elk
  paneel bevestigt elk beeld voordat het het volgende krijgt, dus een frame dat langer duurt komt
  alleen later. Alleen panelen waarvan het beeld verandert krijgen een nieuw frame, dus rustige
  GIF's hebben minder tijd nodig dan drukke. Kortere frames
  worden samengevoegd, zodat snelle GIF's even lang duren maar minder frames hebben.
- Bij streamen wordt de normale `send_command` van iPIXEL Color overgeslagen. Die zet per pakket
  de notificaties uit en aan en wacht tot 2 seconden op een antwoord. In plaats daarvan wordt
  direct naar de schrijfkarakteristiek geschreven.
- Bij gewone uploads (tekst in scroll-modus, `stream: false`) gaan de pakketten om de beurt naar
  de panelen, zodat de laatste pakketten tegelijk aankomen.

### Opnieuw coderen door pypixelcolor

De bibliotheek `pypixelcolor` codeert elk beeld opnieuw, ook als het al 32x32 is. Daarbij worden
identieke frames samengevoegd, en een paneel met één frame laat het zelfs crashen. De integratie
vervangt `pypixelcolor.commands.send_image._resize_image` daarom bij het laden door een versie die
beelden van precies 32x32 ongewijzigd doorgeeft.

## Opslag op de panelen

| Slot | Inhoud |
|---|---|
| 0 | Wat de wall stuurt: alleen tonen, niet bewaren |
| 1 en hoger | Bewaarde beelden, bijvoorbeeld van de iPIXEL-app; die worden getoond na het aanzetten |

- **Opstartbeeld zwart maken** wist de slots 1-16 met `delete(n)` en zet een zwart beeld in slot 1.
- **Paneelgeheugen volledig wissen** gebruikt `clear()`. Dat wist alles, ook de instellingen van
  het paneel.

## Instellingen in `const.py`

| Constante | Standaard | |
|---|---|---|
| `MAX_GIF_FRAMES` | 2500 | Maximaal aantal frames per GIF |
| `MAX_MEDIA_BYTES` | 10 MB | Maximale bestandsgrootte |
| `STREAM_GIFS` | `True` | GIF's standaard streamen |
| `STREAM_MIN_FRAME_MS` | 150 | Minimale frameduur bij streamen; verhoog naar 200 of 250 als frames vaak te laat zijn (`te laat` in de log) |
| `STREAM_WRITE_MODE` | `chunked_noack` | Hoe frames worden verstuurd: `chunked_noack` (snelst), `chunked` (bevestiging per blokje van 244 bytes) of `single` (één lange schrijfactie) |
| `STREAM_ACK_TIMEOUT` | 1.0 | Max. aantal seconden wachten op de bevestiging van een paneel tijdens het streamen |
| `PANEL_START_OFFSETS_MS` | `(0, 0, 0, 0)` | Vertraging per paneel bij de resync na een gewone GIF-upload |

Na een wijziging moet je Home Assistant herstarten. Bij een update worden deze bestanden
overschreven.

## Log

Met het logniveau `info` (zie [Installatie](installatie.md)) zie je onder andere:

- `Synced upload: … packets per panel … failed: none`: een gewone upload;
- `Streaming start: N frames` en `Stream loop: N frames in X s (doel Y s), te laat: Z`: de stream.
  Ligt X ver boven Y, dan haalt Bluetooth het tempo niet;
- `Panel N: stored slots cleared, black boot screen saved`: het opstartbeeld is gezet.
