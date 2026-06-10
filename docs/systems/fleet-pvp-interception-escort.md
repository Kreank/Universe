# Flotten-PvP: Abfangen, Phalanx-Sensor & Eskort-Patrouillen — Design-Spec

> Stand 2026-06-10. Größtes Feature bisher; legt die PvP-Grundregeln dauerhaft fest.
> Nutzer-Entscheidungen: **(1) Eskorte + Abfangen als EIN Wurf**, **(2) Phalanx-Sensor (Gebäude/Tech)
> für Sichtbarkeit**, **(3) volles OGame — auch Heimkehrer am Heimatplaneten fangbar** (Fleetsave-Pflicht).
> NPC-Routenrisiko bleibt als harmlose Würze; der eigentliche Reiz ist Spieler-Timing.

## 0. Leitprinzip (das Herz des Systems)
**Flotten im Flug sind unantastbar (= Fleetsave).** Eine Flotte ist NUR verwundbar, wenn sie irgendwo *sitzt*:
- **A) In einer Garnison** (Heimatplanet/Kolonie) — gefangen, indem man den Planeten angreift, *getimt* auf den
  Moment, in dem die mobile Flotte zuhause ist (nicht fleetsaved). ← der OGame-Klassiker.
- **B) Am fremden Ziel im Ankunftsfenster** — eine Handels-/Transportflotte ist `intercept_window_seconds`
  lang am Ziel fangbar, bevor sie heimkehrt.
- **C) Stationiert** (Eskort-Patrouille / Deploy) — sitzt dauerhaft, jederzeit angreifbar.

**Sichtbarkeit (Phalanx + Spionage) ist das, was Timing zum Können macht.** Ohne ETA-Intel kein Abfangen.
**Eskorte ist die Verteidigungs-Seite derselben Mechanik:** eine stationierte Patrouille kämpft auf der
Verteidiger-Seite mit, wenn in ihrer Region ein eskortierter Transport abgefangen wird.

---

## 1. Flotten-Verwundbarkeit & Lebenszyklus (Backend)
Heute: `flying → arrive_at → returning → return_at → done`; Schiffe als `Ship(fleet_id=…)`, Garnison als
`Ship(planet_id=…, fleet_id=None)`.

Neu:
- **Ankunftsfenster (B):** Flotte bleibt nach `arrive_at` für `intercept_window_seconds` (Default **60 s**)
  im Status `arrived` am Ziel, *dann* `returning`. In diesem Fenster ist sie ein gültiges Angriffsziel.
  (Heute kehrt sie sofort um — wir schieben `return_at` um das Fenster.)
- **Fangbar-Query:** „Welche Flotten sitzen JETZT verwundbar an Koordinate (g,s,p)?" = SQL über `Fleet`
  (`status='arrived'` am Ziel) + stationierte Patrouillen + Garnison des Planeten. Alles DB-queryable.
- **Garnison (A):** existiert schon (zurückgekehrte Schiffe). Sobald PvP-Planetenkampf da ist, kämpft sie
  automatisch mit. **Fleetsave** = der Verteidiger schickt seine Flotte rechtzeitig raus.

## 2. Phalanx-Sensor (Sichtbarkeit)
- **Neues Gebäude `sensorphalanx`** (balance.json `buildings`): Kosten + Faktor wie andere; benötigt
  Forschungs-/Gebäude-Voraussetzung (z. B. Kommandozentrale-Lvl X).
- **Reichweite** = `level² − 1` Systeme (OGame-Formel) in derselben Galaxie. Level 1 → 0 (nur eigenes
  System), Lvl 5 → 24 Systeme. Tunebar in balance `phalanx`.
- **Scan-Endpoint** `POST /api/phalanx/scan {galaxy,system,position}`: liefert alle Flottenbewegungen
  **zu/von** der Zielkoordinate (mission, Richtung, `arrive_at`/`return_at`, grobe Größe), wenn die Koordinate
  in Reichweite eines eigenen Phalanx-Gebäudes liegt. **Kostet Deuterium je Scan** (Default 5 000, balance).
- Eigene Flotten + eingehende Angriffe auf einen selbst sind immer sichtbar (kein Scan nötig).

## 3. Abfangen / PvP-Kampf (Kern)
- **PvP-Planetenkampf (Voraussetzung, fehlt komplett):** `attack` gegen einen Spieler-Planeten muss die
  **Garnison + Verteidigungsanlagen** des Verteidigers bekämpfen (Engine `simulate_battle` ist wiederverwendbar:
  `defender = {ships: garnison, defenses: planet.defenses, tech: research}`). Sieg → Plünderung (Default **50 %**
  der ungeschützten Ressourcen), Trümmerfeld, Kampfbericht an beide.
- **Flotten-Fang am Ziel (B):** Kommt ein Angreifer an (g,s,p) an, während dort eine Beute-Flotte im
  Ankunftsfenster sitzt → `simulate_battle(angreifer, {ships: beute_flotte, defenses:{}, tech: beute_research})`.
  Verlierer-Schiffe zerstört, **Fracht zu 100 % erbeutet**, Trümmerfeld. (Beim Heim-Fang (A) ist die Garnison
  die „Beute".)
- **Stationierte Patrouille (C):** ist ein normales Angriffsziel; wird sie zerstört, erlischt ihr Eskortangebot.
- **Timing-Präzision:** APScheduler löst `arrive_at` sekundengenau auf; Reihenfolge zweier Ankünfte am selben
  Ort = nach `arrive_at`. Wer zuerst da ist, ist „da"; der Spätere trifft ihn (oder verpasst, wenn das Fenster
  zu ist). → genau das OGame-Rechenspiel.

## 4. Eskorte / Stationierung (Modell B)
- **`deploy`-Mission implementieren (heute Stub):** Schiffe verlassen die Flotte und werden eine **stationierte
  Patrouille** am Zielsystem (neue Tabelle `stationed_fleet`: owner, coords, ships, locked). Schiffe sind für
  den Besitzer **gesperrt** (nicht anderweitig nutzbar), bis er sie **zurückruft** (fliegen heim).
- **Eskort-Angebot:** eine Patrouille kann ein Angebot tragen: Wirkungsradius **R Systeme** um die Station,
  **Gebühr = % des Frachtwerts** (Anbieter setzt %, Default-Cap 10 %).
- **Trader-Seite:** beim Versand eines Transports/Handels zeigt das UI die **Regionen auf der Route** + die
  Eskort-Angebote, die sie decken. Trader wählt **pro Region ja/nein**, zahlt je gewählter Region % des
  Frachtwerts (async an den Anbieter). Wirkung:
  1. senkt NPC-Routenrisiko (vorhandene `escort_power`-Dämpfung), und
  2. **bei einem Abfang-Versuch in dieser Region kämpft die Patrouillen-Kampfkraft auf Verteidiger-Seite mit.**
- **Auto-Remove:** Patrouille zerstört → Angebot weg (gratis, weil die Schiffe weg sind). Live-Kraft = echte
  aktuelle Schiffe der Station.
- **Region/Deckung:** Region = Systeme im Radius R um die Station (intra-galaxy). Eine Route (origin→target)
  ist gedeckt, wenn ihr System-Intervall den Stationsradius schneidet.

## 5. Engine-Wiederverwendung & Nebenwirkungen
- `simulate_battle` bleibt rein; PvP/Fleet-Kampf füttert nur andere Verteidiger-dicts. **Trümmerfeld**
  (`UniverseCell.debris_field`) existiert; Plünderung folgt dem vorhandenen Loot-Muster. Kampfberichte über
  den vorhandenen `serialize_combat_report` an beide Seiten (Postfach).
- **Neulingsschutz** (`is_protected`) gilt weiter — geschützte Spieler weder angreifbar noch abfangbar.

## 6. Zahlen (Default-Vorschläge, alle tunebar in balance.json)
| Parameter | Default | Sinn |
|---|---|---|
| `intercept_window_seconds` | 60 | Fangfenster am fremden Ziel |
| `phalanx.range = level²−1` | — | Sensor-Reichweite (Systeme) |
| `phalanx.scan_cost_deuterium` | 5 000 | Kosten je Scan |
| `pvp.plunder_fraction` | 0.5 | Anteil erbeuteter Planet-Ressourcen |
| `pvp.cargo_capture` | 1.0 | erbeutete Fracht einer gefangenen Flotte |
| `pvp.debris_fraction` | 0.3 | Anteil zerstörter Schiffe → Trümmer |
| `escort.region_radius` | 5 | Deckungsradius einer Patrouille (Systeme) |
| `escort.max_fee_pct` | 0.10 | Gebühren-Obergrenze |

## 7. Frontend
- **Galaxie:** Phalanx-Scan-Aktion an Koordinaten in Reichweite → Flottenbewegungs-Liste mit ETAs (Countdown).
  Eingehende Angriffe (auch von Spielern) im Cockpit-Alert + Postfach.
- **Flotten-Versand:** Eskort-Regionen auf der Route mit Ja/Nein-Auswahl + Gebührenvorschau.
- **Stationieren/Eskorte:** UI zum Deploy einer Patrouille + Eskort-Angebot (Radius, Gebühr-%), Rückruf.
- **Kampfberichte:** vorhandener Viewer zeigt PvP-/Fang-Berichte (Read-Path existiert).

## 8. Build-Scheiben (jede einzeln verifizierbar + committet)
1. **PvP-Planetenkampf + Plünderung** (Garnison-Verteidigung, Loot, Trümmer, Bericht an beide). *Foundation.*
2. **Phalanx-Sensor** (Gebäude + Reichweite + Scan-Endpoint + Flottensichtbarkeit) + eingehende Spieler-Angriffe.
3. **Abfangen am Ziel** (Ankunftsfenster, Flotte-vs-Flotte-Kampf am Ort, Fracht-Beute).
4. **Stationierung + Eskort-Patrouillen** (deploy-Implementierung, stationed_fleet, Angebote, Regions-Deckung,
   Gebühren, Eskorte kämpft mit).
5. **Frontend** für 2–4 (Scan-UI/Countdowns, Eskort-Auswahl im Versand, Stationier-/Angebots-UI).
6. **Balance-Tuning + Tests** je Scheibe; Deploy.

> Offene Mikro-Entscheidungen mit gewählten Defaults oben — beim Bauen bestätigen/tunen.
