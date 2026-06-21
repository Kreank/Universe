import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  Coordinate,
  FleetMission,
  NpcTarget,
  PlayerTarget,
  ThreatItem,
} from '../../core/models/api.models';
import { missionIcon, navIcon, uiIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { FleetDispatchComponent } from '../../shared/components/fleet-dispatch.component';
import { NpcNegotiateComponent } from '../../shared/components/npc-negotiate.component';
import { MessageComposeComponent } from '../../shared/components/message-compose.component';
import { PhalanxPanelComponent } from '../../shared/components/phalanx-panel.component';

type TabKey = 'threats' | 'npcs' | 'players';

/** Offenes Versand-Overlay (Schnellangriff / Schnelltransport / Spionage am Ziel). */
interface DispatchCtx {
  target: Coordinate;
  name: string | null;
  mission: FleetMission;
}

/** Anzeige-Metadaten je Beziehungsstatus (Status-Badge). */
const REL_META: Record<string, { glyph: string; label: string; cls: string }> = {
  neutral: { glyph: '◌', label: 'neutral', cls: 'rel-neutral' },
  allied: { glyph: '🤝', label: 'verbündet', cls: 'rel-allied' },
  ceasefire: { glyph: '🕊', label: 'Waffenstillstand', cls: 'rel-ceasefire' },
  hostile: { glyph: '⚔', label: 'feindlich', cls: 'rel-hostile' },
  broken_pact: { glyph: '💔', label: 'Pakt gebrochen', cls: 'rel-broken' },
};

/**
 * Ziele & Bedrohungen (W1). Bündelt alle Ziel-Aktionen, die früher in der Galaxie
 * verstreut waren, in einem Screen — die Galaxie bleibt reine Übersicht + Navigation.
 *
 * Drei Abschnitte (Bedrohungen zuerst, weil dringend):
 * - Bedrohungen: eingehende Angriffe (Countdown + Fleetsave-Hinweis) und nahe
 *   feindliche NPCs (Angreifen/Verhandeln).
 * - NPC-Imperien: entdeckte KI-Imperien mit Relation/Intel + allen Aktionen über die
 *   geteilten Overlays (Angriff/Transport/Spionage/Diplomatie/Phalanx).
 * - Spieler: entdeckte Spieler mit Angriff/Transport/Spionage + Nachricht; bei
 *   Handelsangebot Verweis auf den Handel-Reiter.
 *
 * Die Listen sind serverseitig vorsortiert (Bedrohungen nach priority/ETA).
 */
@Component({
  selector: 'app-targets',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    RouterLink,
    BtnIconComponent,
    CountdownComponent,
    EmptyStateComponent,
    FleetDispatchComponent,
    NpcNegotiateComponent,
    MessageComposeComponent,
    PhalanxPanelComponent,
  ],
  template: `
    <h1>Ziele &amp; Bedrohungen</h1>
    <p class="sub">
      Steuere von hier aus alle aufgeklärten NPC-Imperien und Spieler — angreifen, spionieren,
      verhandeln, transportieren. Bedrohungen oben behalten den Überblick über eingehende Angriffe.
    </p>

    <div class="tabs">
      <button class="tab" [class.on]="tab() === 'threats'" (click)="tab.set('threats')">
        <app-btn-icon [src]="missionIcon('attack')" glyph="⚠" [size]="16" /> Bedrohungen
        @if (acuteCount() > 0) { <span class="tab-badge">{{ acuteCount() }}</span> }
      </button>
      <button class="tab" [class.on]="tab() === 'npcs'" (click)="tab.set('npcs')">
        <app-btn-icon [src]="uiIcon('target')" glyph="🤖" [size]="16" /> NPC-Imperien
        @if (npcs().length) { <span class="tab-count">{{ npcs().length }}</span> }
      </button>
      <button class="tab" [class.on]="tab() === 'players'" (click)="tab.set('players')">
        <app-btn-icon [src]="navIcon('ranking')" glyph="👤" [size]="16" /> Spieler
        @if (players().length) { <span class="tab-count">{{ players().length }}</span> }
      </button>
      <button class="btn btn-sm btn-ghost reload" (click)="reload()">↻ Aktualisieren</button>
    </div>

    @if (loading()) {
      <p class="muted">Lade Ziele…</p>
    } @else {
      <!-- ===================== BEDROHUNGEN ===================== -->
      @if (tab() === 'threats') {
        @if (threats().length) {
          <div class="list">
            @for (t of threats(); track $index) {
              <article class="card threat" [class.acute]="t.priority === 0" [class.incoming]="t.kind === 'incoming'">
                <div class="t-main">
                  <div class="t-head">
                    @if (t.kind === 'incoming') {
                      <span class="t-tag danger"><app-btn-icon [src]="missionIcon('attack')" glyph="⚠" [size]="14" /> Eingehender Angriff</span>
                    } @else {
                      <span class="t-tag warn"><app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="14" /> Feindliches Imperium</span>
                    }
                    <span class="t-name">{{ t.name }}</span>
                    @if (t.priority === 0) { <span class="t-acute">AKUT</span> }
                  </div>
                  <div class="t-sub small">
                    @if (t.origin) { <span class="mono">{{ t.origin }}</span> }
                    @if (t.origin && t.target) { <span class="faint">→</span> }
                    @if (t.target) { <span class="mono">[{{ t.target.galaxy }}:{{ t.target.system }}:{{ t.target.position }}]</span> }
                    <span class="t-stat"><app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="14" /> {{ t.ships_total }}</span>
                    @if (t.mission) { <span class="faint">· {{ t.mission }}</span> }
                  </div>
                  @if (t.kind === 'incoming' && t.arrive_at) {
                    <div class="t-eta">
                      Ankunft in <app-countdown [target]="t.arrive_at" />
                      <span class="fleetsave">🛡 Fleetsave prüfen — Flotte rechtzeitig in Sicherheit bringen!</span>
                    </div>
                  }
                </div>
                @if (t.kind === 'hostile_npc' && t.npc_id) {
                  <div class="acts">
                    <button class="ic dipl" type="button" (click)="openNegotiate(t.npc_id!, t.name)" title="Verhandeln (Bündnis/Waffenstillstand/Tribut)"><app-btn-icon [src]="navIcon('diplomacy')" glyph="🕊" [size]="18" /></button>
                    @if (t.target) {
                      <button class="ic spy" type="button" (click)="quickSpy(t.target!, t.name)" [title]="spyTitle()"><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="18" /></button>
                      <button class="ic atk" type="button" (click)="openDispatch(t.target!, t.name, 'attack')" title="Angreifen"><app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="18" /></button>
                    }
                  </div>
                }
              </article>
            }
          </div>
        } @else {
          <app-empty-state art="empty_search">
            Keine akuten Bedrohungen. Keine eingehenden Angriffe und keine feindlichen Imperien in der Nähe.
          </app-empty-state>
        }
      }

      <!-- ===================== NPC-IMPERIEN ===================== -->
      @if (tab() === 'npcs') {
        @if (npcs().length) {
          <div class="grid cards">
            @for (n of npcs(); track n.npc_id) {
              <article class="card tgt">
                <div class="tgt-top">
                  <span class="tgt-name">🤖 {{ n.name }}</span>
                  <a class="coord mono" [routerLink]="['/galaxy']" [queryParams]="{ g: n.galaxy, s: n.system }" title="In der Galaxie-Karte ansehen">[{{ n.coords }}]</a>
                </div>
                <div class="tgt-meta small">
                  @if (relMeta(n.relation_status); as rm) {
                    <span class="rel-badge {{ rm.cls }}">{{ rm.glyph }} {{ rm.label }}</span>
                  }
                  <span class="chip lvl">L{{ n.intel_level }}/3</span>
                  <span class="faint">{{ n.behavior_profile }}</span>
                  @if (n.distance_galaxies !== null) { <span class="faint">· {{ distLabel(n.distance_galaxies) }}</span> }
                </div>
                <div class="tgt-sub small">
                  <span class="tgt-stat"><app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="14" /> {{ n.ships_total }}</span>
                  <span class="tgt-stat"><app-btn-icon [src]="'assets/img/icons/spec/stat_shield.png'" glyph="🛡" [size]="14" /> {{ n.defenses_total }}</span>
                </div>
                <div class="acts tgt-acts">
                  <button class="ic dipl" type="button" (click)="openNegotiate(n.npc_id, n.name)" title="Diplomatie / verhandeln"><app-btn-icon [src]="navIcon('diplomacy')" glyph="🕊" [size]="18" /></button>
                  <button class="ic phx" type="button" (click)="phalanxTarget.set(npcCoord(n))" title="Sensorphalanx-Scan"><app-btn-icon [src]="'assets/img/buildings/sensorphalanx.png'" glyph="📡" [size]="18" /></button>
                  <button class="ic spy" type="button" (click)="quickSpy(npcCoord(n), n.name)" [title]="spyTitle()"><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="18" /></button>
                  <button class="ic trp" type="button" (click)="openDispatch(npcCoord(n), n.name, 'transport')" title="Transport"><app-btn-icon [src]="missionIcon('transport')" glyph="🚚" [size]="18" /></button>
                  <button class="ic atk" type="button" (click)="openDispatch(npcCoord(n), n.name, 'attack')" title="Angreifen"><app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="18" /></button>
                </div>
              </article>
            }
          </div>
        } @else {
          <app-empty-state art="empty_search">
            Noch keine NPC-Imperien aufgeklärt. Entsende Spionagesonden (🛰) auf belegte Felder in der Galaxie.
          </app-empty-state>
        }
      }

      <!-- ===================== SPIELER ===================== -->
      @if (tab() === 'players') {
        @if (players().length) {
          <div class="grid cards">
            @for (p of players(); track p.coords) {
              <article class="card tgt">
                <div class="tgt-top">
                  <span class="tgt-name">👤 {{ p.name }}</span>
                  <a class="coord mono" [routerLink]="['/galaxy']" [queryParams]="{ g: p.galaxy, s: p.system }" title="In der Galaxie-Karte ansehen">[{{ p.coords }}]</a>
                </div>
                <div class="tgt-meta small">
                  <span class="chip lvl">L{{ p.intel_level }}/3</span>
                  @if (p.has_trade_offer) {
                    <a class="chip trade" routerLink="/trade" title="Hat ein Handelsangebot — zum Handel-Reiter"><app-btn-icon [src]="navIcon('market')" glyph="💱" [size]="14" /> Handelsangebot →</a>
                  }
                  @if (p.distance_galaxies !== null) { <span class="faint">· {{ distLabel(p.distance_galaxies) }}</span> }
                </div>
                <div class="tgt-sub small">
                  <span class="tgt-stat"><app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="14" /> {{ p.ships_total }}</span>
                </div>
                <div class="acts tgt-acts">
                  @if (p.player_id) {
                    <button class="ic msg" type="button" (click)="messagePlayer(p)" title="Nachricht an Spieler"><app-btn-icon [src]="navIcon('mail')" glyph="✉" [size]="18" /></button>
                  }
                  <button class="ic phx" type="button" (click)="phalanxTarget.set(playerCoord(p))" title="Sensorphalanx-Scan"><app-btn-icon [src]="'assets/img/buildings/sensorphalanx.png'" glyph="📡" [size]="18" /></button>
                  <button class="ic spy" type="button" (click)="quickSpy(playerCoord(p), p.name)" [title]="spyTitle()"><app-btn-icon [src]="missionIcon('spy')" glyph="🛰" [size]="18" /></button>
                  <button class="ic trp" type="button" (click)="openDispatch(playerCoord(p), p.name, 'transport')" title="Transport"><app-btn-icon [src]="missionIcon('transport')" glyph="🚚" [size]="18" /></button>
                  <button class="ic atk" type="button" (click)="openDispatch(playerCoord(p), p.name, 'attack')" title="Angreifen"><app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="18" /></button>
                </div>
              </article>
            }
          </div>
        } @else {
          <app-empty-state art="empty_search">
            Noch keine Spieler entdeckt. Spähe belegte Felder in der Galaxie aus, um Spieler-Ziele zu finden.
          </app-empty-state>
        }
      }
    }

    <!-- Geteilte Overlays (gleiche wie zuvor in der Galaxie) -->
    @if (dispatch(); as d) {
      <app-fleet-dispatch
        [target]="d.target"
        [targetName]="d.name"
        [initialMission]="d.mission"
        (sent)="onDispatched()"
        (close)="dispatch.set(null)"
      />
    }
    @if (negotiate(); as n) {
      <app-npc-negotiate
        [npcId]="n.npcId"
        [npcName]="n.name"
        (changed)="reload()"
        (close)="negotiate.set(null)"
      />
    }
    @if (composePlayer(); as c) {
      <app-message-compose
        [toPlayerId]="c.id"
        [toName]="c.name"
        (close)="composePlayer.set(null)"
      />
    }
    @if (phalanxTarget(); as pt) {
      <app-phalanx-panel [target]="pt" (close)="phalanxTarget.set(null)" />
    }
  `,
  styles: [
    `
      .sub { color: var(--text-dim); margin-top: calc(-1 * var(--sp-2)); }
      .tabs { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; margin: var(--sp-3) 0; }
      .tab {
        display: inline-flex; align-items: center; gap: var(--sp-1);
        font-size: var(--fs-sm); padding: var(--sp-1) var(--sp-3); border-radius: var(--r-pill);
        background: rgba(255,255,255,0.04); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer;
        transition: color var(--motion-fast) var(--ease-out), border-color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .tab:hover { color: var(--text); border-color: var(--border-strong); }
      .tab.on { background: var(--accent-soft); color: var(--accent); border-color: var(--accent-dim); }
      .tab-count { font-size: var(--fs-xs); background: var(--surface-3); border-radius: var(--r-pill); padding: 0 6px; color: var(--text-dim); }
      .tab-badge { font-size: var(--fs-xs); background: var(--danger); color: #fff; border-radius: var(--r-pill); padding: 0 6px; font-weight: 700; }
      .reload { margin-left: auto; }

      .list { display: flex; flex-direction: column; gap: var(--sp-2); }
      .grid.cards { display: grid; grid-template-columns: repeat(auto-fill, minmax(280px, 1fr)); gap: var(--sp-3); }

      /* Bedrohungs-Zeilen */
      .threat { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-3); padding: var(--sp-3); }
      .threat.incoming { border-color: var(--danger-dim); }
      .threat.acute { border-color: var(--danger); background: color-mix(in srgb, var(--danger) 8%, transparent); }
      .t-main { display: flex; flex-direction: column; gap: var(--sp-1); min-width: 0; }
      .t-head { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
      .t-tag { font-size: var(--fs-xs); padding: 1px var(--sp-2); border-radius: var(--r-sm); background: rgba(255,255,255,0.06); }
      .t-tag.danger { color: var(--danger); }
      .t-tag.warn { color: var(--warn); }
      .t-name { font-weight: 600; }
      .t-acute { font-size: var(--fs-xs); font-weight: 700; color: #fff; background: var(--danger); border-radius: var(--r-sm); padding: 0 6px; }
      .t-sub { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; color: var(--text-dim); }
      .t-eta { font-size: var(--fs-sm); color: var(--text-dim); display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
      .fleetsave { color: var(--warn); font-size: var(--fs-xs); }

      /* Ziel-Karten (NPC/Spieler) */
      .tgt { display: flex; flex-direction: column; gap: var(--sp-2); padding: var(--sp-3); }
      .tgt-top { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); }
      .tgt-name { font-weight: 600; }
      .coord { color: var(--text); text-decoration: none; border-bottom: 1px dotted var(--border-strong); }
      .coord:hover { color: var(--accent); }
      .tgt-meta, .tgt-sub { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; color: var(--text-dim); }
      .chip { font-size: var(--fs-xs); padding: 1px var(--sp-2); border-radius: var(--r-sm); background: rgba(255,255,255,0.06); color: var(--text-dim); }
      .chip.lvl { font-family: var(--font-mono); }
      .chip.trade { color: var(--accent); text-decoration: none; border: 1px solid var(--accent-dim); background: var(--accent-soft); }
      .rel-badge { font-size: var(--fs-xs); padding: 1px var(--sp-2); border-radius: var(--r-pill); border: 1px solid var(--border-strong); }
      .rel-badge.rel-allied { color: var(--accent); border-color: var(--accent-dim); background: var(--accent-soft); }
      .rel-badge.rel-ceasefire { color: var(--success, #6fd08a); }
      .rel-badge.rel-hostile, .rel-badge.rel-broken { color: var(--danger); border-color: var(--danger); }

      .acts { display: flex; align-items: center; gap: var(--sp-1); }
      .tgt-acts { margin-top: auto; }
      .ic {
        display: inline-flex; align-items: center; justify-content: center; width: 34px; height: 34px;
        border-radius: var(--r-sm); border: 1px solid var(--border); background: rgba(255,255,255,0.03);
        color: var(--text-dim); cursor: pointer;
        transition: color var(--motion-fast) var(--ease-out), border-color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .ic:hover { color: var(--text); border-color: var(--border-strong); background: rgba(255,255,255,0.08); }
      .ic.atk:hover { color: var(--danger); border-color: var(--danger); }
      .ic.spy:hover, .ic.phx:hover { color: var(--accent); border-color: var(--accent-dim); }
      .ic.dipl:hover { color: var(--success, #6fd08a); }
      .faint { color: var(--text-faint); }
    `,
  ],
})
export class TargetsComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  /** Asset-Pfad-Helfer fuers Template (Glyph-Fallback via app-btn-icon). */
  protected readonly missionIcon = missionIcon;
  protected readonly navIcon = navIcon;
  protected readonly uiIcon = uiIcon;

  /** Standard-Sondenzahl der Schnell-Spionage (analog Galaxie). */
  private readonly DEFAULT_PROBES = 3;

  protected readonly tab = signal<TabKey>('threats');
  protected readonly loading = signal(true);
  protected readonly npcs = signal<NpcTarget[]>([]);
  protected readonly players = signal<PlayerTarget[]>([]);
  protected readonly threats = signal<ThreatItem[]>([]);

  /** Offene geteilte Overlays. */
  protected readonly dispatch = signal<DispatchCtx | null>(null);
  protected readonly negotiate = signal<{ npcId: string; name: string | null } | null>(null);
  protected readonly composePlayer = signal<{ id: string; name: string } | null>(null);
  protected readonly phalanxTarget = signal<Coordinate | null>(null);

  /** Anzahl akuter Bedrohungen (priority 0) — Tab-Badge. */
  protected readonly acuteCount = computed(() => this.threats().filter((t) => t.priority === 0).length);

  /** Verfuegbare Spionagesonden auf dem aktiven Planeten. */
  protected readonly probeCount = computed(
    () => this.state.activePlanet()?.ships?.find((s) => s.type === 'spy_probe')?.count ?? 0,
  );
  protected readonly spyTitle = computed(
    () => `Spionieren — sendet ${Math.min(this.probeCount(), this.DEFAULT_PROBES) || this.DEFAULT_PROBES} Sonde(n)`,
  );

  constructor() {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    let pending = 3;
    const done = () => { if (--pending <= 0) { this.loading.set(false); } };
    this.api.getThreats().subscribe({ next: (t) => { this.threats.set(t); done(); }, error: () => { this.threats.set([]); done(); } });
    this.api.getTargetNpcs().subscribe({ next: (n) => { this.npcs.set(n); done(); }, error: () => { this.npcs.set([]); done(); } });
    this.api.getTargetPlayers().subscribe({ next: (p) => { this.players.set(p); done(); }, error: () => { this.players.set([]); done(); } });
  }

  // --- Koordinaten-Helfer -------------------------------------------------
  npcCoord(n: NpcTarget): Coordinate {
    return { galaxy: n.galaxy, system: n.system, position: n.position };
  }
  playerCoord(p: PlayerTarget): Coordinate {
    return { galaxy: p.galaxy, system: p.system, position: p.position };
  }

  /** Status-Badge-Metadaten (oder null bei unbekanntem Status). */
  relMeta(status: string | null): { glyph: string; label: string; cls: string } | null {
    if (!status) {
      return null;
    }
    return REL_META[status] ?? { glyph: '◌', label: status, cls: 'rel-neutral' };
  }

  distLabel(d: number): string {
    return d <= 0 ? 'Heimat-Galaxie' : `${d} Gal.`;
  }

  // --- Aktionen über die geteilten Overlays -------------------------------
  openDispatch(target: Coordinate, name: string | null, mission: FleetMission): void {
    this.dispatch.set({ target, name, mission });
  }
  onDispatched(): void {
    this.dispatch.set(null);
    this.reload();
  }

  openNegotiate(npcId: string, name: string | null): void {
    this.negotiate.set({ npcId, name });
  }

  messagePlayer(p: PlayerTarget): void {
    if (!p.player_id) {
      return;
    }
    this.composePlayer.set({ id: p.player_id, name: p.name });
  }

  /** Ein-Klick-Spionage: schickt sofort Standard-Sonden zum Ziel (analog Galaxie). */
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
}
