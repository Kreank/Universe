# Planetentypen, Felder & Ressourcen-Hooks — *Universe*

> **Status:** v0.1-Design · **Stand:** 2026-06-07 · Konkretisiert [Doku 06 §3](./06-universe-and-map.md)
> (dort als „Prototyp" markiert). Quelle der Zahlen: [`shared/balance.json`](../../shared/balance.json).
> **Entscheidung:** Planetentypen + Felder-Kurve werden **jetzt gebaut**; Gasplaneten +
> Exotische Materie werden **jetzt designt, später gebaut** (Hook reserviert).

---

## 1. Position bestimmt den Planeten

Die **Position im System** (1..`positions_per_system`, aktuell 15) leitet drei Eigenschaften ab:
**Typ**, **Temperatur** (`temp_max`) und **Felder** (`fields_max`). Mit leichter, seed-stabiler
Streuung je Koordinate (deterministisch, damit reproduzierbar).

### 1.1 Typ-Bänder (15 Positionen)

| Position | Typ | Asset | Charakter |
|---|---|---|---|
| 1–3   | 🔥 **Feuer/Lava** | `planet_hot` | sehr heiß, wenige Felder, kaum Deuterium, viel Solar-Sat-Energie |
| 4–5   | 🪨 **Karg/Felsig** | `planet_normal` | heiß-gemäßigt, mittlere Felder |
| 6–10  | 🌍 **Normal/Gemäßigt** | `planet_normal` / `planet_homeworld` | Optimum: meiste Felder, ausgewogen |
| 11–12 | ❄️ **Kalt** | `planet_cold` | kühl, mehr Deuterium, weniger Sat-Energie |
| 13–15 | 🧊 **Eis** | `planet_cold` | sehr kalt, wenige-mittlere Felder, viel Deuterium |
| *(selten, reserviert)* | 🪐 **Gas** | *(Asset fehlt)* | Quelle für **Exotische Materie** — siehe §3 |

### 1.2 Felder-Kurve (`fields_max`)

Symmetrisch, Peak in der Systemmitte — innen wenig, Mitte viel, außen wieder weniger.
**Basis-Felder** (ohne Terraformer); Peak an OGame angelehnt, da bei uns jede Gebäude-*Stufe*
ein Feld kostet und ein Vollausbau 300+ Felder braucht:

| Pos | 1 | 2 | 3 | 4 | 5 | 6 | 7 | 8 | 9 | 10 | 11 | 12 | 13 | 14 | 15 |
|----|--|--|--|--|--|--|--|--|--|--|--|--|--|--|--|
| `fields_max` | 90 | 110 | 130 | 165 | 200 | 230 | 255 | **265** | 255 | 230 | 200 | 165 | 135 | 110 | 95 |

- Formel-Idee: `base + amp * (1 - |pos - center| / (center-1))` mit `center = ceil(positions/2)`,
  plus ±kleine deterministische Streuung. Alle Stützwerte/Streuung leben in `balance.json`.
- **Heimatplanet:** garantiertes Minimum (z. B. ≥190), unabhängig von der Position (fairer Start).
- **Terraformer / Mond-Bauplatz (später, Doku 06 §4):** erweitern `fields_max` additiv →
  Endausbau guter Lagen Richtung **~350–400+** (OGame-Niveau), ohne dass die Basis schon dort liegt.

### 1.3 Temperatur (`temp_max`)

Aus der Position interpoliert (innen heiß → außen kalt), z. B. `temp_max ≈ T_innen - (pos-1) * step`.
Wirkt bereits heute in `economy.service` (`deut_temp_factor`, Solar-Satellit-Energie). Keine neue
Mechanik nötig — nur die **Herleitung bei Planet-Erstellung** ergänzen (heute Default 40).

---

## 2. Bauplatz-Regeln (Felder)

- **Modell A (GELOCKT):** Gebäude verbrauchen **1 Feld pro Stufe** (`fields_used += 1` je
  Ausbau — bereits implementiert). Metallmine Stufe 25 = 25 Felder. Felder sind damit ein
  knappes, strategisches Budget → Planetengröße/Typ/Position bedeuten etwas, Terraformer hat Zweck.
- **Verteidigung verbraucht KEIN Feld** (Werft fasst `fields_*` nicht an — bereits so).
- **NEU: `fields_max` wird erzwungen** — Bau-Start blockt, wenn `fields_used >= fields_max`
  (heute kein Guard). Fehlermeldung „Kein Bauplatz frei".
- **NEU (Pflicht-Begleitfeature): Abreißen/Zurückstufen erstattet Felder** (`fields_used -= 1`)
  → Felder sind ein *verwaltetes* Budget, kein endgültiger Verlust; mildert „Planet voll"-Frust.
- *(Später: Terraformer/Mond-Bauplatz erweitern `fields_max` additiv → Endausbau ~350–400+,
  vgl. Doku 06 §4.)*

---

## 3. Gasplaneten & Exotische Materie — RESERVIERT (Design jetzt, Bau später)

> **Nicht implementieren**, bis Allianzen + High-End-Forschung existieren. Hier nur der
> festgelegte Hook, damit Schema/Enum/Balance konsistent vorbereitet werden können.

- **Gasplanet** = eigener, **seltener** Planetentyp (bevorzugt äußere Positionen). Eigene Optik
  (`planet_gas`-Asset noch zu erstellen). Evtl. **keine/wenige normalen Felder**, dafür einziger
  Quell-Typ für Exotische Materie.
- **Exotische Materie** = **strategische 4. Ressource**:
  - **Kein/kaum Verfall**, eigenes (knappes) Lager, langsame Förderung (Spezialgebäude, z. B.
    „Gas-Synthesizer" auf Gasplaneten).
  - **Verwendung:** Allianzgebäude, End-Game-Forschung, evtl. Top-Schiffe/Module.
  - **NICHT** Teil des normalen Wirtschafts-Loops (Metall/Kristall/Deuterium bleiben Basis).
- **Reservierter Hook (wenn so weit):** `resource_type`-Enum um `exotic_matter` erweitern,
  `balance.json` → eigene Sektion `exotic`, Topbar/Lager nur einblenden, wenn der Spieler
  Zugang hat. Bis dahin: **nichts am Schema ändern** (vermeidet toten Ballast).

---

## 4. Umsetzungs-Status / nächste Schritte

**Jetzt baubar (self-contained):**
1. `balance.json` → Sektion `planets`: Typ-Bänder, Felder-Stützwerte, Temp-Interpolation, Streuung.
2. Backend: Helfer `derive_planet(position) -> (type, temp_max, fields_max)`; bei Planet-Erstellung
   (`auth.service` / spätere Kolonisierung) setzen. `planet_type`-Spalte ergänzen (Migration).
3. **`fields_max` erzwingen** im Bau-Start (`buildings.service`).
4. Galaxie/Planet-UI: Typ + Felder anzeigen; Planet-Asset nach Typ (`planet_hot/normal/cold/...`).

**Reserviert (nicht jetzt):** Gasplaneten, Exotische Materie (§3), Terraformer.
