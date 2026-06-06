import { ChangeDetectionStrategy, Component, computed, effect, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { GalaxyCell, GalaxyTarget } from '../../core/models/api.models';
import { NotificationService } from '../../core/services/notification.service';
import { galaxyStyles } from './galaxy.styles';

/**
 * Galaxie-/Kartenansicht (UX-Doku 11 §2). Zeigt ein System Position fuer Position,
 * markiert den eigenen Planeten und liefert ein Verzeichnis bekannter (NPC-)Ziele —
 * damit der Spieler weiss, *wen* er angreifen kann. "Angreifen" verlinkt mit
 * vorausgefuelltem Ziel auf den Flotten-Screen.
 */
@Component({
  selector: 'app-galaxy',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule],
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
                <div class="cell-pos mono">{{ c.position }}</div>
                <div class="cell-body">
                  <div class="cell-kind">{{ occupantLabel(c) }}</div>
                  <div class="cell-name">{{ c.name ?? '—' }}</div>
                </div>
                @if (c.occupant_type === 'npc' || (c.occupant_type === 'player' && !isOwn(c))) {
                  <button class="btn btn-danger btn-sm" type="button" (click)="attack(c)">⚔ Angreifen</button>
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
        <div class="panel-title">🎯 Bekannte Ziele</div>
        @if (targets().length) {
          <p class="muted small">Aufklaerung gemeldet — wähle ein Ziel:</p>
          @for (t of targets(); track t.npc_id) {
            <div class="target-row">
              <div class="target-main">
                <span class="target-name">🤖 {{ t.name }}</span>
                <span class="mono small">[{{ t.coords }}]</span>
              </div>
              <div class="target-meta small muted">
                🚀 {{ t.ships_total }} Schiffe · 🛡 {{ t.defenses_total }} Verteidigung
              </div>
              <div class="target-act">
                <button class="btn btn-ghost btn-sm" type="button" (click)="jumpTo(t)">Anfliegen</button>
                <button class="btn btn-danger btn-sm" type="button" (click)="attackTarget(t)">⚔ Angreifen</button>
              </div>
            </div>
          }
        } @else {
          <p class="muted small">Keine Ziele in Reichweite gemeldet.</p>
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
    void this.router.navigate(['/fleet'], {
      queryParams: { g: t.galaxy, s: t.system, p: t.position, mission: 'attack' },
    });
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
