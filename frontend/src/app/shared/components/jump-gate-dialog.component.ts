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
      <div class="popup glass" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
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
        padding: var(--sp-4); background: rgba(4, 7, 14, 0.72);
        backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
        animation: fade var(--motion-fast) var(--ease-out);
      }
      @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
      /* .glass (global) liefert Background/Blur/Border/Elevation; hier nur Layout + Signatur-Ecke. */
      .popup {
        position: relative; width: 100%; max-width: 520px; max-height: 88vh; overflow-y: auto;
        border-radius: var(--r-lg); padding: var(--sp-5);
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
        animation: pop var(--motion-base) var(--ease-out);
      }
      @keyframes pop { from { transform: translateY(8px) scale(0.98); opacity: 0; } to { transform: none; opacity: 1; } }
      .x {
        position: absolute; top: var(--sp-2); right: var(--sp-2); width: 32px; height: 32px; border-radius: var(--r-sm);
        background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text-dim);
        cursor: pointer; display: flex; align-items: center; justify-content: center;
        transition: color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .x:hover { color: var(--text); background: rgba(255,255,255,0.1); }
      .head { display: flex; align-items: baseline; flex-wrap: wrap; gap: var(--sp-2) var(--sp-3); padding-right: var(--sp-8); }
      .head h2 { margin: 0; font-size: var(--fs-lg); }
      .coord { color: var(--accent); font-size: var(--fs-base); }

      .opts { display: flex; flex-wrap: wrap; gap: var(--sp-3); margin: var(--sp-3) 0 var(--sp-1); }
      .opts .field { flex: 1 1 200px; display: flex; flex-direction: column; gap: var(--sp-1); }
      .opts label { font-size: var(--fs-xs); color: var(--text-dim); }
      .opts select { min-height: 30px; }

      .ships {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: var(--sp-2); margin-top: var(--sp-2);
      }
      .ship {
        display: flex; flex-direction: column; align-items: center; gap: var(--sp-1);
        padding: var(--sp-2); border: 1px solid var(--border); border-radius: var(--r-md);
        background: rgba(255,255,255,0.02);
        transition: border-color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .ship.picked { border-color: var(--accent-dim); background: var(--accent-soft); }
      .ship-art { position: relative; }
      .ship-art .avail {
        position: absolute; bottom: -4px; right: -6px; min-width: 18px; padding: 0 4px; height: 18px;
        border-radius: var(--r-pill); background: var(--surface-3); border: 1px solid var(--border);
        font-size: var(--fs-xs); display: flex; align-items: center; justify-content: center; color: var(--text);
        font-family: var(--mono); font-variant-numeric: tabular-nums;
      }
      .ship-name { font-size: var(--fs-sm); text-align: center; line-height: 1.1; color: var(--text-dim); }
      .ship-pick { display: flex; gap: var(--sp-1); align-items: center; }
      .ship-pick input { width: 52px; text-align: center; min-height: 28px; padding: var(--sp-1); }

      .summary { margin-top: var(--sp-3); display: flex; flex-direction: column; gap: var(--sp-1); }
      .sum-row { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-3); }
      .sum-row .neg { color: var(--warn); }
      .warn-row { color: var(--warn); }

      .actions { margin-top: var(--sp-4); }
      .actions .btn { width: 100%; }
      .hint { color: var(--warn); margin: var(--sp-1) 0 0; }

      @media (max-width: 560px) {
        .backdrop { padding: var(--sp-2); }
        .popup { max-width: 100%; max-height: 94vh; padding: var(--sp-4); }
      }
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
