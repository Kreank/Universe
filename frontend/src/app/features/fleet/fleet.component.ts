import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { DecimalPipe } from '@angular/common';
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
import { MISSION_META, RANK_META, RESOURCE_META, SHIP_META, metaFor } from '../../core/models/display';
import { fleetIcon, missionIcon, navIcon, resourceIcon, statIcon, statusIcon, uiIcon } from '../../core/models/icon-assets';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { NotificationService } from '../../core/services/notification.service';
import { BalanceService } from '../../core/services/balance.service';
import { fleetStyles } from './fleet.styles';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';

@Component({
  selector: 'app-fleet',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, DecimalPipe, RouterLink, CountdownComponent, IconTileComponent, BtnIconComponent, EmptyStateComponent],
  template: `
    <h1>Flotte</h1>

    @if (incoming().length) {
      <section class="card incoming">
        <div class="panel-title"><app-btn-icon [src]="statusIcon('incoming_attack')" glyph="🚨" [size]="16" /> Eingehende Angriffe</div>
        @for (a of incoming(); track a.id) {
          <div class="incoming-row has-tip">
            <div class="incoming-info">
              <span class="badge-threat"><app-btn-icon [src]="fleetIcon()" glyph="⚔️" [size]="18" /> {{ a.attacker }}</span>
              <span class="mono small">@if (a.origin) { von [{{ a.origin }}] } → [{{ a.target.galaxy }}:{{ a.target.system }}:{{ a.target.position }}]</span>
              <span class="chip">@if ((a.intel_level ?? 1) < 2) {~}{{ a.ships_total }} Schiffe</span>
              <span class="chip muted">{{ missionMeta(a.mission ?? 'attack').label }}</span>
              <div class="fleet-tip" role="tooltip">
                <div class="tip-head">📡 Aufklaerung {{ a.intel_level ?? 1 }}/3 · {{ missionMeta(a.mission ?? 'attack').label }}</div>
                @if (a.ships) {
                  <div class="tip-sec">
                    <div class="tip-sec-title">Schiffe ({{ a.ships_total }})</div>
                    @for (e of shipEntries(a.ships); track e.label) {
                      <div class="tip-row"><span>{{ e.label }}</span><span class="mono">{{ e.count | number: '1.0-0' }}</span></div>
                    }
                  </div>
                } @else {
                  <div class="tip-sec"><div class="tip-row muted">Zusammensetzung unbekannt — Spionagetechnik Stufe 2 nötig.</div></div>
                }
                @if (a.cargo) {
                  @if (cargoEntries(a.cargo).length) {
                    <div class="tip-sec">
                      <div class="tip-sec-title">Fracht</div>
                      @for (e of cargoEntries(a.cargo); track e.label) {
                        <div class="tip-row"><span>{{ e.label }}</span><span class="mono">{{ e.amount | number: '1.0-0' }}</span></div>
                      }
                    </div>
                  } @else {
                    <div class="tip-sec"><div class="tip-row muted">Keine erbeutbare Fracht.</div></div>
                  }
                } @else {
                  <div class="tip-sec"><div class="tip-row muted">Fracht unbekannt — Spionagetechnik Stufe 4 nötig.</div></div>
                }
              </div>
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
        <div class="panel-title"><app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="16" /> Flotte entsenden</div>

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
          <p class="hint small"><app-btn-icon [src]="uiIcon('target')" glyph="🎯" [size]="14" /> Ziel aus der Galaxie-Karte uebernommen: [{{ prefilled() }}]</p>
        }

        <!-- Fracht (Transport / Stationierung) -->
        @if (showCargo() && hasSelection()) {
          <div class="cargo-box">
            <div class="cargo-head">
              <span>📦 Fracht</span>
              <button class="btn btn-ghost btn-sm" type="button" (click)="fillAll()"
                      [disabled]="cargoCapacity() <= 0">Alles laden</button>
            </div>
            <div class="cargo-grid">
              @for (rf of cargoFields; track rf.key) {
                <div class="cargo-field">
                  <label><img class="cargo-ico" [src]="resourceIcon(rf.key)" alt="" />{{ rf.label }}</label>
                  <div class="cargo-input">
                    <input type="number" min="0" [max]="cargoCapFor(rf.key)"
                           [ngModel]="cargo()[rf.key]" (ngModelChange)="setCargo(rf.key, $event)" />
                    <button class="btn btn-ghost btn-sm" type="button"
                            (click)="setCargo(rf.key, cargoCapFor(rf.key))">max</button>
                  </div>
                  <span class="avail-hint muted">Vorrat: {{ (planetRes()?.[rf.key]?.amount ?? 0) | number: '1.0-0' }}</span>
                </div>
              }
            </div>
          </div>
        }

        <!-- Flotten-Übersicht: Kapazität, Distanz, Sprit, Flugzeit -->
        @if (hasSelection()) {
          <div class="fleet-summary">
            <div class="cap" [class.over]="cargoOver()">
              <div class="cap-line">
                <span>📦 Fracht {{ cargoUsed() | number: '1.0-0' }} / {{ cargoCapacity() | number: '1.0-0' }}</span>
                <span class="muted small">frei {{ cargoFree() | number: '1.0-0' }}</span>
              </div>
              <div class="cap-bar" [class.over]="cargoOver()"><span [style.width.%]="cargoPct()"></span></div>
              @if (cargoOver()) { <span class="hint small">Überladen — reduziere die Fracht oder nimm mehr Frachtraum mit.</span> }
            </div>
            @if (routeSummary(); as rs) {
              <div class="route-chips small">
                <span class="tip" data-tip="Distanz (OGame-Distanzmodell)">📏 {{ rs.distance.toLocaleString('de-DE') }}</span>
                <span class="tip" data-tip="Treibstoff (Deuterium) vom Startplaneten"><img class="cargo-ico" [src]="resourceIcon('deuterium')" alt="" />{{ rs.fuel.toLocaleString('de-DE') }} {{ rs.roundTrip ? '(Hin+Rück)' : '(einfach)' }}</span>
                <span class="tip" data-tip="Geschätzte Flugzeit je Strecke (Tempo-Regler wirkt; ohne Antriebsforschung konservativ)"><app-btn-icon [src]="uiIcon('time')" glyph="⏱" [size]="14" /> ca. {{ rs.flightText }}{{ rs.roundTrip ? ' / Strecke' : '' }}</span>
              </div>
            }
          </div>
        }

        <!-- Auftrags-Leiste: Ziel, Mission, Tempo, Commander, Start -->
        <div class="order-bar">
          <div class="field coords">
            <label>Ziel (Galaxie : System : Position)</label>
            <div class="coord">
              <input type="number" min="1" [ngModel]="targetG()" (ngModelChange)="targetG.set(+$event || 1)" aria-label="Galaxie" />
              <span class="sep">:</span>
              <input type="number" min="1" [ngModel]="targetS()" (ngModelChange)="targetS.set(+$event || 1)" aria-label="System" />
              <span class="sep">:</span>
              <input type="number" min="1" [ngModel]="targetP()" (ngModelChange)="targetP.set(+$event || 1)" aria-label="Position" />
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

          @if (missionSig() === 'escort') {
            <div class="field">
              <label class="tip" data-tip="Wie viele Systeme um das Stationssystem dein Geleitschutz-Angebot Handelsrouten deckt.">Eskort-Radius {{ escortRadius() }} Sys</label>
              <input type="number" min="0" max="50" [ngModel]="escortRadius()" (ngModelChange)="escortRadius.set(+$event || 0)" />
            </div>
            <div class="field">
              <label class="tip" data-tip="Dein Anteil am Frachtwert, den der Trader als Deuterium zahlt (max. 10 %).">Gebühr {{ escortFeePct() }} %</label>
              <input type="number" min="0" max="10" step="0.5" [ngModel]="escortFeePct()" (ngModelChange)="escortFeePct.set(+$event || 0)" />
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
              <app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="18" /> Eigenes System patrouillieren
            </button>
            @if (!hasSelection()) {
              <span class="hint small">Mindestens ein Schiff auswaehlen.</span>
            }
          </div>
        </div>
      </section>

      <!-- Laufende Flotten -->
      <section class="card running">
        <div class="panel-title"><app-btn-icon [src]="navIcon('fleet')" glyph="🛰️" [size]="16" /> Laufende Flotten</div>
        @if (activeFleets().length) {
          @for (f of activeFleets(); track f.id) {
            <div class="fleet-row has-tip">
              <div class="fleet-info">
                <span class="badge-mission"><app-btn-icon [src]="fleetIcon()" glyph="🚀" [size]="20" /> {{ missionMeta(f.mission).label }}</span>
                <span class="mono small">→ [{{ f.target.galaxy }}:{{ f.target.system }}:{{ f.target.position }}]</span>
                <span class="chip">{{ shipsTotal(f) }} Schiffe · {{ statusLabel(f.status) }}</span>
                <div class="fleet-tip" role="tooltip">
                  <div class="tip-head"><app-btn-icon [src]="fleetIcon()" glyph="🚀" [size]="14" /> {{ missionMeta(f.mission).label }} → [{{ f.target.galaxy }}:{{ f.target.system }}:{{ f.target.position }}]</div>
                  <div class="tip-sec">
                    <div class="tip-sec-title">Schiffe ({{ shipsTotal(f) }})</div>
                    @for (e of shipEntries(f.ships); track e.label) {
                      <div class="tip-row"><span>{{ e.label }}</span><span class="mono">{{ e.count | number: '1.0-0' }}</span></div>
                    }
                  </div>
                  @if (cargoEntries(f.cargo).length) {
                    <div class="tip-sec">
                      <div class="tip-sec-title">Fracht</div>
                      @for (e of cargoEntries(f.cargo); track e.label) {
                        <div class="tip-row"><span>{{ e.label }}</span><span class="mono">{{ e.amount | number: '1.0-0' }}</span></div>
                      }
                    </div>
                  } @else {
                    <div class="tip-sec"><div class="tip-row muted">Keine Fracht</div></div>
                  }
                </div>
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
          <app-empty-state art="empty_fleet" [fill]="true">Keine Flotten unterwegs.</app-empty-state>
        }
      </section>

      <!-- Stationierte Flotten (genau ein Modus je Flotte: Geparkt / Abfangen / Eskorte) -->
      <section class="card running">
        <div class="panel-title"><app-btn-icon [src]="statIcon('shield')" glyph="🛡" [size]="16" /> Stationierte Flotten</div>
        @if (stationed().length) {
          @for (s of stationed(); track s.id) {
            <div class="fleet-row">
              <div class="fleet-info">
                <span class="mono small">[{{ s.coords }}]</span>
                <span class="chip">{{ s.ships_total }} Schiffe</span>
                @switch (s.mode) {
                  @case ('intercept') {
                    <span class="chip"><app-btn-icon [src]="'assets/img/buildings/sensorphalanx.png'" glyph="⚔" [size]="14" /> Abfangen · Radius {{ s.intercept_radius }}</span>
                  }
                  @case ('escort') {
                    <span class="chip"><app-btn-icon [src]="statIcon('shield')" glyph="🛡" [size]="14" /> Eskorte · Radius {{ s.escort_radius }} · {{ (s.escort_fee_pct * 100).toFixed(1) }} %</span>
                  }
                  @default {
                    <span class="chip muted"><app-btn-icon [src]="missionIcon('deploy')" glyph="🚚" [size]="14" /> Geparkt</span>
                  }
                }
              </div>
              <div class="fleet-act">
                <button class="btn btn-danger btn-sm" type="button" (click)="recallPatrol(s)"><app-btn-icon [src]="missionIcon('return')" glyph="↩" /> Rueckruf</button>
              </div>
            </div>
          }
        } @else {
          <p class="muted small">Keine stationierten Flotten. Mission „🚚 Stationierung", „📡 Abfangen" oder „🛡 Eskorte" wählen — oder Schiffe auswählen → „⚔ Eigenes System patrouillieren".</p>
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
  private readonly balance = inject(BalanceService);

  protected readonly missions: FleetMission[] = [
    'attack', 'transport', 'spy', 'deploy', 'intercept', 'escort', 'recycle', 'colonize', 'mine', 'expedition',
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
  protected readonly targetG = signal(1);
  protected readonly targetS = signal(1);
  protected readonly targetP = signal(1);
  commanderId: string | null = null;
  // Fracht (Transport/Stationierung), wird in send() mitgeschickt.
  protected readonly cargo = signal<{ metal: number; crystal: number; deuterium: number }>({
    metal: 0, crystal: 0, deuterium: 0,
  });
  protected readonly cargoFields: { key: 'metal' | 'crystal' | 'deuterium'; label: string }[] = [
    { key: 'metal', label: 'Metall' },
    { key: 'crystal', label: 'Kristall' },
    { key: 'deuterium', label: 'Deuterium' },
  ];
  protected readonly speed = signal(100);
  protected readonly interceptRadius = signal(0);
  protected readonly escortRadius = signal(5);
  protected readonly escortFeePct = signal(2); // Prozent (0..10), Backend deckelt
  protected readonly sending = signal(false);

  // Nur entsendbare Schiffe: count > 0 UND mit Antrieb (stationaere Einheiten wie der
  // Solarsatellit haben speed 0 und bleiben in der Umlaufbahn -> nicht waehlbar).
  protected readonly availableShips = computed<PlanetUnit[]>(() => {
    const ships = this.balance.value?.ships as Record<string, { speed?: number }> | undefined;
    return (
      this.state.activePlanet()?.ships?.filter(
        (s) => s.count > 0 && (ships?.[s.type]?.speed ?? 1) > 0,
      ) ?? []
    );
  });

  protected readonly assignableCommanders = computed(() =>
    this.state.commanders().filter((c) => c.status !== 'training' && !c.assigned_fleet_id),
  );

  protected readonly activeFleets = computed(() =>
    this.state.fleets().filter((f) => f.status !== 'returned'),
  );

  protected readonly hasSelection = computed(() =>
    Object.values(this.selection()).some((n) => n > 0),
  );

  protected readonly canSend = computed(
    () => this.hasSelection() && !!this.state.activePlanetId() && !this.cargoOver(),
  );

  // Hinweis auf das Pflicht-Schiff der gewaehlten Mission, falls noch nicht ausgewaehlt.
  protected readonly missionHint = computed<string | null>(() => {
    const m = this.missionSig();
    if (m === 'deploy') {
      return 'Parkt die Flotte passiv am Ziel — fängt nichts ab, bietet keine Eskorte.';
    }
    if (m === 'intercept') {
      return 'Stationiert als aktive Patrouille, die durchreisende Feindflotten abfängt.';
    }
    if (m === 'escort') {
      return 'Stationiert als Geleitschutz-Angebot für Trader (fängt selbst nicht ab).';
    }
    const req = this.missionRequires[m];
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
      this.targetG.set(Number(g));
      this.targetS.set(Number(s));
      this.targetP.set(Number(p));
      const m = qp.get('mission') as FleetMission | null;
      if (m && this.missions.includes(m)) {
        this.missionSig.set(m);
      }
      this.prefilled.set(`${this.targetG()}:${this.targetS()}:${this.targetP()}`);
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

  // -- Fracht + Flotten-Übersicht (OGame-artig) --------------------------------
  private bnum(v: unknown, d = 0): number {
    return typeof v === 'number' ? v : d;
  }

  protected readonly showCargo = computed(
    () => this.missionSig() === 'transport' || this.missionSig() === 'deploy',
  );
  protected readonly planetRes = computed(() => this.state.activePlanet()?.resources ?? null);

  /** Gesamte Frachtkapazität der gewählten Flotte (Summe ship.cargo × Anzahl). */
  protected readonly cargoCapacity = computed(() => {
    const ships = this.balance.value?.ships as Record<string, { cargo?: number }> | undefined;
    let cap = 0;
    for (const [type, n] of Object.entries(this.selection())) {
      if (n > 0) cap += this.bnum(ships?.[type]?.cargo) * n;
    }
    return cap;
  });

  protected readonly cargoUsed = computed(() => {
    const c = this.cargo();
    return this.bnum(c.metal) + this.bnum(c.crystal) + this.bnum(c.deuterium);
  });
  protected readonly cargoFree = computed(() => Math.max(0, this.cargoCapacity() - this.cargoUsed()));
  protected readonly cargoOver = computed(() => this.cargoUsed() > this.cargoCapacity());
  protected readonly cargoPct = computed(() => {
    const cap = this.cargoCapacity();
    return cap > 0 ? Math.min(100, (this.cargoUsed() / cap) * 100) : 0;
  });

  /** Max. beladbare Menge je Ressource = min(Vorrat am Planeten, freie Flotten-Kapazität). */
  cargoCapFor(key: 'metal' | 'crystal' | 'deuterium'): number {
    const res = this.planetRes();
    const avail = res ? Math.floor(this.bnum(res[key]?.amount)) : Infinity;
    const c = this.cargo();
    const others = this.bnum(c.metal) + this.bnum(c.crystal) + this.bnum(c.deuterium) - this.bnum(c[key]);
    const room = Math.max(0, this.cargoCapacity() - others);
    return Math.max(0, Math.min(avail, room));
  }

  setCargo(key: 'metal' | 'crystal' | 'deuterium', value: number): void {
    const n = Math.max(0, Math.min(this.cargoCapFor(key), Math.floor(value || 0)));
    this.cargo.update((c) => ({ ...c, [key]: n }));
  }

  /** „Alles laden": füllt Metall→Kristall→Deuterium bis zur Gesamtkapazität (so viel wie da ist). */
  fillAll(): void {
    this.cargo.set({ metal: 0, crystal: 0, deuterium: 0 });
    for (const key of ['metal', 'crystal', 'deuterium'] as const) {
      this.setCargo(key, this.cargoCapFor(key));
    }
  }

  private distanceTo(): number | null {
    const p = this.state.activePlanet();
    const bal = this.balance.value as { fleet?: { distance?: Record<string, number> } } | undefined;
    const d = bal?.fleet?.distance;
    if (!p || !d) return null;
    const g = this.targetG(), s = this.targetS(), pos = this.targetP();
    if (p.galaxy !== g) return this.bnum(d['inter_galaxy_per_galaxy']) * Math.abs(p.galaxy - g);
    if (p.system !== s) return this.bnum(d['same_galaxy_base']) + this.bnum(d['same_galaxy_per_system']) * Math.abs(p.system - s);
    if (p.position !== pos) return this.bnum(d['same_system_base']) + this.bnum(d['same_system_per_position']) * Math.abs(p.position - pos);
    return this.bnum(d['same_position']);
  }

  /** Übersicht: Distanz, Sprit (Hin+Rück außer deploy), geschätzte Flugzeit je Strecke. */
  protected readonly routeSummary = computed(() => {
    const sel = Object.entries(this.selection()).filter(([, n]) => n > 0);
    const dist = this.distanceTo();
    if (!sel.length || dist === null) return null;
    const bal = this.balance.value as any;
    const roundTrip = this.missionSig() !== 'deploy';
    const legs = roundTrip ? 2 : 1;
    let fuelSum = 0;
    let slowest = Infinity;
    for (const [type, n] of sel) {
      fuelSum += this.bnum(bal?.ships?.[type]?.fuel) * n;
      const sp = this.bnum(bal?.ships?.[type]?.speed);
      if (sp > 0 && sp < slowest) slowest = sp;
    }
    const f = bal?.fleet;
    const fuel = Math.max(1, Math.ceil((fuelSum * dist) / this.bnum(f?.speed_factor, 1) * this.bnum(f?.fuel_per_distance_unit, 1) * legs));
    let secsText = '–';
    if (isFinite(slowest) && slowest > 0) {
      const fleetSpeed = Math.max(0.01, this.bnum(bal?.universe?.fleet_speed, 1));
      const pct = Math.max(1, this.speed());
      const s = Math.round((10 + (35000 / pct) * Math.sqrt((dist * 10) / slowest)) / fleetSpeed);
      const h = Math.floor(s / 3600), m = Math.floor((s % 3600) / 60), sec = s % 60;
      secsText = (h ? `${h}h ` : '') + (h || m ? `${m}m ` : '') + `${sec}s`;
    }
    return { distance: dist, fuel, roundTrip, flightText: secsText };
  });

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
        target: { galaxy: this.targetG(), system: this.targetS(), position: this.targetP() },
        mission: this.missionSig(),
        ships,
        cargo: this.showCargo() ? this.cargo() : { metal: 0, crystal: 0, deuterium: 0 },
        commander_id: this.commanderId,
        speed_pct: this.speed(),
        radius: this.missionSig() === 'intercept' ? this.interceptRadius() : undefined,
        escort_radius: this.missionSig() === 'escort' ? this.escortRadius() : undefined,
        escort_fee_pct: this.missionSig() === 'escort' ? this.escortFeePct() / 100 : undefined,
      })
      .subscribe({
        next: () => {
          this.sending.set(false);
          this.selection.set({});
          this.cargo.set({ metal: 0, crystal: 0, deuterium: 0 });
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
  resMeta = (r: string) => metaFor(RESOURCE_META, r);

  /** Schiffs-Zusammensetzung als sortierte Label/Anzahl-Liste (groesste Gruppe zuerst). */
  shipEntries(ships: Record<string, number> | null | undefined): { label: string; count: number }[] {
    if (!ships) return [];
    return Object.entries(ships)
      .filter(([, c]) => (c ?? 0) > 0)
      .map(([t, c]) => ({ label: this.shipMeta(t).label, count: c as number }))
      .sort((a, b) => b.count - a.count);
  }

  /** Fracht als Label/Menge-Liste (nur Ressourcen mit Menge > 0). */
  cargoEntries(cargo: Record<string, number> | null | undefined): { label: string; amount: number }[] {
    if (!cargo) return [];
    return Object.entries(cargo)
      .filter(([, v]) => (v ?? 0) > 0)
      .map(([k, v]) => ({ label: this.resMeta(k).label, amount: v as number }));
  }

  protected readonly fleetIcon = fleetIcon;
  protected readonly missionIcon = missionIcon;
  protected readonly navIcon = navIcon;
  protected readonly statIcon = statIcon;
  protected readonly resourceIcon = resourceIcon;
  protected readonly statusIcon = statusIcon;
  protected readonly uiIcon = uiIcon;
  /** Blendet ein nicht ladbares Inline-Icon aus (Label bleibt sichtbar). */
  hideImg(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
}
