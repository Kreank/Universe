# 🌌 Game-Events / Quests — Design & Architektur

> Stand 2026-06-16. Dynamische Welt-Events + persönliche Events, die Minern Sinn geben,
> Ressourcen/Schiffe verbrauchen (Anti-Stagnation) und Geschichten erzeugen.
> **Grundprinzip: ALLES offline-sicher** — keine Live-Reaktion nötig; Entscheidungen laufen
> async übers Postfach mit Timeout-Default.

## Fundament (einmal bauen, alle Events docken an)

### 1. `event_buffs` — generisches temporäres Buff/Debuff-System
Spalten: `id, source_event_id?, scope ('player'|'planet'|'system'), player_id?, planet_id?, galaxy?, system?, buff_type, magnitude, expires_at, created_at`.
- Service `app/events/buffs.py`: `apply_buff(...)`, `buff_mult(session, buff_type, scope, ...)` (multiplikativ), `buff_sum(...)` (additiv), `is_blocked(...)` (bool).
- 7 Integrationspunkte (chirurgisch, je 1–3 Zeilen):
  - Produktion: `economy/service.py` compute_rates `production_mult` (Minen-Streik 0.5, Anomalie-Malus).
  - Bauzeit: `buildings/service.py` build_seconds (Flüchtlinge +Bau-Tempo).
  - Forschung: `research/service.py` research_seconds (Anomalie +Forschungstempo).
  - Moral: `commander/service.py` morale (Flüchtlinge +, Streik-Gewalt −).
  - Phalanx: `fleet/phalanx.py` (Sonnensturm: scan_block).
  - Spionage: `universe/spionage.py` (Sonnensturm: spionage_block).
  - (Energie/Schild später bei Schwarzmarkt-Buffs.)

### 2. `cosmic_events` — Welt-/Karten-Events mit Lebensdauer
Spalten: `id, event_type, scope, galaxy?, system?, position?, player_id?, data JSONB, status ('active'|'resolved'|'expired'), spawned_at, expires_at, created_at`.
- Galaxie-Overlay wie Asteroidenfelder (blockiert die Zelle NICHT) → neues `CellOut.event`-Feld.
- Spawner-Tick `spawn_cosmic_events()` (idempotent, hält Ziel-Dichte je Typ; balance.events).
- Ablauf-Job via `schedule_at(expires_at, resolve_event, id)`; Recovery in `recover_pending_jobs`.

### 3. Async-Entscheidung (offline-sicher)
- Event-Entscheidung = Transmission mit `requires_decision=True` + `decision_payload={event_type, event_id, choices, default_choice, timeout_at}`.
- Neuer Endpoint `POST /api/events/decide {transmission_id, choice}` → dispatch nach `event_type`.
- `schedule_at(timeout_at, apply_event_default, transmission_id)` wendet bei Nichtreaktion die Default-Wahl an. Decide canceltden Timeout-Job. Recovery stellt Timeouts wieder her.

## Events

### Wave 1 — Quick Wins (max. Wiederverwendung)
1. **Piraten-Razzia** — skalierter NPC-Angriff (`maybe_launch_attack`/`effective_tier`) auf einen Spielerplaneten, Vorwarnzeit, Sieg → Trümmer. Persönlich, offline-sicher (Verteidigung kämpft automatisch).
2. **Wissenschaftlicher Durchbruch** — Postfach-Geschenk: +1 Forschungsstufe ODER nächstes Upgrade −50 %. Instant, keine Entscheidung nötig.
3. **Minen-Streik** — Produktions-Debuff (Buff 0.5/12h) + Entscheidung: Deuterium zahlen (sofort beenden) ODER Gewalt (Moral −). Offline → Default = aussitzen.
4. **Expeditions-Doktrin + Geisterschiff** — Doktrin (vorsichtig/risikofreudig) vor Start in `mission_data`; Geisterschiff = Entscheidung bei Ankunft, Default nach Doktrin. Schwarzes-Loch-Outcome erweitern.
5. **Schwarzes-Loch-Phänomen** — temporäres Wurmhol-Karten-Event: kurze Expeditions-Flugzeit, 3× Ertrag, 15–20 % Totalverlust.

### Wave 2 — Karten-Events (Galaxie)
6. **Wandernder Komet** — temporäres, abbaubares Feld (wie Asteroid) mit hohem Deuterium/Kristall, läuft ab → Wettrennen.
7. **Kosmische Anomalie** — Zone: Forschungssonde/Expedition hinschicken → temp. research_speed-Buff (Risiko leichte Beschädigung).
8. **Schwarzmarkt** — temporäres NPC-Handelszentrum mit Sonderkursen + Buff-Tausch (wie `ensure_trade_centers`).
9. **Flüchtlings-Flottille** — Deuterium spenden → +Moral/+Bau-Tempo (Buff); nach 12 h NPC-Verfolger-Welle; Abwehr → behaltbare Zivil-Transporter.
10. **Sonnensturm** — System geblendet (scan_block + spionage_block Buffs) für 24 h, 12 h Vorankündigung.
11. **Super-Frachter-Wrack** — verteidigt durch NPC-Drohnen; erst Drohnen besiegen → dann für Mining/Recycler frei (riesige Beute).
12. **Utopia-Werft** — globale Ressourcen-Auktion per Transport; Top-3-Lieferer in 48 h → einzigartiges Flaggschiff (neuer Schiffstyp).

## Phasen / Reihenfolge des Baus
1. Fundament (Buffs, cosmic_events, async-decision, Recovery, Spawner-Tick, balance.events).
2. Buff-Integrationspunkte verdrahten.
3. Wave 1 (persönliche + Expeditions-Events) + Frontend (Postfach-Entscheidungen, Doktrin-Auswahl).
4. Wave 2 (Karten-Events) + Frontend (Galaxie-Event-Chips/Aktionen, Countdown).
5. Balance, Tests, Deploy, Render-Checks.

## Offene Balance-Regler (balance.json -> events)
Spawn-Häufigkeit je Typ, Lebensdauer, Belohnungen, Debuff-Stärke, Streik-Bestechungskosten, Komet-Vorrat, Schwarzloch-Risiko, Flüchtlings-Welle-Stärke, Utopia-Lieferschwelle. Default: **selten & besonders**.
