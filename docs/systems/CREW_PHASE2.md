# Crew / Manpower — Phase 2

Aufbau auf Phase 1 (`POPULATION_PHASE1.md`). Sascha-Freigabe 2026-07-02.

## Idee in einem Satz
Schiffe zu **bauen** ist unverändert — aber eine Flotte **loszuschicken** braucht **Crew**
(= Bevölkerung) vom Start-Planeten. Das begrenzt die einsetzbare Flotten-Größe natürlich
über die Bevölkerung.

## Crew-Lebenszyklus
- **Start** (`send_fleet`): Summe der Crew aller mitfliegenden Schiffe wird als `population`
  vom START-Planeten abgezogen. Reicht die Bevölkerung nicht → Start blockiert (wie zu wenig
  Deut). Der Wert wird als `mission_data.embarked_crew` gemerkt.
- **Heile Rückkehr** (`fleet_return`): der ZIEL-/Heimatplanet bekommt Crew gutgeschrieben —
  gedeckelt auf `min(embarked_crew, Crew der ÜBERLEBENDEN Schiffe)`. Verlorene Schiffe →
  ihre Crew ist weg. Der Deckel verhindert, dass **gekaperte** Schiffe Gratis-Bevölkerung geben.
- **Einbahn / Stationieren am eigenen Planeten** (`_land_at_own_planet`): Crew der gelandeten
  Schiffe geht in die ZIEL-Planeten-Bevölkerung (Sascha-Entscheid Q3).
- **Stationierte Flotte** (intercept/escort/deploy an fremdem Ort): Crew bleibt abgezogen,
  bis die Flotte zurückgerufen wird → dann normale Rückkehr-Gutschrift.
- **Flotte komplett verloren / gekapert**: keine Rückkehr → Crew endgültig tot. (Gefängnis/
  Bekehren = evtl. später, offen.)

## Welche Schiffe brauchen Crew
**Alle** außer den autonomen: `spy_probe`, `solar_satellite`, `drone` (= 0 Crew).
Crew-Werte grob proportional zu Größe/Kosten (Jäger wenig, Kapitalschiffe viel). Als Map
`population.crew` in balance.json (nicht in jedem Schiff-Block) — leicht tunebar.

## Grund-Bevölkerung (Rollout-Fundament)
Damit Phase 2 bestehende Spieler / frische Kolonien nicht vom Flottenversand aussperrt und
JEDER Planet sichtbar Bevölkerung hat (Tester-Feedback): jeder Planet hat eine **Grund-
Bevölkerung** `base_pop`.
- `pop_cap = base_pop + Wohnhaus-Beitrag` (Wohnhaus hebt die Obergrenze über die Basis).
- Bevölkerungs-Zeile wird bei erstem Refresh mit `amount = base_pop` angelegt (existierende
  Planeten ziehen so automatisch nach — kein separater Backfill nötig).
- **Subsistenz**: nur Bevölkerung ÜBER `base_pop` isst Farm-Nahrung und kann verhungern;
  die Basis ernährt sich selbst. Starvation schrumpft die Bevölkerung nie unter `base_pop`.
- **Recovery**: sinkt die Bevölkerung unter `base_pop` (z. B. Crew im Kampf verloren), wächst
  sie ohne Farm langsam wieder auf `base_pop` (natürliche Wiederbesiedlung).
- Crew darf aus der GESAMTEN Bevölkerung schöpfen (auch der Basis) — man kann „alle
  losschicken"; kehren sie heil zurück, ist die Bevölkerung wieder da.

## Kopplung zu Phase 1 (gewollt)
Bevölkerung ist zugleich Arbeitskraft für die Minen. Ist eine Flotte unterwegs, fehlt ihre
Crew auf dem Planeten → Minen-Produktion sinkt kurzzeitig (weniger Arbeiter), bis sie
zurückkehrt. Bewusster Tradeoff (Sascha-Entscheid Q1).

## Balance-Startwerte (tunebar)
- `population.base_pop = 200` (Grund-Bevölkerung/Floor je Planet)
- `population.base_recovery_rate_per_hour = 0.05`
- `population.crew`: Map ship_type→Crew (autonome fehlen ⇒ 0). Startwerte grob:
  small_cargo 2, large_cargo 6, recycler 8, colony_ship 20, miner 5, expedition_ship 15,
  deep_scout 3, light_fighter 2, heavy_fighter 4, cruiser 8, battleship 20, battlecruiser 30,
  bomber 25, destroyer 40, deathstar 2000, interceptor 3, escort_frigate 10, shield_tender 12,
  carrier 50, interdictor 60, warp_stabilizer 15, ewar_frigate 10, boarder 20,
  stealth_corvette 6, harvest_titan 80, flagship 200, corsair 15, tanker 12, trade_leviathan 40.
  Mk2-Varianten = wie Basis.

## Phase 3 (geparkt, mit Sascha abzustimmen)
Automatisierungs-Forschung (Roboter senken Crew-/Arbeiter-Bedarf) + Gegen-Forschung
(mehr Bevölkerung/Produktion) → Spieler-Identität Miner/Fleeter/Händler.

## Frontend
Flotten-Versand-Dialog (`fleet-dispatch`): Crew-Bedarf der Auswahl anzeigen + gegen die
verfügbare Bevölkerung des Start-Planeten prüfen; „Losschicken" sperren bei zu wenig Crew.
