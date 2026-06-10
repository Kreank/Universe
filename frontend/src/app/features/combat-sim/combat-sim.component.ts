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
          <div class="card col">
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
          <div class="card col">
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
    .sim { display: flex; flex-direction: column; gap: 1rem; }
    .sim-head h1 { margin: 0 0 0.25rem; font-size: 1.25rem; }
    .faint { color: var(--text-faint); }
    .small { font-size: 0.82rem; }
    .state { color: var(--text-dim); padding: 1.5rem 0; }

    .cols { display: grid; grid-template-columns: 1fr 1fr; gap: 1rem; }
    .col { display: flex; flex-direction: column; gap: 0.2rem; }

    .sub-head { font-size: 0.72rem; letter-spacing: 0.1em; text-transform: uppercase;
      color: var(--text-dim); margin: 0.7rem 0 0.3rem; }

    /* Panel-Überschrift mit Summen-Badge + Mini-Aktion rechts. */
    .panel-title { justify-content: flex-start; }
    .panel-title .ptotal {
      margin-left: 0.1rem; font-size: 0.72rem; color: var(--accent);
      background: color-mix(in srgb, var(--accent) 14%, transparent);
      border: 1px solid var(--accent-dim); border-radius: 99px; padding: 0.05rem 0.5rem;
    }
    .panel-title .mini {
      margin-left: auto; text-transform: none; letter-spacing: 0; font-size: 0.74rem;
      color: var(--accent); background: rgba(46,230,214,0.08);
      border: 1px solid var(--accent-dim); border-radius: var(--radius-sm);
      padding: 0.2rem 0.55rem; cursor: pointer;
    }
    .panel-title .mini:hover:not(:disabled) { background: rgba(46,230,214,0.18); }
    .panel-title .mini:disabled { opacity: 0.4; cursor: not-allowed; }

    .row { display: grid; grid-template-columns: 40px 1fr 5rem; align-items: center;
      gap: 0.6rem; padding: 0.3rem 0.15rem; border-radius: 8px;
      transition: background 0.12s ease; cursor: pointer; }
    .row:hover { background: rgba(255,255,255,0.03); }
    .r-ico { display: inline-flex; justify-self: center; }
    .r-label { font-size: 0.86rem; color: var(--text); }
    .r-num { width: 100%; text-align: right; }

    .actions { display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap;
      position: sticky; bottom: 0; padding-top: 0.5rem; }
    .err { color: #ff9b9b; font-size: 0.85rem; }

    @media (max-width: 700px) { .cols { grid-template-columns: 1fr; } }
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
