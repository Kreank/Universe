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

interface BuildingGroup {
  key: string;
  label: string;
  glyph: string;
  rows: BuildingRow[];
}

/** Kategorien gemaess Wunsch: Rohstoffe, Energie, Anlagen, Lager, Kommando. */
const CATEGORY_ORDER: { key: string; label: string; glyph: string; types: string[] }[] = [
  { key: 'resource', label: 'Rohstoff-Gebaeude', glyph: '⛏️', types: ['metal_mine', 'crystal_mine', 'deuterium_synth'] },
  { key: 'energy', label: 'Energie', glyph: '⚡', types: ['solar_plant', 'fusion_reactor'] },
  { key: 'facility', label: 'Anlagen', glyph: '🏭', types: ['robot_factory', 'shipyard', 'research_lab'] },
  { key: 'storage', label: 'Lager', glyph: '📦', types: ['metal_storage', 'crystal_storage', 'deuterium_tank'] },
  { key: 'command', label: 'Kommando', glyph: '🎖️', types: ['command_academy', 'command_center'] },
];

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
      @for (group of groups(); track group.key) {
        <section class="cat">
          <h2 class="cat-title">{{ group.glyph }} {{ group.label }}</h2>
          <div class="grid list">
            @for (b of group.rows; track b.type) {
              <div class="card building" [class.busy]="b.finishesAt">
                <app-icon-tile [glyph]="meta(b.type).glyph" [src]="'assets/img/buildings/' + b.type + '.png'" [size]="52" />
                <div class="info">
                  <div class="row-between">
                    <h3 class="tip" [attr.data-tip]="meta(b.type).blurb ?? ''">{{ meta(b.type).label }}</h3>
                    <span class="chip">Stufe {{ b.level }}</span>
                  </div>

                  @if (b.option) {
                    <div class="next">
                      <span class="muted small">Naechste Stufe {{ b.option.next_level }}</span>
                      <app-cost-line [cost]="b.option.cost" [available]="balances()" />
                      <div class="meta-line">
                        <span class="muted small">⏱ {{ formatTime(b.option.build_seconds) }}</span>
                        @if (b.option.energy_now !== 0 || b.option.energy_delta !== 0) {
                          <span class="energy small"
                            [class.produces]="b.option.energy_now > 0"
                            [class.consumes]="b.option.energy_now < 0"
                            [attr.data-tip]="energyTip(b.option)">
                            ⚡ {{ energyLabel(b.option.energy_now) }}
                            @if (b.option.energy_delta !== 0) {
                              <span class="delta">(Δ {{ signed(b.option.energy_delta) }})</span>
                            }
                          </span>
                        }
                      </div>
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
        </section>
      }
    }
  `,
  styles: [
    `
      .sub { margin-top: -0.3rem; font-size: 0.85rem; }
      .cat { margin-bottom: 1.6rem; }
      .cat-title {
        font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: var(--accent); margin: 0 0 0.7rem;
        padding-bottom: 0.4rem; border-bottom: 1px solid var(--border);
      }
      .list { grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
      .meta-line { display: flex; align-items: center; gap: 0.8rem; flex-wrap: wrap; }
      .energy { display: inline-flex; align-items: center; gap: 0.25rem; color: var(--text-dim); }
      .energy.produces { color: var(--ok); }
      .energy.consumes { color: var(--warn); }
      .energy .delta { color: var(--text-faint); }
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

  /** Gruppiert die Gebaeude in Kategorien (Reihenfolge aus CATEGORY_ORDER). */
  protected readonly groups = computed<BuildingGroup[]>(() => {
    const byType = new Map(this.rows().map((r) => [r.type, r]));
    const used = new Set<string>();
    const groups: BuildingGroup[] = [];
    for (const cat of CATEGORY_ORDER) {
      const rows = cat.types.map((t) => byType.get(t)).filter((r): r is BuildingRow => !!r);
      rows.forEach((r) => used.add(r.type));
      if (rows.length) {
        groups.push({ key: cat.key, label: cat.label, glyph: cat.glyph, rows });
      }
    }
    // Etwaige unkategorisierte Gebaeude (z. B. neue Typen) als "Sonstiges".
    const rest = this.rows().filter((r) => !used.has(r.type));
    if (rest.length) {
      groups.push({ key: 'other', label: 'Sonstiges', glyph: '🏗️', rows: rest });
    }
    return groups;
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

  /** Energie-Label: erzeugt (+), verbraucht (-) oder neutral. */
  energyLabel(value: number): string {
    if (value > 0) return `+${Math.round(value)}`;
    if (value < 0) return `${Math.round(value)}`;
    return '0';
  }

  signed(value: number): string {
    const v = Math.round(value);
    return v > 0 ? `+${v}` : `${v}`;
  }

  energyTip(o: BuildingOption): string {
    const verb = o.energy_now > 0 ? 'erzeugt' : o.energy_now < 0 ? 'verbraucht' : 'neutral';
    const now = Math.abs(Math.round(o.energy_now));
    const next = Math.abs(Math.round(o.energy_next));
    if (o.energy_now === 0 && o.energy_delta !== 0) {
      return `Naechste Stufe ${o.energy_next > 0 ? 'erzeugt' : 'verbraucht'} ${next} Energie`;
    }
    return `Aktuell: ${verb} ${now} Energie\nNaechste Stufe: ${next} Energie`;
  }

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
