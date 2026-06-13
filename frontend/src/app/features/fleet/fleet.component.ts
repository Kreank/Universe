import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import {
  Fleet,
  FleetMission,
  IncomingAttack,
  PlanetUnit,
  StationedFleet,
} from '../../core/models/api.models';
import { MISSION_META, RANK_META, SHIP_META, metaFor } from '../../core/models/display';
import { missionIcon } from '../../core/models/icon-assets';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { NotificationService } from '../../core/services/notification.service';
import { fleetStyles } from './fleet.styles';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';

@Component({
  selector: 'app-fleet',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink, CountdownComponent, IconTileComponent, BtnIconComponent, EmptyStateComponent],
  template: `
    <h1>Flotte</h1>

    @if (incoming().length) {
      <section class="card incoming">
        <div class="panel-title">🚨 Eingehende Angriffe</div>
        @for (a of incoming(); track a.id) {
          <div class="incoming-row">
            <div class="incoming-info">
              <span class="badge-threat">⚔️ {{ a.attacker }}</span>
              <span class="mono small">@if (a.origin) { von [{{ a.origin }}] } → [{{ a.target.galaxy }}:{{ a.target.system }}:{{ a.target.position }}]</span>
              <span class="chip">{{ a.ships_total }} Schiffe</span>
            </div>
            <app-countdown [target]="a.arrive_at" />
          </div>
        }
        <p class="hint small">Verstaerke deine Verteidigung oder evakuiere die Flotte (Fleetsave), bevor sie eintrifft.</p>
      </section>
    }

    <div class="grid layout">
      <!-- Flotte senden -->
      <section class="card send">
        <div class="panel-title">🚀 Flotte entsenden</div>

        <!-- Schiffsauswahl als dichtes, bild-zentriertes Kachel-Raster (OGame-Stil) -->
        <div class="grid ships-grid">
          @for (s of availableShips(); track s.type) {
            <div class="ship" [class.picked]="shipCount(s.type) > 0">
              <div class="ship-art">
                <app-icon-tile
                  [glyph]="shipMeta(s.type).glyph"
                  [src]="'assets/img/ships/' + s.type + '.png'"
                  [size]="70"
                />
                <span class="avail" title="vorhanden">{{ s.count }}</span>
              </div>
              <div class="ship-name">{{ shipMeta(s.type).label }}</div>
              <div class="ship-pick">
                <input
                  type="number"
                  min="0"
                  [max]="s.count"
                  [ngModel]="shipCount(s.type)"
                  (ngModelChange)="setShip(s.type, $event, s.count)"
                  aria-label="Menge"
                />
                <button
                  class="btn btn-ghost btn-sm"
                  type="button"
                  title="Alle auswaehlen"
                  (click)="setShip(s.type, s.count, s.count)"
                >
                  alle
                </button>
              </div>
            </div>
          } @empty {
            <p class="muted small empty-ships">Keine Schiffe auf diesem Planeten. <a href="/shipyard">Werft →</a></p>
          }
        </div>

        @if (prefilled()) {
          <p class="hint small">🎯 Ziel aus der Galaxie-Karte uebernommen: [{{ prefilled() }}]</p>
        }

        <!-- Auftrags-Leiste: Ziel, Mission, Tempo, Commander, Start -->
        <div class="order-bar">
          <div class="field coords">
            <label>Ziel (Galaxie : System : Position)</label>
            <div class="coord">
              <input type="number" min="1" [(ngModel)]="targetG" aria-label="Galaxie" />
              <span class="sep">:</span>
              <input type="number" min="1" [(ngModel)]="targetS" aria-label="System" />
              <span class="sep">:</span>
              <input type="number" min="1" [(ngModel)]="targetP" aria-label="Position" />
            </div>
          </div>

          <div class="field">
            <label>Mission</label>
            <select [ngModel]="missionSig()" (ngModelChange)="missionSig.set($event)">
              @for (m of missions; track m) {
                <option [value]="m">{{ missionMeta(m).glyph }} {{ missionMeta(m).label }}</option>
              }
            </select>
            @if (missionHint()) {
              <span class="hint small">{{ missionHint() }}</span>
            }
          </div>

          @if (missionSig() === 'intercept') {
            <div class="field">
              <label class="tip" data-tip="0 = nur das Zielsystem. Reichweite steigt mit Hyperraum-Interdiktion-Forschung (max 6).">Abfang-Radius {{ interceptRadius() }} Sys</label>
              <input type="number" min="0" max="6" [ngModel]="interceptRadius()" (ngModelChange)="interceptRadius.set(+$event || 0)" />
            </div>
          }

          <div class="field">
            <label class="tip" data-tip="Langsamer = weniger Sprit">Tempo {{ speed() }}%</label>
            <input type="range" min="10" max="100" step="10" [ngModel]="speed()" (ngModelChange)="speed.set($event)" />
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

          <div class="field send-field">
            <button class="btn btn-primary full" type="button" [disabled]="!canSend() || sending()" (click)="send()">
              {{ sending() ? 'Sende…' : '🚀 Flotte starten' }}
            </button>
            <button class="btn btn-ghost full" type="button"
              [disabled]="!hasSelection() || !state.activePlanetId() || sending()"
              title="Stellt die ausgewaehlten Schiffe sofort als Abfang-Patrouille im eigenen System auf (kein Flug)."
              (click)="patrolHome()">
              ⚔ Eigenes System patrouillieren
            </button>
            @if (!hasSelection()) {
              <span class="hint small">Mindestens ein Schiff auswaehlen.</span>
            }
          </div>
        </div>
      </section>

      <!-- Laufende Flotten -->
      <section class="card running">
        <div class="panel-title">🛰️ Laufende Flotten</div>
        @if (activeFleets().length) {
          @for (f of activeFleets(); track f.id) {
            <div class="fleet-row">
              <div class="fleet-info">
                <span class="badge-mission">@if (missionIcon(f.mission); as mi) {<img class="mission-ico" [src]="mi" alt="" (error)="hideImg($event)" />} @else {{{ missionMeta(f.mission).glyph }} }{{ missionMeta(f.mission).label }}</span>
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
          <app-empty-state art="empty_fleet">Keine Flotten unterwegs.</app-empty-state>
        }
      </section>

      <!-- Patrouillen (stationiert) -->
      <section class="card running">
        <div class="panel-title">🛡 Meine Patrouillen</div>
        @if (stationed().length) {
          @for (s of stationed(); track s.id) {
            <div class="fleet-row">
              <div class="fleet-info">
                <span class="mono small">[{{ s.coords }}]</span>
                <span class="chip">{{ s.ships_total }} Schiffe</span>
                @if (s.intercept_enabled) {
                  <span class="chip">⚔ Abfangen · Radius {{ s.intercept_radius }}</span>
                } @else {
                  <span class="chip muted">Abfangen aus</span>
                }
              </div>
              <div class="fleet-act">
                <button class="btn btn-danger btn-sm" type="button" (click)="recallPatrol(s)"><app-btn-icon [src]="missionIcon('return')" glyph="↩" /> Rueckruf</button>
              </div>
            </div>
          }
        } @else {
          <p class="muted small">Keine stationierten Patrouillen. Schiffe auswaehlen → „⚔ Eigenes System patrouillieren".</p>
        }
      </section>

    </div>

    <p class="muted small galaxy-hint">
      🌌 Systeme scannen, Ziele aufklären und Schnellaktionen gibt's auf der
      <a routerLink="/galaxy">Galaxie-Karte →</a>
    </p>
  `,
  styles: [fleetStyles],
})
export class FleetComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);

  protected readonly missions: FleetMission[] = [
    'attack', 'transport', 'spy', 'deploy', 'intercept', 'recycle', 'colonize', 'mine', 'expedition',
  ];

  // Pflicht-Schiff je Spezial-Mission (Backend erzwingt es; hier als Hinweis).
  private readonly missionRequires: Partial<Record<FleetMission, { type: string; label: string }>> = {
    spy: { type: 'spy_probe', label: 'Spionagesonde' },
    recycle: { type: 'recycler', label: 'Recycler' },
    colonize: { type: 'colony_ship', label: 'Kolonieschiff' },
    mine: { type: 'miner', label: 'Bergbauschiff' },
    expedition: { type: 'expedition_ship', label: 'Expeditions-Schiff' },
  };

  protected readonly incoming = signal<IncomingAttack[]>([]);
  protected readonly stationed = signal<StationedFleet[]>([]);

  // Sende-Formular
  protected readonly selection = signal<Record<string, number>>({});
  targetG = 1;
  targetS = 1;
  targetP = 1;
  commanderId: string | null = null;
  protected readonly speed = signal(100);
  protected readonly interceptRadius = signal(0);
  protected readonly sending = signal(false);

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

  // Hinweis auf das Pflicht-Schiff der gewaehlten Mission, falls noch nicht ausgewaehlt.
  protected readonly missionHint = computed<string | null>(() => {
    const req = this.missionRequires[this.missionSig()];
    if (!req) {
      return null;
    }
    return this.shipCount(req.type) > 0
      ? null
      : `Diese Mission benoetigt mindestens ein ${req.label}.`;
  });

  // Signal-Spiegel der Mission, damit missionHint reaktiv ist (ngModel schreibt das Feld).
  protected readonly missionSig = signal<FleetMission>('attack');

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
        this.missionSig.set(m);
      }
      this.prefilled.set(`${this.targetG}:${this.targetS}:${this.targetP}`);
    }

    this.loadIncoming();
    this.loadStationed();
  }

  loadStationed(): void {
    this.api.getStationed().subscribe({
      next: (rows) => this.stationed.set(rows),
      error: () => this.stationed.set([]),
    });
  }

  recallPatrol(s: StationedFleet): void {
    this.api.recallStation(s.id).subscribe({
      next: () => {
        this.notify.success('Rueckruf gestartet', `Patrouille von [${s.coords}] kehrt in die Garnison zurueck.`);
        this.loadStationed();
        void this.state.reloadFleets();
      },
      error: (err) => this.notify.warning('Rueckruf fehlgeschlagen', err?.error?.detail ?? 'Fehler.'),
    });
  }

  loadIncoming(): void {
    this.api.getIncomingAttacks().subscribe({
      next: (rows) => this.incoming.set(rows),
      error: () => this.incoming.set([]),
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
        mission: this.missionSig(),
        ships,
        cargo: { metal: 0, crystal: 0, deuterium: 0 },
        commander_id: this.commanderId,
        speed_pct: this.speed(),
        radius: this.missionSig() === 'intercept' ? this.interceptRadius() : undefined,
      })
      .subscribe({
        next: () => {
          this.sending.set(false);
          this.selection.set({});
          this.notify.success('Flotte gestartet', `Mission ${this.missionMeta(this.missionSig()).label} unterwegs.`);
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

  patrolHome(): void {
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
    this.api.patrolHome(origin, { ships, radius: 0 }).subscribe({
      next: () => {
        this.sending.set(false);
        this.selection.set({});
        this.notify.success('Patrouille aktiv', 'Deine Schiffe patrouillieren jetzt das eigene System.');
        void this.state.reloadActivePlanet();
        this.loadStationed();
      },
      error: (err) => {
        this.sending.set(false);
        this.notify.warning('Patrouille fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
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

  shipMeta = (t: string) => metaFor(SHIP_META, t);
  missionMeta = (m: string) => metaFor(MISSION_META, m);
  rankMeta = (r: string) => metaFor(RANK_META, r);
  protected readonly missionIcon = missionIcon;
  /** Blendet ein nicht ladbares Inline-Icon aus (Label bleibt sichtbar). */
  hideImg(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
}
