# Universe — game-server (FastAPI)

Autoritativer, modularer Monolith für das Browser-MMO *Universe*. Alle Spielregeln,
Kosten, Zeiten, Produktion und Kämpfe werden **serverseitig** berechnet; der Client
schickt nur Befehle. Zahlen kommen ausschließlich aus `shared/balance.json`.

## Architektur

```
app/
  main.py                 FastAPI-App, registriert Router unter /api, mountet /ws, startet Scheduler
  ws.py                   WebSocket-Gateway (JWT-Auth, Redis-Subscriber, resource_tick)
  platform/               Querschnitts-Infrastruktur
    config.py             ENV-Settings (DATABASE_URL, REDIS_URL, JWT_SECRET, BALANCE_PATH)
    db.py                 Async-Engine + Session (SQLAlchemy 2.0 / asyncpg)
    models.py             ORM-Modelle, exakt gemappt auf infra/db/init.sql
    security.py           bcrypt-Passwörter, HS256-JWT, get_current_player-Dependency
    balance.py            Loader + typisierte Sicht auf balance.json (gecached)
    eventbus.py           Redis: publish ws:player:{id}, enqueue ai:jobs (degradiert sauber)
    scheduler.py          APScheduler (Abschluss-Jobs + periodische Jobs)
  auth/                   Registrierung (Welt-Setup), Login, /me
  economy/                Lazy-Ressourcen, Produktions-/Energie-Bilanz, Planet-Endpunkte
  buildings/              Gebäudeausbau + Werft (shipyard.py)
  research/               Technologiebaum (genau eine Forschung gleichzeitig)
  fleet/                  Flotte senden/zurückrufen, Anflug-/Rückkehr-Jobs, Sprit/Distanz
  combat/                 engine.py (deterministisch, seeded) + service.py (Auswertung) + Reports
  commander/              Roster, Moral-Bänder, Span, Training, Moral-Drift-Job (USP)
  messaging/              Sofort-Funksprüche (Bank-Lookup, 0 ms), Postfach, Forderungen
  universe/               Galaxie-Ansicht, freie-Zellen-Suche
```

Jede Domäne hat `router.py` (APIRouter), `service.py` (Logik) und `schemas.py` (pydantic).

## Implementierte Endpunkte (api-contract v0.1)

- **Auth**: `POST /api/auth/register`, `POST /api/auth/login`, `GET /api/auth/me`
- **Planet/Wirtschaft**: `GET /api/planets`, `GET /api/planets/{id}`
- **Gebäude**: `GET /api/planets/{id}/buildings`, `POST /api/planets/{id}/buildings/{type}/upgrade`
- **Forschung**: `GET /api/research`, `POST /api/research/{type}/start`
- **Werft**: `GET /api/planets/{id}/shipyard`, `POST /api/planets/{id}/shipyard/build`
- **Flotte**: `GET /api/fleets`, `POST /api/fleets/send`, `POST /api/fleets/{id}/recall`
- **Galaxie**: `GET /api/galaxy/{galaxy}/{system}`
- **Commander**: `GET /api/commanders`, `GET /api/commanders/{id}`, `POST /api/commanders/train`, `GET /api/player/span`
- **Postfach**: `GET /api/transmissions`, `POST /api/transmissions/{id}/read`, `POST /api/transmissions/{id}/decide`
- **Combat-Report**: `GET /api/combat-reports/{id}`
- **WebSocket**: `WS /ws?token=<jwt>` (resource_tick, build_complete, research_complete,
  fleet_arrived/returned, transmission, combat_report)
- **Health**: `GET /health`

## Kern-Mechaniken

- **Lazy-Ressourcen (ADR-002)**: Beim Lesen `amount += rate·Δt`, gedeckelt auf Lager.
  Energie ist Bilanz; bei Defizit drosselt `factor = min(1, produced/consumed)` die Minen.
- **Kosten**: Gebäude `cost·factor^lvl`, Forschung `base·2^(lvl-1)`; Bauzeiten aus balance.json.
- **Kampf (engine.py)**: deterministisch (Seed), ≤6 Runden, Schild-Abprall <1 %,
  Rapidfire-Kette `(rf-1)/rf`, Explosion <70 % Hülle, Moral-/Trait-/Überdehnungs-Modifikatoren,
  Trümmer 30 %, Plünderung 50 % (fracht-begrenzt), Verteidigungs-Regen 70 %, Commander-XP/Moral,
  Evakuierungs-Wurf → Permadeath/Capture (unter Neulingsschutz kein Permadeath).
- **Messaging**: Sofort-Reaktion ohne LLM (Bank-Lookup → Slot-Filling → `transmissions` →
  Redis-Push). Banken leer → Template-Fallback. Entscheidende Schlacht → `big_moment`-Job.

## Lokal starten

Voraussetzung: Python 3.12, ein Postgres mit dem Schema aus `infra/db/init.sql` und ein Redis.

```bash
cd backend
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

export DATABASE_URL="postgresql+asyncpg://universe:universe@localhost:5432/universe"
export REDIS_URL="redis://localhost:6379/0"
export JWT_SECRET="dev-only-change-me"
# BALANCE_PATH ist optional: ohne wird shared/balance.json automatisch gefunden.

uvicorn app.main:app --reload --port 8000
```

Am einfachsten über Compose (startet DB+Redis+Server mit gemountetem `shared/`):

```bash
docker compose -f infra/docker-compose.yml up --build
```

OpenAPI-Doku dann unter `http://localhost:8000/docs`.

## Tests

```bash
cd backend
pytest                      # deterministische Kampf-Engine + Wirtschafts-Formeln
```

Die Smoke-Tests laufen ohne DB/Redis (reine Formel-/Engine-Prüfung).

## Bekannte Einschränkungen / Designentscheidungen (Vertical Slice)

- **Werft-Queue** wird prozess-lokal im Speicher gehalten (kein Queue-Schema in der DB);
  fertige Bauten landen persistent in `ships`/`defenses`, die *Anzeige* der Queue überlebt
  jedoch keinen Server-Neustart.
- **APScheduler-Jobs** liegen im `MemoryJobStore`. Nach einem Neustart laufende Bau-/Flug-Timer
  werden nicht automatisch wiederhergestellt (für die Alpha akzeptiert; ein Recovery-Job, der
  fällige `*_finishes_at`/`arrive_at` beim Start nachzieht, ist der nächste Schritt).
- **Kampf** ist im Slice gegen **NPC-Ziele** (`npc_empires`) ausgelegt; PvP-Verteidigung
  ist rudimentär vorbereitet.
- **Überdehnung**: Zahl der Schiffstypen im Geschwader dient als Proxy für „Geschwader > Span".
- **Fusionsreaktor** erzeugt Energie (Doku-Formel), verbraucht im Slice aber noch kein Deuterium.
- **Sprit-Formel** ist eine begründete Slice-Näherung (`Σ Schiff-Sprit · Distanz / speed_factor`).
- **Grundeinkommen** wird wie die Produktion mit dem Universe-Speed skaliert, aber nicht
  durch das Energiedefizit gedrosselt.
- E-Mail wird als `str` validiert (kein `email-validator`, um Abhängigkeiten schlank zu halten).
- `reaction_banks.embedding`/`flavor_pool.embedding` (pgvector) werden im game-server nicht
  gemappt — die Spalten gehören dem ai-worker.
