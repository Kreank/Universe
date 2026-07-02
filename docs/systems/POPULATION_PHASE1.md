# Bevölkerung & Nahrung — Phase 1

Tester-Idee (Pflanzenextrakt, /dashboard) + Sascha-Freigabe (2026-07-01). Phase 1 = additive
Wirtschafts-Schicht. **Manpower/Crew-Limit (Schiffe brauchen Besatzung) ist bewusst NICHT Teil
von Phase 1** — kommt ggf. als Phase 2.

## Idee in einem Satz
Jeder Planet hat eine **Bevölkerung** (Arbeitskraft), die **Nahrung** braucht. Gut versorgte
Bevölkerung steigert die Minen-Produktion, hungernde schrumpft und bremst sie.

## Zwei neue Ressourcen
- `food` (Nahrung): planetar, mit Lager-Cap. Produziert von der **Farm**. Wird von der
  Bevölkerung verbraucht.
- `population` (Bevölkerung): planetar. Wächst bei Nahrungsüberschuss Richtung Kapazität,
  schrumpft bei Hunger. KEIN klassisches Lager — Kapazität kommt aus dem **Wohnhaus**.

## Zwei neue Gebäude
- `housing` (Wohnhaus): setzt die **Bevölkerungs-Obergrenze** (pop_cap). Kein Rohstoff-Output.
- `farm` (Farm): produziert **Nahrung** pro Tick (wie eine Mine), verbraucht etwas Energie.

## Mechanik (im Lazy-Tick `refresh_resources`, analog zum Exoten-Block)
Pro Refresh, aus dem aktuellen Zustand:
1. `food_production = farm_output * energy_factor` (Farm zählt in die Energiebilanz → ein
   Energie-Defizit drosselt auch die Nahrung, exakt wie bei den Minen).
2. `food_consumption = population * food_per_pop_per_hour`.
3. `food_rate = food_production − food_consumption` (kann negativ sein → Nahrungslager sinkt).
4. **Zufriedenheit** (3 Stufen) aus dem Verhältnis `r = food_production / max(1, food_consumption)`
   und dem Nahrungs-Lagerstand:
   - **satt**: `r ≥ 1 + satt_surplus` → Arbeitskraft **+15 %** auf Minen, Bevölkerung wächst.
   - **neutral**: `1 ≤ r < 1 + satt_surplus` → **0 %**, Bevölkerung stabil.
   - **hungernd**: `r < 1` UND Nahrungslager leer → **−10 %**, Bevölkerung **schrumpft**
     (`starve_rate_per_hour`). Solange noch Nahrung im Lager ist (r<1, Lager>0), zehrt die
     Bevölkerung von den Reserven: kein Wachstum, aber (noch) kein Schrumpf, 0 % Bonus.
5. `population_rate`:
   - hungernd → `−population * starve_rate_per_hour`
   - satt & `population < pop_cap` → Wachstum Richtung pop_cap (`growth_rate_per_hour`, gedeckelt)
   - sonst → 0
6. **Arbeitskraft-Bonus** (`workforce_mult = 1 + workforce_bonus[tier]`) fließt als zusätzlicher
   `production_mult` in die Minen (dieselbe Schiene wie der Gouverneur-Bonus `gov_mult`).

## Kommandeur-Synergie (Phase 1)
Ein als Gouverneur eingesetzter Kommandeur verschiebt die Zufriedenheit über seine
Spezialisierung (`commander_satisfaction_shift[spec]`): wirtschafts-/verwaltungsnahe Archetypen
heben die Zufriedenheit (leichter zu „satt"), militärische senken sie leicht. Der Shift
verändert den Schwellenvergleich in Schritt 4 (additiv auf `r`).

## Planetengröße
Zwei neue Gebäudelinien = mehr Feld-Druck (1 Feld je Gebäude-STUFE). Daher `field_curve` +~15 %
und `homeworld_min_fields` 190 → 220. `backfill_planets()` zieht beim Neustart alle bestehenden
Planeten nach (schrumpft nie unter `fields_used`).

## Balance-Startwerte (tunebar)
`population`-Block in balance.json:
- `food_per_pop_per_hour: 0.05`
- `growth_rate_per_hour: 0.03`, `starve_rate_per_hour: 0.06`
- `satt_surplus: 0.20`
- `workforce_bonus: { satt: 0.15, neutral: 0.0, hungernd: -0.10 }`
- `food_base_cap: 20000`, `food_cap_per_farm_level: 8000`
- `commander_satisfaction_shift`: pro Spezialisierung (Default 0)

`housing`: `pop_cap_base: 500`, `pop_cap_growth: 1.1`, Energie leicht.
`farm`: `food_prod_base: 60`, `food_prod_growth: 1.1`, Energie leicht.

## Assets
Neue Gebäude-Bilder `housing.png` + `farm.png` via Codex (stiltreu, Anker
metal_mine/solar_plant/trade_center). Ressourcen-Icons `population`/`food` vorerst per Glyph
(👥 / 🌾), echte Icons später.
