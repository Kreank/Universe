# Implementierungsplan — Routinen (automatisierte Farm-Routen)

> Erstellt 2026-06-15 aus dem Design-Dialog mit dem Besitzer (Telegram). Dieser Plan ist die
> Arbeitsgrundlage — **erst durchsehen, dann bauen**. Reihenfolge top-down.
> Scope bewusst eng: Routinen farmen **ausschließlich Asteroidenfelder + Trümmerfelder**. Kein Angriff,
> kein Transport, keine Kolonisierung.

---

## 0. Bestätigtes Design (Dialog-Ergebnis — gesetzt)

- **Gemeinsamer Flotten-Laderaum** (kein Split-Fleet). Bergbauschiffe, Recycler und Transporter teilen
  sich einen Frachtraum (Kapazität = Summe aller `ship.cargo`). Das ist bereits das heutige Verhalten in
  `fleet/mining.py` und `fleet/harvest.py` → Transporter werden automatisch mitbeladen.
- **Ein Feld pro Ankunft** wird in EINEM Zug bearbeitet. Ergebnis ist immer binär:
  - **Feld leer geräumt** (Laderaum hatte noch Platz) → weiter zum nächsten Feld der Route.
  - **Laderaum voll** (Feld hatte noch Vorrat) → Rückflug zur Station, ausladen, **danach zurück zum
    SELBEN Feld** (Cursor bleibt stehen), bis es wirklich leer ist.
- **„Leer" ist nur ein Moment-Zustand** — Felder regenerieren (`regen_ratio_per_hour: 0.03`). Die Routine
  fliegt ihre Felder **endlos im Kreis**; geleerte Felder werden im nächsten Durchlauf erneut gefarmt.
- **Zwei Forschungs-Hebel, beide Start 2, +1 je Stufe, kein Maximum:**
  - **Anzahl gleichzeitiger Routinen** (Breite).
  - **Anzahl Felder pro Route** (Tiefe).
- **Mehrere Routinen pro Spieler**, auch über verschiedene Galaxien verteilt.
- **Treibstoff** wird pro Flug-Leg von der Heim-Station abgezogen. Kein Deuterium → Routine pausiert +
  Benachrichtigung.

---

## 1. Offene Entscheidungen (vor dem Code klären)

Diese 3 will ich von dir noch abgesegnet haben — Default-Annahmen sind angegeben:

- **A) Abfangbarkeit:** Ist eine Routinen-Flotte im Flug wie jede andere Flotte **abfangbar** (Phalanx,
  Patrouille, Interdiktor) und ihre Fracht **erbeutbar**? → **Default-Annahme: JA.** Farming soll Risiko
  tragen (passt zur Design-Philosophie „lebensecht + fordernd"). Bei Verlust der Flotte → Routine
  pausiert automatisch + Benachrichtigung. *Alternative: unangreifbar wie NPC-Handelszentren — würde
  Farming aber risikofrei machen, daher nicht empfohlen.*
- **B) Heimat-Anker:** Lädt eine Routine immer bei EINER festen Heim-Station aus (bei Anlage gewählt), egal
  in welcher Galaxie sie farmt? → **Default-Annahme: JA, eine feste Station je Routine.** (Treibstoff/Zeit
  für weite Galaxien sind der natürliche Balancing-Preis.)
- **C) Felder-Typ-Mischung:** Darf EINE Route Asteroiden- UND Trümmerfelder mischen? → **Default-Annahme:
  JA, frei mischbar** (an Asteroid → `resolve_mine`, an Trümmer → `resolve_harvest`, beides in denselben
  Laderaum). Die Flotte sollte dann sinnvollerweise Bergbauschiffe UND Recycler enthalten.

---

## 2. Datenmodell

### 2.1 Neue Tabelle `FarmRoute` (`platform/models.py`)

Persistente Definition + zugewiesene Schiffe. Lebt weiter, auch während die Schiffe gerade an der Station
docken (zwischen zwei Zyklen).

```
class FarmRoute(Base):
    id: UUID
    player_id: UUID                       # Besitzer
    home_planet_id: UUID                  # feste Ausgangs-/Auslade-Station (Entscheidung B)
    name: str                             # frei wählbar ("Asteroiden G1", …)
    ships: dict                           # {typ: count} — die fest zugeordnete Farm-Flotte
    waypoints: list                       # [{galaxy, system, position}], Reihenfolge = Flugreihenfolge
    enabled: bool                         # vom Spieler an/aus
    status: str                           # idle | flying | working | returning | paused
    pause_reason: str | None              # "no_fuel" | "fleet_lost" | None
    cursor: int                           # Index des aktuell anzufliegenden Waypoints
    active_fleet_id: UUID | None          # Fleet, die diese Routine GERADE fliegt (sonst None)
    created_at: datetime
```

- `ships` als Dict (wie `mission_data` anderswo) statt eigener Tabelle — Schiffe sind exklusiv an die
  Routine gebunden, solange sie aktiv ist (analog zu „Schiffe sind im Flug gebunden").
- Der **Frachtraum lebt auf der `active_fleet_id`-Fleet** (`Fleet.cargo`) — kein zweites Cargo-Feld.
  Zwischen Zyklen (status `idle`) ist keine Fleet aktiv, Laderaum = leer (gerade ausgeladen).

### 2.2 Wiederverwendung des bestehenden Fleet-Modells

Jeder einzelne Flug-Leg einer Routine ist eine **normale `Fleet`** mit neuer Mission `"routine"` und
`fleet.mission_data = {"farm_route_id": <id>, "leg": "outbound"|"return"}`. Damit greifen automatisch:
`compute_distance`, `fuel_cost`, `fleet_arrive`, Abfang-/Phalanx-Logik (Entscheidung A) — **kein
Parallel-System für Flugzeiten/Treibstoff nötig.**

Neuer Wert in der Missions-Liste (`fleet/service.py` Enum-Stelle): `"routine"`.

---

> **UMSETZUNGS-ENTSCHEIDUNG (2026-06-15): per-Feld-Rückkehr statt Feld→Feld-Direktflug.**
> Implementiert ist: jeder Zyklus = EIN getaggter `mine`/`recycle`-Flug zum aktuellen Feld + Rückkehr +
> Ausladen; danach startet der nächste Zyklus. Dadurch erbt jeder Zyklus Flugzeit, Treibstoff (Hin+Rück),
> Frachtdeckel, Abfangbarkeit und Ausladen KOMPLETT vom bestehenden Flotten-System — keine neue
> Flug-/Tank-Mechanik, kein Risiko gestrandeter Flotten, keine Enum-Änderung (mine/recycle sind bereits
> gültig). Der einzige Unterschied zum ursprünglich skizzierten Direkt-Hop: räumt ein Feld mit Restladeraum
> leer, fliegt die Flotte erst heim (ausladen) und im nächsten Zyklus zum nächsten Feld — statt direkt
> Feld→Feld. In der Praxis identisch (Felder sind riesig vs. Laderaum → es wird ohnehin pro Feld mehrfach
> heimgependelt). Cursor-Logik unverändert: Feld leer → Cursor++ (modulo, endlos); Laderaum voll → Cursor
> bleibt. Direkt-Hop ist eine mögliche v2-Optimierung.

## 3. Ablauf — der Routinen-Controller

Ein Controller (`fleet/routines.py`, neu) treibt jede aktive Routine. Angestoßen an denselben Punkten wie
heutige Flotten-Resolver (bei `fleet_arrive` der Routinen-Legs) plus ein leichter Tick/Scheduler für den
Neustart docking→Abflug.

**Zyklus einer Routine (Cursor = aktueller Waypoint):**

1. **Start-Leg (status `idle`→`flying`):** Schiffe an Station. Controller nimmt `waypoints[cursor]`,
   berechnet Treibstoff/Zeit für das Leg, **zieht Deuterium von `home_planet` ab**.
   - Kein Deuterium → `status=paused`, `pause_reason="no_fuel"`, Benachrichtigung. Ende.
   - Sonst: erzeuge `Fleet(mission="routine", mission_data={farm_route_id, leg:"outbound"})` zum Waypoint.
2. **Ankunft am Feld (`fleet_arrive` → Controller, status `working`):**
   - Asteroid (`occupant=asteroid_field`) → `resolve_mine` in `fleet.cargo`.
   - Trümmer (`debris_field` gesetzt) → `resolve_harvest` in `fleet.cargo`.
   - Feld weg/leer bei Ankunft → 0 Ertrag, behandeln wie „Feld leer" (Schritt 3b).
3. **Entscheidung nach dem Abbau (binär):**
   - **a) Laderaum voll** → Rückflug-Leg zur Station (`leg:"return"`), **Cursor bleibt** (Feld noch nicht
     leer). Treibstoff fürs Return-Leg von Station abziehen.
   - **b) Feld leer, Laderaum noch Platz** → **Cursor++**.
     - Noch ein Waypoint da → direktes **Feld→Feld-Leg** (Fracht bleibt an Bord, kein Heimflug).
     - Cursor über Listenende → Rückflug-Leg zur Station.
4. **Ankunft an Station (`leg:"return"`, status `returning`→`idle`):**
   - `add_resources(home_planet, fleet.cargo)` — ausladen.
   - Fleet auflösen, Schiffe „docken" (zurück in den Routinen-Pool).
   - **Cursor-Logik beim Neustart:**
     - Kam der Heimflug, weil Laderaum voll war (Feld noch nicht leer) → **Cursor unverändert** (zurück
       zum selben Feld).
     - Kam er, weil die Route durch war (Cursor über Ende) → **Cursor = 0** (Route von vorn).
   - `enabled && !paused` → zurück zu Schritt 1. Sonst `status=idle`/`paused`.

> **Warum „ein Feld pro Ankunft" sauber ist:** Mining/Harvest ist pro Ankunft ein einziger gedeckelter
> Zug (`min(Feldvorrat, Laderaum-frei)`). Danach ist entweder das Feld leer ODER der Laderaum voll — nie
> beides offen. Das löst die Frage „Feld leerräumen vs. Laderaum-Cap" ganz ohne Sonderfälle.

---

## 4. Forschung (`shared/balance.json` → `techs`)

Vorlage: die bestehenden repeatable `*_command`-Techs (`harvest_command`, `corsair_command` …), die eine
Stückzahl-Obergrenze pro Stufe heben. Default 2 wird im neuen `routines`-Block (§5) gesetzt; jede Stufe +1.

```jsonc
"fleet_logistics": {
  "cost": { "metal": 4000, "crystal": 6000, "deuterium": 2000 },
  "repeatable": true,
  "requires": { "research_lab": 4, "computer_tech": 4 },
  "effect": "Logistik-Netz (wiederholbar): +1 gleichzeitig laufende Routine je Stufe (Default 2)."
},
"route_planning": {
  "cost": { "metal": 3000, "crystal": 5000, "deuterium": 2000 },
  "repeatable": true,
  "requires": { "research_lab": 4, "impulse_drive": 3 },
  "effect": "Routen-Planung (wiederholbar): +1 Feld je Route je Stufe (Default 2)."
}
```

- **Anzahl Routinen** = `routines.base_routines + fleet_logistics_level`.
- **Felder pro Route** = `routines.base_fields_per_route + route_planning_level`.
- Beide repeatable, lineare Kosten, sinkender Grenznutzen — passt zur „ewiges Universum"-Endgame-Linie.
- Kosten oben sind Startwerte zum Tunen.

---

## 5. Balance-Block (`shared/balance.json`, neuer Top-Level-Key `routines`)

```jsonc
"routines": {
  "_note": "Automatisierte Farm-Routen. Eine Routine = dauerhaft fliegende Sammelschleife über Asteroiden-/Trümmerfelder; lädt an der Heim-Station aus und startet neu. Anzahl Routinen = base_routines + fleet_logistics-Stufe; Felder pro Route = base_fields_per_route + route_planning-Stufe.",
  "base_routines": 2,
  "base_fields_per_route": 2,
  "allowed_field_types": ["asteroid_field", "debris_field"],
  "unload_to": "home_planet",
  "interceptable": true,           // Entscheidung A
  "pause_on_empty_fuel": true,
  "pause_on_fleet_loss": true
}
```

> **Mirror-Pflicht:** Nach jeder `balance.json`-Änderung `cp shared/balance.json
> frontend/src/assets/balance.json` (siehe HANDOFF / Memory `project_universe_devloop`).

---

## 6. API (`backend/app/.../routes`)

CRUD + Steuerung. Vorschlag:

- `GET  /api/routines` — eigene Routinen + Status/Fortschritt (Cursor, aktuelles Feld, Laderaum-Füllstand).
- `POST /api/routines` — anlegen `{name, home_planet_id, ships, waypoints}`.
  - Validierung: Anzahl ≤ erlaubte Routinen; `len(waypoints)` ≤ erlaubte Felder/Route; jeder Waypoint ist
    Asteroid/Trümmer; genug Schiffe vorhanden; Felder-Typ passt zu Schiffstypen (Recycler für Trümmer,
    Bergbauschiff für Asteroiden).
- `PATCH /api/routines/{id}` — `enabled` an/aus, Waypoints/Schiffe ändern (greift ab nächstem Zyklus).
- `DELETE /api/routines/{id}` — auflösen, Schiffe freigeben (nur wenn `idle`/docked).

---

## 7. Frontend

- Neuer Screen **„Routinen"** (Nav-Icon, Stil wie bestehende Screens; ggf. Parallel-Agent für Rendering).
- **Routen-Designer:** Galaxie-/Feld-Auswahl (Asteroiden + Trümmer markierbar), Reihenfolge per
  Drag/Up-Down, Schiffe zuweisen, Heim-Station wählen.
- **Live-Status je Routine:** aktuelles Feld, Laderaum-Balken, „fliegt zu …", ETA, Pausen-Grund.
- Limits sichtbar: „Routinen 2/3", „Felder dieser Route 2/4" (aus Forschung).
- `frontend/src/assets/balance.json` liest die neuen Werte (Mirror, s. §5).

---

## 8. Edge-Cases & Entscheidungen

| Fall | Verhalten |
|------|-----------|
| Kein Deuterium an Station beim Leg-Start | Routine `paused` (`no_fuel`) + Benachrichtigung; Schiffe bleiben wo sie sind (an Station bzw. fliegen letztes Leg zu Ende). |
| Trümmerfeld bei Ankunft schon leer (anderer war schneller) | 0 Ertrag, behandeln wie „Feld leer" → nächstes Feld. |
| Asteroidenfeld weg (sollte statisch sein) | Waypoint überspringen, Cursor++; bei Anlage validieren. |
| Flotte unterwegs abgefangen/zerstört (Entscheidung A) | Routine `paused` (`fleet_lost`) + Benachrichtigung; Fracht ist beim Abfang erbeutbar. |
| Spieler ändert Waypoints/Schiffe während aktiv | Übernahme **ab nächstem Zyklus** (laufendes Leg fliegt zu Ende). |
| Zwei Routinen / mehrere Spieler auf demselben Feld | Geteilte Reserven; wer ankommt, nimmt was da ist (bestehendes Verhalten). |
| Forschung sinkt (gibt's nicht) bzw. zu viele Routinen | Über-Limit-Routinen blockieren das Anlegen; bestehende laufen weiter. |
| Schiffe anderweitig gebraucht | Routine pausieren/löschen, um Schiffe freizugeben. |

---

## 9. Tests (Pflicht vor Deploy — s. HANDOFF Verifikations-Loop)

- Controller-Zyklus: Feld leer → nächstes Feld; Laderaum voll → Rückflug → selbes Feld.
- Cursor-Reset am Routenende vs. Cursor-Halt bei vollem Laderaum.
- Forschung: erlaubte Routinen / Felder-pro-Route = base + Stufe.
- Treibstoff-Abzug pro Leg + Pause bei 0 Deuterium.
- Gemischte Route (Asteroid + Trümmer) lädt in denselben Laderaum.
- API-Validierung: Über-Limit blockiert; falscher Feld-Typ blockiert.
- `ruff check backend/app --select F` grün; `npx ng build` grün.

---

## 10. Umsetzungs-Reihenfolge (Vorschlag)

1. `balance.json`: `routines`-Block + 2 Techs; Mirror kopieren.
2. `FarmRoute`-Modell + Migration.
3. `fleet/routines.py` Controller + Mission `"routine"` + `fleet_arrive`-Hook.
4. API-Endpoints + Validierung.
5. Backend-Tests, `build game-server`, pytest.
6. Frontend-Screen + Designer (ggf. Parallel-Agent).
7. Deploy (`build game-server` + `up -d`, Frontend `build` + `up -d`), live verifizieren.
```
