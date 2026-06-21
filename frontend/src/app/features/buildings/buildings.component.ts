import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { BuildingOption, BuildingState, BuildingsResponse } from '../../core/models/api.models';
import { BUILDING_META, metaFor } from '../../core/models/display';
import { missionIcon, navIcon, resourceIcon, statIcon, uiIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { DetailPopupComponent } from '../../shared/components/detail-popup.component';
import { BuildTileComponent } from '../../shared/components/build-tile.component';
import { TabBarComponent } from '../../shared/components/tab-bar.component';
import {
  ConfirmDialogComponent,
  ConfirmRequest,
} from '../../shared/components/confirm-dialog.component';
import { NotificationService } from '../../core/services/notification.service';
import { ActivatedRoute } from '@angular/router';
import { scrollToTile } from '../../shared/focus-scroll';

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
  icon: string | null;
  rows: BuildingRow[];
}

/** Kategorien gemaess Wunsch: Rohstoffe, Energie, Anlagen, Lager, Kommando. */
const CATEGORY_ORDER: { key: string; label: string; glyph: string; icon: string | null; types: string[] }[] = [
  { key: 'resource', label: 'Rohstoff-Gebaeude', glyph: '⛏️', icon: missionIcon('mine'), types: ['metal_mine', 'crystal_mine', 'deuterium_synth'] },
  { key: 'energy', label: 'Energie', glyph: '⚡', icon: resourceIcon('energy'), types: ['solar_plant', 'fusion_reactor'] },
  { key: 'facility', label: 'Anlagen', glyph: '🏭', icon: navIcon('buildings'), types: ['robot_factory', 'shipyard', 'defense_factory', 'research_lab', 'nanite_factory'] },
  { key: 'storage', label: 'Lager', glyph: '📦', icon: statIcon('cargo'), types: ['metal_storage', 'crystal_storage', 'deuterium_tank'] },
  { key: 'command', label: 'Kommando', glyph: '🎖️', icon: navIcon('command'), types: ['command_academy', 'command_center'] },
  { key: 'exotic', label: 'Exotisch', glyph: '🌌', icon: navIcon('megastructures'), types: ['antimatter_collector', 'dark_matter_condenser'] },
];

@Component({
  selector: 'app-buildings',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CountdownComponent, DetailPopupComponent, BuildTileComponent, TabBarComponent, ConfirmDialogComponent, BtnIconComponent],
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
      <app-tab-bar [tabs]="tabDefs()" [active]="activeTab()" (select)="activeTab.set($event)" />
      @if (activeGroup(); as group) {
        <div class="tile-grid">
          @for (b of group.rows; track b.type) {
            <app-build-tile
              [attr.id]="'tile-' + b.type"
              [iconSrc]="'assets/img/buildings/' + b.type + '.png'"
              [glyph]="meta(b.type).glyph"
              [name]="meta(b.type).label"
              [badge]="b.level"
              badgeTip="Stufe"
              [cost]="b.option?.cost ?? null"
              [available]="balances()"
              [timeSeconds]="b.option?.build_seconds ?? null"
              [busy]="!!b.finishesAt"
              [focused]="focusType() === b.type"
              (openDetail)="openDetail(b)"
            >
              @if (b.option && (b.option.energy_now !== 0 || b.option.energy_delta !== 0)) {
                <span stats class="energy small"
                  [class.produces]="b.option.energy_now > 0"
                  [class.consumes]="b.option.energy_now < 0"
                  [attr.data-tip]="energyTip(b.option)">
                  <app-btn-icon [src]="resourceIcon('energy')" glyph="⚡" [size]="14" /> {{ energyLabel(b.option.energy_now) }}@if (b.option.energy_delta !== 0) {<span class="delta"> (Δ {{ signed(b.option.energy_delta) }})</span>}
                </span>
              }

              <ng-container action>
                @if (b.finishesAt) {
                  <span class="building-badge"><app-btn-icon [src]="uiIcon('time')" glyph="⏳" [size]="14" /> Im Bau</span>
                  <app-countdown [target]="b.finishesAt" />
                  <button
                    class="btn btn-ghost btn-sm full cancel-build"
                    type="button"
                    [disabled]="pending() === b.type"
                    (click)="askCancelBuild(b.type)"
                  >
                    {{ pending() === b.type ? '…' : '✕ Abbrechen' }}
                  </button>
                } @else {
                  @if (b.option) {
                    @if (b.option.maxed) {
                      <span class="hint small">Stufe {{ b.option.max_level }} — kein Ausbau (Boni über Forschung Handelsnetz)</span>
                    } @else {
                      <button
                        class="btn btn-primary btn-sm full"
                        type="button"
                        [disabled]="!canUpgrade(b) || pending() === b.type || anyBuilding()"
                        (click)="upgrade(b.type)"
                      >
                        {{ pending() === b.type ? '…' : 'Ausbauen → ' + b.option.next_level }}
                      </button>
                      @if (b.option.account_blocked) {
                        <span class="hint warn small">Nur eines pro Imperium</span>
                      } @else if (b.option.position_ok === false) {
                        <span class="hint warn small">Nur auf Position {{ (b.option.allowed_positions ?? []).join(', ') }}</span>
                      } @else if (!b.option.requirements_met) {
                        <span class="hint warn small">Voraussetzung fehlt</span>
                      } @else if (!b.option.can_afford) {
                        <span class="hint warn small">Zu teuer</span>
                      } @else if (anyBuilding()) {
                        <span class="hint small">Bauschleife belegt</span>
                      }
                    }
                  }
                  @if (b.level > 0) {
                    <button
                      class="btn btn-ghost btn-sm demolish full"
                      type="button"
                      [disabled]="pending() === b.type || anyBuilding()"
                      (click)="askDemolish(b.type, b.level)"
                    >
                      Abreissen → {{ b.level - 1 }}
                    </button>
                  }
                }
              </ng-container>
            </app-build-tile>
          }
        </div>
      }
    }

    @if (selected(); as sel) {
      <app-detail-popup
        kind="building"
        [type]="sel.type"
        [level]="sel.level"
        [cost]="sel.option?.cost ?? null"
        [available]="balances()"
        [buildSeconds]="sel.option?.build_seconds ?? null"
        [requirements]="sel.option?.requirements ?? null"
        [actionLabel]="sel.option && !sel.finishesAt && !sel.option.maxed ? ('Ausbauen → ' + sel.option.next_level) : null"
        [actionDisabled]="!canUpgrade(sel) || anyBuilding()"
        [actionHint]="buildingHint(sel)"
        [pending]="pending() === sel.type"
        (confirm)="upgradeFromPopup()"
        (close)="selected.set(null)"
      />
    }

    @if (confirmReq(); as c) {
      <app-confirm-dialog
        [title]="c.title"
        [message]="c.message"
        [confirmLabel]="c.confirmLabel"
        [pending]="pending() !== null"
        (confirm)="runConfirm()"
        (dismiss)="confirmReq.set(null)"
      />
    }
  `,
  styles: [
    `
      /* Unterzeile unter dem Titel (Bau-Hinweis + Feld-Budget). */
      .sub { margin-top: calc(-1 * var(--sp-1)); font-size: var(--fs-sm); }

      /* Feld-Budget-Anzeige: Zahlenwerte tabellarisch, faerbt bei Vollauslastung. */
      .fields { color: var(--text-dim); font-family: var(--mono); font-variant-numeric: tabular-nums; }
      .fields.full { color: var(--warn); font-weight: 600; }

      /* Projizierte Energie-Bilanz als Chip in der Kachel. */
      .energy {
        display: inline-flex; align-items: center; gap: var(--sp-1);
        color: var(--text-dim); font-variant-numeric: tabular-nums;
      }
      .energy.produces { color: var(--ok); }
      .energy.consumes { color: var(--warn); }
      .energy .delta { color: var(--text-faint); }

      .small { font-size: var(--fs-xs); }

      /* "Im Bau"-Marke ueber dem Countdown. */
      .building-badge {
        font-family: var(--font-display);
        font-size: var(--fs-xs); color: var(--accent);
        text-transform: uppercase; letter-spacing: 0.12em;
      }

      /* Hinweistexte unter der Aktion. */
      .hint { color: var(--text-faint); }
      .hint.warn { color: var(--warn); }

      /* Abreissen: dezent, wird erst beim Hover zur Warnung. */
      .demolish { color: var(--text-dim); }
      .demolish:hover:not(:disabled) { color: var(--warn); }
    `,
  ],
})
export class BuildingsComponent {
  private readonly api = inject(ApiService);
  private readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);

  /** Per Deeplink angesprungenes Gebaeude (Query-Param ?focus=) — Tab + Highlight + Scroll. */
  protected readonly focusType = signal<string | null>(null);
  private focusHandled = false;

  private readonly data = signal<BuildingsResponse | null>(null);
  protected readonly loading = signal(true);
  protected readonly pending = signal<string | null>(null);
  protected readonly selected = signal<BuildingRow | null>(null);
  /** Ausstehende Sicherheitsabfrage (Abbrechen/Abreissen) — null = kein Dialog offen. */
  protected readonly confirmReq = signal<ConfirmRequest | null>(null);

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
        groups.push({ key: cat.key, label: cat.label, glyph: cat.glyph, icon: cat.icon, rows });
      }
    }
    // Etwaige unkategorisierte Gebaeude (z. B. neue Typen) als "Sonstiges".
    const rest = this.rows().filter((r) => !used.has(r.type));
    if (rest.length) {
      groups.push({ key: 'other', label: 'Sonstiges', glyph: '🏗️', icon: null, rows: rest });
    }
    return groups;
  });

  // -- Reiter (Kategorie-Tabs) --
  protected readonly activeTab = signal<string>('resource');
  protected readonly tabDefs = computed(() =>
    this.groups().map((g) => ({ key: g.key, label: g.label, glyph: g.glyph, icon: g.icon, count: g.rows.length })),
  );
  protected readonly activeGroup = computed(() => {
    const gs = this.groups();
    return gs.find((g) => g.key === this.activeTab()) ?? gs[0] ?? null;
  });

  protected readonly anyBuilding = computed(() => this.rows().some((r) => r.finishesAt));

  /** Feld-Budget des aktiven Planeten (Modell A: 1 Feld pro Gebaeudestufe). */
  protected readonly fields = computed(() => {
    const p = this.state.activePlanet();
    return p ? { used: p.fields_used, max: p.fields_max } : null;
  });

  protected readonly balances = computed(() => {
    const res = this.state.activePlanet()?.resources;
    if (!res) {
      return null;
    }
    const exo = res.exotic ?? {};
    return {
      metal: res.metal.amount,
      crystal: res.crystal.amount,
      deuterium: res.deuterium.amount,
      antimatter: exo['antimatter']?.amount ?? 0,
      dark_matter: exo['dark_matter']?.amount ?? 0,
    };
  });

  constructor() {
    const focus = this.route.snapshot.queryParamMap.get('focus');
    if (focus) {
      this.focusType.set(focus);
    }
    effect(() => {
      const id = this.state.activePlanetId();
      this.state.buildingsVersion(); // bei Bau-Fertigstellung automatisch neu laden
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
        this.applyFocus();
      },
      error: () => this.loading.set(false),
    });
  }

  /** Deeplink vom Dashboard: zum laufenden Ausbau springen (Tab + Scroll + Flash), einmalig. */
  private applyFocus(): void {
    const ft = this.focusType();
    if (this.focusHandled || !ft) {
      return;
    }
    this.focusHandled = true;
    const grp = this.groups().find((g) => g.rows.some((r) => r.type === ft));
    if (grp) {
      this.activeTab.set(grp.key);
    }
    scrollToTile(ft);
    setTimeout(() => this.focusType.set(null), 4500);
  }

  canUpgrade(b: BuildingRow): boolean {
    return (
      !!b.option &&
      b.option.can_afford &&
      b.option.requirements_met &&
      b.option.position_ok !== false &&
      !b.option.account_blocked &&
      !b.option.maxed &&
      !b.finishesAt
    );
  }

  openDetail(row: BuildingRow): void {
    this.selected.set(row);
  }

  upgradeFromPopup(): void {
    const sel = this.selected();
    if (sel) {
      this.upgrade(sel.type);
      this.selected.set(null);
    }
  }

  /** Aktions-Hinweis fuer das Detail-Popup. */
  buildingHint(b: BuildingRow): string | null {
    if (!b.option || b.finishesAt) {
      return null;
    }
    if (b.option.maxed) {
      return `Stufe ${b.option.max_level} — kein Ausbau (Boni über Forschung Handelsnetz)`;
    }
    if (b.option.account_blocked) {
      return 'Nur eines pro Imperium';
    }
    if (!b.option.requirements_met) {
      return 'Voraussetzung fehlt';
    }
    if (!b.option.can_afford) {
      return 'Zu teuer';
    }
    if (this.anyBuilding()) {
      return 'Bauschleife belegt';
    }
    return null;
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

  /** Fragt vor dem Bau-Abbruch nach (Ressourcen werden erstattet). */
  askCancelBuild(type: string): void {
    this.confirmReq.set({
      title: 'Bau abbrechen?',
      message: `${this.meta(type).label}: Der laufende Ausbau wird abgebrochen, die Ressourcen werden zurückerstattet.`,
      confirmLabel: '✕ Bau abbrechen',
      action: () => this.cancelBuild(type),
    });
  }

  /** Fragt vor dem Abreissen nach (Stufe sinkt, Feld wird frei). */
  askDemolish(type: string, level: number): void {
    this.confirmReq.set({
      title: 'Gebäude abreißen?',
      message: `${this.meta(type).label} wird von Stufe ${level} auf ${level - 1} abgerissen. Das gibt ein Feld frei, erstattet aber nur einen Teil der Kosten.`,
      confirmLabel: 'Abreißen',
      action: () => this.demolish(type),
    });
  }

  /** Fuehrt die bestaetigte Aktion aus und schliesst den Dialog. */
  runConfirm(): void {
    const c = this.confirmReq();
    this.confirmReq.set(null);
    c?.action();
  }

  cancelBuild(type: string): void {
    const planetId = this.state.activePlanetId();
    if (!planetId) {
      return;
    }
    this.pending.set(type);
    this.api.cancelBuilding(planetId, type).subscribe({
      next: () => {
        this.pending.set(null);
        this.notify.info('Bau abgebrochen', `${this.meta(type).label}: Ressourcen zurueckerstattet.`);
        this.load(planetId);
        void this.state.reloadActivePlanet();
      },
      error: (err) => {
        this.pending.set(null);
        this.notify.warning('Abbruch fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
        // Stale "fertig"-Zustand aufraeumen, falls ein WS-Event verpasst wurde.
        this.load(planetId);
        void this.state.reloadActivePlanet();
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
  protected readonly resourceIcon = resourceIcon;
  protected readonly uiIcon = uiIcon;

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
