import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { GameStateService } from '../../core/services/game-state.service';
import { CombatReport } from '../../core/models/api.models';
import { DEFENSE_META, SHIP_META, metaFor } from '../../core/models/display';
import { CombatReportComponent } from '../transmissions/combat-report.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';

/** Eine waehlbare Einheit im Picker (Schiff oder Verteidigung). */
interface PickRow {
  type: string;
  label: string;
  glyph: string;
  /** Asset-Pfad des echten Einheiten-Bildes (Fallback: glyph via icon-tile). */
  icon: string;
}

/**
 * Kampf-Simulator: eine Was-waere-wenn-Schlacht ohne jeden Spielstand-Effekt.
 *
 * Der Spieler stellt eine eigene Flotte und einen Gegner (Schiffe + Verteidigung)
 * zusammen; der Server rechnet mit der ECHTEN Forschung des Spielers (Gegner-Tech = 0)
 * und liefert einen vollwertigen Kampfbericht, den der bestehende Viewer rendert.
 */
@Component({
  selector: 'app-combat-sim',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, CombatReportComponent, IconTileComponent],
  template: `
    <section class="sim">
      <header class="sim-head">
        <h1>⚔️ Kampf-Simulator</h1>
        <p class="faint small">
          Nutzt deine aktuelle Forschung; Gegner-Tech = 0. Das Ergebnis ist eine Stichprobe —
          erneut simulieren für Varianz.
        </p>
      </header>

      @if (!balanceLoaded()) {
        <p class="state">Balance lädt …</p>
      } @else {
        <div class="cols">
          <!-- Eigene Flotte: nur Kampf-Schiffe -->
          <div class="card col side-own">
            <div class="panel-title">
              🛡 Deine Flotte
              @if (ownTotal()) { <span class="ptotal mono">{{ ownTotal() }}</span> }
              <button class="mini" type="button" [disabled]="!garrisonCombat().length"
                title="Schiffe vom aktiven Planeten übernehmen" (click)="fillOwnFromFleet()">🚀 Meine Flotte</button>
            </div>
            @for (s of combatShips(); track s.type) {
              <label class="row">
                <app-icon-tile class="r-ico" [glyph]="s.glyph" [src]="s.icon" [size]="36" variant="accent" />
                <span class="r-label">{{ s.label }}</span>
                <input
                  type="number"
                  min="0"
                  class="r-num"
                  [ngModel]="ownCounts()[s.type] ?? null"
                  (ngModelChange)="setCount('own', s.type, $event)"
                  placeholder="0"
                />
              </label>
            }
          </div>

          <!-- Gegner: Schiffe + Verteidigung -->
          <div class="card col side-enemy">
            <div class="panel-title">
              ⚔ Gegner
              @if (enemyTotal()) { <span class="ptotal mono">{{ enemyTotal() }}</span> }
            </div>

            <div class="sub-head">Schiffe</div>
            @for (s of combatShips(); track s.type) {
              <label class="row">
                <app-icon-tile class="r-ico" [glyph]="s.glyph" [src]="s.icon" [size]="36" variant="magenta" />
                <span class="r-label">{{ s.label }}</span>
                <input
                  type="number"
                  min="0"
                  class="r-num"
                  [ngModel]="enemyShipCounts()[s.type] ?? null"
                  (ngModelChange)="setCount('enemyShip', s.type, $event)"
                  placeholder="0"
                />
              </label>
            }

            <div class="sub-head">Verteidigung</div>
            @for (d of defenses(); track d.type) {
              <label class="row">
                <app-icon-tile class="r-ico" [glyph]="d.glyph" [src]="d.icon" [size]="36" variant="magenta" />
                <span class="r-label">{{ d.label }}</span>
                <input
                  type="number"
                  min="0"
                  class="r-num"
                  [ngModel]="enemyDefCounts()[d.type] ?? null"
                  (ngModelChange)="setCount('enemyDef', d.type, $event)"
                  placeholder="0"
                />
              </label>
            }
          </div>
        </div>

        <div class="actions">
          <button
            class="btn btn-primary"
            [disabled]="!canSimulate() || pending()"
            (click)="simulate()"
          >
            {{ pending() ? 'Simuliere …' : '⚔️ Simulieren' }}
          </button>
          <button class="btn btn-ghost" type="button" (click)="clearAll()">🧹 Leeren</button>
          @if (error()) {
            <span class="err">{{ error() }}</span>
          }
        </div>
      }
    </section>

    @if (result(); as r) {
      <app-combat-report [report]="r" (close)="result.set(null)" />
    }
  `,
  styles: [`
    .sim { display: flex; flex-direction: column; gap: var(--sp-4); }
    .sim-head h1 { font-family: var(--font-display); }
    .small { font-size: var(--fs-sm); }
    .state { color: var(--text-dim); padding: var(--sp-5) 0; }

    .cols { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4); align-items: start; }
    .col { display: flex; flex-direction: column; gap: var(--sp-1); min-width: 0; }

    /* Seiten-Semantik: eigene Flotte = Akzent (Cyan), Gegner = Gefahr (Magenta). */
    .side-own { border-top: 2px solid var(--accent); }
    .side-enemy { border-top: 2px solid var(--danger-dim); }

    .sub-head {
      font-family: var(--font-display);
      font-size: var(--fs-xs); letter-spacing: 0.1em; text-transform: uppercase;
      color: var(--text-dim); margin: var(--sp-3) 0 var(--sp-2);
    }

    /* Panel-Überschrift mit Summen-Badge + Mini-Aktion rechts. */
    .panel-title { justify-content: flex-start; }
    .ptotal {
      margin-left: var(--sp-1);
      font-family: var(--mono); font-variant-numeric: tabular-nums;
      font-size: var(--fs-xs); color: var(--accent);
      background: var(--accent-soft);
      border: 1px solid var(--accent-dim); border-radius: var(--r-pill);
      padding: 2px var(--sp-2);
    }
    .side-enemy .ptotal {
      color: var(--danger);
      background: color-mix(in srgb, var(--danger) 12%, transparent);
      border-color: var(--danger-dim);
    }
    .mini {
      margin-left: auto; text-transform: none; letter-spacing: 0;
      font-family: var(--font); font-size: var(--fs-xs); font-weight: 600;
      color: var(--accent); background: var(--accent-soft);
      border: 1px solid var(--accent-dim); border-radius: var(--r-md);
      min-height: 44px; padding: var(--sp-1) var(--sp-3); cursor: pointer;
      transition: background var(--motion-fast) var(--ease-out),
        box-shadow var(--motion-fast) var(--ease-out);
    }
    .mini:hover:not(:disabled) { background: rgba(47,227,210,0.18); box-shadow: var(--glow-soft); }
    .mini:disabled { opacity: 0.4; cursor: not-allowed; }

    .row { display: grid; grid-template-columns: 40px 1fr 5rem; align-items: center;
      gap: var(--sp-3); padding: var(--sp-1); border-radius: var(--r-sm);
      transition: background var(--motion-fast) var(--ease-out); cursor: pointer; }
    .row:hover { background: rgba(255,255,255,0.03); }
    .r-ico { display: inline-flex; justify-self: center; }
    .r-label { font-size: var(--fs-base); color: var(--text); }
    .r-num { width: 100%; text-align: right;
      font-family: var(--mono); font-variant-numeric: tabular-nums; }

    .actions { display: flex; align-items: center; gap: var(--sp-3); flex-wrap: wrap;
      position: sticky; bottom: 0; padding-top: var(--sp-2); margin-top: var(--sp-2); }
    .err { color: var(--danger); font-size: var(--fs-sm); }

    @media (max-width: 700px) {
      .cols { grid-template-columns: 1fr; }
      .row { grid-template-columns: 40px 1fr 4.5rem; }
    }

    /* Desktop-Dichte (OGame-Stil): kompaktere Mini-Aktion ab Maus-Breite. */
    @media (min-width: 900px) {
      .mini { min-height: 32px; }
    }
  `],
})
export class CombatSimComponent {
  private readonly api = inject(ApiService);
  private readonly balance = inject(BalanceService);
  private readonly state = inject(GameStateService);

  protected readonly ownCounts = signal<Record<string, number>>({});
  protected readonly enemyShipCounts = signal<Record<string, number>>({});
  protected readonly enemyDefCounts = signal<Record<string, number>>({});

  protected readonly result = signal<CombatReport | null>(null);
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);

  protected readonly balanceLoaded = computed(() => this.balance.value !== null);

  /** Kampf-Schiffe = bewaffnete Schiffe (combat_roster[typ].weapon_type gesetzt). */
  protected readonly combatShips = computed<PickRow[]>(() => {
    const bal = this.balance.value;
    if (!bal) {
      return [];
    }
    const roster = (bal as any)?.combat_roster ?? {};
    const out: PickRow[] = [];
    for (const type of Object.keys(bal.ships ?? {})) {
      const prof = roster[type];
      // Nur echte, bewaffnete Schiffe (Notiz-Keys wie `_note` haben kein Profil/Waffentyp).
      if (prof && typeof prof === 'object' && prof.weapon_type) {
        const meta = metaFor(SHIP_META, type);
        out.push({ type, label: meta.label, glyph: meta.glyph, icon: `assets/img/ships/${type}.png` });
      }
    }
    return out;
  });

  /** Verteidigungsanlagen (nur echte Konfigurationen, Notiz-Keys ausgefiltert). */
  protected readonly defenses = computed<PickRow[]>(() => {
    const bal = this.balance.value;
    if (!bal) {
      return [];
    }
    const out: PickRow[] = [];
    for (const [type, cfg] of Object.entries(bal.defenses ?? {})) {
      // Virtuelle Einheiten (z. B. Mond-Orbitalbatterie) sind nicht direkt baubar/wählbar.
      if (cfg && typeof cfg === 'object' && !(cfg as { virtual?: boolean }).virtual) {
        const meta = metaFor(DEFENSE_META, type);
        out.push({ type, label: meta.label, glyph: meta.glyph, icon: `assets/img/defenses/${type}.png` });
      }
    }
    return out;
  });

  protected readonly canSimulate = computed(() => {
    const own = hasUnit(this.ownCounts());
    const enemy = hasUnit(this.enemyShipCounts()) || hasUnit(this.enemyDefCounts());
    return own && enemy;
  });

  /** Summe ausgewählter Einheiten je Seite (für die Spalten-Überschrift). */
  protected readonly ownTotal = computed(() => sumCounts(this.ownCounts()));
  protected readonly enemyTotal = computed(
    () => sumCounts(this.enemyShipCounts()) + sumCounts(this.enemyDefCounts()),
  );

  /** Kampf-Schiffe der aktiven Garnison (für „Meine Flotte übernehmen"). */
  protected readonly garrisonCombat = computed(() => {
    const valid = new Set(this.combatShips().map((s) => s.type));
    return (this.state.activePlanet()?.ships ?? []).filter((s) => s.count > 0 && valid.has(s.type));
  });

  /** Übernimmt die eigene Garnison als „Deine Flotte". */
  fillOwnFromFleet(): void {
    const next: Record<string, number> = {};
    for (const s of this.garrisonCombat()) {
      next[s.type] = s.count;
    }
    this.ownCounts.set(next);
  }

  /** Setzt beide Seiten zurück. */
  clearAll(): void {
    this.ownCounts.set({});
    this.enemyShipCounts.set({});
    this.enemyDefCounts.set({});
    this.result.set(null);
  }

  /** Number-Input -> Signal (negatives/leeres wird zu 0). */
  setCount(side: 'own' | 'enemyShip' | 'enemyDef', type: string, value: unknown): void {
    const n = Math.max(0, Math.floor(Number(value) || 0));
    const target =
      side === 'own' ? this.ownCounts : side === 'enemyShip' ? this.enemyShipCounts : this.enemyDefCounts;
    target.update((m) => ({ ...m, [type]: n }));
  }

  simulate(): void {
    if (!this.canSimulate() || this.pending()) {
      return;
    }
    this.pending.set(true);
    this.error.set(null);
    this.api
      .simulateCombat({
        attacker_ships: prune(this.ownCounts()),
        defender_ships: prune(this.enemyShipCounts()),
        defender_defenses: prune(this.enemyDefCounts()),
      })
      .subscribe({
        next: (r) => {
          this.result.set(r);
          this.pending.set(false);
        },
        error: (err) => {
          this.error.set(err?.error?.detail ?? 'Simulation fehlgeschlagen.');
          this.pending.set(false);
        },
      });
  }
}

/** Gibt es mindestens eine Einheit (count > 0)? */
function hasUnit(map: Record<string, number>): boolean {
  return Object.values(map).some((n) => n > 0);
}

function sumCounts(map: Record<string, number>): number {
  return Object.values(map).reduce((a, b) => a + (b > 0 ? b : 0), 0);
}

/** Entfernt 0-/Leer-Eintraege fuer den Request. */
function prune(map: Record<string, number>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(map)) {
    if (v > 0) {
      out[k] = v;
    }
  }
  return out;
}
