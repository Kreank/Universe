import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { GameStateService } from '../../core/services/game-state.service';
import { ApiService } from '../../core/services/api.service';
import { ShortNumberPipe } from '../../shared/pipes/short-number.pipe';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { BalanceService } from '../../core/services/balance.service';
import {
  BUILDING_META,
  RESOURCE_META,
  RANK_META,
  SPECIALIZATION_META,
  SHIP_META,
  DEFENSE_META,
  TECH_META,
  MISSION_META,
  PLANET_TYPE_META,
  metaFor,
} from '../../core/models/display';
import {
  BuildQueueItem,
  BuildingState,
  Fleet,
  RankingEntry,
  ResearchState,
} from '../../core/models/api.models';
import { dashboardStyles } from './dashboard.styles';

@Component({
  selector: 'app-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ShortNumberPipe, CountdownComponent],
  template: `
    <h1>Dashboard</h1>

    <!-- Imperiums-Punkte (OGame-Score) — prominent, verlinkt zur Rangliste -->
    <a class="score-hero" routerLink="/ranking">
      <img class="score-ico" src="assets/img/nav/ranking.png" alt="" (error)="onIcoError($event)" />
      <div class="score-main">
        <span class="score-label">Imperiums-Punkte</span>
        <span class="score-value mono">{{ (me()?.points ?? 0) | shortNumber }}</span>
      </div>
      <div class="score-rank">
        <span class="rank-big mono">#{{ me()?.rank ?? '–' }}</span>
        <span class="faint small">von {{ totalPlayers() }}</span>
      </div>
      <div class="score-breakdown">
        <span class="bd tip" data-tip="Gebäude">🏗️ {{ (me()?.buildings ?? 0) | shortNumber }}</span>
        <span class="bd tip" data-tip="Forschung">🔬 {{ (me()?.research ?? 0) | shortNumber }}</span>
        <span class="bd tip" data-tip="Flotte">🚀 {{ (me()?.fleet ?? 0) | shortNumber }}</span>
        <span class="bd tip" data-tip="Verteidigung">🛡️ {{ (me()?.defense ?? 0) | shortNumber }}</span>
      </div>
      <span class="score-cta faint small">Rangliste →</span>
    </a>

    @if (planet(); as p) {
      <p class="muted sub">
        {{ p.name }} · {{ planetType(p.planet_type).glyph }} {{ planetType(p.planet_type).label }} ·
        Koordinaten [{{ p.galaxy }}:{{ p.system }}:{{ p.position }}] ·
        {{ p.temp_max }}°C · Felder {{ p.fields_used }}/{{ p.fields_max }}
      </p>

      <div class="cols">
       <div class="col">
        <!-- Ressourcen -->
        <section class="card">
          <div class="panel-title">⛏️ Ressourcen</div>
          <div class="res-grid">
            @for (r of resources(); track r.key) {
              <div class="res-card">
                <div class="row-between">
                  <span>{{ r.glyph }} {{ r.label }}</span>
                  <span class="mono">{{ r.amount | shortNumber }}</span>
                </div>
                <div class="bar" [class.full]="r.pct >= 100">
                  <span class="fill" [style.width.%]="r.pct"></span>
                </div>
                <div class="row-between small">
                  <span class="faint mono">{{ r.amount | shortNumber }} / {{ r.capacity | shortNumber }}</span>
                  <span class="mono" [class.ok]="r.rate >= 0">+{{ r.rate | shortNumber }}/h</span>
                </div>
              </div>
            }
            <div class="res-card energy">
              <div class="row-between">
                <span>⚡ Energie</span>
                <span class="mono" [class.neg]="energy().balance < 0">{{ energy().balance | shortNumber }}</span>
              </div>
              <div class="row-between small">
                <span class="faint">Produktion {{ energy().produced | shortNumber }}</span>
                <span class="faint">Verbrauch {{ energy().consumed | shortNumber }}</span>
              </div>
              <div class="row-between small">
                <span class="faint tip" data-tip="Bei Defizit drosselt der Faktor die Minen-Rate.">Faktor</span>
                <span class="mono" [class.neg]="energy().factor < 1">{{ (energy().factor * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Commander-Moral -->
        <section class="card">
          <div class="panel-title">🎖️ Crew-Moral</div>
          @if (state.commanders().length) {
            @for (c of state.commanders(); track c.id) {
              <a class="cmd-row" [routerLink]="['/commanders', c.id]">
                <span class="cmd-name">
                  {{ rank(c.rank).glyph }} {{ c.name }}
                  <span class="faint">· {{ spec(c.specialization).label }}</span>
                </span>
                <span class="cmd-morale" [class]="bandClass(c.morale)">
                  <span class="dot"></span>{{ c.morale }} · {{ c.morale_band.label }}
                </span>
              </a>
            }
            @if (state.span(); as s) {
              <p class="muted small span-line">
                Span of Control: {{ s.in_use }}/{{ s.total }} belegt
              </p>
            }
          } @else {
            <p class="muted small">Noch keine Commander. <a routerLink="/commanders">Kommandozentrale →</a></p>
          }
        </section>
       </div>

       <div class="col">
        <!-- Aktive Vorgaenge -->
        <section class="card">
          <div class="panel-title">⏳ Aktive Vorgaenge</div>

          <div class="ops-block">
            <div class="ops-label">🏗️ Bau</div>
            @if (activeBuild(); as b) {
              <div class="queue-row">
                <span>{{ metaB(b.type).glyph }} {{ metaB(b.type).label }} → Stufe {{ b.level + 1 }}</span>
                <app-countdown [target]="b.upgrade_finishes_at" />
              </div>
            } @else {
              <p class="muted small">Kein Bau aktiv. <a routerLink="/buildings">Bauen →</a></p>
            }
          </div>

          <hr />

          <div class="ops-block">
            <div class="ops-label">🔬 Forschung</div>
            @if (activeResearch(); as t) {
              <div class="queue-row">
                <span>{{ metaT(t.type).glyph }} {{ metaT(t.type).label }} → Stufe {{ t.level + 1 }}</span>
                <app-countdown [target]="t.finishes_at" />
              </div>
            } @else {
              <p class="muted small">Keine Forschung aktiv. <a routerLink="/research">Techbaum →</a></p>
            }
          </div>

          <hr />

          <div class="ops-block">
            <div class="ops-label">🛠️ Werft</div>
            @if (shipyardQueue().length) {
              @for (q of shipyardQueue(); track $index) {
                <div class="queue-row">
                  <span>{{ metaShip(q).glyph }} {{ q.count }}× {{ metaShip(q).label }}</span>
                  <app-countdown [target]="q.finishes_at" />
                </div>
              }
            } @else {
              <p class="muted small">Werft frei. <a routerLink="/shipyard">Schiffe bauen →</a></p>
            }
          </div>
        </section>

        <!-- Flottenbewegungen -->
        <section class="card">
          <div class="panel-title">🚀 Flottenbewegungen</div>
          @if (activeFleets().length) {
            @for (f of activeFleets(); track f.id) {
              <div class="queue-row">
                <span>
                  {{ metaM(f.mission).glyph }} {{ metaM(f.mission).label }}
                  <span class="faint">→ [{{ f.target.galaxy }}:{{ f.target.system }}:{{ f.target.position }}]</span>
                  <span class="chip">{{ statusLabel(f.status) }}</span>
                </span>
                <app-countdown [target]="f.status === 'returning' ? f.return_at : f.arrive_at" />
              </div>
            }
          } @else {
            <p class="muted small">Keine Flotten unterwegs. <a routerLink="/fleet">Flotte entsenden →</a></p>
          }
        </section>

        <!-- Alerts / Ereignisse -->
        <section class="card">
          <div class="panel-title">⚠ Alerts & Ereignisse</div>
          @if (state.attackAlerts().length) {
            @for (a of state.attackAlerts(); track a.location) {
              <div class="alert danger">
                <span>⚔️ Angriff auf {{ a.location }}</span>
                <app-countdown [target]="a.arriveAt" />
              </div>
            }
          }
          @if (energyDeficit()) {
            <div class="alert danger">
              <span>⚡ Energie-Defizit ({{ energy().balance | shortNumber }}) drosselt die Minen</span>
              <a class="btn btn-sm" routerLink="/buildings">Beheben</a>
            </div>
          }
          @if (fullStorages().length) {
            <div class="alert">
              <span>📦 Lager fast voll: {{ fullStoragesLabel() }}</span>
              <a class="btn btn-sm" routerLink="/buildings">Ausbauen</a>
            </div>
          }
          @if (state.unreadTransmissions() > 0) {
            <div class="alert decision">
              <span>📡 {{ state.unreadTransmissions() }} ungelesene Transmission(en)</span>
              <a class="btn btn-sm" routerLink="/transmissions">Oeffnen</a>
            </div>
          }
          @if (!hasAlerts()) {
            <p class="muted small">Keine offenen Ereignisse. Alles ruhig im Sektor.</p>
          }
        </section>

       </div>
      </div>
    } @else {
      <p class="empty-state">Lade Planetendaten…</p>
    }
  `,
  styles: [dashboardStyles],
})
export class DashboardComponent {
  protected readonly state = inject(GameStateService);
  private readonly api = inject(ApiService);
  private readonly balance = inject(BalanceService);

  protected readonly planet = this.state.activePlanet;

  // --- Aktive Vorgaenge (per Effekt beim Planetenwechsel geladen) ---
  protected readonly activeBuild = signal<BuildingState | null>(null);
  protected readonly activeResearch = signal<ResearchState | null>(null);
  protected readonly shipyardQueue = signal<BuildQueueItem[]>([]);

  // --- Imperiums-Punkte (Rangliste) ---
  protected readonly me = signal<RankingEntry | null>(null);
  protected readonly totalPlayers = signal(0);

  constructor() {
    // Eigenen Score + Rang frisch laden (Server rechnet bei jedem Abruf neu).
    this.api.getRanking().subscribe({
      next: (r) => {
        this.me.set(r.me);
        this.totalPlayers.set(r.total_players);
      },
      error: () => {},
    });

    // Reload der Timer, sobald ein anderer Planet aktiv wird.
    effect(() => {
      const id = this.state.activePlanetId();
      if (id) {
        void this.loadActiveOps(id);
      } else {
        this.activeBuild.set(null);
        this.activeResearch.set(null);
        this.shipyardQueue.set([]);
      }
    });
  }

  private async loadActiveOps(planetId: string): Promise<void> {
    // Bau
    try {
      const res = await firstValueFrom(this.api.getBuildings(planetId));
      this.activeBuild.set(res.buildings.find((b) => b.upgrade_finishes_at) ?? null);
    } catch {
      this.activeBuild.set(null);
    }
    // Forschung (global)
    try {
      const res = await firstValueFrom(this.api.getResearch());
      this.activeResearch.set(res.research.find((t) => t.finishes_at) ?? null);
    } catch {
      this.activeResearch.set(null);
    }
    // Werft-Queue
    try {
      const res = await firstValueFrom(this.api.getShipyard(planetId));
      this.shipyardQueue.set(res.queue ?? []);
    } catch {
      this.shipyardQueue.set([]);
    }
  }

  protected readonly resources = computed(() => {
    const res = this.planet()?.resources;
    const keys: ('metal' | 'crystal' | 'deuterium')[] = ['metal', 'crystal', 'deuterium'];
    return keys.map((key) => {
      const pool = res?.[key];
      const amount = pool?.amount ?? 0;
      const capacity = pool?.capacity ?? 0;
      return {
        key,
        label: RESOURCE_META[key].label,
        glyph: RESOURCE_META[key].glyph,
        amount,
        capacity,
        rate: pool?.rate ?? 0,
        pct: capacity > 0 ? Math.min(100, (amount / capacity) * 100) : 0,
      };
    });
  });

  protected readonly energy = computed(
    () =>
      this.planet()?.resources?.energy ?? { produced: 0, consumed: 0, balance: 0, factor: 1 },
  );

  protected readonly energyDeficit = computed(() => this.energy().balance < 0);

  /** Lager mit >= 95% Fuellstand. */
  protected readonly fullStorages = computed(() => this.resources().filter((r) => r.pct >= 95));
  protected readonly fullStoragesLabel = computed(() =>
    this.fullStorages().map((r) => r.label).join(', '),
  );

  /** Aktive Flotten: unterwegs zum Ziel oder auf dem Rueckflug. */
  protected readonly activeFleets = computed(() =>
    this.state.fleets().filter((f) => f.status === 'flying' || f.status === 'returning'),
  );

  protected readonly hasAlerts = computed(
    () =>
      this.state.attackAlerts().length > 0 ||
      this.energyDeficit() ||
      this.fullStorages().length > 0 ||
      this.state.unreadTransmissions() > 0,
  );

  statusLabel = (s: string) => (s === 'returning' ? 'Rueckflug' : 'unterwegs');

  metaB = (t: string) => metaFor(BUILDING_META, t);
  metaT = (t: string) => metaFor(TECH_META, t);
  metaM = (m: string) => metaFor(MISSION_META, m);
  metaShip = (q: BuildQueueItem) =>
    metaFor(q.category === 'defense' ? DEFENSE_META : SHIP_META, q.type);
  rank = (r: string) => metaFor(RANK_META, r);
  spec = (s: string) => metaFor(SPECIALIZATION_META, s);
  planetType = (t: string | undefined) => metaFor(PLANET_TYPE_META, t ?? 'normal');
  bandClass = (m: number) => this.balance.moraleBandClass(m);

  protected onIcoError(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
}
