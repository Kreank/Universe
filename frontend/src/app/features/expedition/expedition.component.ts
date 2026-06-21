import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import { BalanceService } from '../../core/services/balance.service';
import { Coordinate, Fleet, FleetSlots, Transmission } from '../../core/models/api.models';
import { MISSION_META, metaFor } from '../../core/models/display';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { FleetDispatchComponent } from '../../shared/components/fleet-dispatch.component';
import { FleetSlotsComponent } from '../../shared/components/fleet-slots.component';

/**
 * Expedition · Galaktische Weiten. Eigenständiger Bereich (analog Bergbau), aus dem
 * überladenen Flotten-Dropdown herausgelöst: Expeditionen werden hier entsendet
 * (Zielsystem wählen → tiefer Raum = Position {{deep}}), laufende Expeditionen mit
 * Countdown verfolgt und die Funde der letzten Expeditionen als Log angezeigt.
 *
 * Der Versand läuft weiterhin über /api/fleets/send (mission="expedition") via das
 * gemeinsame Versand-Overlay (FleetDispatchComponent) — am Deep-Space-Slot bietet es
 * nur die Expeditions-Mission inkl. Doktrin- und Verweildauer-Wahl an.
 */
@Component({
  selector: 'app-expedition',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, CountdownComponent, EmptyStateComponent, FleetDispatchComponent, FleetSlotsComponent],
  template: `
    <h1>Expedition · Galaktische Weiten</h1>
    <p class="sub">
      Schick eine Flotte in den tiefen Raum (Position {{ deepPos() }}) eines Systems. Sie verweilt
      die gewählte Dauer und kehrt mit Funden heim — Rohstoffe, Schiffe, exotische Materie … oder sie
      trifft auf Piraten, Aliens oder ein Schwarzes Loch.
    </p>

    @if (maxHours() < 1) {
      <div class="card lock">
        <div class="lock-ico">🛰</div>
        <div>
          <strong>Astrophysik nicht erforscht</strong>
          <p class="muted small">
            Erforsche <strong>Astrophysik</strong>, um Expeditionen in die galaktischen Weiten zu
            entsenden. Jede Stufe verlängert die mögliche Verweildauer (und damit den Ertrag).
          </p>
          <a class="btn btn-sm btn-primary" routerLink="/research" [queryParams]="{ focus: 'astrophysics' }">Zur Forschung →</a>
        </div>
      </div>
    } @else {
      <section class="card launch">
        <div class="panel-title">🌌 Expedition entsenden</div>
        <p class="muted small">
          Zielsystem wählen — die Expedition fliegt automatisch auf den Deep-Space-Slot
          (Position {{ deepPos() }}). Schiffe, Doktrin & Verweildauer wählst du im nächsten Schritt.
        </p>
        <div class="launch-row">
          <div class="field">
            <label>Zielsystem (Galaxie : System)</label>
            <div class="coord">
              <input type="number" min="1" [ngModel]="g()" (ngModelChange)="g.set(+$event || 1)" aria-label="Galaxie" />
              <span class="sep">:</span>
              <input type="number" min="1" [ngModel]="s()" (ngModelChange)="s.set(+$event || 1)" aria-label="System" />
              <span class="sep">:</span>
              <span class="fixed mono" title="Tiefer Raum (fest)">{{ deepPos() }}</span>
            </div>
          </div>
          <button class="btn btn-primary launch-btn" type="button" (click)="openDispatch()">
            🌌 Schiffe wählen & starten
          </button>
        </div>
        <p class="muted small">
          Tipp: Position {{ deepPos() }} ist in jedem System der tiefe Raum — meist nutzt man das
          eigene System ([{{ home()?.galaxy }}:{{ home()?.system }}:{{ deepPos() }}]).
          <button class="lnk" type="button" (click)="useHome()">eigenes System übernehmen</button>
        </p>
      </section>
    }

    <section class="card running">
      <div class="panel-title">🛰️ Laufende Expeditionen</div>
      <p class="slot-line muted small">
        {{ runningExpeditions().length }} Expedition{{ runningExpeditions().length === 1 ? '' : 'en' }} aktiv ·
        <app-fleet-slots [slots]="slots()" [compact]="true" />
      </p>
      @if (runningExpeditions().length) {
        @for (f of runningExpeditions(); track f.id) {
          <div class="fleet-row">
            <div class="fleet-info">
              <span class="mono small">→ [{{ f.target.galaxy }}:{{ f.target.system }}:{{ f.target.position }}]</span>
              <span class="chip">{{ shipsTotal(f) }} Schiffe · {{ statusLabel(f.status) }}</span>
            </div>
            <div class="fleet-act">
              <app-countdown [target]="f.status === 'returning' ? f.return_at : f.arrive_at" />
              @if (f.status !== 'returning' && f.status !== 'returned') {
                <button class="btn btn-danger btn-sm" type="button" (click)="recall(f.id)">Rückruf</button>
              }
            </div>
          </div>
        }
      } @else {
        <app-empty-state art="empty_fleet" [fill]="true">Keine Expeditionen unterwegs.</app-empty-state>
      }
    </section>

    <section class="card log">
      <div class="panel-title">📜 Funde der letzten Expeditionen</div>
      @if (loadingLog()) {
        <p class="muted small">Lade Berichte…</p>
      } @else if (expeditionLog().length) {
        @for (t of expeditionLog(); track t.id) {
          <article class="log-row" [class.unread]="!t.read">
            <div class="log-head">
              <span class="log-subj">{{ t.subject }}</span>
              <span class="log-date muted small">{{ formatDate(t.created_at) }}</span>
            </div>
            <p class="log-body small">{{ t.body }}</p>
          </article>
        }
        <p class="muted small">
          Alle Berichte stehen im <a routerLink="/transmissions">Postfach →</a>
        </p>
      } @else {
        <app-empty-state art="empty_search">
          Noch keine Expeditionsberichte. Schick deine erste Flotte in die Weiten.
        </app-empty-state>
      }
    </section>

    @if (dispatch(); as d) {
      <app-fleet-dispatch
        [target]="d"
        targetName="Tiefer Raum"
        [initialMission]="'expedition'"
        (sent)="onSent()"
        (close)="dispatch.set(null)"
      />
    }
  `,
  styles: [
    `
      .sub { color: var(--text-dim); margin-top: calc(-1 * var(--sp-2)); max-width: 70ch; }
      .panel-title { font-family: var(--font-display); font-size: var(--fs-sm); text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); margin-bottom: var(--sp-3); }
      .card { padding: var(--sp-4); margin-bottom: var(--sp-4); }
      .lock { display: flex; gap: var(--sp-3); align-items: center; }
      .lock-ico { font-size: 2rem; }

      .launch-row { display: flex; flex-wrap: wrap; gap: var(--sp-3); align-items: flex-end; }
      .field { display: flex; flex-direction: column; gap: var(--sp-1); }
      .field label { font-size: var(--fs-xs); color: var(--text-dim); }
      .coord { display: flex; align-items: center; gap: var(--sp-1); }
      .coord input { width: 64px; text-align: center; min-height: 32px; }
      .coord .sep { color: var(--text-faint); }
      .coord .fixed { width: 40px; text-align: center; color: var(--text-dim); border: 1px dashed var(--border-strong); border-radius: var(--r-sm); padding: 4px 0; }
      .launch-btn { min-height: 38px; }
      .lnk { background: none; border: none; color: var(--accent); cursor: pointer; padding: 0; font: inherit; text-decoration: underline; }

      .slot-line { display: flex; align-items: baseline; gap: 0.35em; flex-wrap: wrap; margin: calc(-1 * var(--sp-2)) 0 var(--sp-2); }
      .slot-line app-fleet-slots { display: inline; }
      .fleet-row { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); padding: var(--sp-2) 0; border-bottom: 1px solid var(--border); }
      .fleet-row:last-child { border-bottom: none; }
      .fleet-info { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
      .fleet-act { display: flex; align-items: center; gap: var(--sp-2); }
      .chip { font-size: var(--fs-sm); background: var(--surface-2); border: 1px solid var(--border-strong); border-radius: var(--r-sm); padding: 2px var(--sp-2); }

      .log-row { padding: var(--sp-2) 0; border-bottom: 1px solid var(--border); }
      .log-row:last-of-type { border-bottom: none; }
      .log-row.unread { border-left: 2px solid var(--accent); padding-left: var(--sp-2); }
      .log-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-2); }
      .log-subj { font-weight: 600; }
      .log-body { color: var(--text-dim); margin: var(--sp-1) 0 0; }
    `,
  ],
})
export class ExpeditionComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly balance = inject(BalanceService);

  /** Deep-Space-Slot (tiefer Raum) aus der Balance — Expeditionen fliegen immer dorthin. */
  protected readonly deepPos = computed(() =>
    Number((this.balance.value as any)?.expedition?.deep_space_position ?? 16),
  );

  protected readonly home = computed(() => this.state.activePlanet());
  protected readonly g = signal(1);
  protected readonly s = signal(1);

  /** Astrophysik-Stufe (account-weit) -> Obergrenze der Verweildauer (0 = nicht freigeschaltet). */
  protected readonly astroLevel = signal(0);
  protected readonly maxHours = computed(() => {
    const dur = (this.balance.value as { expedition?: { duration?: Record<string, number> } } | undefined)
      ?.expedition?.duration ?? {};
    const per = Number(dur['max_hours_per_astro_level'] ?? 1);
    const cap = Number(dur['hour_cap'] ?? 24);
    return Math.max(0, Math.min(cap, Math.floor(this.astroLevel() * per)));
  });

  /** Offenes Versand-Overlay (Ziel = gewähltes System, Position = tiefer Raum). */
  protected readonly dispatch = signal<Coordinate | null>(null);

  /** Flotten-Slot-Kapazität (gemeinsamer Pool — Expeditionen zählen mit). */
  protected readonly slots = signal<FleetSlots | null>(null);

  protected readonly runningExpeditions = computed(() =>
    this.state.fleets().filter((f) => f.mission === 'expedition' && f.status !== 'returned'),
  );

  protected readonly loadingLog = signal(true);
  protected readonly transmissions = signal<Transmission[]>([]);
  /** Expeditionsberichte = Transmissions mit „Expedition" im Betreff (System-/Kampfbericht). */
  protected readonly expeditionLog = computed(() =>
    this.transmissions()
      .filter((t) => (t.subject ?? '').includes('Expedition'))
      .slice(0, 8),
  );

  constructor() {
    // Zielsystem mit dem aktiven Planeten vorbelegen.
    this.useHome();
    this.api.getResearch().subscribe({
      next: (r) => {
        const astro = r.research.find((x) => x.type === 'astrophysics');
        this.astroLevel.set(astro?.level ?? 0);
      },
      error: () => {},
    });
    this.loadLog();
    this.loadSlots();
  }

  loadSlots(): void {
    this.api.getFleetSlots().subscribe({
      next: (s) => this.slots.set(s),
      error: () => this.slots.set(null),
    });
  }

  loadLog(): void {
    this.loadingLog.set(true);
    this.api.getTransmissions().subscribe({
      next: (rows) => { this.transmissions.set(rows); this.loadingLog.set(false); },
      error: () => { this.transmissions.set([]); this.loadingLog.set(false); },
    });
  }

  /** Zielsystem auf das aktive Heimatsystem setzen. */
  useHome(): void {
    const p = this.state.activePlanet();
    if (p) {
      this.g.set(p.galaxy);
      this.s.set(p.system);
    }
  }

  /** Versand-Overlay öffnen — Ziel = gewähltes System auf dem Deep-Space-Slot. */
  openDispatch(): void {
    this.dispatch.set({ galaxy: this.g(), system: this.s(), position: this.deepPos() });
  }

  /** Nach erfolgreichem Start: Overlay schließen, laufende Expeditionen + Log frisch ziehen. */
  onSent(): void {
    this.dispatch.set(null);
    void this.state.reloadFleets();
    this.loadLog();
    this.loadSlots();
  }

  recall(fleetId: string): void {
    this.api.recallFleet(fleetId).subscribe({
      next: () => {
        this.notify.info('Rückruf', 'Expedition kehrt zur Basis zurück.');
        this.loadSlots();
        void this.state.reloadFleets();
      },
      error: (err) => this.notify.warning('Rückruf fehlgeschlagen', err?.error?.detail ?? 'Fehler.'),
    });
  }

  shipsTotal(f: Fleet): number {
    return Object.values(f.ships).reduce((a, b) => a + b, 0);
  }

  statusLabel(status: string): string {
    switch (status) {
      case 'flying': return 'im Anflug';
      case 'arrived': return 'in den Weiten';
      case 'returning': return 'Rückflug';
      default: return status;
    }
  }

  formatDate(iso: string): string {
    const d = new Date(iso);
    return isNaN(d.getTime()) ? '' : d.toLocaleString('de-DE', { day: '2-digit', month: '2-digit', hour: '2-digit', minute: '2-digit' });
  }

  missionMeta = (m: string) => metaFor(MISSION_META, m);
}
