# API-Contract — Universe Vertical Slice (v0.1)

> **Single Source of Truth** für die Schnittstelle zwischen Angular-Frontend und FastAPI-game-server.
> Backend implementiert *exakt* diese Endpunkte; Frontend ruft *exakt* diese auf. Contract-first.
> Basis: ARCHITECTURE.md §5, GAME_DESIGN_DOCUMENT §13 (Vertical Slice).

Alle Pfade unter `/api`. Auth via Bearer-JWT im `Authorization`-Header (außer `/auth/*`).
Antworten sind JSON. Fehler: `{ "detail": "..." }` mit passendem HTTP-Status.
IDs sind UUID-Strings. Zeitstempel ISO-8601 UTC (`2026-06-06T20:00:00Z`).

---

## 1. Auth

### POST /api/auth/register
Req: `{ "email": str, "password": str, "display_name": str }`
Res 201: `{ "token": str, "player": Player }`
→ Legt Spieler, Heimatplanet, Start-Ressourcen/-Gebäude und 1 Start-Commander an (balance.json `starting_player`).

### POST /api/auth/login
Req: `{ "email": str, "password": str }`
Res 200: `{ "token": str, "player": Player }`

### GET /api/auth/me
Res 200: `Player`

**Player** = `{ id, email, display_name, score, is_protected, created_at, last_active }`

---

## 2. Planet & Wirtschaft

### GET /api/planets
Res 200: `Planet[]`

### GET /api/planets/{planet_id}
Res 200: `PlanetDetail`

**Planet** = `{ id, name, galaxy, system, position, temp_max, fields_used, fields_max, is_homeworld }`

**PlanetDetail** = `Planet` plus:
```
{
  "resources": {
    "metal":     { "amount": float, "rate": float, "capacity": float },
    "crystal":   { "amount": float, "rate": float, "capacity": float },
    "deuterium": { "amount": float, "rate": float, "capacity": float },
    "energy":    { "produced": float, "consumed": float, "balance": float, "factor": float }
  },
  "buildings": [ { "type": str, "level": int, "upgrade_finishes_at": iso|null } ],
  "ships":     [ { "type": str, "count": int } ],
  "defenses":  [ { "type": str, "count": int } ]
}
```
> `resources.*.amount` wird **lazy** server-seitig berechnet (Rate × Δt, gedeckelt auf capacity). `energy.factor` ∈ [0,1] drosselt die Minen-Rate bei Energiedefizit.

---

## 3. Gebäude

### GET /api/planets/{planet_id}/buildings
Res 200: `{ "buildings": BuildingState[], "available": BuildingOption[] }`
- **BuildingState** = `{ type, level, upgrade_finishes_at }`
- **BuildingOption** = `{ type, next_level, cost: {metal,crystal,deuterium}, build_seconds, can_afford: bool, requirements_met: bool }`

### POST /api/planets/{planet_id}/buildings/{type}/upgrade
Res 202: `{ "type": str, "level": int, "upgrade_finishes_at": iso }`
Fehler 409 wenn schon Bau läuft / nicht leistbar.

---

## 4. Forschung

### GET /api/research
Res 200: `{ "research": ResearchState[], "available": ResearchOption[] }`
- **ResearchState** = `{ type, level, finishes_at }`
- **ResearchOption** = `{ type, next_level, cost, research_seconds, can_afford, requirements_met }`

### POST /api/research/{type}/start
Body: `{ "planet_id": str }` (Labor-Standort)
Res 202: `{ "type": str, "level": int, "finishes_at": iso }`
Fehler 409 wenn bereits eine Forschung läuft (one_at_a_time).

---

## 5. Werft

### GET /api/planets/{planet_id}/shipyard
Res 200: `{ "ships": ShipOption[], "defenses": DefenseOption[], "queue": BuildQueueItem[] }`
- **ShipOption** = `{ type, cost, build_seconds_each, can_build: bool, requirements_met: bool }`

### POST /api/planets/{planet_id}/shipyard/build
Req: `{ "type": str, "count": int, "category": "ship"|"defense" }`
Res 202: `{ "queue": BuildQueueItem[] }`

---

## 6. Flotte

### GET /api/fleets
Res 200: `Fleet[]`
**Fleet** = `{ id, mission, status, origin, target: {galaxy,system,position}, commander_id|null, ships: {type:count}, cargo, depart_at, arrive_at, return_at }`

### POST /api/fleets/send
Req:
```
{
  "origin_planet_id": str,
  "target": { "galaxy": int, "system": int, "position": int },
  "mission": "attack"|"transport"|"spy"|"deploy",
  "ships": { "light_fighter": 10, ... },
  "cargo": { "metal": 0, "crystal": 0, "deuterium": 0 },
  "commander_id": str|null,
  "speed_pct": 100
}
```
Res 202: `Fleet` — berechnet `arrive_at`/`return_at` und Spritkosten serverseitig.
Fehler 409: zu wenig Schiffe/Sprit, keine Flottenslots frei, Ziel unter Neulingsschutz.

### POST /api/fleets/{fleet_id}/recall
Res 200: `Fleet` (status → returning) — Basis für Fleetsave.

### GET /api/galaxy/{galaxy}/{system}
Res 200: `{ "cells": [ { position, occupant_type, name|null, player_id|null, npc_id|null } ] }`

---

## 7. Kommandozentrale (Commander)

### GET /api/commanders
Res 200: `Commander[]`
**Commander** =
```
{
  id, name, persona: {background, voice}, traits: str[],
  specialization, rank, xp, morale, loyalty, span_capacity, status,
  morale_band: { label, combat_mod },         // abgeleitet aus balance.json
  assigned_fleet_id: str|null,
  training_finishes_at: iso|null
}
```

### GET /api/commanders/{id}
Res 200: `Commander` plus `history: Transmission[]` (gesammelte Funksprüche).

### POST /api/commanders/train
Body: `{ "planet_id": str }` (braucht Kommando-Akademie)
Res 202: `{ "commander": Commander }` (status=training)

### GET /api/player/span
Res 200: `{ "base": int, "from_command_center": int, "from_doctrine": int, "total": int, "in_use": int }`

---

## 8. Postfach / Funksprüche

### GET /api/transmissions
Query: `?unread=true`
Res 200: `Transmission[]`
**Transmission** = `{ id, type, subject, body, commander_id|null, requires_decision, decision_payload, read, created_at }`

### POST /api/transmissions/{id}/read
Res 200: `{ "ok": true }`

### POST /api/transmissions/{id}/decide
Req: `{ "choice": "accept"|"reject"|"negotiate" }`
Res 200: `{ "ok": true, "morale_delta": int, "message": str }`
→ Forderungs-Mechanik (Doku 05 §7). Kein LLM nötig.

---

## 9. WebSocket — Live-Updates

`WS /ws?token=<jwt>`

Server→Client Nachrichten (JSON, alle haben `type`):
```
{ "type": "resource_tick",   "planet_id": str, "resources": {...} }   // periodisch
{ "type": "build_complete",  "planet_id": str, "building": str, "level": int }
{ "type": "research_complete","tech": str, "level": int }
{ "type": "fleet_arrived",   "fleet_id": str, "mission": str }
{ "type": "fleet_returned",  "fleet_id": str }
{ "type": "transmission",    "transmission": Transmission }   // Funkspruch-Push (GDD §10.5)
{ "type": "attack_warning",  "location": str, "arrive_at": iso }   // wichtigste Warnung
{ "type": "combat_report",   "report_id": str, "summary": {...} }
```

Client→Server:
```
{ "type": "subscribe", "planet_id": str }
{ "type": "ping" }
```

---

## 10. Combat-Report

### GET /api/combat-reports/{id}
Res 200: `{ id, location, attacker, defender, rounds: Round[], winner, loot, debris, created_at }`
- **Round** = `{ round, attacker_fire, defender_fire, attacker_losses, defender_losses }`

---

## Konventionen für beide Teams
- Ressourcen-Objekte immer `{ metal, crystal, deuterium }` (deuterium optional 0).
- Gebäude-/Schiff-/Tech-`type` = die Keys aus `shared/balance.json` (z. B. `metal_mine`, `light_fighter`, `energy_tech`).
- Alle Berechnungen (Kosten, Zeiten, Produktion, Kampf) sind **server-autoritativ** (ADR-006). Das Frontend zeigt nur an.
- Build-/Forschungszeiten als absolute `*_finishes_at`-Zeitstempel; das Frontend zählt lokal runter.
