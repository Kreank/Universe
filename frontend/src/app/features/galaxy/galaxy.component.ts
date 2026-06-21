import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  Coordinate,
  FleetMission,
  AllianceZone,
  Conjunction,
  ConjunctionInfo,
  GalaxyCell,
  NpcRelation,
  NpcRelationStatus,
} from '../../core/models/api.models';
import { missionIcon, navIcon, uiIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { FleetDispatchComponent } from '../../shared/components/fleet-dispatch.component';
import { NpcNegotiateComponent } from '../../shared/components/npc-negotiate.component';
import { MessageComposeComponent } from '../../shared/components/message-compose.component';
import { PhalanxPanelComponent } from '../../shared/components/phalanx-panel.component';
import { ShortNumberPipe } from '../../shared/pipes/short-number.pipe';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { galaxyStyles } from './galaxy.styles';

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
  host: { '(document:keydown.escape)': 'closeActions()' },
  imports: [
    FormsModule,
    ShortNumberPipe,
    BtnIconComponent,
    FleetDispatchComponent,
    NpcNegotiateComponent,
    MessageComposeComponent,
    PhalanxPanelComponent,
    CountdownComponent,
  ],
  template: `
    <h1>Galaxie · Karte</h1>
    <p class="sub">Erkunde Systeme und navigiere die Galaxie. Schnellaktionen per Klick aufs Ziel — Angriff/Spionage/Diplomatie/Transport, Asteroiden/Trümmer/Monde inklusive.</p>

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

        <!-- Welle 5: Konjunktion aktiv im aktuell gescannten System (dezenter Marker). -->
        @if (viewConjunctions().length) {
          <div class="conj-banner" title="Wandernde Galaxie: Routen von/zu diesem System sind gerade verkürzt.">
            @for (c of viewConjunctions(); track c.from + '>' + c.to) {
              <span class="conj-chip" [class.bane]="c.discount_pct < 0">
                🌌 [{{ conjPartner(c) }}] {{ c.discount_pct >= 0 ? '−' : '+' }}{{ abs(c.discount_pct).toFixed(0) }}%
                @if (c.ends_at) { <span class="small muted">· <app-countdown [target]="c.ends_at" /></span> }
              </span>
            }
          </div>
        }

        @if (loading()) {
          <p class="muted small">Scanne System…</p>
        } @else {
          <div class="positions">
            @for (c of cells(); track c.position) {
              <div class="row" [class]="rowClass(c)" [class.actionable]="hasActions(c)"
                   [attr.role]="hasActions(c) ? 'button' : null"
                   [attr.tabindex]="hasActions(c) ? 0 : null"
                   [attr.title]="hasActions(c) ? 'Schnellaktionen am Ziel öffnen' : null"
                   (click)="hasActions(c) && openActions(c)"
                   (keydown.enter)="hasActions(c) && openActions(c)"
                   (keydown.space)="hasActions(c) && openActions(c)">
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
                  @if (c.debris; as dbr) {
                    <span class="chip debris tip" [attr.data-tip]="'Trümmerfeld (nach Kämpfen) — mit Recyclern abbaubar: ' + (dbr.metal | shortNumber) + ' Metall / ' + (dbr.crystal | shortNumber) + ' Kristall'">💥 {{ dbr.metal | shortNumber }}M / {{ dbr.crystal | shortNumber }}K</span>
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
                  @if (npcRelation(c); as rel) {
                    @if (rel.status !== 'neutral') {
                      <span class="chip rel tip" [attr.data-tip]="relationTip(rel)">{{ relGlyph(rel.status) }} {{ relLabel(rel.status) }}</span>
                    }
                  }
                  @if (isHostile(c) && c.discovered) {
                    <span class="chip disc tip" data-tip="Automatisch aufgeklärt: spawnte nahe deinem Planeten (≤ 8 Systeme)."><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="14" /> aufgeklärt</span>
                  }
                </div>
                @if (isOwn(c)) {
                  <span class="chip own">dein Planet</span>
                } @else if (hasActions(c) && c.occupant_type !== 'empty') {
                  <span class="act-hint" aria-hidden="true">⚡</span>
                }
              </div>
            }
          </div>
        }
      </section>

    </div>

    <!-- Klick→Overlay: kompaktes "Aktionen am Ziel"-Menü (kontextabhängige Schnellaktionen). -->
    @if (actionMenu(); as c) {
      <div class="am-backdrop" (click)="closeActions()">
        <div class="glass am-popup" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
          <button class="x" type="button" (click)="closeActions()" aria-label="Schliessen">✕</button>
          <header class="am-head">
            <h2>{{ occupantLabel(c) }}@if (c.name) { <span class="faint"> · {{ c.name }}</span> }</h2>
            <span class="coord mono">[{{ viewG }}:{{ viewS }}:{{ c.position }}]</span>
          </header>
          <div class="am-grid">
            @if (c.occupant_type === 'npc') {
              <button class="am-act atk" type="button" (click)="openDispatch(cellCoord(c), c.name, 'attack')"><app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="18" /> <span>Angreifen</span></button>
              <button class="am-act trp" type="button" (click)="openDispatch(cellCoord(c), c.name, 'transport')"><app-btn-icon [src]="missionIcon('transport')" glyph="🚚" [size]="18" /> <span>Transport</span></button>
              <button class="am-act col" type="button" (click)="openDispatch(cellCoord(c), c.name, 'deploy')"><app-btn-icon [src]="missionIcon('deploy')" glyph="🛬" [size]="18" /> <span>Stationieren</span></button>
              <button class="am-act spy" type="button" (click)="quickSpy(cellCoord(c), c.name)"><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="18" /> <span>Spionage</span></button>
              @if (c.npc_id) {
                <button class="am-act dipl" type="button" (click)="openNegotiate(c.npc_id!, c.name)"><app-btn-icon [src]="navIcon('diplomacy')" glyph="🕊" [size]="18" /> <span>Diplomatie</span></button>
              }
              <button class="am-act phx" type="button" (click)="openPhalanx(cellCoord(c))"><app-btn-icon [src]="'assets/img/buildings/sensorphalanx.png'" glyph="📡" [size]="18" /> <span>Phalanx</span></button>
            }
            @if (c.occupant_type === 'player' && !isOwn(c)) {
              <button class="am-act atk" type="button" (click)="openDispatch(cellCoord(c), c.name, 'attack')"><app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="18" /> <span>Angreifen</span></button>
              <button class="am-act trp" type="button" (click)="openDispatch(cellCoord(c), c.name, 'transport')"><app-btn-icon [src]="missionIcon('transport')" glyph="🚚" [size]="18" /> <span>Transport</span></button>
              <button class="am-act col" type="button" (click)="openDispatch(cellCoord(c), c.name, 'deploy')"><app-btn-icon [src]="missionIcon('deploy')" glyph="🛬" [size]="18" /> <span>Stationieren</span></button>
              <button class="am-act spy" type="button" (click)="quickSpy(cellCoord(c), c.name)"><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="18" /> <span>Spionage</span></button>
              @if (c.player_id) {
                <button class="am-act msg" type="button" (click)="openCompose(c.player_id!, c.name ?? c.player_name ?? 'Spieler')"><app-btn-icon [src]="navIcon('mail')" glyph="✉" [size]="18" /> <span>Nachricht</span></button>
              }
              <button class="am-act phx" type="button" (click)="openPhalanx(cellCoord(c))"><app-btn-icon [src]="'assets/img/buildings/sensorphalanx.png'" glyph="📡" [size]="18" /> <span>Phalanx</span></button>
            }
            @if (c.moon; as m) {
              @if (!m.own) {
                <button class="am-act atk" type="button" (click)="openDispatch(cellCoord(c), m.name, 'attack', 'moon')"><app-btn-icon [src]="missionIcon('attack')" glyph="🌙⚔" [size]="18" /> <span>Mond angreifen</span></button>
                <button class="am-act spy" type="button" (click)="openDispatch(cellCoord(c), m.name, 'spy', 'moon')"><app-btn-icon [src]="missionIcon('spy')" glyph="🌙🛰" [size]="18" /> <span>Mond spionieren</span></button>
              }
            }
            @if (c.station; as st) {
              @if (!st.mine && st.status !== 'destroyed') {
                <button class="am-act atk" type="button" (click)="openDispatch(cellCoord(c), 'Allianz-Station [' + st.tag + ']', 'attack', 'station')"><app-btn-icon [src]="missionIcon('attack')" glyph="🛰⚔" [size]="18" /> <span>Station belagern</span></button>
              }
            }
            @if (c.mining_fleet; as mf) {
              @if (!mf.mine) {
                <button class="am-act atk" type="button" (click)="openDispatch(cellCoord(c), '⛏ Flotte [' + (mf.owner ?? '?') + ']', 'attack', 'mining_fleet')"><app-btn-icon [src]="missionIcon('attack')" glyph="⛏⚔" [size]="18" /> <span>Flotte angreifen</span></button>
              }
            }
            @if (c.asteroid) {
              <button class="am-act mine" type="button" (click)="openDispatch(cellCoord(c), 'Asteroidenfeld', 'mine')"><app-btn-icon [src]="missionIcon('mine')" glyph="⛏" [size]="18" /> <span>Minen</span></button>
            }
            @if (c.debris) {
              <button class="am-act recycle" type="button" (click)="openDispatch(cellCoord(c), 'Trümmerfeld', 'recycle')"><app-btn-icon [src]="missionIcon('recycle')" glyph="♻" [size]="18" /> <span>Recyceln</span></button>
            }
            @if (c.event; as ev) {
              @if (ev.event_type === 'cosmic_anomaly') {
                <button class="am-act spy" type="button" (click)="openDispatch(cellCoord(c), 'Anomalie', 'spy')"><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="18" /> <span>Anomalie spähen</span></button>
              }
              @if (ev.event_type === 'utopia_shipyard' || ev.event_type === 'black_market') {
                <button class="am-act trp" type="button" (click)="openDispatch(cellCoord(c), eventLabel(ev.event_type), 'transport')"><app-btn-icon [src]="missionIcon('transport')" glyph="🚚" [size]="18" /> <span>Liefern/Handeln</span></button>
              }
            }
            @if (c.occupant_type === 'deep_space') {
              <button class="am-act exp" type="button" (click)="openDispatch(cellCoord(c), c.name, 'expedition')"><app-btn-icon [src]="missionIcon('expedition')" glyph="🌌" [size]="18" /> <span>Expedition</span></button>
            }
            @if (c.occupant_type === 'empty' && !c.station) {
              <button class="am-act col" type="button" (click)="openDispatch(cellCoord(c), null, 'colonize')"><app-btn-icon [src]="missionIcon('colonize')" glyph="🌱" [size]="18" /> <span>Kolonisieren</span></button>
            }
          </div>
        </div>
      </div>
    }

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
    @if (negotiate(); as n) {
      <app-npc-negotiate
        [npcId]="n.npcId"
        [npcName]="n.name"
        (changed)="scan()"
        (close)="negotiate.set(null)"
      />
    }
    @if (composePlayer(); as cp) {
      <app-message-compose
        [toPlayerId]="cp.id"
        [toName]="cp.name"
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
  private readonly balance = inject(BalanceService);
  private readonly route = inject(ActivatedRoute);
  private readonly notify = inject(NotificationService);

  /** Standard-Sondenzahl der Schnell-Spionage (analog Ziele-Screen). */
  private readonly DEFAULT_PROBES = 3;

  /** Asset-Pfad-Helfer fuers Template (Buttons mit Glyph-Fallback via app-btn-icon). */
  protected readonly missionIcon = missionIcon;
  protected readonly navIcon = navIcon;
  protected readonly uiIcon = uiIcon;

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
  protected readonly loading = signal(false);
  protected readonly dispatch = signal<DispatchCtx | null>(null);
  /** Klick→Overlay: aktuell im "Aktionen am Ziel"-Menü gewählte Zelle (oder null). */
  protected readonly actionMenu = signal<GalaxyCell | null>(null);
  /** Geteilte Fach-Overlays (gespiegelt vom Ziele-Screen). */
  protected readonly negotiate = signal<{ npcId: string; name: string | null } | null>(null);
  protected readonly composePlayer = signal<{ id: string; name: string } | null>(null);
  protected readonly phalanxTarget = signal<Coordinate | null>(null);
  /** Beziehungen zu NPC-Imperien je npc_id (fuer Status-Badge in der Zelle). */
  protected readonly relations = signal<Record<string, NpcRelation>>({});
  /** Welle 5: aktive Konjunktions-Fenster (wandernde Galaxie) — fuer den System-Marker. */
  protected readonly conjunctions = signal<ConjunctionInfo | null>(null);
  private initialized = false;

  /** Aktive Konjunktionen, die das aktuell gescannte System (viewG:viewS) betreffen. */
  protected viewConjunctions(): Conjunction[] {
    return (this.conjunctions()?.active ?? []).filter(
      (c) =>
        (c.from_coords.galaxy === this.viewG && c.from_coords.system === this.viewS) ||
        (c.to_coords.galaxy === this.viewG && c.to_coords.system === this.viewS),
    );
  }

  /** Das jeweils andere System der Route (g:s) — relativ zum gescannten System. */
  protected conjPartner(c: Conjunction): string {
    const here = c.from_coords.galaxy === this.viewG && c.from_coords.system === this.viewS;
    return here ? c.to : c.from;
  }

  protected abs(n: number): number {
    return Math.abs(n);
  }

  /** Tooltip fuer die P2P-Handelsanzeige eines Spielers. */
  tradeTip(tr: { offer: string | null; want: string | null; rate: number | null; note: string | null }, name?: string | null): string {
    const head = name ? `${name} handelt: ` : 'Handelt: ';
    const deal = tr.offer && tr.want ? `${tr.offer} → ${tr.want}${tr.rate ? ' @ ' + tr.rate : ''}` : 'offen für Angebote';
    const note = tr.note ? ` · „${tr.note}"` : '';
    return `${head}${deal}${note} — Kurs aushandeln per Nachricht, liefern per Transport.`;
  }

  protected readonly scannedCount = computed(
    () => this.cells().filter((c) => c.occupant_type !== 'empty').length,
  );

  constructor() {
    // Welle 5: aktive Konjunktions-Fenster laden (wandernde Galaxie — System-Marker; Fehler stumm).
    this.api.getConjunctions().subscribe({
      next: (c) => this.conjunctions.set(c),
      error: () => {},
    });

    // Ziel aus den Query-Parametern (?g=&s=) — z. B. per Klick auf Koordinaten in den
    // Flottenbewegungen — hat Vorrang vor dem Heimatsystem.
    const qp = this.route.snapshot.queryParamMap;
    const qg = Number(qp.get('g'));
    const qs = Number(qp.get('s'));
    const fromQuery = qg > 0 && qs > 0;

    // Standardmäßig das EIGENE Heimatsystem scannen, sobald der aktive Planet geladen ist
    // (race-sicher: initialisiert erst, wenn echte Koordinaten vorliegen — nicht auf 1:1).
    effect(() => {
      const p = this.state.activePlanet();
      if (p && !this.initialized) {
        this.initialized = true;
        this.viewG = fromQuery ? qg : p.galaxy;
        this.viewS = fromQuery ? qs : p.system;
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
        this.loadRelations(res.cells);
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

  // --- Koordinaten-Helfer ------------------------------------------------
  cellCoord(c: GalaxyCell): Coordinate {
    return { galaxy: this.viewG, system: this.viewS, position: c.position };
  }

  // --- Klick→Aktions-Overlay --------------------------------------------
  /** Verfuegbare Spionagesonden auf dem aktiven Planeten (Schnell-Spionage). */
  private probeCount(): number {
    return this.state.activePlanet()?.ships?.find((s) => s.type === 'spy_probe')?.count ?? 0;
  }

  /** Hat die Zelle kontext-passende Schnellaktionen (-> Zeile klickbar)? Eigene Felder: nein. */
  hasActions(c: GalaxyCell): boolean {
    if (this.isOwn(c)) {
      return false;
    }
    return !!(
      this.isHostile(c) ||
      (c.moon && !c.moon.own) ||
      (c.station && !c.station.mine && c.station.status !== 'destroyed') ||
      (c.mining_fleet && !c.mining_fleet.mine) ||
      c.asteroid ||
      c.debris ||
      (c.event && ['cosmic_anomaly', 'utopia_shipyard', 'black_market'].includes(c.event.event_type)) ||
      c.occupant_type === 'deep_space' ||
      (c.occupant_type === 'empty' && !c.station)
    );
  }

  /** Klick auf ein aktionierbares Ziel -> kompaktes Aktions-Overlay oeffnen. */
  openActions(c: GalaxyCell): void {
    this.actionMenu.set(c);
  }

  /** Aktions-Overlay schliessen (ESC/Backdrop/nach Auswahl einer Aktion). */
  closeActions(): void {
    this.actionMenu.set(null);
  }

  // --- Schnellaktionen ---------------------------------------------------
  /** Versand-Overlay fuer Angriff/Transport/… am Ziel oeffnen (schliesst das Aktions-Menü). */
  openDispatch(target: Coordinate, name: string | null, mission: FleetMission, targetType?: 'moon' | 'station' | 'mining_fleet'): void {
    this.actionMenu.set(null);
    this.dispatch.set({ target, name, mission, targetType });
  }

  /** Diplomatie-Overlay (npc-negotiate) am NPC-Imperium oeffnen. */
  openNegotiate(npcId: string, name: string | null): void {
    this.actionMenu.set(null);
    this.negotiate.set({ npcId, name });
  }

  /** Nachricht-Overlay (message-compose) an einen Spieler oeffnen. */
  openCompose(playerId: string, name: string): void {
    this.actionMenu.set(null);
    this.composePlayer.set({ id: playerId, name });
  }

  /** Sensorphalanx-Overlay am Ziel oeffnen. */
  openPhalanx(target: Coordinate): void {
    this.actionMenu.set(null);
    this.phalanxTarget.set(target);
  }

  /** Ein-Klick-Spionage: schickt sofort Standard-Sonden zum Ziel (analog Ziele-Screen). */
  quickSpy(target: Coordinate, _name: string | null): void {
    this.actionMenu.set(null);
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

  onDispatched(): void {
    // Flotten/Planet sind im Overlay schon nachgeladen; Scanner ggf. auffrischen.
    this.scan();
  }

  // --- NPC-Diplomatie (Welle 1) -----------------------------------------
  /** Laedt die Beziehungen zu allen sichtbaren NPC-Imperien (fuer Status-Badges). */
  private loadRelations(cells: GalaxyCell[]): void {
    const ids = cells
      .filter((c) => c.occupant_type === 'npc' && c.npc_id)
      .map((c) => c.npc_id as string);
    if (!ids.length) {
      this.relations.set({});
      return;
    }
    for (const id of ids) {
      this.api.getNpcRelation(id).subscribe({
        next: (rel) => this.relations.update((m) => ({ ...m, [id]: rel })),
        error: () => {},
      });
    }
  }

  /** Beziehung zu einem NPC-Feld (oder null). */
  npcRelation(c: GalaxyCell): NpcRelation | null {
    return c.npc_id ? this.relations()[c.npc_id] ?? null : null;
  }

  private readonly REL_META: Record<NpcRelationStatus, { glyph: string; label: string }> = {
    neutral: { glyph: '◌', label: 'neutral' },
    allied: { glyph: '🤝', label: 'verbündet' },
    ceasefire: { glyph: '🕊', label: 'Waffenstillstand' },
    hostile: { glyph: '⚔', label: 'feindlich' },
    broken_pact: { glyph: '💔', label: 'Pakt gebrochen' },
  };
  relGlyph(s: NpcRelationStatus): string {
    return this.REL_META[s]?.glyph ?? '◌';
  }
  relLabel(s: NpcRelationStatus): string {
    return this.REL_META[s]?.label ?? s;
  }
  relationTip(rel: NpcRelation): string {
    const parts: string[] = [`Diplomatie: ${this.relLabel(rel.status)}`];
    if (rel.tribute_metal_per_cycle > 0) {
      parts.push(`Tribut: ${Math.round(rel.tribute_metal_per_cycle).toLocaleString('de-DE')} Metall/Zyklus`);
    }
    if (rel.betrayed_by_player) {
      parts.push('Du hast einen Pakt gebrochen.');
    }
    if (rel.betrayed_by_npc) {
      parts.push('Das Imperium hat dich verraten.');
    }
    parts.push('Klick aufs Ziel öffnet die Schnellaktionen.');
    return parts.join('\n');
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
