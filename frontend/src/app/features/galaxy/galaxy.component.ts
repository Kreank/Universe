import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { GameStateService } from '../../core/services/game-state.service';
import {
  Coordinate,
  FleetMission,
  AllianceZone,
  GalaxyCell,
  GalaxyIntel,
  GalaxyTarget,
} from '../../core/models/api.models';
import { NotificationService } from '../../core/services/notification.service';
import { DEFENSE_META, RESOURCE_META, SHIP_META, metaFor } from '../../core/models/display';
import { missionIcon, navIcon, uiIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { FleetDispatchComponent } from '../../shared/components/fleet-dispatch.component';
import { MessageComposeComponent } from '../../shared/components/message-compose.component';
import { PhalanxPanelComponent } from '../../shared/components/phalanx-panel.component';
import { ShortNumberPipe } from '../../shared/pipes/short-number.pipe';
import { galaxyStyles } from './galaxy.styles';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';

/** Offenes Versand-Overlay (Schnellangriff / Schnelltransport / …). */
interface DispatchCtx {
  target: Coordinate;
  name: string | null;
  mission: FleetMission;
  targetType?: 'moon' | 'station' | 'mining_fleet';
}

/**
 * Galaxie-/Kartenansicht (UX-Doku 11 §2). Kompakte OGame-artige Positions-Liste
 * mit Inline-Schnellaktionen direkt am Ziel:
 * - 🛰 Schnell-Spionage: schickt sofort Sonden (kein Tab-Wechsel).
 * - ⚔ Angriff / 🚚 Transport: oeffnen ein kompaktes Versand-Overlay am Ziel.
 *
 * "aufgeklaert" = Auto-Discovery: NPCs, die nahe (<= balance auto_discover_radius
 * Systeme) deines Planeten spawnen, werden gratis mit Basis-Intel sichtbar.
 */
@Component({
  selector: 'app-galaxy',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, DatePipe, ShortNumberPipe, BtnIconComponent, FleetDispatchComponent, MessageComposeComponent, PhalanxPanelComponent, EmptyStateComponent],
  template: `
    <h1>Galaxie · Karte</h1>
    <p class="sub">Erkunde Systeme, finde Ziele und entsende deine Flotten — Schnellaktionen direkt am Ziel.</p>

    <div class="grid layout">
      <!-- System-Scanner ------------------------------------------------ -->
      <section class="card scanner">
        <div class="panel-title"><app-btn-icon [src]="navIcon('map')" glyph="🌌" [size]="16" /> System-Scanner</div>

        <div class="gx-nav">
          <button class="btn btn-sm" type="button" (click)="stepSystem(-1)" aria-label="System zurueck">◀</button>
          <div class="coordbox">
            <label>Galaxie</label>
            <input type="number" min="1" [max]="maxG()" [ngModel]="viewG"
                   (ngModelChange)="viewG = $event; clampOnInput()" />
          </div>
          <div class="coordbox">
            <label>System</label>
            <input type="number" min="1" [max]="maxS()" [ngModel]="viewS"
                   (ngModelChange)="viewS = $event; clampOnInput()" />
          </div>
          <button class="btn btn-sm" type="button" (click)="stepSystem(1)" aria-label="System vor">▶</button>
          <button class="btn btn-primary btn-sm" type="button" (click)="scan()">Scannen</button>
          <button class="btn btn-ghost btn-sm" type="button" (click)="goHome()"><app-btn-icon [src]="uiIcon('home')" glyph="⌂" [size]="16" /> Heimat</button>
        </div>

        <div class="coords-current mono">[{{ viewG }}:{{ viewS }}] · {{ scannedCount() }} belegt</div>

        @if (zones().length) {
          <div class="zone-banner">
            @for (z of zones(); track z.alliance_id) {
              <span class="zone-chip" [class.mine]="z.mine"
                    [title]="(z.mine ? 'Einflusszone deiner Allianz' : 'Fremde Einflusszone') + ' [' + z.tag + '] · Zentrum System ' + z.center_system + ' · Radius ' + z.radius">
                <img class="zone-mark" src="assets/img/status/alliance_zone.png" alt="" aria-hidden="true" />
                <span class="zone-tag">[{{ z.tag }}]</span>
                <span class="small muted">{{ z.mine ? 'eigene Zone' : 'Einflusszone' }}</span>
              </span>
            }
          </div>
        }

        @if (loading()) {
          <p class="muted small">Scanne System…</p>
        } @else {
          <div class="positions">
            @for (c of cells(); track c.position) {
              <div class="row" [class]="rowClass(c)">
                <span class="pos mono">{{ c.position }}</span>
                <div class="vis">
                  @if (cellImage(c); as img) {
                    <img class="vis-img" [src]="img" [alt]="occupantLabel(c)" loading="lazy" />
                  } @else {
                    <span class="vis-dot" aria-hidden="true"></span>
                  }
                </div>
                <div class="info">
                  <span class="kind">{{ occupantLabel(c) }}</span>
                  @if (c.name) { <span class="name">{{ c.name }}</span> }
                  @if (c.trade; as tr) {
                    <span class="chip trade tip" [attr.data-tip]="tradeTip(tr, c.player_name)"><app-btn-icon [src]="navIcon('market')" glyph="💱" [size]="14" /> {{ tr.offer }}→{{ tr.want }}{{ tr.rate ? ' @' + tr.rate : '' }}</span>
                  }
                  @if (c.asteroid; as a) {
                    <span class="chip rock tip" [attr.data-tip]="asteroidTip(a)"><app-btn-icon [src]="missionIcon('mine')" glyph="⛏" [size]="14" /> {{ a.metal | shortNumber }}M / {{ a.crystal | shortNumber }}K</span>
                  }
                  @if (c.moon; as m) {
                    <span class="chip moon tip" [attr.data-tip]="m.own ? 'Dein Mond' : ('Mond von ' + (m.player_name ?? 'Spieler') + ' — angreifbar/spionierbar')"><app-btn-icon [src]="'assets/img/backgrounds/moon.png'" glyph="🌙" [size]="14" /> {{ m.name }}</span>
                  }
                  @if (c.station; as st) {
                    <span class="chip station tip" [class.mine]="st.mine" [attr.data-tip]="st.mine ? ('Allianz-Station deiner Allianz [' + st.tag + '] · Hülle ' + st.hp_pct + '%') : ('Fremde Allianz-Station [' + st.tag + '] — belagerbar (≥2 Angreifer) · Resthülle ' + st.hp_pct + '%')"><app-btn-icon [src]="'assets/img/alliance/alliance_station.png'" glyph="🛰" [size]="14" /> [{{ st.tag }}] {{ st.hp_pct }}%</span>
                  }
                  @if (c.mining_fleet; as mf) {
                    <span class="chip rock tip" [attr.data-tip]="mf.mine ? ('Deine Bergbauflotte schürft hier (' + mf.ships_total + ' Schiffe)') : ('Fremde Bergbauflotte von ' + (mf.owner ?? 'Spieler') + ' schürft hier — angreifbar, Fracht erbeutbar (' + mf.ships_total + ' Schiffe)')"><app-btn-icon [src]="missionIcon('mine')" glyph="⛏" [size]="14" /> Flotte{{ mf.mine ? '' : ' [' + (mf.owner ?? '?') + ']' }}</span>
                  }
                  @if (c.event; as ev) {
                    <span class="chip event tip" [attr.data-tip]="eventTip(ev)">{{ eventGlyph(ev.event_type) }} {{ eventLabel(ev.event_type) }} · {{ eventCountdown(ev.expires_at) }}</span>
                  }
                </div>
                @if (c.asteroid) {
                  <div class="acts">
                    <button class="ic mine" type="button" (click)="openDispatch(cellCoord(c), 'Asteroidenfeld', 'mine')" title="Hier Erz abbauen (Bergbauschiff nötig)"><app-btn-icon [src]="missionIcon('mine')" glyph="⛏" [size]="18" /></button>
                  </div>
                }
                @if (c.event; as ev) {
                  <div class="acts">
                    @if (ev.event_type === 'cosmic_anomaly') {
                      <button class="ic spy" type="button" (click)="openDispatch(cellCoord(c), 'Anomalie', 'spy')" title="Spionagesonde schicken → Forschungstempo-Buff"><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="18" /></button>
                    }
                    @if (ev.event_type === 'utopia_shipyard' || ev.event_type === 'black_market') {
                      <button class="ic trp" type="button" (click)="openDispatch(cellCoord(c), eventLabel(ev.event_type), 'transport')" title="Per Transport liefern/handeln"><app-btn-icon [src]="missionIcon('transport')" glyph="🚚" [size]="18" /></button>
                    }
                  </div>
                }
                @if (c.moon; as m) {
                  @if (!m.own) {
                    <div class="acts">
                      <button class="ic spy" type="button" (click)="openDispatch(cellCoord(c), m.name, 'spy', 'moon')" title="Mond spionieren"><app-btn-icon [src]="missionIcon('spy')" glyph="🌙🛰" [size]="18" /></button>
                      <button class="ic atk" type="button" (click)="openDispatch(cellCoord(c), m.name, 'attack', 'moon')" title="Mond angreifen"><app-btn-icon [src]="missionIcon('attack')" glyph="🌙⚔" [size]="18" /></button>
                    </div>
                  }
                }
                @if (c.station; as st) {
                  @if (!st.mine && st.status !== 'destroyed') {
                    <div class="acts">
                      <button class="ic atk" type="button" (click)="openDispatch(cellCoord(c), 'Allianz-Station [' + st.tag + ']', 'attack', 'station')" title="Allianz-Station belagern — chippt die Hülle; zur Zerstörung ≥2 verschiedene Angreifer nötig"><app-btn-icon [src]="missionIcon('attack')" glyph="🛰⚔" [size]="18" /></button>
                    </div>
                  }
                }
                @if (c.mining_fleet; as mf) {
                  @if (!mf.mine) {
                    <div class="acts">
                      <button class="ic atk" type="button" (click)="openDispatch(cellCoord(c), '⛏ Flotte [' + (mf.owner ?? '?') + ']', 'attack', 'mining_fleet')" title="Schürfende Bergbauflotte angreifen — bei Sieg wird ihre Fracht (Erz + Exoten) erbeutet"><app-btn-icon [src]="missionIcon('attack')" glyph="⛏⚔" [size]="18" /></button>
                    </div>
                  }
                }
                @if (isHostile(c)) {
                  <div class="acts">
                    @if (c.discovered) {
                      <span class="chip disc tip" data-tip="Automatisch aufgeklärt: spawnte nahe deinem Planeten (≤ 8 Systeme). Sende eine Sonde für tiefere/aktuellere Daten."><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="14" /> aufgeklärt</span>
                    }
                    @if (c.occupant_type === 'player' && c.player_id) {
                      <button class="ic msg" type="button" (click)="messagePlayer(c)" title="Nachricht an Spieler"><app-btn-icon [src]="navIcon('mail')" glyph="✉" [size]="18" /></button>
                    }
                    <button class="ic phx" type="button" (click)="phalanxTarget.set(cellCoord(c))" title="Sensorphalanx-Scan (Flottenbewegungen)"><app-btn-icon [src]="'assets/img/buildings/sensorphalanx.png'" glyph="📡" [size]="18" /></button>
                    <button class="ic spy" type="button" (click)="quickSpy(cellCoord(c), c.name)" [title]="spyTitle()"><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="18" /></button>
                    <button class="ic atk" type="button" (click)="openDispatch(cellCoord(c), c.name, 'attack')" title="Angreifen"><app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="18" /></button>
                    <button class="ic trp" type="button" (click)="openDispatch(cellCoord(c), c.name, 'transport')" [title]="c.trade ? 'Transport (P2P-Handel: Ware schicken)' : 'Transport'"><app-btn-icon [src]="missionIcon('transport')" glyph="🚚" [size]="18" /></button>
                  </div>
                } @else if (isOwn(c)) {
                  <span class="chip own">dein Planet</span>
                } @else if (c.occupant_type === 'deep_space') {
                  <div class="acts">
                    <button class="ic exp" type="button" (click)="openDispatch(cellCoord(c), c.name, 'expedition')" title="Expedition in die galaktischen Weiten (Expeditionsschiff + Astrophysik nötig)"><app-btn-icon [src]="missionIcon('expedition')" glyph="🌌" [size]="18" /></button>
                  </div>
                } @else if (c.occupant_type === 'empty' && !c.station) {
                  <div class="acts">
                    <button class="ic col" type="button" (click)="openDispatch(cellCoord(c), null, 'colonize')" title="Hier kolonisieren (Kolonieschiff nötig)"><app-btn-icon [src]="missionIcon('colonize')" glyph="🌱" [size]="18" /></button>
                  </div>
                }
              </div>
            }
          </div>
        }
      </section>

      <!-- Ziel-Verzeichnis ---------------------------------------------- -->
      <section class="card targets">
        <div class="panel-title"><app-btn-icon [src]="uiIcon('target')" glyph="🎯" [size]="16" /> Aufgeklärte Ziele</div>
        @if (targets().length) {
          <ul class="tgt-list">
            @for (t of targets(); track t.coords) {
              <li class="tgt">
                <div class="tgt-top">
                  <span class="tgt-name">{{ t.name }}</span>
                  <span class="chip lvl">L{{ t.level ?? 1 }}/3</span>
                  @if (t.intel?.trade_center) {
                    <span class="chip trade tip" data-tip="Neutrales Handelszentrum (unangreifbar) · globaler Handelskurs">Handelszentrum</span>
                  } @else if (t.intel?.merchant) {
                    <span class="chip trade tip" [attr.data-tip]="'Händler · Spez.: ' + (t.intel?.spec ?? '?') + ' — handeln statt kämpfen'">Händler</span>
                  }
                  <span class="tgt-coords mono">[{{ t.coords }}]</span>
                </div>
                <div class="tgt-sub small">
                  <span class="tgt-stat tip" [attr.data-tip]="intelTip(t)">
                    <app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="14" /> {{ t.ships_total }}
                  </span>
                  <span class="tgt-stat">
                    <app-btn-icon [src]="'assets/img/icons/spec/stat_shield.png'" glyph="🛡" [size]="14" /> {{ t.defenses_total }}
                  </span>
                  @if (t.discovered_at) {
                    <span class="faint">· {{ t.discovered_at | date: 'short' }}</span>
                  }
                </div>
                <div class="acts tgt-acts">
                  <button class="ic" type="button" (click)="jumpTo(t)" title="Im Scanner zeigen"><app-btn-icon [src]="navIcon('map')" glyph="🌌" [size]="18" /></button>
                  <button class="ic spy" type="button" (click)="quickSpy(targetCoord(t), t.name)" title="Spionieren"><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="18" /></button>
                  <button class="ic phx" type="button" (click)="phalanxTarget.set(targetCoord(t))" title="Sensorphalanx-Scan"><app-btn-icon [src]="'assets/img/buildings/sensorphalanx.png'" glyph="📡" [size]="18" /></button>
                  <button class="ic trp" type="button" (click)="openDispatch(targetCoord(t), t.name, 'transport')" title="Transport"><app-btn-icon [src]="missionIcon('transport')" glyph="🚚" [size]="18" /></button>
                  @if (t.intel?.merchant) {
                    <button class="ic trd" type="button" (click)="openDispatch(targetCoord(t), t.name, 'trade')" title="Handeln"><app-btn-icon [src]="navIcon('market')" glyph="💱" [size]="18" /></button>
                  }
                  @if (t.npc_id && !t.intel?.trade_center) {
                    <button class="ic atk" type="button" (click)="openDispatch(targetCoord(t), t.name, 'attack')" title="Angreifen"><app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="18" /></button>
                  }
                </div>
              </li>
            }
          </ul>
        } @else {
          <app-empty-state art="empty_search">
            Noch keine Ziele aufgeklärt. Entsende Spionagesonden (🛰) auf belegte Felder im Scanner.
          </app-empty-state>
        }
      </section>
    </div>

    @if (dispatch(); as d) {
      <app-fleet-dispatch
        [target]="d.target"
        [targetName]="d.name"
        [initialMission]="d.mission"
        [targetType]="d.targetType ?? null"
        (sent)="onDispatched()"
        (close)="dispatch.set(null)"
      />
    }
    @if (composePlayer(); as c) {
      <app-message-compose
        [toPlayerId]="c.id"
        [toName]="c.name"
        [initialSubject]="c.subject"
        (close)="composePlayer.set(null)"
      />
    }
    @if (phalanxTarget(); as pt) {
      <app-phalanx-panel [target]="pt" (close)="phalanxTarget.set(null)" />
    }
  `,
  styles: [galaxyStyles],
})
export class GalaxyComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly balance = inject(BalanceService);

  /** Asset-Pfad-Helfer fuers Template (Buttons mit Glyph-Fallback via app-btn-icon). */
  protected readonly missionIcon = missionIcon;
  protected readonly navIcon = navIcon;
  protected readonly uiIcon = uiIcon;

  /** Standard-Sondenzahl der Schnell-Spionage (L2-Intel, balance.spy.level2_probes). */
  private readonly DEFAULT_PROBES = 3;

  /** Universums-Grenzen aus balance.json (Fallback 8 / 200). */
  protected maxG(): number { return this.balance.value?.universe?.galaxies ?? 8; }
  protected maxS(): number { return this.balance.value?.universe?.systems_per_galaxy ?? 200; }

  /** Haelt Galaxie/System in den gueltigen Grenzen [1..max] (vor dem Scannen). */
  private clampView(): void {
    this.viewG = Math.min(this.maxG(), Math.max(1, Math.round(this.viewG) || 1));
    this.viewS = Math.min(this.maxS(), Math.max(1, Math.round(this.viewS) || 1));
  }

  /** Live beim Tippen: nur das Maximum kappen (Min/Runden erst beim Scannen, sonst stoert es das Tippen). */
  protected clampOnInput(): void {
    if (this.viewG > this.maxG()) { this.viewG = this.maxG(); }
    if (this.viewS > this.maxS()) { this.viewS = this.maxS(); }
  }

  viewG = 1;
  viewS = 1;
  protected readonly cells = signal<GalaxyCell[]>([]);
  protected readonly zones = signal<AllianceZone[]>([]);
  protected readonly targets = signal<GalaxyTarget[]>([]);
  protected readonly loading = signal(false);
  protected readonly dispatch = signal<DispatchCtx | null>(null);
  protected readonly composePlayer = signal<{ id: string; name: string; subject: string } | null>(null);
  protected readonly phalanxTarget = signal<Coordinate | null>(null);
  private initialized = false;

  /** Tooltip fuer die P2P-Handelsanzeige eines Spielers. */
  tradeTip(tr: { offer: string | null; want: string | null; rate: number | null; note: string | null }, name?: string | null): string {
    const head = name ? `${name} handelt: ` : 'Handelt: ';
    const deal = tr.offer && tr.want ? `${tr.offer} → ${tr.want}${tr.rate ? ' @ ' + tr.rate : ''}` : 'offen für Angebote';
    const note = tr.note ? ` · „${tr.note}"` : '';
    return `${head}${deal}${note} — Kurs aushandeln per Nachricht, liefern per Transport.`;
  }

  messagePlayer(c: GalaxyCell): void {
    if (!c.player_id) {
      return;
    }
    const subj = c.trade?.offer && c.trade?.want
      ? `Handel: dein ${c.trade.offer} gegen mein ${c.trade.want}`
      : 'Handelsanfrage';
    this.composePlayer.set({ id: c.player_id, name: c.player_name ?? c.name ?? 'Spieler', subject: subj });
  }

  protected readonly scannedCount = computed(
    () => this.cells().filter((c) => c.occupant_type !== 'empty').length,
  );

  /** Verfuegbare Spionagesonden auf dem aktiven Planeten. */
  protected readonly probeCount = computed(
    () => this.state.activePlanet()?.ships?.find((s) => s.type === 'spy_probe')?.count ?? 0,
  );

  protected readonly spyTitle = computed(
    () => `Spionieren — sendet ${Math.min(this.probeCount(), this.DEFAULT_PROBES) || this.DEFAULT_PROBES} Sonde(n)`,
  );

  constructor() {
    // Aufgeklärte Ziele für das Verzeichnis laden (steuert NICHT den Scan-Ort).
    this.api.getGalaxyTargets().subscribe({
      next: (t) => this.targets.set(t),
      error: () => {},
    });

    // Standardmäßig das EIGENE Heimatsystem scannen, sobald der aktive Planet geladen ist
    // (race-sicher: initialisiert erst, wenn echte Koordinaten vorliegen — nicht auf 1:1).
    effect(() => {
      const p = this.state.activePlanet();
      if (p && !this.initialized) {
        this.initialized = true;
        this.viewG = p.galaxy;
        this.viewS = p.system;
        this.scan();
      }
    });
  }

  scan(): void {
    this.clampView();
    this.loading.set(true);
    this.api.getGalaxy(this.viewG, this.viewS).subscribe({
      next: (res) => {
        this.cells.set(res.cells);
        this.zones.set(res.zones ?? []);
        this.loading.set(false);
      },
      error: () => {
        this.cells.set([]);
        this.zones.set([]);
        this.loading.set(false);
      },
    });
  }

  stepSystem(delta: number): void {
    this.viewS = Math.min(this.maxS(), Math.max(1, this.viewS + delta));
    this.scan();
  }

  goHome(): void {
    const p = this.state.activePlanet();
    if (p) {
      this.viewG = p.galaxy;
      this.viewS = p.system;
      this.scan();
    }
  }

  jumpTo(t: GalaxyTarget): void {
    this.viewG = t.galaxy;
    this.viewS = t.system;
    this.scan();
  }

  // --- Koordinaten-Helfer ------------------------------------------------
  cellCoord(c: GalaxyCell): Coordinate {
    return { galaxy: this.viewG, system: this.viewS, position: c.position };
  }
  targetCoord(t: GalaxyTarget): Coordinate {
    return { galaxy: t.galaxy, system: t.system, position: t.position };
  }

  // --- Schnellaktionen ---------------------------------------------------
  /** Versand-Overlay fuer Angriff/Transport am Ziel oeffnen. */
  openDispatch(target: Coordinate, name: string | null, mission: FleetMission, targetType?: 'moon' | 'station' | 'mining_fleet'): void {
    this.dispatch.set({ target, name, mission, targetType });
  }

  onDispatched(): void {
    // Flotten/Planet sind im Overlay schon nachgeladen; Scanner ggf. auffrischen.
    this.scan();
  }

  /** Ein-Klick-Spionage: schickt sofort Standard-Sonden zum Ziel. */
  quickSpy(target: Coordinate, _name: string | null): void {
    const origin = this.state.activePlanetId();
    if (!origin) {
      return;
    }
    const probes = Math.min(this.probeCount(), this.DEFAULT_PROBES);
    if (probes < 1) {
      this.notify.warning('Keine Spionagesonden', 'Baue Spionagesonden in der Werft, um zu spähen.');
      return;
    }
    this.api
      .sendFleet({
        origin_planet_id: origin,
        target,
        mission: 'spy',
        ships: { spy_probe: probes },
        cargo: { metal: 0, crystal: 0, deuterium: 0 },
        commander_id: null,
        speed_pct: 100,
      })
      .subscribe({
        next: () => {
          this.notify.success('Sonden unterwegs', `${probes} Spionagesonde(n) gestartet → [${target.galaxy}:${target.system}:${target.position}].`);
          void this.state.reloadFleets();
          void this.state.reloadActivePlanet();
        },
        error: (err) => this.notify.warning('Spionage fehlgeschlagen', err?.error?.detail ?? 'Fehler.'),
      });
  }

  /** Rendert eine {typ: anzahl}-Map kompakt. */
  fmtUnits(map?: Record<string, number> | null): string {
    if (!map) {
      return '';
    }
    const parts = Object.entries(map)
      .filter(([, n]) => n > 0)
      .map(([type, n]) => {
        const meta = SHIP_META[type] ?? metaFor(DEFENSE_META, type);
        return `${n}× ${meta.label}`;
      });
    return parts.join(', ');
  }

  fmtRes(res?: GalaxyIntel['resources'] | null): string {
    if (!res) {
      return '';
    }
    const parts: string[] = [];
    for (const key of ['metal', 'crystal', 'deuterium'] as const) {
      const val = res[key];
      if (val != null) {
        parts.push(`${metaFor(RESOURCE_META, key).label} ${val.toLocaleString('de-DE')}`);
      }
    }
    return parts.join(' · ');
  }

  /** Aufklaerungs-Detail als Tooltip (Flotte/Verteidigung/Ressourcen) — entlastet die Liste. */
  intelTip(t: GalaxyTarget): string {
    const parts: string[] = [];
    const f = this.fmtUnits(t.intel?.fleet);
    if (f) { parts.push('Flotte: ' + f); }
    const d = this.fmtUnits(t.intel?.defenses);
    if (d) { parts.push('Verteidigung: ' + d); }
    const r = this.fmtRes(t.intel?.resources);
    if (r) { parts.push('Ressourcen: ' + r); }
    return parts.length
      ? parts.join('\n')
      : `${t.ships_total} Schiffe · ${t.defenses_total} Verteidigung — mehr per Spionage`;
  }

  isOwn(c: GalaxyCell): boolean {
    const p = this.state.activePlanet();
    return (
      c.occupant_type === 'player' &&
      !!p &&
      this.viewG === p.galaxy &&
      this.viewS === p.system &&
      c.position === p.position
    );
  }

  /** Feindliches/fremdes Ziel (NPC oder fremder Spieler) -> Schnellaktionen anbieten. */
  isHostile(c: GalaxyCell): boolean {
    return c.occupant_type === 'npc' || (c.occupant_type === 'player' && !this.isOwn(c));
  }

  rowClass(c: GalaxyCell): string {
    if (this.isOwn(c)) return 'row occupied own';
    if (c.occupant_type === 'empty') return 'row empty';
    return `row occupied ${c.occupant_type}`;
  }

  cellImage(c: GalaxyCell): string | null {
    const base = 'assets/img/backgrounds/';
    // Asteroidenfeld-Overlay auf sonst leerem Feld -> Trümmer-/Felsoptik.
    if (c.asteroid && (c.occupant_type === 'empty' || !c.occupant_type)) {
      return base + 'debris_field.png';
    }
    switch (c.occupant_type) {
      case 'player':
        return base + (this.isOwn(c) ? 'planet_homeworld.png' : 'planet_normal.png');
      case 'npc': {
        let name = 'planet_normal';
        if (c.position <= 3) name = 'planet_hot';
        else if (c.position >= 11) name = 'planet_cold';
        return base + name + '.png';
      }
      case 'debris':
        return base + 'debris_field.png';
      case 'asteroid_field':
        return base + 'debris_field.png';
      case 'deep_space':
        return base + 'deep_space.png';
      default:
        return null;
    }
  }

  /** Tooltip eines Asteroidenfelds: Reichtum + Vorrat/Maximum. */
  asteroidTip(a: NonNullable<GalaxyCell['asteroid']>): string {
    return (
      `Asteroidenfeld · Reichtum: ${a.richness} (×${a.mult})\n` +
      `Metall: ${Math.round(a.metal)} / ${Math.round(a.metal_max)}\n` +
      `Kristall: ${Math.round(a.crystal)} / ${Math.round(a.crystal_max)}\n` +
      `Bergbauschiff hinschicken (⛏), Vorrat regeneriert mit der Zeit.`
    );
  }

  occupantLabel(c: GalaxyCell): string {
    switch (c.occupant_type) {
      case 'empty':
        return 'leer';
      case 'player':
        return this.isOwn(c) ? '👤 Du' : '👤 ' + (c.player_name ?? 'Spieler');
      case 'npc':
        return '🤖 NPC-Imperium';
      case 'debris':
        return '💥 Trümmerfeld';
      case 'asteroid_field':
        return '☄️ Asteroidenfeld';
      case 'deep_space':
        return '🌌 Galaktische Weiten';
      default:
        return c.occupant_type;
    }
  }

  // -- Game-Events auf der Karte -------------------------------------------
  private readonly EVENT_META: Record<string, { glyph: string; label: string; tip: string }> = {
    wandering_comet: { glyph: '☄️', label: 'Wandernder Komet', tip: 'Riesiger Vorrat an Kristall/Deuterium — schick Schürf-/Recycler-Flotten (Mining-Mission), bevor er weiterzieht!' },
    cosmic_anomaly: { glyph: '🌀', label: 'Kosmische Anomalie', tip: 'Schick eine Spionagesonde hin (Spionage-Mission) → temporärer Forschungstempo-Buff (kleines Risiko).' },
    black_market: { glyph: '🏴', label: 'Schwarzmarkt', tip: 'Temporäres Händlerschiff mit Sonderkursen — handeln per Transport/Handel.' },
    solar_storm: { glyph: '⚡', label: 'Sonnensturm', tip: 'In diesem System fallen Phalanx & Spionage aus — Flottenbewegungen sind unsichtbar.' },
    super_freighter_wreck: { glyph: '⚓', label: 'Frachter-Wrack', tip: 'Von Drohnen bewacht — erst Kampfschiffe schicken, dann ausschlachten.' },
    utopia_shipyard: { glyph: '⚙️', label: 'Utopia-Werft', tip: 'Liefer Ressourcen per Transport — Top-Lieferer bekommen ein einzigartiges Schiff.' },
    refugee_flotilla: { glyph: '🚢', label: 'Flüchtlinge', tip: 'Deuterium spenden → Moral-/Bau-Boost. Aber Verfolger greifen an!' },
    black_hole: { glyph: '🕳️', label: 'Schwarzes Loch', tip: 'Kurze, riskante Expedition mit dreifachem Ertrag — aber hohe Verlustchance.' },
  };

  eventGlyph(type: string): string {
    return this.EVENT_META[type]?.glyph ?? '✨';
  }
  eventLabel(type: string): string {
    return this.EVENT_META[type]?.label ?? type;
  }
  eventTip(ev: NonNullable<GalaxyCell['event']>): string {
    return `${this.eventLabel(ev.event_type)}\n${this.EVENT_META[ev.event_type]?.tip ?? ''}\nEndet in ${this.eventCountdown(ev.expires_at)}`;
  }
  eventCountdown(expiresAt: string): string {
    const diff = new Date(expiresAt).getTime() - Date.now();
    if (diff <= 0) {
      return 'gleich';
    }
    const h = Math.floor(diff / 3600000);
    const m = Math.floor((diff % 3600000) / 60000);
    return h > 0 ? `${h}h ${m}m` : `${m}m`;
  }
}
