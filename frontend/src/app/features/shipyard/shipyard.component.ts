import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { PlanetUnit, Requirement, ShipOption, ShipyardCategory, ShipyardResponse } from '../../core/models/api.models';
import { BUILDING_META, DEFENSE_META, RANGE_META, SHIP_META, TECH_META, WEAPON_META, metaFor } from '../../core/models/display';
import { defenseIcon, missionIcon, navIcon, rangeIcon, resourceIcon, shipIcon, statIcon, statusIcon, uiIcon, weaponIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { DetailPopupComponent, DetailTag } from '../../shared/components/detail-popup.component';
import { BuildTileComponent } from '../../shared/components/build-tile.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { TabBarComponent } from '../../shared/components/tab-bar.component';
import {
  ConfirmDialogComponent,
  ConfirmRequest,
} from '../../shared/components/confirm-dialog.component';
import { NotificationService } from '../../core/services/notification.service';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { scrollToTile } from '../../shared/focus-scroll';

interface SelectedUnit {
  cat: ShipyardCategory;
  option: ShipOption;
}

interface ShipGroup {
  key: string;
  label: string;
  glyph: string;
  icon: string | null;
  ships: ShipOption[];
}

/** Schiffs-Kategorien: zivile Flotte vs. Kampfflotte. */
const SHIP_CATEGORY_ORDER: { key: string; label: string; glyph: string; icon: string | null; types: string[] }[] = [
  {
    key: 'civil',
    label: 'Zivile Schiffe',
    glyph: '🚚',
    icon: missionIcon('transport'),
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
    icon: statusIcon('attack'),
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
    icon: uiIcon('target'),
    types: [
      'interceptor',
      'escort_frigate',
      'shield_tender',
      'carrier',
      'drone',
      'interdictor',
      'warp_stabilizer',
      'ewar_frigate',
      'boarder',
      'stealth_corvette',
    ],
  },
];

@Component({
  selector: 'app-shipyard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, CountdownComponent, DetailPopupComponent, BuildTileComponent, IconTileComponent, TabBarComponent, ConfirmDialogComponent, BtnIconComponent],
  template: `
    <h1>Werft</h1>
    <p class="muted sub">Baue Raumschiffe auf {{ state.activePlanet()?.name ?? '—' }}. Planetare Verteidigung entsteht in der <a routerLink="/defense">Verteidigung</a>.</p>

    @if (loading()) {
      <p class="empty-state">Lade Werft…</p>
    } @else if (data(); as d) {
      <!-- Bauschleife (nur Schiffe; Verteidigung hat eine eigene, parallele Schlange) -->
      <section class="card queue">
        <div class="panel-title"><app-btn-icon [src]="navIcon('shipyard')" glyph="🛠️" [size]="16" /> Bauschleife</div>
        @if (queueView().length) {
          @for (q of queueView(); track q.id; let first = $first) {
            <div class="queue-row" [class.building]="first" [class.waiting]="!first">
              <span class="q-unit">
                <app-icon-tile class="q-ico" [glyph]="unitMeta(q.type, q.category).glyph" [src]="unitIcon(q.type, q.category)" [size]="22" variant="muted" />{{ q.count }}× {{ unitMeta(q.type, q.category).label }}
                @if (first) {
                  <span class="q-status active">⏳ Im Bau</span>
                } @else {
                  <span class="q-status wait">⏸ wartet</span>
                }
              </span>
              <div class="q-right">
                @if (first) {
                  <app-countdown [target]="q.finishes_at" />
                } @else {
                  <span class="q-eta muted tip" data-tip="Startet erst, wenn die vorherigen Aufträge fertig sind (serielle Werft). Eine Bauzeit läuft hier noch nicht.">in Warteschlange</span>
                }
                <button
                  class="btn btn-ghost btn-sm q-cancel"
                  type="button"
                  [disabled]="cancelling() === q.id"
                  (click)="askCancelQueue(q.id, q.type, q.category, q.count)"
                  title="Auftrag abbrechen — Ressourcen zurueck"
                >
                  {{ cancelling() === q.id ? '…' : '✕' }}
                </button>
              </div>
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
              [attr.id]="'tile-' + s.type"
              [iconSrc]="'assets/img/' + (view.cat === 'ship' ? 'ships' : 'defenses') + '/' + s.type + '.png'"
              [glyph]="unitMeta(s.type, view.cat).glyph"
              [name]="unitMeta(s.type, view.cat).label"
              [badge]="ownedCount(s.type, view.cat)"
              [focused]="focusType() === s.type"
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
                <span class="stock-line">Auf diesem Planeten: <strong>{{ ownedCount(s.type, view.cat) }}</strong></span>
                @if (s.capstone) {
                  <span class="hint small cap-line">
                    Besitz {{ s.capstone.owned }}/{{ s.capstone.cap }}
                    @if (s.cost.antimatter) { · <app-btn-icon [src]="resourceIcon('antimatter')" glyph="⚛️" [size]="14" /> {{ s.cost.antimatter }} }
                    @if (s.cost.dark_matter) { · <app-btn-icon [src]="resourceIcon('dark_matter')" glyph="🌑" [size]="14" /> {{ s.cost.dark_matter }} }
                  </span>
                }
                @if (!s.requirements_met) {
                  <span class="hint warn small">{{ missingReqText(s) }}</span>
                } @else if (s.capstone && s.capstone.owned >= s.capstone.cap) {
                  <span class="hint warn small">Besitz-Limit erreicht — Kommando-Forschung für +1</span>
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

    @if (confirmReq(); as c) {
      <app-confirm-dialog
        [title]="c.title"
        [message]="c.message"
        [confirmLabel]="c.confirmLabel"
        [pending]="cancelling() !== null"
        (confirm)="runConfirm()"
        (dismiss)="confirmReq.set(null)"
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
        padding: var(--sp-2) 0 var(--sp-2) var(--sp-3); font-size: var(--fs-sm);
        border-bottom: 1px solid var(--border);
      }
      .queue-row:last-child { border-bottom: none; }

      /* Aktiv bauender (erster) Auftrag: pulsierender Akzent-Balken links. */
      .queue-row.building { position: relative; }
      .queue-row.building::before {
        content: ''; position: absolute; left: 0; top: 18%; bottom: 18%; width: 3px;
        border-radius: var(--r-pill); background: var(--accent); box-shadow: var(--glow-soft);
        animation: qBuild 1.6s ease-in-out infinite;
      }
      @keyframes qBuild { 0%, 100% { opacity: 0.35; } 50% { opacity: 1; } }
      @media (prefers-reduced-motion: reduce) { .queue-row.building::before { animation: none; opacity: 0.7; } }
      .q-unit { display: inline-flex; align-items: center; gap: var(--sp-2); }
      .q-ico { flex: 0 0 auto; }
      /* Status-Chip: aktiv bauender vs. wartender Auftrag (macht die serielle Schlange klar). */
      .q-status {
        flex: 0 0 auto; font-size: var(--fs-xs); font-weight: 600;
        padding: 1px var(--sp-2); border-radius: var(--r-pill); white-space: nowrap;
      }
      .q-status.active { color: #04201d; background: var(--accent); }
      .q-status.wait { color: var(--text-dim); background: rgba(255,255,255,0.06); border: 1px solid var(--border-strong); }
      .queue-row.waiting { opacity: 0.7; }
      .q-eta { display: inline-flex; align-items: center; gap: 4px; font-size: var(--fs-xs); cursor: help; }

      .small { font-size: var(--fs-xs); }

      /* Mengen-Eingabe + Bauen-Button in der Kachel-Aktion. */
      .qty-row { display: flex; gap: var(--sp-2); align-items: center; }
      .qty-row input { width: 56px; flex: 0 0 auto; text-align: center; }
      .qty-row .btn { flex: 0 0 auto; white-space: nowrap; }

      /* Hinweistexte unter der Aktion. */
      .hint { color: var(--text-faint); text-align: right; }
      .hint.warn { color: var(--warn); }

      /* Klar sichtbarer Bestand auf dem aktiven Planeten (nicht nur der Eck-Badge). */
      .stock-line { display: block; font-size: var(--fs-xs); color: var(--text-dim); margin-top: var(--sp-1); }
      .stock-line strong { color: var(--accent); font-variant-numeric: tabular-nums; }

      /* Bauschleifen-Zeile: Countdown + Abbrechen-Button rechts. */
      .q-right { display: flex; align-items: center; gap: var(--sp-2); flex: 0 0 auto; }
      .q-cancel { color: var(--text-faint); min-width: 30px; }
      .q-cancel:hover:not(:disabled) { color: var(--danger); border-color: var(--danger-dim); }
    `,
  ],
})
export class ShipyardComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);

  /** Per Deeplink angesprungener Bau (Query-Param ?focus=) — Reiter + Highlight + Scroll. */
  protected readonly focusType = signal<string | null>(null);
  private focusHandled = false;

  /** Asset-Pfad-Helfer fuers Template (Buttons mit Glyph-Fallback via app-btn-icon). */
  protected readonly navIcon = navIcon;
  protected readonly resourceIcon = resourceIcon;

  protected readonly data = signal<ShipyardResponse | null>(null);
  protected readonly loading = signal(true);
  protected readonly pending = signal<string | null>(null);
  protected readonly cancelling = signal<string | null>(null);
  protected readonly counts = signal<Record<string, number>>({});
  protected readonly selected = signal<SelectedUnit | null>(null);
  /** Ausstehende Sicherheitsabfrage (Werft-Auftrag abbrechen) — null = kein Dialog offen. */
  protected readonly confirmReq = signal<ConfirmRequest | null>(null);

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
        groups.push({ key: cat.key, label: cat.label, glyph: cat.glyph, icon: cat.icon, ships: rows });
      }
    }
    // Etwaige unkategorisierte Schiffe als "Sonstiges".
    const rest = ships.filter((s) => !used.has(s.type));
    if (rest.length) {
      groups.push({ key: 'other', label: 'Sonstiges', glyph: '🚀', icon: navIcon('fleet'), ships: rest });
    }
    return groups;
  });

  /** Bauschleife der Werft: nur Schiff-Auftraege (Verteidigung hat eine eigene, parallele Schlange). */
  protected readonly queueView = computed(() => (this.data()?.queue ?? []).filter((q) => q.category === 'ship'));

  // -- Reiter: nur Schiff-Kategorien (Verteidigung ist ein eigener Screen) --
  protected readonly activeTab = signal<string>('');
  protected readonly tabDefs = computed(() =>
    this.shipGroups().map((g) => ({ key: g.key, label: g.label, glyph: g.glyph, icon: g.icon, count: g.ships.length })),
  );
  protected readonly activeView = computed<{ cat: ShipyardCategory; items: ShipOption[] } | null>(() => {
    const tab = this.activeTab();
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
    const focus = this.route.snapshot.queryParamMap.get('focus');
    if (focus) {
      this.focusType.set(focus);
    }
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
        this.applyFocus();
      },
      error: () => {
        this.data.set(null);
        this.loading.set(false);
      },
    });
  }

  /** Deeplink vom Dashboard: zum Werft-Auftrag springen (richtiger Reiter + Scroll + Flash). */
  private applyFocus(): void {
    const ft = this.focusType();
    if (this.focusHandled || !ft) {
      return;
    }
    this.focusHandled = true;
    const grp = this.shipGroups().find((g) => g.ships.some((s) => s.type === ft));
    if (grp) {
      this.activeTab.set(grp.key);
    }
    scrollToTile(ft);
    setTimeout(() => this.focusType.set(null), 4500);
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
      tags.push({ glyph: '🛡', label: 'Unbewaffnet', icon: statIcon('shield') });
    }
    if (s.drive === 0) {
      tags.push({ glyph: '⚓', label: 'stationär', icon: statusIcon('stranded') });
    } else if (s.drive) {
      tags.push({ glyph: '⚙', label: 'Antrieb ' + s.drive, icon: statIcon('speed') });
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

  /** Findet die Bau-Option (Schiff/Verteidigung) zu einem Typ im aktuellen Werft-Datensatz. */
  private findOption(type: string, category: ShipyardCategory): ShipOption | undefined {
    const d = this.data();
    if (!d) {
      return undefined;
    }
    const list = category === 'defense' ? d.defenses : d.ships;
    return list?.find((o) => o.type === type);
  }

  /**
   * Maximal baubare Stueckzahl mit den aktuellen Rohstoffen (Stueckkosten linear).
   * Liefert Infinity, wenn die Einheit nichts kostet, und 0, wenn nicht mal eines geht.
   */
  private maxAffordable(cost: { metal?: number; crystal?: number; deuterium?: number }): number {
    const bal = this.balances();
    if (!bal) {
      return Infinity; // Rohstoffe unbekannt -> nicht klemmen, Backend validiert.
    }
    let max = Infinity;
    for (const key of ['metal', 'crystal', 'deuterium'] as const) {
      const c = cost[key] ?? 0;
      if (c > 0) {
        max = Math.min(max, Math.floor(bal[key] / c));
      }
    }
    return max === Infinity ? Infinity : Math.max(0, max);
  }

  build(type: string, category: ShipyardCategory): void {
    const planetId = this.state.activePlanetId();
    if (!planetId) {
      return;
    }
    let count = this.counts()[type] ?? 1;
    const label = this.unitMeta(type, category).label;

    // Statt einer Fehlermeldung bei zu hoher Menge: auf die maximal bezahlbare Anzahl klemmen.
    const option = this.findOption(type, category);
    if (option) {
      const affordable = this.maxAffordable(option.cost);
      if (affordable <= 0) {
        this.notify.warning('Zu wenig Ressourcen', `Die Rohstoffe reichen nicht fuer ein ${label}.`);
        return;
      }
      if (count > affordable) {
        count = affordable;
        this.setCount(type, count); // angepasste Menge im Eingabefeld spiegeln
        this.notify.info(
          'Menge angepasst',
          `Rohstoffe reichen fuer ${count}× ${label} — so viele werden gebaut.`,
        );
      }
    }

    this.pending.set(type);
    this.api.buildShips(planetId, { type, count, category }).subscribe({
      next: (res) => {
        this.pending.set(null);
        this.data.update((d) => (d ? { ...d, queue: res.queue } : d));
        this.notify.info('In Bau', `${count}× ${label} eingereiht.`);
        void this.state.reloadActivePlanet();
      },
      error: (err) => {
        this.pending.set(null);
        this.notify.warning('Bau nicht moeglich', err?.error?.detail ?? 'Fehler.');
      },
    });
  }

  /** Bricht einen Werft-Auftrag ab (Refund + Schlange rueckt nach). */
  /** Fragt vor dem Abbruch eines Werft-Auftrags nach (Ressourcen werden erstattet). */
  askCancelQueue(itemId: string, type: string, category: ShipyardCategory, count: number): void {
    this.confirmReq.set({
      title: 'Auftrag abbrechen?',
      message: `${count}× ${this.unitMeta(type, category).label}: Der Bauauftrag wird abgebrochen, die Ressourcen werden zurückerstattet.`,
      confirmLabel: '✕ Auftrag abbrechen',
      action: () => this.cancelQueue(itemId),
    });
  }

  /** Fuehrt die bestaetigte Aktion aus und schliesst den Dialog. */
  runConfirm(): void {
    const c = this.confirmReq();
    this.confirmReq.set(null);
    c?.action();
  }

  cancelQueue(itemId: string): void {
    const planetId = this.state.activePlanetId();
    if (!planetId) {
      return;
    }
    this.cancelling.set(itemId);
    this.api.cancelShipyardItem(planetId, itemId).subscribe({
      next: (res) => {
        this.cancelling.set(null);
        this.data.update((d) => (d ? { ...d, queue: res.queue } : d));
        this.notify.info('Abgebrochen', 'Auftrag abgebrochen — Ressourcen zurueckerstattet.');
        void this.state.reloadActivePlanet();
      },
      error: (err) => {
        this.cancelling.set(null);
        this.notify.warning('Abbruch fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
      },
    });
  }

  unitMeta(type: string, category: ShipyardCategory) {
    return metaFor(category === 'defense' ? DEFENSE_META : SHIP_META, type);
  }

  /** Asset-Pfad fuer eine Bauschleifen-Einheit (Schiff oder Verteidigung). */
  unitIcon(type: string, category: ShipyardCategory): string {
    return category === 'defense' ? defenseIcon(type) : shipIcon(type);
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
