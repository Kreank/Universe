import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { ResearchOption, ResearchResponse, ResearchState } from '../../core/models/api.models';
import { TECH_META, metaFor } from '../../core/models/display';
import { CostLineComponent } from '../../shared/components/cost-line.component';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { NotificationService } from '../../core/services/notification.service';

interface ResearchRow {
  type: string;
  level: number;
  finishesAt: string | null;
  option: ResearchOption | null;
}

interface ResearchGroup {
  key: string;
  label: string;
  glyph: string;
  rows: ResearchRow[];
}

/** Kategorien des Techbaums: Antriebe, Kampftechnik, Fuehrung. */
const CATEGORY_ORDER: { key: string; label: string; glyph: string; types: string[] }[] = [
  {
    key: 'drive',
    label: 'Antriebe & Reichweite',
    glyph: '🚀',
    types: ['energy_tech', 'combustion_drive', 'impulse_drive', 'spy_tech', 'computer_tech'],
  },
  {
    key: 'combat',
    label: 'Kampftechnik',
    glyph: '⚔️',
    types: ['weapons_tech', 'shield_tech', 'armor_tech'],
  },
  {
    key: 'command',
    label: 'Fuehrung & Crew',
    glyph: '🎖️',
    types: ['command_doctrine', 'logistics_tech', 'crew_psychology'],
  },
];

@Component({
  selector: 'app-research',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CostLineComponent, CountdownComponent, IconTileComponent],
  template: `
    <h1>Forschung</h1>
    <p class="muted sub">
      Techbaum · es laeuft nur <strong>eine</strong> Forschung gleichzeitig (Labor:
      {{ state.activePlanet()?.name ?? '—' }}).
    </p>

    @if (activeResearch(); as ar) {
      <div class="card active-banner">
        <span>🔬 In Forschung: {{ meta(ar.type).label }} → Stufe {{ ar.level + 1 }}</span>
        <app-countdown [target]="ar.finishesAt" />
      </div>
    }

    @if (loading()) {
      <p class="empty-state">Lade Techbaum…</p>
    } @else {
      @for (group of groups(); track group.key) {
        <section class="cat">
          <h2 class="cat-title">{{ group.glyph }} {{ group.label }}</h2>
          <div class="grid list">
            @for (t of group.rows; track t.type) {
              <div class="bld" [class.busy]="t.finishesAt">
                <div class="bld-art">
                  <app-icon-tile [glyph]="meta(t.type).glyph" [size]="78" variant="muted" />
                  <span class="lvl" [class.zero]="t.level === 0" title="Stufe">{{ t.level }}</span>
                </div>
                <div class="bld-name tip" [attr.data-tip]="meta(t.type).blurb ?? ''">{{ meta(t.type).label }}</div>

                @if (t.option) {
                  <app-cost-line [cost]="t.option.cost" [available]="balances()" />
                  <div class="bld-meta">
                    <span class="muted small">⏱ {{ formatTime(t.option.research_seconds) }}</span>
                  </div>
                }

                <div class="bld-action">
                  @if (t.finishesAt) {
                    <span class="building-badge">⏳ In Forschung</span>
                    <app-countdown [target]="t.finishesAt" />
                  } @else if (t.option) {
                    <button
                      class="btn btn-primary btn-sm full"
                      type="button"
                      [disabled]="!canStart(t) || pending() === t.type || researchBusy()"
                      (click)="start(t.type)"
                    >
                      {{ pending() === t.type ? '…' : 'Erforschen → ' + t.option.next_level }}
                    </button>
                    @if (!t.option.requirements_met) {
                      <span class="hint warn small">Voraussetzung fehlt</span>
                    } @else if (!t.option.can_afford) {
                      <span class="hint warn small">Zu teuer</span>
                    } @else if (researchBusy()) {
                      <span class="hint small">Labor belegt</span>
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
      .active-banner {
        display: flex; align-items: center; justify-content: space-between;
        gap: 1rem; margin-bottom: 1rem; border-color: var(--border-strong);
        box-shadow: var(--glow);
      }
      .cat { margin-bottom: 1.4rem; }
      .cat-title {
        font-size: 0.9rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: var(--accent); margin: 0 0 0.6rem;
        padding-bottom: 0.35rem; border-bottom: 1px solid var(--border);
      }
      /* Dichtes, icon-zentriertes Kachel-Raster (OGame-Stil). */
      .list { grid-template-columns: repeat(auto-fill, minmax(208px, 1fr)); gap: 0.7rem; }
      .bld {
        display: flex; flex-direction: column; align-items: stretch; gap: 0.5rem;
        padding: 0.75rem; text-align: center;
      }
      .bld.busy { border-color: var(--accent); box-shadow: var(--glow); }
      .bld-art { position: relative; align-self: center; }
      .bld-art .lvl {
        position: absolute; bottom: -5px; right: -5px;
        min-width: 22px; height: 22px; padding: 0 6px; border-radius: 99px;
        background: var(--accent); color: #04121a; font-size: 0.74rem; font-weight: 700;
        display: flex; align-items: center; justify-content: center;
        box-shadow: 0 0 8px var(--accent);
      }
      .bld-art .lvl.zero {
        background: var(--surface-2); color: var(--text-dim);
        box-shadow: none; border: 1px solid var(--border);
      }
      .bld-name { font-weight: 600; font-size: 0.92rem; }
      .bld-meta { display: flex; justify-content: center; gap: 0.8rem; flex-wrap: wrap; }
      .bld-action { margin-top: auto; display: flex; flex-direction: column; align-items: center; gap: 0.3rem; }
      .full { width: 100%; }
      .building-badge { font-size: 0.7rem; color: var(--accent); text-transform: uppercase; letter-spacing: 0.05em; }
      .small { font-size: 0.76rem; }
      .hint { color: var(--text-faint); }
      .hint.warn { color: var(--warn); }
    `,
  ],
})
export class ResearchComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  private readonly data = signal<ResearchResponse | null>(null);
  protected readonly loading = signal(true);
  protected readonly pending = signal<string | null>(null);

  protected readonly rows = computed<ResearchRow[]>(() => {
    const d = this.data();
    if (!d) {
      return [];
    }
    const stateByType = new Map<string, ResearchState>(d.research.map((r) => [r.type, r]));
    const optByType = new Map<string, ResearchOption>(d.available.map((o) => [o.type, o]));
    const types = new Set<string>([...stateByType.keys(), ...optByType.keys()]);
    return [...types]
      .map((type) => {
        const st = stateByType.get(type);
        return {
          type,
          level: st?.level ?? 0,
          finishesAt: st?.finishes_at ?? null,
          option: optByType.get(type) ?? null,
        };
      })
      .sort((a, b) => a.type.localeCompare(b.type));
  });

  /** Gruppiert die Technologien in Kategorien (Reihenfolge aus CATEGORY_ORDER). */
  protected readonly groups = computed<ResearchGroup[]>(() => {
    const byType = new Map(this.rows().map((r) => [r.type, r]));
    const used = new Set<string>();
    const groups: ResearchGroup[] = [];
    for (const cat of CATEGORY_ORDER) {
      const rows = cat.types.map((t) => byType.get(t)).filter((r): r is ResearchRow => !!r);
      rows.forEach((r) => used.add(r.type));
      if (rows.length) {
        groups.push({ key: cat.key, label: cat.label, glyph: cat.glyph, rows });
      }
    }
    // Etwaige unkategorisierte Technologien als "Sonstiges".
    const rest = this.rows().filter((r) => !used.has(r.type));
    if (rest.length) {
      groups.push({ key: 'other', label: 'Sonstiges', glyph: '🔬', rows: rest });
    }
    return groups;
  });

  protected readonly activeResearch = computed(() => this.rows().find((r) => r.finishesAt) ?? null);
  protected readonly researchBusy = computed(() => this.activeResearch() !== null);

  protected readonly balances = computed(() => {
    const res = this.state.activePlanet()?.resources;
    return res
      ? { metal: res.metal.amount, crystal: res.crystal.amount, deuterium: res.deuterium.amount }
      : null;
  });

  constructor() {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.api.getResearch().subscribe({
      next: (res) => {
        this.data.set(res);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  canStart(t: ResearchRow): boolean {
    return (
      !!t.option && t.option.can_afford && t.option.requirements_met && !this.researchBusy()
    );
  }

  start(type: string): void {
    const planetId = this.state.activePlanetId();
    if (!planetId) {
      return;
    }
    this.pending.set(type);
    this.api.startResearch(type, planetId).subscribe({
      next: () => {
        this.pending.set(null);
        this.notify.info('Forschung gestartet', `${this.meta(type).label} wird erforscht.`);
        this.load();
        void this.state.reloadActivePlanet();
      },
      error: (err) => {
        this.pending.set(null);
        this.notify.warning('Forschung nicht moeglich', err?.error?.detail ?? 'Fehler.');
      },
    });
  }

  meta = (t: string) => metaFor(TECH_META, t);

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
