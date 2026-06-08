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
    <p class="muted sub">
      Baue deinen Planeten aus. Es laeuft jeweils ein Bau gleichzeitig.
      @if (fields(); as f) {
        · <span class="fields" [class.full]="f.used >= f.max">Felder {{ f.used }}/{{ f.max }}</span>
      }
    </p>

    @if (loading()) {
      <p class="empty-state">Lade Gebaeude…</p>
    } @else if (rows().length === 0) {
      <p class="empty-state">Keine Gebaeudedaten verfuegbar.</p>
    } @else {
      @for (group of groups(); track group.key) {
        <section class="card cat">
          <h2 class="cat-title">{{ group.glyph }} {{ group.label }}</h2>
          <div class="bld-list">
            @for (b of group.rows; track b.type) {
              <div class="bld-row" [class.busy]="b.finishesAt">
                <div class="bld-art">
                  <app-icon-tile [glyph]="meta(b.type).glyph" [src]="'assets/img/buildings/' + b.type + '.png'" [size]="56" />
                  <span class="lvl" [class.zero]="b.level === 0" title="Stufe">{{ b.level }}</span>
                </div>

                <div class="bld-info">
                  <div class="bld-name tip" [attr.data-tip]="meta(b.type).blurb ?? ''">{{ meta(b.type).label }}</div>
                  @if (b.option) {
                    <div class="bld-stats">
                      <app-cost-line [cost]="b.option.cost" [available]="balances()" />
                      <span class="muted small">⏱ {{ formatTime(b.option.build_seconds) }}</span>
                      @if (b.option.energy_now !== 0 || b.option.energy_delta !== 0) {
                        <span class="energy small"
                          [class.produces]="b.option.energy_now > 0"
                          [class.consumes]="b.option.energy_now < 0"
                          [attr.data-tip]="energyTip(b.option)">
                          ⚡ {{ energyLabel(b.option.energy_now) }}@if (b.option.energy_delta !== 0) {<span class="delta"> (Δ {{ signed(b.option.energy_delta) }})</span>}
                        </span>
                      }
                    </div>
                  }
                </div>

                <div class="bld-action">
                  @if (b.finishesAt) {
                    <span class="building-badge">⏳ Im Bau</span>
                    <app-countdown [target]="b.finishesAt" />
                  } @else {
                    @if (b.option) {
                      <button
                        class="btn btn-primary btn-sm"
                        type="button"
                        [disabled]="!canUpgrade(b) || pending() === b.type || anyBuilding()"
                        (click)="upgrade(b.type)"
                      >
                        {{ pending() === b.type ? '…' : 'Ausbauen → ' + b.option.next_level }}
                      </button>
                      @if (!b.option.requirements_met) {
                        <span class="hint warn small">Voraussetzung fehlt</span>
                      } @else if (!b.option.can_afford) {
                        <span class="hint warn small">Zu teuer</span>
                      } @else if (anyBuilding()) {
                        <span class="hint small">Bauschleife belegt</span>
                      }
                    }
                    @if (b.level > 0) {
                      <button
                        class="btn btn-ghost btn-sm demolish"
                        type="button"
                        [disabled]="pending() === b.type || anyBuilding()"
                        (click)="demolish(b.type)"
                      >
                        Abreissen → {{ b.level - 1 }}
                      </button>
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
      .cat { margin-bottom: 1rem; }
      .cat-title {
        font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.14em;
        color: #b9c6de; margin: 0 0 0.4rem;
        padding-bottom: 0.6rem; border-bottom: 1px solid var(--border);
      }
      /* Zeilen-Layout: Art links, Infos mittig, Aktion rechts. */
      .bld-list { display: flex; flex-direction: column; }
      .bld-row {
        display: flex; align-items: center; gap: 1rem;
        padding: 0.75rem 0.25rem;
        border-bottom: 1px solid rgba(255,255,255,0.06);
      }
      .bld-row:last-child { border-bottom: none; }
      .bld-row.busy { box-shadow: inset 2px 0 0 var(--accent); }
      .bld-art { position: relative; flex: 0 0 auto; }
      .bld-art .lvl {
        position: absolute; bottom: -5px; right: -5px;
        min-width: 20px; height: 20px; padding: 0 5px; border-radius: 99px;
        background: var(--accent); color: #04121a; font-size: 0.72rem; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 8px var(--accent);
      }
      .bld-art .lvl.zero {
        background: var(--surface-2); color: var(--text-dim);
        box-shadow: none; border: 1px solid var(--border);
      }
      .bld-info { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 0.3rem; }
      .bld-name { font-weight: 600; font-size: 0.95rem; }
      .bld-stats { display: flex; align-items: center; gap: 0.9rem; flex-wrap: wrap; }
      .bld-action {
        flex: 0 0 auto; display: flex; flex-direction: column; align-items: flex-end;
        gap: 0.3rem; min-width: 150px;
      }
      .bld-action .btn { white-space: nowrap; }
      .building-badge { font-size: 0.7rem; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; }
      .energy { display: inline-flex; align-items: center; gap: 0.25rem; color: var(--text-dim); }
      .energy.produces { color: var(--ok); }
      .energy.consumes { color: var(--warn); }
      .energy .delta { color: var(--text-faint); }
      .small { font-size: 0.76rem; }
      .hint { color: var(--text-faint); }
      .hint.warn { color: var(--warn); }
      .fields { color: var(--text-dim); }
      .fields.full { color: var(--warn); font-weight: 600; }
      .demolish { color: var(--text-dim); }
      .demolish:hover:not(:disabled) { color: var(--warn); }
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

  /** Feld-Budget des aktiven Planeten (Modell A: 1 Feld pro Gebaeudestufe). */
  protected readonly fields = computed(() => {
    const p = this.state.activePlanet();
    return p ? { used: p.fields_used, max: p.fields_max } : null;
  });

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

  demolish(type: string): void {
    const planetId = this.state.activePlanetId();
    if (!planetId) {
      return;
    }
    this.pending.set(type);
    this.api.demolishBuilding(planetId, type).subscribe({
      next: (res) => {
        this.pending.set(null);
        this.notify.info('Abgerissen', `${this.meta(type).label} ist jetzt Stufe ${res.level}. Feld freigegeben.`);
        this.load(planetId);
        void this.state.reloadActivePlanet();
      },
      error: (err) => {
        this.pending.set(null);
        this.notify.warning('Abriss nicht moeglich', err?.error?.detail ?? 'Fehler beim Abreissen.');
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
