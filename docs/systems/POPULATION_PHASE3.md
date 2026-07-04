# Bevölkerung Phase 3 — Automatisierungs- & Habitattechnik (2026-07-04)

Zwei Forschungen schaffen Spieler-Identität über das Bevölkerungs-System
(Phase 1: `POPULATION_PHASE1.md`, Phase 2: `CREW_PHASE2.md`). Sascha-Freigabe 2026-07-04.
Beide Wege konkurrieren um Forschungszeit und -kosten.

## 🤖 Automatisierungstechnik (`automation_tech`) — der Fleeter-Weg

Roboter ersetzen Crew: **−`automation_crew_reduction_per_level` (5 %) Crew-Bedarf je Stufe**
beim Flotten-Losschicken, Untergrenze **`automation_crew_floor` (40 %)** des Normalbedarfs.

- Reduktion auf der **Summe** der Flotten-Crew (nicht je Schiff gerundet) →
  `economy.fleet_crew(ships, automation_level)` via `automation_crew_mult(level)`.
- Konsistent an allen Crew-Punkten: Abzug beim Start (`fleet.send_fleet`), Deckel-Gutschrift
  bei Rückkehr (`fleet_return`), Landung (`stationing._land_at_own_planet`) und
  Station-Heimkehr (`_send_station_home`) — sonst käme bei Teilverlusten mehr Crew heim,
  als anteilig mitflog.
- Voraussetzungen: Forschungslabor 6, Computertechnik 6.

## 🏙️ Habitattechnik (`habitat_tech`) — der Miner-Weg

Mehr Menschen, mehr Produktion:

1. **+`habitat_pop_cap_per_level` (8 %) Wohnhaus-Kapazität je Stufe** — hebt NUR den
   Wohnhaus-Beitrag, nicht die Grund-Bevölkerung (`population_capacity(buildings, habitat_level)`).
2. **+`habitat_satt_bonus_per_level` (1 %-Punkt) „satt"-Arbeitskraft-Bonus je Stufe**,
   Cap `habitat_satt_bonus_max` (15 Punkte → max. +30 % statt +15 %). Nur im Tier „satt" —
   hungernde Bevölkerung profitiert nicht (`habitat_satt_bonus` + `population_dynamics`-Param
   `satt_workforce_extra`).
- Tradeoff bleibt: mehr Bevölkerung isst mehr → mehr Farmen → Felder-Konkurrenz.
- Voraussetzungen: Forschungslabor 5, Wohnhaus 5.

## Frontend

- Forschungs-Screen: `automation_tech` unter „Kommandeure & Flotte", `habitat_tech` unter
  „Wirtschaft & Ausbau" (`research.component.ts` CATEGORY_ORDER); Meta in
  `core/models/display.ts` (TECH_META + TECH_EFFECTS).
- Flotten-Versand (`fleet-dispatch.component.ts`): Crew-Anzeige spiegelt die Reduktion
  (`automationCrewMult`, Werte aus `balance.research.effects`), Anzeige aufgerundet.
- Icons: `assets/img/tech/{automation_tech,habitat_tech}.png` (Codex); bis dahin Emoji-Fallback.

## Balance-Knöpfe (`shared/balance.json`)

`research.effects`: `automation_crew_reduction_per_level` 0.05 · `automation_crew_floor` 0.4 ·
`habitat_pop_cap_per_level` 0.08 · `habitat_satt_bonus_per_level` 0.01 · `habitat_satt_bonus_max` 0.15.
Kosten/Voraussetzungen in `research.techs`.

Tests: `backend/tests/test_population_phase3.py` (6, rein funktional).
