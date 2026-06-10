import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { NgTemplateOutlet } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { Requirement, ShipOption, ShipyardCategory, ShipyardResponse } from '../../core/models/api.models';
import { BUILDING_META, DEFENSE_META, RANGE_META, SHIP_META, TECH_META, WEAPON_META, metaFor } from '../../core/models/display';
import { CostLineComponent } from '../../shared/components/cost-line.component';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { DetailPopupComponent, DetailTag } from '../../shared/components/detail-popup.component';
import { NotificationService } from '../../core/services/notification.service';

interface SelectedUnit {
  cat: ShipyardCategory;
  option: ShipOption;
}

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
    types: [
      'small_cargo',
      'large_cargo',
      'recycler',
      'colony_ship',
      'solar_satellite',
      'spy_probe',
      'miner',
      'deep_scout',
      'expedition_ship',
    ],
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
  {
    key: 'roles',
    label: 'Rollen-Schiffe',
    glyph: '🎯',
    types: [
      'interceptor',
      'escort_frigate',
      'shield_tender',
      'carrier',
      'drone',
      'interdictor',
      'ewar_frigate',
      'boarder',
      'stealth_corvette',
    ],
  },
];

@Component({
  selector: 'app-shipyard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, NgTemplateOutlet, CostLineComponent, CountdownComponent, IconTileComponent, DetailPopupComponent],
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
        <section class="card cat">
          <h2 class="cat-title">{{ group.glyph }} {{ group.label }}</h2>
          <div class="bld-list">
            @for (s of group.ships; track s.type) {
              <ng-container *ngTemplateOutlet="unitCard; context: { $implicit: s, cat: 'ship' }" />
            }
          </div>
        </section>
      }

      <section class="card cat">
        <h2 class="cat-title">🛡️ Verteidigung</h2>
        <div class="bld-list">
          @for (s of d.defenses; track s.type) {
            <ng-container *ngTemplateOutlet="unitCard; context: { $implicit: s, cat: 'defense' }" />
          }
        </div>
      </section>

      <ng-template #unitCard let-s let-cat="cat">
        <div class="bld-row">
          <div class="bld-art clickable" (click)="openDetail(s, cat)" title="Details ansehen">
            <app-icon-tile
              [glyph]="unitMeta(s.type, cat).glyph"
              [src]="'assets/img/' + (cat === 'ship' ? 'ships' : 'defenses') + '/' + s.type + '.png'"
              [size]="46"
              [variant]="cat === 'defense' ? 'magenta' : 'accent'"
            />
          </div>

          <div class="bld-info">
            <div class="bld-name clickable" (click)="openDetail(s, cat)" title="Details ansehen">{{ unitMeta(s.type, cat).label }} <span class="info-dot">ⓘ</span></div>
            <div class="bld-stats">
              <app-cost-line [cost]="s.cost" [available]="balances()" />
              <span class="muted small">⏱ {{ formatTime(s.build_seconds_each) }} / Stk.</span>
            </div>
          </div>

          <div class="bld-action">
            <div class="qty-row">
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
              <span class="hint warn small">{{ missingReqText(s) }}</span>
            } @else if (!s.can_build) {
              <span class="hint warn small">Zu wenig Ressourcen</span>
            }
          </div>
        </div>
      </ng-template>
    } @else {
      <p class="empty-state">Keine Werft auf diesem Planeten.</p>
    }

    @if (selected(); as sel) {
      <app-detail-popup
        [kind]="sel.cat === 'defense' ? 'defense' : 'ship'"
        [type]="sel.option.type"
        [cost]="sel.option.cost"
        [available]="balances()"
        [buildSeconds]="sel.option.build_seconds_each"
        [requirements]="sel.option.requirements ?? null"
        [tags]="unitTags(sel.option)"
        [quantity]="true"
        [actionLabel]="'Bauen'"
        [actionDisabled]="!buildable(sel.option)"
        [actionHint]="!sel.option.requirements_met ? missingReqText(sel.option) : (!sel.option.can_build ? 'Zu wenig Ressourcen' : null)"
        [pending]="pending() === sel.option.type"
        (confirm)="buildFromPopup($event)"
        (close)="selected.set(null)"
      />
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
      .queue-row:last-child { border-bottom: none; }
      .cat { margin-bottom: 0.7rem; }
      .cat-title {
        font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.14em;
        color: #b9c6de; margin: 0 0 0.3rem;
        padding-bottom: 0.45rem; border-bottom: 1px solid var(--border);
      }
      /* Zeilen-Layout: Art links, Infos mittig, Aktion rechts. */
      .bld-list { display: flex; flex-direction: column; }
      .bld-row {
        display: flex; align-items: center; gap: 1rem;
        padding: 0.75rem 0.25rem;
        border-bottom: 1px solid rgba(255,255,255,0.06);
      }
      .bld-row:last-child { border-bottom: none; }

      /* Desktop: Kacheln statt Vollbreit-Zeilen (wie Gebaeude). */
      @media (min-width: 900px) {
        .bld-list {
          display: grid;
          grid-template-columns: repeat(auto-fill, minmax(330px, 1fr));
          gap: 0.1rem 1.4rem;
        }
        .bld-row { gap: 0.7rem; padding: 0.5rem 0.25rem; }
      }
      .bld-art { position: relative; flex: 0 0 auto; }
      .clickable { cursor: pointer; }
      .bld-art.clickable:hover { filter: brightness(1.15); }
      .bld-info { flex: 1 1 auto; min-width: 0; display: flex; flex-direction: column; gap: 0.3rem; }
      .bld-name { font-weight: 600; font-size: 0.95rem; }
      .bld-name.clickable:hover { color: var(--accent); }
      .info-dot { color: var(--text-faint); font-size: 0.8rem; }
      .bld-name.clickable:hover .info-dot { color: var(--accent); }
      .bld-stats { display: flex; align-items: center; gap: 0.9rem; flex-wrap: wrap; }
      .combat-stats { display: flex; gap: 0.6rem; flex-wrap: wrap; }
      .cchip {
        font-size: 0.72rem; padding: 0.1rem 0.4rem; border-radius: 6px;
        background: rgba(255,255,255,0.05); color: #b9c6de; white-space: nowrap;
      }
      .bld-action {
        flex: 0 0 auto; display: flex; flex-direction: column; align-items: flex-end;
        gap: 0.25rem; min-width: 134px; max-width: 200px;
      }
      .qty-row { display: flex; gap: 0.4rem; align-items: center; }
      .qty-row input { width: 56px; flex: 0 0 auto; text-align: center; }
      .qty-row .btn { flex: 0 0 auto; white-space: nowrap; }
      .small { font-size: 0.76rem; }
      .hint { color: var(--text-faint); text-align: right; }
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
  protected readonly selected = signal<SelectedUnit | null>(null);

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

  openDetail(option: ShipOption, cat: ShipyardCategory): void {
    this.selected.set({ option, cat });
  }

  /** Kampf-Tags (Reichweite, Waffentyp, Antrieb) fuer das Detail-Popup. */
  unitTags(s: ShipOption): DetailTag[] {
    const tags: DetailTag[] = [];
    if (s.range) {
      const r = this.rangeMeta(s.range);
      tags.push({ glyph: r.dot, label: r.label });
    }
    if (s.weapon_type) {
      const w = this.weaponMeta(s.weapon_type);
      tags.push({ glyph: w.glyph, label: w.label, tip: w.vs });
    } else {
      tags.push({ glyph: '🛡', label: 'Unbewaffnet' });
    }
    if (s.drive === 0) {
      tags.push({ glyph: '⚓', label: 'stationär' });
    } else if (s.drive) {
      tags.push({ glyph: '⚙', label: 'Antrieb ' + s.drive });
    }
    return tags;
  }

  /** Bau aus dem Detail-Popup heraus (uebernimmt die gewaehlte Menge). */
  buildFromPopup(count: number): void {
    const sel = this.selected();
    if (!sel) {
      return;
    }
    this.setCount(sel.option.type, count);
    this.build(sel.option.type, sel.cat);
    this.selected.set(null);
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

  protected weaponMeta(t?: string | null) { return t ? (WEAPON_META[t] ?? { label: t, glyph: '•', vs: '' }) : { label: 'Unbewaffnet', glyph: '🛡', vs: '' }; }
  protected rangeMeta(r?: string | null) { return RANGE_META[r ?? ''] ?? { label: r ?? '', dot: '•' }; }

  /** Klarname einer Voraussetzung (Tech ODER Gebaeude) inkl. benoetigter Stufe. */
  reqLabel(r: Requirement): string {
    return metaFor({ ...BUILDING_META, ...TECH_META }, r.type).label + ' ' + r.level;
  }

  /** Anzeigetext der NICHT erfuellten Voraussetzungen mit Klarnamen. */
  missingReqText(option: ShipOption): string {
    const labels = (option.requirements ?? [])
      .filter((r) => !r.met)
      .map((r) => this.reqLabel(r));
    return labels.length ? 'benötigt: ' + labels.join(', ') : 'Voraussetzung fehlt';
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
