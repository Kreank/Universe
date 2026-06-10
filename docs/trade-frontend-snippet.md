# Handels-Frontend — Integrations-Snippet (fleet-dispatch)

> ✅ **IMPLEMENTIERT 2026-06-10** (Commit `7a86aa2`), live deployed. Dieses Dokument ist nur noch
> historische Referenz — das Snippet wurde gegen den echten Backend-Code validiert und angewandt:
> `fleet-dispatch` hat den 💱-Handel-Tab (Biete/Erhalte + Kurs-Vorschau + Eskorte-Hinweis), die
> Galaxie zeigt 💱-Händler-Badge + „Handeln"-Schnellaktion, Modelle/MISSION_META ergänzt.
> Galaxie-Integration (war als „optional/nächstes" offen) ist ebenfalls drin.
>
> Stand 2026-06-09 (urspr.). Das **Backend-Handelssystem ist fertig & live** (3 Commits, s. HANDOFF §0b).
> Das EINZIGE offene UI-Stück war das Handels-Auftragsformular. Es gehört in das
> `shared/components/fleet-dispatch.component.ts` (Versand-Overlay aus der Galaxie) — das war beim
> Bauen **uncommittete WIP des Nutzers**, deshalb hier als drop-in Snippet statt direkter Edit.
>
> Handel ist auch OHNE dieses UI nutzbar: Belege + Überfall-Warnungen kommen als System-Funksprüche
> ins Postfach. Das Snippet liefert nur das bequeme Auftragsformular + grobe Kurs-Vorschau.

## 1) `core/models/api.models.ts` — 3 additive Ergänzungen

```ts
export type FleetMission =
  | 'attack' | 'transport' | 'spy' | 'deploy' | 'recycle'
  | 'colonize' | 'mine' | 'expedition' | 'trade';        // + 'trade'

export interface FleetSendRequest {
  // … bestehende Felder …
  offer_res?: 'metal' | 'crystal' | 'deuterium';
  offer_amount?: number;
  want_res?: 'metal' | 'crystal' | 'deuterium';
}

export interface GalaxyIntel {
  // … bestehende Felder …
  merchant?: boolean;
  spec?: string;
  prices?: { metal?: number; crystal?: number; deuterium?: number };
  prices_at?: string;
}
```

## 2) `core/models/display.ts` — `MISSION_META` um `trade`

```ts
trade: { glyph: '💱', label: 'Handel' },
```

## 3) `shared/components/fleet-dispatch.component.ts`

**Imports:**
```ts
import { /* … */ effect } from '@angular/core';
import { Coordinate, FleetMission, PlanetUnit, GalaxyIntel } from '../../core/models/api.models';
```

**Felder/Signals:**
```ts
protected readonly missions: FleetMission[] = ['attack', 'transport', 'spy', 'deploy', 'trade'];

protected readonly offerRes = signal<'metal' | 'crystal' | 'deuterium'>('metal');
protected readonly offerAmount = signal(0);
protected readonly wantRes = signal<'metal' | 'crystal' | 'deuterium'>('deuterium');
protected readonly merchantIntel = signal<GalaxyIntel | null>(null);

protected readonly showTrade = computed(() => this.mission() === 'trade');

// Grobe Vorschau aus dem zuletzt gesehenen Snapshot (OHNE Slippage/Reputation —
// der echte Wert wird serverseitig bei Ankunft berechnet).
protected readonly tradeEstimate = computed<number | null>(() => {
  const p = this.merchantIntel()?.prices;
  if (!p) return null;
  const pIn = p[this.offerRes()] ?? 0;
  const pOut = p[this.wantRes()] ?? 0;
  if (pIn <= 0 || pOut <= 0 || this.offerAmount() <= 0) return null;
  return Math.round(this.offerAmount() * (pIn / pOut) * 0.96); // 0.96 ≈ Standard-Marge
});

constructor() {
  effect(() => {
    const t = this.target();
    this.api.getGalaxyTargets().subscribe((list) => {
      const hit = list.find((x) => x.galaxy === t.galaxy && x.system === t.system && x.position === t.position);
      this.merchantIntel.set(hit?.intel?.merchant ? (hit.intel as GalaxyIntel) : null);
    });
  });
}
```

**Template** (nach dem `@if (showCargo()) { … }`-Block):
```html
@if (showTrade()) {
  <div class="cargo">
    <div class="cargo-title">💱 Handelsauftrag</div>
    <div class="trade-grid">
      <div class="field">
        <label>Biete</label>
        <select [ngModel]="offerRes()" (ngModelChange)="offerRes.set($event)">
          @for (r of cargoFields; track r.key) { <option [ngValue]="r.key">{{ r.glyph }} {{ r.label }}</option> }
        </select>
        <input type="number" min="0" [max]="planetRes()?.[offerRes()]?.amount ?? 0"
          [ngModel]="offerAmount()" (ngModelChange)="offerAmount.set(+$event || 0)" />
      </div>
      <div class="field">
        <label>Erhalte</label>
        <select [ngModel]="wantRes()" (ngModelChange)="wantRes.set($event)">
          @for (r of cargoFields; track r.key) { <option [ngValue]="r.key">{{ r.glyph }} {{ r.label }}</option> }
        </select>
        @if (merchantIntel(); as mi) {
          <span class="muted small">Spez.: {{ mi.spec }} · Kurse vom letzten Besuch</span>
        } @else {
          <span class="muted small">Kurse unbekannt — Händler erst aufklären/besuchen.</span>
        }
      </div>
    </div>
    @if (tradeEstimate(); as est) {
      <p class="trade-preview small">≈ <strong>{{ est }}</strong> {{ wantRes() }} (ungefähr, vor Slippage/Reputation)</p>
    }
    @if (offerRes() === wantRes()) {
      <p class="hint small">Biete- und Wunsch-Ressource müssen verschieden sein.</p>
    }
  </div>
}
```

**`canSend` ersetzen:**
```ts
protected readonly canSend = computed(() => {
  if (!this.hasSelection() || !this.state.activePlanetId() || this.missionHint()) return false;
  if (this.mission() === 'trade') {
    return this.offerAmount() > 0 && this.offerRes() !== this.wantRes();
  }
  return true;
});
```

**`send()` — Body + Handels-Felder:**
```ts
const body: FleetSendRequest = {
  origin_planet_id: origin, target: this.target(), mission: this.mission(),
  ships, cargo, commander_id: this.commanderId(), speed_pct: this.speed(),
};
if (this.mission() === 'trade') {
  body.offer_res = this.offerRes();
  body.offer_amount = this.offerAmount();
  body.want_res = this.wantRes();   // cargo baut der Server aus dem Angebot
}
this.api.sendFleet(body).subscribe({ /* … bestehend … */ });
```

**Styles (optional):**
```css
.trade-grid { display: flex; flex-wrap: wrap; gap: 0.6rem; }
.trade-grid .field { flex: 1 1 200px; }
.trade-grid select, .trade-grid input { min-height: 30px; }
.trade-preview { color: var(--accent); margin: 0.5rem 0 0; }
```

## Hinweise
- Backend validiert hart: Ziel muss ein `merchant`-NPC sein, Angebot ≤ Frachtkapazität, Ressourcen
  verschieden. Fehler kommen als `err.error.detail` (bestehender error-Handler zeigt sie).
- **Eskorte = bewaffnete Schiffe** in der Flotte senken das Routen-Überfallrisiko. Evtl. einen
  Hinweis ergänzen („Frachter ohne Eskorte werden auf der Route überfallen").
- Vorschau ist bewusst grob (Snapshot, ohne Slippage). Echter Tausch inkl. Slippage/Reputation
  läuft serverseitig bei Ankunft; der **Handelsbeleg im Postfach** zeigt die realen Durchschnittskurse.
- Optional als nächstes: Galaxie-Ansicht — Händler mit 💱-Badge + „Handeln"-Schnellaktion
  (`galaxy.component.ts` ist Nutzer-WIP → ebenfalls als Snippet liefern).
