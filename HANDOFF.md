# 🛰️ Handoff — Universe (Stand 2026-06-13)

> Übergabe für die nächste Session. Projekt: browserbasiertes Weltraum-Aufbau-MMO
> *Universe* (OGame-Tradition + persistentes Universum + KI-Crews als USP).
> Server-Pfad: `/srv/storage/projects/universe` · Branch: `master`.
> Live: `universe.tech-artist.de` · lokal Frontend `:4200`, API `:8100→8000`.
> ✅ **Working tree SAUBER** (Stand 2026-06-13, letzter Commit `6eca7b7` — Audit Runde 1/2). 1 echter Account
> (`sascha-richter@hotmail.com`), Test-Account `uitest@example.com` / `Test1234!`.
> ⚠️ Diese Session lief teils PARALLEL zu einem zweiten Agenten (Asteroidenfelder, Reise-Treibstoff/
> Reichweite, Temperatur-Streuung, UI-Icons) — dessen Arbeit ist mit in den Commits. Alles committet & live.
>
> **KI-Test-Gotcha (neu):** ai-worker-Jobs lassen sich NICHT per `docker exec game-server python` enqueuen
> (event_bus.redis ist im Exec nicht verbunden → still verworfen). Test-Jobs direkt:
> `docker compose … exec -T redis redis-cli LPUSH ai:jobs '{"job_type":"flavor",…}'`. Der ai-worker ist
> SEQUENZIELL auf der RTX 3070 (8 GB) → ~15 s/Job, Queue dauert. Nach Worker-Code-Änderung `build ai-worker`.
>
> **Verifikations-Loop (Sandbox-Eigenheiten — wichtig, s. Memory `project_universe_devloop`):**
> - **Backend-Tests:** `docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm --no-deps -v "$(pwd)/backend/tests:/app/tests" game-server python -m pytest tests/ -q` (mountet nur tests/; **Backend-Code ist ins Image gebacken → nach Code-Änderung erst `build game-server`**, sonst läuft pytest gegen alten Code).
> - **Sim-Check (pure Engine, neue Balance):** `docker compose … run --rm --no-deps game-server python -c "from app.combat.engine import simulate_battle; import json; b=json.load(open('/app/shared/balance.json')); …"` — liest die gemountete shared/balance.json frisch.
> - **Frontend-Compile:** `cd frontend && npx ng build --configuration development` (strikt, ~3–7 s).
> - **Deploy:** Code-Änderung → `build game-server` + `up -d game-server` (lädt Image + gemountete balance neu); reine balance.json-Änderung → nur `up -d game-server` (restart) reicht. Frontend-balance ist gebacken → `build frontend` + `up -d frontend`. **`frontend/src/assets/balance.json` ist ein manueller Mirror von `shared/balance.json` → nach jeder balance-Änderung `cp shared/balance.json frontend/src/assets/balance.json`.**
> - **DB-Schreibzugriff + `docker exec … psql`/Seeden sind Auto-Mode-gesperrt** → Test-Daten nur über API/Spiel. Read-only `docker exec game-server python -c "…"` (ohne rm/cp) ist erlaubt.
> - **NEU — Lint-Guard:** `ruff check backend/app --select F` fängt Undefined-Name/Use-before-Assignment (F821/F823) in <1 s — genau die Klasse der Loop-Breaker, die die Tests NICHT abdecken. Verdrahtet als versionierter pre-commit-Hook (`.githooks/`, aktiv via `core.hooksPath`) + GitHub-Actions (`.github/workflows/lint.yml`). ruff lokal im user-site (`python3 -m ruff`).

---

## 🗓️ Session 2026-06-13 (B) — Audit Runde 1/2 behoben (15 Befunde) + Lint-Guard

> Commit `6eca7b7`, getestet **185/185** (178 + 7 neue Regressionstests), deployt & live.
> Detail-Memory: `project_universe_audit_tooling`.

**Zwei Loop-Breaker lagen LIVE** (nur unentdeckt, weil die Suite die DB-Pfade nicht prüft):
- **#1** `research` UnboundLocalError in `fleet/service.send_fleet` → Angriff/Abfangen crashten.
- **#12** fehlender `Planet`-Import in `fleet/trade.py` → Handel mit Routenrisiko crashte.

Weiter behoben: #2 Engine sortiert Units (Determinismus, Permutations-Test), #3 Abfang-Verteidiger
nutzt echte Forschung, #4 Hinterhalt = **nur Stealth-Schiffe feuern** in der Überraschungsrunde
(Verteidiger vorbereitet), #5 neuer ausgewogener weapon_type `orbital` + Roster-Eintrag (+ Roster-
Vollständigkeitstest), #6 Deut-bewusste **stückweise** Lazy-Accrual (`accrue_amount`, Fusion-aus via
`fusion_reactor=0`, 4 Tests), #7 `catalog_items()`-Helper, #8 max_rounds=8 (Doku angeglichen),
#9/#15 Notizen, #10 zivile attack-Werte als Proxy dokumentiert (NICHT genullt — `fleet_power`/
`station_power` lesen sie), #11 Report zeigt echten Schaden, #13 toter Code weg, #14 `/combat/simulate`
optional `defender_tech`.

> ⚠️ **Achtung Engine-Math:** bei #11 wäre fast `target.hull -= …` durch `applied += …` ersetzt statt
> ergänzt worden → 7 Tests rot. Nur der Suite-Lauf gegen das NEU gebaute Image fing es. Engine nie
> ohne `build game-server` + pytest anfassen.

---

## 🗓️ Session 2026-06-12/13 (MARATHON) — Flug/Abfang-Überholung + NPCs lebendig + KOMPLETTE KI-Roadmap

> Sehr große Session. Alles committet (`6f12f07` … `e7c6f0f`), getestet (**178/178**), deployt & live.
> Detail-Memories: `project_universe_fleet_pvp`, `project_universe_ai` (neu). Reihenfolge unten = grob chronologisch.

### ⚙️ Flugzeiten + Abfang-Redesign (`6f12f07`, `569be3b`, `3801973`)
- **OGame-Flugzeiten:** Distanzklassen waren Platzhalter + Konstante `3500` statt `35000` → Flüge dauerten
  SEKUNDEN. `compute_distance` jetzt echtes OGame-Modell (Position im System zählt). **Eigener Regler
  `universe.fleet_speed` (1.0)** entkoppelt Flottentempo von `universe.speed` (=Produktion). Nachbarsystem-
  Kolonieschiff ~20 min @Antrieb 0. Antriebsforschung wirkt (war schon da).
- **In-Flug-Abfang neu, GETRENNTE ACHSEN:** Fangen = nur Abfangjäger (1 %/Schiff, Cap **90 %**) + Forschung
  `hyperspace_interdiction` (0,5 %/Stufe, reservierte letzte 5 %, Cap **95 %, nie 100 %**). Interdiktor fängt
  NICHT mehr — er pinnt nur im Kampf (`engine.disengage_phase`). → Forschung immer wirksam.
- **Patrouille kostet 1 Flotten-Slot** (`service.py used_fleet_slots`) → harte Obergrenze gegen Omnipräsenz.
- **Treibstoff:** Tank = mitgeführtes Deuterium (länger patrouillieren = Transporter mitladen). Vorgeschoben
  zehrt immer (Modell C); eigenes Gebiet nur als Patrouille + langsamer; Starter-Tank für Sofort-Heim-Patrouille.
- **„Abfangen" als eigene Mission** (`intercept`) im Flotten-Versand + Radius (Default **0**, Cap **6** via
  Forschung); der verwirrende Intercept-Schalter im Handel-Tab ist raus (nur noch read-only Status + Rückruf).
- **Hinterhalt-Entdeckung weich** (Tief-Aufklärer): analog Abfangen (1 %/Sensor, Cap 90 %, spy_tech die letzten
  5 %). Tief-Aufklärer-Text korrigiert (war irreführend „Langstrecke", ist Anti-Tarnkappe).

### 👾 NPCs lebendiger (`569be3b`, `a8efad4`)
- **NPC-Tier-Skalierung** (hergeleitet, kein DB-Feld): Kombi Region (Kern-Entfernung) + nächster Spieler
  (`Player.score`). Skaliert Garnison, Einkommen, Loot-Cap UND Tech gemeinsam → NPCs wachsen mit (waren vorher
  trivialer Fix-Level-Loot). NPC-Verteidiger hatten vorher **Tech 0** — jetzt Basis 4 + Tier.
- **Dichte-Sicherungen:** je System bleiben ≥ `reserve_positions_per_system` (5) Plätze FREI für Spieler
  (Spawn + Expansion blocken); **NPC-Decay** entfernt verwaiste NPCs (nächster Spieler > 30 Sys weg) im
  Populations-Tick (Handelszentren ausgenommen, Schonfrist 1 h).
- **Kolonie-Limit** OGame-Stil: base 3, +1/Astrophysik-Stufe, hart bei 20 (war fix 9 inkl. Heimat).
- **Galaxie-View:** Galaxie/System-Eingaben auf Universums-Max (8 / 200) begrenzt.

### 🤖 KI-Roadmap KOMPLETT (Phase 0–5) — `a8efad4`, `7649a67`, `5d98814`, `42541dd`, `e7c6f0f`
> Detail in Memory `project_universe_ai`. Alles über die entkoppelte ai-worker/Ollama-Pipeline (llama3.1:8b).
- **Phase 0:** nightly_batch läuft automatisch (24h-Scheduler + Startup-Bootstrap) — vorher liefen Banken leer.
- **Phase 1:** NPC-Personas + Diplomatie-Funksprüche (Schema verallgemeinert: `reaction_banks.npc_id`,
  `npc_empires.persona`). 4 Trigger: NPC greift an / du greifst NPC an / Spionage entdeckt (35 %) / Ambient.
  Fallback-Templates → greifen sofort, werden charaktervoll sobald Banken voll.
- **Phase 2:** Spionage- & Expeditions-Flavor via neuem `flavor`-Job (Erzähler-Stimme, kein Entity/Bank, Live).
- **Phase 3a:** evokative NPC-Namen per LLM („Aschefürsten von Khrazix" statt „Handelsgilde 8901"; `named`-Marker
  benennt auch Alt-NPCs um). System-Lore (3b) bewusst ausgelassen (schwächster Posten).
- **Phase 4:** Galaxie-Nachrichten-Ticker — `messaging/news.py` aggregiert größte Schlacht (6h) → Broadcast-
  flavor-Job (Erzähler `news_anchor`, an alle Spieler).
- **Phase 5:** Spieler-Berater — `messaging/advisor.py` fasst Imperiums-Zustand + Schwachstellen zusammen →
  advisor-flavor-Job mit Empfehlungs-Anweisung. Frontend: „🧠 Berater fragen" im Postfach, Rat kommt via WS.

### 🔭 Offen / für morgen
- **KI optional (alle im Memory `project_universe_ai`):** Modellwechsel **`gemma2:9b`** (`! ollama pull gemma2:9b`,
  dann `OLLAMA_MODEL` in `infra/.env` + `up -d ai-worker`) — besseres Deutsch + mehr Namens-Varianz, wertet ALLE
  KI-Features auf einmal auf. 2 NPCs scheitern gelegentlich am Persona-JSON (llama3.1 8B) → heilen via Nacht-Tick.
  Weiter offen: System-/Sektor-Lore (3b), adaptive „Haltung"-Schicht (LLM setzt offline NPC-Posture), echte
  Tribut-Mechanik (Phase 1 war nur Flavor).
- **Kampf/Abfang im echten Spiel fühlen + tunen:** die Balance-Knöpfe (damage_scale etc., fleet.speed, Abfang-Cap,
  Hinterhalt-Cap). Reine balance.json → `cp` in frontend/assets + `up -d game-server`.
- **In-Game-Klick-Smoke** vieler Mechaniken steht weiter aus (Test-Account ist dünn; DB-Seeding gesperrt):
  Abfang-Mission, Treibstoff-Leerlauf→Rückkehr, NPC-Tier im Kampf, Mondzerstörung, Trümmer-Recycling.
- Älteres weiter offen: NPC-Carrier-Tuning, Gegen-Spionage.

---

## ⚔️ Session 2026-06-11 (Teil 2, GROSS) — Kampf-Redesign 03d (Rapidfire abgeschafft) + Treibstoff-Unterhalt

> Spec: **`docs/systems/03d-combat-redesign-rapidfire-roles.md`** (Quelle der Wahrheit). Detail-Memory:
> `project_universe_combat` (auf erledigt aktualisiert). **Alles gebaut, getestet, deployt & live.**
> Backend-Suite **127/127 grün**. Working Tree sauber.
>
> ⚠ **WICHTIG — überholt:** Der „Rapidfire-Konter-Kreis" aus Teil 1 (Commit `3dbdd2e`) wurde in diesem
> Redesign **wieder ENTFERNT**. Schiff-vs-Schiff-Rapidfire gibt es nicht mehr. Nicht reaktivieren.

**Warum (mit dem Nutzer erarbeitet):** OGames Rapidfire degeneriert zur Monokultur, weil es die einzige
Anti-Masse-Bremse der Engine — **Overkill verpufft** (1 Schuss/1 Ziel, Rest verloren) — aushebelt
(Kette auf frische Ziele = nie verschwendet). Lösung: **Rapidfire zwischen Schiffen komplett raus.**

**Phase 1 + Letalitäts-Modell (`b5c348b`):**
- Alle Schiff-vs-Schiff-`rapidfire` entfernt; **nur Bomber** behält Anti-Verteidigung (Türme + Solarsat/
  Sonde-Chaff). Rückgrat = **Schadenstyp×Subsystem-Matrix** (Energie strippt Schild → Kinetik/Rakete
  zerlegt Hülle → Ionen lähmt) + Reichweite + Overkill + Rollen-Mechaniken.
- **Befund:** Rapidfire trug ~5–7× der Letalität (Schild regenerierte voll/Runde + 6 Runden). Ohne es Patt.
  → Engine: **Schild = abnutzbarer Puffer** (`combat.shield_regen_ratio=0.3`, Teil-Regen statt voll),
  **globaler Letalitäts-Regler** `combat.damage_scale=2.0`, `max_rounds 6→8`, Kinetik-vs-Schild `0.25→0.1`.
- **Das sind die 4 zentralen Tuning-Knöpfe.** Sim-belegt: KOMBI (Energie+Kinetik) schlägt Mono beidseitig,
  Schlachten lösen sich entscheidend-mit-Verlusten; Glaskanone/Entern/Schild-Matrix intakt.

**Phase 2+3 (`a2f36ce`):** Abfangjäger war Auto-Pick (4000 Kosten / 400 Energie-Schaden) → 12000 via
**Deuterium** (bleibt fragil, da Hülle=(Metall+Kristall)/10). Zerstörer = **Glaskanone** bestätigt. Jedes
Schiff bekommt **Werft-Stufe als Bauvoraussetzung** (`requires.shipyard` 1–12) → die 9 impulse_drive-
Schiffe verteilen sich über Werft 2–7 (Backend prüft generisch, kein Code).

**Phase 4 — Todesstern (`a5d9507`):** Star-Wars-stimmig: kämpft NICHT gegen Schiffe (Overkill), ist
**Drohnenträger** (`combat.carrier.capacity_by_type` carrier 8 / deathstar 50, per `computer_tech` bis 100)
+ **Mondzerstörung** (`moon.maybe_destroy_moon`, `balance.moon.destruction`): nach gewonnenem PvP-Angriff
belagern überlebende RIPs den Ziel-Mond, Chance ~ Anzahl/Mondgröße, **Rückschlag-Risiko**, löscht den Mond
+ Funksprüche. Träger-Beladung in `send_fleet` auf Kapazität pro Typ verallgemeinert.

**Treibstoff-Unterhalt — Modell C (`23e4d7e`):** Stationierung war gratis-für-immer (auch vorgeschoben).
Jetzt: **eigenes Gebiet gratis** (`StationedFleet.fuel=NULL`), **vorgeschoben** (fremde Koordinaten) trägt
das mitgeladene Deuterium (Deploy-Fracht) als **Vorrat**; `station_fuel_tick` (stündlich, `balance.fleet.
station_fuel`) zehrt ihn (`upkeep_ratio_per_tick=0.05 × Σ Schiff-fuel`), **leer → Zwangs-Rückkehr** heim.
UI im Handel-Tab: „🏠 gratis" / „⛽ N Deut". Migration 47 (`stationed_fleets.fuel`).

**⚠ Verifikations-Stand:** Pure-Formeln (Letalität, Träger-Kapazität, Mond-Chance, Upkeep) sind **getestet**
(127/127). Die **DB-Pfade** (Mond-Löschung, Drohnen-Beladung, Treibstoff-Tick/Zwangs-Rückkehr) sind
pure-function + Compile + Live-Startup verifiziert, aber **NICHT echter In-Game-Klick-Test** (Test-Suite
rein pure-function, DB-Schreibzugriff gesperrt).

### 🔭 Für morgen / offene Punkte
- **Kampf im echten Spiel fühlen + tunen:** die 4 Knöpfe (`damage_scale`, `shield_regen_ratio`, `max_rounds`,
  kinetic-vs-shield). „Tödlicher/schneller" → `damage_scale` hoch; „Schilde brechen leichter" → `shield_regen_ratio`
  runter. Reine balance.json → nur `up -d game-server` (restart) + `cp` in frontend/assets.
- **In-Game-Smoke der DB-Mechaniken** (sobald Daten da sind): Todesstern+Drohnen auf Angriff; Mondzerstörung
  (braucht PvP-Mond — Monde entstehen aus Kämpfen); vorgeschobene Stationierung → Vorrat leerlaufen → Auto-Rückkehr.
- **Kosten-Feintuning** restlicher Schiffe (Phase 2 war nur der Abfangjäger-Fix; Rest plausibel, aber playtest-bedürftig).
- **Mond-Frontend-Klicktest** (Sprungtor-Dialog) steht weiter aus (kein Mond am Test-Account; DB-Seeding gesperrt).
- Älteres weiter offen: NPC-Carrier-Tuning, Gegen-Spionage, LLM-Funksprüche (Nutzer aufgeschoben).

---

## 🚀 Session 2026-06-11 (Teil 1) — Aufräumen · Antriebs-Tempo-FIX · Mond-Frontend · ~~Rapidfire-Konter-Kreis~~ (überholt)

> Reihenfolge: erst die offenen Reste committet, dann Backend-Suite verifiziert, dann den
> Antriebs-Tempo-FIX gebaut. **Alles committet, gebaut, deployt & live** (API `:8100`).
> Backend-Suite **124/124 grün** (121 + 3 neue). Working Tree nach dieser Session sauber.

**Aufgeräumt (committet):**
- `07568f9` chore(assets): 21 PNGs (6 Mondgebäude, `orbital_gun`, restliche Tech-Icons).
- `346c474` feat(display): Mond/Tech-Labels in `display.ts` + Popup-Doppel-★-Fix (`detail-popup`
  unterdrückt das generische ★-Banner, wenn schon eine reiche TechEffect-Ansicht rendert).

**Verifiziert:** volle Backend-Suite vor dem Build = **121/121 grün** (`run --rm`-Pfad).

**⚙️ Antriebs-Tempo-FIX (`18f7b2f`) — der lange offene Punkt, jetzt erledigt:**
- **Bug:** `combustion_/impulse_/hyperspace_drive` waren nur Bau-Voraussetzung; die Flugzeit (ETA)
  ignorierte die Antriebsforschung komplett (grep belegte: in keinem Flug-Modul gelesen).
- **Fix in `fleet/service.py`:** neue reine Funktion `ship_speed(typ, research)` →
  `Grundtempo × (1 + per_level × Stufe)`. Der **Reiseantrieb wird aus den Bau-`requires` abgeleitet**
  (Priorität hyperspace > impulse > combustion) — KEINE Duplikation eines `drive_type`-Felds über
  25 Schiffe, self-maintaining. `slowest_ship_speed(ships, research)` nimmt jetzt Forschung; die
  langsamste Einheit bestimmt weiterhin die ETA. **Bewusst getrennt** vom Kampf-`drive`
  (`combat_roster[*].drive` / `combat.drive_stages` = Disengage/Interdiktion).
- **Wiring:** `send_fleet` (`service.py`) + `recall_station` (`stationing.py`) holen
  `get_research_levels` und reichen es durch. **NPC-Pfad** (`npc/attack.py`) ruft ohne `research`
  → kein Bonus → Verhalten unverändert (keine Regression).
- **Balance** (`balance.research.effects`, OGame-Werte): `combustion_drive_speed_per_level` 0.10,
  `impulse_drive_speed_per_level` 0.20, `hyperspace_drive_speed_per_level` 0.30. `flight_seconds`-
  Formel unverändert (Effekt steckt sauber im skalierten `slowest_speed`).
- **Tests** (`tests/test_fleet_missions.py`, 3 neue, exakte Zahlen): `ship_speed`-Skalierung
  (light_fighter 12500→18750 @combustion 5, battleship 10000→19000 @hyperspace 3, escort_frigate
  unverändert mangels Reiseantrieb), `slowest_ship_speed` mit Forschung, ETA-Reduktion.
- **Runtime-Smoke:** read-only `docker exec` gegen den **deployten** Container bestätigt die Skalierung
  live (ETA @dist95 sinkt 2,81 s→2,55 s bei combustion 5). Effekt bei kurzen Strecken durch den
  Fixkosten-Term `+10` gedämpft, nähert sich auf Fernflügen ~22,5 % — Antrieb lohnt v. a. weit.
- **Frontend:** rechnet KEINE ETA client-seitig (grep nach `3500`/`sqrt`/`slowest` leer) → maßgebliche
  Flugzeit rein serverseitig, keine Inkonsistenz, kein Frontend-Change nötig.
- **⚠ Echter In-Game-Klick-Smoke offen:** Test-Account `uitest@example.com` ist frisch (keine Forschung,
  kein Labor, kaum Ressourcen) → eine echte „Antrieb hochforschen → Flotte senden → kürzere ETA"-Kette
  bräuchte erst Spielfortschritt. Formel + Wiring sind unit- und container-verifiziert.

**🌑 Mond-Frontend (`2dbdc38`) — der offene „Mond-Frontend tiefer"-Punkt, jetzt erledigt:**
- **Architektur-Entscheidung: KEINE neue Route.** Der aktive-Planet-Kontext (`game-state.selectPlanet`)
  treibt bereits Topbar/Gebäude/Werft/Flotte; ein Mond ist ein vollwertiger Planet-Eintrag, und der
  Gebäude-Endpoint filtert serverseitig auf Mond-Gebäude. Eine eigene Route würde das duplizieren.
- **Neuer `shared/components/jump-gate-dialog.component.ts`** (Modal/Ship-Picker aus `fleet-dispatch`
  geklont): Zielmond-Auswahl aus den eigenen Monden, Garnison-Schiffspicker, **Deuterium-Sprungkosten +
  Cooldown live vorgerechnet** aus `balance.json` (`moon.jump_cost_*`) + `jump_gate_tech` — **exakt wie
  Backend `jump_fleet`** (cost_mult·base·Σ(class_mult·count); cd_mult mit floor 0.4). Fehler via
  `err.error.detail`, `reloadActivePlanet` nach Sprung.
- **Dashboard:** auf einem Mond erscheinen **🪐-Planet-Chip** (zurück zum Mutterplaneten, Koordinaten-Match)
  + **🌀-Sprungtor-Button** (nur wenn `jump_gate` gebaut) → öffnet den Dialog.
- **API:** `api.jumpFleet(POST /api/fleets/jump)`; `PlanetDetail`/`PlanetDetailOut` um `parent_planet_id`
  + `last_jump_at` erweitert (Backend `economy/schemas.py`+`router.py`, für Cooldown-Vorschau).
- **⚠ `frontend/src/assets/balance.json` war VERALTET** (Stand 10.6., vor der Sprung-Ökonomie) → auf
  `shared/balance.json` gesynct. **Merke:** die FE-Kopie ist ein manueller Mirror von shared und driftet —
  nach balance-Änderungen `cp shared/balance.json frontend/src/assets/balance.json` nicht vergessen.
- **Verifiziert:** `ng build` (strict) sauber, Backend 124/124, API liefert die neuen Felder, Dashboard
  rendert sauber (Screenshot). **⚠ Mond-spezifische UI visuell NICHT geprüft:** Test-Account hat keinen
  Mond (Monde entstehen nur aus Kämpfen), DB-Seeding ist Auto-Mode-gesperrt. Logik per strict-Compile +
  Code-Review abgesichert. Für echten Klick-Test: 2 Monde mit Sprungtor + Garnison + Deuterium seeden
  (braucht Freigabe für DB-Schreibzugriff) ODER per Kampf einen Mond entstehen lassen.

**⚔️ Rapidfire-Konter-Kreis (`3dbdd2e`) — auf Nutzer-Hinweis, „nicht vollständig durchdacht":**
- **Befund:** Die Rapidfire-Matrix deckte nur den **klassischen OGame-Kern** (Jäger/Cruiser/Battleship/
  Battlecruiser/Bomber/Destroyer + interceptor) und den **Todesstern** (RF gegen alles) ab. Die **12 Phase-4-
  Spezialschiffe** (carrier, drone, interdictor, ewar_frigate, boarder, stealth_corvette, escort_frigate,
  shield_tender, miner, deep_scout, expedition_ship) + die Mond-`orbital_gun` hingen **außerhalb** des Schere-
  Stein-Papier: gaben kein sinnvolles RF (nur spy/solar-Boilerplate) **und wurden von nichts gekontert**.
- **Fix (nur Ergänzungen in `balance.json`):** cruiser→+interceptor/ewar/boarder/stealth (schließt den
  interceptor-Kreis); battlecruiser→+interceptor/escort/ewar; destroyer→+carrier/interdictor/shield_tender;
  battleship→+carrier/interdictor; escort_frigate→+boarder/stealth (Punktverteidigung = Design-Absicht
  „fängt Enterer ab"); interceptor→+bomber; bomber→+orbital_gun 10; deathstar→+orbital_gun 50.
- **Bewusst rapidfire-FREI** bleiben die Effekt-Spezialisten (ewar/interdictor/boarder/shield_tender/carrier) —
  Stärke = Spezialeffekt —, sie sind jetzt aber **konterbar**. Reine Nicht-Kämpfer (cargo/colony/recycler/
  miner/deep_scout/expedition, Schildkuppeln, Raketen) bleiben absichtlich außen vor.
- **Verifiziert:** Analyse bestätigt „0 ungekonterte Kampfeinheiten", JSON valide, 124/124, Live-Container hat
  die neue Matrix geladen (game-server nur **restartet** — `shared/` ist read-only gemountet, `get_balance`
  cached beim Start; Frontend-balance.json neu gebaut). **Engine-Semantik:** `rf>1` ⇒ Kettenschuss-Wahrsch.
  `(rf-1)/rf`; Verteidigung läse `rapidfire_against` (bleibt leer). **⚠ Laufzeit-Balance (Multiplikatoren) noch
  nicht im echten Spiel getunt** — erster kohärenter Wurf, im Simulator/Spiel nachjustierbar.

---

## 🌑 Session 2026-06-10 (sehr spät, Mond-Strang/Forts.) — Monde fertig · Sprungtor-Ökonomie · UI-Politur · Screenshot-Pipeline

> Forts. des Mond-Strangs. Detail-Memory: `project_universe_moons`, `reference_universe_ui_screenshots`.
> **Alles gebaut, deployt, live** (Frontend `:4200`, API `:8100`). Backend-Suite **grün** (121/121).

**Monde — KOMPLETT & live** (Spec `docs/systems/08-moons-and-warfare-buildings.md`):
- **Entstehung** aus Trümmerfeld nach Kampf an einem Spieler-Planeten (`app/planets/moon.py` `maybe_form_moon`,
  Cap 20 %, per `gravitics`-Forschung erhöhbar). Mond = Planet (`planet_type='moon'`, `parent_planet_id`, gleiche
  Koordinate), keine Minen, wenige Felder (Mondbasis hebt sie). Mond-only Bau-Filter + `requires` in
  `buildings/service`. **Migration 46** (`planets.parent_planet_id`, `last_jump_at`). Hooks in `combat/service`
  (PvP) + `npc/attack`.
- **Mond verteidigt den Planeten:** Orbitalbatterie (`orbital_gun`, `virtual:true`) + Schildkuppel (Schild-Tech-
  Bonus) via `moon_defense_support` in `resolve_attack` + `npc/attack` (fremde Flotte trifft den Mond nicht direkt).
- **Sprungtor:** `POST /api/fleets/jump` (instant zwischen 2 eigenen Monden). **Kosten nach Schiffsklasse**
  (`balance.moon.jump_cost_base_deuterium` × `jump_cost_class_mult`: fighter/civil 1, cruiser 2, capital 4 →
  Träger 4×), Cooldown 60 min; beides per `jump_gate_tech` reduzierbar. Befördert nur Schiffe (keine Ressourcen).

**4 Forschungs-Techs (= die „4 Mond-Techs"):** `jump_gate_tech` (−Cooldown/−Sprungkosten), `phalanx_tech`
(+Scan-Reichweite/−Scankosten), `gravitics` (+Mond-Chance-Cap/+Orbitalgeschütze), `convoy_tactics`
(−**NPC-Piraten**-Routenrisiko — ehrlich beschriftet: hilft NICHT gegen Spieler-Abfangen). Skalare in
`balance.research.effects`; Effekte in `fleet/service` (jump), `fleet/phalanx`, `planets/moon`, `fleet/trade`.

**UI-Politur (jede per echtem Screenshot verifiziert — Pipeline s. u.):**
- **Auto-Reload:** Gebäude/Forschung/Werft luden ihre Liste nicht bei Fertigstellung → GameState-Versions-Signale
  (`buildingsVersion`/`researchVersion`/`shipyardVersion`) + Werft pusht jetzt `shipyard_complete` (fehlte).
- **Postfach** Filter → `app-tab-bar`; **Handel** `.card-title` → `.panel-title` (Konsistenz).
- **Flotte entschlackt:** redundante eingebettete Galaxie-Tabelle raus (→ Verweis auf `/galaxy`).
- **Simulator:** „🚀 Meine Flotte" (Garnison übernehmen) + „🧹 Leeren" + Summen-Badge je Seite; virtuelle
  `orbital_gun` aus Werft- UND Simulator-Liste gefiltert.
- **Galaxie:** Race-Condition-Fix → Scanner öffnet aufs **Heimatsystem** statt leerem 1:1.
- **Dashboard:** 🌑-Mond-Chip in der Planeten-Zeile (Klick → wechselt zum Mond).
- **Kampfbericht** (`combat-report.component`): echte Schiffs-/Verteidigungs-Bilder statt Emoji-Fallback (via
  `app-icon-tile`) — wirkt auch im Postfach (gleicher Component).

**🆕 Screenshot-Pipeline (NEU, wiederverwendbar — Memory `reference_universe_ui_screenshots`):** Chrome ist jetzt
installiert (`/opt/google/chrome/chrome`; kein X-Server → MCP-Browser geht nicht, headless schon). Headless-Shot:
`google-chrome --headless=new --no-sandbox --virtual-time-budget=8000 --screenshot=/tmp/x.png URL`. **Eingeloggte**
Seiten via puppeteer-core (`/tmp/node_modules`) + Token in `localStorage['universe.token']`:
`node /tmp/shoot.js /dashboard /fleet …`. **Test-Account `uitest@example.com` / `Test1234!`**. ⚠ Direkte
DB-Inserts (Seeden) sind Auto-Mode-gesperrt → Daten nur über API/Spiel.

**✅ Test-Befehl, der in der Sandbox FUNKTIONIERT** (einfacher als der `cp/exec`-Pfad in §2/§3):
`docker compose -f infra/docker-compose.yml --env-file infra/.env run --rm --no-deps -v "$(pwd)/backend/tests:/app/tests" game-server python -m pytest tests/ -q` → 121/121 grün. Frontend-Compile: `cd frontend && npx ng build --configuration development`.

---

## ⭐ Session 2026-06-10 (spät, Claude-Hauptstrang) — Kampf-Redesign · Rangliste · Forschungsbaum · UI-Kacheln · Carrier

> Parallel lief ein **zweiter Agent an MONDEN** (moon_base/sensorphalanx/orbital_battery/shield_dome_moon/
> gravity_lab/jump_gate, 4 Mond-Techs, orbital_gun) — geteiltes Working-Tree, dieser Agent committet selbst.
> Detaillierte Notizen in der Auto-Memory: `project_universe_combat.md`, `project_universe_ranking.md`,
> `project_universe_frontend.md`. **Alles unten ist gebaut, deployt und live** (Frontend `:4200`, API `:8100`).

**Geliefert & live:**
- **UI-Kohärenz (OGame-Stil):** neue geteilte Komponenten `shared/components/build-tile.component.ts`
  (quadratische Kachel) + `tab-bar.component.ts` (Reiter) + globale `.tile-grid`/`.tab-bar`/`.full`.
  **Gebäude, Forschung, Werft** auf **Reiter + Kachel-Grid** umgebaut (vorher gestapelte „Streifen"). Werft hat
  Verteidigungs-Tab + `ownedCount`-Badge. Muster bewusst auch für **Flotte/Handel** wiederverwendbar (noch offen).
- **Rangliste/Punktesystem** (OGame): `backend/app/ranking/` (Imperiumswert = investierte Ress/1000, sinkt bei
  Verlust), `GET /api/ranking` (rechnet frisch + schreibt `Player.score`), Scheduler-Tick `score_tick` (5 min),
  `/ranking`-Screen + Nav „Rangliste" + Dashboard-„Imperiums-Punkte"-Hero.
- **Kampf-Redesign A+B+C:** (B) Abfangjäger-Anti-Jäger-Rapidfire; (C) **Ionen legen Verteidigung lahm**
  (`combat.defense_disable`, Engine: Verteidigung hat System-Integrität, Ionen-drive-Schaden → Geschütz feuert
  nicht mehr); (A) **Abfangen im Flug** via dedizierter Patrouille + Interdiktor (`fleet/interception.py`,
  `StationedFleet.intercept_enabled/radius`, Hook in `send_fleet`, Endpoint `PUT /api/stationed/{id}/intercept`).
  **Heim-Patrouille** (`POST /api/planets/{id}/patrol` — Garnison sofort als Abfang-Patrouille) + Rückruf-UI auf
  der Flotte-Seite. Engine gibt jetzt das **volle Forschungs-Dict** in den Kampf (für forschungs-skalierte Techs).
- **Carrier/Drohnen Option A:** ephemeres Drohnen-Spawnen ENTFERNT; Träger lädt beim **Angriff** echte Drohnen aus
  der Garnison nach (`combat.carrier.drone_capacity=8`), die als echte Schiffe mit echten Verlusten kämpfen. Test
  `test_combat.py::test_carrier_drones_are_real_no_ephemeral` neu geschrieben.
- **Forschungsbaum 17 → 26 Techs**, alle mit verdrahtetem Effekt: hyperspace_interdiction, ion_disruptors,
  boarding_doctrine (Kampf, engine); leadership_doctrine, tactical_academy, crew_psychology-FIX, logistics-Regen
  (Kommando, `commander.service.morale_drift_tick`/`_apply_commander`); mining_efficiency, storage_tech,
  astrophysics, expedition_tech (Wirtschaft, `economy/service`+`colonize`+`expedition`). Skalare in
  `balance.research.effects` bzw. `balance.combat.*`.
- **Reiche Tech-Detailansicht:** `TECH_EFFECTS` in `display.ts` (Branch + Summary + „aktuell→nächste Stufe");
  Popup zeigt „Schaltet frei" mit benötigter Stufe.
- **Kolonisieren-Schnellaktion** 🌱 an leeren Galaxie-Zellen → öffnet fleet-dispatch mit Mission „colonize"
  (fleet-dispatch um colonize erweitert). Kolonieschiff wird bei Erfolg um 1 verbraucht.
- **Universe-Größe** auf **8 Galaxien × 200 Systeme** (balance.universe). **Abfang-Radius** lokal: cap 5, Default 1
  (per Forschung Hyperraum-Interdiktion erweiterbar).
- **Assets:** kompletter Icon-Satz integriert/verdrahtet (nav, tech, traits, missions, weapons, status, ranks,
  planets, range, spec) + Defense-Platzhalter durch echte Renders ersetzt; 9 neue Tech-Icons + 11 Mond-Assets
  (4 Tech, 6 Gebäude, 1 Verteidigung) gepullt/kopiert/live. Mond-Gebäude/Verteidigung/Tech-Labels in `display.ts`.

**⚠ Uncommitted im Working-Tree (Stand jetzt):** `frontend/src/app/core/models/display.ts` +
`shared/components/detail-popup.component.ts` (Mond-Labels + Popup-Doppel-★-Fix) sowie **20 neue Asset-PNGs**
unter `frontend/src/assets/img/{tech,buildings,defenses}/`. Der Großteil der obigen Arbeit wurde im Lauf der
Session bereits committet (u. a. durch den Mond-Agenten-Flow); diese Reste noch **committen**.

**⚠ Test-/Verifikations-Stand (wichtig):** Engine-Änderungen (Ionen-Disable, Ionen-Disruptoren, Boarding, Carrier)
**pure-function verifiziert**. NICHT runtime-getestet (Prod-Container-Exec war permission-gesperrt, am Host kein
sqlalchemy/pytest): die forschungs-skalierten **Wirtschafts-/Kommandeur-/Kolonie-/Expeditions-Effekte**,
**Abfangen im Flug**, **Heim-Patrouille**, **Carrier-Auto-Beladung**. → **Morgen zuerst:** volle Backend-Suite
im Container fahren (`docker cp backend/tests` + `docker exec … pytest`) + In-Game-Smoke-Test (Träger+Drohnen auf
Angriff; Patrouille mit/ohne Interdiktor; Forschung baut Effekt auf).

**Offene Punkte / nächste Schritte:**
- ~~**Antriebs-Tempo-FIX**~~ **ERLEDIGT (2026-06-11)** — Antriebsforschung beschleunigt jetzt Flotten (`18f7b2f`, s. Session-Sektion oben).
- **NPC-Carrier** ohne ephemere Drohnen evtl. leicht geschwächt — ggf. NPC-Flotten Drohnen mitgeben/nachtunen.
- **Flotte- & Handel-Screen** noch nicht auf das Kachel/Tab-Muster umgestellt; einheitlicher **Seiten-Kopf** für alle Screens steht aus.
- Unverdrahtete Platzhalter weiterhin offen: `commanders/frames`+`commanders/spec` (Portrait-Layer), `backgrounds/region_*`.
- `orbital_gun` ist `virtual:true` (aus Orbitalbatterie abgeleitet) — kein eigenständiger Bau-Tile nötig.

---

## -2. Session 2026-06-10 (Forts.) — HANDELS-REDESIGN: NPC-Handelszentren (Phase 1 fertig + live)
**Design mit Nutzer durchgesprochen, Phase 1 (NPC-Seite) gebaut, 115/115 Tests gruen, deployed.**
```
2824928 feat(trade): Handelszentren im UI — Kurs immer sichtbar
80cdd86 feat(trade): unangreifbare Handelszentren mit globalem Kurs-Index
```
**Gemeinsam beschlossenes Gesamtmodell (zwei Handelsarten):**
- **NPC-Handel (Phase 1, FERTIG):** neutrale, **unangreifbare** „Handelszentren" (behavior_profile
  `trade_center`) quoten einen **universumsweiten** Kurs. `Kurs_r = base_value_r*(neutral_r+V_r)/(weltvorrat_r+V_r)`.
  weltvorrat = liquider Spieler-Vorrat (EMA-geglaettet), neutral_r = neutral_per_player_r*aktive_spieler
  (skaliert mit Population), virtual_reserve V gross -> stabil + nahe base bei wenig Spielern, zugleich
  Order-Tiefe. **Trick:** als synthetischer Markt (setpoint=neutral+V, stock=vorrat+V) in den vorhandenen
  `price_of`/`simulate_swap` gespeist -> Slippage automatisch, keine neue Swap-Logik. Spread = `margin`
  (Spieler-P2P kann immer unterbieten -> kein OGame-Automat). Module: `fleet/trade_index.py`,
  `WorldMarket`-Singleton (Migration), `index_tick`, `ensure_trade_centers` (seedet 6, fuer alle sichtbar),
  Unangreifbar in `send_fleet`, `GET /api/trade/index`. balance: `trade.index`. Frontend: Kurs IMMER
  sichtbar (kein „erst aufklaeren"), 💱-Handelszentrum-Badge, „Angreifen" an Zentren aus.
- **P2P-Handel (Phase 2, FERTIG + live — Commits c6923be/1049d17):** **klassisch wie OGame, KEIN Automat/
  Escrow.** Gebaut: (a) Spieler-Handelsprofil (`players.trade_enabled/offer/want/rate/note`) — unverbindlicher
  Werbe-Kurs + an/aus; GET/PUT `/api/trade/profile`, GET `/api/trade/partners`. (b) Galaxie zeigt am Spieler-
  Planeten die Handelsanzeige (`player_name` + `trade` in CellOut) + ✉-Nachricht-Button; (c) **async Chat**
  ueber das Postfach: `Transmission.from_player_id` + Typ `player_message`, POST `/api/messages`, Absender in
  `/api/transmissions`. Frontend: neue **/trade-View** (Profil-Editor + Partner-Verzeichnis), shared
  `message-compose`, Postfach-„Antworten". Abwicklung = normale `transport`-Flotten (Kurs per Nachricht
  aushandeln). **Hinweis:** voll testbar erst mit ≥2 Accounts (aktuell 1 echter Spieler) — Profil speichern +
  NPC-Zentren gehen solo. Echtzeit-Chat + WS-Push fuer neue Nachrichten waeren spaetere Politur.
- **Entschieden:** Handelszentren flatly unangreifbar (statt adaptiver Ueber-Deff); lokale Arbitrage zwischen
  Zentren entfaellt bewusst (ein globaler Kurs = verlaesslicher Leitfaden auch fuer P2P). Legacy-`merchant`-
  Pfad bleibt im Code, wird aber nicht mehr aktiv gespawnt.
- **Trade-v2-Ideen (spaeter):** zeitlich begrenzte Nachfrage-Events, Markt-Uebersichts-Screen, Flavor-Deff
  an Zentren (optischer „schwer bewacht"-Eindruck), Nachfrage-Komponente im Index (Flow statt nur Bestand).

---

## -1. Session 2026-06-10 — Nutzer-WIP committet + Handels-Frontend implementiert
**Beide auf Live deployed, Build sauber.** Reihenfolge: erst die hängende Frontend-WIP fertig, dann Handel.
```
7a86aa2 feat(trade): Handels-Auftragsformular im Frontend + Galaxie-Haendler-Badge
ac50eef feat(frontend): OGame-Detail-Popups + Desktop-Dichte-Schicht
```
- **Frontend-WIP committet** (`ac50eef`): die seit Tagen uncommittete Desktop-Dichte-Schicht +
  OGame-Detail-Popups (`detail-popup.component.ts` in Gebäude/Werft/Forschung, `fleet-dispatch.component.ts`
  in Galaxie) verifiziert (Build grün, alle Komponenten verdrahtet) und committet. package-lock-Rauschen
  (npm-install-Regen) verworfen, `proxy.local.json` (lokales Dev-Proxy) gitignored.
- **Handels-Frontend implementiert** (`7a86aa2`): das offene Auftragsformular aus `docs/trade-frontend-snippet.md`
  angewandt — **gegen den echten Backend-Code validiert** (`SendFleetRequest` nimmt offer_res/offer_amount/
  want_res top-level; `merchant_intel` liefert merchant/spec/prices/prices_at, gemerged in galaxy-target intel
  via population/spionage/trade). `fleet-dispatch`: 💱-Handel-Tab (Biete/Erhalte, Kurs-Vorschau aus Snapshot
  ohne Slippage, Eskorte-Hinweis). Galaxie: 💱-Händler-Badge + „Handeln"-Schnellaktion an aufgeklärten
  merchant-Zielen (die **vorher als „optional/nächstes" offen** notierte Galaxie-Integration ist damit auch erledigt).
  Modelle: FleetMission +'trade', FleetSendRequest +offer/want, GalaxyIntel +merchant/spec/prices, MISSION_META +trade.
  `docs/trade-frontend-snippet.md` oben als IMPLEMENTIERT markiert.
- **Offen/nächste Ideen** (unverändert aus §0b): Trade-v2 — Spieler-zu-Spieler-Handel, zeitlich begrenzte
  Nachfrage-Events, Markt-Übersichts-Screen. Simulator-Live-Klickdurchlauf im Browser steht noch aus.

---

## 0a. Session 2026-06-09 (Forts.) — 4 Features gebaut + committet, Frontend-WIP des Nutzers getrennt
**Alles verifiziert (69 Backend-Tests grün, Frontend-Build sauber) und gezielt committet** (nur eigene
Dateien; die parallele Nutzer-WIP blieb unangetastet). Backend + Frontend live deployed.
```
971a173 feat(npc): Populations-Spawner — lebendiges Universum (Dichte nahe Spielern)
a8cb4ca feat(combat): Kampf-Simulator — Was-waere-wenn-Schlacht ohne Spielstand-Effekt
39ee40c feat(shipyard): Rollen-Kampf-Profil in den Werft-Kacheln anzeigen
ead08f8 feat(npc): eingehende Angriffe als Live-Cockpit-Alert (WS-Push) + Reload-fest
858e6b9 docs: Handoff — Kampfbericht-Viewer dokumentiert
e518566 feat(techtree): Techbaum als echter Abhaengigkeits-Graph
7f733d7 feat(frontend): PWA — installierbar mit Angular Service Worker
37d015a feat(combat): Kampfbericht-Viewer im Frontend (Read-Path der Engine)
```
- **Kampf-Simulator** (`POST /api/combat/simulate`, Nav „Simulator"): seiteneffektfreie Was-wäre-wenn-
  Schlacht, Angreifer nutzt echte Forschung, Gegner Tech 0, nichts persistiert. Antwort in
  `serialize_combat_report`-Form → der Kampfbericht-Viewer wurde um einen `[report]`-Direkt-Input erweitert
  und rendert das Sim-Ergebnis wieder. Validierung als reine Funktion `_prepare_sim_input` (DoS-Cap
  `MAX_SIM_UNITS=50_000`, da die Engine jede Stückzahl zu Einzelobjekten expandiert). Picker zieht
  bewaffnete Schiffe aus `combat_roster` via `BalanceService`.
- **Werft-Kacheln** zeigen jetzt das Rollen-Kampf-Profil (Schadenstyp + Effektivitäts-Tooltip aus
  `damage_matrix`, Reichweiten-Band 🔴🟡🔵, Antriebs-Stufe / ⚓ stationär). Backend: `build_options` reicht
  `weapon_type`/`drive`/`range` durch (neue `Balance.combat_roster`-Property).
- **Eingehende Angriffe** als Live-Cockpit-Alert: `maybe_launch_attack` liefert ein Warn-Payload, der
  NPC-Tick pusht es NACH `session.commit()` als `attack_warning`-WS-Event; das Frontend war schon
  verdrahtet. Zusätzlich seedet `game-state` die Alerts beim Bootstrap aus `GET /api/incoming-attacks`
  (reload-fest, dedupe per location).
- **Populations-Spawner (lebendiges Universum):** `npc/population.py` + `npc.population`-Config + Tick in
  `main.py`. Hält nahe bei jedem Spieler (`radius_systems`) eine Ziel-NPC-Dichte (`target_per_player`),
  spawnt gemischte Profile (aggressive Piraten / defensive Raid-Ziele / merchant / expansive), respawnt
  zerstörte NPCs, Auto-Discovery naher Spawns. Behebt: Galaxie war mit nur 3 statischen defensiven Seeds
  leer; aktiviert die gebauten NPC-Aktivangriff/Expansion-Features (brauchten aggressive/expansive NPCs).
  Manueller Test-Tick lief: 3 Spawns nahe Spieler (1:87) inkl. Pirat 1:88, 1 Discovery angelegt. Reine
  Helfer testbar (14 Tests). Tunebar: Dichte/Radius/Gewichte/Templates in `shared/balance.json`.
- **Offen direkt hieran:** Live-Klickdurchlauf des Simulators im Browser (Build kompiliert, Endpoint 401-
  gated, aber kein End-to-End-UI-Test gefahren — kein Browser am Server). Simulator-v2-Ideen: Commander-/
  Doktrin-Boni wählbar, Varianz-Statistik über N Läufe, eigene Verteidigung simulieren.
- **HANDEL/MARKT — Backend GEBAUT diese Session** (war „existiert noch nicht"). Vollständig recherchiert,
  durchdacht (kein 0815-Festkurs) und end-to-end verifiziert. Details unten in **§0b**. Offen nur noch das
  Frontend-Auftragsformular → **`docs/trade-frontend-snippet.md`** (drop-in für `fleet-dispatch`).

---

## 0b. Session 2026-06-09 (Forts.) — HANDELSSYSTEM „Lebende Händler" (Backend komplett, 3 Schichten)
**Recherchiert → durchdacht → gebaut.** Nutzer-Wunsch: NPCs nicht nur bekämpfen, sondern auch beliefern/
behandeln (PvE statt erzwungenem PvP) — und **explizit KEIN 0815-Festkurs-Handel**. Web-Recherche (EVE/X4/
Patrician/OGame-Kritik) → Design „Lebende Händler". **Backend verifiziert (107 Backend-Tests grün) + live.**
```
eaac967 feat(trade): lebende Maerkte + Routen-Risiko + Reputation-Sichtbarkeit
16287ce feat(trade): Kern-Handelsschleife — Anfliegen, tauschen, heimkehren
b22273e feat(trade): Preis-Kern — dynamische Preise mit Slippage (X4-Modell)
```
**Modell (Anfliegen):** Spieler schickt eine Flotte mit Angebots-Ressource zu einem `merchant`-NPC,
tauscht zu dynamischen Preisen, kehrt mit der Ware heim. Mission `trade` (neu im fleet_mission-ENUM).
- **Preis-Kern** (`fleet/trade_pricing.py`, rein/getestet): `price_of` = `base_value*(setpoint/stock)`,
  geclamped → hoher Bestand billig, knapp teuer. `simulate_swap` rechnet chunk-weise → **Slippage in beide
  Richtungen** (große Order bewegt den Kurs gegen den Spieler). Config `balance.json` `trade`: base_value
  (M1/K2/D3), margin, swap_steps, 4 **Spezialisierungen** (metal_world/crystal_hub/deuterium_refinery/
  generalist → Preis-Differenziale = **Arbitrage**), reputation.
- **Kern-Schleife** (`fleet/trade.py` `resolve_trade`, Dispatch aus `fleet_arrive`): Händler am Ziel →
  `ensure_market` (lazy init, zufällige Spec, stock=setpoint) → Reputation → Cargo-Kapazität → `simulate_swap`
  → Bestand/Reputation/Fracht aktualisieren → **Preis-Snapshot in PlayerDiscovery** → Handels-Beleg-Funkspruch.
  Schema (init.sql + idempotente Migration): `fleets.mission_data`, `npc_empires.market`, Tabelle
  `trade_reputation`. Refund: nicht ausgegebenes Budget kommt als Angebots-Ressource zurück.
- **Lebende/Risiko-Schicht:** `market_regen_tick` (Bestände driften langsam zum Soll; **geteilt** → leerkaufen
  verdirbt den Kurs für Stunden = Vergänglichkeit/Konkurrenz). Spawner initialisiert Händler-Märkte + nimmt
  Spec/Kurse in die Auto-Discovery. Spionage deckt bei Händlern Spec+Kurse auf (**Info-Asymmetrie**: Kurse
  erst nach Besuch/Spionage sichtbar, als Schnappschuss). **Routen-Risiko** (`route_risk_chance`): ungeschützte
  Frachter werden auf der Route überfallen (Teil der Fracht weg) — **Eskorte** (bewaffnete Schiffe) senkt es;
  **Reputation/Stammkunden** senken die Marge.
- **End-to-End verifiziert** (resolve_trade gegen reale DB, Rollback): 50k Metall → 15,5k Deuterium bei einem
  metal_world-Händler; Slippage + Spezialisierung + Bestandsaktualisierung wirken. Belege/Warnungen erscheinen
  **schon jetzt im Postfach** (System-Funksprüche) → Handel ist auch ohne UI nutzbar.
- **OFFEN — Frontend-Auftragsformular:** gehört in `shared/components/fleet-dispatch.component.ts` (Nutzer-WIP).
  Fertiges drop-in Snippet (Missions-Tab „Handel" + Biete/Erhalte + grobe Kurs-Vorschau aus dem Snapshot,
  Modell-/display-Ergänzungen) liegt in **`docs/trade-frontend-snippet.md`**. Danach: Galaxie-Ansicht —
  Händler-Badge 💱 + „Handeln"-Schnellaktion (ebenfalls als Snippet, da galaxy.component.ts Nutzer-WIP).
- **Mögliche Trade-v2-Ideen:** Spieler-zu-Spieler-Handel (OGames Tod war der NPC-Automat — NPC-Kurse so
  kalibrieren, dass P2P daneben lohnt), zeitlich begrenzte Nachfrage-Events, Markt-Übersichts-Screen.

---

## 0. Vorige Teil-Session (2026-06-09) — Kampfberichte im Frontend sichtbar (Read-Path der Engine)
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

### 🔭 Stand 2026-06-10 — aktuell offen (ersetzt veraltete Punkte unten)
- ~~**Monde** (Mond-Frontend tiefer)~~ **ERLEDIGT (2026-06-11, `2dbdc38`)**: Sprungtor-Dialog (Mond→Mond mit
  Schiffsauswahl, Kosten/Cooldown) + Mondansicht-Navigation (🪐-Planet-Chip + 🌀-Sprungtor-Button im Dashboard)
  über den aktiven-Planet-Kontext. Backend war komplett & live. **Offen nur noch:** visueller Klick-Test braucht
  einen echten Mond (Seeding/Schreibzugriff gesperrt). Mond-Marker (🌑) in Kolonie-Leiste + Dashboard waren schon da.
- **Kampf-Simulator existiert & läuft** (Endpoint `simulateCombat`, Screen poliert + „Meine Flotte"/„Leeren") —
  der „Simulator braucht noch Endpoint"-Punkt weiter unten ist damit **erledigt**.
- **Flotte/Handel/Postfach** konsistent (tab-bar/panel-title) + Flotte entschlackt; ein vollständiger
  **einheitlicher Seiten-Kopf über ALLE Screens** steht noch aus (kosmetisch, niedrige Prio).
- ~~**Antriebs-Tempo-FIX**~~ **ERLEDIGT (2026-06-11)** — Antriebsforschung skaliert das Reise-Tempo
  (`ship_speed`/`slowest_ship_speed` lesen jetzt Forschung; `18f7b2f`).
- **In-Game-Smoke-Tests** der forschungs-skalierten Effekte + Carrier-Auto-Beladung + Abfangen im Flug
  (Backend-Suite ist grün; Laufzeit-Smoke fehlt — s. Hauptstrang-Sektion „Test-/Verifikations-Stand").
- **NPC-Carrier-Tuning**, **Gegen-Spionage**, **LLM-Funksprüche** (vom Nutzer aufgeschoben) bleiben offen.

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
