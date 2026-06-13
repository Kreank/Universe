import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { Requirement, ResearchOption, ResearchResponse, ResearchState } from '../../core/models/api.models';
import { BUILDING_META, TECH_META, metaFor } from '../../core/models/display';
import { techIcon } from '../../core/models/icon-assets';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { DetailPopupComponent } from '../../shared/components/detail-popup.component';
import { BuildTileComponent } from '../../shared/components/build-tile.component';
import { TabBarComponent } from '../../shared/components/tab-bar.component';
import {
  ConfirmDialogComponent,
  ConfirmRequest,
} from '../../shared/components/confirm-dialog.component';
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
    label: 'Antrieb & Reichweite',
    glyph: '🚀',
    types: [
      'energy_tech',
      'combustion_drive',
      'impulse_drive',
      'hyperspace_drive',
      'hyperspace_tech',
      'hyperspace_interdiction',
    ],
  },
  {
    key: 'combat',
    label: 'Kampftechnik',
    glyph: '⚔️',
    types: [
      'weapons_tech',
      'shield_tech',
      'armor_tech',
      'laser_tech',
      'ion_tech',
      'ion_disruptors',
      'plasma_tech',
      'boarding_doctrine',
      'graviton_tech',
    ],
  },
  {
    key: 'command',
    label: 'Führung & Crew',
    glyph: '🎖️',
    types: [
      'command_doctrine',
      'logistics_tech',
      'crew_psychology',
      'leadership_doctrine',
      'tactical_academy',
      'computer_tech',
      'spy_tech',
    ],
  },
  {
    key: 'economy',
    label: 'Wirtschaft & Expansion',
    glyph: '⛏️',
    types: ['mining_efficiency', 'storage_tech', 'astrophysics', 'expedition_tech'],
  },
];

@Component({
  selector: 'app-research',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CountdownComponent, DetailPopupComponent, BuildTileComponent, TabBarComponent, ConfirmDialogComponent],
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
        <button
          class="btn btn-ghost btn-sm cancel-research"
          type="button"
          [disabled]="cancelling()"
          (click)="askCancelResearch()"
        >
          {{ cancelling() ? '…' : '✕ Abbrechen' }}
        </button>
      </div>
    }

    @if (loading()) {
      <p class="empty-state">Lade Techbaum…</p>
    } @else {
      <app-tab-bar [tabs]="tabDefs()" [active]="activeTab()" (select)="activeTab.set($event)" />
      @if (activeGroup(); as group) {
        <div class="tile-grid">
          @for (t of group.rows; track t.type) {
            <app-build-tile
              [iconSrc]="techIcon(t.type)"
              [glyph]="meta(t.type).glyph"
              [name]="meta(t.type).label"
              [badge]="t.level"
              badgeTip="Stufe"
              variant="muted"
              [cost]="t.option?.cost ?? null"
              [available]="balances()"
              [timeSeconds]="t.option?.research_seconds ?? null"
              [busy]="!!t.finishesAt"
              (openDetail)="openDetail(t)"
            >
              <ng-container action>
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
                    <span class="hint warn small">{{ missingReqText(t.option) }}</span>
                  } @else if (!t.option.can_afford) {
                    <span class="hint warn small">Zu teuer</span>
                  } @else if (researchBusy()) {
                    <span class="hint small">Labor belegt</span>
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
        kind="tech"
        [type]="sel.type"
        [level]="sel.level"
        [cost]="sel.option?.cost ?? null"
        [available]="balances()"
        [buildSeconds]="sel.option?.research_seconds ?? null"
        [requirements]="sel.option?.requirements ?? null"
        [actionLabel]="sel.option && !sel.finishesAt ? ('Erforschen → ' + sel.option.next_level) : null"
        [actionDisabled]="!canStart(sel)"
        [actionHint]="researchHint(sel)"
        [pending]="pending() === sel.type"
        (confirm)="startFromPopup()"
        (close)="selected.set(null)"
      />
    }

    @if (confirmReq(); as c) {
      <app-confirm-dialog
        [title]="c.title"
        [message]="c.message"
        [confirmLabel]="c.confirmLabel"
        [pending]="cancelling()"
        (confirm)="runConfirm()"
        (dismiss)="confirmReq.set(null)"
      />
    }
  `,
  styles: [
    `
      .sub { margin-top: calc(-1 * var(--sp-1)); font-size: var(--fs-sm); }

      /* Aktive Forschung — ruhiger Fokus-Banner (Glow dezent). */
      .active-banner {
        display: flex; align-items: center; justify-content: space-between;
        gap: var(--sp-4); margin-bottom: var(--sp-4);
        border-color: color-mix(in srgb, var(--accent) 36%, transparent);
        box-shadow: var(--e1), var(--glow-soft);
      }
      .active-banner span { font-family: var(--font-display); font-size: var(--fs-base); }

      .building-badge {
        font-family: var(--font-display);
        font-size: var(--fs-xs); color: var(--accent);
        text-transform: uppercase; letter-spacing: 0.08em;
      }
      .small { font-size: var(--fs-xs); }
      .hint { color: var(--text-faint); text-align: right; }
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
  protected readonly cancelling = signal(false);
  protected readonly selected = signal<ResearchRow | null>(null);
  /** Ausstehende Sicherheitsabfrage (Forschung abbrechen) — null = kein Dialog offen. */
  protected readonly confirmReq = signal<ConfirmRequest | null>(null);

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

  // -- Reiter (Kategorie-Tabs) --
  protected readonly activeTab = signal<string>('drive');
  protected readonly tabDefs = computed(() =>
    this.groups().map((g) => ({ key: g.key, label: g.label, glyph: g.glyph, count: g.rows.length })),
  );
  protected readonly activeGroup = computed(() => {
    const gs = this.groups();
    return gs.find((g) => g.key === this.activeTab()) ?? gs[0] ?? null;
  });

  protected readonly balances = computed(() => {
    const res = this.state.activePlanet()?.resources;
    return res
      ? { metal: res.metal.amount, crystal: res.crystal.amount, deuterium: res.deuterium.amount }
      : null;
  });

  constructor() {
    effect(() => {
      this.state.researchVersion(); // bei Forschungs-Fertigstellung automatisch neu laden
      this.load();
    });
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
      !!t.option && t.option.can_afford && t.option.requirements_met && !this.researchBusy() && !t.finishesAt
    );
  }

  openDetail(row: ResearchRow): void {
    this.selected.set(row);
  }

  startFromPopup(): void {
    const sel = this.selected();
    if (sel) {
      this.start(sel.type);
      this.selected.set(null);
    }
  }

  /** Aktions-Hinweis fuer das Detail-Popup (Voraussetzung/Kosten/Labor belegt). */
  researchHint(t: ResearchRow): string | null {
    if (!t.option || t.finishesAt) {
      return null;
    }
    if (!t.option.requirements_met) {
      return this.missingReqText(t.option);
    }
    if (!t.option.can_afford) {
      return 'Zu teuer';
    }
    if (this.researchBusy()) {
      return 'Labor belegt';
    }
    return null;
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

  /** Fragt vor dem Forschungs-Abbruch nach (Ressourcen werden erstattet). */
  askCancelResearch(): void {
    const ar = this.activeResearch();
    const label = ar ? this.meta(ar.type).label : 'Die laufende Forschung';
    this.confirmReq.set({
      title: 'Forschung abbrechen?',
      message: `${label} wird abgebrochen, die Ressourcen werden zurückerstattet.`,
      confirmLabel: '✕ Forschung abbrechen',
      action: () => this.cancelResearch(),
    });
  }

  /** Fuehrt die bestaetigte Aktion aus und schliesst den Dialog. */
  runConfirm(): void {
    const c = this.confirmReq();
    this.confirmReq.set(null);
    c?.action();
  }

  cancelResearch(): void {
    this.cancelling.set(true);
    this.api.cancelResearch().subscribe({
      next: () => {
        this.cancelling.set(false);
        this.notify.info('Forschung abgebrochen', 'Ressourcen zurueckerstattet.');
        this.load();
        void this.state.reloadActivePlanet();
      },
      error: (err) => {
        this.cancelling.set(false);
        this.notify.warning('Abbruch fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
      },
    });
  }

  meta = (t: string) => metaFor(TECH_META, t);
  protected readonly techIcon = techIcon;

  /** Klarname einer Voraussetzung (Tech ODER Gebaeude) inkl. benoetigter Stufe. */
  reqLabel(r: Requirement): string {
    return metaFor({ ...BUILDING_META, ...TECH_META }, r.type).label + ' ' + r.level;
  }

  /** Anzeigetext der NICHT erfuellten Voraussetzungen mit Klarnamen. */
  missingReqText(option: ResearchOption): string {
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
