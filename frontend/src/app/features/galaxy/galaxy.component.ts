import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import {
  Coordinate,
  FleetMission,
  GalaxyCell,
  GalaxyIntel,
  GalaxyTarget,
} from '../../core/models/api.models';
import { NotificationService } from '../../core/services/notification.service';
import { DEFENSE_META, RESOURCE_META, SHIP_META, metaFor } from '../../core/models/display';
import { FleetDispatchComponent } from '../../shared/components/fleet-dispatch.component';
import { MessageComposeComponent } from '../../shared/components/message-compose.component';
import { galaxyStyles } from './galaxy.styles';

/** Offenes Versand-Overlay (Schnellangriff / Schnelltransport / …). */
interface DispatchCtx {
  target: Coordinate;
  name: string | null;
  mission: FleetMission;
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
  imports: [FormsModule, DatePipe, FleetDispatchComponent, MessageComposeComponent],
  template: `
    <h1>Galaxie · Karte</h1>
    <p class="sub">Erkunde Systeme, finde Ziele und entsende deine Flotten — Schnellaktionen direkt am Ziel.</p>

    <div class="grid layout">
      <!-- System-Scanner ------------------------------------------------ -->
      <section class="card scanner">
        <div class="panel-title">🌌 System-Scanner</div>

        <div class="gx-nav">
          <button class="btn btn-sm" type="button" (click)="stepSystem(-1)" aria-label="System zurueck">◀</button>
          <div class="coordbox">
            <label>Galaxie</label>
            <input type="number" min="1" [(ngModel)]="viewG" />
          </div>
          <div class="coordbox">
            <label>System</label>
            <input type="number" min="1" [(ngModel)]="viewS" />
          </div>
          <button class="btn btn-sm" type="button" (click)="stepSystem(1)" aria-label="System vor">▶</button>
          <button class="btn btn-primary btn-sm" type="button" (click)="scan()">Scannen</button>
          <button class="btn btn-ghost btn-sm" type="button" (click)="goHome()">⌂ Heimat</button>
        </div>

        <div class="coords-current mono">[{{ viewG }}:{{ viewS }}] · {{ scannedCount() }} belegt</div>

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
                    <span class="chip trade tip" [attr.data-tip]="tradeTip(tr, c.player_name)">💱 {{ tr.offer }}→{{ tr.want }}{{ tr.rate ? ' @' + tr.rate : '' }}</span>
                  }
                </div>
                @if (isHostile(c)) {
                  <div class="acts">
                    @if (c.discovered) {
                      <span class="chip disc tip" data-tip="Automatisch aufgeklärt: spawnte nahe deinem Planeten (≤ 8 Systeme). Sende eine Sonde für tiefere/aktuellere Daten.">🛰 aufgeklärt</span>
                    }
                    @if (c.occupant_type === 'player' && c.player_id) {
                      <button class="ic msg" type="button" (click)="messagePlayer(c)" title="Nachricht an Spieler">✉</button>
                    }
                    <button class="ic spy" type="button" (click)="quickSpy(cellCoord(c), c.name)" [title]="spyTitle()">🛰</button>
                    <button class="ic atk" type="button" (click)="openDispatch(cellCoord(c), c.name, 'attack')" title="Angreifen">⚔</button>
                    <button class="ic trp" type="button" (click)="openDispatch(cellCoord(c), c.name, 'transport')" [title]="c.trade ? 'Transport (P2P-Handel: Ware schicken)' : 'Transport'">🚚</button>
                  </div>
                } @else if (isOwn(c)) {
                  <span class="chip own">dein Planet</span>
                }
              </div>
            }
          </div>
        }
      </section>

      <!-- Ziel-Verzeichnis ---------------------------------------------- -->
      <section class="card targets">
        <div class="panel-title">🎯 Aufgeklärte Ziele</div>
        @if (targets().length) {
          <p class="muted small">Aufklaerung gemeldet — wähle ein Ziel:</p>
          @for (t of targets(); track t.coords) {
            <div class="target-row">
              <div class="target-main">
                <span class="target-name">🤖 {{ t.name }}</span>
                <span class="mono small">
                  <span class="chip lvl">L{{ t.level ?? 1 }}/3</span>
                  @if (t.intel?.trade_center) {
                    <span class="chip trade tip" data-tip="Neutrales Handelszentrum (unangreifbar) · globaler Handelskurs">💱 Handelszentrum</span>
                  } @else if (t.intel?.merchant) {
                    <span class="chip trade tip" [attr.data-tip]="'Händler · Spez.: ' + (t.intel?.spec ?? '?') + ' — handeln statt kämpfen'">💱 Händler</span>
                  }
                  [{{ t.coords }}]
                </span>
              </div>
              <div class="target-meta small muted">
                🚀 {{ t.ships_total }} Schiffe · 🛡 {{ t.defenses_total }} Verteidigung
              </div>
              @if (fmtUnits(t.intel?.fleet); as f) {
                <div class="target-intel small">🚀 {{ f }}</div>
              }
              @if (fmtUnits(t.intel?.defenses); as d) {
                <div class="target-intel small">🛡 {{ d }}</div>
              }
              @if (fmtRes(t.intel?.resources); as r) {
                <div class="target-intel small">💰 {{ r }}</div>
              }
              @if (t.discovered_at) {
                <div class="target-meta small muted">zuletzt aufgeklärt: {{ t.discovered_at | date: 'short' }}</div>
              }
              <div class="target-act">
                <button class="btn btn-ghost btn-sm" type="button" (click)="jumpTo(t)">Anfliegen</button>
                <button class="btn btn-ghost btn-sm" type="button" (click)="quickSpy(targetCoord(t), t.name)">🛰 Spionieren</button>
                <button class="btn btn-ghost btn-sm" type="button" (click)="openDispatch(targetCoord(t), t.name, 'transport')">🚚 Transport</button>
                @if (t.intel?.merchant) {
                  <button class="btn btn-trade btn-sm" type="button" (click)="openDispatch(targetCoord(t), t.name, 'trade')">💱 Handeln</button>
                }
                @if (t.npc_id && !t.intel?.trade_center) {
                  <button class="btn btn-danger btn-sm" type="button" (click)="openDispatch(targetCoord(t), t.name, 'attack')">⚔ Angreifen</button>
                }
              </div>
            </div>
          }
        } @else {
          <p class="muted small">
            Noch keine Ziele aufgeklärt. Entsende Spionagesonden (🛰) auf belegte Felder im Scanner.
          </p>
        }
      </section>
    </div>

    @if (dispatch(); as d) {
      <app-fleet-dispatch
        [target]="d.target"
        [targetName]="d.name"
        [initialMission]="d.mission"
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
  `,
  styles: [galaxyStyles],
})
export class GalaxyComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  /** Standard-Sondenzahl der Schnell-Spionage (L2-Intel, balance.spy.level2_probes). */
  private readonly DEFAULT_PROBES = 3;

  viewG = 1;
  viewS = 1;
  protected readonly cells = signal<GalaxyCell[]>([]);
  protected readonly targets = signal<GalaxyTarget[]>([]);
  protected readonly loading = signal(false);
  protected readonly dispatch = signal<DispatchCtx | null>(null);
  protected readonly composePlayer = signal<{ id: string; name: string; subject: string } | null>(null);
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
    this.api.getGalaxyTargets().subscribe({
      next: (t) => {
        this.targets.set(t);
        if (!this.initialized) {
          this.initialized = true;
          if (t.length) {
            this.viewG = t[0].galaxy;
            this.viewS = t[0].system;
          } else {
            const p = this.state.activePlanet();
            if (p) {
              this.viewG = p.galaxy;
              this.viewS = p.system;
            }
          }
          this.scan();
        }
      },
      error: () => {
        const p = this.state.activePlanet();
        if (p && !this.initialized) {
          this.initialized = true;
          this.viewG = p.galaxy;
          this.viewS = p.system;
          this.scan();
        }
      },
    });

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
    this.loading.set(true);
    this.api.getGalaxy(this.viewG, this.viewS).subscribe({
      next: (res) => {
        this.cells.set(res.cells);
        this.loading.set(false);
      },
      error: () => {
        this.cells.set([]);
        this.loading.set(false);
      },
    });
  }

  stepSystem(delta: number): void {
    this.viewS = Math.max(1, this.viewS + delta);
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
  openDispatch(target: Coordinate, name: string | null, mission: FleetMission): void {
    this.dispatch.set({ target, name, mission });
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
      default:
        return null;
    }
  }

  occupantLabel(c: GalaxyCell): string {
    switch (c.occupant_type) {
      case 'empty':
        return 'leer';
      case 'player':
        return '👤 Spieler';
      case 'npc':
        return '🤖 NPC-Imperium';
      case 'debris':
        return '💥 Trümmerfeld';
      default:
        return c.occupant_type;
    }
  }
}
