# Rollen-Roster — konkrete Spezifikation

> **Status:** v0.1-Spec · **Stand:** 2026-06-07 · konkretisiert [03b Rollen-Kampf](./03b-role-based-combat.md).
> Werte = **relative Prototyp-Tiers** (1–5); exakte `balance.json`-Zahlen folgen beim Engine-Bau (03b Phase 1).
> Spalten: **S/A/H** = Schild/Antrieb/Hülle · **Waffe** = Angriff (Schadenstyp) · **Reichw.** = Nah/Mittel/Fern.

## Legende
- **S/A/H 1–5:** 1 = vernachlässigbar … 5 = sehr hoch. (Antrieb = Tempo/Initiative/Flucht.)
- **Schadenstyp:** Energie (anti-Schild) · Kinetik (anti-Hülle) · Ionen (anti-Schild+Antrieb) · Rakete (anti-Hülle, abfangbar).
- **Reichweite:** **Nah** (muss ran) · **Mittel** · **Fern** (Standoff/Sensor; feuert zuerst, schwach im Nahkampf).
- **Doktrin:** UNI = universell (alle) · MIL/HAN/PIR/PIO = doktrin-vergünstigt (für andere teurer/später).
- **Asset:** ✓ = vorhanden (03a) · 🎨 = **neu zu erstellen**.

---

## 1. Universell (Kernspiel — alle Spieler)

| Schiff | Rolle | S | A | H | Waffe | Reichw. | Spezial / Konter | Dok | Asset |
|--------|-------|:-:|:-:|:-:|-------|:-:|------------------|:-:|:-:|
| **Späher** | Aufklärung | 1 | 5 | 1 | — | Fern | hohe Sensorreichweite, kein Kampf | UNI | ✓ (spy_probe) |
| **Kleiner Frachter** | Transport | 1 | 3 | 2 | — | — | schnelle, kleine Fracht | UNI | ✓ (small_cargo) |
| **Großer Frachter** | Transport | 2 | 2 | 4 | — | — | Massenfracht (Beute-Ziel!) | UNI | ✓ (large_cargo) |
| **Kolonieschiff** | Expansion | 2 | 1 | 5 | — | — | **gründet Kolonie (Pflicht-Mechanik, alle!)** | UNI | ✓ (colony_ship) |
| **Bergungsschiff** | Wirtschaft | 1 | 2 | 3 | — | — | sammelt Wracks/Loot nach Schlacht | UNI | ✓ (recycler) |
| **Leichter Jäger** | Schwarm | 1 | 5 | 1 | 2 Kinetik | Nah | billig, Masse; **schlägt Artillerie** (kommt drunter) | UNI | ✓ (light_fighter) |
| **Kreuzer** | Allrounder | 3 | 4 | 3 | 3 Energie | Mittel | Jäger-Killer, solide Mitte | UNI | ✓ (cruiser) |
| **Solarsatellit** | Energie | 0 | 0 | 1 | — | — | Energie im Orbit, im Kampf zerstörbar | UNI | ✓ (solar_satellite) |

## 2. Militär — Kriegsherr (offener Krieg, Linienflotten)

| Schiff | Rolle | S | A | H | Waffe | Reichw. | Spezial / Konter | Dok | Asset |
|--------|-------|:-:|:-:|:-:|-------|:-:|------------------|:-:|:-:|
| **Schwerer Jäger** | robuster Schwarm | 2 | 4 | 2 | 3 Kinetik | Nah | Anti-Jäger/Anti-Boarder | MIL | ✓ (heavy_fighter) |
| **Schlachtschiff** | Linie-Tank | 4 | 2 | 5 | 4 Kinetik | Nah–Mit | Brawler, hält Fokus; **schlägt Schwarm** mit Eskort-Flak | MIL | ✓ (battleship) |
| **Artillerieschiff** | Standoff | 2 | 2 | 2 | 5 Kinetik | **Fern** | Glaskanone, **überreicht Linie**; schwach Nah | MIL | ✓ (destroyer) |
| **Bomber** | Belagerung | 3 | 2 | 4 | 4 **Rakete** | Mittel | **Verteidigungs-Brecher**; von Punktverteidigung abfangbar | MIL | ✓ (bomber) |
| **Träger** | Kraftmultiplikator | 4 | 2 | 5 | 2 | Mittel | **startet Drohnen/Jäger-Staffeln** im Gefecht | MIL | 🎨 |
| **Großkampfschiff** | Flotten-Anker | 5 | 1 | 5 | 5 gemischt | Mittel | selten/teuer/langsam, Endgame-Anker | MIL | ✓ (deathstar) |

## 3. Piraterie — Freibeuter (disable & board)

| Schiff | Rolle | S | A | H | Waffe | Reichw. | Spezial / Konter | Dok | Asset |
|--------|-------|:-:|:-:|:-:|-------|:-:|------------------|:-:|:-:|
| **Interdiktor** | Fangschiff | 3 | 3 | 3 | 1 | Mittel | **Fang-Feld: Disengage→0** (Herzstück der Piraterie) | PIR | 🎨 |
| **EWAR-Fregatte** | Entwaffner | 2 | 4 | 2 | 3 **Ionen** | Mittel | **leert Schilde + legt Antrieb lahm** (erzeugt „gestrandet") | PIR | 🎨 |
| **Enterschiff** | Kaperung | 2 | 3 | 4 | 1 Kinetik | Nah | **entert Gestrandete** → kapert Schiff (+Fracht) | PIR | 🎨 |
| **Tarnkappen-Korvette** | Hinterhalt | 1 | 5 | 2 | 2 Energie | Nah | **Stealth**, eröffnet den Überfall (Überraschungs-Runde) | PIR | 🎨 |

## 4. Eskorte — Service für ALLE (MIL/HAN-Boni)

| Schiff | Rolle | S | A | H | Waffe | Reichw. | Spezial / Konter | Dok | Asset |
|--------|-------|:-:|:-:|:-:|-------|:-:|------------------|:-:|:-:|
| **Eskort-Fregatte** | Punktverteidigung | 3 | 3 | 3 | 2 Kinetik | Nah–Mit | **fängt Raketen + Enterer ab**, schirmt Fracht | UNI | 🎨 |
| **Schild-Tender** | Schild-Support | 5 | 2 | 3 | — | Mittel | **projiziert/repariert Schilde** im Gefecht (kontert Strand-Fenster) | UNI | 🎨 |
| **Abfangjäger** | Interceptor | 2 | 5 | 1 | 3 Energie | Nah | sehr schnell, Anti-Jäger/Anti-Boarder | UNI | 🎨 |

## 5. Wirtschaft & Pionier (HAN / PIO Signatur)

| Schiff | Rolle | S | A | H | Waffe | Reichw. | Spezial / Konter | Dok | Asset |
|--------|-------|:-:|:-:|:-:|-------|:-:|------------------|:-:|:-:|
| **Bergbauschiff** | mobiler Abbau | 2 | 1 | 4 | — | — | baut Asteroiden/Felder ab | HAN | 🎨 |
| **Tief-Aufklärer** | Langstrecken-Recon | 2 | 4 | 2 | — | Fern | große Sensorreichweite, Tief-Spionage | PIO | 🎨 |
| **Expeditions-Schiff** | Erkundung | 3 | 3 | 4 | 1 | Mittel | Expeditionen/Langstrecke, Bergungs-Boni | PIO | 🎨 |

---

## 6. Konter-Gerüst (Schere-Stein-Papier mit Tiefe)

- **Offener Kampf:** Schwarm (leichter/schwerer Jäger) → schlägt **Artillerie** (kommt unter die Geschütze)
  → schlägt **Linie-Tank** (Überreichweite) → schlägt **Schwarm** (Flak via Eskort-Fregatte / Flächenschaden).
  **Träger** multipliziert Schwarm; **Großkampfschiff** ankert, ist aber langsam & teuer.
- **Piraterie-Loop:** Interdiktor (Fang) + EWAR (Schild→Antrieb lahm) → **gestrandet** → Enterschiff kapert.
  **Tarnkappe** eröffnet. **Konter:** Schild-Tender (hält Schilde) + Eskort-Fregatte (killt Enterer/Raketen)
  + Abfangjäger (jagt Stealth/Boarder).
- **Reichweite:** Artillerie/Tief-Aufklärer feuern aus **Fern** zuerst; Nah-Schiffe müssen über Bänder
  heran (Antrieb = Initiative). Glaskanonen sterben, wenn der Schwarm sie erreicht.

## 7. Finale Asset-Liste (neu zu erstellen 🎨)

**Schiffe (12)** — Stil wie der bestehende Satz (3D-Render, cyan Akzentlicht, transparenter Hintergrund):
| Datei (key) | Visueller Brief |
|-------------|-----------------|
| `carrier.png` | Träger: breiter Rumpf mit offenem Hangar-Deck, Drohnen-Buchten, wuchtig |
| `interdictor.png` | Interdiktor: gedrungen, große Feld-Generator-Ringe/Antennen-Gitter (Fang-Feld) |
| `ewar_frigate.png` | EWAR-Fregatte: schlank, markante Ionen-/EMP-Emitter, blaue Energie-Coils |
| `boarder.png` | Enterschiff: gepanzerter Bug mit Enter-/Greifklauen, Andock-Tunnel |
| `stealth_corvette.png` | Tarnkappen-Korvette: kantig-facettiert, dunkel, schwaches Glühen (stealth) |
| `escort_frigate.png` | Eskort-Fregatte: viele kleine Punktverteidigungs-Türme, kompakt-defensiv |
| `shield_tender.png` | Schild-Tender: zentraler Schild-Projektor-Dom, Support-Optik, kaum Waffen |
| `interceptor.png` | Abfangjäger: extrem schlank, große Triebwerke, Speed-Silhouette |
| `miner.png` | Bergbauschiff: Bohr-/Sammelarme, Erz-Buchten, industriell |
| `deep_scout.png` | Tief-Aufklärer: große Sensor-Schüssel/Antennen, leicht & schnell |
| `expedition_ship.png` | Expeditions-Schiff: robust, Langstrecken-Tanks, Bergungs-Optik |
| *(opt.)* `drone.png` | Träger-Drohne/Jäger-Staffel (klein, für Träger-Mechanik) |

**Waffen-/Schadenstyp-Icons (4):** `weapon_energy`, `weapon_kinetic`, `weapon_ion`, `weapon_missile` (für Ladungs-/Tooltip-UI).
**Status-Icons (5):** `status_shield_down`, `status_drive_damaged`, `status_stranded`, `status_interdiction`, `status_boarding`.
**Effekte (3):** `fx_ion_emp`, `fx_boarding`, `fx_warp_disrupt` (ergänzend zu shield_hit/explosion/engine_glow).

> Bereits vorhandene 03a-Schiffe (✓) brauchen **keine** neue Art — sie übernehmen ihre Rolle.
