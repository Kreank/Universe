import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { PlanetUnit, Requirement, ShipOption, ShipyardCategory, ShipyardResponse } from '../../core/models/api.models';
import { BUILDING_META, DEFENSE_META, RANGE_META, SHIP_META, TECH_META, WEAPON_META, metaFor } from '../../core/models/display';
import { rangeIcon, weaponIcon } from '../../core/models/icon-assets';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { DetailPopupComponent, DetailTag } from '../../shared/components/detail-popup.component';
import { BuildTileComponent } from '../../shared/components/build-tile.component';
import { TabBarComponent } from '../../shared/components/tab-bar.component';
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
  imports: [FormsModule, CountdownComponent, DetailPopupComponent, BuildTileComponent, TabBarComponent],
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

      <app-tab-bar [tabs]="tabDefs()" [active]="activeTab()" (select)="activeTab.set($event)" />
      @if (activeView(); as view) {
        <div class="tile-grid">
          @for (s of view.items; track s.type) {
            <app-build-tile
              [iconSrc]="'assets/img/' + (view.cat === 'ship' ? 'ships' : 'defenses') + '/' + s.type + '.png'"
              [glyph]="unitMeta(s.type, view.cat).glyph"
              [name]="unitMeta(s.type, view.cat).label"
              [badge]="ownedCount(s.type, view.cat)"
              badgeTip="Bestand"
              [cost]="s.cost"
              [available]="balances()"
              [timeSeconds]="s.build_seconds_each"
              [variant]="view.cat === 'defense' ? 'magenta' : 'accent'"
              [locked]="!s.requirements_met"
              (openDetail)="openDetail(s, view.cat)"
            >
              <ng-container action>
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
                    (click)="build(s.type, view.cat)"
                  >
                    {{ pending() === s.type ? '…' : 'Bauen' }}
                  </button>
                </div>
                @if (!s.requirements_met) {
                  <span class="hint warn small">{{ missingReqText(s) }}</span>
                } @else if (!s.can_build) {
                  <span class="hint warn small">Zu wenig Ressourcen</span>
                }
              </ng-container>
            </app-build-tile>
          }
        </div>
      }
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
      /* Unterzeile unter dem Titel. */
      .sub { margin-top: calc(-1 * var(--sp-1)); font-size: var(--fs-sm); }

      /* Bauschleifen-Panel (nutzt globale .card / .panel-title). */
      .queue { margin-bottom: var(--sp-4); }
      .queue-row {
        display: flex; align-items: center; justify-content: space-between;
        gap: var(--sp-3);
        padding: var(--sp-2) 0; font-size: var(--fs-sm);
        border-bottom: 1px solid var(--border);
      }
      .queue-row:last-child { border-bottom: none; }

      .small { font-size: var(--fs-xs); }

      /* Mengen-Eingabe + Bauen-Button in der Kachel-Aktion. */
      .qty-row { display: flex; gap: var(--sp-2); align-items: center; }
      .qty-row input { width: 56px; flex: 0 0 auto; text-align: center; }
      .qty-row .btn { flex: 0 0 auto; white-space: nowrap; }

      /* Hinweistexte unter der Aktion. */
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

  // -- Reiter: Schiff-Kategorien + Verteidigung --
  protected readonly activeTab = signal<string>('');
  protected readonly tabDefs = computed(() => {
    const tabs = this.shipGroups().map((g) => ({ key: g.key, label: g.label, glyph: g.glyph, count: g.ships.length }));
    const defenses = this.data()?.defenses ?? [];
    if (defenses.length) {
      tabs.push({ key: 'defense', label: 'Verteidigung', glyph: '🛡️', count: defenses.length });
    }
    return tabs;
  });
  protected readonly activeView = computed<{ cat: ShipyardCategory; items: ShipOption[] } | null>(() => {
    const tab = this.activeTab();
    if (tab === 'defense') {
      return { cat: 'defense', items: this.data()?.defenses ?? [] };
    }
    const groups = this.shipGroups();
    const g = groups.find((x) => x.key === tab) ?? groups[0] ?? null;
    return g ? { cat: 'ship', items: g.ships } : null;
  });

  /** Aktueller Bestand eines Schiff-/Verteidigungstyps auf dem aktiven Planeten (Eck-Badge). */
  ownedCount(type: string, cat: ShipyardCategory): number {
    const p = this.state.activePlanet();
    const list: PlanetUnit[] = (cat === 'defense' ? p?.defenses : p?.ships) ?? [];
    return list.find((u) => u.type === type)?.count ?? 0;
  }

  constructor() {
    effect(() => {
      const id = this.state.activePlanetId();
      this.state.shipyardVersion(); // bei Werft-Fertigstellung automatisch neu laden
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
      tags.push({ glyph: r.dot, label: r.label, icon: rangeIcon(s.range) });
    }
    if (s.weapon_type) {
      const w = this.weaponMeta(s.weapon_type);
      tags.push({ glyph: w.glyph, label: w.label, tip: w.vs, icon: weaponIcon(s.weapon_type) });
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
