# Implementierungsplan — Allianzen (Forschung + Station)

> Erstellt 2026-06-14. Umsetzung geplant für den Folgetag. Design-Dialog-Stand siehe Memory
> `project_universe_alliances_planned`. Dieser Plan ist die Arbeitsgrundlage — Reihenfolge top-down.

---

> ✅ **UMSETZUNG GESTARTET 2026-06-15.** Entscheidungen A/B/C = Defaults bestätigt (Nutzer). Knotenliste
> finalisiert (20 Knoten, je 5/Baum). Backend gebaut + getestet (260/260): balance-Block, DB
> (alliances/alliance_members/alliance_stations/alliance_invites + players.alliance_id via migrations.py),
> Verwaltung+Pool, Forschung (Soft-Cap/Reset), Bonus-Resolver (context-Gating) + Hook Förderquote-Zone,
> Station (Bau/Tank/Radius/Upkeep/Zone). Frontend-Screen via Agent. **Offen/Phase 2:** coop/ally-Hooks
> feuern erst mit echten gemeinsamen Aktionen (geteilte Flotten); Stations-Zerstörung (combat-Integration);
> weitere Hooks (Piraterie/Handel/Schutz-Wirkungen über den Förderquote-Hook hinaus).

## 0. Vor dem Code — 3 offene Entscheidungen (zuerst klären!)

Diese MÜSSEN am Anfang fixiert werden, sonst baut man zweimal:

- **A) Station-Boni:** projiziert die Station die Baum-Spezialisierung der Allianz (Empfehlung, kohärent)
  oder hat sie ein eigenes, unabhängiges Bonus-Menü? → **Default-Annahme: projiziert die Bäume.**
- **B) Zonen-Wirkung:** nur Mitglieder-Buff in der Zone, oder zusätzlich Eindringling-Debuff (echtes
  Kampfgebiet)? Anti-Grief beachten. → **Default-Annahme: Mitglieder-Buff; Piraterie-Baum als einzige
  Ausnahme darf Fremde in der eigenen Zone leicht debuffen (Räuberhöhle).**
- **C) Stationszahl:** eine zentrale Station oder mehrere territoriale Vorposten? → **Default-Annahme:
  1 Hauptstation + später wenige Vorposten (Vorposten = Phase 2).**

**Bestätigtes Prinzip (Doppel-Dip-Schutz):** Spieler-Forschung = GLOBALE Grundlage (nichts streichen,
Solo bleibt komplett). Allianz-Forschung = NEUE kollektive Fähigkeiten + BEDINGTE Boni, die nur in
Kontexten greifen, die es solo nicht gibt: **Koop-Aktion**, **Stations-Zone**, **Ally-Kontext**,
**Pool/Logistik**. → kein globaler Doppel-Stack derselben Zahl.

**Spezialisierung bestätigt:** nicht hart-exklusiv; Soft-Cap-Tiefe + Pool-Knappheit belohnen Fokus;
Reset = Sink für echten Pfadwechsel.

---

## 1. Datenmodell — `shared/balance.json` (neuer Block `alliance`)

Neuer Top-Level-Key `"alliance"` mit:

```
"alliance": {
  "max_members": 50,
  "create_cost": { metal, crystal, deuterium },
  "pool": { "_note": "Mitglieder zahlen ein; daraus wird geforscht/gebaut" },
  "research": {
    "reset_refund_ratio": 0.0,          // 0 = voller Sink (User-Idee); evtl. 0.1 als Stellschraube
    "cost_scales_with_members": true,    // Guardrail gegen Größen-Schneeball
    "member_cost_factor_per_member": 0.0X,
    "trees": {
      "piracy":      { "nodes": { ... } },
      "economy":     { "nodes": { ... } },
      "trade":       { "nodes": { ... } },
      "protection":  { "nodes": { ... } }
    }
  },
  "station": {
    "build_cost": {...}, "base_radius": 1, "max_radius": 5,
    "radius_per_research_level": 1,
    "upkeep_deuterium_per_tick": ..., "tick_interval_seconds": 3600,  // reuse station_fuel-Idee
    "max_per_alliance": 1,
    "destroy_min_attackers": 2,         // braucht mehrere Spieler (Plan-Vorgabe)
    "zone_bonus_softcap": ...           // Guardrail
  }
}
```

**Knoten-Format** je Node (analog `research.techs`): `{ cost, max_level (für Soft-Cap/repeatable),
effect (Klartext), context: "coop"|"zone"|"ally"|"passive_collective", lever (welcher Hebel) }`.
Das `context`-Feld kodiert den Doppel-Dip-Schutz maschinenlesbar.

**Knotenliste (Vorschlag, FINALISIEREN bevor Icons bestellt werden):**
- 🏴‍☠️ **piracy:** `raid_loot` (coop, +plunder beim Raid mit Ally) · `shadow_fleet` (zone, schwerer
  entdeckbar) · `boarding_doctrine_ally` (coop, +Kaperung) · `gravity_snare` (zone, +Interdiktion gg.
  Fremde) · ⭐`pack_hunt` (coop, gemeinsamer Abfang → Extra-Beute + geteilte Phalanx-Sicht)
- 🏭 **economy:** `extraction_zone` (zone, +Abbau in Zone) · `deep_drilling` (zone, +Asteroid/Trümmer/
  Exotik in Zone) · `forward_yards` (zone, −Bauzeit in Zone) · `depot_storage` (passive_collective,
  +Pool-Lager/−decay) · ⭐`joint_extraction` (coop, geteilte Minen-Op → +Ertrag)
- 💱 **trade:** `market_access` (zone/pool, bessere Preise für Zonen-/Pool-Trades) · `cargo_logistics`
  (ally, +Fracht/−Sprit bei Ally-Transport) · `safe_routes` (coop, −Routenrisiko Konvoi) ·
  `depot_logistics` (passive_collective, billigere Pool-Einzahlung) · ⭐`escort_convoy` (coop,
  eskortierter Konvoi → +sichere Ladung +Profit)
- 🛡️ **protection:** `escort_doctrine` (ally, Konvois unkaperbar) · `rapid_response` (ally, +Abfang
  bei Verteidigung eines Mitglieds) · `early_warning` (zone, +Phalanx/Hinterhalt-Entdeckung) ·
  `bounty` (passive_collective, Bonus für Pirat-Kill) · ⭐`shield_wall` (coop, gemeinsame Verteidigung
  → gestapelte Aura + Gruppen-Warp-Stabilisator)

**Mirror:** `cp shared/balance.json frontend/src/assets/balance.json` (Pflicht nach jeder Änderung).

---

## 2. DB-Schema + Migration (`backend/app/platform/models.py`, `migrations.py`)

Neue Tabellen (greenfield — es gibt noch KEIN Alliance-Modell):
- `alliances` — id, name, tag, founder_id, created_at, category-Default (optional), `pool` (JSON
  metal/crystal/deuterium), `research_levels` (JSON {node_key: level}).
- `alliance_members` — alliance_id, player_id, role (founder/officer/member), joined_at.
- `alliance_stations` — id, alliance_id, galaxy, system, position, `research_radius_level`,
  `fuel` (Deuterium-Vorrat), built_at, hp/status (zerstörbar).
- Optional: `alliance_pool_log` (wer hat wann was eingezahlt) — für Transparenz/Governance.

`Player` bekommt `alliance_id` (nullable FK) — der einzige Eingriff am Spieler-Modell.

Migration im bestehenden `migrations.py`-Stil (idempotent, `ensure_*`).

---

## 3. Backend — Services

### 3a. Allianz-Verwaltung (`backend/app/alliance/` NEU: `service.py`, `router.py`, `schemas.py`)
- create/disband, invite/join/leave/kick, Rollen (founder/officer/member, Berechtigung für Pool-Ausgaben
  & Reset = Governance).
- Pool-Einzahlung: Spieler überweist Ressourcen von Planet → Allianz-Pool (`spend_resources` Planet →
  Pool gutschreiben). Race-sicher (Postgres-Row-Lock wie `book_slot`-Muster).

### 3b. Allianz-Forschung
- `spend_alliance_research(node)` — zahlt aus Pool, erhöht Level (Soft-Cap via `max_level`,
  Kosten skalieren mit Mitgliederzahl = Guardrail).
- `reset_alliance_research()` — wischt Levels, refund = `reset_refund_ratio` (default 0 = voller Sink).
  Nur Founder/Officer. Bestätigungs-Dialog im Frontend.

### 3c. **Bonus-Resolver (Kernstück — Doppel-Dip-Schutz)**
Zentrale Funktion `alliance_bonus(player, context, lever)` die je nach `context` greift:
- `coop`: nur wenn ≥2 Mitglieder gemeinsam in der Aktion (Raid/Konvoi/Minen-Op) → Multiplikator.
- `zone`: nur wenn Ziel-Planet/-System in der Einflusszone einer eigenen Station liegt.
- `ally`: nur wenn die Aktion ein anderes Mitglied schützt/transportiert.
- `passive_collective`: immer für Mitglieder (rein soziale Hebel: Pool-Logistik, Bounty).
**Hook-Punkte (bestehende Dateien):**
  - Abbau/Ertrag → `fleet/mining.py`, `economy/service.py` (Produktion).
  - Kampf: Beute/Aura/Interdiktion → `combat/service.py` (`_combat_aura_mult`, `_raider_loot_mult`),
    `combat/engine.py` (Stabilisator/Interdiktion bereits da).
  - Abfangen/Verteidigung → `fleet/interception.py`, `fleet/stationing.py`.
  - Handel/Konvoi → `fleet/trade.py`, `trade`-Block.
  - Phalanx-Sicht → `fleet/phalanx.py`.

### 3d. Station
- build/deploy (aus Pool, an Galaxie:System:Pos), Einflusszone = Systeme im Radius
  (`base_radius + radius_per_research_level*level`, Cap `max_radius`) — **gleiches System-Distanz-Muster
  wie `interception`/Phalanx-Radius**.
- Upkeep-Tick (Scheduler-Job, wie `station_fuel_tick`): zehrt Deuterium aus Stations-`fuel`; leer →
  Zone aus / Station inaktiv.
- Zerstörung: braucht `destroy_min_attackers` ≥2 → Zone kollabiert.
- `zone_for_alliance(galaxy, system)` Helper, den der Bonus-Resolver (`zone`-Kontext) nutzt.

---

## 4. Frontend (Angular)

- **Nav-Eintrag „Allianz"** (`icons/nav/alliance.png`), neuer Route/Screen `features/alliance/`.
- **Allianz-Screen:** Übersicht (Mitglieder, Pool, Rollen), **Forschungs-Tabs** (4 Bäume, Soft-Cap-Anzeige
  + Reset-Button mit Bestätigung), **Station** (Bau, Radius-Ausbau, Upkeep-Anzeige, Einflusszone).
- **Galaxie-/System-Karte:** Einflusszone-Overlay (`icons/status/alliance_zone.png`, eingefärbt) über
  Systemen im Radius; Station als Besatzer-Marker.
- **display.ts:** Namen/Blurbs/Icons für Bäume + Knoten + Station (wie `SHIP_META`/`TECH_META`).
- **api.models.ts:** Alliance-DTOs.

---

## 5. Assets
Bereits in `asset_liste.md` eingetragen (Sektion „🤝 Allianzen"): 4 Baum-Embleme, `alliance_station`,
Nav-Icon, Zonen-Marker. **Knoten-Icons** erst nach Finalisierung der Knotenliste (Schritt 1) ergänzen.

---

## 6. Tests
- Pool-Einzahlung/Abhebung race-sicher; Forschung Soft-Cap + Reset-Sink (Refund 0).
- Bonus-Resolver: `coop` greift NUR bei ≥2 Mitgliedern; `zone` NUR in Reichweite; kein Stack mit
  Spieler-Tech im Normalfall (Doppel-Dip-Regressionstest!).
- Station: Radius-Berechnung, Upkeep-Leerlauf → Zone aus, Zerstörung braucht ≥2.
- Bestehende Suite grün halten (Schiff-Balance-Harness `tmp/universe_ship_audit.py` unberührt).

---

## 7. Reihenfolge für den Tag (Vorschlag)
1. **Entscheidungen A/B/C + Knotenliste finalisieren** (30 min Design-Sync).
2. `balance.json`-Block `alliance` schreiben + Mirror. → Knoten-Icons in `asset_liste.md` nachtragen.
3. DB-Modelle + Migration + `Player.alliance_id`.
4. Allianz-Verwaltung (create/join/pool) + Router + minimaler Frontend-Screen (Mitglieder/Pool).
5. Forschung (spend/reset/soft-cap) + Frontend-Tabs.
6. **Bonus-Resolver** + erste Hook-Punkte (Wirtschaft-Zone, Schutz-Koop) — das Kernstück, gründlich testen.
7. Station (build/Radius/Upkeep/Zone) + Karten-Overlay.
8. Restliche Hooks (Piraterie/Handel), Tests, `docker compose build game-server frontend && up -d`.

> Realistisch ist Tag 1 = Schritte 1–6 (Forschung + Resolver-Fundament). Station (7) + restliche Hooks (8)
> ggf. Tag 2. Lieber das Doppel-Dip-Fundament sauber als alles halb.
