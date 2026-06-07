# 🛰️ Handoff — Universe (Stand 2026-06-07)

> Übergabe für die nächste Session. Projekt: browserbasiertes Weltraum-Aufbau-MMO
> *Universe* (OGame-Tradition + persistentes Universum + KI-Crews als USP).
> Repo: `D:/Privat/Universe/Universe` · Branch: `main` (lokal, kein Remote) · Working tree sauber.

---

## 1. TL;DR — wo wir stehen
Der **Vertical Slice läuft end-to-end** durch den kompletten Stack (Angular → FastAPI →
PostgreSQL/pgvector → Redis → ai-worker → Ollama). Alle 5 Container laufen via
`docker compose`. Diese Session lief vollständig in Docker und ist verifiziert.

**Letzte Commits (diese Session, oben = neu):**
```
e30e795 feat(spionage): Galaxie-Screen mit Aufklaerung + Sonden-Deep-Links — Frontend
efdb87f feat(spionage): Ziele erst per Sonde aufdecken (Doku 04 §6) — Backend
57d49f4 feat(npc): Behavior-Tree-Tick laesst NPC-Imperien leben (Doku 08)
1d897e4 feat(werft): persistente Bau-Warteschlange (Tech-Debt #2)
f19e8b9 feat(commander): Spezialisierung + Fokus bei Akademie-Ausbildung waehlbar
```

**Neu in dieser Session (alles verifiziert, Working Tree sauber):**
- **Werft-Queue persistent** (Tech-Debt #2 geschlossen): neue `shipyard_queue`-Tabelle,
  Auftraege ueberleben Neustart, Scheduler-Recovery plant sie nach.
- **Idempotente Startup-Migration** (`platform/migrations.py`, `ensure_schema`): bringt neue
  Tabellen/ENUMs in bestehende DBs OHNE `down -v` (laeuft im lifespan vor der Recovery).
- **NPC-Verhalten** (Behavior Trees, `app/npc/`): periodischer Tick laesst NPCs ihre Garnison
  Richtung baseline regenerieren / je Profil wachsen (Anti-Farming, Doku 08).
- **Spionage** (Doku 04 §6): `spy`-Mission deckt Ziele per Sonde auf (Detailstufe 1–3 je nach
  Sondenzahl/Spionagetech), Spionagebericht ins Postfach, `player_discoveries`-Tabelle;
  `GET /galaxy/targets` liefert nur noch aufgeklaerte Ziele; Galaxie-Screen mit Spionieren-Buttons.

---

## 2. Schnellstart (morgen)
```bash
cd D:/Privat/Universe/Universe/infra
docker compose up -d            # Images sind gecacht, Daten persistieren im pgdata-Volume
# Frontend:  http://localhost:4200
# API-Docs:  http://localhost:8000/docs
```
Stoppen: `docker compose stop` (Daten bleiben) · Komplett zurücksetzen inkl. DB:
`docker compose down -v` (löscht das pgdata-Volume → frisches Universum).

Nach Code-Änderungen neu bauen: `docker compose up -d --build game-server` (bzw. `frontend`).
Frontend lokal schneller iterieren: `cd frontend && npm run build` (oder `npm start` mit Dev-Proxy).

**Backend-Tests:** `docker compose cp ../backend/tests game-server:/app/tests && docker compose exec game-server python -m pytest tests/ -q` (8 Tests, grün).

---

## 3. Test-Account (⚠ enthält Spuren der Verifikation)
- **Login:** `admiral@universe.test` / `sehr-geheim-123`
- Eingebrachter Test-Zustand: 1 Start-Commander **Mara** (Kampf, Moral 100 durch Testkämpfe),
  1 ausgebildeter **Cassius** (Logistik/zivil), eine per SQL gesetzte **Kommando-Akademie Stufe 1**,
  ein paar injizierte NPC-Ziele (u. a. „Nahes Pirateziel" 2:10:9), Schiffe/Deuterium aufgefüllt.
- **Neu durch die Verifikation dieser Session** (Planet `e993d533…`):
  Werft auf Stufe 1 gesetzt; ein paar `spy_probe`/`light_fighter` injiziert; **2 aufgeklärte Ziele**
  vorhanden (1:42:8 „Verlassene Schmugglerbasis" L3, 1:58:4 „Piraten-Aussenposten K17" L1) →
  damit sind im Galaxie-Verzeichnis sofort Ziele sichtbar. Spy-Reports liegen im Postfach.
- ⚠ **Wichtige Verhaltensänderung:** Frische Konten sehen NPC-Ziele jetzt **erst nach Spionage**
  (Sonde senden). Der obige Test-Account hat dank der 2 Discoveries schon Ziele.
- Für einen **sauberen Eindruck**: neues Konto registrieren oder `docker compose down -v`.

---

## 4. Was funktioniert (verifiziert)
- **Auth** (Register/Login/JWT), Start-Setup (Heimatplanet + Ressourcen + 1 Commander).
- **Wirtschaft**: Lazy-Ressourcen (Rate × Δt, speed ×7), Energie-Drossel bei Defizit.
- **Gebäude**: Ausbau mit Timer; **Energie-Anzeige je Gebäude** (verbraucht/erzeugt + Δ);
  **Kategorien** (Rohstoff/Energie/Anlagen/Lager/Kommando).
- **Forschung** (eine gleichzeitig) + **Werft**: jeweils **kategorisiert**.
- **Flotte**: senden mit Commander, Sprit/Slots/Tempo, Rückruf; Timer via Scheduler.
- **Galaxie-Screen**: System-Scanner + **Ziel-Verzeichnis** (`/api/galaxy/targets`) +
  „Angreifen" verlinkt vorausgefüllt auf die Flotte.
- **Kampf**: deterministische Engine (6 Runden, Rapidfire, Schild-Abprall, Explosion),
  Beute/Trümmer/Verteidigungs-Regen, Commander Moral/XP/Rang, Evakuierung/Permadeath.
- **Commander-USP**:
  - **schiffsklassen-spezifische Boni** (Angriff/Schild/Tempo, abgeleitet aus
    Spezialisierung + Rang + Traits + Fokus, moral-skaliert) — wirken im Kampf (pro Schiffstyp)
    und auf die Flugzeit (Tempo).
  - **Akademie-Ausbildung mit Auswahl** (Spezialisierung + Fokus-Schiffsklasse) + Live-Boni-Vorschau
    (`/api/commanders/bonus-preview`).
- **Funkspruch-Pipeline**: nach Kampf sofort (0 ms, Bank-Lookup + Slot-Filling) ins Postfach + WS-Push.
- **AI-Worker**: konsumiert Jobs, degradiert sauber ohne Ollama-Modelle (ADR-003).
- **Scheduler-Recovery**: offene Timer überleben Server-Neustart (ADR-007).

---

## 5. Bekannte Einschränkungen / Tech-Debt
1. **LLM-Funksprüche noch nicht live**: Host-Ollama hat nur `qwen3-coder:30b`. Für echte,
   persona-spezifische Funksprüche fehlen die Modelle →
   `ollama pull llama3.1:8b` + `ollama pull nomic-embed-text` (Host). Bis dahin Template-Fallback.
2. ~~Werft-Queue ist In-Memory~~ → **ERLEDIGT** (persistent via `shipyard_queue` + Recovery).
3. **Fusionsreaktor** erzeugt Energie, verbraucht aber noch **kein** Deuterium (Doku 01 §4).
4. **NPC-Verhalten**: Behavior-Tick existiert jetzt (Regen/Wachstum der Garnison), aber NPCs
   **greifen noch nicht aktiv an** und expandieren nicht auf neue Felder (nur Aufbau am Standort).
   Default-Tick-Intervall 1 h (`balance.npc.tick_interval_seconds`).
5. **Spionage**: Aufklärung + Berichte stehen; **Gegen-Spionage / Sonden-Erkennung** beim Ziel
   fehlt noch (Doku 04 §6). Spieler-Planet-Resschen werden „roh" (ungelazy-refresht) gelesen.
6. **PvP** weiterhin rudimentär; Ziele sind v. a. NPCs.
7. **Sprit-/Distanz-Formel** ist eine Slice-Näherung (Doku 07 §2 noch nicht final).
8. **Überdehnung** nutzt „Anzahl Schiffstypen" als Geschwader-Proxy (vereinfachte Span-Logik).
9. Ungenutzte Doku-Screens ohne Endpunkt: Allianz, Markt, Ranglisten, Kampf-Simulator.
10. **`_note`-Meta-Keys in balance.json**: Kataloge (ships/defenses) enthalten `_note`-Kommentare.
    Iterierende Codestellen müssen `_`-Keys überspringen (in `shipyard.build_options` gefixt) —
    bei neuen Katalog-Schleifen beachten.

---

## 6. Vorgeschlagene nächste Schritte (priorisiert)
1. **Spielfluss real durchspielen** (frisches Konto): Werft + Akademie + Labor hochziehen,
   Schiffe + Sonden bauen, Ziele **erst spionieren, dann angreifen** → Balance/Pacing am echten
   Spielgefühl tunen (`shared/balance.json`, inkl. neuer `npc`- und `spy`-Sektionen).
2. ~~Spionage-Mechanik~~ → **ERLEDIGT** (diese Session). Nächster Ausbau: Gegen-Spionage /
   Sonden-Erkennung beim Ziel (Tech-Debt #5).
3. ~~Werft-Queue persistent~~ → **ERLEDIGT** (diese Session).
4. **NPC-Verhalten erweitern**: aktive NPC-Angriffe + Expansion auf neue Felder (Tech-Debt #4).
5. **LLM-Funksprüche aktivieren** (Modelle pullen) und die Großmoment-Pipeline live erleben.
   (Vom Nutzer bewusst aufgeschoben, bis der Rest „rund" ist.)
6. **Assets**: echte Grafiken nach `docs/ASSETS.md` + `docs/STYLE_BIBLE.md` erzeugen
   (aktuell SVG/Emoji-Platzhalter; `assets/` liegt bereits mit Platzhaltern im Working Tree,
   noch nicht committet).

---

## 7. Wichtige Dateien (Orientierung)
| Zweck | Pfad |
|------|------|
| Balance-Zahlen (Single Source of Truth) | `shared/balance.json` |
| API-Contract / Event-Contract | `shared/api-contract.md` · `shared/events.md` |
| DB-Schema + NPC-Seeds | `infra/db/init.sql` |
| Compose / Env | `infra/docker-compose.yml` · `infra/.env.example` |
| Backend-Module | `backend/app/<domain>/{router,service,schemas}.py` |
| Kampf-Engine (rein, getestet) | `backend/app/combat/engine.py` |
| Commander-Boni-Logik | `backend/app/commander/bonuses.py` |
| Scheduler-Recovery | `backend/app/platform/recovery.py` |
| **Startup-Migrationen (idempotent)** | `backend/app/platform/migrations.py` |
| **NPC-Behavior-Tree + Tick** | `backend/app/npc/{behavior,profiles,service}.py` |
| **Spionage-Aufloesung** | `backend/app/universe/spionage.py` |
| AI-Worker | `ai-worker/` (jobs/, prompts/) |
| Frontend-Screens | `frontend/src/app/features/<screen>/` |
| Design-Doku | `docs/` (GDD, ARCHITECTURE, DESIGN_DECISIONS, systems/01–12, adr/, ASSETS, STYLE_BIBLE) |

---

## 8. Offene Design-Frage (für dich)
- Bei „automatischem" Fokus wird die Schiffsklasse halb-zufällig gewählt. Soll der **Rang-Aufstieg**
  später auch neue **aktive Commander-Fähigkeiten** freischalten (Doku 05 §6: Konzentriertes Feuer,
  Eilmarsch, …)? Bisher nur passive Boni. → Kandidat für eine eigene Session.

> Alles committet, Working Tree sauber. Viel Erfolg morgen! 🚀
