import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import { Planet, PlanetUnit } from '../../core/models/api.models';
import { SHIP_META, metaFor } from '../../core/models/display';
import { CountdownComponent } from './countdown.component';
import { IconTileComponent } from './icon-tile.component';

/**
 * Sprungtor-Dialog: versetzt Schiffe SOFORT zwischen zwei eigenen Monden (kein Flug).
 *
 * Quellmond = aktiver Planet-Kontext (muss ein Mond mit Sprungtor sein). Zielmond aus den
 * anderen eigenen Monden waehlbar. Deuterium-Kosten (nach Schiffs-Groessenklasse) und der
 * Cooldown werden lokal aus `balance.json` + `jump_gate_tech` vorgerechnet — die autoritative
 * Pruefung macht der Server (`POST /api/fleets/jump`). Markup/Styles lehnen sich an
 * `fleet-dispatch.component.ts` an (OGame-Modal mit Schiffs-Picker).
 */
@Component({
  selector: 'app-jump-gate-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, IconTileComponent, CountdownComponent],
  host: { '(document:keydown.escape)': 'close.emit()' },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>

        <header class="head">
          <h2>🌀 Sprungtor</h2>
          @if (source(); as s) {
            <span class="coord mono">🌑 {{ s.name }} [{{ s.galaxy }}:{{ s.system }}:{{ s.position }}]</span>
          }
        </header>

        @if (!hasSource()) {
          <p class="hint small">Kein Mond aktiv. Wechsle zuerst auf einen Mond mit Sprungtor.</p>
        } @else if (targets().length === 0) {
          <p class="hint small">
            Kein zweiter Mond mit Sprungtor vorhanden. Ein Sprung braucht zwei eigene Monde, die
            beide ein Sprungtor besitzen.
          </p>
        } @else {
          <!-- Zielmond -->
          <div class="opts">
            <div class="field">
              <label>Zielmond</label>
              <select [ngModel]="targetId()" (ngModelChange)="targetId.set($event)">
                <option [ngValue]="null">— wählen —</option>
                @for (m of targets(); track m.id) {
                  <option [ngValue]="m.id">🌑 {{ m.name }} [{{ m.galaxy }}:{{ m.system }}:{{ m.position }}]</option>
                }
              </select>
            </div>
          </div>

          <!-- Schiffs-Picker (Garnison des Quellmonds) -->
          <div class="ships">
            @for (s of availableShips(); track s.type) {
              <div class="ship" [class.picked]="shipCount(s.type) > 0">
                <div class="ship-art">
                  <app-icon-tile [glyph]="shipMeta(s.type).glyph" [src]="'assets/img/ships/' + s.type + '.png'" [size]="40" />
                  <span class="avail" title="vorhanden">{{ s.count }}</span>
                </div>
                <div class="ship-name">{{ shipMeta(s.type).label }}</div>
                <div class="ship-pick">
                  <input type="number" min="0" [max]="s.count"
                    [ngModel]="shipCount(s.type)" (ngModelChange)="setShip(s.type, $event, s.count)" aria-label="Menge" />
                  <button class="btn btn-ghost btn-sm" type="button" (click)="setShip(s.type, s.count, s.count)">alle</button>
                </div>
              </div>
            } @empty {
              <p class="muted small">Keine Schiffe auf diesem Mond. <a href="/shipyard">Werft →</a></p>
            }
          </div>

          <!-- Kosten + Cooldown -->
          <div class="summary">
            <div class="sum-row">
              <span class="faint">🛢️ Sprungkosten</span>
              <span class="mono" [class.neg]="!enoughDeuterium()">{{ jumpCost() }} Deuterium</span>
            </div>
            <div class="sum-row">
              <span class="faint">vorhanden</span>
              <span class="mono">{{ deuteriumAvailable() }}</span>
            </div>
            @if (onCooldown()) {
              <div class="sum-row warn-row">
                <span>⏳ Sprungtor im Cooldown</span>
                <app-countdown [target]="nextJumpAt()!" />
              </div>
            }
            <p class="muted small">Nur Schiffe werden versetzt (keine Ressourcen). Sprung ist sofort, kein Flug.</p>
          </div>

          <div class="actions">
            <button class="btn btn-primary" type="button" [disabled]="!canJump() || jumping()" (click)="jump()">
              {{ jumping() ? 'Springe…' : '🌀 Sprung auslösen' }}
            </button>
          </div>
          @if (!hasSelection()) {
            <p class="hint small">Mindestens ein Schiff auswählen.</p>
          } @else if (!targetId()) {
            <p class="hint small">Zielmond wählen.</p>
          } @else if (!enoughDeuterium()) {
            <p class="hint small">Nicht genug Deuterium am Quellmond.</p>
          }
        }
      </div>
    </div>
  `,
  styles: [
    `
      .backdrop {
        position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center;
        padding: 1rem; background: rgba(4, 7, 14, 0.72); backdrop-filter: blur(4px);
      }
      .popup {
        position: relative; width: 100%; max-width: 520px; max-height: 88vh; overflow-y: auto;
        background: linear-gradient(160deg, var(--surface-2), var(--surface));
        border: 1px solid var(--border-strong); border-radius: var(--radius);
        box-shadow: var(--shadow), var(--glow); padding: 1.1rem 1.2rem 1.2rem;
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
      }
      .x {
        position: absolute; top: 0.5rem; right: 0.6rem; width: 30px; height: 30px; border-radius: 8px;
        background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text-dim);
        cursor: pointer; display: flex; align-items: center; justify-content: center;
      }
      .x:hover { color: var(--text); background: rgba(255,255,255,0.1); }
      .head { display: flex; align-items: baseline; flex-wrap: wrap; gap: 0.5rem 0.7rem; padding-right: 2rem; }
      .head h2 { margin: 0; font-size: 1.15rem; }
      .coord { color: var(--accent); font-size: 0.9rem; }

      .opts { display: flex; flex-wrap: wrap; gap: 0.9rem; margin: 0.9rem 0 0.2rem; }
      .opts .field { flex: 1 1 200px; display: flex; flex-direction: column; gap: 0.25rem; }
      .opts label { font-size: 0.74rem; color: var(--text-dim); }
      .opts select { min-height: 30px; }

      .ships {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: 0.5rem; margin-top: 0.7rem;
      }
      .ship {
        display: flex; flex-direction: column; align-items: center; gap: 0.25rem;
        padding: 0.45rem; border: 1px solid var(--border); border-radius: var(--radius-sm);
        background: rgba(255,255,255,0.02);
      }
      .ship.picked { border-color: var(--accent-dim); background: rgba(46,230,214,0.06); }
      .ship-art { position: relative; }
      .ship-art .avail {
        position: absolute; bottom: -4px; right: -6px; min-width: 18px; padding: 0 4px; height: 18px;
        border-radius: 99px; background: var(--surface-3); border: 1px solid var(--border);
        font-size: 0.7rem; display: flex; align-items: center; justify-content: center; color: var(--text);
      }
      .ship-name { font-size: 0.76rem; text-align: center; line-height: 1.1; color: var(--text-dim); }
      .ship-pick { display: flex; gap: 0.25rem; align-items: center; }
      .ship-pick input { width: 52px; text-align: center; min-height: 28px; padding: 0.2rem; }

      .summary { margin-top: 0.9rem; display: flex; flex-direction: column; gap: 0.3rem; }
      .sum-row { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; }
      .sum-row .neg { color: var(--warn); }
      .warn-row { color: var(--warn); }

      .actions { margin-top: 1rem; }
      .actions .btn { width: 100%; }
      .hint { color: var(--warn); margin: 0.4rem 0 0; }
    `,
  ],
})
export class JumpGateDialogComponent {
  private readonly api = inject(ApiService);
  private readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly balance = inject(BalanceService);

  readonly close = output<void>();
  readonly jumped = output<void>();

  /** Quellmond = aktiver Planet-Kontext (Dashboard oeffnet den Dialog nur auf einem Mond). */
  protected readonly source = this.state.activePlanet;
  protected readonly hasSource = computed(() => this.source()?.planet_type === 'moon');

  /** Andere eigene Monde (Zielkandidaten). Sprungtor-Pflicht prueft der Server. */
  protected readonly targets = computed<Planet[]>(() => {
    const srcId = this.source()?.id;
    return this.state.planets().filter((p) => p.planet_type === 'moon' && p.id !== srcId);
  });

  protected readonly availableShips = computed<PlanetUnit[]>(
    () => this.source()?.ships?.filter((s) => s.count > 0) ?? [],
  );

  protected readonly targetId = signal<string | null>(null);
  protected readonly selection = signal<Record<string, number>>({});
  protected readonly jumping = signal(false);
  /** jump_gate_tech-Stufe (senkt Kosten/Cooldown) — beim Oeffnen geladen. */
  protected readonly jumpGateTech = signal(0);

  constructor() {
    this.api.getResearch().subscribe({
      next: (r) => this.jumpGateTech.set(r.research.find((t) => t.type === 'jump_gate_tech')?.level ?? 0),
      error: () => {},
    });
  }

  shipCount(type: string): number {
    return this.selection()[type] ?? 0;
  }

  setShip(type: string, value: number, max: number): void {
    const n = Math.max(0, Math.min(max, Math.floor(value || 0)));
    this.selection.update((s) => ({ ...s, [type]: n }));
  }

  protected readonly hasSelection = computed(() =>
    Object.values(this.selection()).some((n) => n > 0),
  );

  /** Schiffstyp → Groessenklasse (Reverse-Map aus balance.commander.ship_classes). */
  private readonly shipClass = computed<Record<string, string>>(() => {
    const classes = (this.balance.value?.commander?.['ship_classes'] ?? {}) as Record<string, unknown>;
    const map: Record<string, string> = {};
    for (const [cls, types] of Object.entries(classes)) {
      if (cls.startsWith('_') || !Array.isArray(types)) {
        continue;
      }
      for (const t of types as string[]) {
        map[t] = cls;
      }
    }
    return map;
  });

  /** Deuterium-Sprungkosten (exakt wie Backend jump_fleet): cost_mult·base·Σ(class_mult·count). */
  protected readonly jumpCost = computed(() => {
    const moon = (this.balance.value?.['moon'] ?? {}) as Record<string, unknown>;
    const base = Number(moon['jump_cost_base_deuterium'] ?? 0);
    const classMult = (moon['jump_cost_class_mult'] ?? {}) as Record<string, number>;
    const eff = (this.balance.value?.research?.['effects'] ?? {}) as Record<string, number>;
    const costMult = Math.max(0, 1 - this.jumpGateTech() * Number(eff['jump_cost_reduction_per_level'] ?? 0));
    const cls = this.shipClass();
    let sum = 0;
    for (const [type, count] of Object.entries(this.selection())) {
      if (count > 0) {
        sum += Number(classMult[cls[type] ?? 'fighter'] ?? 1) * count;
      }
    }
    return Math.round(costMult * base * sum);
  });

  protected readonly deuteriumAvailable = computed(() =>
    Math.floor(this.source()?.resources?.deuterium?.amount ?? 0),
  );
  protected readonly enoughDeuterium = computed(() => this.deuteriumAvailable() >= this.jumpCost());

  /** Cooldown-Ende des Quellmonds (last_jump_at + cd) als ISO-String, oder null. */
  protected readonly nextJumpAt = computed<string | null>(() => {
    const last = this.source()?.last_jump_at;
    if (!last) {
      return null;
    }
    const moon = (this.balance.value?.['moon'] ?? {}) as Record<string, unknown>;
    const eff = (this.balance.value?.research?.['effects'] ?? {}) as Record<string, number>;
    const cdMult = Math.max(
      Number(eff['jump_cooldown_floor'] ?? 0.4),
      1 - this.jumpGateTech() * Number(eff['jump_cooldown_reduction_per_level'] ?? 0),
    );
    const cdMs = Number(moon['jump_gate_cooldown_seconds'] ?? 3600) * cdMult * 1000;
    return new Date(new Date(last).getTime() + cdMs).toISOString();
  });

  protected readonly onCooldown = computed(() => {
    const next = this.nextJumpAt();
    return !!next && new Date(next).getTime() > Date.now();
  });

  protected readonly canJump = computed(
    () =>
      this.hasSelection() &&
      !!this.targetId() &&
      this.enoughDeuterium() &&
      !this.onCooldown(),
  );

  jump(): void {
    const from = this.source()?.id;
    const to = this.targetId();
    if (!from || !to || !this.canJump()) {
      return;
    }
    const ships: Record<string, number> = {};
    for (const [type, n] of Object.entries(this.selection())) {
      if (n > 0) {
        ships[type] = n;
      }
    }
    this.jumping.set(true);
    this.api.jumpFleet({ from_moon_id: from, to_moon_id: to, ships }).subscribe({
      next: () => {
        this.jumping.set(false);
        this.notify.success('Sprung erfolgreich', 'Die Schiffe wurden zum Zielmond versetzt.');
        void this.state.reloadActivePlanet();
        this.jumped.emit();
        this.close.emit();
      },
      error: (err) => {
        this.jumping.set(false);
        this.notify.warning('Sprung fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
      },
    });
  }

  shipMeta = (t: string) => metaFor(SHIP_META, t);
}
