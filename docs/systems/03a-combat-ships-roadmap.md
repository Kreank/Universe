# Kampf & Schiffe — Roadmap zur Vertiefung

> **Status:** v0.1-Plan · **Stand:** 2026-06-07 · konkretisiert [03 Schiffe](./03-ships-and-units.md)
> + [04 Kampf](./04-combat-model.md). Ziel: „tiefer als OGame", aber auf der bestehenden,
> getesteten Engine aufbauend (kein Reinfall in Neubau).

---

## 0. Ist-Zustand (verifiziert) — was schon da ist ✅

- **Engine** (`combat/engine.py`): deterministisch, 8 Runden, gezieltes Feuer, Schild→Hülle,
  Schild-Regen/Runde, **Schild-Abprall** (<1 %), **Rapidfire-Ketten** `(rf-1)/rf`,
  Explosion <70 % Hülle, Tech-Boni (Waffen/Schild/Panzer), **Commander-Schiffsboni**. → solide.
- **Balance** (`combat`-Sektion): Trümmer **30 %** (Schiffe; Verteidigung 0), Plünderung 50 %,
  Verteidigungs-Regen 70 %, Evakuierungs-Parameter (Rang/Logistik/Überlebende). → definiert.
- **Lücke:** `balance.json` hat erst **5 Schiffe / 2 Verteidigungen** — Doku 03 designt **14 / 10**.
  Rapidfire-Matrix ist nur rudimentär. Tempo/Interception, aktive Fähigkeiten, Simulator fehlen.

**Antworten auf die offenen Fragen:** Rapidfire = ja, volle Tiefe behalten. Kreuzer-vs-leichte-
Jäger = ja (RF 6). Trümmer-% = 30 (tunebar). → Kein Redesign der Engine nötig, wir **füllen & vertiefen**.

---

## 1. Phasenplan (priorisiert)

| # | Phase | Inhalt | Abhängig von |
|---|-------|--------|--------------|
| **1** | **Roster finalisieren** | volle 14 Schiffe + 10 Verteidigungen + **Rapidfire-Matrix** + neue Tech-Gates (Antriebe/Waffen) in `balance.json`; Frontend-Metas + Werft-Gruppen; Doku-Werte | — |
| **2** | **Trümmer- & Recycler-Loop** | Trümmerfeld als Orbit-Objekt persistieren; **Recycler** + `recycle`-Mission zum Einsammeln; Trümmer-% tunen | 1 |
| **3** | ⭐ **Tempo & Interception** | Flotten in Reichweite sichtbar (Sensor-Phalanx); **Abfang-Mission**: schnelle Flotte fängt langsamere im Flug ab → Kampf im freien Raum (keine Planetenverteidigung) | 1 |
| **4** | **Aktive Commander-Fähigkeiten** | Konzentriertes Feuer / Rückzug / Flanke (Doku 04 §8.1, entschieden) als einsetzbare Manöver vor/in der Schlacht | 1 |
| **5** | **Flaggschiff / Permadeath / Capture** | Ist-Stand prüfen & vervollständigen: Commander reist auf Flaggschiff; Vernichtung → Evakuierung→Capture→Permadeath-Kette | 1, 4 |
| **6** | **Kampf-Simulator** | In-Game-Planungstool, **dieselbe Engine** (eine Wahrheit), seed-basiert | 1 |
| **7** | **Verteidigungs-Spezialmechaniken** | Schildkuppeln (max 1/Planet), Abfang-/Interplanetarrakete (Raketen-Mechanik), Verteidigungs-Trümmer optional | 1 |

> Empfohlene Reihenfolge: **1 → 2 → 3 → 4 → 5 → 6 → 7.** Phase 1 ist Fundament für alles.

---

## 2. Phase 1 — Roster-Spezifikation (Prototyp-Werte, tunebar)

Hülle = (Metall+Kristall)/10 (Engine-Formel). Werte OGame-nah, als Startpunkt fürs Balancing.

### 2.1 Zivile / Hilfsschiffe
| Schiff | Angriff | Schild | Metall | Kristall | Deut | Fracht | Tempo | Sprit | Tech-Gate |
|--------|:--:|:--:|--:|--:|--:|--:|--:|--:|--|
| Kleiner Transporter ✓ | 5 | 10 | 2000 | 2000 | 0 | 5000 | 5000 | 10 | combustion_drive 2 |
| **Großer Transporter** | 5 | 25 | 6000 | 6000 | 0 | 25000 | 7500 | 50 | combustion_drive 6 |
| **Kolonieschiff** | 50 | 100 | 10000 | 20000 | 0 | 7500 | 2500 | 1000 | impulse_drive 3 |
| **Recycler** | 1 | 10 | 10000 | 6000 | 2000 | 20000 | 2000 | 300 | combustion_drive 6 · shield_tech 2 |
| Spionagesonde ✓ | 0 | 0 | 0 | 1000 | 0 | 5 | 1e8 | 1 | spy_tech 1 |
| **Solarsatellit** | 0 | 1 | 0 | 2000 | 0 | 0 | 0 | 0 | shipyard 1 *(Energie im Orbit, im Kampf zerstörbar)* |

### 2.2 Kampfschiffe
| Schiff | Angriff | Schild | Metall | Kristall | Deut | Tempo | Sprit | Tech-Gate |
|--------|:--:|:--:|--:|--:|--:|--:|--:|--|
| Leichter Jäger ✓ | 50 | 10 | 3000 | 1000 | 0 | 12500 | 20 | combustion_drive 1 |
| Schwerer Jäger ✓ | 150 | 25 | 6000 | 4000 | 0 | 10000 | 75 | impulse_drive 2 · armor_tech 2 |
| Kreuzer ✓ | 400 | 50 | 20000 | 7000 | 2000 | 15000 | 300 | impulse_drive 4 · ion_tech 2 |
| **Schlachtschiff** | 1000 | 200 | 45000 | 15000 | 0 | 10000 | 500 | hyperspace_drive 4 |
| **Schlachtkreuzer** | 700 | 400 | 30000 | 40000 | 15000 | 10000 | 250 | hyperspace_tech 5 · laser_tech 12 |
| **Bomber** | 1000 | 500 | 50000 | 25000 | 0 | 4000 | 1000 | impulse_drive 6 · plasma_tech 5 |
| **Zerstörer** | 2000 | 500 | 60000 | 50000 | 15000 | 5000 | 1000 | hyperspace_drive 6 · plasma_tech 5 |
| **Todesstern** | 200000 | 50000 | 5000000 | 4000000 | 1000000 | 100 | 1 | graviton_tech 1 · hyperspace_drive 7 · hyperspace_tech 6 |

### 2.3 Rapidfire-Matrix (wer feuert schnell gegen wen)
Kern der Tiefe — „Komposition schlägt Masse". Auszug der wichtigsten Ketten:
- **Kreuzer** → leichter Jäger 6, Raketenwerfer 10, Sonde/Sat 5
- **Schwerer Jäger** → kleiner Transporter 3, Sonde 5, Sat 3
- **Schlachtkreuzer** → kleiner/großer Transporter 3, schwerer Jäger 4, Kreuzer 4, **Schlachtschiff 7**, Sonde/Sat 5
- **Bomber** → **Verteidigung** (Raketenwerfer 20, leichtes/schweres Laser 10–20, Ionen/Gauß/Plasma 5–10)
- **Zerstörer** → leichtes Laser 10, **Schlachtkreuzer 2**, Sonde/Sat 5
- **Todesstern** → fast alles (sehr hohe RF), außer Zerstörer/Schlachtkreuzer moderat
- Alle Kampfschiffe → Spionagesonde 5, Solarsatellit 5

### 2.4 Verteidigung
| Anlage | Angriff | Schild | Metall | Kristall | Deut | Hinweis | Tech-Gate |
|--------|:--:|:--:|--:|--:|--:|--|--|
| Raketenwerfer ✓ | 80 | 20 | 2000 | 0 | 0 | Kanonenfutter | werft 1 |
| Leichtes Laser ✓ | 100 | 25 | 1500 | 500 | 0 | Allround | energy_tech 1 · laser_tech 3 |
| **Schweres Laser** | 250 | 100 | 6000 | 2000 | 0 | robuster | energy_tech 3 · laser_tech 6 |
| **Gaußkanone** | 1100 | 200 | 20000 | 15000 | 2000 | Anti-Groß | weapons_tech 3 · shield_tech 1 · energy_tech 6 |
| **Ionengeschütz** | 150 | 500 | 2000 | 6000 | 0 | Schildtank | ion_tech 4 |
| **Plasmawerfer** | 3000 | 300 | 50000 | 50000 | 30000 | stärkste | plasma_tech 7 |
| **Kleine Schildkuppel** | 1 | 2000 | 10000 | 10000 | 0 | **max 1/Planet** | shield_tech 2 |
| **Große Schildkuppel** | 1 | 10000 | 50000 | 50000 | 0 | **max 1/Planet** | shield_tech 6 |
| **Abfangrakete** | — | — | 8000 | 0 | 2000 | fängt Interplanetarraketen (Phase 7) | werft 1 |
| **Interplanetarrakete** | 12000 | — | 12500 | 2500 | 10000 | zerstört feindl. Verteidigung (Phase 7) | impulse_drive 1 · werft 4 |

### 2.5 Neue Forschungen (Tech-Gates oben)
`hyperspace_drive`, `hyperspace_tech`, `laser_tech`, `ion_tech`, `plasma_tech`, `graviton_tech`
(+ optional `astrophysics` fürs Kolonieschiff/Kolonie-Limit). Reine Daten in `research.techs`
(Kosten/`requires`/`effect`) + Frontend-`TECH_META`. Antriebs-Techs könnten später auch das
**Flug-Tempo** skalieren (Hook offen).

---

## 3. ⭐ Phase 3 — Interception (das „tiefer als OGame")

OGame lässt Flotten **im Flug nicht** abfangen. Genau das ist unser Mehrwert:

- **Sichtbarkeit:** Sensor-Phalanx/Mond (Doku 06 §4) zeigt feindliche **Flottenbewegungen** in
  Reichweite (Start, Ziel, Ankunftszeit).
- **Abfang-Mission (`intercept`):** Spieler schickt eine Flotte auf eine **gegnerische Flotte**
  (nicht auf einen Planeten). Erfolg, wenn der Abfänger den Kurs **vor Ankunft** erreichen kann —
  rein über **Tempo & Distanz** (schnelle Schiffe: Schlachtkreuzer/Kreuzer/leichter Jäger).
- **Kampf im freien Raum:** keine Planetenverteidigung, kein Plündern von Gebäuden — nur Flotten
  gegeneinander; Trümmer entstehen am Abfangpunkt.
- **Gegenspiel:** Fleetsave/Umleiten, Eskorte, Tempo-Mix; Picket-/Piraten-Spielstil wird real.
- **MVP-Scope:** erst gegen **fliegende** Flotten mit bekanntem Kurs (Phalanx-Lock); Timing-Fenster
  über Ankunftszeit; ein Abfang-Versuch je Lock. Schrittweise verfeinern.

---

## 4. Abnahme je Phase
- **1:** alle 14/10 Einheiten baubar & im Kampf wirksam; Rapidfire greift; bestehende Combat-Tests grün + neue RF-Tests.
- **2:** Trümmerfeld entsteht, bleibt im Orbit, Recycler holt es; Bilanz stimmt.
- **3:** Abfang nur bei ausreichendem Tempo erfolgreich; Kampf im freien Raum; Bericht im Postfach.
- **4–7:** je eigener Akzeptanztest (siehe Phase-Doc bei Umsetzung).
