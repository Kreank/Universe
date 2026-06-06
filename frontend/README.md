# Universe — Frontend (Angular SPA)

Web-first, responsive Single-Page-App fuer das Weltraum-Aufbau-MMO **Universe**.
Dunkles Sci-Fi-Theme (Cyan/Magenta), Standalone-Components, Signals, Lazy Routes.

- **Angular:** 22 (standalone, signals, `@angular/build`)
- **Sprache:** TypeScript (strict) + strictTemplates
- **Styling:** SCSS, globales Theme in `src/styles.scss`
- **Server-autoritativ:** das Frontend rechnet nicht; es zeigt an und zaehlt
  `*_finishes_at`-Zeitstempel lokal runter (ADR-006 / api-contract.md).

## Screens & Routen

| Route | Inhalt |
|-------|--------|
| `/login`, `/register` | Auth, Token in `localStorage` |
| `/dashboard` | Ressourcen live (Rate + Kapazitaet, Energie-Bilanz), Bau-Queue, Alerts, Crew-Moral |
| `/buildings` | Gebaeudeausbau mit Kosten/Bauzeit/Countdown |
| `/research` | Techbaum, eine Forschung gleichzeitig |
| `/shipyard` | Schiffe & Verteidigung bauen (Anzahl, Queue) |
| `/fleet` | Flotte senden (Ziel G:S:P, Mission, Commander, Tempo), laufende Flotten + Rueckruf, Galaxie-Ansicht |
| `/commanders` | Kommandozentrale: Roster, Moral-Baender, Traits, Span, Training |
| `/commanders/:id` | Commander-Detail mit Funkspruch-Historie |
| `/transmissions` | Postfach: Funksprueche, Forderungen (Erfuellen/Verhandeln/Ablehnen), Live-Push |

## Architektur

```
src/app/
  core/
    models/        api.models.ts (Vertrag), balance.ts, display.ts (Labels/Glyphs)
    services/      api, auth, balance, websocket, notification, game-state
    interceptors/  auth.interceptor.ts (Bearer-Token, 401-Handling)
    guards/        auth.guard.ts (authGuard / guestGuard)
  shared/
    components/    countdown, icon-tile, cost-line, toast-container
    pipes/         short-number
  layout/shell/    Topbar (Ressourcen + Planet-Wahl), Sidenav, Angriffsbanner
  features/        auth, dashboard, buildings, research, shipyard, fleet, commanders, transmissions
```

- **`ApiService`** — typsichere Huelle ueber alle REST-Endpunkte aus `shared/api-contract.md`.
- **`WebSocketService`** — verbindet `/ws?token=`, RxJS-Stream;
  `on('transmission' | 'resource_tick' | 'build_complete' | 'fleet_arrived' | 'attack_warning' | …)`.
  Auto-Reconnect + Ping.
- **`GameStateService`** — zentraler reaktiver Zustand (Signals), verteilt Live-Updates an alle Screens.
- **`BalanceService`** — laedt `assets/balance.json` (Labels, Moral-Baender, Tooltip-Werte;
  **keine** Berechnungen).

## Lokale Entwicklung

```bash
npm install
npm start          # ng serve auf http://localhost:4200
```

`npm start` nutzt **`proxy.conf.json`**: `/api` und `/ws` werden an
`http://localhost:8000` (game-server) weitergeleitet — keine CORS-Probleme.
Den game-server separat starten (siehe `backend/` bzw. `infra/docker-compose`).

### balance.json synchronisieren

Die App laedt `src/assets/balance.json`. Abgleich mit der Single-Source-of-Truth
`shared/balance.json`:

```bash
npm run sync:balance
```

(Bewusst nicht Teil von `npm run build`, damit der Docker-Build-Context
eigenstaendig bleibt — die Kopie liegt bereits unter `src/assets/`.)

## Build

```bash
npm run build      # Produktions-Build nach dist/universe/browser
```

## Docker

Multi-Stage (Node-Build → nginx-Serve). Die mitgelieferte `nginx.conf` serviert
die SPA und proxyt `/api` + `/ws` an `http://game-server:8000`.

```bash
docker build -t universe-frontend ./frontend
docker run -p 8080:80 universe-frontend
```

Im Compose-Verbund (`infra/`) laeuft der Container neben `game-server`; nginx
loest den Hostnamen `game-server` im Docker-Netzwerk auf.

## Assets / Platzhalter

Echte Bilder fehlen noch. Verwendet werden:
- **Glyph-Kacheln** (`IconTileComponent`) fuer Schiffe/Gebaeude/Ressourcen,
- **SVG-Platzhalter** unter `src/assets/img/<kind>/<key>.svg`
  (z. B. `ships/light_fighter.svg`, `commanders/portrait.svg`).

Die `type`-Keys entsprechen exakt `shared/balance.json`, sodass Platzhalter
spaeter 1:1 durch echte Bilder ersetzbar sind. Labels/Glyphs werden in
`core/models/display.ts` gepflegt.
