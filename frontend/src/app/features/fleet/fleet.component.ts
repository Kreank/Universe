import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import {
  Coordinate,
  Fleet,
  FleetMission,
  FleetSlots,
  IncomingAttack,
  StationedFleet,
} from '../../core/models/api.models';
import { MISSION_META, RESOURCE_META, SHIP_META, isMk2, metaFor } from '../../core/models/display';
import { fleetIcon, missionIcon, navIcon, shipIcon, statIcon, statusIcon } from '../../core/models/icon-assets';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { NotificationService } from '../../core/services/notification.service';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { FleetDispatchComponent } from '../../shared/components/fleet-dispatch.component';
import { FleetSlotsComponent } from '../../shared/components/fleet-slots.component';
import { fleetStyles } from './fleet.styles';

/**
 * Flotten-Verwaltung (W0: Bergbau-Stil). Reiner Verwaltungs-Screen — eingehende Angriffe,
 * laufende Flotten (Countdown + Rückruf) und stationierte Flotten (Modi + Rückruf).
 *
 * Das Verschicken läuft jetzt ausschließlich über das gemeinsame Versand-Overlay
 * (FleetDispatchComponent): „Flotte entsenden" öffnet es mit editierbarem Ziel + vollem
 * Missions-Satz, „Eigenes System patrouillieren" öffnet es im Patrouillen-Modus
 * (Schiffs-Picker + Radius → api.patrolHome). Das frühere Inline-Sendeformular samt
 * duplizierter Rechenlogik ist entfallen.
 */
@Component({
  selector: 'app-fleet',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DecimalPipe, RouterLink, CountdownComponent, BtnIconComponent, IconTileComponent, EmptyStateComponent, FleetDispatchComponent, FleetSlotsComponent],
  template: `
    <h1>Flotte</h1>

    <!-- Kapazitäts-Anzeige: belegte/freie Flotten-Slots + Aufschlüsselung nach Aktivität -->
    <app-fleet-slots [slots]="slots()" />

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

    <!-- Flottenkommando: Aktions-Leiste -> öffnet das gemeinsame Versand-Overlay -->
    <section class="card actions-card">
      <div class="panel-title"><app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="16" /> Flottenkommando</div>
      <div class="action-row">
        <button class="btn btn-primary" type="button" (click)="openSend('attack')">🚀 Flotte entsenden</button>
        <button class="btn btn-ghost" type="button"
          title="Stellt ausgewählte Schiffe als Abfang-Patrouille im eigenen System auf (kein Flug)."
          (click)="openPatrol()">
          <app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="18" /> Eigenes System patrouillieren
        </button>
      </div>
      <p class="muted small">Ziel & Mission (Angriff, Transport, Spionage, Stationierung, Abfangen, Eskorte, Recycling, Kolonisierung) wählst du im Versand-Dialog.</p>
    </section>

    <!-- Schiffe auf dem aktiven Planeten (Hangar/Garnison) -->
    <section class="card hangar">
      <div class="panel-title"><app-btn-icon [src]="navIcon('shipyard')" glyph="🛠️" [size]="16" /> Schiffe auf diesem Planeten</div>
      @if (hangarShips().length) {
        <div class="hangar-grid">
          @for (s of hangarShips(); track s.type) {
            <div class="hship" [attr.title]="shipMeta(s.type).label">
              <app-icon-tile [glyph]="shipMeta(s.type).glyph" [src]="shipIcon(s.type)" [size]="44" [mk2]="isMk2(s.type)" />
              <span class="hship-name">{{ shipMeta(s.type).label }}</span>
              <span class="hship-count mono">{{ s.count | number: '1.0-0' }}</span>
            </div>
          }
        </div>
      } @else {
        <app-empty-state art="empty_fleet">Keine Schiffe auf diesem Planeten. <a href="/shipyard">Zur Werft →</a></app-empty-state>
      }
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
        <p class="muted small">Keine stationierten Flotten. Im Versand-Dialog Mission „🚚 Stationierung", „📡 Abfangen" oder „🛡 Eskorte" wählen — oder „⚔ Eigenes System patrouillieren".</p>
      }
    </section>

    <p class="muted small galaxy-hint">
      🌌 Systeme scannen, Ziele aufklären und Schnellaktionen gibt's auf der
      <a routerLink="/galaxy">Galaxie-Karte →</a>
    </p>

    @if (sendOverlay(); as o) {
      <app-fleet-dispatch
        [target]="o.target"
        [editableTarget]="true"
        [initialMission]="o.mission"
        (sent)="onSent()"
        (close)="sendOverlay.set(null)"
      />
    }
    @if (patrolOverlay()) {
      <app-fleet-dispatch
        [patrolMode]="true"
        (sent)="onPatrolled()"
        (close)="patrolOverlay.set(false)"
      />
    }
  `,
  styles: [fleetStyles],
})
export class FleetComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly route = inject(ActivatedRoute);

  protected readonly incoming = signal<IncomingAttack[]>([]);
  protected readonly stationed = signal<StationedFleet[]>([]);
  protected readonly slots = signal<FleetSlots | null>(null);

  /** Offenes Versand-Overlay (editierbares Ziel) bzw. Patrouillen-Overlay. */
  protected readonly sendOverlay = signal<{ target: Coordinate | null; mission: FleetMission } | null>(null);
  protected readonly patrolOverlay = signal(false);

  protected readonly activeFleets = computed(() =>
    this.state.fleets().filter((f) => f.status !== 'returned'),
  );

  /** Schiffe auf dem aktiven Planeten (Hangar/Garnison) — Bestands-Übersicht. */
  protected readonly hangarShips = computed(() =>
    (this.state.activePlanet()?.ships ?? []).filter((s) => s.count > 0),
  );
  protected readonly shipIcon = shipIcon;
  protected readonly isMk2 = isMk2;

  constructor() {
    // Deep-Link aus der Galaxie-Ansicht: /fleet?g=&s=&p=&mission= -> Versand-Overlay vorbelegt öffnen.
    const qp = this.route.snapshot.queryParamMap;
    const g = qp.get('g');
    const s = qp.get('s');
    const p = qp.get('p');
    if (g && s && p) {
      const m = (qp.get('mission') as FleetMission | null) ?? 'attack';
      this.sendOverlay.set({
        target: { galaxy: Number(g), system: Number(s), position: Number(p) },
        mission: m,
      });
    }

    this.loadIncoming();
    this.loadStationed();
    this.loadSlots();
  }

  /** Slot-Kapazität (belegt/frei + Aufschlüsselung) frisch ziehen. */
  loadSlots(): void {
    this.api.getFleetSlots().subscribe({
      next: (s) => this.slots.set(s),
      error: () => this.slots.set(null),
    });
  }

  /** Versand-Overlay mit editierbarem Ziel öffnen (Ziel + Mission wählt der Spieler dort). */
  openSend(mission: FleetMission): void {
    this.sendOverlay.set({ target: null, mission });
  }

  /** Patrouillen-Overlay öffnen (Schiffs-Picker + Radius → eigenes System abfangen). */
  openPatrol(): void {
    this.patrolOverlay.set(true);
  }

  /** Nach erfolgreichem Versand: Overlay schließen + Listen frisch ziehen. */
  onSent(): void {
    this.sendOverlay.set(null);
    void this.state.reloadFleets();
    this.loadIncoming();
    this.loadStationed();
    this.loadSlots();
  }

  /** Nach erfolgreicher Patrouille: Overlay schließen + stationierte Flotten neu laden. */
  onPatrolled(): void {
    this.patrolOverlay.set(false);
    this.loadStationed();
    this.loadSlots();
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
        this.loadSlots();
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

  recall(fleetId: string): void {
    this.api.recallFleet(fleetId).subscribe({
      next: () => {
        this.notify.info('Rueckruf', 'Flotte kehrt zur Basis zurueck.');
        this.loadSlots();
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
  protected readonly statusIcon = statusIcon;
}
