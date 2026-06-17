import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { PlanetUnit, Requirement, ShipOption, ShipyardResponse } from '../../core/models/api.models';
import { BUILDING_META, DEFENSE_META, RANGE_META, TECH_META, WEAPON_META, metaFor } from '../../core/models/display';
import { defenseIcon, navIcon, rangeIcon, resourceIcon, statIcon, weaponIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { DetailPopupComponent, DetailTag } from '../../shared/components/detail-popup.component';
import { BuildTileComponent } from '../../shared/components/build-tile.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { ConfirmDialogComponent, ConfirmRequest } from '../../shared/components/confirm-dialog.component';
import { NotificationService } from '../../core/services/notification.service';
import { scrollToTile } from '../../shared/focus-scroll';

/**
 * Verteidigungs-Screen — aus der Werft herausgeloest (2026-06-17). Baut planetare Verteidigung
 * in der Verteidigungsfabrik (eigene, zur Werft parallele Bauschlange). Nutzt denselben
 * Werft-Endpunkt; zeigt aber NUR die Verteidigungs-Optionen + die Verteidigungs-Queue.
 */
@Component({
  selector: 'app-defense',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, CountdownComponent, DetailPopupComponent, BuildTileComponent, IconTileComponent, ConfirmDialogComponent, BtnIconComponent],
  template: `
    <h1>Verteidigung</h1>
    <p class="muted sub">Baue planetare Verteidigung auf {{ state.activePlanet()?.name ?? '—' }}. Raumschiffe entstehen in der <a routerLink="/shipyard">Werft</a>.</p>

    @if (loading()) {
      <p class="empty-state">Lade Verteidigung…</p>
    } @else if (data(); as d) {
      @if (!hasFactory()) {
        <section class="card factory-hint">
          <app-btn-icon [src]="buildingIcon" glyph="🛡️" [size]="20" />
          <span>Du brauchst eine <strong>Verteidigungsfabrik</strong>, um planetare Verteidigung zu bauen. Errichte sie im <a routerLink="/buildings">Gebäude-Menü</a>.</span>
        </section>
      }

      <!-- Bauschleife (nur Verteidigung; Schiffe haben eine eigene, parallele Schlange) -->
      <section class="card queue">
        <div class="panel-title"><app-btn-icon [src]="navIcon('defense')" glyph="🛡️" [size]="16" /> Bauschleife</div>
        @if (queueView().length) {
          @for (q of queueView(); track q.id; let first = $first) {
            <div class="queue-row" [class.building]="first" [class.waiting]="!first">
              <span class="q-unit">
                <app-icon-tile class="q-ico" [glyph]="unitMeta(q.type).glyph" [src]="defenseIcon(q.type)" [size]="22" variant="muted" />{{ q.count }}× {{ unitMeta(q.type).label }}
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
                  <span class="q-eta muted tip" data-tip="Startet erst, wenn die vorherigen Aufträge fertig sind (serielle Verteidigungsfabrik). Eine Bauzeit läuft hier noch nicht.">in Warteschlange</span>
                }
                <button
                  class="btn btn-ghost btn-sm q-cancel"
                  type="button"
                  [disabled]="cancelling() === q.id"
                  (click)="askCancelQueue(q.id, q.type, q.count)"
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

      <div class="tile-grid">
        @for (s of d.defenses; track s.type) {
          <app-build-tile
            [attr.id]="'tile-' + s.type"
            [iconSrc]="defenseIcon(s.type)"
            [glyph]="unitMeta(s.type).glyph"
            [name]="unitMeta(s.type).label"
            [badge]="ownedCount(s.type)"
            [focused]="focusType() === s.type"
            badgeTip="Bestand"
            [cost]="s.cost"
            [available]="balances()"
            [timeSeconds]="s.build_seconds_each"
            variant="magenta"
            [locked]="!s.requirements_met"
            (openDetail)="openDetail(s)"
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
                  (click)="build(s.type)"
                >
                  {{ pending() === s.type ? '…' : 'Bauen' }}
                </button>
              </div>
              <span class="stock-line">Auf diesem Planeten: <strong>{{ ownedCount(s.type) }}</strong>@if (s.max_per_planet) { <span class="stock-max">(max. {{ s.max_per_planet }})</span>}</span>
              @if (!s.requirements_met) {
                <span class="hint warn small">{{ missingReqText(s) }}</span>
              } @else if (atPlanetCap(s)) {
                <span class="hint warn small">Maximal {{ s.max_per_planet }} pro Planet — bereits vorhanden/in Bau.</span>
              } @else if (!s.can_build) {
                <span class="hint warn small">Zu wenig Ressourcen</span>
              }
            </ng-container>
          </app-build-tile>
        }
      </div>
    } @else {
      <p class="empty-state">Keine Verteidigungsdaten für diesen Planeten.</p>
    }

    @if (selected(); as sel) {
      <app-detail-popup
        kind="defense"
        [type]="sel.type"
        [cost]="sel.cost"
        [available]="balances()"
        [buildSeconds]="sel.build_seconds_each"
        [requirements]="sel.requirements ?? null"
        [tags]="unitTags(sel)"
        [quantity]="true"
        [actionLabel]="'Bauen'"
        [actionDisabled]="!buildable(sel)"
        [actionHint]="!sel.requirements_met ? missingReqText(sel) : (!sel.can_build ? 'Zu wenig Ressourcen' : null)"
        [pending]="pending() === sel.type"
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
      .sub { margin-top: calc(-1 * var(--sp-1)); font-size: var(--fs-sm); }

      /* Hinweis, wenn noch keine Verteidigungsfabrik steht. */
      .factory-hint {
        display: flex; align-items: center; gap: var(--sp-3);
        margin-bottom: var(--sp-4); font-size: var(--fs-sm); color: var(--text-dim);
      }

      .queue { margin-bottom: var(--sp-4); }
      .queue-row {
        display: flex; align-items: center; justify-content: space-between;
        gap: var(--sp-3);
        padding: var(--sp-2) 0 var(--sp-2) var(--sp-3); font-size: var(--fs-sm);
        border-bottom: 1px solid var(--border);
      }
      .queue-row:last-child { border-bottom: none; }
      .queue-row.building { position: relative; }
      .queue-row.building::before {
        content: ''; position: absolute; left: 0; top: 18%; bottom: 18%; width: 3px;
        border-radius: var(--r-pill); background: var(--magenta, var(--accent)); box-shadow: var(--glow-soft);
        animation: qBuild 1.6s ease-in-out infinite;
      }
      @keyframes qBuild { 0%, 100% { opacity: 0.35; } 50% { opacity: 1; } }
      @media (prefers-reduced-motion: reduce) { .queue-row.building::before { animation: none; opacity: 0.7; } }
      .q-unit { display: inline-flex; align-items: center; gap: var(--sp-2); }
      .q-ico { flex: 0 0 auto; }
      .q-status {
        flex: 0 0 auto; font-size: var(--fs-xs); font-weight: 600;
        padding: 1px var(--sp-2); border-radius: var(--r-pill); white-space: nowrap;
      }
      .q-status.active { color: #04201d; background: var(--accent); }
      .q-status.wait { color: var(--text-dim); background: rgba(255,255,255,0.06); border: 1px solid var(--border-strong); }
      .queue-row.waiting { opacity: 0.7; }
      .q-eta { display: inline-flex; align-items: center; gap: 4px; font-size: var(--fs-xs); cursor: help; }

      .small { font-size: var(--fs-xs); }
      .qty-row { display: flex; gap: var(--sp-2); align-items: center; }
      .qty-row input { width: 56px; flex: 0 0 auto; text-align: center; }
      .qty-row .btn { flex: 0 0 auto; white-space: nowrap; }
      .hint { color: var(--text-faint); text-align: right; }
      .hint.warn { color: var(--warn); }

      /* Klar sichtbarer Bestand auf dem aktiven Planeten (nicht nur der Eck-Badge). */
      .stock-line { display: block; font-size: var(--fs-xs); color: var(--text-dim); margin-top: var(--sp-1); }
      .stock-line strong { color: var(--accent); font-variant-numeric: tabular-nums; }
      .stock-max { color: var(--text-faint); }
      .q-right { display: flex; align-items: center; gap: var(--sp-2); flex: 0 0 auto; }
      .q-cancel { color: var(--text-faint); min-width: 30px; }
      .q-cancel:hover:not(:disabled) { color: var(--danger); border-color: var(--danger-dim); }
    `,
  ],
})
export class DefenseComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);

  protected readonly focusType = signal<string | null>(null);
  private focusHandled = false;

  /** Asset-Pfad-Helfer fuers Template. */
  protected readonly navIcon = navIcon;
  protected readonly resourceIcon = resourceIcon;
  protected readonly defenseIcon = defenseIcon;
  protected readonly buildingIcon = 'assets/img/buildings/defense_factory.png';

  protected readonly data = signal<ShipyardResponse | null>(null);
  protected readonly loading = signal(true);
  protected readonly pending = signal<string | null>(null);
  protected readonly cancelling = signal<string | null>(null);
  protected readonly counts = signal<Record<string, number>>({});
  protected readonly selected = signal<ShipOption | null>(null);
  protected readonly confirmReq = signal<ConfirmRequest | null>(null);

  protected readonly balances = computed(() => {
    const res = this.state.activePlanet()?.resources;
    return res
      ? { metal: res.metal.amount, crystal: res.crystal.amount, deuterium: res.deuterium.amount }
      : null;
  });

  /** Bauschleife der Verteidigungsfabrik: nur Verteidigungs-Auftraege. */
  protected readonly queueView = computed(() => (this.data()?.queue ?? []).filter((q) => q.category === 'defense'));

  /** Steht eine Verteidigungsfabrik (Stufe >= 1)? Leitet sich aus can_build der Optionen ab:
   * rocket_launcher hat als einzige Voraussetzung defense_factory>=1, also ist requirements_met
   * dort gleichbedeutend mit "Fabrik vorhanden". Fallback: irgendeine baubare Verteidigung. */
  protected readonly hasFactory = computed(() => {
    const defenses = this.data()?.defenses ?? [];
    const rl = defenses.find((d) => d.type === 'rocket_launcher');
    if (rl) {
      return rl.requirements_met;
    }
    return defenses.some((d) => d.requirements_met);
  });

  ownedCount(type: string): number {
    const list: PlanetUnit[] = this.state.activePlanet()?.defenses ?? [];
    return list.find((u) => u.type === type)?.count ?? 0;
  }

  constructor() {
    const focus = this.route.snapshot.queryParamMap.get('focus');
    if (focus) {
      this.focusType.set(focus);
    }
    effect(() => {
      const id = this.state.activePlanetId();
      this.state.shipyardVersion(); // bei Fertigstellung automatisch neu laden (gemeinsames Signal)
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

  private applyFocus(): void {
    const ft = this.focusType();
    if (this.focusHandled || !ft) {
      return;
    }
    this.focusHandled = true;
    scrollToTile(ft);
    setTimeout(() => this.focusType.set(null), 4500);
  }

  buildable(s: ShipOption): boolean {
    return s.can_build && s.requirements_met;
  }

  /** Ist das Pro-Planet-Limit (z. B. Schildkuppel 1) auf diesem Planeten erreicht? */
  atPlanetCap(s: ShipOption): boolean {
    return s.max_per_planet != null && (s.planet_owned ?? 0) >= s.max_per_planet;
  }

  openDetail(option: ShipOption): void {
    this.selected.set(option);
  }

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
      tags.push({ glyph: '🛡', label: 'Schild/Defensiv', icon: statIcon('shield') });
    }
    return tags;
  }

  buildFromPopup(count: number): void {
    const sel = this.selected();
    if (!sel) {
      return;
    }
    this.setCount(sel.type, count);
    this.build(sel.type);
    this.selected.set(null);
  }

  unitCount(type: string): number {
    return this.counts()[type] ?? 1;
  }

  setCount(type: string, value: number): void {
    this.counts.update((c) => ({ ...c, [type]: Math.max(1, Math.floor(value || 1)) }));
  }

  private findOption(type: string): ShipOption | undefined {
    return this.data()?.defenses?.find((o) => o.type === type);
  }

  private maxAffordable(cost: { metal?: number; crystal?: number; deuterium?: number }): number {
    const bal = this.balances();
    if (!bal) {
      return Infinity;
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

  build(type: string): void {
    const planetId = this.state.activePlanetId();
    if (!planetId) {
      return;
    }
    let count = this.counts()[type] ?? 1;
    const label = this.unitMeta(type).label;

    const option = this.findOption(type);
    if (option) {
      const affordable = this.maxAffordable(option.cost);
      if (affordable <= 0) {
        this.notify.warning('Zu wenig Ressourcen', `Die Rohstoffe reichen nicht fuer ein ${label}.`);
        return;
      }
      if (count > affordable) {
        count = affordable;
        this.setCount(type, count);
        this.notify.info('Menge angepasst', `Rohstoffe reichen fuer ${count}× ${label} — so viele werden gebaut.`);
      }
    }

    this.pending.set(type);
    this.api.buildShips(planetId, { type, count, category: 'defense' }).subscribe({
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

  askCancelQueue(itemId: string, type: string, count: number): void {
    this.confirmReq.set({
      title: 'Auftrag abbrechen?',
      message: `${count}× ${this.unitMeta(type).label}: Der Bauauftrag wird abgebrochen, die Ressourcen werden zurückerstattet.`,
      confirmLabel: '✕ Auftrag abbrechen',
      action: () => this.cancelQueue(itemId),
    });
  }

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

  unitMeta(type: string) {
    return metaFor(DEFENSE_META, type);
  }

  protected weaponMeta(t?: string | null) { return t ? (WEAPON_META[t] ?? { label: t, glyph: '•', vs: '' }) : { label: 'Unbewaffnet', glyph: '🛡', vs: '' }; }
  protected rangeMeta(r?: string | null) { return RANGE_META[r ?? ''] ?? { label: r ?? '', dot: '•' }; }

  reqLabel(r: Requirement): string {
    return metaFor({ ...BUILDING_META, ...TECH_META }, r.type).label + ' ' + r.level;
  }

  missingReqText(option: ShipOption): string {
    const labels = (option.requirements ?? [])
      .filter((r) => !r.met)
      .map((r) => this.reqLabel(r));
    return labels.length ? 'benötigt: ' + labels.join(', ') : 'Voraussetzung fehlt';
  }
}
