# 🛰️ Handoff — Universe (Stand 2026-06-09)

> Übergabe für die nächste Session. Projekt: browserbasiertes Weltraum-Aufbau-MMO
> *Universe* (OGame-Tradition + persistentes Universum + KI-Crews als USP).
> Server-Pfad: `/srv/storage/projects/universe` · Branch: `master` (lokal, kein Remote).
> Live: `universe.tech-artist.de` · lokal Frontend `:4200`, API `:8100→8000`.
> ⚠ Working tree NICHT sauber: **(a)** meine Kampfbericht-Frontend-Arbeit dieser Session
> (6 Dateien, s. §0, NOCH NICHT committet — gezielt committen, NICHT `git add .`), **(b)** fremder
> Vor-WIP `frontend/.../techtree.component.ts` + die **Asset-Umstellung** (Nutzer generiert noch
> Assets nach). Beim Committen NUR die §0-Dateien nehmen.
> ⚠ DB wurde zwischenzeitlich zurückgesetzt (`down -v`): der alte Test-Account
> `admiral@universe.test` existiert NICHT mehr. Aktuell 1 echter Account
> (`sascha-richter@hotmail.com`), **0 Kampfberichte** in der DB.

---

## 0. Diese Session (2026-06-09) — Kampfberichte im Frontend sichtbar (Read-Path der Engine)
**Headline:** Die reiche Kampf-Engine (Phase 1–4) war im Frontend komplett unsichtbar — der
Endpoint `GET /api/combat-reports/{id}` existierte, wurde aber NIE genutzt; im Postfach gab es nur
ein ⚔️-Badge ohne Inhalt. Jetzt: voller **Kampfbericht-Viewer**. Kernmotiv (Nutzer): *man kann
offline angegriffen werden und nimmt nicht selbst am Kampf teil* → der asynchrone Bericht ist die
einzige Art, das nachzuvollziehen. **NOCH NICHT committet** (s. Warnung oben).

- **Backend:**
  - `combat/router.py`: Serialisierung in reine Funktion `serialize_combat_report(report, viewer_id)`
    extrahiert; reicht jetzt die **volle** Engine-Ausgabe durch (Runden mit `distance`/`fled`/`ambush`,
    `*_survivors`, `*_losses`, `*_captured`, `*_drive_disabled`) + `role` (Sicht des Abrufers) + `npc_name`.
  - `combat/service.py`: offensiver Angriff erzeugt jetzt einen anklickbaren `combat_report`-Funkspruch
    (`decision_payload={report_id, role:"attacker", winner, location}`) zusätzlich zur Persona-Reaktion.
  - `npc/attack.py`: defensiver (auch **offline**) Kampf legt die `report_id` ins `decision_payload`.
- **Frontend:**
  - **NEU** `features/transmissions/combat-report.component.ts`: Modal-Viewer. Ergebnis-Banner aus
    Spieler-Perspektive (Sieg/Abgewehrt/Durchbrochen/Niederlage), beide Flotten (eigene Seite „DU"-markiert:
    Ausgang→Verluste/gekapert/gestrandet/geflohen), Runden-Timeline mit Distanz-Band (🔴 Nah/🟡 Mittel/
    🔵 Fern) + Feuerbalken + Hinterhalt-Runde, Beute + Trümmerfeld.
  - `api.models.ts`: `CombatReport`/`CombatRound` auf die reiche Form gebracht.
  - `transmissions.component.ts`: „⚔️ Bericht öffnen" auf Kampfbericht-Funksprüchen → öffnet den Viewer
    (markiert zugleich als gelesen). `create_system_transmission` pusht das `transmission`-WS-Event → Postfach
    aktualisiert live.
- **Verifiziert:** Frontend `--no-cache` Build sauber (keine TS-Fehler), game-server importiert sauber,
  **52 Backend-Tests grün** (inkl. 4 neue `tests/test_combat_report.py` — Serialisierung aus Angreifer-
  UND Verteidiger-Sicht), API + Frontend liefern 200. Frontend + game-server neu gebaut & deployed.
- **Offen direkt hieran:** Live-Klickdurchlauf steht aus (0 Berichte in DB — frischer Account). Entweder
  echten Kampf auslösen (ändert Spielstand) oder Wegwerf-Account durchspielen.

---

## 0b. Vorige Session (2026-06-08) — Rollen-Kampf Phase 1–4 + 5 asset-freie Features + Frontend
Alles verifiziert (34 Backend-Tests grün + End-to-End-DB-Smokes) und committet:
```
b41135a feat(combat): Rollen-Kampf Phase 3 — Entern/Capture gestrandeter Schiffe
d97ebf9 feat(combat): Rollen-Roster Phase 4 — 12 neue Spezial-Schiffe (Doku 03c)
5bafcf5 feat(fleet): recycle/colonize waehlbar + eingehende NPC-Angriffe im Flotten-Screen
15a403c feat(npc): NPC-Aktivangriff auf Spieler (eingehende Angriffe)
86132aa feat(npc): NPC-Expansion — expansive NPCs gruenden neue Garnisonen
e12cbe9 feat(planets): Kolonisierung — colonize-Mission gruendet Planeten
edc6c03 feat(fleet): Truemmerfeld + Recycler-Harvest-Loop
d900439 feat(economy): Fusionsreaktor verbrennt Deuterium
b175c3b feat(combat): Rollen-Kampf Phase 2 — Antriebs-Stufen + Disengage + Interdiktion
4546bba feat(combat): Rollen-Kampf Phase 1 — Antrieb-Subsystem + Schadenstyp-Matrix + Reichweiten
```
- **Rollen-Kampf Phase 1–4 GEBAUT** (Doku 03b): 3 Subsysteme + Schadenstyp×Subsystem-Matrix
  (`combat.damage_matrix`) + Reichweiten-Bänder (`combat.range_bands`) · Antriebs-Stufen + Disengage
  + Interdiktion (`combat.drive_stages`/`disengage`) · **Entern/Capture** (`combat.boarding`) · **12
  neue Spezial-Schiffe** (`combat_roster`, in der Werft baubar, Assets integriert). Der volle
  **Piraterie-Loop läuft**: EWAR-Ionen stranden → Interdiktor hält → Enterschiff kapert.
- **Frontend:** `recycle`/`colonize`/`mine`/`expedition` im Flotten-Versand wählbar + **eingehende
  Angriffe** als Warn-Banner (`GET /api/incoming-attacks`); 12 neue Schiffe in der Werft.
- **Eskort-Konter + Sondermechaniken:** Punktverteidigung (Eskort-Fregatte) + Schild-Tender
  (Antriebs-Reparatur) · Tarnkappen-Hinterhalt (Überraschungsrunde) + Sensor-Entdeckung als Konter ·
  Träger-Drohnen (ephemer) · Artillerie zur Glaskanone re-tiert (Konter-Dreieck).
- **Mining + Expedition** als Flotten-Missionen (Bergbau-Ertrag / gewichteter Zufalls-Fund).
- **Imperiums-Doktrinen** (Kriegsherr/Händler/Freibeuter/Pionier): Flottenslots, Signatur-Bau-Rabatt,
  Kampf-Angriff; Wahl/Wechsel via `/api/player/doctrine` (Kosten+Cooldown). UI-Screen offen.
- **Fusionsreaktor** verbrennt jetzt Deuterium (Tech-Debt #3 erledigt).
- **Trümmer/Recycler-Loop**: Kämpfe hinterlassen Trümmer (`universe_cells.debris_field`),
  `recycle`-Mission sammelt sie ein.
- **Kolonisierung**: `colonize`-Mission gründet echte Planeten (war Stub).
- **NPC-Expansion**: expansive NPCs gründen Außenposten im eigenen System.
- **NPC-Aktivangriff**: aggressive NPCs greifen ungeschützte Spieler an (eigene
  `npc_attacks`-Tabelle, Warnung + Kampf bei Ankunft, Beute/Verluste/Trümmer, Recovery-fest).

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

**Backend-Tests:** `docker compose cp ../backend/tests game-server:/app/tests && docker compose exec game-server python -m pytest tests/ -q` (32 Tests, grün).
> ⚠ Mehrfaches `cp ../backend/tests` verschachtelt `tests/tests/` (Doppel-Zählung). Vor dem Lauf
> `docker compose exec game-server sh -c 'rm -rf /app/tests'`, dann frisch kopieren.

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
3. ~~Fusionsreaktor verbraucht kein Deuterium~~ → **ERLEDIGT (2026-06-08)**: verbrennt
   `deut_cost_base·lvl·growth^lvl`/h (fix, nicht energie-gedrosselt).
4. ~~NPC-Verhalten: kein Aktivangriff/keine Expansion~~ → **ERLEDIGT (2026-06-08)**: Expansion
   (expansive NPCs gründen Außenposten) + **Aktivangriff** (aggressive NPCs greifen ungeschützte
   Spieler an — eigene `npc_attacks`-Tabelle, Warnung + Kampf bei Ankunft, Beute/Verluste/Trümmer,
   Recovery-fest). Tick-Intervall 1 h (`balance.npc.tick_interval_seconds`).
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
- **Rollen-Kampf (`03b/03c`):** Phase 1–4 GEBAUT (Subsysteme/Matrix/Reichweite · Antrieb/Disengage/
  Interdiktion · **Entern/Capture** · **12-Schiff-Roster** integriert, in der Werft baubar). Der volle
  Piraterie-Loop läuft inkl. **Eskort-Kontern** (Eskort-Fregatte fängt Enterer ab, Schild-Tender
  repariert Antriebe gegen Stranding) → vollständiges Schere-Stein-Papier. **Sondermechaniken
  gebaut:** Tarnkappen-Hinterhalt (Überraschungsrunde) + Träger-Drohnen (ephemere Staffeln). Offen:
  **Phase 5 Söldner-/Markt-Layer**, **Mining/Expedition** als Wirtschafts-Loops, **Sensor-Entdeckung**
  (Stealth-Konter), **Stat-Neutierung der alten Artillerie** (Konter-Dreieck offener Kampf), und die
  **Doktrinen** (Kriegsherr/Händler/Freibeuter/Pionier — Kosten-/Zeit-Boni).
- **Kampf (Roadmap `03a`):** ~~Trümmer-/Recycler-Loop~~ **ERLEDIGT**. Offen: ⭐ **Interception**
  (Flotten im Flug abfangen — verschmilzt mit Disengage aus 03b §6.2), **aktive Commander-
  Faehigkeiten**, **Flaggschiff/Permadeath/Capture**, **Kampf-Simulator** (nutzt jetzt die
  reichere Engine!), Verteidigungs-Spezialmechanik (Schildkuppel max 1/Planet, ABM/IPM).
- **Planeten (`06a`):** Typen/Felder + ~~Kolonisierung~~ **ERLEDIGT** (colonize gründet Planeten).
  Offen: **Gasplaneten + Exotische Materie** (RESERVIERT), Terraformer.
- **Commander (`05a`):** Grade gebaut. Offen: Grade auch via **Expeditionen** finden;
  aktive Faehigkeiten (Doku 05 §6).
- **KI/LLM-Funksprüche** weiterhin bewusst aufgeschoben (Nutzer-Wunsch), bis der Rest rund ist.

---

## 6. Vorgeschlagene nächste Schritte (priorisiert)

### ⭐ Kandidaten für die nächste Session
Rollen-Kampf Phase 1–4 sind gebaut (s. §0b). Naheliegende nächste Schritte:
1. **Frontend an die neue Engine anbinden:** ~~Kampfbericht zeigt Distanz/Fliehen/`drive_disabled`~~
   **ERLEDIGT (2026-06-09, s. §0)** — voller Kampfbericht-Viewer aus dem Postfach (offensiv + defensiv/
   offline). **Offen:** UI für `weapon_type`/Reichweite/Antriebs-Stufen in den **Werft-Schiff-Kacheln**
   + der **Kampf-Simulator** (Doku-Screen ohne Endpunkt — braucht neuen Backend-Endpoint, der
   `simulate_battle` mit Spieler-Eingaben aufruft). Engine ist reich genug.
2. ~~`recycle`/`colonize` im Frontend wählbar~~ **ERLEDIGT (2026-06-08)** — Missionen im
   Flotten-Versand wählbar (mit Pflicht-Schiff-Hinweis) + **eingehende Angriffe** als rotes
   Warn-Banner im Flotten-Screen (`GET /api/incoming-attacks`). Offen: Cockpit/Dashboard-Alert
   (dort liegt noch die uncommittete „Kolonien-Leiste"-WIP — bewusst nicht angefasst).
3. ~~NPC-Aktivangriff~~ **GEBAUT (2026-06-08)** — eingehende Angriffe via `npc_attacks`-Tabelle
   (`npc/attack.py`): aggressive NPCs greifen ungeschützte Spieler an, Warnung im Anflug, Kampf bei
   Ankunft (Spieler = Verteidiger), Beute/Verluste/Trümmer, Recovery-fest. Frontend: Warn-Banner im
   Flotten-Screen (s. o.). Offen: Cockpit-Alert + WS-Live-Update des Banners (statt nur beim Laden).
4. **Phase 3 Entern/Capture** & **Phase 4 Roster-Stat-Neutierung** — brauchen die neuen Rollen-Assets.

### Parallel / sonst offen
- **Assets v0.2:** Nutzer generiert die **§11-Rollen-Assets** (`docs/ASSETS.md`: 12 neue Schiffe +
  Waffen-/Status-Icons + Effekte) — DANN Working Tree (Asset-Umstellung) sauber committen.
- **Spielfluss real durchspielen** (frisches Konto) → Balance/Pacing tunen (`shared/balance.json`),
  inkl. der neuen Kampf-Zahlen (`combat.damage_matrix`/`range_bands`/`disengage`, kinetic-vs-shield 0.25).
- **Gegen-Spionage** (Tech-Debt #5) · **aktive Commander-Fähigkeiten** (Doku 05 §6).
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
| **Kampfbericht-Viewer (Modal) + Read-Path** | `frontend/.../transmissions/combat-report.component.ts` · `backend/app/combat/router.py` (`serialize_combat_report`) |
| **⭐ Rollen-Kampf-System (Design, nächster Build)** | `docs/systems/03b-role-based-combat.md` · `03c-role-roster-spec.md` |
| **Asset-Spezifikation (v0.1 produziert, §11 neu)** | `docs/ASSETS.md` |
| Design-Doku | `docs/` (GDD, ARCHITECTURE, DESIGN_DECISIONS, systems/01–12 + 03a/03b/03c/05a/06a, adr/, ASSETS, STYLE_BIBLE) |

---

## 8. Offene Design-Frage (für dich)
- Bei „automatischem" Fokus wird die Schiffsklasse halb-zufällig gewählt. Soll der **Rang-Aufstieg**
  später auch neue **aktive Commander-Fähigkeiten** freischalten (Doku 05 §6: Konzentriertes Feuer,
  Eilmarsch, …)? Bisher nur passive Boni. → Kandidat für eine eigene Session.

> Alles committet, Working Tree sauber. Viel Erfolg morgen! 🚀
