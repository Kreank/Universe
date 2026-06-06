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

      <div class="grid two">
        <section>
          <div class="panel-title">🚀 Schiffe</div>
          <div class="grid list">
            @for (s of d.ships; track s.type) {
              <ng-container *ngTemplateOutlet="unitCard; context: { $implicit: s, cat: 'ship' }" />
            }
          </div>
        </section>

        <section>
          <div class="panel-title">🛡️ Verteidigung</div>
          <div class="grid list">
            @for (s of d.defenses; track s.type) {
              <ng-container *ngTemplateOutlet="unitCard; context: { $implicit: s, cat: 'defense' }" />
            }
          </div>
        </section>
      </div>

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
      .two { grid-template-columns: 1fr 1fr; align-items: start; }
      .list { grid-template-columns: 1fr; }
      .unit-head { display: flex; gap: 0.8rem; align-items: flex-start; }
      .unit h3 { font-size: 0.98rem; margin: 0 0 0.3rem; }
      .unit-build { display: flex; gap: 0.5rem; margin-top: 0.7rem; }
      .unit-build input { width: 90px; }
      .small { font-size: 0.76rem; }
      .hint { display: block; margin-top: 0.4rem; color: var(--text-faint); }
      .hint.warn { color: var(--warn); }
      @media (max-width: 860px) { .two { grid-template-columns: 1fr; } }
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
