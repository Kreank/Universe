import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { BuildingOption, BuildingState, BuildingsResponse } from '../../core/models/api.models';
import { BUILDING_META, metaFor } from '../../core/models/display';
import { CostLineComponent } from '../../shared/components/cost-line.component';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { NotificationService } from '../../core/services/notification.service';

interface BuildingRow {
  type: string;
  level: number;
  finishesAt: string | null;
  option: BuildingOption | null;
}

@Component({
  selector: 'app-buildings',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CostLineComponent, CountdownComponent, IconTileComponent],
  template: `
    <h1>Gebaeude</h1>
    <p class="muted sub">Baue deinen Planeten aus. Es laeuft jeweils ein Bau gleichzeitig.</p>

    @if (loading()) {
      <p class="empty-state">Lade Gebaeude…</p>
    } @else if (rows().length === 0) {
      <p class="empty-state">Keine Gebaeudedaten verfuegbar.</p>
    } @else {
      <div class="grid list">
        @for (b of rows(); track b.type) {
          <div class="card building" [class.busy]="b.finishesAt">
            <app-icon-tile [glyph]="meta(b.type).glyph" [size]="52" />
            <div class="info">
              <div class="row-between">
                <h3 class="tip" [attr.data-tip]="meta(b.type).blurb ?? ''">{{ meta(b.type).label }}</h3>
                <span class="chip">Stufe {{ b.level }}</span>
              </div>

              @if (b.option) {
                <div class="next">
                  <span class="muted small">Naechste Stufe {{ b.option.next_level }}</span>
                  <app-cost-line [cost]="b.option.cost" [available]="balances()" />
                  <span class="muted small">⏱ {{ formatTime(b.option.build_seconds) }}</span>
                </div>
              }
            </div>

            <div class="action">
              @if (b.finishesAt) {
                <span class="muted small">Im Bau</span>
                <app-countdown [target]="b.finishesAt" />
              } @else if (b.option) {
                <button
                  class="btn btn-primary btn-sm"
                  type="button"
                  [disabled]="!canUpgrade(b) || pending() === b.type || anyBuilding()"
                  (click)="upgrade(b.type)"
                >
                  {{ pending() === b.type ? '…' : 'Ausbauen' }}
                </button>
                @if (!b.option.requirements_met) {
                  <span class="hint warn small">Voraussetzung fehlt</span>
                } @else if (!b.option.can_afford) {
                  <span class="hint warn small">Zu teuer</span>
                } @else if (anyBuilding()) {
                  <span class="hint small">Bauschleife belegt</span>
                }
              }
            </div>
          </div>
        }
      </div>
    }
  `,
  styles: [
    `
      .sub { margin-top: -0.3rem; font-size: 0.85rem; }
      .list { grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
      .building {
        display: grid;
        grid-template-columns: auto 1fr auto;
        gap: 0.9rem;
        align-items: center;
      }
      .building.busy { border-color: var(--border-strong); box-shadow: var(--glow); }
      .info { min-width: 0; }
      .info h3 { font-size: 1rem; margin: 0; }
      .next { display: flex; flex-direction: column; gap: 0.3rem; margin-top: 0.4rem; }
      .small { font-size: 0.76rem; }
      .action { display: flex; flex-direction: column; align-items: flex-end; gap: 0.3rem; }
      .hint { color: var(--text-faint); }
      .hint.warn { color: var(--warn); }
    `,
  ],
})
export class BuildingsComponent {
  private readonly api = inject(ApiService);
  private readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  private readonly data = signal<BuildingsResponse | null>(null);
  protected readonly loading = signal(true);
  protected readonly pending = signal<string | null>(null);

  protected readonly rows = computed<BuildingRow[]>(() => {
    const d = this.data();
    if (!d) {
      return [];
    }
    const stateByType = new Map<string, BuildingState>(d.buildings.map((b) => [b.type, b]));
    const optByType = new Map<string, BuildingOption>(d.available.map((o) => [o.type, o]));
    const types = new Set<string>([...stateByType.keys(), ...optByType.keys()]);
    return [...types]
      .map((type) => {
        const st = stateByType.get(type);
        return {
          type,
          level: st?.level ?? 0,
          finishesAt: st?.upgrade_finishes_at ?? null,
          option: optByType.get(type) ?? null,
        };
      })
      .sort((a, b) => a.type.localeCompare(b.type));
  });

  protected readonly anyBuilding = computed(() => this.rows().some((r) => r.finishesAt));

  protected readonly balances = computed(() => {
    const res = this.state.activePlanet()?.resources;
    return res
      ? { metal: res.metal.amount, crystal: res.crystal.amount, deuterium: res.deuterium.amount }
      : null;
  });

  constructor() {
    effect(() => {
      const id = this.state.activePlanetId();
      if (id) {
        this.load(id);
      }
    });
  }

  private load(planetId: string): void {
    this.loading.set(true);
    this.api.getBuildings(planetId).subscribe({
      next: (res) => {
        this.data.set(res);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  canUpgrade(b: BuildingRow): boolean {
    return !!b.option && b.option.can_afford && b.option.requirements_met && !b.finishesAt;
  }

  upgrade(type: string): void {
    const planetId = this.state.activePlanetId();
    if (!planetId) {
      return;
    }
    this.pending.set(type);
    this.api.upgradeBuilding(planetId, type).subscribe({
      next: () => {
        this.pending.set(null);
        this.notify.info('Bau gestartet', `${this.meta(type).label} wird ausgebaut.`);
        this.load(planetId);
        void this.state.reloadActivePlanet();
      },
      error: (err) => {
        this.pending.set(null);
        this.notify.warning('Bau nicht moeglich', err?.error?.detail ?? 'Fehler beim Ausbau.');
      },
    });
  }

  meta = (t: string) => metaFor(BUILDING_META, t);

  formatTime(seconds: number): string {
    const s = Math.max(0, Math.round(seconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) {
      return `${h}h ${m}m`;
    }
    if (m > 0) {
      return `${m}m ${sec}s`;
    }
    return `${sec}s`;
  }
}
