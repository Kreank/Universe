import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  linkedSignal,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import { Coordinate, FleetMission, PlanetUnit } from '../../core/models/api.models';
import { MISSION_META, RANK_META, SHIP_META, metaFor } from '../../core/models/display';
import { IconTileComponent } from './icon-tile.component';

/**
 * Kompaktes Versand-Overlay (OGame-Schnellaktion): direkt aus der Galaxie
 * eine Flotte zu einem Ziel schicken — Schiffs-Picker, optional Cargo
 * (Transport/Stationierung), Commander, Tempo — ohne Tab-Wechsel.
 *
 * Liest verfuegbare Schiffe/Commander/Ressourcen aus dem GameState des aktiven
 * Planeten und sendet via ApiService. Schliesst nach erfolgreichem Start.
 */
@Component({
  selector: 'app-fleet-dispatch',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, IconTileComponent],
  host: { '(document:keydown.escape)': 'close.emit()' },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>

        <header class="head">
          <h2>{{ missionMeta(mission()).glyph }} Flotte entsenden</h2>
          <span class="coord mono">→ [{{ target().galaxy }}:{{ target().system }}:{{ target().position }}]</span>
          @if (targetName()) { <span class="tname">{{ targetName() }}</span> }
        </header>

        <!-- Missionswahl -->
        <div class="mission-tabs">
          @for (m of missions; track m) {
            <button
              type="button"
              class="mtab"
              [class.active]="mission() === m"
              (click)="mission.set(m)"
            >{{ missionMeta(m).glyph }} {{ missionMeta(m).label }}</button>
          }
        </div>

        <!-- Schiffs-Picker -->
        <div class="ships">
          @for (s of availableShips(); track s.type) {
            <div class="ship" [class.picked]="shipCount(s.type) > 0">
              <div class="ship-art">
                <app-icon-tile [glyph]="shipMeta(s.type).glyph" [src]="'assets/img/ships/' + s.type + '.png'" [size]="40" />
                <span class="avail" title="vorhanden">{{ s.count }}</span>
              </div>
              <div class="ship-name">{{ shipMeta(s.type).label }}</div>
              <div class="ship-pick">
                <input type="number" min="0" [max]="s.count"
                  [ngModel]="shipCount(s.type)" (ngModelChange)="setShip(s.type, $event, s.count)" aria-label="Menge" />
                <button class="btn btn-ghost btn-sm" type="button" (click)="setShip(s.type, s.count, s.count)">alle</button>
              </div>
            </div>
          } @empty {
            <p class="muted small">Keine Schiffe auf diesem Planeten. <a href="/shipyard">Werft →</a></p>
          }
        </div>

        @if (missionHint(); as h) {
          <p class="hint small">{{ h }}</p>
        }

        <!-- Cargo (Transport/Stationierung) -->
        @if (showCargo()) {
          <div class="cargo">
            <div class="cargo-title">📦 Fracht</div>
            <div class="cargo-row">
              @for (r of cargoFields; track r.key) {
                <div class="cargo-field">
                  <label>{{ r.glyph }} {{ r.label }}</label>
                  <input type="number" min="0" [max]="planetRes()?.[r.key]?.amount ?? 0"
                    [ngModel]="cargo()[r.key]" (ngModelChange)="setCargo(r.key, $event)" />
                  <button class="btn btn-ghost btn-sm" type="button"
                    (click)="setCargo(r.key, planetRes()?.[r.key]?.amount ?? 0)">max</button>
                </div>
              }
            </div>
          </div>
        }

        <!-- Commander + Tempo -->
        <div class="opts">
          <div class="field">
            <label>Commander</label>
            <select [ngModel]="commanderId()" (ngModelChange)="commanderId.set($event)">
              <option [ngValue]="null">— ohne —</option>
              @for (c of assignableCommanders(); track c.id) {
                <option [ngValue]="c.id">{{ rankMeta(c.rank).glyph }} {{ c.name }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label class="tip" data-tip="Langsamer = weniger Sprit">Tempo {{ speed() }}%</label>
            <input type="range" min="10" max="100" step="10" [ngModel]="speed()" (ngModelChange)="speed.set($event)" />
          </div>
        </div>

        <div class="actions">
          <button class="btn btn-primary" type="button" [disabled]="!canSend() || sending()" (click)="send()">
            {{ sending() ? 'Sende…' : (missionMeta(mission()).glyph + ' ' + missionMeta(mission()).label + ' starten') }}
          </button>
        </div>
        @if (!hasSelection()) {
          <p class="hint small">Mindestens ein Schiff auswählen.</p>
        }
      </div>
    </div>
  `,
  styles: [
    `
      .backdrop {
        position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center;
        padding: 1rem; background: rgba(4, 7, 14, 0.72); backdrop-filter: blur(4px);
      }
      .popup {
        position: relative; width: 100%; max-width: 560px; max-height: 88vh; overflow-y: auto;
        background: linear-gradient(160deg, var(--surface-2), var(--surface));
        border: 1px solid var(--border-strong); border-radius: var(--radius);
        box-shadow: var(--shadow), var(--glow); padding: 1.1rem 1.2rem 1.2rem;
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
      }
      .x {
        position: absolute; top: 0.5rem; right: 0.6rem; width: 30px; height: 30px; border-radius: 8px;
        background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text-dim);
        cursor: pointer; display: flex; align-items: center; justify-content: center;
      }
      .x:hover { color: var(--text); background: rgba(255,255,255,0.1); }
      .head { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.5rem 0.7rem; padding-right: 2rem; }
      .head h2 { margin: 0; font-size: 1.15rem; }
      .coord { color: var(--accent); font-size: 0.9rem; }
      .tname { color: var(--text-dim); font-size: 0.85rem; }

      .mission-tabs { display: flex; flex-wrap: wrap; gap: 0.3rem; margin: 0.8rem 0; }
      .mtab {
        font-size: 0.8rem; padding: 0.3rem 0.6rem; border-radius: 99px;
        background: rgba(255,255,255,0.04); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer;
      }
      .mtab:hover { color: var(--text); }
      .mtab.active { background: rgba(46,230,214,0.14); color: var(--accent); border-color: var(--accent-dim); }

      .ships {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 0.5rem; margin-top: 0.4rem;
      }
      .ship {
        display: flex; flex-direction: column; align-items: center; gap: 0.25rem;
        padding: 0.45rem; border: 1px solid var(--border); border-radius: var(--radius-sm);
        background: rgba(255,255,255,0.02);
      }
      .ship.picked { border-color: var(--accent-dim); background: rgba(46,230,214,0.06); }
      .ship-art { position: relative; }
      .ship-art .avail {
        position: absolute; bottom: -4px; right: -6px; min-width: 18px; padding: 0 4px; height: 18px;
        border-radius: 99px; background: var(--surface-3); border: 1px solid var(--border);
        font-size: 0.7rem; display: flex; align-items: center; justify-content: center; color: var(--text);
      }
      .ship-name { font-size: 0.76rem; text-align: center; line-height: 1.1; color: var(--text-dim); }
      .ship-pick { display: flex; gap: 0.25rem; align-items: center; }
      .ship-pick input { width: 52px; text-align: center; min-height: 28px; padding: 0.2rem; }

      .cargo { margin-top: 0.9rem; }
      .cargo-title { font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em; color: #b9c6de; margin-bottom: 0.4rem; }
      .cargo-row { display: flex; flex-wrap: wrap; gap: 0.6rem; }
      .cargo-field { display: flex; flex-direction: column; gap: 0.2rem; flex: 1 1 130px; }
      .cargo-field label { font-size: 0.74rem; color: var(--text-dim); }
      .cargo-field input { min-height: 30px; }

      .opts { display: flex; flex-wrap: wrap; gap: 0.9rem; margin-top: 0.9rem; }
      .opts .field { flex: 1 1 200px; display: flex; flex-direction: column; gap: 0.25rem; }
      .opts label { font-size: 0.74rem; color: var(--text-dim); }

      .actions { margin-top: 1rem; }
      .actions .btn { width: 100%; }
      .hint { color: var(--warn); margin: 0.4rem 0 0; }
    `,
  ],
})
export class FleetDispatchComponent {
  private readonly api = inject(ApiService);
  private readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  readonly target = input.required<Coordinate>();
  readonly targetName = input<string | null>(null);
  readonly initialMission = input<FleetMission>('attack');

  readonly close = output<void>();
  readonly sent = output<void>();

  /** Auf die galaxie-relevanten Missionen beschraenkt. */
  protected readonly missions: FleetMission[] = ['attack', 'transport', 'spy', 'deploy'];
  protected readonly mission = linkedSignal<FleetMission>(() => this.initialMission());

  protected readonly cargoFields = [
    { key: 'metal' as const, glyph: '⛏️', label: 'Metall' },
    { key: 'crystal' as const, glyph: '💎', label: 'Kristall' },
    { key: 'deuterium' as const, glyph: '🛢️', label: 'Deuterium' },
  ];

  protected readonly selection = signal<Record<string, number>>({});
  protected readonly cargo = signal<{ metal: number; crystal: number; deuterium: number }>({
    metal: 0, crystal: 0, deuterium: 0,
  });
  protected readonly commanderId = signal<string | null>(null);
  protected readonly speed = signal(100);
  protected readonly sending = signal(false);

  private readonly missionRequires: Partial<Record<FleetMission, { type: string; label: string }>> = {
    spy: { type: 'spy_probe', label: 'Spionagesonde' },
  };

  protected readonly availableShips = computed<PlanetUnit[]>(
    () => this.state.activePlanet()?.ships?.filter((s) => s.count > 0) ?? [],
  );
  protected readonly planetRes = computed(() => this.state.activePlanet()?.resources ?? null);
  protected readonly assignableCommanders = computed(() =>
    this.state.commanders().filter((c) => c.status !== 'training' && !c.assigned_fleet_id),
  );

  protected readonly showCargo = computed(
    () => this.mission() === 'transport' || this.mission() === 'deploy',
  );
  protected readonly hasSelection = computed(() =>
    Object.values(this.selection()).some((n) => n > 0),
  );
  protected readonly missionHint = computed<string | null>(() => {
    const req = this.missionRequires[this.mission()];
    if (!req) {
      return null;
    }
    return this.shipCount(req.type) > 0 ? null : `Diese Mission benötigt mindestens ein ${req.label}.`;
  });
  protected readonly canSend = computed(
    () => this.hasSelection() && !!this.state.activePlanetId() && !this.missionHint(),
  );

  shipCount(type: string): number {
    return this.selection()[type] ?? 0;
  }

  setShip(type: string, value: number, max: number): void {
    const n = Math.max(0, Math.min(max, Math.floor(value || 0)));
    this.selection.update((s) => ({ ...s, [type]: n }));
  }

  setCargo(key: 'metal' | 'crystal' | 'deuterium', value: number): void {
    const cap = Math.floor(this.planetRes()?.[key]?.amount ?? 0);
    const n = Math.max(0, Math.min(cap, Math.floor(value || 0)));
    this.cargo.update((c) => ({ ...c, [key]: n }));
  }

  send(): void {
    const origin = this.state.activePlanetId();
    if (!origin || !this.canSend()) {
      return;
    }
    const ships: Record<string, number> = {};
    for (const [type, n] of Object.entries(this.selection())) {
      if (n > 0) {
        ships[type] = n;
      }
    }
    const cargo = this.showCargo()
      ? this.cargo()
      : { metal: 0, crystal: 0, deuterium: 0 };
    this.sending.set(true);
    this.api
      .sendFleet({
        origin_planet_id: origin,
        target: this.target(),
        mission: this.mission(),
        ships,
        cargo,
        commander_id: this.commanderId(),
        speed_pct: this.speed(),
      })
      .subscribe({
        next: () => {
          this.sending.set(false);
          this.notify.success('Flotte gestartet', `Mission ${this.missionMeta(this.mission()).label} unterwegs.`);
          void this.state.reloadFleets();
          void this.state.reloadActivePlanet();
          void this.state.reloadCommanders();
          this.sent.emit();
          this.close.emit();
        },
        error: (err) => {
          this.sending.set(false);
          this.notify.warning('Start fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
        },
      });
  }

  shipMeta = (t: string) => metaFor(SHIP_META, t);
  missionMeta = (m: string) => metaFor(MISSION_META, m);
  rankMeta = (r: string) => metaFor(RANK_META, r);
}
