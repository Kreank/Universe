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
| ✅ | prospecting | `tech/prospecting.png` | PNG transparent, 256×256 (Stil = `tech/spy_tech.png` / `tech/energy_tech.png`) | Ortung / Prospektion (wiederholbar): plastisches Sensor-/Ortungs-Emblem — eine Radar-/Scanner-Schale aussendend, konzentrische cyan Scan-Pulsringe über einem kleinen Asteroiden/Erz-Kristall (Erz-Aufspürung), Zielpeil-Akzent + dezenter **∞-Ring** (repeatable). Gleiches Rendering/Material/Glanz wie die Tech-Anker, cyan `#2fe3d2`, KEIN Text. |

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

### Nanitenfabrik — GEBÄUDE (Master `assets/buildings/`, Spiegel `frontend/src/assets/img/buildings/`)

> ⬜ **NEU ERSTELLEN (2026-06-14).** Reguläres High-Tech-Gebäude (Endgame-Anlage, baubar ab
> Roboterfabrik 12; senkt Bauzeit aller Gebäude/Schiffe). **EXAKT wie die vorhandenen `buildings/*.png`**
> — gleiche 3/4-Aufsicht, gleiches Rendering/Licht/Palette. **Stil-Anker (genau anschauen!):**
> `buildings/robot_factory.png`, `buildings/shipyard.png`. Format wie die anderen Gebäude
> (PNG RGBA, transparent, **512×512**, EIN plastisches Bauwerk mittig, cyan `#2fe3d2` Akzentlicht, KEIN Text).

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | nanite_factory | `buildings/nanite_factory.png` | PNG transparent, 512×512 (wie `buildings/*`) | Nanitenfabrik: eine **hochmoderne, sterile Hightech-Fertigungshalle als Bauwerk** — Reinraum-Module, Roboterarme/Montage-Gantries, schwebende Nanit-Schwärme als feine cyan Partikelwolken/Glitzern um die Anlage, leuchtende cyan `#2fe3d2` Daten-/Steuerleitungen. Wirkt wie eine aufgewertete, glänzendere Variante der `robot_factory`. Gerendert wie ein Gebäude (3/4-Aufsicht), NICHT als Weltraumszene. |

### Ressourcen-Icons (exotisch) — referenziert als `assets/img/resources/<name>.png`

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | dark_matter | `icons/resources/dark_matter.png` | PNG transparent, 256×256 | Dunkle Materie (zivil/Forschung): tief-violette, gewundene Void-/Energiekugel mit leichter Gravitations-Verzerrung ringsum; **kühl, ruhig-mysteriös**. Muss klar von Antimaterie unterscheidbar sein. Stil wie `resources/metal|crystal|deuterium`. |
| ✅ | antimatter | `icons/resources/antimatter.png` | PNG transparent, 256×256 | Antimaterie (militärisch/Energie): instabil glühender Energiekern in einem Magnet-Eindämmungsfeld (Ringe), **heiß, aggressiv magenta `#ff4d7d`**, „gefährlich/energetisch". Muss klar von Dunkler Materie unterscheidbar sein. |

---

## 🚀 Endgame-Capstone-Schiffe (4 Archetypen — je Spielstil) — referenziert als `assets/img/ships/<name>.png`

> Vier „ultimative" Schiffe, je eines pro Spielstil (Kämpfer/Pirat/Händler/Miner). Verdrahtung folgt.
> **Stil-Anker (genau anschauen!):** `ships/battleship.png`, `ships/deathstar.png` — detailliert
> gerendertes **3/4-Seiten-Capital**, dunkler Metall-Rumpf, **cyan `#2fe3d2` Triebwerks-/Akzent-Glow**,
> transparenter Hintergrund, 512×512 RGBA, KEIN Text. **Wuchtiger/imposanter als das Schlachtschiff**
> (Capstone-Tier). Jedes mit eigener, klar erkennbarer Silhouette gemäß Rolle. Militär-Schiffe dürfen
> einen **magenta `#ff4d7d`** (Antimaterie-)Akzent tragen, zivile einen **violetten** (Dunkle-Materie-)Akzent.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | flagship | `ships/flagship.png` | PNG transparent, 512×512 (Stil = `ships/battleship.png`) | **Flaggschiff** (ehrenvoller Kämpfer): majestätisches Kommando-Capital, markanter Kommandoturm/Brücke, würdevoll-imposant, Insignien-Anmutung, kräftiger cyan Aura-Glow (es verstärkt die Flotte). Leicht magenta Antimaterie-Akzent erlaubt. |
| ✅ | corsair | `ships/corsair.png` | PNG transparent, 512×512 (Stil = `ships/battleship.png`) | **Korsar** (Pirat): schlanker, räuberischer Raider — kantig, aggressive/schnelle Silhouette, dunkler Tarn-Rumpf, sichtbare Enterhaken/Greifarme, bedrohlich. Cyan Triebwerk + magenta `#ff4d7d` Piraten-Akzent. |
| ✅ | trade_leviathan | `ships/trade_leviathan.png` | PNG transparent, 512×512 (Stil = `ships/battleship.png`) | **Handels-Leviathan** (Händler): kolossaler, bulliger Frachter — massive Container-/Laderaum-Sektionen, gepanzert aber zivil, Eskort-/Schutz-Pods. Logistik-Gigant. Cyan + violetter (Dunkle-Materie-)Akzent. |
| ✅ | harvest_titan | `ships/harvest_titan.png` | PNG transparent, 512×512 (Stil = `ships/battleship.png`) | **Ernte-Titan** (Miner): gewaltiges Bergbau-/Erntschiff — Bohrer/Ernte-Arme, Erz-Einlauf-Trichter, Raffinerie-Module, industriell-wuchtig. Cyan + violetter (Dunkle-Materie-)Akzent. |

### ⚙️ Kampfschiff-Artwork (nachgezogen) — referenziert als `assets/img/ships/<name>.png`

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | warp_stabilizer | `ships/warp_stabilizer.png` | PNG transparent, 512×512 (Stil = `ships/interdictor.png`) | **Warp-Stabilisator** (Konter zum Interdiktor): mittelgroßes Kampfschiff mit Stabilisator-Feld-Emittern/Gyroskop-Ringen (Gegenstück zu den Interdiktor-Feldpods), cyan `#2fe3d2` statt lila. Dunkler Metall-Rumpf, eigene Silhouette. |
| ✅ | tanker | `ships/tanker.png` | PNG transparent, 512×512 (Stil = `ships/large_cargo.png`) | **Tankschiff** (Support/Logistik): bulliges Versorgungs-/Betankungsschiff mit prominenten zylindrischen Treibstofftanks und Betankungs-Auslegern/-Düsen + Rohrleitungen; klar als Tanker lesbar (NICHT Container-Frachter), kaum Bewaffnung. Dunkler Metall-Rumpf, cyan `#2fe3d2` Triebwerks-/Akzent-Glow + dezenter violetter (ziviler) Akzent. Eigene erkennbare Silhouette. |

### Kommando-Forschungen der Capstone-Schiffe (je +1 Besitz-Limit) — referenziert als `assets/img/tech/<name>.png`

> Vier neue Forschungen, je eine pro Capstone-Schiff: default darf man 1 besitzen, jede Stufe gibt +1.
> **Stil-Anker:** wie die übrigen `tech/*.png` (plastisches Tech-Emblem, cyan `#2fe3d2`, transparent,
> 256×256, kein Text). Idealerweise **bildlich auf das jeweilige Schiff bezogen** (kleine Schiffs-
> Silhouette + Kommando-/Rang-Element), damit die Zugehörigkeit klar ist.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | flagship_command | `tech/flagship_command.png` | PNG transparent, 256×256 | Flaggschiff-Doktrin (+1 Flaggschiff): Kommandostab/Admirals-Insignie mit Capital-Silhouette, cyan. |
| ✅ | corsair_command | `tech/corsair_command.png` | PNG transparent, 256×256 | Korsaren-Verband (+1 Korsar): Piraten-/Raider-Emblem (Enterhaken + schlanke Schiffs-Silhouette), cyan + dezent magenta. |
| ✅ | leviathan_command | `tech/leviathan_command.png` | PNG transparent, 256×256 | Großhandels-Lizenz (+1 Handels-Leviathan): Fracht-/Konvoi-Emblem mit massiver Frachter-Silhouette, cyan + dezent violett. |
| ✅ | harvest_command | `tech/harvest_command.png` | PNG transparent, 256×256 | Schürf-Kommando (+1 Ernte-Titan): Bergbau-/Bohr-Emblem mit Ernteschiff-Silhouette, cyan + dezent violett. |

---

## 🤝 Allianzen (NEU 2026-06-14 — Feature in Planung, Verdrahtung folgt)

> Assets für das kommende **Allianz-System**: eine kollektive Allianz-Forschung mit **4 Rollen-Bäumen**
> (Piraterie / Wirtschaft / Handel / Schutz) und eine **Allianz-Station** mit Einflusszone (±1 System,
> über Forschung auf ±5 erweiterbar). Design-Stand siehe Memory/Plan. **Erst die hier bereits
> ENTSCHIEDENEN Assets bauen** (4 Baum-Embleme, Station, Nav-Icon, Zonen-Marker); die **Einzel-Knoten-Icons**
> der Bäume kommen, sobald die Knotenliste final ist (siehe letzte Zeile dieser Sektion — noch NICHT bauen).

### Allianz-Forschungsbaum-Embleme — referenziert als `assets/img/tech/<name>.png`

> Die 4 obersten **Baum-/Branch-Embleme** (Kategorie-Köpfe der Allianz-Forschung). **Stil-Anker (genau
> anschauen!):** `tech/weapons_tech.png`, `tech/energy_tech.png` — EIN klares, plastisch gerendertes
> Tech-Emblem, cyan `#2fe3d2`, transparent, 256×256, KEIN Text. Jedes Emblem soll die Rolle sofort lesbar
> machen; je ein dezenter rollentypischer Zweitakzent erlaubt.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | alliance_piracy | `tech/alliance_piracy.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Baum **Piraterie**: räuberisches Emblem — Enterhaken/Krallen + schlanke Raider-Silhouette oder Totenkopf-Anmutung dezent, aggressiv. Cyan + dezent **magenta `#ff4d7d`** Piraten-Akzent. |
| ✅ | alliance_economy | `tech/alliance_economy.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Baum **Wirtschaft/Förderung**: industrielles Förder-Emblem — Bohr-/Förderkopf + Zahnrad/Erzstrom, solide/produktiv. Cyan, dezent goldener Industrie-Akzent. |
| ✅ | alliance_trade | `tech/alliance_trade.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Baum **Handel**: Merkantil-Emblem — Frachtcontainer + Handelsrouten-Pfeile/Waage, wohlhabend-logistisch. Cyan, dezent warm-goldener Akzent. |
| ✅ | alliance_protection | `tech/alliance_protection.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Baum **Schutz/Ordnungsmacht**: Wächter-Emblem — Schild + Geleitschutz-/Stern-Insignie (Polizei/Eskorte), wehrhaft-ehrenhaft. Cyan, klar/blau. |

### Allianz-Station — NEUER Ordner `alliance/` (Master `assets/alliance/`, Spiegel `frontend/src/assets/img/alliance/`)

> Die **Allianz-Station** ist eine **orbitale Weltraum-Struktur** (sitzt als Besatzer in einem System,
> NICHT auf einem Planeten) — projiziert die Einflusszone. **Stil-Anker (genau anschauen!):**
> `ships/deathstar.png` (Stations-Anmutung im Raum) + `megastructures/research_nexus.png` (monumentale
> Bauwerks-Plastik). Also: eine **imposante, frei im Raum schwebende Stationsstruktur** — Ring-/Kern-Bau,
> Andock-Arme, Antennen-/Sensor-Türme, bewohnt/beleuchtet. PNG RGBA transparent, 512×512, EINE Station
> mittig, cyan `#2fe3d2` Akzentlicht, KEIN Text, KEINE Planetenoberfläche/Weltraumszene drumherum.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | alliance_station | `alliance/alliance_station.png` | PNG transparent, 512×512 | **Allianz-Station**: monumentale orbitale Kommando-/Versorgungs-Station, frei im Raum schwebend — zentraler Kern mit umlaufendem Ring/Andock-Armen, Sensor-/Kommunikationstürme, viele beleuchtete Fenster (bewohnt), cyan `#2fe3d2` Energiekern/Akzentglow. Wirkt wie das **Herz eines Territoriums** — wuchtig, dauerhaft, wehrhaft. Gerendert als freistehende Station (wie `deathstar`, aber Ring-/Bau-Station statt Kugel). |

### Allianz-UI-Icons — referenziert als `assets/img/nav/<name>.png` bzw. `assets/img/status/<name>.png`

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | alliance (nav) | `icons/nav/alliance.png` | PNG transparent, 256×256 (~24px lesbar) | Nav-Icon „Allianz"-Screen: schlichte Wappen-/Bündnis-Silhouette (zwei verschränkte Hände / geteiltes Wappenschild / Sternen-Bund), cyan Akzent. Stil wie vorhandene `nav/*.png`, als kleine klare Silhouette lesbar. |
| ✅ | alliance_zone | `icons/status/alliance_zone.png` | PNG transparent, 256×256 | Karten-Marker „Einflusszone" (liegt auf Systemen im Stations-Radius der Galaxie-/System-Karte): weicher, **tintbarer** cyan Aura-/Ring-Glow (heller Rand, transparente Mitte), neutral genug zum Einfärben pro Allianz. Dezent, soll Inhalt nicht überdecken. |

### Allianz-Forschungs-Knoten-Icons (Knotenliste FINAL, 2026-06-15) — referenziert als `assets/img/tech/<name>.png`

> Je Knoten ein eigenes `tech/alliance_<knoten>.png` (Stil = `tech/*`, plastisches Emblem, cyan Akzent,
> Baum-Akzentfarbe wie das jeweilige Baum-Emblem). **🔁 = wiederholbar → dezenter ∞-Ring** (wie
> `tech/*_mastery.png`). **⭐ = Koop-Schlüsselknoten** → etwas prominenter / Gruppen-Anmutung.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | alliance_raid_loot | `tech/alliance_raid_loot.png` | PNG 256×256 | 🏴‍☠️🔁 Beutezug: Plünderungs-/Beute-Emblem (Schatztruhe/Krallen am Frachtgut) + **∞-Ring**. |
| ✅ | alliance_shadow_fleet | `tech/alliance_shadow_fleet.png` | PNG 256×256 | 🏴‍☠️🔁 Schattenflotte: getarnte Raider-Silhouette, halb im Dunkel/Phasen-Effekt + **∞-Ring**. |
| ✅ | alliance_boarding_doctrine_ally | `tech/alliance_boarding_doctrine_ally.png` | PNG 256×256 | 🏴‍☠️ Enterhaken (Koop): Enterhaken/Greifarm an gekapertem Schiff. |
| ✅ | alliance_gravity_snare | `tech/alliance_gravity_snare.png` | PNG 256×256 | 🏴‍☠️ Fanggriff: Gravitations-/Interdiktionsfeld, das ein Schiff festhält (Räuberhöhle). |
| ✅ | alliance_pack_hunt | `tech/alliance_pack_hunt.png` | PNG 256×256 | 🏴‍☠️⭐ Rudeljagd: mehrere Raider im Verband auf ein Ziel, geteilte Sicht (Gruppen-Anmutung). |
| ✅ | alliance_extraction_zone | `tech/alliance_extraction_zone.png` | PNG 256×256 | 🏭🔁 Förderquote: Förderkopf/Erzstrom über einem Zonen-Ring + **∞-Ring**. |
| ✅ | alliance_deep_drilling | `tech/alliance_deep_drilling.png` | PNG 256×256 | 🏭🔁 Tiefenbohrung: tiefer Bohrer in Asteroid/Trümmer + **∞-Ring**. |
| ✅ | alliance_forward_yards | `tech/alliance_forward_yards.png` | PNG 256×256 | 🏭🔁 Vorgeschobene Werften: kompaktes Werft-/Baugerüst mit Tempo-Anmutung + **∞-Ring**. |
| ✅ | alliance_depot_storage | `tech/alliance_depot_storage.png` | PNG 256×256 | 🏭 Lagernetz: Depot-/Lagercontainer-Cluster, solide. |
| ✅ | alliance_joint_extraction | `tech/alliance_joint_extraction.png` | PNG 256×256 | 🏭⭐ Gemeinschaftsförderung: mehrere Förderschiffe an einem Feld (Gruppen-Anmutung). |
| ✅ | alliance_market_access | `tech/alliance_market_access.png` | PNG 256×256 | 💱🔁 Marktzugang: Handels-/Kurs-Emblem (Waage/Kurvenpfeil) + **∞-Ring**. |
| ✅ | alliance_cargo_logistics | `tech/alliance_cargo_logistics.png` | PNG 256×256 | 💱🔁 Frachtoptimierung: prall gefüllter Frachter/Container mit Effizienz-Pfeil + **∞-Ring**. |
| ✅ | alliance_safe_routes | `tech/alliance_safe_routes.png` | PNG 256×256 | 💱 Sichere Routen: Handelsroute mit Schutzschirm/Konvoi-Linie. |
| ✅ | alliance_depot_logistics | `tech/alliance_depot_logistics.png` | PNG 256×256 | 💱 Depot-Logistik: Einzahlung/Pfeil-in-Depot, günstig/effizient. |
| ✅ | alliance_escort_convoy | `tech/alliance_escort_convoy.png` | PNG 256×256 | 💱⭐ Geleitzug: eskortierter Konvoi (Frachter + Begleitschiffe). |
| ✅ | alliance_escort_doctrine | `tech/alliance_escort_doctrine.png` | PNG 256×256 | 🛡️ Geleitschutz: Schild über Frachter/Verbündetem. |
| ✅ | alliance_rapid_response | `tech/alliance_rapid_response.png` | PNG 256×256 | 🛡️🔁 Schnelle Eingreiftruppe: Abfangjäger mit Tempo-/Alarm-Anmutung + **∞-Ring**. |
| ✅ | alliance_early_warning | `tech/alliance_early_warning.png` | PNG 256×256 | 🛡️🔁 Frühwarnnetz: Sensor-/Radar-Sweep über der Zone + **∞-Ring**. |
| ✅ | alliance_bounty | `tech/alliance_bounty.png` | PNG 256×256 | 🛡️ Kopfgeld: Fahndungs-/Kopfgeld-Marke gegen Pirat. |
| ✅ | alliance_shield_wall | `tech/alliance_shield_wall.png` | PNG 256×256 | 🛡️⭐ Schildwall: gestapelte Schilde mehrerer Schiffe (Gruppen-Verteidigung). |

---

## 🛰️ Farm-Routinen (automatisiertes Farmen von Asteroiden-/Trümmerfeldern)

> Feature **Routinen**: Spieler legen dauerhafte Sammelschleifen (Flotte fliegt Feld für Feld ab,
> lädt an der Heim-Station aus, wiederholt endlos). Eigener Screen + zwei wiederholbare Forschungen.

### Screen-Hintergrund — referenziert als `assets/img/backgrounds/bg_routines.jpg`

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | bg_routines | `backgrounds/` | JPG, 1920×1080, dunkel | Screen-Hintergrund **Routinen**: Bergbau-/Sammel-Szene im All — Förder-/Bergbauschiffe + Transporter an einem Asteroidengürtel/Trümmerfeld, dünne Förderstrahlen, ferne Frachtcontainer. Ruhige, dunkle Mitte (dort liegt die Routinen-Liste), Interesse an Rändern/oben. **Stil-/Kompositions-Brief siehe oben bei den bg_***. |

### Navigations-Icon — referenziert als `assets/img/nav/routines.png`

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | routines (nav) | `icons/nav/routines.png` | PNG transparent, 256×256 (~24px lesbar) | Nav-Icon „Routinen"-Screen: schlichte Silhouette einer **zyklischen Sammelroute** — kleiner Frachter/Bergbauschiff auf einer geschlossenen Umlauf-/Schleifenbahn zwischen zwei Punkten (Pfeil-Kreislauf), cyan Akzent. Stil wie vorhandene `nav/*.png`, als kleine klare Silhouette lesbar. |

### Forschungs-Icons — referenziert als `assets/img/tech/<name>.png` (beide **wiederholbar → ∞-Ring** wie `tech/*_mastery.png`)

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | fleet_logistics | `tech/fleet_logistics.png` | PNG transparent, 256×256 (Stil = `tech/*`) | **Logistik-Netz** (wiederholbar, +1 gleichzeitige Routine je Stufe): plastisches Tech-Emblem — ein zentraler Stations-/Hub-Knoten mit mehreren auslaufenden Versorgungs-/Frachtrouten (verzweigtes Logistik-Netz), cyan Datenlinien + dezenter **∞-Ring** (repeatable-Merkmal). |
| ✅ | route_planning | `tech/route_planning.png` | PNG transparent, 256×256 (Stil = `tech/*`) | **Routen-Planung** (wiederholbar, +1 Feld je Route je Stufe): plastisches Tech-Emblem — eine geplante Mehr-Stopp-Route (Wegpunkt-Kette mit nummerierten Knoten/Pins über einer Sternenkarte), cyan Pfad + dezenter **∞-Ring** (repeatable-Merkmal). |

---

## 🧩 UI-/Status-Icons — Ablösung hartkodierter Emoji-Fallbacks (2026-06-15)

> **Kontext:** Audit des gesamten Frontends auf hartkodierte Emoji-„Fallback-Icons" in Templates.
> Wo ein passendes Asset existierte, ist das Emoji bereits gegen das echte Asset getauscht (via
> `app-btn-icon`/`app-icon-tile`, Emoji bleibt nur als Notfall-Glyph). Die folgenden **fehlten** —
> bis sie geliefert sind, zeigen die Stellen weiterhin den Emoji-Fallback.
>
> **Stil-Anker (genau anschauen!):** vorhandene `icons/ui/*.png` (`broom`/`trash`/`advisor`), `icons/nav/*.png`,
> `icons/status/*.png`, `icons/spec/stat_*.png`. Also: **schlichte, sofort lesbare Silhouette**, cyan
> `#2fe3d2` Akzent, PNG transparent, KEIN Rahmen/Text (das Frontend rahmt selbst). Sitzen als **kleines
> führendes Icon (~16–18px) in Buttons / Panel-Titeln / Chips** → bei ~16px klar erkennbar bleiben.
> `ui/`-Ordner-Spiegel: Master `assets/icons/ui/<name>.png` → `frontend/src/assets/img/ui/<name>.png`.

### Generische UI-Icons — referenziert als `assets/img/ui/<name>.png` (`uiIcon()`-Helfer)

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | time | `icons/ui/time.png` | PNG transparent, 256×256 | **Zeit/Dauer** (löst ⏱/⏳ ab — Bauzeit, Forschungszeit, Flugzeit, Cooldown; sehr häufig). Schlichte Uhr/Sanduhr-Silhouette, cyan Zeiger/Glow. Neutral genug für „läuft" UND „Restzeit". |
| ✅ | home | `icons/ui/home.png` | PNG transparent, 256×256 | **Heimat/Heimatplanet** (löst 🏠/⌂ ab — „Heimat"-Button Galaxie, „gratis"-Heimatgebiet im Handel). Stilisierter Heimat-Planet mit Markierungs-Pin/Haus-Glyph, cyan Akzent. |
| ✅ | target | `icons/ui/target.png` | PNG transparent, 256×256 | **Ziel/erfasst** (löst 🎯 ab — „Aufgeklärte Ziele", Anfälligkeit/Verwundbarkeit). Fadenkreuz/Zielscheibe, cyan Ringe. |
| ✅ | loot | `icons/ui/loot.png` | PNG transparent, 256×256 | **Beute** (löst 💰 ab — Kampfbericht „Beute", Intel „Ressourcen"). Stapel/Truhe aus Erz-/Kristall-Splittern (kein irdisches Gold), cyan Glanz. Passt zur Ressourcen-Ästhetik (`resources/*`). |
| ✅ | distance | `icons/ui/distance.png` | PNG transparent, 256×256 | **Distanz** (löst 📏 ab — Flotten-Versand Distanz-Anzeige). Mess-Linie/Lineal zwischen zwei Punkten über Sternenraster, cyan. Klar von `range/*` (Reichweiten-Klasse) unterscheidbar. |
| ✅ | requirements | `icons/ui/requirements.png` | PNG transparent, 256×256 | **Voraussetzungen** (löst 🔗 ab — Detail-Popup „Voraussetzungen"). Verkettete Knoten/Glieder (Abhängigkeitskette), cyan. |
| ✅ | unlock | `icons/ui/unlock.png` | PNG transparent, 256×256 | **Schaltet frei** (löst 🔓 ab — Detail-Popup „Schaltet frei"). Offenes Schloss mit cyan Aufleucht-Strahl. Paarig zu `lock`. |
| ✅ | lock | `icons/ui/lock.png` | PNG transparent, 256×256 | **Verschlossen/geheim** (löst 🔒 ab — Intel unzureichend aufgeklärt). Geschlossenes Schloss, gedämpft cyan. Paarig zu `unlock`. |
| ✅ | levels | `icons/ui/levels.png` | PNG transparent, 256×256 | **Nächste Stufen/Steigerung** (löst 📈 ab — Detail-Popup „Nächste Stufen"). Aufsteigende Balken-/Stufen-Treppe mit cyan Pfeil. |
| ✅ | ability | `icons/ui/ability.png` | PNG transparent, 256×256 | **Aktive Fähigkeit** (löst ⚡ in „Fähigkeiten"-Kontext ab — Commander-Abilities, Versand „Fähigkeiten scharf"). Energie-/Funken-Sigille (klar verschieden vom Energie-Ressourcen-Blitz `resources/energy`), cyan. |
| ✅ | morale | `icons/ui/morale.png` | PNG transparent, 256×256 | **Crew-Moral** (löst 🎖️ in „Crew-Moral" ab — Dashboard). Stimmungs-/Herz-puls- oder Banner-Symbol einer Crew, cyan. Unterscheidbar vom Kommando-Nav-Icon. |
| ✅ | governor | `icons/ui/governor.png` | PNG transparent, 256×256 | **Gouverneur** (löst 🏛️ ab — Commander-Detail „Gouverneur": Kommandeur verwaltet einen Planeten). Verwaltungs-/Amts-Silhouette (Säulenbau + Stern/Rang), cyan. |
| ✅ | genetics | `icons/ui/genetics.png` | PNG transparent, 256×256 | **Charakter-Zucht** (löst 🧬 ab — Commander-Detail „Charakter-Zucht": Trait-Vererbung). DNA-/Doppelhelix-Strang, cyan. |
| ✅ | player | `icons/ui/player.png` | PNG transparent, 256×256 | **Spieler/Pilot** (löst 🧑‍🚀 ab — Handelspartner-Name). Helm-/Pilot-Silhouette (neutral), cyan Visier-Glanz. |
| ✅ | rapidfire | `icons/ui/rapidfire.png` | PNG transparent, 256×256 | **Schnellfeuer** (löst 💥 im Detail-Popup „Schnellfeuer gegen" ab). Mehrfach-Mündungsfeuer-Salve/Burst, cyan-heiße Spitzen. |

### Status-Icons (Kampf) — referenziert als `assets/img/status/<name>.png` (`statusIcon()`-Helfer)

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | losses | `icons/status/losses.png` | PNG transparent, 256×256 | **Verluste** (löst 💥 im Kampfbericht „Verluste" ab). Zerbrochener Schiffsrumpf/Wrackteil mit Funken, gedämpft-warnend. Stil wie übrige `status/*`. |
| ✅ | ambush | `icons/status/ambush.png` | PNG transparent, 256×256 | **Hinterhalt** (löst 🥷 im Kampfbericht-Runde ab). Verdeckte/getarnte Schiff-Silhouette aus dem Schatten auftauchend (Stealth-Motiv), cyan Kante. Passt zu `ships/stealth_corvette`. |
| ✅ | fled | `icons/status/fled.png` | PNG transparent, 256×256 | **Geflohen** (löst 🏃 im Kampfbericht „Geflohen" ab). Abdrehendes Schiff mit Fluchtspur/Triebwerks-Streak, cyan. Klar von `stranded` (Antrieb tot) unterscheidbar. |

### Stat-Icon — referenziert als `assets/img/icons/spec/stat_<key>.png` (`statIcon()`-Helfer)

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | stat_hull | `icons/spec/stat_hull.png` | PNG transparent, 256×256 (Stil = `icons/spec/stat_*`) | **Hülle/HP** (löst ❤ ab — Allianz-Stations-Hülle, Schiffs-HP im Detail-Popup). Gepanzerte Rumpf-/Hüllen-Platte mit Niet/Integritäts-Glyph, cyan. Reiht sich in `stat_attack/stat_shield/stat_cargo/stat_speed/stat_fuel/stat_energy` ein. |

### Welle 2 — TS-Glyph-Layer (2026-06-15): daten-getriebene Icons (Kampfbericht/Funk/Fähigkeiten)

> Zweite Audit-Welle: Emojis aus TS-Datenstrukturen (`resultIcon`, `typeGlyph`, `catGlyph`, Tab-Defs),
> die als Tabs/Chips/Labels rendern. Wo ein Asset existierte, ist es bereits verdrahtet (inkl. Reuse:
> Allianz-Bäume `tech/alliance_*`, Reichweite `range/*`, Stat-Glyphs `icons/spec/stat_*`, Werft-Kategorien
> via `missions/*`+`ui/target`, Funk-Typen via `missions/*`+`status/*`, Gebäude/Schiff/Tech-Queues via
> `buildings|ships|defenses|tech/*`). Die folgenden fehlten noch. Stil-Anker wie oben.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | victory | `icons/status/victory.png` | PNG transparent, 256×256 | **Sieg** (löst 🏆 ab — Kampfbericht-Ergebnis, „Großmoment"-Funk). Sieges-Sigille (Lorbeer/Stern-Triumph, KEIN irdischer Pokal), cyan-leuchtend, positiv. |
| ✅ | defeat | `icons/status/defeat.png` | PNG transparent, 256×256 | **Niederlage** (löst ☠️ ab — Kampfbericht-Ergebnis). Zerstörtes-Schiff-/Totenkopf-Sigille, gedämpft-warnend (dunkel + magenta Rand). Paarig zu `victory`. |
| ✅ | draw | `icons/status/draw.png` | PNG transparent, 256×256 | **Unentschieden** (löst 🤝 ab — Kampfbericht-Ergebnis). Patt-/Gleichgewicht-Sigille (gekreuzte Klingen im Gleichstand / Waage), neutral cyan. |
| ✅ | broadcast | `icons/status/broadcast.png` | PNG transparent, 256×256 | **Funkspruch/Reaktion** (löst 🎙️ ab — Funk-Nachrichtentyp). Sende-/Funk-Welle (Antennen-/Mikrofon-Puls), cyan. Unterscheidbar von `transmission_unread` (Postfach). |
| ✅ | trait_category_combat | `icons/traits/trait_category_combat.png` | PNG transparent, 256×256 (Stil = `icons/traits/trait_category_*`) | **Fähigkeits-Kategorie Kampf** (löst ⚔ ab). Reiht sich in vorhandene `trait_category_admin/general` ein — gekreuzte Klingen, cyan. |
| ✅ | trait_category_logistics | `icons/traits/trait_category_logistics.png` | PNG transparent, 256×256 (Stil wie oben) | **Fähigkeits-Kategorie Logistik** (löst 📦 ab). Fracht-/Versorgungs-Symbol, cyan. |
| ✅ | trait_category_spy | `icons/traits/trait_category_spy.png` | PNG transparent, 256×256 (Stil wie oben) | **Fähigkeits-Kategorie Spionage** (löst 🛰️ ab). Aufklärungs-/Sonden-Symbol, cyan. |
| ✅ | trait_category_research | `icons/traits/trait_category_research.png` | PNG transparent, 256×256 (Stil wie oben) | **Fähigkeits-Kategorie Forschung** (löst 🔬 ab). Wissenschafts-/Datensymbol, cyan. |
| ✅ | npc | `icons/ui/npc.png` | PNG transparent, 256×256 | **NPC-Imperium** (löst 🤖 ab — Funk-Absender-/Belegungs-Kennung „NPC" vs. Spieler). Fremd-/KI-Fraktions-Silhouette (kantiger Droiden-/Alien-Kopf), cyan. Paarig zum vorhandenen `ui/player.png`. |
| ✅ | pool | `icons/ui/pool.png` | PNG transparent, 256×256 | **Allianz-Pool** (löst 🏦 ab — Allianz-Tab „Pool", gemeinsamer Ressourcenspeicher). Tresor-/Sammelspeicher mit Erz-/Kristall-Andeutung (kein irdisches Bankgebäude), cyan. |

### Flottenbewegung — Schiff statt Missions-Name (Dashboard + Flotten-Screen)

> **Kontext (Nutzer-Wunsch 2026-06-15):** In der Liste der Flottenbewegungen (Dashboard
> „Flottenbewegungen" UND Flotten-Screen „Laufende Flotten") soll **statt des Missions-Namens**
> (Bergbau/Transport/Angriff …) **ein Schiff** angezeigt werden. **Verbessert (Nutzer):** lieber
> **je Mission das passende Schiff** statt eines einzigen generischen.
>
> **➜ Für den verdrahtenden Agenten — REUSE-FIRST (keine neuen Assets nötig):** Für fast jede
> Mission existiert bereits ein passendes Schiff-Asset unter `ships/*`. Verdrahte je Bewegungs-Zeile
> ein führendes Icon (~16–20px) über eine Mission→Schiff-Abbildung, z. B. `shipIcon(MISSION_SHIP[mission])`
> (Glyph-Fallback = bisheriges Missions-Glyph). Tabelle unten. **Nur `deploy` (Stationierung)** hat
> kein eigenes Schiff → dort das generische `ui/fleet_underway.png` (bereits vorhanden) ODER `ships/cruiser.png`.

| Mission | Asset (vorhanden, reuse) | Schiff |
|---|---|---|
| `attack`     | `ships/battlecruiser.png` | Schlachtkreuzer (Kriegsschiff) |
| `transport`  | `ships/large_cargo.png`   | Großer Transporter |
| `spy`        | `ships/spy_probe.png`     | Spionagesonde |
| `recycle`    | `ships/recycler.png`      | Recycler |
| `colonize`   | `ships/colony_ship.png`   | Kolonieschiff |
| `mine`       | `ships/miner.png`         | Bergbauschiff |
| `expedition` | `ships/expedition_ship.png` | Expeditionsschiff |
| `trade`      | `ships/large_cargo.png`   | Handelsfrachter (alt.: `ships/trade_leviathan.png`) |
| `intercept`  | `ships/interceptor.png`   | Abfangjäger |
| `escort`     | `ships/escort_frigate.png` | Eskort-Fregatte |
| `deploy`     | `ui/fleet_underway.png` *(generisch)* | — (kein eigenes Schiff; Fallback) |

> **Optional (NEU erstellen — nur falls ein einheitlicher kleiner „im Flug"-Look gewünscht ist
> statt der detaillierten 512er-Renders):** dedizierte Mini-Flug-Icons `icons/ui/fleet_<mission>.png`
> (gleiche 11 Missionen), je eine **kompakte 3/4-Schiffs-Silhouette im Flug mit kurzer Triebwerksspur**,
> cyan `#2fe3d2`, ~16–20px lesbar (Stil-Anker: `nav/fleet.png` + das jeweilige `ships/*` oben als
> Form-Referenz). Nicht zwingend — die Reuse-Variante oben sieht je Mission bereits ein echtes Schiff.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | fleet_underway | `icons/ui/fleet_underway.png` | PNG transparent, 256×256 (~16–20px lesbar) | **Flotte unterwegs (generisch)** — Fallback für `deploy` und unbekannte Missionen. Kompakte 3/4-Schiffs-Silhouette im Flug mit kurzer Triebwerksspur, cyan `#2fe3d2`. Stil zwischen `nav/fleet.png` und `ships/*`. |

---

## 🛡️ Werft/Verteidigung-Trennung (2026-06-17 — Feature in Umsetzung)

> **Umbau:** Verteidigungsanlagen werden aus der **Werft** herausgelöst und in ein **eigenes Gebäude**
> verlagert (Realismus: eine Schiffswerft baut keine Bodengeschütze). Neues Gebäude
> **„Verteidigungsfabrik"** (Key `defense_factory`) in der Gebäude-Übersicht; ein eigener Screen
> **„Verteidigung"** (Nav-Slug `defense`), auf dem die Verteidigungs-Einheiten gebaut werden (analog
> zur Werft für Schiffe, schaltet erst ab Fabrik-Stufe ≥ 1 frei). Drei Assets: Gebäude-Artwork +
> Nav-Icon + Screen-Hintergrund.

### Gebäude-Artwork — GEBÄUDE (Master `assets/buildings/`, Spiegel `frontend/src/assets/img/buildings/`)

> **Verteidigungsfabrik** (Key `defense_factory`) — die Produktionsanlage für planetare Verteidigung.
> **Muss EXAKT wie die vorhandenen `buildings/*.png` aussehen** — gleiche 3/4-Aufsicht, gleiches
> Rendering/Licht/Palette, als Bauwerk auf der Oberfläche (KEINE Weltraumszene). **Stil-Anker (genau
> anschauen!):** `buildings/robot_factory.png`, `buildings/shipyard.png`, `buildings/orbital_battery.png`,
> `buildings/command_center.png`. Format wie die anderen Gebäude (PNG RGBA, 512×512).

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | defense_factory | `buildings/defense_factory.png` | PNG transparent, 512×512 (wie `buildings/*`) | Verteidigungsfabrik: eine **schwer gepanzerte militärische Rüstungs-/Waffenfabrik als Bauwerk** — bunkerartige Produktionshalle mit gepanzerten Wänden, montierten Geschütztürmen/Raketenrampen auf dem Dach, Munitions-/Bauteil-Gantries, Werkshof mit halbfertigen Geschützen. Martialisch-industriell, dezente Warn-Streifen, kühle Stahl-Palette mit cyan `#2fe3d2` Akzent-Leuchten. Gerendert wie ein Gebäude (3/4-Aufsicht), Mischung aus `robot_factory` (Fertigung) und `orbital_battery` (Geschütz-Anmutung), NICHT als Weltraumszene. |

### Navigations-Icon — referenziert als `assets/img/nav/defense.png`

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | defense (nav) | `icons/nav/defense.png` | PNG transparent, 256×256 (~24px lesbar) | Nav-Icon „Verteidigung"-Screen: schlichte Silhouette eines **planetaren Verteidigungs-Geschützes / einer Schild-Kuppel über Boden** (Flak-/Laserturm mit nach oben gerichtetem Lauf, optional dünner Schildbogen darüber), cyan Akzent. Klar von der Werft (`nav/shipyard.png`, Schiffsbau) und der Schild-Stat (`icons/spec/stat_shield.png`) unterscheidbar — Fokus: **Boden-Verteidigungsturm**. Stil wie vorhandene `nav/*.png`, als kleine klare Silhouette lesbar. |

### Screen-Hintergrund — referenziert als `assets/img/backgrounds/bg_defense.jpg`

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | bg_defense | `backgrounds/` | JPG, 1920×1080, dunkel | Screen-Hintergrund **Verteidigung**: planetare Verteidigungsstellung bei Nacht — eine Reihe Boden-Geschütztürme/Raketenrampen + eine schimmernde Energie-Schildkuppel über der Basis, ferner Orbit/Sternenfeld am Horizont, sparsame defensiv-cyan Glut (kein aktiver Kampf, ruhige Bereitschaft). Ruhige, dunkle Mitte (dort liegt die Bauliste), Interesse an Rändern/oben. **Stil-/Kompositions-Brief siehe oben bei den bg_***. |

---

## 🎖️ Kommandeurs-Equipment (2026-06-17 — Feature in Umsetzung)

> **Neu:** Kommandeure können mit **Ausrüstung** in 4 Slots (Kopf/Hände/Brust/Schuhe) bestückt werden;
> Ausrüstung gibt **Schiffsklassen-Boni** (Angriff/Schild/Tempo auf `fighter`/`cruiser`/`capital`/`civil`)
> und bildet **4er-Sets** (Set-Bonus bei 2/4 Teilen). Items kommen aus Quests/Expeditionen/globalen
> Events/Akademie-Fertigung. Code referenziert die Pfade bereits → bis zur Lieferung Emoji/CSS-Fallback.
>
> **NEUER Ordner `equipment/`** — Master `assets/icons/equipment/`, Frontend-Spiegel
> `frontend/src/assets/img/equipment/` (Achtung: im Spiegel OHNE `icons/`-Segment, referenziert als
> `assets/img/equipment/<name>.png`). **Gemeinsamer Stil-Brief (alle Equipment-Assets):** Sci-Fi-UI,
> PNG transparent, **256×256**, EIN klar lesbares Objekt/Symbol mittig, cyan `#2fe3d2` Akzentlicht,
> dunkel-metallische Anmutung passend zum bestehenden UI (`#080d18`), KEIN Text, KEIN Rahmen (außer
> Slot-Platzhalter/Set-Emblem wie unten), auch ~24–32px klein klar erkennbar. Raritäts-Färbung macht
> später CSS — die Icons selbst neutral halten.

### Slot-Platzhalter (leerer Slot) — referenziert als `assets/img/equipment/slot_<name>.png`

> Schlichtes, gedämpftes Linien-Icon, das einen **leeren** Ausrüstungs-Slot markiert (wird hinter dem
> Item halbtransparent angezeigt). Klar als Körperzone lesbar, dezent (nicht ablenkend), monochrom-cyan.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | slot_head | `icons/equipment/slot_head.png` | PNG transparent, 256×256 | Leerer **Kopf**-Slot: schlichte Helm-/Kopf-Silhouette als Umriss, gedämpft cyan, dezent. |
| ✅ | slot_hands | `icons/equipment/slot_hands.png` | PNG transparent, 256×256 | Leerer **Hände**-Slot: Handschuh-/Hand-Umriss, gedämpft cyan, dezent. |
| ✅ | slot_chest | `icons/equipment/slot_chest.png` | PNG transparent, 256×256 | Leerer **Brust**-Slot: Brustpanzer-/Westen-Umriss, gedämpft cyan, dezent. |
| ✅ | slot_shoes | `icons/equipment/slot_shoes.png` | PNG transparent, 256×256 | Leerer **Schuhe**-Slot: Stiefel-/Fuß-Umriss, gedämpft cyan, dezent. |

### Item-Icons (16) — 4 Sets × 4 Slots — referenziert als `assets/img/equipment/<key>.png`

> Je ein **plastisch gerendertes Ausrüstungsstück** (kein flaches Clipart). Pro Set eine erkennbare
> gemeinsame Designsprache/Farbakzent, damit Set-Zugehörigkeit auf einen Blick sichtbar ist. Jeweils
> Kopf/Hände/Brust/Schuhe einer Sci-Fi-Kommandeurs-Montur. Stil-Konsistenz untereinander wichtig.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | fighter_helm | `icons/equipment/fighter_helm.png` | PNG transparent, 256×256 | Set **Jäger-Schwarm** (Schiffsklasse `fighter`, agil/offensiv, scharfe Kanten, cyan): **Kopf** — leichter aerodynamischer Pilotenhelm mit Visier. |
| ✅ | fighter_gloves | `icons/equipment/fighter_gloves.png` | PNG transparent, 256×256 | Set **Jäger-Schwarm**: **Hände** — schlanke Pilotenhandschuhe mit Steuer-/Sensor-Akzenten. |
| ✅ | fighter_vest | `icons/equipment/fighter_vest.png` | PNG transparent, 256×256 | Set **Jäger-Schwarm**: **Brust** — leichte Flugweste/Exo-Geschirr, beweglich, cyan Linien. |
| ✅ | fighter_boots | `icons/equipment/fighter_boots.png` | PNG transparent, 256×256 | Set **Jäger-Schwarm**: **Schuhe** — leichte Schub-/Manöver-Stiefel mit kleinen Düsen. |
| ✅ | cruiser_helm | `icons/equipment/cruiser_helm.png` | PNG transparent, 256×256 | Set **Kreuzer-Bataillon** (Schiffsklasse `cruiser`, ausgewogen/taktisch, blau-cyan): **Kopf** — taktischer Offiziershelm mit Comm-Headset. |
| ✅ | cruiser_gloves | `icons/equipment/cruiser_gloves.png` | PNG transparent, 256×256 | Set **Kreuzer-Bataillon**: **Hände** — verstärkte Taktik-Handschuhe. |
| ✅ | cruiser_plate | `icons/equipment/cruiser_plate.png` | PNG transparent, 256×256 | Set **Kreuzer-Bataillon**: **Brust** — mittlerer Brustpanzer mit Schulterplatten, taktisch. |
| ✅ | cruiser_boots | `icons/equipment/cruiser_boots.png` | PNG transparent, 256×256 | Set **Kreuzer-Bataillon**: **Schuhe** — robuste Einsatzstiefel. |
| ✅ | capital_helm | `icons/equipment/capital_helm.png` | PNG transparent, 256×256 | Set **Schlachtlinie** (Schiffsklasse `capital`, wuchtig/schwer gepanzert, martialisch): **Kopf** — massiver gepanzerter Kommandanten-Helm. |
| ✅ | capital_gauntlets | `icons/equipment/capital_gauntlets.png` | PNG transparent, 256×256 | Set **Schlachtlinie**: **Hände** — schwere Panzerhandschuhe (Gauntlets). |
| ✅ | capital_cuirass | `icons/equipment/capital_cuirass.png` | PNG transparent, 256×256 | Set **Schlachtlinie**: **Brust** — schwerer Panzer-Kürass mit Verstärkungsplatten, imposant. |
| ✅ | capital_greaves | `icons/equipment/capital_greaves.png` | PNG transparent, 256×256 | Set **Schlachtlinie**: **Schuhe** — schwere Panzerstiefel (Greaves). |
| ✅ | salvage_visor | `icons/equipment/salvage_visor.png` | PNG transparent, 256×256 | Set **Bergungs-Montur** (Schiffsklasse `civil`, Transporter/Miner, industriell, warm-cyan): **Kopf** — Bergmanns-/Industrie-Visier mit Stirnlampe. |
| ✅ | salvage_gloves | `icons/equipment/salvage_gloves.png` | PNG transparent, 256×256 | Set **Bergungs-Montur**: **Hände** — schwere Arbeitshandschuhe mit Greifverstärkung. |
| ✅ | salvage_rig | `icons/equipment/salvage_rig.png` | PNG transparent, 256×256 | Set **Bergungs-Montur**: **Brust** — Industrie-Exo-Geschirr/Werkzeug-Rig mit Bergungs-Modulen. |
| ✅ | salvage_boots | `icons/equipment/salvage_boots.png` | PNG transparent, 256×256 | Set **Bergungs-Montur**: **Schuhe** — schwere Magnet-/Greifstiefel. |

### Set-Embleme (4) — referenziert als `assets/img/equipment/set_<class>.png`

> Rundes, plastisch gerendertes **Set-Emblem** (Stil-Anker: `tech/*.png` Medaillon-Look), zeigt im UI
> den Set-Fortschritt (z.B. „Jäger-Schwarm 2/4"). Soll die Set-Identität/Schiffsklasse sofort lesbar machen.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | set_fighter | `icons/equipment/set_fighter.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Set-Emblem **Jäger-Schwarm**: agiles Jäger-/Schwarm-Motiv (mehrere kleine Jäger-Silhouetten/Pfeilspitze), cyan. |
| ✅ | set_cruiser | `icons/equipment/set_cruiser.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Set-Emblem **Kreuzer-Bataillon**: taktisches Kreuzer-/Bataillons-Wappen, blau-cyan. |
| ✅ | set_capital | `icons/equipment/set_capital.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Set-Emblem **Schlachtlinie**: wuchtiges Schlachtschiff-/Linien-Wappen, martialisch, cyan + dezent magenta `#ff4d7d`. |
| ✅ | set_civil | `icons/equipment/set_civil.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Set-Emblem **Bergungs-Montur**: Industrie-/Bergungs-Motiv (Zahnrad + Frachter/Bohrer), warm-cyan. |

### ⬛ ERWEITERUNG (2026-06-19): Beine-Slot + 5 Spielstil-Sets (gleicher Stil-Brief wie oben)

> Neuer **5. Slot „Beine"** für ALLE Sets + **5 neue Sets** (Spielstil statt Schiffsklasse). Gleiche
> Vorgaben: plastisch gerendertes Stück, transparenter Hintergrund, 256×256, ~24–32px noch erkennbar,
> Ablage Master `assets/icons/equipment/<key>.png` + Spiegel `frontend/src/assets/img/equipment/<key>.png`.

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|:---:|---|---|---|---|
| ✅ | slot_legs | `icons/equipment/slot_legs.png` | PNG transparent, 256×256 | Leerer **Beine**-Slot: Beinschienen-/Bein-Umriss, gedämpft cyan, dezent. |
| ✅ | fighter_legs | `icons/equipment/fighter_legs.png` | PNG transparent, 256×256 | Set **Jäger-Schwarm**: **Beine** — leichte aerodynamische Flug-Beinschienen mit Manöver-Akzenten, cyan. |
| ✅ | cruiser_legs | `icons/equipment/cruiser_legs.png` | PNG transparent, 256×256 | Set **Kreuzer-Bataillon**: **Beine** — verstärkte Taktik-Beinschienen, blau-cyan. |
| ✅ | capital_legs | `icons/equipment/capital_legs.png` | PNG transparent, 256×256 | Set **Schlachtlinie**: **Beine** — schwere Panzer-Beinschienen, martialisch. |
| ✅ | salvage_legs | `icons/equipment/salvage_legs.png` | PNG transparent, 256×256 | Set **Bergungs-Montur**: **Beine** — robuste Industrie-Beinschützer mit Werkzeugtaschen, warm-cyan. |
| ✅ | miner_helm | `icons/equipment/miner_helm.png` | PNG transparent, 256×256 | Set **Förder-Garnitur** (Bergbau, industriell, amber-cyan, Erz/Bohrer): **Kopf** — Bergmanns-Helm mit Stirnlampe + Scanner-Visier. |
| ✅ | miner_gloves | `icons/equipment/miner_gloves.png` | PNG transparent, 256×256 | Set **Förder-Garnitur**: **Hände** — schwere Förder-Handschuhe mit Greifverstärkung. |
| ✅ | miner_vest | `icons/equipment/miner_vest.png` | PNG transparent, 256×256 | Set **Förder-Garnitur**: **Brust** — Industrie-Exo mit Erz-Behälter/Bohr-Modulen. |
| ✅ | miner_legs | `icons/equipment/miner_legs.png` | PNG transparent, 256×256 | Set **Förder-Garnitur**: **Beine** — verstärkte Beinschützer mit Werkzeug-Holstern. |
| ✅ | miner_boots | `icons/equipment/miner_boots.png` | PNG transparent, 256×256 | Set **Förder-Garnitur**: **Schuhe** — schwere Magnet-Grubenstiefel. |
| ✅ | trader_visor | `icons/equipment/trader_visor.png` | PNG transparent, 256×256 | Set **Händler-Garnitur** (Handel, edel, gold-cyan, Fracht/Waage): **Kopf** — eleganter Quartiermeister-Helm mit Holo-Display/Monokel. |
| ✅ | trader_gloves | `icons/equipment/trader_gloves.png` | PNG transparent, 256×256 | Set **Händler-Garnitur**: **Hände** — feine Handels-Handschuhe mit Daten-Akzenten. |
| ✅ | trader_coat | `icons/equipment/trader_coat.png` | PNG transparent, 256×256 | Set **Händler-Garnitur**: **Brust** — edler Kaufmanns-Mantel/Geschirr mit Fracht-Manifest-Holo. |
| ✅ | trader_legs | `icons/equipment/trader_legs.png` | PNG transparent, 256×256 | Set **Händler-Garnitur**: **Beine** — elegante Beinschienen mit Gürtel-Beuteln. |
| ✅ | trader_boots | `icons/equipment/trader_boots.png` | PNG transparent, 256×256 | Set **Händler-Garnitur**: **Schuhe** — polierte Reisestiefel. |
| ✅ | scout_hood | `icons/equipment/scout_hood.png` | PNG transparent, 256×256 | Set **Späher-Garnitur** (Spionage, getarnt, dunkel-cyan, Sensor/Tarnung): **Kopf** — getarnte Aufklärer-Kapuze/Helm mit Sensor-Optik. |
| ✅ | scout_gloves | `icons/equipment/scout_gloves.png` | PNG transparent, 256×256 | Set **Späher-Garnitur**: **Hände** — schlanke Schleicher-Handschuhe mit Hack-Akzenten. |
| ✅ | scout_suit | `icons/equipment/scout_suit.png` | PNG transparent, 256×256 | Set **Späher-Garnitur**: **Brust** — Tarn-Anzug/Geschirr mit aktiver Camouflage-Schimmer. |
| ✅ | scout_legs | `icons/equipment/scout_legs.png` | PNG transparent, 256×256 | Set **Späher-Garnitur**: **Beine** — leise Schleich-Beinschienen. |
| ✅ | scout_boots | `icons/equipment/scout_boots.png` | PNG transparent, 256×256 | Set **Späher-Garnitur**: **Schuhe** — gedämpfte Tarnstiefel. |
| ✅ | explorer_helm | `icons/equipment/explorer_helm.png` | PNG transparent, 256×256 | Set **Expeditions-Garnitur** (Expedition, abenteuerlich, teal, Nebel/Kompass): **Kopf** — robuster Expeditions-Helm mit Weitsicht-Visier. |
| ✅ | explorer_gloves | `icons/equipment/explorer_gloves.png` | PNG transparent, 256×256 | Set **Expeditions-Garnitur**: **Hände** — strapazierfähige Forscher-Handschuhe. |
| ✅ | explorer_jacket | `icons/equipment/explorer_jacket.png` | PNG transparent, 256×256 | Set **Expeditions-Garnitur**: **Brust** — Expeditions-Jacke/Geschirr mit Versorgungs-Modulen. |
| ✅ | explorer_legs | `icons/equipment/explorer_legs.png` | PNG transparent, 256×256 | Set **Expeditions-Garnitur**: **Beine** — strapazierfähige Expeditions-Beinschienen. |
| ✅ | explorer_boots | `icons/equipment/explorer_boots.png` | PNG transparent, 256×256 | Set **Expeditions-Garnitur**: **Schuhe** — grobe Allzweck-Trekkingstiefel. |
| ✅ | governor_circlet | `icons/equipment/governor_circlet.png` | PNG transparent, 256×256 | Set **Verwaltungs-Garnitur** (Planet/Gouverneur, edel-autoritär, blau-cyan + gold, Holo-Insignien): **Kopf** — würdevoller Verwalter-Reif/Helm mit Holo-Insignien. |
| ✅ | governor_gloves | `icons/equipment/governor_gloves.png` | PNG transparent, 256×256 | Set **Verwaltungs-Garnitur**: **Hände** — formelle Kommando-Handschuhe. |
| ✅ | governor_robe | `icons/equipment/governor_robe.png` | PNG transparent, 256×256 | Set **Verwaltungs-Garnitur**: **Brust** — Gouverneurs-Robe/Uniform mit Rang-Insignien + Holo-Datenband. |
| ✅ | governor_legs | `icons/equipment/governor_legs.png` | PNG transparent, 256×256 | Set **Verwaltungs-Garnitur**: **Beine** — formelle Uniform-Beinschienen. |
| ✅ | governor_boots | `icons/equipment/governor_boots.png` | PNG transparent, 256×256 | Set **Verwaltungs-Garnitur**: **Schuhe** — polierte Kommando-Stiefel. |
| ✅ | set_miner | `icons/equipment/set_miner.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Set-Emblem **Förder-Garnitur**: Spitzhacke/Bohrer + Erz-Kristall, amber-cyan. |
| ✅ | set_trader | `icons/equipment/set_trader.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Set-Emblem **Händler-Garnitur**: Waage + Frachtcontainer/Münze, gold-cyan. |
| ✅ | set_scout | `icons/equipment/set_scout.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Set-Emblem **Späher-Garnitur**: Auge/Sonde + Tarn-Pulse, dunkel-cyan. |
| ✅ | set_explorer | `icons/equipment/set_explorer.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Set-Emblem **Expeditions-Garnitur**: Kompass/Stern + Nebel, teal. |
| ✅ | set_governor | `icons/equipment/set_governor.png` | PNG transparent, 256×256 (Stil = `tech/*`) | Set-Emblem **Verwaltungs-Garnitur**: Planet + Zahnrad/Insignie, blau-cyan + gold. |

---

## 🗒️ Notizen für Codex

- Optional/später (noch NICHT verdrahtet, daher keine aktive Anforderung): Regions-Hintergründe
  `backgrounds/region_core|region_mid|region_frontier` (atmosphärische Nebel je Galaxie-Region) —
  erst eintragen, wenn das Frontend sie per Region einbindet.
- **`ui`-Button-Icons (trash/advisor/broom):** Master nach `assets/icons/ui/<name>.png`, Spiegel nach
  `frontend/src/assets/img/ui/<name>.png` (der `img/ui/`-Ordner existiert im Frontend noch NICHT → bitte
  anlegen). Sind im Code bereits verdrahtet (`uiIcon()`), zeigen bis dahin den Emoji-Fallback. Sie sitzen
  als kleines führendes Icon IN Buttons (neben Text) → schlichte, klar lesbare Silhouette wichtig, kein Rahmen.

---

## 🏴 Handels-Umbau (2026-06-21) — erledigt

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|---|---|---|---|---|
| ✅ | trade_center | `buildings/` | PNG transparent, 512×512 | Gebäude „Handelszentrum": freistehende orbitale Handelshafen-Station (Markthalle/Kuppel, Andock-Arme, Frachtcontainer, Holo-Handelsanzeigen). Stil-Anker: command_center/shipyard. Master + Spiegel `frontend/src/assets/img/buildings/`. |
| ✅ | trade_network | `icons/tech/` | PNG transparent, 256×256 | Forschung „Handelsnetz": rundes Tech-Medaillon, cyan Knoten-/Routen-Netz zwischen Sternen + zentrale Frachtcontainer. Stil-Anker: astrophysics/alliance_trade. Master + Spiegel `frontend/src/assets/img/tech/`. |

---

## 🏗️ Frontend-Konsistenz-Epos (2026-06-21) — erledigt

| Status | Name | Kategorie / Pfad | Format | Beschreibung / Referenz |
|---|---|---|---|---|
| ✅ | mk2_frame | `icons/ui/` | PNG transparent (Mitte+Ecken), 256×256 | Mk2/Elite-Rahmen-Overlay: goldener Sci-fi-Rahmen + Glow am Rand, transparente Mitte (legt sich um ein Schiff-Icon). Master + Spiegel `frontend/src/assets/img/ui/`. |
| ✅ | targets | `icons/nav/` | PNG transparent, 256×256 | Nav-Icon „Ziele/Bedrohungen": Metallrahmen + cyan Fadenkreuz/Radar-Sweep mit rotem Bedrohungs-Blip. Stil-Anker diplomacy/command. Master + Spiegel `frontend/src/assets/img/nav/`. |

| ✅ | deuterium_prospecting | `icons/tech/` | PNG transparent, 256×256 | Forschung „Deuterium-Prospektion": Tech-Medaillon, Deuterium-Tank + Bohrkopf/Asteroid, cyan. Master + Spiegel `frontend/src/assets/img/tech/`. |
| ✅ | veteran_shipyard | `icons/tech/` | PNG transparent, 256×256 | Forschung „Veteranen-Werft" (schaltet Mk2 frei): Tech-Medaillon, Schiff im Dock + goldener „II"/Stern-Elite-Akzent. Master + Spiegel. |
| ✅ | chronicle | `icons/nav/` | PNG transparent, 256×256 | Nav-Icon „Chronik": Metallrahmen + cyan Holo-Buch + ✦-Funken. Master + Spiegel `frontend/src/assets/img/nav/`. |
