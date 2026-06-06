import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { GameStateService } from '../../core/services/game-state.service';
import { ShortNumberPipe } from '../../shared/pipes/short-number.pipe';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { BalanceService } from '../../core/services/balance.service';
import {
  BUILDING_META,
  RESOURCE_META,
  RANK_META,
  SPECIALIZATION_META,
  metaFor,
} from '../../core/models/display';
import { dashboardStyles } from './dashboard.styles';

@Component({
  selector: 'app-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ShortNumberPipe, CountdownComponent],
  template: `
    <h1>Dashboard</h1>
    @if (planet(); as p) {
      <p class="muted sub">
        {{ p.name }} · Koordinaten [{{ p.galaxy }}:{{ p.system }}:{{ p.position }}] ·
        Felder {{ p.fields_used }}/{{ p.fields_max }}
      </p>

      <div class="grid cols">
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

        <!-- Bau-Queue -->
        <section class="card">
          <div class="panel-title">🏗️ Bau & Forschung</div>
          @if (buildQueue().length) {
            @for (b of buildQueue(); track b.type) {
              <div class="queue-row">
                <span>{{ metaB(b.type).glyph }} {{ metaB(b.type).label }} → Stufe {{ b.level + 1 }}</span>
                <app-countdown [target]="b.upgrade_finishes_at" />
              </div>
            }
          } @else {
            <p class="muted small">Kein Gebaeudeausbau aktiv. <a routerLink="/buildings">Bauen →</a></p>
          }
          <hr />
          @if (state.activePlanet()) {
            <p class="muted small">Forschung wird global verwaltet. <a routerLink="/research">Techbaum →</a></p>
          }
        </section>

        <!-- Alerts / Ankuenfte -->
        <section class="card">
          <div class="panel-title">⚠ Alerts & Ankuenfte</div>
          @if (state.attackAlerts().length) {
            @for (a of state.attackAlerts(); track a.location) {
              <div class="alert danger">
                <span>⚔️ Angriff auf {{ a.location }}</span>
                <app-countdown [target]="a.arriveAt" />
              </div>
            }
          }
          @for (f of incomingFleets(); track f.id) {
            <div class="alert">
              <span>🚀 {{ f.mission }} → [{{ f.target.galaxy }}:{{ f.target.system }}:{{ f.target.position }}]</span>
              <app-countdown [target]="f.status === 'returning' ? f.return_at : f.arrive_at" />
            </div>
          }
          @if (!state.attackAlerts().length && !incomingFleets().length) {
            <p class="muted small">Keine offenen Ereignisse. Alles ruhig im Sektor.</p>
          }
          @if (state.pendingDecisions() > 0) {
            <div class="alert decision">
              <span>📡 {{ state.pendingDecisions() }} Funkspruch/Forderung wartet</span>
              <a class="btn btn-sm" routerLink="/transmissions">Oeffnen</a>
            </div>
          }
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
    } @else {
      <p class="empty-state">Lade Planetendaten…</p>
    }
  `,
  styles: [dashboardStyles],
})
export class DashboardComponent {
  protected readonly state = inject(GameStateService);
  private readonly balance = inject(BalanceService);

  protected readonly planet = this.state.activePlanet;

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

  protected readonly buildQueue = computed(
    () => this.planet()?.buildings?.filter((b) => b.upgrade_finishes_at) ?? [],
  );

  protected readonly incomingFleets = computed(() =>
    this.state.fleets().filter((f) => f.status !== 'returned'),
  );

  metaB = (t: string) => metaFor(BUILDING_META, t);
  rank = (r: string) => metaFor(RANK_META, r);
  spec = (s: string) => metaFor(SPECIALIZATION_META, s);
  bandClass = (m: number) => this.balance.moraleBandClass(m);
}
