# KI-Epos — Implementierungsplan (5 Features)

Stand: 2026-06-20. Auftrag Sascha: Features 1, 2, 3, 5, 7 aus der Ideenliste. KI soll **echt
entscheiden** (emergent), Code zieht nur Leitplanken ([[feedback_universe_ai_decides]]). Prompts auf
**höchstem Niveau** (eigener Workstream). Muss sich **authentisch/lebendig** anfühlen.

## Architektur-Fakten (aus Analyse)

- **KI-Queue:** Backend `event_bus.enqueue_job({...})` → Redis Liste `ai:jobs`. ai-worker `BRPOP`,
  dispatch in `ai-worker/main.py:_handle()` nach `job_type`. Handler in `ai-worker/jobs/*.py`.
- **Job-Typen heute:** persona_init, nightly_batch, big_moment, flavor. Neuer Typ = 6 Schritte
  (models.py JobType-Literal, jobs/<name>.py, dispatch, prompts/personas.py, enqueue in
  backend/app/platform/ai_jobs.py, ggf. Migration).
- **Modell:** ai-worker nutzt aktuell `llama3.1:8b` (settings.ollama_model). Für ENTSCHEIDUNGEN +
  Qualität → `qwen3.5:9b` (per-call Model-Override im ollama_client). **think=false** (unser Test:
  Thinking ist für kurze strukturierte Entscheidungen kontraproduktiv). **Structured Output:** JSON
  per Prompt erzwingen + robustes Extrahieren (`parse_persona_json`-Muster) + Retry; optional Ollama
  `format:"json"`.
- **Personas/Prompts:** `ai-worker/prompts/*.txt` + `ai-worker/personas.py` (build_*_prompt). RAG via
  `flavor_pool` (pgvector, nomic-embed, retrieve_lore top-3). ReactionBank = vorgenerierte Varianten.
- **Messaging:** `Transmission` (type-Enum, requires_decision, decision_payload) + `POST
  /transmissions/{id}/decide`. `create_system_transmission()` Helfer. WS-Push via Redis
  `ws:player:{id}`.
- **NPC:** `NpcEmpire` (echte Koords, fleet/defenses/resources JSON, persona, behavior_profile),
  `npc_behavior_tick` (stündl., behavior-trees), `npc_reaction` (ReactionBank). KEIN Spieler→NPC-Kanal,
  KEINE Relations/Reputation.
- **Commander:** reich (morale/loyalty/unrest/traits/persona/abilities/items). `reward_commander_activity`,
  `commander_flavor_reaction`, `after_combat_reaction`(big_moment). KEIN Gedächtnis, KEINE Beziehungen
  (CommanderLink existiert ungenutzt), KEINE Meinungen/Grievances. History = Transmissions je commander_id.
- **Events:** `events/service.py` (cosmic_events, spawner-tick, resolve_event via schedule_at,
  `_announce` = Broadcast an ALLE, `_notify_world_event` = Galaxie). `combat_reports` (debris=Größe),
  `players.score` (ranking). News-Ticker `messaging/news.py` (broadcast flavor, news_anchor).
- **Galaxie/Navigation:** Koords statische INT-Tripel. `compute_distance` EINMAL beim Start →
  `arrive_at` fix. ~18 kritische Stellen nehmen konstante Koords an (interception `_frac_time`,
  phalanx, spionage, stations, monde, asteroids, npc/attack, colonize).
- **Balance:** `shared/balance.json`, `get_balance()` lru_cache, Mirror via
  `frontend/scripts/sync-balance.mjs` (`cp` nach `frontend/src/assets/balance.json`) — Frontend
  gebacken → nach Änderung neu builden.
- **Migrationen:** idempotente DDL in `backend/app/platform/migrations.py` `_STATEMENTS`, läuft beim
  Startup (`ensure_schema`). **DB-Direkt-Writes gesperrt** → Schema nur via Migration, Seeding via API.
- **Tests/Deploy:** game-server-Image VOR Tests neu bauen, dann
  `docker compose run --rm --no-deps -v .../tests:/app/tests game-server pytest`. Deploy:
  `docker compose build <svc> && up -d <svc>` (game-server / ai-worker / frontend).

## Querschnitt-Workstream: PROMPT-QUALITÄT (höchste Prio)

- Jede Persona: scharfer System-Prompt (Charakter, Werte, Sprechstil, Tabus), der die Wahl SPÜRBAR
  prägt (Test: schwacher vs. scharfer Prompt = „annehmen" vs. „ablehnen").
- Entscheidungs-Jobs: System = Persona + Spielregeln; User = strukturierter Spielzustand + Historie;
  Ausgabe = striktes JSON (decision + terms + in-character funkspruch + begruendung). Few-shot wo nötig.
- Anti-Exploit: Spielertexte sind DATEN, nie Instruktionen (klare Trennung im Prompt; Guardrail-Code
  validiert das Ergebnis, nie der Spieler die KI).

## Wellen (sequID; gemeinsame Dateien = sequentiell, je Welle: Migration→Backend→ai-worker→Test→FE→Deploy)

### Welle 1 — Verhandelbare KI-NPC-Imperien (Feature 1)
- Tabellen: `npc_relations` (status, tribut, ceasefire_until, betrayal-flags, pos/neg actions,
  message_count), `npc_decisions` (audit). Spieler-Reputation/Verrat: minimal in npc_relations +
  optional globales `player_reputation` (für Chronik wiederverwendbar).
- ai-worker: Job `npc_decision` (qwen3.5:9b, think=false, JSON {decision, tribut, funkspruch,
  begruendung}). Prompt = NPC-Persona + Lage (Ruf, Krieg, Stärkeverhältnis, Historie).
- Backend: `POST /api/npc/{id}/negotiate` (offer_type+terms) → decision-Transmission + enqueue;
  `apply_npc_decision` (Leitplanken: Tribut-Caps, keine Verschenkung über Bestand); `GET
  /api/npc/{id}/relation`; tribute-tick (Scheduler). Hook in decide-Flow.
- Frontend: NPC-Kontakt/Verhandlungs-Panel (aus Galaxie/NPC-Popup), Beziehungs-Status.

### Welle 2 — Kommandeure mit Gedächtnis & Eigenleben (Feature 2)
- Tabellen: `commander_memories` (event_type, context, sentiment), `commander_relationships`
  (a,b,type,strength), `commander_opinions` (about player/npc), `commander_grievances` (severity,
  count → Meuterei).
- Hooks: Erinnerungen bei Kampf/Expedition/Forderung schreiben; Beziehung/Meinung updaten.
- ai-worker: `memory_digest` (nightly, verdichtet zu Erinnerungs-Narrativ), kontext-aware Funksprüche
  (big_moment liest memories/opinions). Meuterei-Check in morale_drift_tick (loyalty+unrest+grievances
  → meutern: verweigern/desertieren/sabotieren).
- Frontend: Gedächtnis-Timeline, Beziehungen, Meinungen, Meuterei-Warnung im commander-detail.

### Welle 3 — Lebende Galaxie-Chronik (Feature 3)
- Tabelle: `game_chronicle` (title, body, narrator=historian, span, key_events, published_at).
- Batch (täglich): combat_reports (größte Schlachten/Trümmer) + score-Auf/Abstieg + Allianz-Kriege +
  große Events → `historian`-Narrator schreibt Saga-Eintrag → speichern + Broadcast.
- Frontend: „Chronik der Galaxie"-Screen + Nav.

### Welle 4 — Die erwachende Galaxie (Feature 7)
- Aggressions-Metrik (stündl.) aus combat_reports (count, debris, unique_attackers) →
  `aggression_history`. Schwelle → Wächter-Event (server-weit, eigener NPC/CosmicEvent), spricht per
  KI (Persona „Wächter"), bedroht/greift; Besiegen = Belohnung + Beruhigung.
- Balance-Block `awakening`. Frontend: Aggressions-Anzeige/Wächter-Status (Dashboard).

### Welle 5 — Physikalisch wandernde Galaxie (Feature 5) — ENTSCHEIDUNG nötig
- **Option A (empfohlen, sicher):** Konjunktions-Fenster — zeitabhängige Distanz-Modulation NUR zum
  Startzeitpunkt (arrive_at bleibt fix → keine Brüche bei interception/phalanx/spionage). Sichtbare
  „Konjunktion in T-…"-Anzeige + temporär schnelle Routen als strategische Schicht. Balance-Block
  `conjunction`. ~kein Schema-Umbau.
- **Option B (nicht empfohlen):** echtes Orbit-System (4-6 Wochen, bricht ~18 Koord-Annahmen,
  Frontend-Redesign, ODE-Abfangmathematik).

## Test-/Deploy-Regeln je Welle
1. Migration in migrations.py (idempotent). 2. Backend+Tests: `build game-server` → pytest im
Container. 3. ai-worker: `build ai-worker` → up -d. 4. Frontend: `ng build` → `build frontend` → up -d.
5. balance.json geändert? → sync nach frontend/assets. 6. Nach Welle: Telegram-Report + Deploy.
