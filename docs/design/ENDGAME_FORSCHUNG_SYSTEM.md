# Endgame, Forschung & ewiges Universum — Systemdesign

> Status: **Design** (2026-06-14). Leitmemory: `project_universe_endgame_econ`.
> Quelle: 6-teilige Web-Recherche (OGame Lifeforms, Stellaris, EVE, Hades' Star, Civ VI,
> Endless Space 2, Travian, Anno, X4, Factorio/NMS u.a.) + bestehende Universe-Systeme.

## 0. Leitprinzipien (nicht verhandelbar)

1. **Ewiges Universum, kein Reset.** Forschung & Endgame müssen *unendlich* relevant
   bleiben, ohne in Power-Creep zu kippen.
2. **Kein Pay-to-Win.** Monetarisierung höchstens kosmetisch. Exotische Materie ist
   **erspielt** (Abbau/Quest/Farming), nie gekauft.
3. **Neuling UND Veteran profitieren.** Jede Mechanik wird an dieser Achse geprüft.
   Veteranen dürfen nicht uneinholbar enteilen; Neulinge müssen pro investierter
   Stunde *mehr* herausholen (sinkender Grenznutzen + Catch-up-Hebel).
4. **Forschung = Motor, Aktivitäten = Inhalt.** Forschung schaltet frei/skaliert;
   Megastrukturen, Schwarzes Loch, Deep-Space sind das, was man *tut*.

## 1. Das Neuling-vs-Veteran-Modell (Querschnitt)

Drei zusammenwirkende Mechaniken halten die Schere klein — alle aus der Recherche belegt:

- **Sinkender Grenznutzen (Stellaris Repeatables):** lineare Kosten + *additiver* Effekt
  → Level 50 kostet ein Vielfaches von Level 5, gibt aber denselben Block. Der Veteran
  zahlt für jedes weitere Prozent immer mehr; der Neuling holt früh viel Prozent billig.
- **Aktivitäts-Boosts / Eureka (Civ VI):** In-Game-Leistung verbilligt die nächste
  passende Forschung (z. B. „gewinne eine Schlacht mit Schiffstyp X" → −X % auf
  Waffentech). Belohnt *Spielen*, nicht Zeit/Geld → gezielter Catch-up für Neue.
- **Horizontale Tiefe (EVE T2/T3):** ab dem Plateau Breite/Optionen (Module, Fits,
  Crew-Spezialisierung) statt rohem +X %. Ein Spezialist schlägt einen Generalisten in
  *seiner* Nische, egal wie alt dessen Account ist.

Plus **Anti-Snowball-Bremsen** (s. §6), damit Veteranen-Flotten Neulinge nicht aus
entfernten Regionen drängen können.

## 2. Forschung — Struktur & Klarheit

### 2.1 Sofort (Klarheit, teils erledigt)
- **Präzise Effektzeile pro Tech** im Detail-Popup (`TECH_EFFECTS.levelEffect`):
  „aktuell → nächste Stufe" mit echten Zahlen. ✅ erledigt: `energy_tech` (Energieausbeute
  sichtbar), `combustion/impulse/hyperspace_drive` (+10/20/30 % Reisetempo).
- **Verbleibend:** `command_doctrine` (Span-Formel), `jump_gate_tech`/`gravitics`
  (Doppeleffekt), Freischalt-Techs `laser/ion/plasma/hyperspace/graviton` listen die
  konkret freigeschalteten Schiffe/Defs.

### 2.2 IGFN — Intergalaktisches Forschungsnetzwerk (beschlossen: nur Forschung)
- Neue Forschung `research_network`. Heute zählt für die Forschungszeit **nur das Labor
  am Forschungsplaneten**. IGFN summiert die **Labore der besten (network_level+1)
  Planeten**. Voraussetzung: `computer_tech` (z. B. 8) + `research_lab` hoch.
- Implementierung: `research/service.py::research_seconds` bekommt die **Summe** statt
  `lab_lvl`; neue Helper `effective_lab_level(player, network_level)`.
- Nutzen Neuling↔Veteran: belohnt Expansion (mehr Kolonien = schneller), wirkt aber erst
  ab 2+ Planeten → kein Vorteil für reine Turtle-Veteranen ohne Breite.

### 2.3 Repeatable Techs — der ewige Motor (Stellaris-Modell)
- Neuer Tech-Typ mit `repeatable: true`, **kein** `max_level`.
- **Effekt additiv, flach:** z. B. +2 %/Level (Wirtschaft) bzw. +1 %/Level (Kampf).
- **Kosten linear-additiv:** `Kosten(n) = base + n · increment` (NICHT `2^n`!). Das ist
  der entscheidende Unterschied zu den Basis-Techs und der Grund, warum spätere Level
  sich noch lohnen, aber der Grenznutzen sinkt.
- Freischaltung erst nach Maxen der jeweiligen Basis-Tech-Kette (Tier-Gate).
- Kandidaten: `weapons_mastery` (+1 % Angriff), `shield_mastery`, `armor_mastery`,
  `extraction_mastery` (+Förderung), `energy_mastery`, `propulsion_mastery` (+Tempo).
- Hohe Stufen kosten zusätzlich **Dunkle Materie** → koppelt den Motor an den Sink.

### 2.4 Aktivitäts-Boosts (Eureka, Phase später)
- Pro Tech ein optionaler `boost`-Trigger (Schlacht gewonnen, X Ressourcen gehandelt,
  Expedition überlebt) → einmalig −40 % Restkosten der nächsten Stufe.

### 2.5 UI-Gliederung
Tabs existieren (Antrieb/Kampf/Führung/Wirtschaft). Ergänzen: eigener Tab **„Endgame"**
für IGFN/Repeatables/Exotik-Techs, damit der Frühspieler nicht erschlagen wird.

## 3. Wirtschafts-Endgame (#2 — zuerst)

### 3.1 Zwei erspielte Ressourcen (beschlossen)
| Ressource | Achse | Quelle (erspielt) | Verwendung | Haupt-Sink |
|---|---|---|---|---|
| **Dunkle Materie** | zivil/Forschung | Schwarzes-Loch-Vorkommen, Tiefraum-Expedition, seltene Drops | Repeatable-Hochstufen, Terraforming-Hochstufen, Megastruktur-Bau, Kommandeur-Veredelung | laufender Labor-Upkeep + eskalierende Bau-Kosten |
| **Antimaterie** | militärisch/Energie | umkämpfte Sektoren, Kampf-/Trümmer-Drops, Raffinerie aus instabilem Vorprodukt | Top-Schiffsmodule, Antimaterie-Reaktor (Energie), Superwaffen | laufender Modul-Upkeep + Flottenverluste |

**Design-Regeln (Stellaris/EVE):**
- **Klasse B:** NICHT aus Metall/Kristall/Deuterium synthetisierbar → strukturelle Knappheit.
- **Tech-Gate:** `dark_matter_extraction` / `antimatter_containment` (teure Forschung;
  Bootstrap-Charge muss erspielt werden).
- **Kontoweit gespeichert** (neue `Player`-Felder `dark_matter`, `antimatter`; Migration).
  Begründung: global verdient, global ausgegeben (Forschung/Megastruktur).
- **Laufender Verbrauch = Hauptsink.** Dark-Matter-Labore / Antimaterie-Reaktoren
  verbrauchen pro Tick. Hortbestand = „Vorrat für X Tage Betrieb", nicht totes Kapital.
- **Defizit-Malus statt Hard-Block:** leerer Vorrat → Modul/Forschung läuft mit Malus
  weiter (z. B. −50 % Wirkung), kein Crash, keine Sperre.
- **Risiko-Gating:** Vorkommen nur in gefährlichen Zonen (Schwarzes Loch, Tiefraum,
  umkämpfte Sektoren) → kein sicheres AFK-Farmen. Über viele Systeme **gestreut** (kein
  Monopol-Knoten).

### 3.2 Fördertechnik (beschlossen: eigene Tech, nicht plasma)
- Neue Wirtschafts-Tech `extraction_tech`: +1 % Metall, +0,66 % Kristall, +0,33 % Deut
  Förderung je Stufe (OGame-Plasma-Werte). plasma_tech bleibt rein militärisch.
- Verdrahtung in `economy/service.py` (Minen-Rate), analog `mining_efficiency`.

### 3.3 Terraforming
- Neue Forschung `terraforming`: **+5 Bauplätze (`fields_max`) je Stufe** auf allen
  Planeten (account-wide Research, additiv in `effective_fields_max`).
- Kosten steil (Kristall+Deut); ab Stufe X zusätzlich **Dunkle Materie**.
- Ewiger Bau-Sink: mehr Felder → mehr Gebäudestufen → mehr Ressourcen-Senke.

### 3.4 Produktions-Drohnen (Crawler-Analog, optional Phase 2b)
- Stationäre Planeten-Einheit `harvester_drone`: +0,02 %/Stück Förderung, **Cap 50 %**
  der Basis, Max-Anzahl an Minenstufen gekoppelt. Zeitbasierter, hart gedeckelter
  Spätspiel-Sink (kein Zahlsieg).

## 4. Megastrukturen (#3 — danach)

**Payoff nach Achsen getrennt** (Stellaris), je eine strategische Rolle:
| Megastruktur | Achse | Liefert (qualitativ einzigartig!) | Standort |
|---|---|---|---|
| **Dyson-Schwarm** | Energie | massive Energie (entkoppelt von Solar/Fusion) | Heimatstern |
| **Materie-Dekompressor** | Rohstoff | Metall/Kristall-Strom | nur am **Schwarzen Loch** |
| **Forschungs-Nexus** | Forschung | Forschungstempo-Multiplikator | 1× pro Imperium |
| **Orbitalwerft XXL** | Militär | reduzierte Bauzeit/Kapazität für Großschiffe | Mond |
| **Sprungtor-Nexus** | Logistik | Sprung-Netz, senkt Sprung-Erschöpfung | Mond |
| **Galaktisches Monument** | Prestige | Imperiumswert + periodische Belohnung (Crew/Modul) | Heimat |

**Bau-Mechanik (Stellaris/X4/DSP):**
- Mehrschichtiges Gate: Stufen-Forschung → Bauplatz → **4–6 Ausbaustufen** mit
  exponentiell steigenden Kosten + langen Echtzeit-Timern (Wochen).
- **Nur 1 Megastruktur-Projekt gleichzeitig** pro Spieler (zentrale Anti-Snowball-Bremse).
- **Bau-Geschwindigkeit hart gedeckelt, nicht kaufbar** (P2W-Schutz).
- **Baufortschritt öffentlich** auf der Sternenkarte (Statussymbol + Ziel).
- **Standortknappheit** (Schwarzes Loch, besondere Monde) erzeugt PvP-Hotspots.
- **Gegen Obsoleszenz:** qualitativ Einzigartiges + **laufender Unterhalt/Verfall** →
  dauerhafter Sink statt Einmal-Nutzen.
- Imperiumswert-Kopplung: großer Zuwachs, bricht bei Zerstörung ein (Prestige-Risiko).
- **Allianz-Variante** (später): gemeinsam finanziert, eroberbar, Reinforcement-Timer.

## 5. Militär-Endgame (#4 — Richtung greenlit)

- **Kolossal-Schicht über dem Todesstern, Rollen statt Power** (Stellaris/EVE):
  - **Flaggschiff** mit **System-Aura** (Buff eigene / Debuff feindliche Flotte) →
    Bühne für Kommandeur-Traits. Stückzahl-Cap.
  - **Mobile Werft** (1 pro Konto): baut/repariert im Feld.
  - **Planetenzerstörer** mit **Modus-Wahl**: zerstören (→ Trümmer → Mond), lähmen, oder
    Infrastruktur intakt erobern. Extrem teuer/langsam, Antimaterie-gegated.
- **Module/Subsysteme** (EVE T3) auf Endgame-Hüllen: gleiche Hülle → viele Fits
  (Tank/Bomber/EW). Horizontale, endlos re-spielbare Tiefe; entkoppelt Macht von Grind.
- **Superwaffe mit Verwundbarkeits-Fenster** (lange Aufladung → danach immobil/offen) →
  vorhandene Phalanx/Abfangen wird zum Gegenspiel.
- **Jedes Schiff mit explizitem Hard-Counter** (Ionen-Disruptor, Abfangjäger-Rapidfire
  existieren schon — konsequent fortführen).

## 6. Anti-Snowball-Bremsen (Pflicht im ewigen Universum)

- **Flotten-Upkeep mit progressivem Malus** — *die* fehlende OGame-Bremse. Über einer
  „Versorgungskapazität" (skaliert mit Planeten/Monden/Forschung) steigen die laufenden
  Erhaltungskosten (Deut/Energie) **progressiv**. Riesenflotten im Stand-by werden teuer
  → einsetzen oder abrüsten. Kapazität nicht kaufbar → P2W-frei.
- **Sprung-/Reise-Erschöpfung** (EVE Phoebe): wiederholte Schnellsprünge akkumulieren
  Müdigkeit → Machtprojektion bleibt lokal → schützt entfernte Neulinge dauerhaft.
- **Sanfter Aktivitäts-Cap** (Pardus): tägliche Hochrisiko-Aktionen (Expedition/Spionage)
  gedeckelt, für alle gleich → bremst Multi-Account-Monopole.
- **Stückzahl-Caps** pro Top-Klasse; **harte %-Caps** auf Produktions-Boni (Crawler 50 %).

## 7. Implementierungs-Phasen & Status (Stand 2026-06-14)

- **Phase 0 — Klarheit & IGFN — ✅ FERTIG & getestet.** Effektzeilen (energy_tech,
  Antriebe, command_doctrine, laser_tech, …), „Endgame"-Tab, `research_network`
  (IGFN, `sum_top_labs` + `effective_lab_level`). 5 Regressionstests.
- **Phase 1 — Ewiger Motor — ✅ FERTIG & getestet.** Repeatable-Tech-Typ
  (`repeatable: true`, lineare Kosten `base*(level+1)`), Mastery-Techs
  `weapons_/shield_/armor_mastery` (+1 %/Lvl, additiv, in `combat/engine.py`).
  4 Regressionstests. *(Aktivitäts-/Eureka-Boosts: bewusst zurückgestellt.)*
- **Phase 2 — Wirtschafts-Endgame — ✅ FERTIG & getestet.** `extraction_tech`
  (Fördertechnik +1 %/Lvl) + `extraction_mastery` (repeatable) in `economy/service.py`;
  `terraforming` (+5 `fields_max`/Lvl) in `effective_fields_max` + API. Dunkle Materie +
  Antimaterie: `Player`-Spalten + Migration + init.sql + Expeditions-Erspielung
  (`fleet/expedition.py`) + `PlayerOut`-API. 4 Regressionstests.
  - **Offen (Phase 2b):** sichtbare Exotik-Bestände im Frontend-Top-Bar; laufender
    Upkeep-Sink + Defizit-Malus; Tech-Gates `dark_matter_extraction` /
    `antimatter_containment` (greifen erst mit Sinks aus Phase 3/4).
- **Phase 3 — Megastrukturen (#3) — ✅ FERTIG & getestet.** `megastructures`-Tabelle +
  Migration + init.sql; Service (`stage_cost`/`stage_build_seconds`/`effect_mult`/
  `start_build`/`complete_megastructure`), Router (`GET /megastructures`, `POST …/build`),
  Scheduler + Recovery, **1-Projekt-gleichzeitig**, **Dunkle-Materie-Sink**. Zwei Strukturen
  wirksam: `research_nexus` (+8 % Forschungstempo/Lvl → `research_seconds`) +
  `matter_decompressor` (+5 % Förderung/Lvl → `economy`). Frontend-Screen (Nav/Route/API/
  Modelle/Komponente). 3 Regressionstests.
  - **Offen (Phase 3b):** Sternenkarten-Baufortschritt (öffentlich), Standortbindung an
    Schwarzes Loch/Monde, Allianz-/eroberbare Strukturen, weitere Payoff-Achsen.
- **Phase 4 — Militär-Endgame & Bremsen — ◐ KEYSTONE FERTIG & getestet.** **Flotten-Upkeep
  als Anti-Snowball-Bremse** (`fleet/upkeep.py`, stündlicher Job, diskret — kein Eingriff in
  die Lazy-Accrual): über der Versorgungskapazität (`supply_base + supply_per_planet`)
  kosten Schiffe Deuterium; Neulinge zahlen nie, nur Veteranen-Großflotten. 4 Tests.
  - **Antimaterie-Sink ✅ FERTIG & getestet:** Megastruktur **`antimatter_forge`**
    (Antimaterie-Schmiede) — kostet Antimaterie, +3 % Angriff/Stufe imperiumsweit
    (Engine-Term `weapons_forge_per_level`, in `combat/service.py` für Angreifer + beide
    Verteidiger-Pfade injiziert). 2 Tests (inkl. Sim). Megastruktur-Engine spendet jetzt
    Dunkle Materie UND Antimaterie.
  - **Offen (Phase 4c):** Sprung-Erschöpfung, Kolossal-Schicht (Flaggschiff-**Aura**/mobile
    Werft/Planetenzerstörer — Aura braucht eigenes Engine-Design), Schiffs-Module/Subsysteme,
    Superwaffen-Verwundbarkeitsfenster. Spec in §5/§6. Bewusst NICHT eilig nachgezogen
    (PvP-Balance-sensibel).

Jede Phase: balance.json + Backend-Verdrahtung + Frontend-Anzeige + Tests + Deploy,
nach dem Dev-Loop in `project_universe_devloop`.

## 8. Kollisions-Hinweis (Parallel-Agent)
`balance.json`, `display.ts`, `api.models.ts`, `platform/migrations.py` werden teils vom
Parallel-Agenten verändert. In fokussierten Häppchen committen, vor balance/migration-
Änderungen `git status` prüfen.
