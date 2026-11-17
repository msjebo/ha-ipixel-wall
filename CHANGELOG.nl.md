# Wijzigingen

**Nederlands** | [English](CHANGELOG.md)

## 0.7.2 (2026-11-17)
- Accuteken `🔋` in het DMD-lettertype

## 0.7.1 (2026-11-13)
- Voorbereiding voor de standaardlijst van HACS: merkicoon, validatieworkflow (HACS + hassfest), `ipixel_color` als `after_dependencies`

## 0.7.0 (2026-11-13)
- Tv-weergave `camera.ipixel_wall_preview_tv` (16:9): klok bovenaan, de wall in het midden, weer eronder

## 0.6.3 (2026-11-13)
- Oplossing: een paneel kon zwart blijven na een overgang. Overgangen houden nu de minimale frametijd van de panelen aan en sturen het eindbeeld nog één keer

## 0.6.2 (2026-11-13)
- Bliksemteken `⚡` in het DMD-lettertype (bijvoorbeeld voor laden)

## 0.6.1 (2026-11-13)
- Documentatie in het Nederlands en Engels

## 0.6.0 (2026-11-13)
- Eerste versie in deze repository, met HACS-ondersteuning en documentatie
- Standaardovergang is nu `dissolve`

## 0.5.2
- Knop **Paneelgeheugen volledig wissen** (fabrieksreset van het paneelgeheugen)

## 0.5.1
- Knop **Opstartbeeld zwart maken**: wist de opgeslagen slots en zet een zwart opstartbeeld

## 0.5.0
- Overgangen: `wipe`, `slide`, `dissolve`, `drop`; keuzelijst en `extra.transition`
- De wall houdt bij wat er op elk paneel staat, zodat ongewijzigde panelen niet opnieuw worden verstuurd

## 0.4.3
- De voorbeeldcamera's volgen de werkelijke positie van de stream

## 0.4.2
- Voorbeeldcamera's voor 3 en 4 panelen, onafhankelijk van de instelling

## 0.4.1
- DMD-klok (`clock`, `clock:big`) met knipperende dubbele punt
- Betere letter V

## 0.4.0
- DMD-pixellettertype voor alle tekst; automatische grootte en `[fs=N]`, `[ttf]`
- Lichtkrant in DMD-stijl

## 0.3.x
- Ondersteuning voor 3 of 4 panelen, met een instellingenscherm om paneel 4 toe te voegen of weg te halen
- `[vast]`-tekst met een vaste lettergrootte, en twee regels met `|`
- Camera-entiteiten als bron, uitsnijden met `extra.crop`, `extra.resize_mode`
- Weerbericht met pixel-art iconen
- Voorbeeldcamera in het dashboard
- Streamen van GIF's voor synchrone weergave
- Gelijke framestructuur per paneel; het opnieuw coderen door pypixelcolor overgeslagen
- Synchroon eindigende uploads, opnieuw proberen en herstellen van de verbinding

## 0.2.0
- Experimentele eerste versie (3 panelen, 96x32)
