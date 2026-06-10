# Bau-Spec: Monde + Kriegsführungs-Gebäude

> Stand 2026-06-10. Nutzer-Wunsch: OGame-Monde — aus Trümmerfeldern (≤20 % Chance) gebildet, an den Planeten
> gebunden, etwas Besonderes; tragen „höhere Kriegsführung"-Gebäude (Phalanx, Sprungtor, Mond-Abwehr,
> Gravitationslabor) und verteidigen den Planeten mit. „Alles in einem" bauen (in Scheiben A–D).

## 1. Architektur — Mond = spezieller Planet
Ein Mond ist eine `planets`-Zeile mit `planet_type='moon'` + `parent_planet_id` (FK auf den Planeten), gleiche
Koordinate, Besitzer = Planet-Besitzer. **Wiederverwendet** Gebäude-/Bau-/Werft-/Flotten-Maschinerie (Mond kann
Flotten starten, Gebäude tragen, Ziel sein). Unterschiede:
- **Keine Minen/Produktion** (Mond-Bauliste enthält keine Minen; Rate = 0). Hält aber Ressourcen (Storage/Fracht).
- **Wenige Felder:** `fields_max = moon.base_fields + Mondbasis-Level * felder_pro_stufe`.
- **Eigene Bauliste:** nur Mond-Gebäude (s. §3); `building_options` filtert nach `planet_type`.

## 2. Entstehung (aus Trümmerfeld)
Nach Kampfauflösung **an einem Spieler-Planeten** (combat/service): Trümmer entstehen wie gehabt. Dann:
`chance = min(moon.max_chance (0.20), debris_total / moon.value_per_chance)`. Ein Wurf; bei Erfolg **und** noch
kein Mond an der Koordinate → Mond-Planet anlegen (gebunden an den Planeten dort, Besitzer = dessen Owner),
Funkspruch „Ein Mond ist entstanden". (NPC-Kämpfe: Trümmer ja, Mond nein.)

## 3. Mond-Gebäude (balance.buildings + `moon_only`-Flag)
- **Mondbasis** (`moon_base`): Fundament; jede Stufe +Felder. Voraussetzung für alle anderen Mond-Gebäude.
- **Sensorphalanx** (`sensorphalanx`): **mond-only** (Bestand auf Planeten bleibt funktionsfähig = grandfathered;
  Neubau nur auf Monden). Flottenscan unverändert.
- **Sprungtor** (`jump_gate`): instanter Flottensprung zwischen zwei eigenen Monden mit Sprungtor (kein Flug),
  Cooldown (`jump_gate.cooldown_seconds`, von Gravitationsforschung senkbar).
- **Orbitalbatterie** (`orbital_battery`): bringt beim Angriff auf den **Planeten** Verteidigungskraft mit ein
  (Mond feuert herab). Pro Stufe N `orbital_gun`-Verteidigungseinheiten zur Verteidiger-Seite.
- **Schildkuppel** (`shield_dome_moon`): legt im Planetenkampf einen Zusatz-Schild über die Verteidiger
  (Schild-Tech-äquivalente Stufen / Schildpool), pro Stufe.
- **Gravitationslabor** (`gravity_lab`): schaltet den Forschungszweig **„Höhere Kriegsführung"** frei
  (jump_gate_tech: Cooldown/Reichweite, phalanx_range_tech, evtl. Abfang-/Eskorte-Bonus).

## 4. Mond verteidigt den Planeten (Kampf-Integration)
Wird ein **Spieler-Planet** angegriffen (resolve_attack PvP / npc/attack): zusätzlich den **Mond** des Planeten
laden und seine Verteidigungs-Gebäude einrechnen:
- Orbitalbatterie-Level → `orbital_gun`-Einheiten in `def_defenses`.
- Schildkuppel-Level → Verteidiger-`shield_tech` + Bonus (bzw. Schildpool). Die fremde Flotte kämpft so gegen
  Planet **+** Mondunterstützung, ohne den Mond selbst zu treffen. Der Mond selbst ist nur über einen
  eigenen Angriff zerstörbar (eigene Bauliste/Verteidigung).

## 5. Sprungtor-Mechanik
`POST /api/fleets/jump {from_moon_id, to_moon_id, ships, cargo?}`: beide Monde gehören dem Spieler + haben ein
Sprungtor; Cooldown je Quell-Sprungtor; Schiffe wechseln **sofort** zum Ziel-Mond (Garnison), kein Flug, kein
Sprit. Cooldown in `last_jump_at` am Mond (oder eigener Speicher).

## 6. Zahlen (Defaults, tunebar in balance.moon / .buildings / .jump_gate)
| Param | Default |
|---|---|
| moon.max_chance | 0.20 |
| moon.value_per_chance | 1 000 000 (Trümmerwert für 100 %, vor Cap) |
| moon.base_fields | 1 |
| moon_base felder_pro_stufe | 3 |
| jump_gate.cooldown_seconds | 3600 |
| orbital_battery units/Stufe | 8 |
| shield_dome shield_tech/Stufe | +2 |

## 7. Build-Scheiben (alle in einem Durchlauf, je committet + getestet)
A. **Monde-Fundament:** Migration (planets.parent_planet_id; planet_type 'moon' nutzbar), Formation aus Trümmer,
   Mond-only Bau-Filter, Mondbasis (+Felder), Phalanx mond-only, **Frontend** (Mond in Kolonie-Leiste/Planet-
   Switcher, Mond-Bauansicht).
B. **Mond verteidigt Planeten:** Orbitalbatterie + Schildkuppel + Einrechnung in resolve_attack & npc/attack.
C. **Sprungtor:** jump_gate-Gebäude + Jump-Endpoint + Cooldown + Frontend.
D. **Gravitationslabor + Forschungszweig „Höhere Kriegsführung".**

> Mond-Bauliste-Filter: `building_options` zeigt auf Monden nur `moon_only`-Gebäude, auf Planeten nur Nicht-
> Mond-Gebäude (sensorphalanx wandert in `moon_only`). Grandfathering: bestehende sensorphalanx-Gebäude bleiben.
