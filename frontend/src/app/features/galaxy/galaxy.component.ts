import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ActivatedRoute, RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { GameStateService } from '../../core/services/game-state.service';
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
  imports: [FormsModule, RouterLink, ShortNumberPipe, BtnIconComponent, FleetDispatchComponent, CountdownComponent],
  template: `
    <h1>Galaxie · Karte</h1>
    <p class="sub">Erkunde Systeme und navigiere die Galaxie. Gegner anzeigen → über „🎯 im Ziele-Screen steuern" handeln (Angriff/Spionage/Diplomatie); Asteroiden/Trümmer/Monde direkt am Ziel.</p>

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
                </div>
                @if (c.asteroid) {
                  <div class="acts">
                    <button class="ic mine" type="button" (click)="openDispatch(cellCoord(c), 'Asteroidenfeld', 'mine')" title="Hier Erz abbauen (Bergbauschiff nötig)"><app-btn-icon [src]="missionIcon('mine')" glyph="⛏" [size]="18" /></button>
                  </div>
                }
                @if (c.debris) {
                  <div class="acts">
                    <button class="ic recycle" type="button" (click)="openDispatch(cellCoord(c), 'Trümmerfeld', 'recycle')" title="Trümmerfeld abbauen (Recycler nötig)"><app-btn-icon [src]="missionIcon('recycle')" glyph="♻" [size]="18" /></button>
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
                  <div class="acts steer">
                    @if (c.discovered) {
                      <span class="chip disc tip" data-tip="Automatisch aufgeklärt: spawnte nahe deinem Planeten (≤ 8 Systeme)."><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="14" /> aufgeklärt</span>
                    }
                    <a class="steer-hint" routerLink="/targets" title="NPC-Imperien & Spieler werden jetzt im Ziele-Screen gesteuert: Angriff, Spionage, Diplomatie, Transport, Nachricht, Phalanx.">🎯 im Ziele-Screen steuern →</a>
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
  `,
  styles: [galaxyStyles],
})
export class GalaxyComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly balance = inject(BalanceService);
  private readonly route = inject(ActivatedRoute);

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

  // --- Schnellaktionen ---------------------------------------------------
  /** Versand-Overlay fuer Angriff/Transport am Ziel oeffnen. */
  openDispatch(target: Coordinate, name: string | null, mission: FleetMission, targetType?: 'moon' | 'station' | 'mining_fleet'): void {
    this.dispatch.set({ target, name, mission, targetType });
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
    parts.push('🎯 Steuern im Ziele-Screen.');
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
