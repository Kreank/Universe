import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { BuildingOption, BuildingState, BuildingsResponse } from '../../core/models/api.models';
import { BUILDING_META, metaFor } from '../../core/models/display';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { DetailPopupComponent } from '../../shared/components/detail-popup.component';
import { BuildTileComponent } from '../../shared/components/build-tile.component';
import { TabBarComponent } from '../../shared/components/tab-bar.component';
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
  imports: [CountdownComponent, DetailPopupComponent, BuildTileComponent, TabBarComponent],
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
              [iconSrc]="'assets/img/buildings/' + b.type + '.png'"
              [glyph]="meta(b.type).glyph"
              [name]="meta(b.type).label"
              [badge]="b.level"
              badgeTip="Stufe"
              [cost]="b.option?.cost ?? null"
              [available]="balances()"
              [timeSeconds]="b.option?.build_seconds ?? null"
              [busy]="!!b.finishesAt"
              (openDetail)="openDetail(b)"
            >
              @if (b.option && (b.option.energy_now !== 0 || b.option.energy_delta !== 0)) {
                <span stats class="energy small"
                  [class.produces]="b.option.energy_now > 0"
                  [class.consumes]="b.option.energy_now < 0"
                  [attr.data-tip]="energyTip(b.option)">
                  ⚡ {{ energyLabel(b.option.energy_now) }}@if (b.option.energy_delta !== 0) {<span class="delta"> (Δ {{ signed(b.option.energy_delta) }})</span>}
                </span>
              }

              <ng-container action>
                @if (b.finishesAt) {
                  <span class="building-badge">⏳ Im Bau</span>
                  <app-countdown [target]="b.finishesAt" />
                  <button
                    class="btn btn-ghost btn-sm full cancel-build"
                    type="button"
                    [disabled]="pending() === b.type"
                    (click)="cancelBuild(b.type)"
                  >
                    {{ pending() === b.type ? '…' : '✕ Abbrechen' }}
                  </button>
                } @else {
                  @if (b.option) {
                    <button
                      class="btn btn-primary btn-sm full"
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
                      class="btn btn-ghost btn-sm demolish full"
                      type="button"
                      [disabled]="pending() === b.type || anyBuilding()"
                      (click)="demolish(b.type)"
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
        [actionLabel]="sel.option && !sel.finishesAt ? ('Ausbauen → ' + sel.option.next_level) : null"
        [actionDisabled]="!canUpgrade(sel) || anyBuilding()"
        [actionHint]="buildingHint(sel)"
        [pending]="pending() === sel.type"
        (confirm)="upgradeFromPopup()"
        (close)="selected.set(null)"
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

  private readonly data = signal<BuildingsResponse | null>(null);
  protected readonly loading = signal(true);
  protected readonly pending = signal<string | null>(null);
  protected readonly selected = signal<BuildingRow | null>(null);

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

  // -- Reiter (Kategorie-Tabs) --
  protected readonly activeTab = signal<string>('resource');
  protected readonly tabDefs = computed(() =>
    this.groups().map((g) => ({ key: g.key, label: g.label, glyph: g.glyph, count: g.rows.length })),
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
    return res
      ? { metal: res.metal.amount, crystal: res.crystal.amount, deuterium: res.deuterium.amount }
      : null;
  });

  constructor() {
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
      },
      error: () => this.loading.set(false),
    });
  }

  canUpgrade(b: BuildingRow): boolean {
    return !!b.option && b.option.can_afford && b.option.requirements_met && !b.finishesAt;
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
