# Architektur-Dokument — *Universe*

> **Status:** v0.1 · **Stand:** 2026-06-06 · Ergänzt das [Game Design Document](./GAME_DESIGN_DOCUMENT.md).
>
> Beschreibt *wie* das Spiel technisch gebaut wird: Service-Grenzen, Modularität,
> Datenflüsse, DB-Schema-Grundriss, Skalierungspfad und die wichtigsten
> Architektur-Entscheidungen (ADRs). Lebendes Dokument.

---

## 1. Leitprinzipien

1. **Modularer Monolith + entkoppelte Services.** Die Spiel-Logik liegt als *ein*
   gut getrennter Dienst vor (einfach für Solo-Dev), aber alles Asynchrone/KI-Lastige
   ist über Queues hart entkoppelt. Eine einzige Codebasis (Monorepo), klare Modulgrenzen.
2. **Der Game-Tick darf nie auf KI warten.** Die LLM-Schicht ist vollständig
   asynchron. Fällt der AI-Worker aus, läuft das Spiel normal weiter (Templates +
   vorgefüllte Banken decken alle Sofort-Reaktionen).
3. **Autoritativer Server.** Der Client ist „dumm": er zeigt an und schickt Befehle.
   Jede Spielregel/Validierung passiert serverseitig. (Cheat-Schutz, MMO-Pflicht.)
4. **Lazy-Berechnung statt Dauer-Ticking.** Ressourcen werden *bei Bedarf* aus
   Rate × verstrichener Zeit berechnet, nicht jede Sekunde für jeden Planeten
   hochgezählt (siehe ADR-002). Nur *diskrete* Ereignisse (Bau fertig, Flotte
   angekommen) werden geplant ausgelöst.

---

## 2. System-Überblick

```
                         ┌──────────────────────────┐
                         │   Angular SPA (Frontend)  │
                         │   nginx, REST + WebSocket │
                         └─────────────┬─────────────┘
                                       │ REST (Aktionen) + WS (Live-Updates)
                                       ▼
        ┌──────────────────────────────────────────────────────────┐
        │                  GAME-SERVER  (FastAPI)                    │
        │            autoritativ · modularer Monolith               │
        │  ┌────────┐ ┌──────┐ ┌─────────┐ ┌────────┐ ┌──────────┐  │
        │  │economy │ │fleet │ │combat   │ │commander│ │universe │  │
        │  └────────┘ └──────┘ └─────────┘ └────────┘ └──────────┘  │
        │   + auth · WS-Gateway · Tick/Scheduler (Jobs)             │
        └───────┬───────────────────────┬──────────────────┬───────┘
                │ liest/schreibt         │ enqueue / pub    │ enqueue
                ▼                        ▼                  ▼
        ┌───────────────┐        ┌─────────────┐    (Job: Großmoment /
        │  PostgreSQL   │        │    Redis    │     Nacht-Batch)
        │  + pgvector   │◄──────►│ Queue+PubSub│          │
        └───────▲───────┘        └──────┬──────┘          │
                │                        │ subscribe       ▼
                │ schreibt Banken/       │          ┌──────────────┐
                │ Funksprüche            └─────────►│  AI-WORKER   │
                │                                   │  (Python)    │
                └───────────────────────────────────┤  ruft Ollama │
                                                    └──────┬───────┘
                                                           ▼
                                                    ┌──────────────┐
                                                    │   Ollama     │
                                                    │ (lokal, GPU) │
                                                    └──────────────┘
```

---

## 3. Services (Container) & Verantwortlichkeiten

| Service | Tech | Verantwortung | Was es NICHT tut |
|---------|------|---------------|------------------|
| **frontend** | Angular + nginx | UI, sendet Befehle (REST), empfängt Live-Updates (WS) | keine Spielregeln |
| **game-server** | Python / FastAPI | Autoritative Logik, Auth, REST-API, WS-Gateway, Tick/Scheduler, publiziert Events, **enqueued** KI-Jobs | ruft **nie** das LLM direkt/synchron |
| **ai-worker** | Python | konsumiert KI-Jobs (Nacht-Batch + Großmomente), ruft Ollama, dedupliziert (pgvector), schreibt Banken/Funksprüche, pusht Follow-ups | keine Spielregeln, kein direkter Client-Kontakt |
| **postgres** | PostgreSQL + pgvector | Single Source of Truth: Spielstand, Commander-Personas, Reaktions-Banken, Embeddings | — |
| **redis** | Redis | Job-Queue (Combat→KI), Pub/Sub (WS-Fan-out), Cache | keine dauerhafte Wahrheit |
| **ollama** | Ollama | lokale LLM-Inferenz (7–8B Q4) | — |

**Die eine harte Grenze, die zählt:** `game-server` ↔ `ai-worker` kommunizieren
**ausschließlich** über Redis (Jobs) und PostgreSQL (Ergebnisse). Nie direkter Aufruf.
Das hält LLM-Latenz komplett aus dem Spiel-Pfad heraus (ADR-003).

---

## 4. Modulgrenzen im Game-Server (modularer Monolith)

Ein FastAPI-Dienst, aber innen in **Domänen-Module** mit klaren Schnittstellen geteilt.
Module reden über definierte Service-Funktionen/Events, **nicht** quer über fremde Tabellen.

| Modul | Zuständig für |
|-------|---------------|
| `auth` | Konten, Login, Sessions/JWT |
| `economy` | Ressourcen (Lazy-Calc), Gebäude, Energie, Lager |
| `research` | Technologiebaum, Forschungsaufträge |
| `fleet` | Schiffe, Flottenbewegung, Reisedauer, Treibstoff |
| `combat` | Kampfauflösung, Beute, Trümmerfelder → erzeugt **Reaktions-Events** |
| `commander` | Commander, Traits, Moral, Span-of-Control, Befehlskette, Forderungen |
| `universe` | Galaxien/Systeme/Positionen, Frontier-Expansion, Decay |
| `messaging` | Postfach/Funksprüche, Bank-Lookup + Slot-Filling, WS-Push |
| `platform` | gemeinsame Basis: DB-Zugriff, Scheduler, Event-Bus, Config |

> Wenn ein Modul später unabhängig skalieren muss, lässt es sich an seiner Schnittstelle
> als eigener Dienst herauslösen — ohne den Rest umzubauen. Genau dafür die saubere Grenze.

---

## 5. Datenflüsse

### 5.1 Spieler-Aktion (synchron)
```
Angular ──REST──▶ game-server: validiert ▶ schreibt PostgreSQL ▶ Antwort
```
Ressourcenstand wird beim Lesen *lazy* berechnet (Rate × Δt seit last_updated).

### 5.2 Live-Update (asynchron, Push)
```
game-server ──publish──▶ Redis Pub/Sub ──▶ WS-Gateway ──▶ betroffene Clients
```
(z. B. „Bau fertig", „Flotte angekommen", neuer Funkspruch.)

### 5.3 Combat → Sofort-Reaktion des Commanders (0 ms, KEIN LLM)
```
combat löst Kampf auf
  └▶ messaging: passende Zeile aus Reaktions-Bank des Commanders holen
       └▶ Slot-Filling (Feind/Planet/Beute einsetzen)
            └▶ Funkspruch speichern + via WS pushen        ◀── sofort sichtbar
  └▶ (optional) Großmoment-Job in Redis enqueuen
```

### 5.4 Großmoment (optional, Sekunden später, MIT LLM)
```
ai-worker zieht Job aus Redis
  └▶ RAG-Kontext aus pgvector (Persona, Lore, Spielsituation)
       └▶ Ollama generiert einen kontextbezogenen Funkspruch (2–5 s)
            └▶ Embedding-Dedup (kein Wiederholen)
                 └▶ in PostgreSQL speichern ▶ via Redis/WS als „vollständiger Bericht" nachpushen
```

### 5.5 Nächtlicher Batch (GPU idle)
```
Scheduler triggert Nacht-Job ▶ Redis ▶ ai-worker:
  • pro Commander Reaktions-Banken (neu)füllen (Sieg/Niederlage/Meuterei/…)
  • Flavor-Pool rotieren (alte löschen, neue erzeugen)
  • Lore/Anomalie-Texte vorgenerieren & cachen
  • langsame Inhalte (gelangweilte Crew nach Inaktivität)
```

---

## 6. Tick / Zeit-Modell (wichtig)

Kein „jede Sekunde alles hochzählen" (das skaliert nicht auf viele Planeten). Stattdessen:

- **Ressourcen:** *lazy*. Gespeichert werden `menge`, `rate`, `last_updated`.
  Beim Lesen/Schreiben: `menge += rate × (now − last_updated)`, gedeckelt auf Lager.
- **Diskrete Ereignisse:** als geplante Jobs (Bau fertig um T, Flotte kommt an um T).
  Eine Scheduler-Komponente (z. B. APScheduler / Redis-basierte Delayed Jobs) feuert sie.
- **Periodische Wartung:** Moral-Drift, Inaktivitäts-Decay, Frontier-Expansion als
  seltene Cron-Jobs (z. B. stündlich/täglich).

→ Server-Last hängt an *Aktivität & Ereignissen*, nicht an der Zahl der Planeten.

---

## 7. DB-Schema — Grundriss (v0.1, wird verfeinert)

Nur die Kern-Entitäten und wichtigsten Felder. PK = Primärschlüssel, FK = Fremdschlüssel.

- **players**(id, email, pw_hash, created_at, last_active, score)
- **planets**(id, FK player, galaxy, system, position, name, fields_used/max)
- **resources**(FK planet, type[metal|crystal|deut|energy], amount, rate, last_updated)
- **buildings**(FK planet, type, level, upgrade_finishes_at?)
- **research**(FK player, type, level, finishes_at?)
- **fleets**(id, FK player, origin, target, mission, depart_at, arrive_at, FK commander?)
- **ships**(FK fleet|planet, type, count)
- **commanders**(id, FK player, name, **persona** JSONB, **traits** JSONB,
  specialization, **morale** int, span_capacity, status[active|wounded|captured|dead?])
- **commander_links**(FK superior_commander, FK subordinate_commander) — Befehlskette
- **reaction_banks**(id, FK commander, situation, template_text, **embedding** vector,
  used bool, created_at) — die „Munition"
- **flavor_pool**(id, scope, text, embedding vector, week_tag) — Ebene-3-Inhalte
- **transmissions**(id, FK player, FK commander?, body, type, requires_decision bool,
  read bool, created_at) — Postfach des Spielers
- **combat_reports**(id, attacker, defender, location, outcome JSONB, loot JSONB, created_at)
- **universe_cells**(galaxy, system, position, occupant_type[empty|player|npc|debris], FK ref)
- **npc_empires**(id, behavior_profile, …) — Verhalten via Behavior Trees, kein LLM
- **alliances**(id, name, …) + **alliance_members**(FK alliance, FK player, rank)

> `embedding`-Spalten (pgvector) auf `reaction_banks` und `flavor_pool` ⇒ Dedup
> (kein Commander wiederholt sich) und RAG-Kontext bei Live-Generierung (ADR-004).

---

## 8. Skalierungspfad (von Dev-Box zu „echt")

| Stufe | Setup | Tragfähig für |
|-------|-------|---------------|
| **0 – Dev/Alpha** | alles auf der 3070-Box, ein `docker compose` | Dutzende gleichzeitige Spieler (LLM-Events selten) |
| **1 – kleine Live** | game-server horizontal hinter LB, Redis für WS-Fan-out, Postgres mit Backups | Hunderte |
| **2 – Wachstum** | LLM auf dedizierte/dickere GPU **oder** API-Fallback (Cloud-LLM für Großmomente, lokal für Nacht-Batch); Postgres Read-Replicas | Tausende |
| **3 – groß** | lastreiche Module (combat/universe) als eigene Dienste herauslösen; Sharding der Galaxien | viele Tausende |

Wichtig: Die Architektur erzwingt **keine** dieser Stufen vorab. Die Modulgrenzen (§4)
und die Queue-Entkopplung (§3) machen den Übergang möglich, ohne Neubau.

---

## 9. Architektur-Entscheidungen (ADR-Index)

Kurzfassung. Größere Änderungen je als eigenes ADR-File unter `docs/adr/` ablegen.

- **ADR-001 — Modularer Monolith für die Spiel-Logik.** Solo-Dev: eine Codebasis,
  klare Modulgrenzen. Microservices erst, wenn ein Modul es nachweislich braucht.
- **ADR-002 — Lazy-Ressourcen + geplante Ereignisse.** Kein Dauer-Ticking; Last hängt
  an Aktivität, nicht an Objektzahl.
- **ADR-003 — KI vollständig entkoppelt über Queue.** Game-Tick wartet nie auf das LLM;
  AI-Worker-Ausfall ist unkritisch (Templates + Banken decken Sofort-Reaktionen).
- **ADR-004 — pgvector für Dedup + RAG.** Funkspruch-Wiederholung vermeiden,
  Persona/Lore-Kontext für Live-Generierung liefern.
- **ADR-005 — Monorepo, modular.** Ein Git-Repo, intern strikt getrennte Module/Services.
- **ADR-006 — Autoritativer Server, dummer Client.** Alle Regeln serverseitig.

---

## 10. Vorgeschlagene Repo-Struktur (Monorepo, modular)

```
universe/
├── docs/                  # GDD, dieses Dokument, ADRs
│   └── adr/
├── infra/                 # docker-compose.yml, .env.example, init-sql, nginx
├── backend/               # game-server (FastAPI, modularer Monolith)
│   └── app/
│       ├── auth/  economy/  research/  fleet/  combat/
│       ├── commander/  universe/  messaging/
│       └── platform/      # db, scheduler, event-bus, config
├── ai-worker/             # Queue-Consumer, Ollama-Client, Bank-Generierung
│   ├── jobs/              # nightly_batch, big_moment
│   └── prompts/           # Persona-/Situations-Prompt-Vorlagen
├── frontend/              # Angular SPA
└── shared/                # geteilte Schemas/Typen (z. B. Event-/Message-Contracts)
```

→ Genau hier setzt das **Repo-Scaffold** an, wenn du so weit bist (nächster optionaler Schritt).

---

### Änderungshistorie
- **v0.1 (2026-06-06):** Erstfassung. Service-Dekomposition, Modulgrenzen, Datenflüsse,
  Zeit-Modell, DB-Schema-Grundriss, Skalierungspfad, ADR-Index, Repo-Struktur.
