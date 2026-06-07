# Asset-Spezifikation — *Universe*

> **Status:** v0.2 · **Stand:** 2026-06-07 · Teil von [Universe](./GAME_DESIGN_DOCUMENT.md)
> · **Stilvorgabe:** [STYLE_BIBLE.md](./STYLE_BIBLE.md) (Palette, Form, Rendering, Prompt-Baukasten)
> · **Daten-Quelle:** [`shared/balance.json`](../shared/balance.json) (kanonische Keys)
>
> Vollständige, produktionsreife Liste **aller** visuellen Assets. Jeder Eintrag ist so
> spezifiziert, dass ein Artist **oder** ein KI-Bildgenerator ihn eindeutig umsetzen kann.
> Dateinamen = `balance.json`-Keys (snake_case) → das Frontend lädt Assets per Key ohne
> Mapping-Tabelle.

> ## ✅ Produktions-Status
> **Der komplette v0.1-Satz (§1–§8) ist PRODUZIERT** (2026-06-07): hochwertige PNGs für
> Ressourcen-Icons, 14 Gebäude, 14 Schiffe, 10 Verteidigungen, Commander (8 Faces + 5 Frames
> + 5 Spec-Badges + 8 Trait-Marker), 16 Hintergründe (inkl. Planeten/Login/Dashboard/System-View/
> Regionen/Nebel), 6 Effekte sowie Icon-Familien (Ressourcen/Traits/Missions/Status/Nav).
> Liegen unter `assets/` und sind ins Frontend (`frontend/src/assets/img/`) integriert.
> `assets/placeholders/` wurde entfernt.
> **UI-Primitives** (Buttons/Panels/Moral-Balken/Progress) bleiben bewusst **SVG** (skalierbar,
> themable); die sichtbaren Icon-Familien haben zusätzlich PNG-Versionen.
>
> **NEU/offen (v0.2):** das **Rollen-Kampf-System** (Doku [03b](./systems/03b-role-based-combat.md)/
> [03c](./systems/03c-role-roster-spec.md)) bringt neue Schiffe + Icons → **§11** (zu erstellen).

---

## Legende & Konventionen

- **VS** = Vertical Slice (jetzt nötig). **L** = Later (Post-Slice, gleicher Stil).
- **Pfad/ID** ist relativ zu `assets/`. Format/Maße siehe je Eintrag; Defaults in
  [STYLE_BIBLE §7](./STYLE_BIBLE.md#7-format--export-settings).
- Farb-Tokens (`--accent`, `--res-metal`, …) sind in der Style Bible §1 definiert.
- Alle Objekt-Assets: **transparenter Hintergrund**, zentriert, 8–12 % Sicherheitsrand.
- **Prio-Spalte:** P0 = blockt Vertical Slice · P1 = Slice-nice-to-have · P2 = später.

### Asset-Bilanz (Übersicht)

| Kategorie | Assets spezifiziert | Status |
|-----------|:---:|:---:|
| 1. Ressourcen-Icons | 4 | ✅ produziert |
| 2. Gebäude | 14 | ✅ produziert |
| 3. Schiffe | 14 | ✅ produziert |
| 4. Verteidigung | 10 | ✅ produziert |
| 5. Commander-Portraits (modular) | 27 Bausteine | ✅ produziert |
| 6. UI-Elemente | 38 | ✅ produziert (UI-Primitives SVG) |
| 7. Hintergründe/Atmosphäre | 16 | ✅ produziert |
| 8. Effekte | 6 | ✅ produziert |
| **11. Rollen-Kampf-Assets (v0.2)** | **~24 neu** | 🎨 **zu erstellen** |
| **Summe** | **~129 produziert + ~24 neu** | |

---

## 1. Ressourcen-Icons

**Verwendung:** Topbar-Ressourcenleiste (immer sichtbar), Kosten-Listen (Gebäude/Schiffe/
Forschung), Tooltips, Produktions-Übersicht, Handels-UI. Müssen bei **24 px** noch eindeutig
sein. Format: **SVG 64×64** (+ PNG @1x/@2x). Eigenfarben sind fix ([Style Bible §1.5]).

| ID / Datei | Prio | Motiv & Generierungs-Beschreibung |
|------------|:---:|-----------------------------------|
| `icons/resources/metal.svg` | P0 | Gestapelte/gebürstete **Metallbarren** (3 Barren, isometrisch leicht gekippt) in Silber-Grau `--res-metal`, kühles Top-Light, eine cyan Glanzkante. Schwere, solide Silhouette = „Haupt-Baustoff". |
| `icons/resources/crystal.svg` | P0 | **Facettierter Kristall-Cluster** (3–4 spitze Prismen) in leuchtendem Eis-Cyan-Blau `--res-crystal`, innerer Glow, harte Facetten-Highlights. Spitz, edel, „wertvoller als Metall". |
| `icons/resources/deuterium.svg` | P0 | **Tropfen/Fläschchen schwere Flüssigkeit** mit Schwapp-Welle, Teal-Grün `--res-deuterium`, sanfter Treibstoff-Schimmer, kleine Blasen. „Knappster Treibstoff". |
| `icons/resources/energy.svg` | P0 | **Blitz/Energie-Glyph** in einem Kreis oder Bilanz-Pfeil, elektrisches Bernstein-Gelb `--res-energy`, scharfe Strahlen-Spitzen. Signalisiert Bilanz (kein Vorrat) → optional kleiner ±-Hinweis-Slot. |

---

## 2. Gebäude

**Verwendung:** Bau-Screen (Kachel pro Gebäude + Stufen-Anzeige), Planeten-Übersicht,
Bau-Queue-Einträge. **Isometrisch 2:1**, Licht oben-links, gemeinsamer Sockel ([Style Bible
§2.3]). Format: **PNG-32 512×512** transparent. Alle Keys aus `balance.json` → jedes Gebäude
braucht ein Asset; **Naniten-Fabrik** ergänzt aus [Doku 01].

| ID / Datei | Prio | Funktions-Akzent | Generierungs-Beschreibung |
|------------|:---:|------------------|---------------------------|
| `buildings/metal_mine.png` | P0 | Orange-Glühen | Industrieller **Förderturm** über Schacht, Förderband, Erz-Halde. Dunkles Metall, glühend-orange Schmelz-/Förderlicht. Robust, niedrig. |
| `buildings/crystal_mine.png` | P0 | Cyan-Blau | Bohranlage mit freiliegenden **leuchtenden Kristall-Adern** (`--res-crystal`), gläserne Förderröhren, Schneid-Laser. |
| `buildings/deuterium_synth.png` | P0 | Teal-Grün | **Raffinerie-Tanks + Kühltürme**, Rohrleitungen, teal-grün leuchtende Flüssigkeitsfenster. Kondensat-Dampf. |
| `buildings/solar_plant.png` | P0 | Cyan-Panele | Sternförmig angeordnete **Solar-Panel-Flügel** um eine Verteiler-Nabe, cyan schimmernde Zellen. Flach, weit ausladend. |
| `buildings/fusion_reactor.png` | P1 | Heißes Cyan-Weiß | Kuppel mit **Tokamak-Reaktorring**, pulsierender Energiekern (heiß cyan-weiß), Kühlfinnen, Deuterium-Zuleitung. |
| `buildings/robot_factory.png` | P0 | Gelb-Warnstreifen | **Montagehalle** mit Roboterarmen/Kran, gelb-schwarze Warnstreifen am Tor, Funkenflug. Vermittelt „beschleunigt Bau". |
| `buildings/nanite_factory.png` | P2 (L) | Magenta-Schimmer | Hochtech-**Reinraum-Würfel**, fließende Nanit-Schimmer-Linien (`--magenta-dim`), schwebende Mikro-Drohnen. Endgame-Look. |
| `buildings/shipyard.png` | P0 | Cyan-Schweißlicht | Offenes **Trockendock-Gerüst** mit halbfertigem Schiffsrumpf, Schweißfunken (cyan), Kräne/Gantries. Hoch, gerüstartig. |
| `buildings/research_lab.png` | P0 | Cyan-Hologramm | **Laborkuppel** mit Hologramm-Projektor (rotierendes Tech-Hologramm cyan), Antennen, Datenpanels. |
| `buildings/metal_storage.png` | P0 | Silber | Großer **Silo/Bunker** mit Metallbarren-Stapel daneben, Füllstands-Streifen silbergrau. Schwere Lager-Silhouette. |
| `buildings/crystal_storage.png` | P0 | Cyan-Blau | Gläserne **Lager-Kuppel** mit gestapelten Kristallen, blau leuchtende Füllstands-Anzeige. |
| `buildings/deuterium_tank.png` | P0 | Teal-Grün | Zylindrischer **Drucktank** mit Manometer, teal-grünem Füllstandsfenster, Rohranschluss. |
| `buildings/command_academy.png` ⭐ | P0 | **Warm `--human`** | **USP.** Akademie-/Kaserne-Komplex mit beleuchteten Fenstern (warmes Licht = Menschen!), Fahnenmast/Wimpel, Trainingsplatz-Andeutung, Holo-Rang-Insignie über dem Eingang. Hebt sich durch **warmen** Ton von den kalt-cyanen Maschinen-Gebäuden ab. Sorgfältig. |
| `buildings/command_center.png` ⭐ | P1 | **Warm + Cyan** | **USP.** Imposante **Kommandobrücke/Bunker** mit großer Holo-Lagekarte (cyan) und warmen Innenlichtern, Satellitenschüsseln/Antennen, Rang-Banner. Vermittelt „Führungs-Reichweite/Span-of-Control". |

> **Stufen-Varianten (optional, L):** `_lvl2`/`_lvl3`-Overlays oder einfache zusätzliche
> Module/Antennen + stärkeres Glühen. Slice nutzt 1 Asset/Gebäude + UI-Stufenzahl.

---

## 3. Schiffe

**Verwendung:** Werft (Bau), Flotten-Screen, Missions-Dialog, Kampfbericht, Roster-Karten.
**3/4-Top-Down, Bug oben-rechts**, einheitlicher Maßstab ([Style Bible §2.2]). Format:
**PNG-32 512×512** transparent. VS-Schiffe stehen in `balance.json`; spätere aus [Doku 03 §4].

### 3.1 Vertical Slice (in `balance.json`)

| ID / Datei | Prio | Klasse/Rolle | Generierungs-Beschreibung |
|------------|:---:|--------------|---------------------------|
| `ships/light_fighter.png` | P0 | leichter Jäger, Kanonenfutter | Kleiner, **pfeil-/deltaförmiger** Einsitzer, dünne Panzerung, ein Heck-Triebwerk (cyan Glow), zwei Bug-Kanonen. Billig, agil, „Masse"-Look. Kleinste Kampf-Silhouette. |
| `ships/heavy_fighter.png` | P0 | schwerer Jäger | Gedrungener, breiterer Jäger, **doppelte Triebwerke**, sichtbar mehr Panzerplatten, schultermontierte Geschütze. Erkennbar „der größere Bruder" des leichten Jägers. |
| `ships/cruiser.png` | P0 | Kreuzer, Allrounder | Längliche, **aggressive Keil-Form**, drei Triebwerke, Geschütztürme an den Flanken, Brücke mittig. Mittlere Klasse, klar massiver als Jäger. |
| `ships/small_cargo.png` | P0 | kleiner Transporter | **Bauchiger Rumpf** mit gut sichtbaren **Container-/Frachtmodulen**, kleine Triebwerke, kaum Bewaffnung. Zivile, runde Silhouette (Kontrast zu Kampfschiffen). |
| `ships/spy_probe.png` | P0 | Spionagesonde | **Winzig**, asymmetrisch, dominiert von Sensor-Schüssel/Antennen-Array und einem Mini-Ionentriebwerk. Kaum Rumpf. Klar „kein Kampfschiff". |

### 3.2 Später (Doku 03, gleicher Stil)

| ID / Datei | Prio | Klasse/Rolle | Generierungs-Beschreibung |
|------------|:---:|--------------|---------------------------|
| `ships/large_cargo.png` | P2 (L) | großer Transporter | Wie `small_cargo`, aber **deutlich größer**, mehrere gestapelte Container-Reihen, schwerfällig. Reine Fracht-Silhouette. |
| `ships/colony_ship.png` | P2 (L) | Kolonieschiff | Massiges **Siedler-Schiff** mit gewölbten Habitat-Modulen, Landekapsel, „Arche"-Anmutung, wenig Waffen. |
| `ships/recycler.png` | P2 (L) | Recycler | Industrieschiff mit **Greifarmen/Trichter-Sammler** vorne, Lade-Bucht, Schürf-Look. Sammelt Trümmerfelder. |
| `ships/solar_satellite.png` | P2 (L) | Solarsatellit | **Kein Antrieb** — frei schwebendes Panel-Kreuz mit zentralem Energiekollektor (cyan), zerbrechlich. Klar verwundbar im Orbit. |
| `ships/battleship.png` | P2 (L) | Schlachtschiff | **Massives, breites** Rückgrat-Schiff, viele Geschütztürme, vier Triebwerke, schwere Panzerblöcke. „Block"-Silhouette. |
| `ships/battlecruiser.png` | P2 (L) | Schlachtkreuzer, Flotten-Jäger | Schlanker & aggressiver als Schlachtschiff, **vorgepfeilte** Keilform, Hyperraum-Antriebs-Glow, Laserbatterien. Schnell + schlagkräftig. |
| `ships/bomber.png` | P2 (L) | Bomber, Verteidigungsbrecher | Schwer, **buckliger Bombenschacht** unterm Rumpf, dicke Frontpanzerung, langsame Triebwerke. Plasma-Werfer-Look. |
| `ships/destroyer.png` | P2 (L) | Zerstörer, schwere Artillerie | Sehr groß, **dominante Hauptkanone(n)** entlang der Längsachse, schwerste Panzerung, wenige große Triebwerke. Bedrohlich. |
| `ships/deathstar.png` ⭐ | P2 (L) | Todesstern (Superschiff) | **Riesige Kugel** mit Geschützgraben/Äquator-Furche und einem markanten Fokus-Superlaser-Krater. Bewusst ikonisch, extremer Maßstab (im Sheet als „verschluckt den Rahmen"). Endgame, hart gegatet. |

> **Maßstabs-Sheet (P2):** `ships/_scale_reference.png` — alle Schiffe nebeneinander im
> korrekten Größenverhältnis (Sonde ≪ Jäger ≪ Kreuzer ≪ Schlachtschiff ≪ Todesstern).

---

## 4. Verteidigung

**Verwendung:** Werft-/Verteidigungs-Screen, Planeten-Verteidigungs-Übersicht, Kampfbericht.
**Planetar, fliegt nicht** → wie Gebäude **isometrisch**, aber als kompakte Geschütz-Plattform.
Format: **PNG-32 512×512** transparent. VS in `balance.json`; Rest aus [Doku 03 §5].

| ID / Datei | Prio | Rolle | Generierungs-Beschreibung |
|------------|:---:|-------|---------------------------|
| `defenses/rocket_launcher.png` | P0 | Kanonenfutter, Masse | Einfache **Raketenrampe** mit 2–3 Rohren auf Drehsockel, Munitionskasten. Billig, kantig, niedrig. |
| `defenses/light_laser.png` | P0 | Allround | Kompakter **Laser-Turm** mit einem Fokussier-Emitter (cyan Glow), Kühlrippen, Drehsockel. |
| `defenses/heavy_laser.png` | P2 (L) | stärkerer Allround | Größerer Doppel-Laser-Turm, mehr Panzerung, kräftigerer cyan Emitter. Klar „schwere Variante". |
| `defenses/gauss_cannon.png` | P2 (L) | hoher Einzelschaden | Langes **Railgun-/Gauß-Rohr** mit Spulen-Ringen, magnetisches Schimmern, schwerer Rückstoß-Sockel. |
| `defenses/ion_cannon.png` | P2 (L) | hoher Schild | Bauchiger **Ionen-Emitter** mit Schild-Generator-Kuppel, blaues Plasma-Aufladen, breite Basis. |
| `defenses/plasma_turret.png` | P2 (L) | stärkste Verteidigung | Massiver **Plasma-Werfer** mit glühend-violett/cyan geladenem Lauf, schwere Panzerung, bedrohlich groß. |
| `defenses/small_shield_dome.png` | P2 (L) | absorbiert, 1/Planet | Halbtransparente **Energiekuppel** über einer Generator-Basis, sanftes cyan Flimmern. |
| `defenses/large_shield_dome.png` | P2 (L) | absorbiert massiv, 1/Planet | Größere, hellere Schildkuppel, doppelter Generatorring, dichteres Energiegitter. |
| `defenses/anti_ballistic_missile.png` | P2 (L) | fängt Raketen ab | Vertikale **Abfangraketen-Silos** (Klappen offen), Radar-Antenne. Defensiv-Look. |
| `defenses/interplanetary_missile.png` | P2 (L) | zerstört feindl. Verteidigung | Großes **Offensiv-Raketensilo**, eine schwere Rakete sichtbar, Warnstreifen. |

---

## 5. ⭐ Commander-Portraits — modulares Persona-System

> **Das USP. Höchste Sorgfalt.** Ziel: Aus **wenigen Bausteinen** entstehen **hunderte
> distinkte, wiedererkennbare Personas**, deren **Rang sofort lesbar** ist (Kadett → Legende)
> und deren **Traits/Spezialisierung** als Marker erkennbar sind. Die Persona ist der
> emotionale Kern (GDD §6, [Doku 05]) und die Vorlage für die LLM-Funksprüche.

### 5.1 Komposition (4 Layer, vom Backend/Frontend zur Laufzeit gestapelt)

Ein Portrait = **Layer 0 Gesicht** + **Layer 1 Rang-Rahmen** + **Layer 2 Spezialisierungs-
Badge** + **Layer 3 Trait-Marker** (1–2). Alle Layer teilen Canvas, Licht (warmer Rim
`--human`, dunkler Teal-Gradient-Hintergrund) und Maße → sie passen pixelgenau aufeinander.

```
finales Portrait (1024×1024 PNG)
└── L3  Trait-Marker     commanders/markers/marker_<trait>.png      (Eck-Overlay, 1–2 Stück)
└── L2  Spec-Badge       commanders/spec/spec_<spec>.png            (Schulter/Kragen-Insignie)
└── L1  Rang-Rahmen      commanders/frames/frame_<rank>.png         (umlaufender Rahmen + Glow)
└── L0  Basis-Gesicht    commanders/faces/face_<NN>.png             (Bust, neutral beleuchtet)
```

Persona-Vielfalt = `Gesichter × Ränge × Spez × Trait-Kombis`. Schon **8 Gesichter ×
5 Ränge × 5 Spez × (8 über 1–2 Traits)** ⇒ **mehrere Tausend** sichtbar unterschiedliche
Personas aus **27 Bausteinen**.

### 5.2 Layer 0 — Basis-Gesichter (`commanders/faces/face_01..08.png`)

**Format:** PNG-32 1024×1024, Bust (Kopf + Schultern), transparenter/neutral-teal Hintergrund.
**Stil:** [Style Bible §5.2 „Commander-Portrait"] — believable Sci-Fi-Crew, warmer Rim-Light,
selbstbewusster militärischer Ausdruck, **neutrale Schulteruniform ohne Rang/Spez** (die
liefern L1/L2). 8 Archetypen für Diversität (Alter, Geschlecht, Herkunft, Cyber-Augmentierung):

| Datei | Prio | Archetyp (Beispiel) |
|-------|:---:|---------------------|
| `faces/face_01.png` | P0 | junge entschlossene Pilotin, kurzer Haarschnitt |
| `faces/face_02.png` | P0 | grauhaariger narbiger Veteran-Typ, kantiges Kinn |
| `faces/face_03.png` | P0 | Frau mittleren Alters, cybernetisches Auge, ruhig-streng |
| `faces/face_04.png` | P1 | jovialer kräftiger Logistik-Typ, Bart |
| `faces/face_05.png` | P1 | hagerer Spionage-Typ, Kapuze/Headset, verschmitzt |
| `faces/face_06.png` | P1 | junge nerdige Forscherin, Brille/Holo-Visor |
| `faces/face_07.png` | P2 | nicht-binär, geschäftstüchtiger Händler-Look, Schmuck |
| `faces/face_08.png` | P2 | schwer augmentierter Söldner, halbe Gesichtsplatte |

> Konsistenz: identischer Bildausschnitt, Blickrichtung leicht zur Kamera, gleiche
> Licht-/Hintergrund-Logik bei ALLEN Gesichtern (austauschbar unter denselben Frames).

### 5.3 Layer 1 — Rang-Rahmen (`commanders/frames/frame_<rank>.png`)

**Format:** PNG-32 1024×1024, umlaufender Rahmen + Rang-Insignie unten, Glow-Aura.
Verwendet die **Rang-Prestige-Rampe** ([Style Bible §1.7]). **Visuell auf einen Blick
unterscheidbar** — steigende Opulenz von Kadett zu Legende:

| Datei | Prio | Rang | Look (Metall + Insignie + Glow) |
|-------|:---:|------|--------------------------------|
| `frames/frame_cadet.png` | P0 | Kadett | **Mattgrauer**, dünner, schlichter Rahmen, ein einzelner kleiner Stern/Chevron, **kein** Glow. „grün/unfertig". |
| `frames/frame_officer.png` | P0 | Offizier | **Bronze**-Rahmen, zwei Chevrons, dezente Zier-Nieten, schwacher warmer Glow. |
| `frames/frame_veteran.png` | P0 | Veteran | **Silber**-Rahmen, drei Sterne, Lorbeer-Andeutung, sichtbarer kühl-silberner Glow. |
| `frames/frame_elite.png` | P1 | Elite | **Gold**-Rahmen, vierfach Insignie + Flügel/Lorbeer, kräftiger goldener Glow, kleine Edelstein-Akzente. |
| `frames/frame_legend.png` | P1 | Legende | **Prismatisch-magenta** (`--rank-legend`) glühender Zier-Rahmen, einzigartige Aura/Partikel, Kron-/Komet-Insignie. Klar „mythisch". |

### 5.4 Layer 2 — Spezialisierungs-Badge (`commanders/spec/spec_<spec>.png`)

**Format:** PNG-32 1024×1024 (transparent, Badge sitzt an Kragen/Schulter unten-links).
Kleines Branchen-Emblem, einfarbig + dünne Kontur, lesbar als Mini-Glyph. 5 Spezialisierungen
aus `balance.json`:

| Datei | Prio | Spez | Glyph |
|-------|:---:|------|-------|
| `spec/spec_combat.png` | P0 | Kampf | gekreuzte Schwerter/Geschütze + Zielkreis |
| `spec/spec_logistics.png` | P0 | Logistik | Zahnrad + Frachtcontainer/Pfeil |
| `spec/spec_spy.png` | P1 | Spionage | Auge in Dreieck / Sensor-Welle |
| `spec/spec_research.png` | P1 | Forschung | Atom/Kolben + Hologramm-Knoten |
| `spec/spec_trade.png` | P2 | Handel | Waage/Münze + Routen-Pfeil |

### 5.5 Layer 3 — Trait-Marker (`commanders/markers/marker_<trait>.png`)

**Format:** PNG-32 1024×1024 (transparent, kleines Eck-Overlay oben-rechts, max. 2 gestapelt).
**Identische Glyphen wie die UI-Trait-Icons** (§6) — hier als farbiger Persona-Marker mit
Glow. 8 Traits aus `balance.json`. Mapping & Glyph-Beschreibung siehe **§6.4 Trait-Icons**
(nicht doppelt aufgeführt). VS: aggressive, cautious, loyal, ambitious (P0/P1), Rest P2.

### 5.6 Abgeleitet: Thumbnail & Memorial

| Datei | Prio | Verwendung |
|-------|:---:|------------|
| `commanders/thumb_template.png` | P1 | 256×256 Roster-Listen-Thumbnail (komponiertes Portrait, beschnitten auf Kopf). |
| `commanders/memorial_overlay.png` | P2 | Trauer-Overlay (entsättigt + erloschenes Glow + Kerzen-/Stern-Symbol) für **Permadeath-Memorial** ([Doku 11 §3], würdevolle Inszenierung). |
| `commanders/silhouette_unknown.png` | P1 | Anonyme **gefangene/abgeworbene** Commander vor Enthüllung (dunkle Silhouette + „?"). |

---

## 6. UI-Elemente

**Verwendung:** Querschnitt durch alle Screens ([Doku 11 §2]). Wo nicht anders genannt:
**SVG**, an Frontend-CSS-Variablen ([Style Bible §1]) gebunden, in Themes umfärbbar.

### 6.1 Marke

| ID / Datei | Prio | Beschreibung |
|------------|:---:|--------------|
| `icons/ui/logo.svg` | P0 | **Wortmarke „UNIVERSE"** — kantige, technische Versal-Schrift mit 30°-Chamfer am „U", ein Orbit-Ring/Planet als Punkt über dem „I" oder durch das „O/V". Cyan-Akzent auf hellem Versal, optional warmer Funken-Punkt (Mensch-im-Kosmos). Vektoriell, + PNG 1024 breit. |
| `icons/ui/logo_mark.svg` | P0 | **Bildmarke allein** (App-Icon/Favicon): stilisierter Orbit-Ring um einen Kern, cyan, in chamfered Square. 512×512 + Favicon-Größen. |
| `icons/ui/wordmark_mono.svg` | P1 | Einfarbige Wortmarke (hell/dunkel) für Wasserzeichen/Footer. |

### 6.2 Buttons (Zustände)

**Verwendung:** alle Aktionen. **9-Slice-fähige SVG/PNG** + CSS, NICHT als feste Bitmaps
(skalierbar). Chamfered-Corner-Signatur ([Style Bible §2.1]). Je Variante 4 Zustände:
`default / hover / active / disabled`.

| ID / Datei | Prio | Beschreibung |
|------------|:---:|--------------|
| `icons/ui/btn_primary.svg` | P0 | Primär: cyan `--accent` Fill/Glow, dunkler Text, abgeschnittene Ecke oben-rechts, dünne hellere Innenlinie. |
| `icons/ui/btn_secondary.svg` | P0 | Sekundär: transparenter Fill, cyan Kontur, cyan Text („ghost/outline"). |
| `icons/ui/btn_danger.svg` | P1 | Gefahr (Abriss, Flotte-vernichten): `--danger`/`--magenta` Kontur+Glow. |
| `icons/ui/btn_disabled.svg` | P1 | Deaktiviert: `--bg-700` Fill, `--text-faint`, kein Glow. |

### 6.3 Panels, Rahmen & Container

| ID / Datei | Prio | Beschreibung |
|------------|:---:|--------------|
| `icons/ui/panel_frame.svg` | P0 | **9-Slice Panel-Rahmen:** dunkle `--bg-800`-Fläche, 1–2 px `--stroke`-Kante, eine chamfered Ecke + kurzer cyan Akzent-„Tab" oben-links. Standard-Container überall. |
| `icons/ui/panel_header.svg` | P1 | Sektions-Kopfleiste mit cyan Unterstrich + chamfer, für Screen-Titel. |
| `icons/ui/card_slot.svg` | P1 | Leerer **Slot/Karte** (Schiffsbau, Commander-Roster, Queue) — gestricheltes cyan-dimmes Inneres. |
| `icons/ui/tooltip_box.svg` | P1 | Tooltip-Container (kleiner Pfeil-Zipfel), dunkel + cyan Kante. Für transparente Formel-Tooltips ([Doku 11 §8]). |
| `icons/ui/divider.svg` | P2 | Zierde-Trennlinie (cyan, mit Mittel-Raute). |
| `icons/ui/progress_bar.svg` | P0 | Generische **Fortschrittsleiste** (Bau-/Forschungs-/Bauzeit-Queue): dunkle Spur + cyan Fill + animierbarer Glanz. |

### 6.4 Trait-Icons (`icons/traits/<trait>.svg`)

**Verwendung:** Commander-Roster, Tooltips, **und** als Persona-Marker-Glyph (§5.5).
SVG 64×64, line+solid, je Trait eine merkbare Glyphe. 8 Traits aus `balance.json`.
Negative Traits ([Doku 05] — Traits haben Vor- *und* Nachteile) bekommen einen dezenten
warmen/roten Unterton, positive einen cyan/grünen.

| ID / Datei | Prio | Trait | Glyph & Ton |
|------------|:---:|-------|-------------|
| `icons/traits/aggressive.svg` | P0 | aggressiv | nach vorn stoßende Pfeilspitze / geballte Faust, `--magenta`-Unterton |
| `icons/traits/cautious.svg` | P0 | vorsichtig | Schild mit Rückzugs-Pfeil, `--info` |
| `icons/traits/loyal.svg` | P0 | loyal | verschränkte Hände / Wappen-Herz, `--success` |
| `icons/traits/ambitious.svg` | P1 | ehrgeizig | aufsteigender Stern/Treppe, `--res-energy` |
| `icons/traits/greedy.svg` | P1 | gierig | Münzstapel/greifende Hand, `--res-energy`/warm |
| `icons/traits/honorable.svg` | P2 | ehrenhaft | Lorbeer/Medaille, `--rank-veteran` |
| `icons/traits/charismatic.svg` | P2 | charismatisch | Sprech-/Strahlen-Symbol, `--human` |
| `icons/traits/hot_tempered.svg` | P2 | jähzornig | Flamme/Blitz, `--danger` (instabil) |

### 6.5 Missions-Icons (`icons/missions/<type>.svg`)

**Verwendung:** Flotten-Screen, Missions-Dialog, laufende Bewegungen ([Doku 11 §2, Doku 07]).
SVG 64×64.

| ID / Datei | Prio | Mission | Glyph |
|------------|:---:|---------|-------|
| `icons/missions/attack.svg` | P0 | Angriff | gekreuzte Schwerter / Zielfadenkreuz `--magenta` |
| `icons/missions/transport.svg` | P0 | Transport | Frachtkiste + Pfeil `--res-metal` |
| `icons/missions/deploy.svg` | P1 | Stationieren | Anker/Parkplatz-Pfeil `--info` |
| `icons/missions/espionage.svg` | P0 | Spionage | Auge/Sensor-Welle `--info` |
| `icons/missions/colonize.svg` | P1 | Kolonisieren | Planet + Flagge `--success` |
| `icons/missions/recycle.svg` | P2 | Recyceln | Greifarm + Trümmer `--res-crystal` |
| `icons/missions/expedition.svg` | P2 | Expedition | Kompass/„16"-Deep-Space-Pfeil `--human` |
| `icons/missions/return.svg` | P1 | Rückkehr/Rückruf | U-Turn-Pfeil `--accent` |

### 6.6 Status-Badges & Benachrichtigungen (`icons/status/<name>.svg`)

| ID / Datei | Prio | Verwendung |
|------------|:---:|------------|
| `icons/ui/alert.svg` ⚠ | **P0** | **Angriffswarnung** — die wichtigste Benachrichtigung ([Doku 11 §6]). Dreieck mit Ausrufezeichen, `--danger` rot, kräftiges Glow, für animiertes Pulsieren ausgelegt. Auch als Push-/Tab-Icon. |
| `icons/status/badge_attack.svg` | P0 | eingehende feindliche Flotte (Marker auf Karte/Topbar), `--danger`. |
| `icons/status/badge_build_done.svg` | P0 | Bau fertig, `--success` Häkchen. |
| `icons/status/badge_research_done.svg` | P1 | Forschung fertig, cyan Atom-Häkchen. |
| `icons/status/badge_fleet_return.svg` | P1 | Flotte zurück, `--accent` U-Turn. |
| `icons/status/badge_transmission.svg` ⭐ | **P0** | **Eingehende Transmission/Funkspruch** ([Doku 11 §3]) — Funkwellen-Glyph, warm `--human`, „lebendig". USP-relevant. |
| `icons/status/badge_demand.svg` ⭐ | P1 | **Commander-Forderung/Krise** (Meuterei-Risiko) — Sprechblase mit „!", warm→rot je Dringlichkeit. |
| `icons/status/badge_promotion.svg` | P2 | Beförderung verfügbar, Rang-Aufstiegs-Pfeil + Stern. |
| `icons/status/badge_energy_low.svg` | P1 | Energie-Defizit (drosselt Produktion), `--warning` Blitz-durchgestrichen. |
| `icons/status/badge_newbie.svg` | P2 | Neulingsschutz aktiv, Schild `--info`. |
| `icons/status/badge_vacation.svg` | P2 | Urlaubsmodus, Pause-/Palmen-Symbol. |

### 6.7 Moral-Balken (4 Bänder-Zustände) ⭐

**Verwendung:** Commander-Roster & -Detail — das **emotionale Kern-UI** ([Doku 05 §4]).
Horizontaler segmentierter Balken (0–100), Füllfarbe = aktuelles Band. **Exakt** an
`balance.json → commander.morale.bands` gekoppelt. SVG 256×32 (skalierbar), je Zustand 1 Asset
(oder ein parametrisierter Balken, der die Token-Farbe wechselt):

| ID / Datei | Prio | Band (Bereich) | Farbe & Look |
|------------|:---:|----------------|--------------|
| `icons/ui/morale_high.svg` | P0 | hoch (80–100) | `--morale-high` grün, voller Fill, ruhiges Glow, „↑"-Indikator |
| `icons/ui/morale_neutral.svg` | P0 | neutral (50–79) | `--morale-neutral` cyan, ¾-Fill, stabil |
| `icons/ui/morale_low.svg` | P0 | niedrig (25–49) | `--morale-low` bernstein, ½-Fill, dezentes Warnflackern |
| `icons/ui/morale_critical.svg` | P0 | kritisch (0–24) | `--morale-critical` rot, niedriger Fill, pulsierendes Alarm-Glow (Meuterei-Risiko) |

### 6.8 Sonstige UI-Glyphen (Navigation/QoL)

| ID / Datei | Prio | Verwendung |
|------------|:---:|------------|
| `icons/ui/nav_dashboard.svg` … | P1 | Navigations-Icon-Set je Screen (Dashboard, Gebäude, Forschung, Werft, Flotte, Karte, **Kommandozentrale**, Postfach, Allianz, Markt, Rangliste, Simulator) — 12 Glyphen, einheitlicher Stil. |
| `icons/ui/spinner.svg` | P1 | Lade-/Berechnungs-Spinner (cyan Orbit-Ring). |
| `icons/ui/coord_pin.svg` | P2 | [G:S:P]-Koordinaten-Marker für die Karte. |

> Nav-Icon-Set zählt als **12** Glyphen in der Bilanz, hier gebündelt gelistet.

---

## 7. Hintergründe & Atmosphäre

**Verwendung:** Login, Dashboard, Karten, Kampf-/Planeten-Kontexte. Vollflächig (kein Alpha,
außer Planeten-Discs). Stil [Style Bible §5.2 „Hintergrund/Szene"]. Maße [Style Bible §7].

| ID / Datei | Prio | Verwendung | Generierungs-Beschreibung |
|------------|:---:|------------|---------------------------|
| `backgrounds/login.jpg` | P0 | Login/Start-Screen | Cinematic Weltraum-Vista: ein Heimatplanet unten, vorbeiziehende Flotte als Silhouette, ferne Galaxie + cyan Nebel, viel ruhiger Raum für Login-Form. Setzt Ton + Tagline. 1920×1080 + 1080×1920. |
| `backgrounds/dashboard.jpg` | P0 | Dashboard/App-Hintergrund | **Dezenter**, dunkler Sternenfeld-Hintergrund mit leichtem cyan Nebel-Verlauf, sehr kontrastarm (UI liegt darüber, darf nicht ablenken). 1920×1080. |
| `backgrounds/starfield_tile.png` | P0 | nahtloses Sternenfeld | Kachelbares (256×256) Stern-Rauschen für Karte/Parallax. |
| `backgrounds/planet_normal.png` | P0 | Planetentyp normal | Freigestellte runde **Planeten-Disc**, gemäßigte blau-grün-braune Oberfläche, leichte Atmosphäre, Terminator-Schatten. 512×512. ([Doku 06 §3]) |
| `backgrounds/planet_hot.png` | P0 | Planetentyp heiß | Glühend rot-orange Lava-/Wüstenwelt, dünne Atmosphäre (→ weniger Deuterium, mehr Sat-Energie). 512×512. |
| `backgrounds/planet_cold.png` | P0 | Planetentyp kalt | Eis-/Gas-Welt in Blau-Weiß, dichte kalte Atmosphäre (→ mehr Deuterium). 512×512. |
| `backgrounds/planet_homeworld.png` | P1 | Heimatplanet | Einladende blau-grüne „Erde-artige" Welt mit sichtbaren Lichtern (Besiedlung), Mond optional. 512×512. |
| `backgrounds/moon.png` | P2 (L) | Mond ⭐ | Grauer kraterübersäter Mond, klein, neben Planet platzierbar (Phalanx/Sprungtor, [Doku 06 §4]). 256×256. |
| `backgrounds/galaxy_tile.png` | P1 | Galaxie-Kartenansicht | Kachel der Galaxie-Karte: Hintergrund-Gitter `--grid`, Sternen-/System-Punkte, Spiralarm-Nebel. 256×256 tileable. |
| `backgrounds/system_view.png` | P1 | Sonnensystem-Ansicht | Zentralstern + konzentrische Orbit-Ringe (1–15 Positionen), als Layout-Hintergrund für die System-UI. 1920×1080. |
| `backgrounds/region_core.png` | P2 | Frontier-Ringe ⭐ | Stilisierter Karten-Hintergrund **Kern** (dicht, rot-warm, „umkämpft"). ([Doku 06 §6]) |
| `backgrounds/region_mid.png` | P2 | Ring Mitte | gemischt, neutral-cyan. |
| `backgrounds/region_frontier.png` | P2 | Ring Frontier | dünn besiedelt, kühl, „neu/geschützt" (Spieler-Spawn). |
| `backgrounds/debris_field.png` | P1 | Trümmerfeld | Schwebende Metall-/Kristall-Wrackteile in lockerer Wolke (Recycler-Ziel, Mond-Quelle). Freigestellt/halbtransparent, 512×512. ([Doku 03 §3]) |
| `backgrounds/nebula.png` | P1 | Nebel-Ambiente | Großer cyan-magenta Gasnebel als Karten-/Szenen-Akzent. 1920×1080 oder Kachel. |
| `backgrounds/deep_space.png` | P2 | Expeditions-/Deep-Space-Ziel | Leerer, etwas unheimlicher tiefer Raum mit fernen Anomalie-Lichtern ([Doku 06 §8]). 1920×1080. |

---

## 8. Effekte (optional / später)

**Verwendung:** Kampfberichte/-Simulator, Schiff-Renderings, Funkspruch-Inszenierung.
Sprite-Sheets oder WEBP/APNG ([Style Bible §7]). Alle **P2**, außer ggf. simple Statik für VS.

| ID / Datei | Prio | Beschreibung |
|------------|:---:|--------------|
| `effects/explosion.webp` | P2 | Kampf-**Explosion** (Sprite-Sequenz): cyan-weißer Blitz → oranger Feuerball → Trümmer/Rauch. Für Schiff-Zerstörung im Bericht (Hülle < 30 %). |
| `effects/engine_glow.png` | P1 | **Triebwerks-Glow** (additives Sprite, cyan), unter Schiff-Renderings legbar; Slice kann statische Variante nutzen. |
| `effects/shield_hit.webp` | P2 | **Schild-Treffer**: hexagonales Energie-Aufflackern (Schild-Abprall-Visual, [Doku 04]). |
| `effects/transmission.webp` ⭐ | P2 | **Funkspruch-Transmission-Animation** ([Doku 11 §3]): einlaufende Scanlines/Funkwellen + warmer Glitch um das Commander-Thumbnail — inszeniert „eingehende Transmission". USP-Atmosphäre. |
| `effects/warp_in.webp` | P2 | Flotten-Ankunft/Sprungtor-Effekt (cyan Lichtriss). |
| `effects/scan_sweep.png` | P2 | Sensor-/Phalanx-Scan-Welle (Mond-Phalanx, Spionage). |

---

## 9. Asset → System-Mapping (Vollständigkeitsprüfung gegen `balance.json`)

Damit nichts fehlt: jeder spielmechanische Key hat ein Asset.

- **Ressourcen** (`base_income`/Kosten-Keys): metal, crystal, deuterium, **energie** (Bilanz) → §1 ✅ (4/4)
- **buildings** (13 Keys) + nanite_factory (Doku 01) → §2 ✅ (14/14)
- **ships** (5 Keys) + 9 spätere (Doku 03) → §3 ✅ (14)
- **defenses** (2 Keys) + 8 spätere (Doku 03) → §4 ✅ (10)
- **commander.ranks** (5) → §5.3 Rahmen ✅; **specializations** (5) → §5.4 ✅;
  **personality_traits** (8) → §5.5/§6.4 ✅; **morale.bands** (4) → §6.7 ✅
- **research.techs** (11 Keys): nutzen **keine eigenen Vollbild-Assets** im Slice — werden
  über das **Trait-/Glyph-System** + generische `research_lab`-Holo-Icons im Techbaum
  dargestellt. *(Optional P2: 11 kleine Tech-Glyphen — als Folge-Backlog vermerkt, nicht in
  der Kern-Bilanz.)*

> **Offen/Backlog (P2):** Tech-Baum-Glyphen (11), Allianz-Embleme/Wappen-Baukasten,
> NPC-Imperien-Fraktions-Icons ([Doku 08]), Markt-/Handels-Icons, Achievement-/Saison-Badges.

---

## 11. Rollen-Kampf-Assets (v0.2 — NEU, zu erstellen 🎨)

**Quelle:** [Doku 03b Rollen-Kampf](./systems/03b-role-based-combat.md) + [03c Roster-Spec](./systems/03c-role-roster-spec.md).
Das rollenbasierte Kampfsystem (Subsysteme Schild/Antrieb/Hülle, Schadenstypen, Piraterie/Eskorte,
4 Doktrinen) bringt **neue Schiffsrollen** ohne Art sowie Waffen-/Status-Icons + Effekte.
Die **14 bestehenden Schiffe** (§3) decken ihre Rollen weiter ab — **keine** neue Art nötig.

### 11.1 Neue Schiffe (Stil = §3, 3/4-Top-Down, einheitlicher Maßstab, PNG-32 512×512 transparent)

| ID / Datei | Rolle | Doktrin | Generierungs-Beschreibung |
|------------|-------|:---:|---------------------------|
| `ships/carrier.png` | Träger | MIL | Breiter Rumpf mit **offenem Hangar-Deck** + Drohnen-Buchten, mehrere Startkatapulte, wuchtig. „Mutterschiff". |
| `ships/interdictor.png` | Interdiktor/Fangschiff | PIR | Gedrungen, dominiert von großen **Feld-Generator-Ringen/Antennen-Gittern** (Fang-Feld), pulsierendes Energie-Schimmern. |
| `ships/ewar_frigate.png` | EWAR-Fregatte | PIR | Schlank, markante **Ionen-/EMP-Emitter** + blaue Energie-Coils statt klassischer Kanonen. „Entwaffner". |
| `ships/boarder.png` | Enterschiff | PIR | Gepanzerter Bug mit **Enter-/Greifklauen** + Andock-Tunnel, robust, aggressiv. |
| `ships/stealth_corvette.png` | Tarnkappen-Korvette | PIR | Kantig-facettierte, **dunkle** Silhouette, kaum Glow (Stealth), schnelle Linien. |
| `ships/escort_frigate.png` | Eskort-Fregatte (Punktverteidigung) | UNI | Kompakt-defensiv, viele kleine **Punktverteidigungs-Türme/Flak**, Schutz-Optik. |
| `ships/shield_tender.png` | Schild-Tender | UNI | Zentraler **Schild-Projektor-Dom**, Support-Anmutung, kaum Waffen, sanftes cyan Schild-Glühen. |
| `ships/interceptor.png` | Abfangjäger | UNI | Extrem **schlanke** Speed-Silhouette, große Triebwerke, minimal Panzerung. |
| `ships/miner.png` | Bergbauschiff | HAN | Industriell mit **Bohr-/Sammelarmen** + Erz-Buchten, schwerfällig. |
| `ships/deep_scout.png` | Tief-Aufklärer | PIO | Leicht & schnell, große **Sensor-Schüssel/Antennen-Cluster**. |
| `ships/expedition_ship.png` | Expeditions-Schiff | PIO | Robust, **Langstrecken-Tanks** + Bergungs-Optik, „Forschungs-Kutter". |
| `ships/drone.png` *(opt.)* | Träger-Drohne | MIL | Kleine, gesichtslose **Jäger-Drohne** (für die Träger-Mechanik), wiederholbar im Schwarm. |

### 11.2 Waffen-/Schadenstyp-Icons (SVG 64×64, für Ladungs-/Tooltip-UI)

| ID / Datei | Schadenstyp | Glyph |
|------------|-------------|-------|
| `icons/weapons/weapon_energy.svg` | Energie (anti-Schild) | gebündelter **Laserstrahl** / Fokus-Emitter, cyan |
| `icons/weapons/weapon_kinetic.svg` | Kinetik (anti-Hülle) | **Projektil/Geschoss** mit Aufprall-Splittern, silber |
| `icons/weapons/weapon_ion.svg` | Ionen/EMP (Schild+Antrieb) | **EMP-Welle/Blitzkringel**, elektrisch blau-violett |
| `icons/weapons/weapon_missile.svg` | Rakete (anti-Hülle, abfangbar) | **Rakete** mit Abgasfahne, warm/orange |

### 11.3 Status-Icons (SVG 64×64, Kampf-/Flotten-Zustände)

| ID / Datei | Zustand | Glyph |
|------------|---------|-------|
| `icons/status/status_shield_down.svg` | Schild zusammengebrochen | zerbrochenes Schild-Hex, ausgegraut |
| `icons/status/status_drive_damaged.svg` | Antrieb beschädigt (Stufen) | Triebwerk mit Warn-/Riss-Symbol |
| `icons/status/status_stranded.svg` | **gestrandet** (enterbar) | Schiff mit Ketten-/Anker-Symbol, rot |
| `icons/status/status_interdiction.svg` | Fang-Feld aktiv | konzentrische Feld-Ringe, magenta |
| `icons/status/status_boarding.svg` | Entervorgang | Greifklaue + Schiff, „Kaperung" |

### 11.4 Effekte (ergänzend zu §8; WEBP/APNG oder Sprite)

| ID / Datei | Beschreibung |
|------------|--------------|
| `effects/ion_emp.webp` | **Ionen/EMP-Treffer**: elektrische Entladung übers Ziel, Schild-Flimmer + Antriebs-Funken. |
| `effects/boarding.webp` | **Kaper-Effekt**: Andock-Tunnel/Enter-Kapsel + Übernahme-Glow am Ziel. |
| `effects/warp_disrupt.webp` | **Warp-Disruptor** (Interdiktor): kollabierender Sprung-Riss, Flucht verhindert. |

> **Doktrin-Hinweis:** Doktrinen (Kriegsherr/Händler/Freibeuter/Pionier) brauchen optional je ein
> kleines **Doktrin-Emblem** (`icons/doctrines/<key>.svg`) für die Doktrin-Wahl/UI — P2-Backlog.

---

## 10. Abhängigkeiten

- **`shared/balance.json`** — kanonische Keys = Dateinamen. Bei neuen Keys: Asset ergänzen.
- **[STYLE_BIBLE.md](./STYLE_BIBLE.md)** — Palette/Form/Format/Prompt-Baukasten (verbindlich).
- **Frontend** (`frontend/`) — lädt Assets per Key; CSS-Variablen spiegeln Style-Bible-Tokens.
  *(Frontend wird hier NICHT verändert.)*
- **`assets/placeholders/`** — sofort nutzbare SVG-Stubs bis zur finalen Produktion
  (siehe `assets/placeholders/README.md`).

---

### Änderungshistorie
- **v0.2 (2026-06-07):** v0.1-Satz (§1–§8) als **PRODUZIERT** markiert (hochwertige PNGs,
  ins Frontend integriert, Platzhalter entfernt). Neue **§11 Rollen-Kampf-Assets** ergänzt
  (12 neue Schiffe + 4 Waffen-Icons + 5 Status-Icons + 3 Effekte) aus Doku 03b/03c. Bilanz/
  Status-Banner aktualisiert.
- **v0.1 (2026-06-06):** Erstfassung. 8 Kategorien, ~129 Assets gegen `balance.json` +
  System-Dokus 01/03/05/06/11 abgeglichen; modulares Commander-Persona-System (USP);
  Vollständigkeits-Mapping; Backlog markiert.
</content>
</invoke>
