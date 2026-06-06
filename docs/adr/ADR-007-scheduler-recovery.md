# ADR-007 — Startup-Recovery offener Timer

**Status:** akzeptiert · **Datum:** 2026-06-06 · ergänzt ADR-002 (Lazy-Ressourcen + geplante Ereignisse)

## Kontext
Diskrete Ereignisse (Gebäude-/Forschungs-/Werft-Bau, Flottenankunft/-rückkehr,
Commander-Ausbildung) werden über APScheduler als einmalige `date`-Jobs zu absoluten
Zeitpunkten geplant (ARCHITECTURE §6). APScheduler nutzt im Vertical Slice einen
**MemoryJobStore** — die geplanten Jobs leben nur im Prozessspeicher und gehen bei einem
Neustart des `game-server` verloren. Folge: Ein Bau, der zur Neustartzeit „in der Luft"
war, würde nie abgeschlossen; die DB-Zeile (`*_finishes_at` / `arrive_at`) bliebe ewig offen.

## Entscheidung
Beim Startup liest der game-server alle in der DB noch offenen Timer und **plant sie neu
ein** (`app/platform/recovery.py`, aufgerufen im Lifespan-Startup vor dem ersten Request):

- `buildings.upgrade_finishes_at IS NOT NULL` → `complete_building`
- `research.finishes_at IS NOT NULL` → `complete_research`
- `fleets.status IN ('flying','returning')` → `fleet_arrive` / `fleet_return`
- `commanders.status='training'` → `complete_training`

Die Job-IDs sind identisch zu denen der Services (idempotentes `replace_existing`).
Liegt der Zeitpunkt in der Vergangenheit, feuert der Date-Trigger sofort
(`misfire_grace_time=None`) und der Abschluss wird nachgeholt.

## Konsequenzen
- ✅ Die DB bleibt die einzige Wahrheit; der Scheduler ist nur ein flüchtiger Ausführer.
  Ein Neustart (Deploy, Crash) verliert keine Fortschritte mehr.
- ✅ Kein zusätzlicher persistenter JobStore nötig — die Spiel-Tabellen *sind* der Plan.
- ⚠️ Die in-memory **Werft-Queue** (kein eigener Tabellen-Datensatz im Slice) wird **nicht**
  wiederhergestellt — bekannte Slice-Einschränkung; ein `shipyard_queue`-Table schließt die
  Lücke in einem Folgeschritt.
- 🔭 Nächster Ausbaupfad bei Mehr-Instanz-Betrieb: persistenter JobStore (z. B. Redis/SQL)
  oder ein dedizierter Tick-Worker; die Recovery-Logik bleibt als Sicherheitsnetz nützlich.
