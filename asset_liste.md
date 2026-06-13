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
| ⬜ | stat_attack | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Angriff im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ⬜ | stat_shield | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Schild/Verteidigung im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ⬜ | stat_cargo | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Fracht/Laderaum im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ⬜ | stat_speed | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Tempo/Geschwindigkeit im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ⬜ | stat_fuel | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Treibstoff im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ⬜ | stat_energy | `icons/spec/` | PNG transparent, 256×256 | Stat-Icon für Energie im Detail-Popup; konsistenter Sci-Fi-UI-Stil, ohne Text. |
| ⬜ | trait_category_admin | `icons/traits/` | PNG transparent, 256×256 | Fähigkeits-Kategorie-Icon für admin; konsistenter Trait/Commander-Sci-Fi-UI-Stil, ohne Text. |
| ⬜ | trait_category_general | `icons/traits/` | PNG transparent, 256×256 | Fähigkeits-Kategorie-Icon für general; konsistenter Trait/Commander-Sci-Fi-UI-Stil, ohne Text. |

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
