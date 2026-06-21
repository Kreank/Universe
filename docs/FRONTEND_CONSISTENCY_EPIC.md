# Frontend-Konsistenz + Ausbau-Epos (2026-06-21)

Auftrag Sascha: Frontend konsistent machen (v.a. „Schiffe verschicken" — bisher alles drangeklatscht)
+ neue Features. Professionell, Subagents, Plan zuerst, Codex für Assets. Mk2-Schiffe = wie Mk1 mit
erkennbarem Rahmen/Glow (KEIN neuer Render pro Schiff).

## Architektur-Befunde (aus 5 Analyse-Subagents)

- **Zwei Versand-UIs (Inkonsistenz-Quelle):** `fleet.component.ts` hat ein EIGENES Inline-Sendeformular
  (order-bar), `shared/components/fleet-dispatch.component.ts` ist das Overlay (genutzt von Galaxie,
  Bergbau, Handel, Expedition). ~12 doppelte Funktionen (Distanz/Sprit/Flugzeit/Cargo/availOf/…) +
  Lücken: Overlay fehlt colonize-Cargo, intercept-Radius, escort-Radius/Fee, patrolHome; Inline fehlt
  Reichweite-Warnung, Konjunktions-Hinweis, Fähigkeiten-scharf, Cargo-Auto-Kürzen. → Vereinheitlichen
  auf das Overlay; gemeinsame Rechenlogik in einen Service.
- **Galaxie:** mischt Übersicht + alle Ziel-Aktionen inline (NPC Angriff/Spionage/Diplomatie/Phalanx/
  Transport, Spieler, Monde, Stationen, Asteroiden→Bergbau, Trümmer→Recycling, Events). Soll zu reiner
  Übersicht+Schnellwahl werden. Backend hat `/api/galaxy/targets`, `/api/npc/relations`,
  `/api/incoming-attacks`; FEHLEN Listen-Endpoints für „entdeckte NPCs/Spieler/Bedrohungen".
- **Schiffe/Mk2:** balance.ships (shared/balance.json ~986-1632). Fast ALLE Touchpoints iterieren
  generisch über balance.ships → Mk2 als `<type>_mk2` greift automatisch in Werft/Combat/Ranking/
  Fleet-Range/Fuel/NPC/Expedition. Stats generisch aus Mk1 × Faktoren ableiten (NICHT 30 Einträge
  pflegen). Gate: neue Forschung `veteran_shipyard`. Antimaterie-Kosten. Frontend: Mk2-RAHMEN um das
  vorhandene Schiff-Icon (icon-tile) + Badge — KEIN neuer Render je Schiff.
- **Eskorten:** StationedFleet escort-Mode (radius/fee) + coveringEscorts beim Handel. Heute nur
  Anbieten + Read-only-Liste. Marktplatz (Angebote browsen/erstellen/annehmen + Gesuche) braucht
  Frontend + (für Gesuche) neue Tabelle/Endpoints → phasen.
- **Design-System:** stark + konsistent (Tokens var(--…), .card/.panel-title/.chip/.btn*,
  app-countdown/empty-state/btn-icon/icon-tile/fleet-dispatch). EINZIGER großer Ausreißer: fleet.component
  Inline-Formular. Referenz-Screens: mining/trade/expedition.

## Wellen (jede: Backend?+Test → Frontend → Deploy)

### W0 — Dispatch-Vereinheitlichung (Konsistenz-Keystone)
- `fleet-dispatch` zum EINZIGEN Versand-Weg machen: ergänzen um colonize-Cargo, intercept-Radius,
  escort-Radius+Fee, patrolHome; Konjunktion/Reichweite/Fähigkeiten sind schon drin.
- Gemeinsame Rechenlogik → `core/services/fleet-calculation.service.ts` (Distanz/Range/Fuel/Flight/Cargo),
  von Overlay genutzt; Duplikate entfernen.
- `fleet.component` zu Bergbau-Stil: Verwaltung (eingehende Angriffe, laufende, stationierte) +
  Aktions-Buttons → öffnen das Overlay. Inline-order-bar raus.

### W1 — Galaxie → Übersicht + „Ziele/Bedrohungen"-Screen
- Backend: Listen-Endpoints `GET /api/targets/npcs` (entdeckte NPC-Imperien + Relation/Intel),
  `/api/targets/players` (entdeckte Spieler), `/api/targets/threats` (eingehende Angriffe + feindliche
  NPCs nah). Reuse PlayerDiscovery/NpcRelation/incoming-attacks.
- Frontend: neuer Screen `features/targets` (Tabs NPCs/Spieler/Bedrohungen) mit Aktionen via Overlay +
  Diplomatie + Phalanx. Nav: Militär-Gruppe. Eigenes Nav-Icon (Codex).
- Galaxie: auf Scanner+Navigation+Zonen+Konjunktion reduziert; Ziel-Aktionen raus (Verweis auf Ziele-Screen);
  Asteroiden/Trümmer-Schnellaktion bleibt als Kontext optional (Bergbau/Recycling-Einstieg) ODER raus.

### W2 — Handel: Eskort-Marktplatz
- Eskort-Verwaltung in den Handel-Reiter holen; Angebote browsen + erstellen + annehmen. MVP:
  Angebote-Übersicht + Annehmen (reuse StationedFleet escort). Voll: Gesuche-Board (neue Tabelle
  `escort_job` + Endpoints) als Phase 2 falls gewünscht.

### W3 — Mk2/Elite-Schiffe (Endgame)
- balance: `_mk2_factors` (attack/shield ~×1.25, cost ×1.3, fuel ×1.3) + Generator, der `<type>_mk2`
  beim Laden ableitet (mk2_parent, requires veteran_shipyard + Antimaterie-Kosten). Forschung
  `veteran_shipyard`. SHIP_META-Labels generisch („… Mk II").
- Frontend: Mk2-RAHMEN/Glow um das Schiff-Icon (icon-tile-Erweiterung) + Badge in Werft/Flotten/Sim.
  Asset: EIN Mk2-Rahmen-Overlay (Codex).
- Combat-/Balance-Check über die bestehenden combat-Tests; Antimaterie-Kosten validieren.

## Codex-Assets (vor Code briefen)
1. **Mk2-Rahmen-Overlay** (transparent, legt sich um/hinter ein 64–70px Schiff-Icon; goldener/edler
   Sci-fi-Rahmen + dezenter Glow, damit Mk1 vs Mk2 sofort erkennbar). Master assets/icons/ui/ + Mirror.
2. **„Ziele/Bedrohungen"-Nav-Icon** (Nav-Metallrahmen-Stil wie diplomacy.png; Emblem: Fadenkreuz/Radar
   mit Bedrohungs-Akzent). 256×256, Master assets/icons/nav/ + Mirror frontend/src/assets/img/nav/.

## Reihenfolge & Abhängigkeiten
W0 zuerst (alles sendet Schiffe). W1 nutzt das vereinheitlichte Overlay. W2 hängt am Handel-Reiter.
W3 unabhängig (kann jederzeit). Jede Welle gebaut/getestet/deployt, Telegram-Status danach.
