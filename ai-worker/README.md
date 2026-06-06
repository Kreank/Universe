# ai-worker — KI-Content-Pipeline für *Universe*

Eigenständiger, vom Game-Tick **entkoppelter** Worker (GDD §10.5, ADR-003). Er
konsumiert Jobs aus der Redis-Queue `ai:jobs`, ruft **Ollama** (lokal) für
Text- und Embedding-Generierung und schreibt Ergebnisse nach **PostgreSQL +
pgvector**. **Kein direkter Kontakt** zum game-server — nur Redis (Jobs / PubSub)
und PostgreSQL (Ergebnisse).

> Leitprinzip „Munition vs. Verschuss": nachts werden personalisierte
> Reaktions-Banken vorgeneriert; tagsüber zieht der game-server daraus ohne LLM.
> Großmomente werden als einzelner Funkspruch wenige Sekunden später nachgepusht.

## Job-Typen

| job_type | Zweck |
|----------|-------|
| `persona_init`  | Neuen Commander: Persona-Profil (`background`/`voice`) per LLM anreichern + erste, kleine Reaktions-Bank je Situation füllen. |
| `nightly_batch` | Pro Commander die `reaction_banks` je Situation auf ~10 Varianten auffüllen (mit `{enemy} {planet} {loot}`-Slots), Embeddings + pgvector-Dedup. |
| `big_moment`    | EINEN kontextbezogenen Funkspruch generieren (RAG: Persona + Lore + Situation), in `transmissions` schreiben (`type='big_moment'`), via PubSub `ws:player:{player_id}` pushen. |

Situationen: `victory`, `defeat`, `close_win`, `mutiny`, `demand`, `idle_bored`.

## Job-Flow

```
game-server ──LPUSH ai:jobs──▶ Redis ──BRPOP──▶ ai-worker
                                                   │  generate() / embed()  ┌─────────┐
                                                   ├────────────────────────▶│ Ollama  │
                                                   │                         └─────────┘
                                                   │  reaction_banks / transmissions
                                                   ├────────────────────────▶ PostgreSQL + pgvector
                                                   │  big_moment: PUBLISH ws:player:{id}
                                                   └────────────────────────▶ Redis ──▶ game-server WS-Fan-out
```

Dedup/RAG nutzen den pgvector-Cosine-Operator `<=>`. Kandidaten mit Distanz
`< DEDUP_COSINE_THRESHOLD` (Default 0.10) werden verworfen.

## Benötigte Ollama-Modelle

Ollama läuft i. d. R. **nativ auf dem Host** (GPU-Zugriff). Modelle einmalig ziehen:

```bash
ollama pull llama3.1:8b        # Dialog/Funksprüche  (OLLAMA_MODEL)
ollama pull nomic-embed-text   # Embeddings, 768 dim (OLLAMA_EMBED_MODEL)
```

`nomic-embed-text` liefert nativ 768 Dimensionen (passt zu `vector(768)`).
Liefert ein anderes Embed-Modell eine abweichende Dimension, gleicht der Worker
per Trunc/Pad an (mit Warn-Log) — dann besser das Modell wechseln.

## Konfiguration (Umgebungsvariablen)

| Variable | Default | Zweck |
|----------|---------|-------|
| `DATABASE_URL` | `postgresql+asyncpg://universe:universe@localhost:5432/universe` | PostgreSQL (`+asyncpg` wird intern entfernt) |
| `REDIS_URL` | `redis://localhost:6379/0` | Queue + PubSub |
| `OLLAMA_URL` | `http://host.docker.internal:11434` | Ollama-HTTP-API |
| `OLLAMA_MODEL` | `llama3.1:8b` | Generierungs-Modell |
| `OLLAMA_EMBED_MODEL` | `nomic-embed-text` | Embedding-Modell |

Weitere Tuning-Hebel (Schwellen, Ziel-Mengen, Timeouts) in `config.py`.

## Lokal ausführen

```bash
cd ai-worker
python -m venv .venv && . .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
# Voraussetzung: PostgreSQL (Schema aus infra/db/init.sql) + Redis + Ollama laufen.
python main.py
```

## Mit Docker (gesamter Stack)

```bash
docker compose -f infra/docker-compose.yml up --build
```

Der Service `ai-worker` ist in `infra/docker-compose.yml` definiert; Build-Kontext
ist dieser Ordner, Start `python main.py`.

## Test-Job einreihen

`dev_enqueue.py` legt einen Beispiel-Job in `ai:jobs`:

```bash
# Großmoment (braucht existierende commander_id + player_id in der DB):
python dev_enqueue.py big_moment --commander <UUID> --player <UUID> --situation victory

# Nächtliches Bank-Füllen für einen Commander:
python dev_enqueue.py nightly_batch --commander <UUID>

# Persona-Init für einen neuen Commander:
python dev_enqueue.py persona_init --commander <UUID>
```

Der Worker loggt Empfang und Ergebnis. Bei `big_moment` landet die Transmission in
`transmissions` und wird auf `ws:player:{player_id}` publiziert (mit `redis-cli
SUBSCRIBE ws:player:<UUID>` beobachtbar).

## Degradation (ADR-003)

- Ist Ollama nicht erreichbar, wird `OllamaUnavailable` geworfen; der Worker legt
  den Job **zurück** in die Queue (LPUSH an den Kopf) und wartet kurz (Backoff).
  Kein Job geht verloren, der Worker crasht nie.
- Andere (nicht-transiente) Fehler werden geloggt und der Job verworfen, um eine
  Poison-Loop zu vermeiden.
- `nightly_batch`/`persona_init` sind idempotent: Bank-Füllung zählt vorhandene
  Einträge und füllt nur das Defizit — ein erneut eingereihter Job setzt nahtlos fort.
- Graceful Shutdown auf SIGINT/SIGTERM: laufender Job wird ggf. zurückgestellt.

## Bekannte Einschränkungen

- **big_moment-Dedup** läuft gegen die `reaction_banks` desselben Commanders
  (gleiche Situation), nicht gegen frühere `big_moment`-Transmissions — die Tabelle
  `transmissions` hat keine Embedding-Spalte. Verhindert das Echoen von Stock-Zeilen;
  identische Großmomente über die Zeit sind theoretisch möglich.
- **nightly_batch** verarbeitet **einen** Commander pro Job (der Scheduler im
  game-server reiht pro Commander einen Job ein).
- Der `flavor_pool` (RAG-Lore-Quelle für `big_moment`) wird hier nicht befüllt;
  ist er leer, läuft `big_moment` ohne Lore-Kontext (best effort).
