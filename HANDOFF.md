# 🛰️ Handoff — Universe (Stand 2026-06-07)

> Übergabe für die nächste Session. Projekt: browserbasiertes Weltraum-Aufbau-MMO
> *Universe* (OGame-Tradition + persistentes Universum + KI-Crews als USP).
> Repo: `D:/Privat/Universe/Universe` · Branch: `main` (lokal, kein Remote) · Working tree sauber.

---

## 1. TL;DR — wo wir stehen
Der **Vertical Slice läuft end-to-end** durch den kompletten Stack (Angular → FastAPI →
PostgreSQL/pgvector → Redis → ai-worker → Ollama). Alle 5 Container laufen via
`docker compose`. Diese Session lief vollständig in Docker und ist verifiziert.

**Diese Session — gewaltiger Batch (alles verifiziert + committet, oben = neu):**
```
a3b4de9 Galaxie-Planeten/Debris-Renders + Tech-Tree-Ansicht + frische Szenen
88767f0 Commander-Gueteklassen F-SSS (Potenzial + Ausbildungs-Investition)
5550886 Planetentypen + Felder-Kurve (Model A, Doku 06a)
bfcb2c8 voller Schiffs-/Verteidigungs-Roster + Rapidfire-Matrix + neue Techs
6364dd9 Dashboard-Cockpit (aktive Timer + Flottenbewegungen)
13bc444 Voraussetzungen konkret anzeigen ("benoetigt: ...")
061a463 Forschung/Werft/Flotte im OGame-Stil (dichte Kacheln)
ffa4130 Gebaeude-Screen im OGame-Stil
779646d echte Assets integriert (Schiffe/Gebaeude/Verteidigung/Commander/BG)
8841e67 Postfach strukturiert (Spionagebericht-Karte, Typ-Badges) + loeschen
...davor: Spionage, NPC-Verhalten, Werft-Queue persistent (s.u.)
```

**Neu in dieser Session (Highlights):**
- **OGame-UI-Redesign** aller Bau-Screens (Gebaeude/Forschung/Werft/Flotte) — dichte,
  bild-zentrierte Kacheln; **Dashboard = Cockpit** (Bau/Forschung/Werft-Countdowns,
  Flottenbewegungen, Alerts); **Voraussetzungen** werden konkret angezeigt.
- **Echte Assets** integriert (Schiffe/Gebaeude/Verteidigung/Commander-Portraits/
  Ressourcen-Icons/Hintergruende; Galaxie zeigt Planeten-/Debris-Renders).
- **Kampf-Roster Phase 1**: voller Roster (14 Schiffe / 10 Verteidigung) + komplette
  **Rapidfire-Matrix** + 6 neue Techs (laser/ion/plasma/hyperspace/graviton) — `balance.json`,
  Engine datengetrieben. Sim verifiziert (Schlachtkreuzer schlagen Schlachtschiffe via RF 7).
- **Planetentypen + Felder (Model A)**: Position -> Typ/Temp/`fields_max` (Doku 06a),
  fields_max erzwungen, Abreissen erstattet Felder. `derive_planet()` + Startup-Backfill.
- **Commander-Gueteklassen F-SSS** (Doku 05a): Potenzial-Achse (potency 0.6-2.0) neben Rang,
  Ausbildungs-Investition (Standard..Experimentell), SSS max 5%; wirkt real in Kampf/Tempo.
- **Tech-Tree-Screen** (neuer Nav-Eintrag "Techbaum").
- **Postfach** strukturiert (Spionagebericht als Intel-Karte, Typ-Badges) + Loeschen.
- davor: **Spionage** (Sonden decken Ziele auf, Doku 04 §6), **NPC-Verhalten** (Behavior Trees,
  Doku 08), **Werft-Queue persistent** + idempotente Startup-Migration (`platform/migrations.py`).

**Neue Design-Docs (gelockt, teils gebaut):** `docs/systems/03a-combat-ships-roadmap.md`,
`05a-commander-grades.md`, `06a-planet-types-fields.md`.

**🎯 Aktuelle Frontier (NEU diese Session, noch NICHT gebaut):** ein **rollenbasiertes
Kampf-System** mit Subsystemen (Schild/Antrieb/Hülle), Schadenstypen, Piraterie/Eskorte und
4 Soft-Doktrinen — vollständig designt in **`docs/systems/03b-role-based-combat.md`** +
**`03c-role-roster-spec.md`**. Das ist der Headline-Build für morgen (siehe §6). **Assets:** der
komplette v0.1-Satz ist **produziert** und integriert; nur die neuen Rollen-Assets (ASSETS.md §11)
sind offen (Nutzer generiert sie).

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

### Naechste grosse Brocken (designt/teil-gebaut → noch offen)
- **Kampf (Roadmap `03a`):** Phase 1 (Roster) gebaut. Offen: **Trümmer-/Recycler-Loop**,
  ⭐ **Interception** (Flotten im Flug abfangen, Tempo-basiert), **aktive Commander-Faehigkeiten**,
  **Flaggschiff/Permadeath/Capture** vervollstaendigen, **Kampf-Simulator**,
  Verteidigungs-Spezialmechanik (Schildkuppel max 1/Planet, ABM/IPM-Raketen).
- **Planeten (`06a`):** Typen/Felder gebaut. Offen: **Gasplaneten + Exotische Materie**
  (RESERVIERT, erst mit Allianzen/End-Forschung), Terraformer, **Kolonisierung** (colonize-Mission
  hat noch keinen Planet-Erstellungs-Handler).
- **Commander (`05a`):** Grade gebaut. Offen: Grade auch via **Expeditionen** finden;
  aktive Faehigkeiten (Doku 05 §6).
- **KI/LLM-Funksprüche** weiterhin bewusst aufgeschoben (Nutzer-Wunsch), bis der Rest rund ist.

---

## 6. Vorgeschlagene nächste Schritte (priorisiert)

### ⭐ Headline für morgen: Rollen-Kampf-System bauen (Doku 03b/03c)
Das große neue Design dieser Session: Schiffe als **Rollen mit Kontern** statt linearer Machtleiter.
Vollständig spezifiziert in **`docs/systems/03b-role-based-combat.md`** (Mechanik + 4 Doktrinen) und
**`docs/systems/03c-role-roster-spec.md`** (konkreter Roster + Asset-Liste). Build-Pfad (03b §6):
1. **Phase 1 — Engine-Fundament** (`combat/engine.py` + `balance.json`): **Antrieb als 3. Subsystem**
   (Integritäts-Stufen) + **Schadenstyp×Subsystem-Matrix** (Energie/Kinetik/Ionen/Rakete) +
   **Reichweiten-Bänder** (Standoff/Initiative). Danach per Sim verifizierbar. ← *hier anfangen.*
2. Phase 2 Stranden/Disengage/Interdiktion · 3 Entern/Capture (nur Schiffe+Fracht, **keine** Commander) ·
   4 Rollen-Roster + Eskort-Konter (braucht neue Assets) · 5 Söldner-/Markt-Layer.
- **Entscheidungen gelockt:** echte Reichweiten · Capture nur Schiffe · Söldner = Service · 4 Soft-Doktrinen
  (Kriegsherr/Händler/Freibeuter/Pionier) · Kernmechaniken (Kolonisieren!) universell, Doktrin nur Boni.

### Parallel / sonst offen
- **Assets v0.2:** Nutzer generiert die **§11-Rollen-Assets** (`docs/ASSETS.md`: 12 neue Schiffe +
  Waffen-/Status-Icons + Effekte). v0.1-Satz ist komplett produziert.
- **Spielfluss real durchspielen** (frisches Konto) → Balance/Pacing tunen (`shared/balance.json`).
- **NPC-Verhalten erweitern**: aktive Angriffe/Expansion · **Gegen-Spionage** (Tech-Debt #4/#5).
- **Kolonisierung** (colonize-Mission hat noch keinen Planet-Erstellungs-Handler) · **Trümmer/Recycler-Loop**.
- **LLM-Funksprüche** (Modelle pullen) — vom Nutzer bewusst aufgeschoben, bis der Rest „rund" ist.

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
| **⭐ Rollen-Kampf-System (Design, nächster Build)** | `docs/systems/03b-role-based-combat.md` · `03c-role-roster-spec.md` |
| **Asset-Spezifikation (v0.1 produziert, §11 neu)** | `docs/ASSETS.md` |
| Design-Doku | `docs/` (GDD, ARCHITECTURE, DESIGN_DECISIONS, systems/01–12 + 03a/03b/03c/05a/06a, adr/, ASSETS, STYLE_BIBLE) |

---

## 8. Offene Design-Frage (für dich)
- Bei „automatischem" Fokus wird die Schiffsklasse halb-zufällig gewählt. Soll der **Rang-Aufstieg**
  später auch neue **aktive Commander-Fähigkeiten** freischalten (Doku 05 §6: Konzentriertes Feuer,
  Eilmarsch, …)? Bisher nur passive Boni. → Kandidat für eine eigene Session.

> Alles committet, Working Tree sauber. Viel Erfolg morgen! 🚀
