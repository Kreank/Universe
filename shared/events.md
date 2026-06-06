# Event-Contract — game-server ↔ ai-worker (über Redis)

> Die **zweite harte Grenze** (ARCHITECTURE §3): game-server und ai-worker reden
> **ausschließlich** über Redis (Jobs) und PostgreSQL (Ergebnisse). Nie direkter Aufruf.
> Das hält LLM-Latenz komplett aus dem Spiel-Pfad (ADR-003).

## Redis-Strukturen

### Liste `ai:jobs` (Job-Queue, BRPOP durch ai-worker)
JSON-Payload je Job:
```json
{
  "job_type": "big_moment" | "nightly_batch" | "persona_init",
  "commander_id": "uuid",
  "player_id": "uuid",
  "context": {
    "situation": "victory|defeat|close_win|mutiny|...",
    "enemy": "Piraten-Aussenposten K17",
    "planet": "1:58:4",
    "loot": { "metal": 4000, "crystal": 2000, "deuterium": 800 },
    "outcome": "win|loss"
  },
  "enqueued_at": "iso-8601"
}
```

- **big_moment**: ai-worker generiert *einen* kontextbezogenen Funkspruch via Ollama,
  dedupliziert per pgvector, schreibt in `transmissions` (type=`big_moment`) und published
  ein WS-Event (siehe unten). Latenz 2–5 s = Feature („Funk über Lichtjahre").
- **nightly_batch**: füllt pro Commander die `reaction_banks` je Situation nach
  (z. B. 10 Sieg-, 10 Niederlage-Varianten), erzeugt Embeddings, dedupliziert.
- **persona_init**: erzeugt für einen neuen Commander das Persona-Profil + Erst-Banken.

### Pub/Sub-Channel `ws:player:{player_id}` (WS-Fan-out)
Der game-server **subscribed** diesen Channel und leitet Nachrichten an die WS-Clients des
Spielers weiter. Der ai-worker **published** hier seine fertigen Funksprüche:
```json
{ "type": "transmission", "transmission": { ...siehe api-contract.md §8... } }
```

## Wer published was
| Quelle | Mechanismus | Beispiel |
|--------|-------------|----------|
| game-server (sofort, 0 ms) | Bank-Lookup + Slot-Filling, schreibt `transmissions`, published WS | Sofort-Reaktion nach Kampf |
| game-server | enqueue `ai:jobs` (big_moment) | Großmoment nach entscheidender Schlacht |
| Scheduler (game-server) | enqueue `ai:jobs` (nightly_batch) je Commander | nächtliches Bank-Füllen |
| ai-worker | published `ws:player:{id}` + schreibt `transmissions`/`reaction_banks` | LLM-Ergebnisse |

## Degradationsverhalten (wichtig, ADR-003)
Fällt der ai-worker oder Ollama aus:
- Sofort-Reaktionen funktionieren weiter (Bank-Lookup im game-server, kein LLM).
- Sind die Banken leer, nutzt der game-server eine **Template-Fallback-Zeile** (Ebene 1).
- big_moment-Jobs stauen sich in `ai:jobs` und werden abgearbeitet, sobald der Worker zurück ist.
- Das Spiel bleibt voll spielbar. KI ist Veredelung, kein kritischer Pfad.
