# Style Bible — *Universe*

> **Status:** v0.1 · **Stand:** 2026-06-06 · Teil von [Universe](./GAME_DESIGN_DOCUMENT.md)
> · Schwester-Dokument: [Asset-Spezifikation](./ASSETS.md)
>
> Das **verbindliche Design-Pattern** für ALLE visuellen Assets von *Universe*. Wer ein Asset
> erstellt (Artist, KI-Bildgenerator, Frontend-Entwickler), liest zuerst dieses Dokument.
> Ziel: Aus dem heterogenen Asset-Berg (Icons, Schiffe, Gebäude, Portraits, Hintergründe)
> wird **eine erkennbare, kohärente Marke**.

---

## 0. Designthese in einem Satz

> **„Kalter, präziser Militär-Sci-Fi mit einem warmen, menschlichen Kern."**

Die Welt ist tiefes Vakuum-Schwarzblau, technisch, funktional, lesbar — aber das USP von
*Universe* sind **Menschen** (Commander, Crew, Moral). Darum bekommt alles Lebendige
(Portraits, Funksprüche, Moral) einen **warmen Akzent** (Bernstein/Magenta), der sich
bewusst vom kühlen Cyan der Maschinen abhebt. Maschinen sind cyan und kalt; Menschen sind
warm. Dieser Kontrast trägt die Tagline *„Befehlige nicht nur Flotten — führe Menschen."*

---

## 1. Farbpalette (kanonisch, Hex)

Diese Hex-Codes sind die **Single Source of Truth** für Frontend-CSS-Variablen *und*
Asset-Produktion. Reihenfolge: Token-Name · Hex · Verwendung.

### 1.1 Hintergrund- & Flächentöne (kühl, dunkel)

| Token | Hex | Verwendung |
|-------|-----|------------|
| `--void` | `#05070F` | Tiefster Hintergrund (Weltraum, Vakuum), App-Body |
| `--bg-900` | `#080D1A` | Haupt-Canvas-Hintergrund |
| `--bg-800` | `#0B1424` | Panel-/Karten-Fläche (Standard-Container) |
| `--bg-700` | `#12203A` | Erhöhte Fläche (Hover, aktive Karte, Modal) |
| `--bg-600` | `#1B2E4D` | Eingabefelder, Slots, innere Flächen |
| `--grid` | `#1C3354` | Gitterlinien, Hintergrund-Raster, Trennlinien |
| `--stroke` | `#2A467A` | Standard-Rahmen/Border-Linie (1–2 px) |

### 1.2 Akzent — Maschinen / Technik (kalt, Cyan/Türkis-Familie)

| Token | Hex | Verwendung |
|-------|-----|------------|
| `--accent` | `#2BE0E6` | **Primär-Akzent.** Buttons, aktive Linien, Schiff-/Gebäude-Rim-Light, Fokus |
| `--accent-bright` | `#5FF6FB` | Highlights, Glow-Kern, Hover auf Akzent |
| `--accent-dim` | `#157E86` | Gedämpfter Akzent, inaktive Linien, Schatten von Cyan |
| `--accent-deep` | `#0A3B45` | Cyan-Fill mit niedriger Deckkraft, Glow-Halo-Basis |

### 1.3 Material — Metall / Hülle (neutral, lesbar)

| Token | Hex | Verwendung |
|-------|-----|------------|
| `--hull` | `#8DA2BF` | Schiffsrumpf, Gebäudewände, neutrale Metall-Mittel-Töne |
| `--hull-light` | `#C3D2E6` | Beleuchtete Metallkanten, Top-Light |
| `--hull-dark` | `#4A5B78` | Metall im Schatten, Panel-Linien |
| `--hull-shadow` | `#2C3850` | Tiefster Material-Schatten |

### 1.4 Mensch / Warm-Akzent & Status (warm — bewusster Kontrast zu Cyan)

| Token | Hex | Verwendung |
|-------|-----|------------|
| `--human` | `#FFB23F` | **Warm-Akzent** für Crew/Commander/Funksprüche, „lebendige" UI |
| `--magenta` | `#FF41F8` | **Warnung / Fraktions-Hot** (Angriff, dringende Forderung, Krise) |
| `--magenta-dim` | `#CC26D5` | Gedämpftes Magenta, Sekundär-Warnzustand |
| `--danger` | `#F0070C` | **Alarm / Permadeath / kritisch** (höchste Dringlichkeit, Angriffswarnung) |
| `--success` | `#36E07A` | Erfolg, fertige Queue, hohe Moral, positiver Delta |
| `--warning` | `#FFB23F` | Achtung (= `--human`), niedrige Moral, Energie-Defizit |
| `--info` | `#46D5FF` | Neutrale Info, Hinweise |

### 1.5 Ressourcen-Eigenfarben (fest, nie austauschen)

Jede Ressource hat eine **eindeutige** Farbe, die in Icon, Balken, Zahl, Tooltip identisch ist.

| Ressource | Token | Hex | Begründung |
|-----------|-------|-----|------------|
| **Metall** | `--res-metal` | `#B8C2CF` | gebürstetes Silber-Grau, Haupt-Baustoff |
| **Kristall** | `--res-crystal` | `#46D5FF` | leuchtendes Eis-Cyan-Blau, facettiert |
| **Deuterium** | `--res-deuterium` | `#57F2C4` | flüssiges Teal-Grün, „Treibstoff-Schimmer" |
| **Energie** | `--res-energy` | `#FFD23F` | elektrisches Bernstein-Gelb, Blitz |

### 1.6 Text

| Token | Hex | Verwendung |
|-------|-----|------------|
| `--text` | `#E6F2FF` | Primär-Text (fast-weiß, leicht kühl) |
| `--text-muted` | `#8DA2BF` | Sekundär-/Label-Text |
| `--text-faint` | `#5A6B86` | Deaktiviert, Platzhalter, Fußnoten |

### 1.7 Rang-Prestige-Rampe (Commander, Kadett → Legende)

Eine **Medaillen-Metall-Rampe**, damit Ränge auf einen Blick lesbar sind. Wird für
Portrait-Rahmen, Rang-Badges und Akzentlinien der Persona genutzt.

| Rang | Token | Hex | Look |
|------|-------|-----|------|
| **Kadett** | `--rank-cadet` | `#8DA2BF` | mattes Stahlgrau (grün/unfertig) |
| **Offizier** | `--rank-officer` | `#C98A3A` | Bronze |
| **Veteran** | `--rank-veteran` | `#C7D2DD` | poliertes Silber |
| **Elite** | `--rank-elite` | `#FFD23F` | Gold |
| **Legende** | `--rank-legend` | `#FF41F8` | prismatisches Magenta (einzigartig, „glüht") |

### 1.8 Moral-Bänder (4 Zustände, exakt an `balance.json` gekoppelt)

| Band | Bereich | Token | Hex |
|------|---------|-------|-----|
| **hoch** | 80–100 | `--morale-high` | `#36E07A` (grün) |
| **neutral** | 50–79 | `--morale-neutral` | `#2BE0E6` (cyan) |
| **niedrig** | 25–49 | `--morale-low` | `#FFB23F` (bernstein) |
| **kritisch** | 0–24 | `--morale-critical` | `#F0070C` (rot) |

---

## 2. Form- & Silhouetten-Sprache

### 2.1 Globale Form-Grammatik

- **Leitwinkel:** abgeschrägte Ecken bei **30°/60°** (kein reines 45°, kein Radius-Soft-UI).
  Panels und Badges nutzen *chamfered corners* (eine abgeschnittene Ecke oben-rechts oder
  unten-links) als Marken-Signatur.
- **Lesbare Silhouette zuerst.** Jedes Schiff/Gebäude/Icon muss als **reine schwarze
  Silhouette** auf 64 px noch eindeutig identifizierbar sein. Silhouette schlägt Detail.
- **Funktional, nicht verspielt.** Keine organischen Schnörkel, keine Fantasy-Ornamente.
  Alles wirkt konstruiert, genietet, militärisch-zweckmäßig.

### 2.2 Schiffe — kantig-funktional, Klasse an Silhouette erkennbar

- **Perspektive:** leichte **3/4-Top-Down-Ansicht** (ca. 25° von oben, Bug zeigt nach
  oben-rechts), identisch für ALLE Schiffe → Roster wirkt wie ein Set.
- **Silhouetten-Logik je Klasse:**
  - *Jäger* (leicht/schwer): klein, pfeilförmig, deltaflügelig, ein/zwei Triebwerke.
  - *Kreuzer/Schlachtkreuzer:* länglich, aggressive Vorwärts-Keil-Form.
  - *Schlachtschiff/Zerstörer:* massiv, breit, „Block"-artig, viele Geschütztürme.
  - *Transporter/Recycler:* bauchig, Container-/Greifarm-Module, wenig Bewaffnung.
  - *Sonde/Satellit:* winzig, asymmetrisch, Sensor-/Panel-Dominanz, kaum Rumpf.
  - *Todesstern:* Kugel mit Geschützgraben — bewusst ikonisch, riesiger Maßstab.
- **Größenverhältnis im Roster muss stimmen** (Sonde ≪ Jäger ≪ Kreuzer ≪ Schlachtschiff
  ≪ Todesstern). Im Asset-Sheet: konsistenter Maßstabs-Referenzrahmen.

### 2.3 Gebäude — isometrisch, einheitlicher Winkel

- **Perspektive:** **echte Isometrie, 2:1 (30°)**, Lichtquelle immer **oben-links**.
  Jedes Gebäude steht auf einem identischen sechseckigen/quadratischen Iso-Sockel mit
  Cyan-Kantenlicht → sie reihen sich im Bau-Screen sauber aneinander.
- **Material:** Industrie-Metall + dunkle Verkleidung + farbige Funktions-Akzente
  (Mine = Förder-Orange-Glühen, Solar = Cyan-Panele, Akademie = warmes Human-Licht).
- **Stufen-Lesbarkeit:** Höhere Stufen = mehr Module/Antennen/Glühen, gleiche Grundform.

### 2.4 Icons — Glyph-System

- **Resourcen/Status/Trait-Icons:** flacher, **line-+-solid-Hybrid** (2 px Linie, ein
  Solid-Fill-Akzent in Eigenfarbe). In Silhouette lesbar, auf 24 px noch klar.
- Einheitliches **optisches Gewicht** und identisches Padding (Glyph füllt ~70 % der Fläche).

---

## 3. Beleuchtung, Material, Rendering-Stil

| Aspekt | Regel |
|--------|-------|
| **Rendering-Stil** | **Semi-realistisch mit dezentem Cel-Anteil.** Klare Material-Trennung, weiche Verläufe, aber definierte Kanten. Nicht foto-real, nicht flat-vektor. „PBR-light." |
| **Hauptlicht** | Schiffe: oben-rechts. Gebäude: oben-links (Iso). Kühles Weiß (`#E6F2FF`). |
| **Rim-Light** | **Dezenter Neon-Cyan-Rim** (`--accent`) an einer Kante jedes 3D-Objekts — das verbindende Marken-Signal. Bei Crew/Portraits stattdessen **warmer Rim** (`--human`). |
| **Schatten** | Tief, kühl-blau (`--hull-shadow`), nie reines Schwarz. Weicher Kontaktschatten unter Iso-Gebäuden. |
| **Materialität** | Gebürstetes Metall, mattes Verbund-Panel, emittierende Glühlinien. Geringe Reflexion, kein Hochglanz/Chrom. |
| **Linienstärke** | Icon-Outlines 2 px @24–64 px. Objekt-Kanten in Renderings dunkel, kein durchgängiger Outline-Stroke (kein Comic-Outline). |
| **Detailgrad** | Mittel: genug Panel-Lines/Nieten für Glaubwürdigkeit, aber Silhouette + 3–4 Schlüssel-Formen dominieren. „Readable at 64 px." |
| **Glow/Emission** | Sparsam: Triebwerke, Energiekerne, aktive Status. Glow ist **Information**, kein Deko-Spam. |

---

## 4. Konsistenz-Regeln über Kategorien hinweg

1. **Eine Lichtlogik je Kategorie** (Schiffe top-right, Gebäude iso top-left) — innerhalb
   einer Kategorie NIE mischen.
2. **Cyan = Maschine, Warm = Mensch.** Diese semantische Farbtrennung gilt überall.
3. **Transparenter Hintergrund** für alle Objekt-Assets (Schiffe, Gebäude, Icons). Nur
   Hintergründe/Szenen sind vollflächig.
4. **Kein freier Text im Asset** (außer Logo/Wortmarke). Labels liefert die UI.
5. **Ressourcen-Eigenfarben sind sakrosankt** (§1.5) — eine Ressource hat überall dieselbe
   Farbe.
6. **Rang-Rampe konsequent** (§1.7) — ein Veteran ist überall silbern.
7. **Padding-Disziplin:** 8–12 % Sicherheitsrand in jedem quadratischen Asset, damit nichts
   am UI-Rand klebt.
8. **Vertical-Slice-Assets zuerst**, spätere Assets im selben Stil nachziehbar (Markierung
   in ASSETS.md).

---

## 5. Wiederverwendbarer Prompt-Baukasten (für KI-Bildgeneratoren)

Damit alle KI-generierten Assets zusammenpassen, wird **immer** das Master-Präfix + ein
Kategorie-Modul + das Master-Suffix kombiniert. Nur das mittlere `{{MOTIV}}` ändert sich.

### 5.1 Master-Präfix (immer voranstellen)

```
Game asset for "Universe", a dark sci-fi space-strategy MMO. Cohesive set style:
semi-realistic with a subtle cel-shaded edge, military-functional hard-surface design,
clean readable silhouette. Deep vacuum color world: near-black blue background tones,
cool cyan/teal neon rim-light (#2BE0E6), brushed-metal hulls (#8DA2BF). Restrained
emissive glow used only for thrusters/energy/active status. PBR-light materials,
crisp panel lines, no comic outline, no text, no watermark.
```

### 5.2 Kategorie-Module (eins einsetzen)

- **Schiff:** `Single spaceship, 3/4 top-down view (~25° from above, bow toward upper-right),
  {{MOTIV}}. Angular delta/wedge hull, cyan rim-light along one edge, glowing engines at rear.`
- **Gebäude:** `Single building in true 2:1 isometric view, light from upper-left, sitting on
  a neutral hex base with cyan edge-light, {{MOTIV}}. Industrial metal + dark cladding +
  function-colored accent lights.`
- **Ressourcen-/UI-Icon:** `Minimal flat-ish icon, line+solid hybrid, 2px stroke, single
  accent fill, centered glyph filling ~70% of frame, {{MOTIV}}.`
- **Commander-Portrait:** `Character bust portrait, head-and-shoulders, dramatic warm rim-light
  (#FFB23F) against a dark teal studio gradient, {{MOTIV}}. Believable human/sci-fi crew,
  uniform with rank insignia, confident sci-fi-military mood.`
- **Hintergrund/Szene:** `Wide atmospheric space scene, cinematic, deep blue-black, subtle
  starfield, volumetric cyan haze, {{MOTIV}}. No UI, no characters in foreground.`

### 5.3 Master-Suffix (immer anhängen)

```
Centered subject, generous safe-margin padding, transparent background (for objects/icons),
consistent scale within its set, high readability at small sizes, no text overlays.
Style-matched to the cohesive Universe asset library.
```

### 5.4 Beispiel (Leichter Jäger, vollständig zusammengesetzt)

> *[Master-Präfix]* `Single spaceship, 3/4 top-down view (~25° from above, bow toward
> upper-right), a small cheap mass-produced light fighter with a sharp delta wing, twin
> small thrusters, minimal armor. Angular wedge hull, cyan rim-light along one edge,
> glowing engines at rear.` *[Master-Suffix]*

---

## 6. Namens- & Ordnerkonvention

```
assets/
├── icons/
│   ├── resources/        metal.svg, crystal.svg, deuterium.svg, energy.svg
│   ├── traits/           aggressive.svg, cautious.svg, loyal.svg, ...
│   ├── missions/         attack.svg, transport.svg, espionage.svg, ...
│   ├── status/           badge_attack.svg, badge_queue_done.svg, ...
│   └── ui/               alert.svg, logo.svg, ...
├── buildings/            metal_mine.png, crystal_mine.png, ...        (PNG, transparent)
├── ships/                light_fighter.png, heavy_fighter.png, ...    (PNG, transparent)
├── defenses/             rocket_launcher.png, light_laser.png, ...    (PNG, transparent)
├── commanders/
│   ├── faces/            face_01.png ... face_NN.png                  (Basis-Layer)
│   ├── frames/           frame_cadet.png ... frame_legend.png         (Rang-Rahmen)
│   ├── markers/          marker_aggressive.png ...                    (Trait-Overlay)
│   └── spec/             spec_combat.png ...                          (Spezialisierungs-Badge)
├── backgrounds/          login.jpg, dashboard.jpg, planet_hot.png, ...
├── effects/              explosion.png/webp, engine_glow.png, transmission.webp
└── placeholders/         (siehe assets/placeholders/README.md — Stubs)
```

**Regeln:**
- **Dateiname = `balance.json`-Key**, exakt (snake_case): `light_fighter`, `command_academy`.
  So findet das Frontend Assets per Key ohne Mapping-Tabelle.
- Alles **klein, snake_case**, keine Leer-/Sonderzeichen.
- Varianten mit Suffix: `_lvl2`, `@2x`, `_hover`, `_disabled`.

---

## 7. Format- & Export-Settings

| Asset-Typ | Format | Maße | Hinweise |
|-----------|--------|------|----------|
| Ressourcen-/UI-/Trait-/Status-Icons | **SVG** (+ PNG-Fallback) | 64×64 (Artboard), skaliert 24–128 | Stroke nicht in Pfade umwandeln solange editierbar; PNG @1x/@2x |
| Schiffe | **PNG-32** transparent | **512×512** | Objekt ~80 % Fläche, Schatten optional separat |
| Gebäude | **PNG-32** transparent | **512×512** | Iso, gemeinsamer Sockel-Maßstab |
| Verteidigung | **PNG-32** transparent | 512×512 | wie Gebäude (planetar, fliegt nicht) |
| Commander-Portraits (final) | **PNG-32** | **1024×1024** | modular gerendert/komponiert (§ASSETS) |
| Commander-Thumbnail | PNG-32 | 256×256 | Roster-Liste |
| Logo/Wortmarke | **SVG** | vektoriell | + PNG 1024 breit |
| Hintergründe (Szene) | **JPG** (q≈85) oder WEBP | **1920×1080** | + 1080×1920 (mobil/portrait) |
| Planetentypen | **PNG-32** transparent | 512×512 | runde Planeten-Disc, freigestellt |
| Karten-Kacheln | PNG/SVG | 256×256 (tileable) | nahtlos kachelbar |
| Effekte | **WEBP/APNG** (Sprite) oder PNG-Sequenz | 256–512 | Sprite-Sheet bevorzugt |

**Export-Disziplin:**
- 32-bit PNG mit echtem Alpha (kein 1-bit, keine Halos). Trim auf Inhalts-Bounding-Box +
  definiertes Padding.
- sRGB-Farbprofil, eingebettet.
- SVG: `viewBox` gesetzt, keine externen Fonts/URLs, IDs eindeutig prefixed.
- Dateigröße-Budget: Icon < 10 KB, Schiff/Gebäude < 250 KB, Hintergrund < 500 KB.

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Farbpalette (kühl/warm + Ressourcen + Rang-Rampe +
  Moral-Bänder), Form-/Silhouetten-Sprache, Rendering-Stil, Konsistenzregeln,
  Prompt-Baukasten, Namens-/Ordner-/Export-Konventionen.
</content>
</invoke>
