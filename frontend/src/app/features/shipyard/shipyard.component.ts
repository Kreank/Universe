import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgTemplateOutlet } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { ShipOption, ShipyardCategory, ShipyardResponse } from '../../core/models/api.models';
import { DEFENSE_META, SHIP_META, metaFor } from '../../core/models/display';
import { CostLineComponent } from '../../shared/components/cost-line.component';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { NotificationService } from '../../core/services/notification.service';

interface ShipGroup {
  key: string;
  label: string;
  glyph: string;
  ships: ShipOption[];
}

/** Schiffs-Kategorien: zivile Flotte vs. Kampfflotte. */
const SHIP_CATEGORY_ORDER: { key: string; label: string; glyph: string; types: string[] }[] = [
  {
    key: 'civil',
    label: 'Zivile Schiffe',
    glyph: '🚚',
    types: ['small_cargo', 'large_cargo', 'recycler', 'colony_ship', 'solar_satellite', 'spy_probe'],
  },
  {
    key: 'combat',
    label: 'Kampfschiffe',
    glyph: '⚔️',
    types: [
      'light_fighter',
      'heavy_fighter',
      'cruiser',
      'battleship',
      'battlecruiser',
      'bomber',
      'destroyer',
      'deathstar',
    ],
  },
];

@Component({
  selector: 'app-shipyard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, NgTemplateOutlet, CostLineComponent, CountdownComponent, IconTileComponent],
  template: `
    <h1>Werft & Verteidigung</h1>
    <p class="muted sub">Baue Schiffe und Verteidigungsanlagen auf {{ state.activePlanet()?.name ?? '—' }}.</p>

    @if (loading()) {
      <p class="empty-state">Lade Werft…</p>
    } @else if (data(); as d) {
      <!-- Bauschleife -->
      <section class="card queue">
        <div class="panel-title">🛠️ Bauschleife</div>
        @if (d.queue.length) {
          @for (q of d.queue; track $index) {
            <div class="queue-row">
              <span>{{ unitMeta(q.type, q.category).glyph }} {{ q.count }}× {{ unitMeta(q.type, q.category).label }}</span>
              <app-countdown [target]="q.finishes_at" />
            </div>
          }
        } @else {
          <p class="muted small">Bauschleife leer.</p>
        }
      </section>

      @for (group of shipGroups(); track group.key) {
        <section class="cat">
          <h2 class="cat-title">{{ group.glyph }} {{ group.label }}</h2>
          <div class="grid list">
            @for (s of group.ships; track s.type) {
              <ng-container *ngTemplateOutlet="unitCard; context: { $implicit: s, cat: 'ship' }" />
            }
          </div>
        </section>
      }

      <section class="cat">
        <h2 class="cat-title">🛡️ Verteidigung</h2>
        <div class="grid list">
          @for (s of d.defenses; track s.type) {
            <ng-container *ngTemplateOutlet="unitCard; context: { $implicit: s, cat: 'defense' }" />
          }
        </div>
      </section>

      <ng-template #unitCard let-s let-cat="cat">
        <div class="card unit">
          <div class="unit-head">
            <app-icon-tile
              [glyph]="unitMeta(s.type, cat).glyph"
              [size]="48"
              [variant]="cat === 'defense' ? 'magenta' : 'accent'"
            />
            <div>
              <h3 class="tip" [attr.data-tip]="unitMeta(s.type, cat).blurb ?? ''">{{ unitMeta(s.type, cat).label }}</h3>
              <app-cost-line [cost]="s.cost" [available]="balances()" />
              <div class="muted small">⏱ {{ formatTime(s.build_seconds_each) }} / Stueck</div>
            </div>
          </div>
          <div class="unit-build">
            <input
              type="number"
              min="1"
              [ngModel]="unitCount(s.type)"
              (ngModelChange)="setCount(s.type, $event)"
              [disabled]="!buildable(s)"
              aria-label="Anzahl"
            />
            <button
              class="btn btn-sm"
              [class.btn-primary]="buildable(s)"
              type="button"
              [disabled]="!buildable(s) || pending() === s.type"
              (click)="build(s.type, cat)"
            >
              {{ pending() === s.type ? '…' : 'Bauen' }}
            </button>
          </div>
          @if (!s.requirements_met) {
            <span class="hint warn small">Voraussetzung fehlt</span>
          } @else if (!s.can_build) {
            <span class="hint warn small">Zu wenig Ressourcen</span>
          }
        </div>
      </ng-template>
    } @else {
      <p class="empty-state">Keine Werft auf diesem Planeten.</p>
    }
  `,
  styles: [
    `
      .sub { margin-top: -0.3rem; font-size: 0.85rem; }
      .queue { margin-bottom: 1.2rem; }
      .queue-row {
        display: flex; align-items: center; justify-content: space-between;
        padding: 0.4rem 0; font-size: 0.88rem; border-bottom: 1px solid rgba(255,255,255,0.05);
      }
      .cat { margin-bottom: 1.6rem; }
      .cat-title {
        font-size: 0.95rem; text-transform: uppercase; letter-spacing: 0.06em;
        color: var(--accent); margin: 0 0 0.7rem;
        padding-bottom: 0.4rem; border-bottom: 1px solid var(--border);
      }
      .list { grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); }
      .unit-head { display: flex; gap: 0.8rem; align-items: flex-start; }
      .unit h3 { font-size: 0.98rem; margin: 0 0 0.3rem; }
      .unit-build { display: flex; gap: 0.5rem; margin-top: 0.7rem; }
      .unit-build input { width: 90px; }
      .small { font-size: 0.76rem; }
      .hint { display: block; margin-top: 0.4rem; color: var(--text-faint); }
      .hint.warn { color: var(--warn); }
    `,
  ],
})
export class ShipyardComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  protected readonly data = signal<ShipyardResponse | null>(null);
  protected readonly loading = signal(true);
  protected readonly pending = signal<string | null>(null);
  protected readonly counts = signal<Record<string, number>>({});

  protected readonly balances = computed(() => {
    const res = this.state.activePlanet()?.resources;
    return res
      ? { metal: res.metal.amount, crystal: res.crystal.amount, deuterium: res.deuterium.amount }
      : null;
  });

  /** Gruppiert die Schiffe in Kategorien (Reihenfolge aus SHIP_CATEGORY_ORDER). */
  protected readonly shipGroups = computed<ShipGroup[]>(() => {
    const ships = this.data()?.ships ?? [];
    const byType = new Map(ships.map((s) => [s.type, s]));
    const used = new Set<string>();
    const groups: ShipGroup[] = [];
    for (const cat of SHIP_CATEGORY_ORDER) {
      const rows = cat.types.map((t) => byType.get(t)).filter((s): s is ShipOption => !!s);
      rows.forEach((s) => used.add(s.type));
      if (rows.length) {
        groups.push({ key: cat.key, label: cat.label, glyph: cat.glyph, ships: rows });
      }
    }
    // Etwaige unkategorisierte Schiffe als "Sonstiges".
    const rest = ships.filter((s) => !used.has(s.type));
    if (rest.length) {
      groups.push({ key: 'other', label: 'Sonstiges', glyph: '🚀', ships: rest });
    }
    return groups;
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
    this.api.getShipyard(planetId).subscribe({
      next: (res) => {
        this.data.set(res);
        this.loading.set(false);
      },
      error: () => {
        this.data.set(null);
        this.loading.set(false);
      },
    });
  }

  buildable(s: ShipOption): boolean {
    return s.can_build && s.requirements_met;
  }

  unitCount(type: string): number {
    return this.counts()[type] ?? 1;
  }

  setCount(type: string, value: number): void {
    this.counts.update((c) => ({ ...c, [type]: Math.max(1, Math.floor(value || 1)) }));
  }

  build(type: string, category: ShipyardCategory): void {
    const planetId = this.state.activePlanetId();
    if (!planetId) {
      return;
    }
    const count = this.counts()[type] ?? 1;
    this.pending.set(type);
    this.api.buildShips(planetId, { type, count, category }).subscribe({
      next: (res) => {
        this.pending.set(null);
        this.data.update((d) => (d ? { ...d, queue: res.queue } : d));
        this.notify.info('In Bau', `${count}× ${this.unitMeta(type, category).label} eingereiht.`);
        void this.state.reloadActivePlanet();
      },
      error: (err) => {
        this.pending.set(null);
        this.notify.warning('Bau nicht moeglich', err?.error?.detail ?? 'Fehler.');
      },
    });
  }

  unitMeta(type: string, category: ShipyardCategory) {
    return metaFor(category === 'defense' ? DEFENSE_META : SHIP_META, type);
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
