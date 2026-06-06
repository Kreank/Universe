# 🛰️ Handoff — Universe (Stand 2026-06-07)

> Übergabe für die nächste Session. Projekt: browserbasiertes Weltraum-Aufbau-MMO
> *Universe* (OGame-Tradition + persistentes Universum + KI-Crews als USP).
> Repo: `D:/Privat/Universe/Universe` · Branch: `main` (lokal, kein Remote) · Working tree sauber.

---

## 1. TL;DR — wo wir stehen
Der **Vertical Slice läuft end-to-end** durch den kompletten Stack (Angular → FastAPI →
PostgreSQL/pgvector → Redis → ai-worker → Ollama). Alle 5 Container laufen via
`docker compose`. Diese Session lief vollständig in Docker und ist verifiziert.

**Letzte 5 Commits:**
```
f19e8b9 feat(commander): Spezialisierung + Fokus bei Akademie-Ausbildung waehlbar
f3f05a1 feat: Energie-Anzeige + Kategorien (Gebaeude/Forschung/Werft) + Commander-Boni-System
60f3318 feat(galaxy): eigener Galaxie-/Karten-Screen mit Ziel-Verzeichnis
40e0bd8 Vertical Slice v0.1: backend, ai-worker, frontend, assets + scheduler-recovery
5da9c4f Foundation: Repo-Scaffold, balance.json, DB-Schema, API-/Event-Contracts, Infra
```

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
2. **Werft-Queue ist In-Memory** (keine `shipyard_queue`-Tabelle) → überlebt keinen Neustart;
   die Scheduler-Recovery deckt sie deshalb nicht ab. Folgeschritt: eigene Tabelle.
3. **Fusionsreaktor** erzeugt Energie, verbraucht aber noch **kein** Deuterium (Doku 01 §4).
4. **PvP** ist nur rudimentär; Ziele sind aktuell NPCs. NPC-Verhalten (Behavior Trees) fehlt noch.
5. **Sprit-/Distanz-Formel** ist eine Slice-Näherung (Doku 07 §2 noch nicht final).
6. **Überdehnung** nutzt „Anzahl Schiffstypen" als Geschwader-Proxy (vereinfachte Span-Logik).
7. **Commander-Fokus** wird bei „automatisch" halb-zufällig gesetzt; manuelle Wahl existiert jetzt.
8. Ungenutzte Doku-Screens ohne Endpunkt: Allianz, Markt, Ranglisten, Kampf-Simulator.

---

## 6. Vorgeschlagene nächste Schritte (priorisiert)
1. **Spielfluss real durchspielen** (frisches Konto): Werft + Akademie + Labor hochziehen,
   Schiffe bauen, Ziele angreifen → Balance/Pacing am echten Spielgefühl tunen (`shared/balance.json`).
2. **Spionage-Mechanik**: Ziele erst per Sonde aufdecken statt alle „bekannt" (koppelt an
   Galaxie-Screen + Aufklärung, Doku 04 §6).
3. **Werft-Queue persistent** machen (`shipyard_queue`-Tabelle + Recovery) — schließt Tech-Debt #2.
4. **LLM-Funksprüche aktivieren** (Modelle pullen) und die Großmoment-Pipeline live erleben.
5. **NPC-Verhalten** (einfache Behavior Trees, Doku 08) für lebendigere PvE-Ziele.
6. **Assets**: echte Grafiken nach `docs/ASSETS.md` + `docs/STYLE_BIBLE.md` erzeugen
   (aktuell SVG/Emoji-Platzhalter).

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
| AI-Worker | `ai-worker/` (jobs/, prompts/) |
| Frontend-Screens | `frontend/src/app/features/<screen>/` |
| Design-Doku | `docs/` (GDD, ARCHITECTURE, DESIGN_DECISIONS, systems/01–12, adr/, ASSETS, STYLE_BIBLE) |

---

## 8. Offene Design-Frage (für dich)
- Bei „automatischem" Fokus wird die Schiffsklasse halb-zufällig gewählt. Soll der **Rang-Aufstieg**
  später auch neue **aktive Commander-Fähigkeiten** freischalten (Doku 05 §6: Konzentriertes Feuer,
  Eilmarsch, …)? Bisher nur passive Boni. → Kandidat für eine eigene Session.

> Alles committet, Working Tree sauber. Viel Erfolg morgen! 🚀
