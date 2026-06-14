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

### 🎬 Bewegte Hintergründe (Loop-Videos) — ❌ VERWORFEN, Dateien entfernt

> **NICHT bauen / nicht verdrahten.** Vollbild-Loop-Video als Hintergrund ruckelte hinter der Glas-UI
> (`backdrop-filter`-Leisten zeichnen das bewegte Bild jeden Frame neu). **Hintergründe bleiben statische
> Bilder.** Die testweise gelieferten `.webm`/`.mp4`-Dateien (login/dashboard/bg_combat/system_view in
> `assets/backgrounds/` **und** `frontend/src/assets/img/backgrounds/`) wurden am **2026-06-14 gelöscht**
> (gefielen dem Nutzer nicht). Der Nutzer erstellt Videos ggf. anderweitig und liefert sie dann separat —
> bis dahin hier KEINE Loop-Video-Assets anfordern oder einbinden.

### ✨ FX-Overlay-Loops (transparent) — ❌ ZURÜCKGESTELLT (nicht bauen)

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

### 🟢 ANIMIERTE ARTWORKS — ⚠️ NEU EXPORTIEREN (Encoding-Bug in der 1. Welle)

> **Die gelieferten APNGs sind verdrahtet und werden korrekt geladen — aber falsch enkodiert und
> sehen dadurch KAPUTT aus** (Basisbild verschwindet, nur zuckende Fragmente bleiben). Bitte mit den
> unten genannten Einstellungen **neu exportieren** (gleiche Dateinamen, ersetzen). Am Code ist nichts
> zu ändern.
>
> **🔴 GENAUE URSACHE (analysiert):** In den gelieferten Dateien hat **jeder** Frame
> `dispose_op = 2 (APNG_DISPOSE_OP_PREVIOUS)` und die Frames 2…N sind nur **kleine Teil-Rechtecke**
> (geänderter Ausschnitt). `PREVIOUS` setzt den Bereich nach jedem Frame auf den Zustand *davor*
> zurück → die volle Basis (Frame 1) wird sofort wieder geleert, und ab Frame 2 ist nur noch ein
> winziges Fragment auf transparentem/leerem Grund sichtbar. Das Gebäude „verschwindet".
>
> **✅ KORREKTE EXPORT-EINSTELLUNGEN (bitte exakt so):**
> - **Jeder Frame als VOLLES 256×256-Bild** exportieren (keine Delta-/Crop-Optimierung, kein
>   `x_offset`/`y_offset` ≠ 0, keine Teil-Rechtecke). Lieber etwas größere Datei als Geister-Frames.
> - **`dispose_op = 0 (NONE)`** für alle Frames. **NIEMALS `2 (PREVIOUS)`.**
> - **`blend_op = 0 (SOURCE)`** für alle Frames (jeder Frame ersetzt die Leinwand vollständig).
> - **`num_plays = 0`** (Endlos-Loop). Loop nahtlos.
> - **Frame 1 = aktuelles Standbild** (sauberer Fallback). Jeder weitere Frame zeigt das **komplette**
>   Artwork inkl. unbewegtem Rest, nur die genannten Teile bewegen sich.
> - Praktisch am sichersten: alle Frames als eigenständige Voll-PNGs rendern und z. B. mit
>   `ffmpeg -i frame_%03d.png -plays 0 out.apng` oder `apngasm frame_*.png` **ohne** „optimize/crop"
>   zusammensetzen (Optimierung ist genau das, was den Bug erzeugt hat).
> - Dateigröße im Rahmen halten (~≤ 800 KB–1 MB je Datei; Frame-Zahl/Auflösung ggf. reduzieren).

| Status | Name | Kategorie / Pfad (ersetzt das .png) | Format | Beschreibung / Referenz (was sich bewegt) |
|:---:|---|---|---|---|
| 🔁 | metal_mine | `buildings/metal_mine.png` | APNG, 256×256, alpha, Voll-Frames | Rauch steigt aus den Schornsteinen; Förderband/Bagger bewegt sich leicht. |
| 🔁 | crystal_mine | `buildings/crystal_mine.png` | APNG, 256×256, alpha, Voll-Frames | Kristalle schimmern/pulsieren sanft, leichter Abbau-Funke. |
| 🔁 | deuterium_synth | `buildings/deuterium_synth.png` | APNG, 256×256, alpha, Voll-Frames | Tanks blubbern, aufsteigende Gasblasen + leichter Dampf. |
| 🔁 | solar_plant | `buildings/solar_plant.png` | APNG, 256×256, alpha, Voll-Frames | Energie fließt/leuchtet über die Solarpaneele (wandernder Lichtpuls). |
| 🔁 | fusion_reactor | `buildings/fusion_reactor.png` | APNG, 256×256, alpha, Voll-Frames | Pulsierender Fusionskern, Energie-Glühen. |
| 🔁 | shipyard | `buildings/shipyard.png` | APNG, 256×256, alpha, Voll-Frames | Schweißfunken + ein kleines Schiff dockt aus/läuft aus dem Hangar; Kran bewegt sich. |
| 🔁 | robot_factory | `buildings/robot_factory.png` | APNG, 256×256, alpha, Voll-Frames | Roboterarme arbeiten in Schleife. |
| 🔁 | combustion_drive | `tech/combustion_drive.png` | APNG, 256×256, alpha, Voll-Frames | Triebwerk zündet — Flammenstrahl pulsiert/flackert. |
| 🔁 | impulse_drive | `tech/impulse_drive.png` | APNG, 256×256, alpha, Voll-Frames | Impuls-Triebwerk glüht rhythmisch (Plasma-Puls). |
| 🔁 | hyperspace_drive | `tech/hyperspace_drive.png` | APNG, 256×256, alpha, Voll-Frames | Hyperraum-Wirbel dreht/leuchtet langsam. |
| 🔁 | energy_tech | `tech/energy_tech.png` | APNG, 256×256, alpha, Voll-Frames | Energie-Bögen/Funken zucken zwischen den Knoten. |

> **Brief animierte Artworks:** nahtloser Loop ~2–5 s, transparenter Hintergrund (alpha), **dezent**
> (subtile Bewegung, kein hektisches Flackern), Stil/Komposition exakt wie das vorhandene `.png`,
> **Frame 1 = aktuelles Standbild**, **Voll-Frames + `dispose_op=0` + `blend_op=0` + `num_plays=0`**
> (siehe Fix-Block oben). Ablage in `assets/<cat>/` UND `frontend/src/assets/img/<cat>/`
> (beide ersetzen). APNG ist abwärtskompatibel (zeigt notfalls nur Frame 1). Weitere Artworks (Schiffe
> mit Triebwerks-Glühen, Waffen-Techs mit Strahl) können nach demselben Schema folgen — erst diese Welle
> sauber neu exportieren. Falls APNG-Tooling Probleme macht: gleichwertig **animiertes GIF gleichen
> Namens** (ohne weiche Alpha-Kanten) — aber APNG ist bevorzugt (Alpha + Qualität).

### 🎞️ KAMPF-KINO — Highlight-Clips im Kampfbericht (event-gekoppelt) ✅ AKTIV

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

### 📡 BERICHT-VIDEOS — Spionage & NPC-Drohungen ✅ AKTIV

> Wie das Kampf-Kino: kurze Clips, die **im jeweiligen Funkspruch/Bericht auf Klick (Replay)**
> abgespielt werden — kein Hintergrund, kein Blur drüber → flüssig. Generisch & wiederverwendbar.
> Format wie Kampf-Kino: **`.webm` (VP9) + `.mp4` (H.264) + `.jpg`-Poster**, dunkler Weltraum,
> kein Text/HUD, dunkler Ein-/Ausstieg. Ablage `assets/cinematics/` + `frontend/src/assets/img/cinematics/`.

| Status | Name | Pfad (`cinematics/`) | Format | Clip-Idee · spielt bei … |
|:---:|---|---|---|---|
| ⬜ | cine_spy | `cinematics/cine_spy.*` | webm+mp4+jpg, ~8 s, 1280×720 | **Spionage-Sweep:** Spähsonden gleiten ans Ziel, Scanner-Strahl tastet ab, ein Hologramm der gegnerischen Flotte/Verteidigung baut sich auf. · *Spionagebericht (spy_report).* |
| ⬜ | cine_npc_threat | `cinematics/cine_npc_threat.*` | webm+mp4+jpg, ~7 s, 1280×720 | **Drohung:** ein finsteres NPC-Kriegsschiff dreht bei / eine Kommandeurs-Silhouette auf dunkler Brücke „hailt" bedrohlich (Statik/Funk-Flackern, rote `#ff4d7d` Akzente). · *NPC-Droh-/Spott-Funkspruch.* |

> Optional später: `cine_spy_fail` (Sonden entdeckt/abgeschossen — keine Daten), `cine_npc_taunt`
> (höhnisch nach gewonnener Verteidigung) — erst die zwei oben.
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

## 🌌 Endgame-Forschung & Megastrukturen (2026-06-14, live)

> Neues Endgame-System (Forschungs-„Endgame"-Tab, Megastruktur-Screen, exotische Ressourcen).
> Verdrahtung steht & ist live — zeigt bis zu den Assets den Emoji-/Glyph-Fallback.
> **Gemeinsamer Stil (alle Einträge hier):** modern-cinematic Sci-Fi, EIN klares Zentralmotiv,
> dunkler Grund (sitzt auf `#080d18`), Akzent **cyan `#2fe3d2`**, Gefahr/Militär darf **magenta
> `#ff4d7d`** nutzen; KEIN Text, transparenter Hintergrund. Komposition exakt wie die jeweils
> vorhandenen Nachbar-Assets (`tech/*.png`, `icons/nav/*.png`, `icons/resources/*.png`,
> `buildings/*.png`).

### Forschungs-Icons (neuer „Endgame"-Tab) — referenziert als `assets/img/tech/<name>.png`

> ⚠️ **NEU ERSTELLEN — 1. Welle grenzwertig.** **Exakt der Stil/das Rendering der vorhandenen,
> guten Tech-Icons** verwenden — **Stil-Anker (genau anschauen!):** `tech/weapons_tech.png`,
> `tech/shield_tech.png`, `tech/armor_tech.png`, `tech/energy_tech.png`. Also: EIN klares,
> plastisch gerendertes Tech-Emblem/Objekt mittig, gleiche Strichstärke/Schattierung/Glanz wie
> jene, cyan `#2fe3d2` Akzentlicht, transparenter Hintergrund, 256×256, KEIN Text. Nicht flach/
> nicht clipart-haft — gleiche Material- und Lichtanmutung wie die Anker-Icons.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | research_network | `tech/research_network.png` | PNG transparent, 256×256 (Stil = `tech/energy_tech.png`) | Intergalaktisches Forschungsnetzwerk: mehrere vernetzte Labor-Knoten, durch leuchtende cyan Datenlinien zu einem Netz/Konstellation verbunden — als plastisches Tech-Emblem gerendert. |
| ✅ | terraforming | `tech/terraforming.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Terraforming: ein Planet halb kahl / halb begrünt mit umgebendem Atmosphären-Prozessor-Ring — plastisch gerendert wie die Tech-Anker. |
| ✅ | extraction_tech | `tech/extraction_tech.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Fördertechnik: plastischer Bohr-/Förderkopf mit aufsteigendem Erz-/Kristallstrom. |
| ✅ | extraction_mastery | `tech/extraction_mastery.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Förder-Meisterschaft (wiederholbar): wie `extraction_tech` + dezenter **∞-/Loop-Ring** + leicht goldener Akzent. **„repeatable"-Merkmal = ∞-Ring.** |
| ✅ | weapons_mastery | `tech/weapons_mastery.png` | PNG transparent, 256×256 (Stil = `tech/weapons_tech.png`) | Waffen-Meisterschaft (wiederholbar): Waffenkern/Zielkreuz mit Stufen-Chevrons + **∞-Ring**. Direkt am Look von `weapons_tech` orientieren. |
| ✅ | shield_mastery | `tech/shield_mastery.png` | PNG transparent, 256×256 (Stil = `tech/shield_tech.png`) | Schild-Meisterschaft (wiederholbar): Schildemblem mit Verstärkungsringen + **∞-Ring**. Direkt am Look von `shield_tech` orientieren. |
| ✅ | armor_mastery | `tech/armor_mastery.png` | PNG transparent, 256×256 (Stil = `tech/armor_tech.png`) | Panzerungs-Meisterschaft (wiederholbar): geschichtete Verbundpanzer-Platten + **∞-Ring**. Direkt am Look von `armor_tech` orientieren. |

### Navigations-Icon — referenziert als `assets/img/nav/megastructures.png`

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | megastructures (nav) | `icons/nav/megastructures.png` | PNG transparent, 256×256 (~24px lesbar) | Nav-Icon „Megastrukturen": kolossale Orbitalstruktur als schlichte Silhouette — Ring-/Dyson-Segment um einen kleinen Stern/Planeten, cyan Akzent. Stil wie vorhandene `nav/*.png`. |

### Megastruktur-Artworks — NEUER Ordner `megastructures/` (Master `assets/megastructures/`, Spiegel `frontend/src/assets/img/megastructures/`)

> ⚠️ **NEU ERSTELLEN — 1. Welle war zu abstrakt (Orbital-Ringe/Space-Scene, unbrauchbar).**
> **Megastrukturen sind GEBÄUDE. Sie müssen EXAKT wie die vorhandenen `buildings/*.png`
> aussehen** — gleiches Rendering, gleiche Perspektive, gleiche Lichtstimmung/Palette.
> **Konkrete Stil-Anker (genau anschauen!):** `buildings/research_lab.png`, `buildings/shipyard.png`,
> `buildings/fusion_reactor.png`, `buildings/command_center.png`.
> **Vorgabe je Asset:** EIN einzelnes, plastisch gerendertes Bauwerk, mittig, in leichter
> erhöhter 3/4-Aufsicht (wie die Gebäude), halb-realistisch malerisch-cinematic, metallische
> Oberflächen mit cyan `#2fe3d2` Akzentlicht, transparenter Hintergrund, 512×512 RGBA.
> **NICHT:** abstrakte Weltraumszenen, frei schwebende Ringe, Nebel, flache Icons, Text.
> Jede Megastruktur = einfach eine **monumentalere, größere Variante eines Gebäudes** ihrer Funktion.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | research_nexus | `megastructures/research_nexus.png` | PNG transparent, 512×512 (wie `buildings/*`) | Forschungs-Nexus: ein **monumentaler Forschungs-Komplex als Bauwerk** — wie ein gigantisch hochskaliertes `research_lab` mit Türmen/Kuppeln, Antennen-/Sensor-Arrays, leuchtenden cyan Wissens-Kernen & Hologramm-Projektionen. Gerendert wie ein Gebäude (3/4-Aufsicht), NICHT als schwebende Ringe. |
| ✅ | matter_decompressor | `megastructures/matter_decompressor.png` | PNG transparent, 512×512 (wie `buildings/*`) | Materie-Dekompressor: ein **massives Industrie-/Förder-Bauwerk** mit großem Einlauf-Trichter/Schlund, Förderbändern, Erz-Verarbeitungstanks — wie eine riesige Mine/Raffinerie als Gebäude. Dezenter Materie-Strom in den Trichter. Gerendert wie ein Gebäude. |
| ✅ | antimatter_forge | `megastructures/antimatter_forge.png` | PNG transparent, 512×512 (wie `buildings/*`) | Antimaterie-Schmiede: eine **schwer gepanzerte Militär-Schmiede/Reaktor-Halle als Bauwerk** — Eindämmungstürme, Schmiede-Hallen, im Kern ein **magenta `#ff4d7d`** glühender Antimaterie-Reaktor. Bedrohlich-militärisch, aber als Gebäude gerendert (wie `fusion_reactor`, nur martialischer). |

### Exo-Minen — GEBÄUDE (Master `assets/buildings/`, Spiegel `frontend/src/assets/img/buildings/`)

> ⬜ **NEU ERSTELLEN (2026-06-14).** Zwei neue **reguläre Gebäude** (Quelle für exotische Materie,
> positions-gebunden: Antimaterie nur auf heißen inneren Slots Pos 1–2, Dunkle Materie nur auf kalten
> äußeren Slots Pos 14–15). **Müssen EXAKT wie die vorhandenen `buildings/*.png` aussehen** — gleiche
> 3/4-Aufsicht, gleiches Rendering/Licht/Palette. **Stil-Anker (genau anschauen!):** `buildings/metal_mine.png`,
> `buildings/fusion_reactor.png`, `buildings/solar_plant.png`. Format wie die anderen Gebäude (PNG RGBA,
> transparent, **512×512**, EIN plastisches Bauwerk mittig, cyan `#2fe3d2` Akzentlicht, KEIN Text).

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | antimatter_collector | `buildings/antimatter_collector.png` | PNG transparent, 512×512 (wie `buildings/*`) | Antimaterie-Kollektor: ein **hitzefestes Kollektor-Bauwerk** auf einem glühend heißen, sonnennahen Planeten — strahlungsabschirmende Paneele/Kollektor-Schalen zur Sonne ausgerichtet, Magnet-Eindämmungstanks, im Kern ein instabil **magenta `#ff4d7d`** glühender Antimaterie-Speicher. Heiß/aggressiv. Gerendert wie ein Gebäude (3/4-Aufsicht), NICHT als Weltraumszene. |
| ✅ | dark_matter_condenser | `buildings/dark_matter_condenser.png` | PNG transparent, 512×512 (wie `buildings/*`) | Dunkle-Materie-Kondensator: ein **vereistes Kondensator-Bauwerk** auf einem eisig kalten, sternfernen Planeten — Kryo-Kühltürme/Kondensator-Spulen, Raureif auf den Strukturen, im Kern eine tief-violette, ruhig-mysteriöse Dunkle-Materie-Kugel mit leichter Gravitations-Verzerrung. Kühl/mysteriös. Gerendert wie ein Gebäude (3/4-Aufsicht). |

### Ressourcen-Icons (exotisch) — referenziert als `assets/img/resources/<name>.png`

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | dark_matter | `icons/resources/dark_matter.png` | PNG transparent, 256×256 | Dunkle Materie (zivil/Forschung): tief-violette, gewundene Void-/Energiekugel mit leichter Gravitations-Verzerrung ringsum; **kühl, ruhig-mysteriös**. Muss klar von Antimaterie unterscheidbar sein. Stil wie `resources/metal|crystal|deuterium`. |
| ✅ | antimatter | `icons/resources/antimatter.png` | PNG transparent, 256×256 | Antimaterie (militärisch/Energie): instabil glühender Energiekern in einem Magnet-Eindämmungsfeld (Ringe), **heiß, aggressiv magenta `#ff4d7d`**, „gefährlich/energetisch". Muss klar von Dunkler Materie unterscheidbar sein. |

---

## 🗒️ Notizen für Codex

- Optional/später (noch NICHT verdrahtet, daher keine aktive Anforderung): Regions-Hintergründe
  `backgrounds/region_core|region_mid|region_frontier` (atmosphärische Nebel je Galaxie-Region) —
  erst eintragen, wenn das Frontend sie per Region einbindet.
- **`ui`-Button-Icons (trash/advisor/broom):** Master nach `assets/icons/ui/<name>.png`, Spiegel nach
  `frontend/src/assets/img/ui/<name>.png` (der `img/ui/`-Ordner existiert im Frontend noch NICHT → bitte
  anlegen). Sind im Code bereits verdrahtet (`uiIcon()`), zeigen bis dahin den Emoji-Fallback. Sie sitzen
  als kleines führendes Icon IN Buttons (neben Text) → schlichte, klar lesbare Silhouette wichtig, kein Rahmen.
