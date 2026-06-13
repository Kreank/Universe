# 🎨 Asset-Liste — Universe

> Arbeitsdatei für **Codex** (Asset-Agent). Aufgabe: die hier gelisteten Assets erstellen
> und in die richtigen Ordner einsortieren. Diese Liste wird laufend von uns befüllt —
> Codex arbeitet sie ab und hakt erledigte Einträge ab.

---

## 📁 Ordner-Konventionen (Einsortier-Ziele)

Es gibt **zwei** Asset-Wurzeln:

| Wurzel | Zweck |
|---|---|
| `assets/` | Quelle/Master (nach Kategorie sortiert) |
| `frontend/src/assets/img/` | Vom Frontend genutzter Spiegel (hierhin gehört das ausgelieferte Bild) |

**Vorhandene Kategorie-Ordner** (in `assets/` bzw. `frontend/src/assets/img/`):
`backgrounds` · `buildings` · `commanders` (faces/frames/markers/spec) · `defenses` ·
`effects` · `ships` · `icons` (missions/nav/planets/range/ranks/resources/spec/status/tech/traits/ui/weapons)

> Neue Kategorie nötig? Erst hier notieren, nicht still anlegen.

---

## ✅ Legende

- **Status:** ⬜ offen · 🟧 in Arbeit · ✅ fertig
- **Pfad:** Zielordner relativ zur Asset-Wurzel
- **Format:** z. B. PNG transparent, 256×256

---

## 📋 Benötigte Assets

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | empty_fleet | `empty/` (NEU) | PNG transparent, 512×512 | Empty-State-Illustration „keine Flotten unterwegs": leerer Hangar / einzelnes angedocktes Schiff in Ruhe. Stil siehe unten. |
| ✅ | empty_inbox | `empty/` (NEU) | PNG transparent, 512×512 | Empty-State „Postfach leer": stille Kommunikations-Antenne / Satellitenschüssel ohne Signal. |
| ✅ | empty_commanders | `empty/` (NEU) | PNG transparent, 512×512 | Empty-State „keine Kommandeure": leerer Kommandosessel / schwebende Offiziers-Insignie. |
| ✅ | empty_search | `empty/` (NEU) | PNG transparent, 512×512 | Empty-State „nichts gefunden/entdeckt" (Galaxie/Suche): Radar-/Scanner-Sweep ohne Treffer. |
| ✅ | empty_generic | `empty/` (NEU) | PNG transparent, 512×512 | Allgemeiner Empty-State (Fallback): schwebender Asteroid / einzelner Sternen-Funke. |
| ✅ | stat_attack | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Angriff im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ✅ | stat_shield | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Schild/Verteidigung im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ✅ | stat_cargo | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Fracht/Laderaum im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ✅ | stat_speed | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Tempo/Geschwindigkeit im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ✅ | stat_fuel | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Treibstoff im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ✅ | stat_energy | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Energie im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ✅ | trait_category_admin | `icons/traits/` | PNG transparent, 256×256 | Fähigkeits-Kategorie-Icon für admin; konsistenter Trait/Commander-Sci-Fi-UI-Stil, ohne Text. |
| ✅ | trait_category_general | `icons/traits/` | PNG transparent, 256×256 | Fähigkeits-Kategorie-Icon für general; konsistenter Trait/Commander-Sci-Fi-UI-Stil, ohne Text. |
| ✅ | trash | `icons/ui/` → wird als `assets/img/ui/trash.png` ausgeliefert | PNG transparent, 256×256 | Button-Icon „Löschen" (Postfach: Funkspruch löschen / Gelesene löschen). Mülleimer/Papierkorb, monochrom-hell, Sci-Fi-UI-Linienstil, ohne Text. Wird ~16px klein gerendert → klar lesbare Silhouette. |
| ✅ | bg_shipyard | `backgrounds/` | JPG, 1920×1080, dunkel | Screen-Hintergrund **Werft**: orbitale Werft / Hangar mit Baugerüsten + halbfertigen Schiffen, Dock-Strahler. Stil-Brief unten. |
| ✅ | bg_research | `backgrounds/` | JPG, 1920×1080, dunkel | Screen-Hintergrund **Forschung/Techbaum**: Holo-Datenlabor, schwebende Hologramme/Datenstränge, blau-cyan. |
| ✅ | bg_commanders | `backgrounds/` | JPG, 1920×1080, dunkel | Screen-Hintergrund **Kommandozentrale**: Kommandobrücke mit Panoramafenster ins All, ruhige Konsolen-Lichter. |
| ✅ | bg_combat | `backgrounds/` | JPG, 1920×1080, dunkel | Screen-Hintergrund **Simulator/Kampfbericht**: Weltraumschlacht-Szene — ferne Explosionen + Wrackteile + Sternenfeld, dramatisch, sparsame rot-orange Glut. |
| ✅ | bg_trade | `backgrounds/` | JPG, 1920×1080, dunkel | Screen-Hintergrund **Handel**: Handelsstation / Docking-Bay mit Frachtcontainern + andockenden Transportern, warme Markt-Lichter. |
| ✅ | bg_buildings | `backgrounds/` | JPG, 1920×1080, dunkel | Screen-Hintergrund **Gebäude**: Kolonie/Planetenoberfläche aus niedrigem Orbit bei Nacht, leuchtende Basis-Strukturen. |

> **Stil-/Kompositions-Brief für ALLE bg_* (Screen-Hintergründe):** modern-cinematic Sci-Fi,
> **dunkel** (sitzt hinter Inhalt, wird im UI zusätzlich ~65–85% abgedunkelt → ruhig, nicht grell),
> cyan-kompatible Palette (Akzent `#2ee6d6`/`#5aa9ff`), **Komposition mit ruhiger/dunkler Mitte**
> (dort liegen Karten/Text) und **Detail/Interesse eher an Rändern & oben** (analog `dashboard.jpg`),
> KEIN Text, KEINE UI-Elemente, kein harter Fokuspunkt im Zentrum. Ablage in `assets/backgrounds/`
> UND `frontend/src/assets/img/backgrounds/`; Referenz als `assets/img/backgrounds/<name>.jpg`.

### 🎬 Bewegte Hintergründe (Loop-Videos) — heben die Szene auf „cinematic"

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | login | `backgrounds/` (.webm **und** .mp4) | webm VP9 + mp4 H.264 | **Animierte Version von `login.jpg`** (Poster bleibt login.jpg). Sehr langsamer, edler Loop: driftende Sterne + leicht waberndes Nebel-Leuchten + minimaler Kamera-Push (Parallax). IM CODE BEREITS VERDRAHTET (Login-Screen). |
| ✅ | dashboard | `backgrounds/` (.webm + .mp4) | webm VP9 + mp4 H.264 | **Animierte Version von `dashboard.jpg`** (globaler App-Backdrop). Dezente Sternendrift + sanftes Nebel-Pulsieren, ruhige dunkle Mitte. |
| ✅ | bg_combat | `backgrounds/` (.webm + .mp4) | webm VP9 + mp4 H.264 | **Animierte Version von `bg_combat.jpg`**: ferne Explosions-Glut flackert leise an den Rändern, Wrackteile driften langsam, Funken. Mitte ruhig/dunkel. |
| ✅ | system_view | `backgrounds/` (.webm + .mp4) | webm VP9 + mp4 H.264 | **Animierte Version von `system_view.png`** (Galaxie-Ansicht): langsamer Scanner-/Radar-Sweep + Sternendrift. |

> **Format-/Stil-Brief für ALLE Loop-Videos:** nahtloser Loop ~8–12 s, 1920×1080, **Zielgröße ≤ ~2–3 MB**
> je Datei (niedrige Bitrate — dunkle Szenen komprimieren gut). IMMER als Paar **`<name>.webm` (VP9)
> + `<name>.mp4` (H.264)** liefern; das gleichnamige Standbild (`.jpg`/`.png`) bleibt als Poster/Fallback.
> **Sehr langsame, subtile Bewegung; dunkel; ruhige/dunkle Mitte** (dort liegt der Inhalt) — Bewegung nur
> an Rändern/oben (driftende Sterne/Nebel/Funken). **KEIN schnelles Flackern, kein harter Schnitt, kein
> Text/UI.** Optisch = das Standbild, nur „lebendig". Ablage wie die bg_*: `assets/backgrounds/` UND
> `frontend/src/assets/img/backgrounds/`.

### ✨ FX-Overlay-Loops (transparent) — optionaler Flair auf aktiven Kacheln/Zeilen

> Kleine, TRANSPARENTE Loops, die als halbtransparentes Overlay NUR auf aktiven Elementen liegen
> (Bau läuft / Mine fördert / Forschung läuft). Die strukturellen „lebt-wenn-aktiv"-Effekte
> (Puls-Ring, Balken-Schimmer) sind bereits in CSS gelöst — diese Overlays sind das *i-Tüpfelchen*.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ⬜ | fx_construction | `fx/` (NEU) | webm VP9 **mit Alpha** + APNG, ~256×256 | Bau-Loop: dezente Schweiß-/Funken-Glints + leichtes Baugerüst-Flimmern. Liegt auf Kacheln „im Bau" (Gebäude/Werft). Transparent, cyan, subtil. |
| ⬜ | fx_extraction | `fx/` (NEU) | webm VP9 **mit Alpha** + APNG, ~256×256 | Förder-Loop: langsam aufsteigende Energie-/Erz-Partikel. Liegt auf aktiven Minen-Kacheln. Transparent, subtil. |
| ⬜ | fx_research | `fx/` (NEU) | webm VP9 **mit Alpha** + APNG, ~256×256 | Forschungs-Loop: wandernde Daten-/Hologramm-Schlieren. Liegt auf aktiver Forschung. Transparent, blau-cyan, subtil. |

> **Brief FX-Overlays:** nahtloser kurzer Loop (~3–6 s), **transparenter Hintergrund** (Alpha!),
> sehr dezent (wird mit ~30–50 % Deckkraft eingeblendet), dunkel/cyan, kein Text. webm-VP9-mit-Alpha
> als Haupt­format + **APNG-Fallback** (Safari kann webm-Alpha schlecht). Ablage `assets/fx/` UND
> `frontend/src/assets/img/fx/`. Werden später per CSS/Overlay nur auf aktive Elemente gelegt.

### 🟢 ANIMIERTE ARTWORKS — die Icons selbst leben (Hauptwunsch!)

> **Animierte Version des JEWEILIGEN bestehenden Icons** (Mine raucht, Schiff verlässt Hangar,
> Energie fließt, Triebwerk zündet …). **WICHTIG — Format & Ablage so, dass NULL Code-Änderung nötig
> ist:** Liefere ein **APNG (animiertes PNG) unter EXAKT demselben Dateinamen `.png`**, das das
> bestehende statische `.png` **ersetzt** (z.B. `buildings/metal_mine.png`). Das **erste Einzelbild
> MUSS das aktuelle statische Artwork sein** (so bleibt überall ein sauberer Fallback und es animiert
> automatisch dort, wo das Icon schon angezeigt wird — Kachel + Detail-Popup). Vorhandenes Artwork als
> Basis nehmen (gleiche Komposition/Farbe/Perspektive), nur die genannten Teile bewegen — Rest ruhig.

| Status | Name | Kategorie / Pfad (ersetzt das .png) | Format | Beschreibung / Referenz (was sich bewegt) |
|:---:|---|---|---|---|
| ⬜ | metal_mine | `buildings/metal_mine.png` | APNG, 256×256, alpha | Rauch steigt aus den Schornsteinen; Förderband/Bagger bewegt sich leicht. |
| ⬜ | crystal_mine | `buildings/crystal_mine.png` | APNG, 256×256, alpha | Kristalle schimmern/pulsieren sanft, leichter Abbau-Funke. |
| ⬜ | deuterium_synth | `buildings/deuterium_synth.png` | APNG, 256×256, alpha | Tanks blubbern, aufsteigende Gasblasen + leichter Dampf. |
| ⬜ | solar_plant | `buildings/solar_plant.png` | APNG, 256×256, alpha | Energie fließt/leuchtet über die Solarpaneele (wandernder Lichtpuls). |
| ⬜ | fusion_reactor | `buildings/fusion_reactor.png` | APNG, 256×256, alpha | Pulsierender Fusionskern, Energie-Glühen. |
| ⬜ | shipyard | `buildings/shipyard.png` | APNG, 256×256, alpha | Schweißfunken + ein kleines Schiff dockt aus/läuft aus dem Hangar; Kran bewegt sich. |
| ⬜ | robot_factory | `buildings/robot_factory.png` | APNG, 256×256, alpha | Roboterarme arbeiten in Schleife. |
| ⬜ | combustion_drive | `tech/combustion_drive.png` | APNG, 256×256, alpha | Triebwerk zündet — Flammenstrahl pulsiert/flackert. |
| ⬜ | impulse_drive | `tech/impulse_drive.png` | APNG, 256×256, alpha | Impuls-Triebwerk glüht rhythmisch (Plasma-Puls). |
| ⬜ | hyperspace_drive | `tech/hyperspace_drive.png` | APNG, 256×256, alpha | Hyperraum-Wirbel dreht/leuchtet langsam. |
| ⬜ | energy_tech | `tech/energy_tech.png` | APNG, 256×256, alpha | Energie-Bögen/Funken zucken zwischen den Knoten. |

> **Brief animierte Artworks:** nahtloser Loop ~2–5 s, transparenter Hintergrund (alpha), **dezent**
> (subtile Bewegung, kein hektisches Flackern), Stil/Komposition exakt wie das vorhandene `.png`,
> **Frame 1 = aktuelles Standbild**. Ablage in `assets/<cat>/` UND `frontend/src/assets/img/<cat>/`
> (beide ersetzen). APNG ist abwärtskompatibel (zeigt notfalls nur Frame 1). Weitere Artworks (Schiffe
> mit Triebwerks-Glühen, Waffen-Techs mit Strahl) können nach demselben Schema folgen — erst diese Welle.
> Falls APNG technisch nicht geht: gleichwertig **animiertes GIF gleichen Namens** (ohne weiche Alpha-
> Kanten) — aber APNG ist klar bevorzugt (Alpha + Qualität).

### 🎞️ KAMPF-KINO — Highlight-Clips im Kampfbericht (event-gekoppelt)

> Generische, wiederverwendbare Kino-Clips. Der Kampfbericht erkennt aus den Schlacht-Daten das
> markanteste Ereignis und spielt den passenden Clip oben im Bericht ab (Priorität ungefähr:
> **Mondzerstörung > Todesstern-Rückschlag > Entern > Ionen-Lähmung > Hinterhalt > Schwarm/Duell >
> Sieg/Niederlage/Flucht**). Kein per-Kampf-Unikat nötig — der Clip illustriert den TYP des Ereignisses.
> Jeweils **`.webm` (VP9) + `.mp4` (H.264) + `.jpg` als Poster**, abspielen als „Replay" (einmal,
> stummgeschaltet, mit Replay-Button); Reduced-Motion/Mobile → nur das Poster.

| Status | Name | Pfad (`cinematics/`) | Format | Clip-Idee · Trigger |
|:---:|---|---|---|---|
| ⬜ | cine_ambush | `cinematics/cine_ambush.*` | webm+mp4+jpg, ~10 s, 1280×720 | **Tarnkappen-Eröffnung:** der Stealth-Jäger schält sich aus dem Nichts, erste lautlose Salve trifft ahnungslose Schiffe. · *Trigger: Hinterhalt-Runde.* |
| ⬜ | cine_swarm_capital | `cinematics/cine_swarm_capital.*` | webm+mp4+jpg, ~10 s | **Schwarm vs. Koloss:** Jäger & Drohnen umkreisen einen Zerstörer, tänzeln durchs Abwehrfeuer, knabbern ihn nieder. · *Trigger: viele Leichtschiffe vs. Großkampfschiff.* |
| ⬜ | cine_capital_duel | `cinematics/cine_capital_duel.*` | webm+mp4+jpg, ~10 s | **Breitseiten:** zwei Schlachtschiff-Linien tauschen schwere Salven, Schilde flackern, Treffer reißen Hüllen auf. · *Trigger: beide Seiten kapital-lastig.* |
| ⬜ | cine_ion_disable | `cinematics/cine_ion_disable.*` | webm+mp4+jpg, ~8 s | **Lähmung:** Ionenstrahl trifft ein Schiff, Triebwerk erlischt, es treibt manövrierunfähig. · *Trigger: Antrieb-gelähmte Schiffe.* |
| ⬜ | cine_boarding | `cinematics/cine_boarding.*` | webm+mp4+jpg, ~9 s | **Entern:** Enterschiff dockt an, Kaperkommando, das Schiff wechselt die Fraktionsfarbe. · *Trigger: gekaperte Schiffe.* |
| ⬜ | cine_moon_destroy | `cinematics/cine_moon_destroy.*` | webm+mp4+jpg, **~14 s** (Showpiece) | **Mondzerstörung:** Todesstern lädt auf und feuert einen gewaltigen Laser auf den Mond — die Kruste löst sich in Platten, der Trabant glüht/verflüssigt, Risse durchziehen ihn, finale Explosion + Trümmerwolke. · *Trigger: Mond zerstört.* |
| ⬜ | cine_deathstar_backfire | `cinematics/cine_deathstar_backfire.*` | webm+mp4+jpg, ~10 s | **Rückschlag:** der Todesstern-Laser überlädt/fehlzündet, der RIP wird von innen zerrissen. · *Trigger: Todesstern-Backfire.* |
| ⬜ | cine_victory | `cinematics/cine_victory.*` | webm+mp4+jpg, ~8 s | **Triumph:** letzter Gegner explodiert, eigene Flotte zieht ungebrochen durchs treibende Trümmerfeld. · *Trigger: Sieg.* |
| ⬜ | cine_defeat | `cinematics/cine_defeat.*` | webm+mp4+jpg, ~8 s | **Niederlage:** eigene Schiffe brennen & bersten, Wracks treiben ab. · *Trigger: Niederlage.* |
| ⬜ | cine_retreat | `cinematics/cine_retreat.*` | webm+mp4+jpg, ~8 s | **Rückzug/Fleetsave:** Flotte klinkt aus, zieht in den Hyperraum-Sprung davon. · *Trigger: Disengage/Flucht.* |
| ⬜ | cine_clash | `cinematics/cine_clash.*` | webm+mp4+jpg, ~9 s | **Generisches Aufeinandertreffen** (Fallback-Opener, wenn kein Spezial-Event passt). · *Trigger: Default.* |

> **Brief Kampf-Kino:** dunkler Weltraum, cinematic, **kein Text/keine UI/keine HUD-Elemente**,
> 16:9 ~1280×720, Ziel ≤ ~4–6 MB je Clip (einmaliges Replay, keine Endlosschleife). Schiffe dürfen
> stilisiert sein (müssen nicht exakt die Spielmodelle treffen) — Hauptsache Stimmung + lesbares
> Ereignis. Palette: Cyan/Blau für „eigene", Magenta/Rot `#ff4d7d` für Feind/Gefahr, warme Glut bei
> Explosionen. Anfang/Ende dunkel (sauberer Ein-/Ausstieg im Bericht). Ablage `assets/cinematics/`
> UND `frontend/src/assets/img/cinematics/`; Referenz `assets/img/cinematics/<name>.webm|.mp4|.jpg`.
> Reihenfolge der Wichtigkeit für dich: **cine_moon_destroy** (Showpiece) zuerst, dann cine_ambush,
> cine_victory, cine_defeat — der Rest nach Lust.
| ✅ | advisor | `icons/ui/` → wird als `assets/img/ui/advisor.png` ausgeliefert | PNG transparent, 256×256 | Button-Icon „KI-Berater fragen" (Postfach). Stilisiertes Gehirn / KI-Knoten-Netz / Berater-Hologrammkopf, dezenter Cyan-Akzent `#2fe3d2`, Sci-Fi-UI-Linienstil, ohne Text. ~16px-tauglich. |
| ✅ | broom | `icons/ui/` → wird als `assets/img/ui/broom.png` ausgeliefert | PNG transparent, 256×256 | Button-Icon „Leeren/Zurücksetzen" (Kampf-Simulator). Besen oder „Clear/Wisch"-Symbol, monochrom-hell, Sci-Fi-UI-Linienstil, ohne Text. ~16px-tauglich. |

> **NEUE Kategorie `empty/`** (Empty-State-Spot-Illustrationen) — bitte in `assets/empty/` UND
> `frontend/src/assets/img/empty/` ablegen. Werden als `assets/img/empty/<name>.png` referenziert.
>
> **Gemeinsamer Stil-Brief (für Konsistenz, gilt für ALLE empty_*):** modern-cinematic Sci-Fi,
> minimalistisch, EIN zentrales Motiv, dezente Cyan-Linien/Glow (Akzent `#2fe3d2`), gedämpft/
> entsättigt, transparenter Hintergrund (muss auf sehr dunklem UI `#080d18` gut sitzen), KEIN Text,
> ruhig (nicht grell/neon-überladen). Wirken als große, halbtransparente „Leerzustands"-Grafik
> hinter einem kurzen Hinweistext + Aktions-Button.

---

## 🗒️ Notizen für Codex

- Optional/später (noch NICHT verdrahtet, daher keine aktive Anforderung): Regions-Hintergründe
  `backgrounds/region_core|region_mid|region_frontier` (atmosphärische Nebel je Galaxie-Region) —
  erst eintragen, wenn das Frontend sie per Region einbindet.
- **`ui`-Button-Icons (trash/advisor/broom):** Master nach `assets/icons/ui/<name>.png`, Spiegel nach
  `frontend/src/assets/img/ui/<name>.png` (der `img/ui/`-Ordner existiert im Frontend noch NICHT → bitte
  anlegen). Sind im Code bereits verdrahtet (`uiIcon()`), zeigen bis dahin den Emoji-Fallback. Sie sitzen
  als kleines führendes Icon IN Buttons (neben Text) → schlichte, klar lesbare Silhouette wichtig, kein Rahmen.
