import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { GalaxyCell, GalaxyIntel, GalaxyTarget } from '../../core/models/api.models';
import { NotificationService } from '../../core/services/notification.service';
import { DEFENSE_META, RESOURCE_META, SHIP_META, metaFor } from '../../core/models/display';
import { galaxyStyles } from './galaxy.styles';

/**
 * Galaxie-/Kartenansicht (UX-Doku 11 §2). Zeigt ein System Position fuer Position,
 * markiert den eigenen Planeten und liefert ein Verzeichnis bekannter Ziele.
 *
 * Spionage: Im Scanner koennen belegte Gegner-Felder per Spionagesonde aufgeklaert
 * werden (Deep-Link auf den Flotten-Screen mit `mission: 'spy'`). Bereits aufgeklaerte
 * Felder werden markiert. Das Ziel-Verzeichnis listet nur AUFGEKLAERTE Ziele samt
 * Aufklaerungsstufe und — je nach Stufe — Flotten-/Verteidigungs- und Ressourcen-Intel.
 * "Angreifen" verlinkt mit vorausgefuelltem Ziel auf den Flotten-Screen
 * (Blindangriffe ohne Aufklaerung sind erlaubt, aber riskant).
 */
@Component({
  selector: 'app-galaxy',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, DatePipe],
  template: `
    <h1>Galaxie · Karte</h1>
    <p class="sub">Erkunde Systeme, finde Ziele und entsende deine Flotten.</p>

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
              <div class="cell" [class]="cellClass(c)">
                <div class="cell-visual">
                  @if (cellImage(c); as img) {
                    <img class="cell-img" [src]="img" [alt]="occupantLabel(c)" loading="lazy" />
                  } @else {
                    <span class="cell-dot" aria-hidden="true"></span>
                  }
                  <span class="cell-pos mono">{{ c.position }}</span>
                </div>
                <div class="cell-body">
                  <div class="cell-kind">{{ occupantLabel(c) }}</div>
                  <div class="cell-name">{{ c.name ?? '—' }}</div>
                </div>
                @if (c.occupant_type === 'npc' || (c.occupant_type === 'player' && !isOwn(c))) {
                  <div class="cell-act">
                    @if (c.discovered) {
                      <span class="chip">🛰 aufgeklärt ✓</span>
                    }
                    <button class="btn btn-ghost btn-sm" type="button" (click)="spy(c)">🛰 Spionieren</button>
                    <button class="btn btn-danger btn-sm" type="button" (click)="attack(c)">⚔ Angreifen</button>
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
                <button class="btn btn-ghost btn-sm" type="button" (click)="spyTarget(t)">🛰 Spionieren</button>
                @if (t.npc_id) {
                  <button class="btn btn-danger btn-sm" type="button" (click)="attackTarget(t)">⚔ Angreifen</button>
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
  `,
  styles: [galaxyStyles],
})
export class GalaxyComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly router = inject(Router);

  viewG = 1;
  viewS = 1;
  protected readonly cells = signal<GalaxyCell[]>([]);
  protected readonly targets = signal<GalaxyTarget[]>([]);
  protected readonly loading = signal(false);
  private initialized = false;

  protected readonly scannedCount = computed(
    () => this.cells().filter((c) => c.occupant_type !== 'empty').length,
  );

  constructor() {
    // Ziel-Verzeichnis laden.
    this.api.getGalaxyTargets().subscribe({
      next: (t) => {
        this.targets.set(t);
        // Start-Ansicht: erstes bekanntes Ziel-System, sonst eigenes System.
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
        // Fallback: eigenes System scannen.
        const p = this.state.activePlanet();
        if (p && !this.initialized) {
          this.initialized = true;
          this.viewG = p.galaxy;
          this.viewS = p.system;
          this.scan();
        }
      },
    });

    // Sobald der Planet bekannt ist und noch nicht initialisiert wurde.
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

  attack(c: GalaxyCell): void {
    void this.router.navigate(['/fleet'], {
      queryParams: { g: this.viewG, s: this.viewS, p: c.position, mission: 'attack' },
    });
  }

  attackTarget(t: GalaxyTarget): void {
    // Deep-Link nur fuer aufgeklaerte NPC-Ziele (npc_id noetig fuer Vorbelegung).
    if (!t.npc_id) {
      return;
    }
    void this.router.navigate(['/fleet'], {
      queryParams: { g: t.galaxy, s: t.system, p: t.position, mission: 'attack' },
    });
  }

  spy(c: GalaxyCell): void {
    void this.router.navigate(['/fleet'], {
      queryParams: { g: this.viewG, s: this.viewS, p: c.position, mission: 'spy' },
    });
  }

  spyTarget(t: GalaxyTarget): void {
    void this.router.navigate(['/fleet'], {
      queryParams: { g: t.galaxy, s: t.system, p: t.position, mission: 'spy' },
    });
  }

  /** Rendert eine {typ: anzahl}-Map kompakt, z.B. "🛩️ 3× Leichter Jaeger, 📦 8× Kleiner Transporter". */
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

  /** Rendert Ressourcen-Intel mit Tausenderpunkt, z.B. "Metall 12.000 · Kristall 4.500". */
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

  cellClass(c: GalaxyCell): string {
    if (this.isOwn(c)) return 'cell own';
    return `cell ${c.occupant_type}`;
  }

  /**
   * Liefert den Pfad zum Planeten-/Truemmerfeld-Bild einer Zelle oder null
   * (leere Felder). Der NPC-Planetentyp wird deterministisch aus der Position
   * abgeleitet, damit ein System bei jedem Scan gleich aussieht.
   */
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
