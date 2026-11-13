# Installatie en updaten

[← Terug naar de README](../../README.nl.md) · **Nederlands** | [English](../en/installation.md)

## Voor je begint

1. Installeer **[iPIXEL Color](https://github.com/cagcoach/ha-ipixel-color)** en voeg elk paneel
   toe. Controleer dat je via die integratie op elk paneel tekst kunt tonen.
2. Noteer de **tekstentiteit** van elk paneel (bijvoorbeeld `text.led_ble_387bc42d_display`) en
   welk paneel links, in het midden en rechts hangt.

## Methode 1: HACS (alleen bij een publieke repository)

HACS kan **geen private GitHub-repositories** installeren. Is deze repository publiek:

1. **HACS → ⋮ → Aangepaste repositories**
2. URL: `https://github.com/msjebo/ha-ipixel-wall`, type **Integration**
3. Zoek **iPIXEL Wall**, kies **Downloaden** en herstart Home Assistant.

Updates verschijnen daarna vanzelf in HACS.

## Methode 2: handmatig (werkt altijd, ook bij een private repository)

Kopieer de map `custom_components/ipixel_wall` naar de map `custom_components` in je
Home Assistant-configuratie en herstart Home Assistant.

### Op Umbrel

Op Umbrel staat de configuratie van Home Assistant in
`/home/umbrel/umbrel/app-data/home-assistant/data/` (in de container is dat `/config`).

1. Download de repository als zip (**Code → Download ZIP**) en upload die met de
   bestandsbrowser van Umbrel naar je home-map.
2. Installeer of update met:

```bash
ZIP=/home/umbrel/umbrel/home/ha-ipixel-wall-main.zip      # pas de naam zo nodig aan
CC=/home/umbrel/umbrel/app-data/home-assistant/data/custom_components

rm -rf /tmp/ipw && python3 -m zipfile -e "$ZIP" /tmp/ipw
sudo rm -rf /home/umbrel/umbrel/home/ipixel_wall_backup_vorige
[ -d "$CC/ipixel_wall" ] && sudo mv "$CC/ipixel_wall" /home/umbrel/umbrel/home/ipixel_wall_backup_vorige
sudo cp -r /tmp/ipw/*/custom_components/ipixel_wall "$CC/"
sudo chown -R root:root "$CC/ipixel_wall"
grep '"version"' "$CC/ipixel_wall/manifest.json"
sudo docker restart home-assistant_server_1
```

> **Belangrijk:** zet backups **nooit** in `custom_components` zelf (bijvoorbeeld
> `ipixel_wall_backup`). Home Assistant ziet dan twee integraties met dezelfde naam en laadt
> mogelijk de verkeerde.

### Terugzetten

```bash
CC=/home/umbrel/umbrel/app-data/home-assistant/data/custom_components
sudo rm -r "$CC/ipixel_wall" && sudo mv /home/umbrel/umbrel/home/ipixel_wall_backup_vorige "$CC/ipixel_wall"
sudo docker restart home-assistant_server_1
```

## De wall instellen

**Instellingen → Apparaten & diensten → Integratie toevoegen → iPIXEL Wall**

| Veld | |
|---|---|
| Paneel 1 (links) | Tekstentiteit van het linkerpaneel |
| Paneel 2 | Middelste of tweede paneel |
| Paneel 3 | Derde paneel |
| Paneel 4 (rechts, optioneel) | Leeg laten voor een wall van 3 panelen |

### Later een 4e paneel toevoegen (of weghalen)

1. Voeg het paneel toe in **iPIXEL Color**.
2. **iPIXEL Wall → ⚙ Configureren** en vul **Paneel 4** in, of maak het veld leeg.
3. De wall herstart zichzelf als 128x32 (of 96x32). Entiteiten en automatiseringen blijven werken.

## Logniveau voor het oplossen van problemen

```yaml
action: logger.set_level
data:
  custom_components.ipixel_wall: info
```

Daarna:

```bash
sudo docker logs --since 10m home-assistant_server_1 2>&1 | grep -i ipixel_wall
```
