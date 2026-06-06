# Universe 🚀

> Browserbasiertes Weltraum-Aufbau-MMO in der Tradition von OGame — mit **persistentem
> Universum (kein Reset)** und **lebendigen KI-Crews** (Commander mit Moral & LLM-Funksprüchen)
> als Alleinstellungsmerkmalen.

Dieses Repository enthält den **Vertical Slice (v0.1)**: den kleinsten durchgängigen Loop
durch den **kompletten** Stack — Angular → FastAPI → PostgreSQL → Redis → AI-Worker → Ollama.

📖 **Design:** Die vollständige Spiel- und Technik-Doku liegt unter [`docs/`](./docs/)
([GDD](./docs/GAME_DESIGN_DOCUMENT.md) · [Architektur](./docs/ARCHITECTURE.md) ·
[Design-Decisions](./docs/DESIGN_DECISIONS.md) · [Assets](./docs/ASSETS.md) ·
[Style-Bible](./docs/STYLE_BIBLE.md)).

---

## Architektur (Kurzfassung)

```
Angular SPA ──REST/WS──▶ game-server (FastAPI, autoritativ) ──▶ PostgreSQL + pgvector
                                  │                          └──▶ Redis (Queue + Pub/Sub)
                                  │                                      │
                                  └── enqueue KI-Jobs ──▶ ai-worker ──▶ Ollama (lokal, GPU)
```

Die **zwei harten Grenzen**: Der Client ist „dumm" (alle Regeln serverseitig, ADR-006);
der Game-Tick wartet **nie** auf das LLM (KI vollständig über Redis entkoppelt, ADR-003).
Details: [ARCHITECTURE.md](./docs/ARCHITECTURE.md).

| Komponente | Tech | Ordner |
|-----------|------|--------|
| Frontend | Angular (standalone, SCSS) + nginx | [`frontend/`](./frontend) |
| Game-Server | Python · FastAPI · SQLAlchemy async · APScheduler | [`backend/`](./backend) |
| AI-Worker | Python · Redis-Consumer · Ollama-Client · pgvector | [`ai-worker/`](./ai-worker) |
| Datenbank | PostgreSQL 16 + pgvector | [`infra/db/init.sql`](./infra/db/init.sql) |
| Queue/Cache | Redis 7 | — |
| LLM | Ollama (7–8B Q4, lokal) | — |
| Balance/Contracts | Single Source of Truth | [`shared/`](./shared) |

---

## Schnellstart (Docker)

**Voraussetzungen:** Docker Desktop (Compose v2+). Für die KI-Funksprüche optional ein
lokaler [Ollama](https://ollama.com).

```bash
# 1) Env anlegen
cp infra/.env.example infra/.env        # ggf. JWT_SECRET anpassen

# 2) Gesamten Stack bauen & starten
docker compose -f infra/docker-compose.yml up --build

# 3) Öffnen
#    Frontend:  http://localhost:4200
#    API-Docs:  http://localhost:8000/docs   (FastAPI Swagger)
```

Beim ersten Start legt PostgreSQL automatisch das Schema an
([`infra/db/init.sql`](./infra/db/init.sql)) inkl. einiger NPC-Ziele zum Angreifen.

### KI-Funksprüche aktivieren (optional)
Der AI-Worker veredelt Commander-Funksprüche per LLM. Ohne Ollama läuft das Spiel voll
(Template-Fallback + vorgefüllte Banken decken alle Sofort-Reaktionen — ADR-003). Für die
volle Pipeline auf dem Host:

```bash
ollama pull llama3.1:8b          # Generierung (Dialog)
ollama pull nomic-embed-text     # Embeddings (Dedup/RAG, 768-dim → vector(768))
```
Der Worker spricht standardmäßig den **Host-Ollama** via `host.docker.internal:11434` an
(konfigurierbar in `infra/.env`). Alternativ Ollama als Container mitstarten:
`docker compose -f infra/docker-compose.yml --profile ollama up`.

---

## Der Vertical-Slice-Loop (was funktioniert)

1. **Registrieren** → Heimatplanet + Start-Ressourcen + 1 Start-Commander.
2. **Wirtschaft**: Minen/Solar ausbauen → Ressourcen wachsen *lazy* (Rate × Δt), Energie
   drosselt bei Defizit. Bauzeiten als geplante Jobs.
3. **Forschung** (eine gleichzeitig) und **Werft** (Schiffe bauen).
4. **Flotte** mit Commander auf ein **NPC-Ziel** schicken (Angriff).
5. **Kampf** wird autoritativ aufgelöst (6 Runden, Rapidfire, Schild-Abprall, Moral-Mod) →
   Combat-Report, Beute, Trümmer, **Commander-Moral/XP** verschieben sich.
6. **Funkspruch**-Pipeline: Event → Bank-Lookup → Slot-Filling → Postfach + WS-Push
   (0 ms, kein LLM). Großmomente werden vom AI-Worker per LLM „nachgereicht".

Diese Kette ist **end-to-end verifiziert** (siehe [VERIFICATION](#verifikationsstatus)).

---

## Lokale Entwicklung (ohne Docker)

- **Backend:** siehe [`backend/README.md`](./backend/README.md) (FastAPI + uvicorn).
- **Frontend:** siehe [`frontend/README.md`](./frontend/README.md) (`npm start`, Dev-Proxy
  zu `localhost:8000`).
- **AI-Worker:** siehe [`ai-worker/README.md`](./ai-worker/README.md).
- **Balance-Werte** leben zentral in [`shared/balance.json`](./shared/balance.json) — Backend
  und Frontend laden diese Datei, nichts wird hartkodiert.

---

## Verifikationsstatus (Stand 2026-06-06)

End-to-end gegen den laufenden Docker-Stack geprüft:

- ✅ DB-Schema (16 Tabellen), pgvector + pgcrypto, NPC-Seeds laden automatisch.
- ✅ Backend bootet, Scheduler + stündlicher Moral-Job laufen.
- ✅ Auth (Register/Login/JWT), Lazy-Ressourcen + Energie-Drossel, Start-Commander mit Persona.
- ✅ Gebäude-Upgrade, Forschungs-/Werft-Validierung, Flotten-Slots/Sprit, Span-Berechnung.
- ✅ **Voller Kampf-Loop**: Flotte → Kampf (`crushing_victory`) → Beute → Combat-Report →
  Commander Moral 60→76, XP 100→165 → **Funkspruch** im Postfach (Slot-Filling).
- ✅ **Scheduler-Recovery**: offene Timer überleben einen Server-Neustart (DB-basiert).
- ✅ Backend-Unit-Tests grün (8/8: Kampf-Engine deterministisch, Wirtschaft).
- ✅ Frontend baut & serviert die SPA, nginx proxyt `/api` + `/ws` zum Backend.
- ✅ AI-Worker konsumiert Jobs; ohne passende Ollama-Modelle **degradiert er sauber**
  (Jobs zurückgestellt, kein Crash — ADR-003).
- ⏳ LLM-Veredelung live: benötigt `ollama pull llama3.1:8b` + `nomic-embed-text`.

---

## Out of Scope (v1)

Allianzen, voller PvP, NPC-Verhalten (Behavior Trees), prozedurale Galaxien, Saisons,
Markt/Handel, mobile native App. → spätere Meilensteine (siehe GDD §13).
