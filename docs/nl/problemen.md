# Problemen oplossen

[← Terug naar de README](../../README.nl.md) · **Nederlands** | [English](../en/troubleshooting.md)

| Symptoom | Oorzaak | Oplossing |
|---|---|---|
| **iPIXEL Wall** staat niet bij *Integratie toevoegen* | Integratie niet goed gekopieerd, of browsercache | Controleer of `custom_components/ipixel_wall/manifest.json` bestaat, herstart Home Assistant, Ctrl+F5 |
| De log meldt de integratie meerdere keren | Backupmappen in `custom_components` | Verplaats `ipixel_wall_backup*` naar buiten `custom_components` |
| *Instellen mislukt* | Een paneel is niet geladen in iPIXEL Color | Controleer de panelen in iPIXEL Color en herlaad daarna iPIXEL Wall |
| Panelen blijven soms leeg of tonen half geladen beelden | Meerdere automatiseringen schrijven tegelijk naar de wall of naar de losse panelen | Gebruik **één** automatisering voor de wall |
| Animaties lopen niet synchroon | Een GIF wordt niet gestreamd (`stream: false`) of `STREAM_GIFS = False` | Laat streamen aan |
| Animaties haperen of lopen trager | Bluetooth haalt het tempo niet (`te laat:` in de log) | Verhoog `STREAM_MIN_FRAME_MS` (bijv. naar 200 of 250) en gebruik minder kleuren en frames. Bluetooth-proxy's helpen alleen bij bereik: met 4 streamende panelen kan een ESP32-proxy steeds verbindingen verliezen, en de ingebouwde adapter is dan vaak stabieler |
| *GIF has N frames; maximum is …* | GIF te lang | Kort de GIF in of verhoog `MAX_GIF_FRAMES` |
| *weather.… not found* | Verkeerde entiteitsnaam | Zoek de naam op met `{{ states.weather \| map(attribute='entity_id') \| list }}` |
| `[vast]` wordt letterlijk getoond | Spatie of regeleinde vóór het voorvoegsel | Gebruik `-%}` in de template, of zet `[vast]` aan het begin van de waarde |
| Na het aanzetten verschijnen oude plaatjes | Opgeslagen slots op de panelen | Knop **Opstartbeeld zwart maken**, daarna eventueel **Paneelgeheugen volledig wissen** |
| *Bluetooth send failed for panel N* | Verbinding even weg | Gaat meestal vanzelf goed; bij herhaling: paneel herladen in iPIXEL Color of de stroom eraf halen |
| Casten naar de tv mislukt (*requires HTTPS*) | Home Assistant niet via https bereikbaar | Gebruik een dashboard-app op de tv (zie [Dashboard](dashboard.md)) |

## Handige commando's (Umbrel)

```bash
# Versie
grep '"version"' /home/umbrel/umbrel/app-data/home-assistant/data/custom_components/ipixel_wall/manifest.json

# Meldingen van de wall
sudo docker logs --since 10m home-assistant_server_1 2>&1 | grep -iA15 "ipixel_wall" | grep -v "has not been tested"

# Home Assistant herstarten
sudo docker restart home-assistant_server_1
```
