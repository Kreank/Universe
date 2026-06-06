import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import {
  Fleet,
  FleetMission,
  GalaxyCell,
  PlanetUnit,
} from '../../core/models/api.models';
import { MISSION_META, RANK_META, SHIP_META, metaFor } from '../../core/models/display';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { NotificationService } from '../../core/services/notification.service';
import { fleetStyles } from './fleet.styles';

@Component({
  selector: 'app-fleet',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, CountdownComponent],
  template: `
    <h1>Flotte</h1>

    <div class="grid layout">
      <!-- Flotte senden -->
      <section class="card send">
        <div class="panel-title">🚀 Flotte entsenden</div>

        <div class="ships">
          @for (s of availableShips(); track s.type) {
            <label class="ship-pick">
              <span>{{ shipMeta(s.type).glyph }} {{ shipMeta(s.type).label }}</span>
              <span class="faint">verf. {{ s.count }}</span>
              <input
                type="number"
                min="0"
                [max]="s.count"
                [ngModel]="shipCount(s.type)"
                (ngModelChange)="setShip(s.type, $event, s.count)"
              />
            </label>
          } @empty {
            <p class="muted small">Keine Schiffe auf diesem Planeten. <a href="/shipyard">Werft →</a></p>
          }
        </div>

        @if (prefilled()) {
          <p class="hint small">🎯 Ziel aus der Galaxie-Karte uebernommen: [{{ prefilled() }}]</p>
        }

        <div class="coord">
          <div class="field">
            <label>Galaxie</label>
            <input type="number" min="1" [(ngModel)]="targetG" />
          </div>
          <div class="field">
            <label>System</label>
            <input type="number" min="1" [(ngModel)]="targetS" />
          </div>
          <div class="field">
            <label>Position</label>
            <input type="number" min="1" [(ngModel)]="targetP" />
          </div>
        </div>

        <div class="row2">
          <div class="field">
            <label>Mission</label>
            <select [(ngModel)]="mission">
              @for (m of missions; track m) {
                <option [value]="m">{{ missionMeta(m).glyph }} {{ missionMeta(m).label }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label class="tip" data-tip="Langsamer = weniger Sprit">Tempo {{ speed() }}%</label>
            <input type="range" min="10" max="100" step="10" [ngModel]="speed()" (ngModelChange)="speed.set($event)" />
          </div>
        </div>

        <div class="field">
          <label>Commander</label>
          <select [(ngModel)]="commanderId">
            <option [ngValue]="null">— ohne Commander —</option>
            @for (c of assignableCommanders(); track c.id) {
              <option [ngValue]="c.id">{{ rankMeta(c.rank).glyph }} {{ c.name }} ({{ c.morale_band.label }})</option>
            }
          </select>
        </div>

        <button class="btn btn-primary full" type="button" [disabled]="!canSend() || sending()" (click)="send()">
          {{ sending() ? 'Sende…' : 'Flotte starten' }}
        </button>
        @if (!hasSelection()) {
          <p class="hint small">Mindestens ein Schiff auswaehlen.</p>
        }
      </section>

      <!-- Laufende Flotten -->
      <section class="card running">
        <div class="panel-title">🛰️ Laufende Flotten</div>
        @if (activeFleets().length) {
          @for (f of activeFleets(); track f.id) {
            <div class="fleet-row">
              <div class="fleet-info">
                <span class="badge-mission">{{ missionMeta(f.mission).glyph }} {{ missionMeta(f.mission).label }}</span>
                <span class="mono small">→ [{{ f.target.galaxy }}:{{ f.target.system }}:{{ f.target.position }}]</span>
                <span class="chip">{{ shipsTotal(f) }} Schiffe · {{ statusLabel(f.status) }}</span>
              </div>
              <div class="fleet-act">
                <app-countdown [target]="f.status === 'returning' ? f.return_at : f.arrive_at" />
                @if (f.status !== 'returning' && f.status !== 'returned') {
                  <button class="btn btn-danger btn-sm" type="button" (click)="recall(f.id)">Rueckruf</button>
                }
              </div>
            </div>
          }
        } @else {
          <p class="muted small">Keine Flotten unterwegs.</p>
        }
      </section>

      <!-- Galaxie-Ansicht -->
      <section class="card galaxy">
        <div class="panel-title">🌌 Galaxie-Ansicht</div>
        <div class="gx-controls">
          <input type="number" min="1" [(ngModel)]="viewG" aria-label="Galaxie" />
          <span class="faint">:</span>
          <input type="number" min="1" [(ngModel)]="viewS" aria-label="System" />
          <button class="btn btn-sm" type="button" (click)="loadGalaxy()">Scannen</button>
        </div>
        @if (galaxyLoading()) {
          <p class="muted small">Scanne System…</p>
        } @else if (cells().length) {
          <table class="gx-table">
            <thead>
              <tr><th>Pos</th><th>Belegung</th><th>Name</th><th></th></tr>
            </thead>
            <tbody>
              @for (c of cells(); track c.position) {
                <tr [class.occupied]="c.occupant_type !== 'empty'">
                  <td class="mono">{{ c.position }}</td>
                  <td>{{ occupantLabel(c) }}</td>
                  <td class="muted">{{ c.name ?? '—' }}</td>
                  <td>
                    @if (c.occupant_type !== 'empty') {
                      <button class="btn btn-ghost btn-sm" type="button" (click)="targetCell(c)">Anvisieren</button>
                    }
                  </td>
                </tr>
              }
            </tbody>
          </table>
        } @else {
          <p class="muted small">System scannen, um Ziele zu sehen.</p>
        }
      </section>
    </div>
  `,
  styles: [fleetStyles],
})
export class FleetComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);

  protected readonly missions: FleetMission[] = ['attack', 'transport', 'spy', 'deploy'];

  // Sende-Formular
  protected readonly selection = signal<Record<string, number>>({});
  targetG = 1;
  targetS = 1;
  targetP = 1;
  mission: FleetMission = 'attack';
  commanderId: string | null = null;
  protected readonly speed = signal(100);
  protected readonly sending = signal(false);

  // Galaxie
  viewG = 1;
  viewS = 1;
  protected readonly cells = signal<GalaxyCell[]>([]);
  protected readonly galaxyLoading = signal(false);

  protected readonly availableShips = computed<PlanetUnit[]>(
    () => this.state.activePlanet()?.ships?.filter((s) => s.count > 0) ?? [],
  );

  protected readonly assignableCommanders = computed(() =>
    this.state.commanders().filter((c) => c.status !== 'training' && !c.assigned_fleet_id),
  );

  protected readonly activeFleets = computed(() =>
    this.state.fleets().filter((f) => f.status !== 'returned'),
  );

  protected readonly hasSelection = computed(() =>
    Object.values(this.selection()).some((n) => n > 0),
  );

  protected readonly canSend = computed(() => this.hasSelection() && !!this.state.activePlanetId());

  // Wurde aus der Galaxie-Karte mit Ziel-Koordinaten aufgerufen?
  protected readonly prefilled = signal<string | null>(null);

  constructor() {
    // Deep-Link aus der Galaxie-Ansicht: /fleet?g=&s=&p=&mission=attack
    const qp = this.route.snapshot.queryParamMap;
    const g = qp.get('g');
    const s = qp.get('s');
    const p = qp.get('p');
    if (g && s && p) {
      this.targetG = Number(g);
      this.targetS = Number(s);
      this.targetP = Number(p);
      const m = qp.get('mission') as FleetMission | null;
      if (m && this.missions.includes(m)) {
        this.mission = m;
      }
      this.prefilled.set(`${this.targetG}:${this.targetS}:${this.targetP}`);
      // Galaxie-Mini-Ansicht direkt auf das Zielsystem stellen.
      this.viewG = this.targetG;
      this.viewS = this.targetS;
      this.loadGalaxy();
    }

    effect(() => {
      const p2 = this.state.activePlanet();
      if (p2) {
        // Galaxie-Ansicht standardmaessig auf das eigene System (nur ohne Deep-Link)
        if (this.cells().length === 0 && !this.prefilled()) {
          this.viewG = p2.galaxy;
          this.viewS = p2.system;
        }
      }
    });
  }

  shipCount(type: string): number {
    return this.selection()[type] ?? 0;
  }

  setShip(type: string, value: number, max: number): void {
    const n = Math.max(0, Math.min(max, Math.floor(value || 0)));
    this.selection.update((s) => ({ ...s, [type]: n }));
  }

  send(): void {
    const origin = this.state.activePlanetId();
    if (!origin || !this.hasSelection()) {
      return;
    }
    const ships: Record<string, number> = {};
    for (const [type, n] of Object.entries(this.selection())) {
      if (n > 0) {
        ships[type] = n;
      }
    }
    this.sending.set(true);
    this.api
      .sendFleet({
        origin_planet_id: origin,
        target: { galaxy: this.targetG, system: this.targetS, position: this.targetP },
        mission: this.mission,
        ships,
        cargo: { metal: 0, crystal: 0, deuterium: 0 },
        commander_id: this.commanderId,
        speed_pct: this.speed(),
      })
      .subscribe({
        next: () => {
          this.sending.set(false);
          this.selection.set({});
          this.notify.success('Flotte gestartet', `Mission ${this.missionMeta(this.mission).label} unterwegs.`);
          void this.state.reloadFleets();
          void this.state.reloadActivePlanet();
          void this.state.reloadCommanders();
        },
        error: (err) => {
          this.sending.set(false);
          this.notify.warning('Start fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
        },
      });
  }

  recall(fleetId: string): void {
    this.api.recallFleet(fleetId).subscribe({
      next: () => {
        this.notify.info('Rueckruf', 'Flotte kehrt zur Basis zurueck.');
        void this.state.reloadFleets();
      },
      error: (err) => this.notify.warning('Rueckruf fehlgeschlagen', err?.error?.detail ?? 'Fehler.'),
    });
  }

  loadGalaxy(): void {
    this.galaxyLoading.set(true);
    this.api.getGalaxy(this.viewG, this.viewS).subscribe({
      next: (res) => {
        this.cells.set(res.cells);
        this.galaxyLoading.set(false);
      },
      error: () => {
        this.cells.set([]);
        this.galaxyLoading.set(false);
      },
    });
  }

  targetCell(c: GalaxyCell): void {
    this.targetG = this.viewG;
    this.targetS = this.viewS;
    this.targetP = c.position;
    this.notify.info('Ziel gesetzt', `Koordinaten [${this.viewG}:${this.viewS}:${c.position}] uebernommen.`);
  }

  shipsTotal(f: Fleet): number {
    return Object.values(f.ships).reduce((a, b) => a + b, 0);
  }

  statusLabel(status: string): string {
    switch (status) {
      case 'flying':
        return 'im Anflug';
      case 'arrived':
        return 'am Ziel';
      case 'returning':
        return 'Rueckflug';
      default:
        return status;
    }
  }

  occupantLabel(c: GalaxyCell): string {
    switch (c.occupant_type) {
      case 'empty':
        return '— leer —';
      case 'player':
        return '👤 Spieler';
      case 'npc':
        return '🤖 NPC-Imperium';
      case 'planet':
        return '🪐 Planet';
      default:
        return c.occupant_type;
    }
  }

  shipMeta = (t: string) => metaFor(SHIP_META, t);
  missionMeta = (m: string) => metaFor(MISSION_META, m);
  rankMeta = (r: string) => metaFor(RANK_META, r);
}
