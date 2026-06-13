import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import { BalanceService } from '../../core/services/balance.service';
import { Coordinate, EscortOffer, FleetMission, FleetSendRequest, GalaxyIntel, PlanetUnit, TradeIndex } from '../../core/models/api.models';
import { MISSION_META, RANK_META, SHIP_META, metaFor } from '../../core/models/display';
import { IconTileComponent } from './icon-tile.component';

/**
 * Kompaktes Versand-Overlay (OGame-Schnellaktion): direkt aus der Galaxie
 * eine Flotte zu einem Ziel schicken — Schiffs-Picker, optional Cargo
 * (Transport/Stationierung), Commander, Tempo — ohne Tab-Wechsel.
 *
 * Liest verfuegbare Schiffe/Commander/Ressourcen aus dem GameState des aktiven
 * Planeten und sendet via ApiService. Schliesst nach erfolgreichem Start.
 */
@Component({
  selector: 'app-fleet-dispatch',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, IconTileComponent],
  host: { '(document:keydown.escape)': 'close.emit()' },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup glass" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>

        <header class="head">
          <h2>{{ missionMeta(mission()).glyph }} Flotte entsenden</h2>
          <span class="coord mono">→ [{{ target().galaxy }}:{{ target().system }}:{{ target().position }}]</span>
          @if (targetName()) { <span class="tname">{{ targetName() }}</span> }
        </header>

        <!-- Missionswahl -->
        <div class="mission-tabs">
          @for (m of missions(); track m) {
            <button
              type="button"
              class="mtab"
              [class.active]="mission() === m"
              (click)="mission.set(m)"
            >{{ missionMeta(m).glyph }} {{ missionMeta(m).label }}</button>
          }
        </div>

        <!-- Schiffs-Picker -->
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
            <p class="muted small">Keine Schiffe auf diesem Planeten. <a href="/shipyard">Werft →</a></p>
          }
        </div>

        @if (missionHint(); as h) {
          <p class="hint small">{{ h }}</p>
        }

        <!-- Cargo (Transport/Stationierung) -->
        @if (showCargo()) {
          <div class="cargo">
            <div class="cargo-title">📦 Fracht</div>
            <div class="cargo-row">
              @for (r of cargoFields; track r.key) {
                <div class="cargo-field">
                  <label>{{ r.glyph }} {{ r.label }}</label>
                  <input type="number" min="0" [max]="planetRes()?.[r.key]?.amount ?? 0"
                    [ngModel]="cargo()[r.key]" (ngModelChange)="setCargo(r.key, $event)" />
                  <button class="btn btn-ghost btn-sm" type="button"
                    (click)="setCargo(r.key, planetRes()?.[r.key]?.amount ?? 0)">max</button>
                </div>
              }
            </div>
          </div>
        }

        <!-- Handelsauftrag -->
        @if (showTrade()) {
          <div class="cargo">
            <div class="cargo-title">💱 Handelsauftrag</div>
            <div class="trade-grid">
              <div class="field">
                <label>Biete</label>
                <select [ngModel]="offerRes()" (ngModelChange)="offerRes.set($event)">
                  @for (r of cargoFields; track r.key) { <option [ngValue]="r.key">{{ r.glyph }} {{ r.label }}</option> }
                </select>
                <input type="number" min="0" [max]="planetRes()?.[offerRes()]?.amount ?? 0"
                  [ngModel]="offerAmount()" (ngModelChange)="offerAmount.set(+$event || 0)" aria-label="Angebotsmenge" />
              </div>
              <div class="field">
                <label>Erhalte</label>
                <select [ngModel]="wantRes()" (ngModelChange)="wantRes.set($event)">
                  @for (r of cargoFields; track r.key) { <option [ngValue]="r.key">{{ r.glyph }} {{ r.label }}</option> }
                </select>
                @if (merchantIntel(); as mi) {
                  @if (mi.trade_center) {
                    <span class="muted small">💱 Handelszentrum · globaler Handelskurs</span>
                  } @else {
                    <span class="muted small">Spez.: {{ mi.spec }} · Kurse vom letzten Besuch</span>
                  }
                } @else {
                  <span class="muted small">Richtwert: globaler Handelskurs</span>
                }
              </div>
            </div>
            @if (tradeEstimate(); as est) {
              <p class="trade-preview small">≈ <strong>{{ est }}</strong> {{ wantRes() }} (ungefähr, vor Slippage/Reputation)</p>
            }
            @if (offerRes() === wantRes()) {
              <p class="hint small">Biete- und Wunsch-Ressource müssen verschieden sein.</p>
            }
            @if (coveringEscorts().length) {
              <div class="escorts">
                <div class="cargo-title">🛡 Eskorte auf der Route</div>
                @for (e of coveringEscorts(); track e.id) {
                  <label class="escort-row small">
                    <input type="checkbox" [checked]="chosenEscorts().has(e.id)" (change)="toggleEscort(e.id)" />
                    {{ e.owner }} [{{ e.coords }}] · Kraft ~{{ e.power }} · {{ (e.fee_pct * 100).toFixed(1) }}% Gebühr
                  </label>
                }
              </div>
            }
            <p class="muted small">🛡 Frachter ohne bewaffnete Eskorte werden auf der Route überfallen.</p>
          </div>
        }

        <!-- Commander + Tempo -->
        <div class="opts">
          <div class="field">
            <label>Commander</label>
            <select [ngModel]="commanderId()" (ngModelChange)="commanderId.set($event)">
              <option [ngValue]="null">— ohne —</option>
              @for (c of assignableCommanders(); track c.id) {
                <option [ngValue]="c.id">{{ rankMeta(c.rank).glyph }} {{ c.name }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label class="tip" data-tip="Langsamer = weniger Sprit">Tempo {{ speed() }}%</label>
            <input type="range" min="10" max="100" step="10" [ngModel]="speed()" (ngModelChange)="speed.set($event)" />
          </div>
        </div>
        @if (commanderId() && commanderAbilities().abilities.length) {
          <div class="escorts">
            <div class="cargo-title">⚡ Fähigkeiten scharf ({{ armed().size }}/{{ commanderAbilities().slots }})</div>
            @for (a of commanderAbilities().abilities; track a.key) {
              <label class="escort-row small">
                <input type="checkbox" [checked]="armed().has(a.key)" (change)="toggleArmed(a.key)" />
                {{ abilityLabel(a.key) }} · Stufe {{ a.level }}
              </label>
            }
          </div>
        }

        @if (mission() === 'expedition') {
          <div class="field">
            @if (maxExpHours() > 0) {
              <label class="tip" data-tip="Länger = mehr Ertrag, aber mehr Risiko (Piraten/Aliens/Schwarzes Loch). Forschung Astrophysik hebt das Maximum (bis 24h).">
                🌌 Verweildauer {{ expHours() }} / {{ maxExpHours() }} h
              </label>
              <input type="range" min="1" [max]="maxExpHours()" step="1" [ngModel]="expHours()" (ngModelChange)="setExpHours($event)" />
            } @else {
              <p class="hint small">Astrophysik Stufe 1 nötig, um Expeditionen in die galaktischen Weiten zu entsenden.</p>
            }
          </div>
        }

        @if (rangeInfo(); as r) {
          <div class="range-info small" [class.out]="!r.inRange">
            <span class="tip" data-tip="Distanz zwischen Startplanet und Ziel (OGame-Distanzmodell)">📏 Distanz {{ r.distance.toLocaleString('de-DE') }}</span>
            <span class="tip" [attr.data-tip]="'Reichweite der Flotte (Tank). Limitierendes Schiff: ' + shipLabel(r.limiting)">🛰 Reichweite {{ r.maxRangeText }}</span>
            <span class="tip" data-tip="Treibstoff (Deuterium) vom Startplaneten">🛢️ {{ r.fuel.toLocaleString('de-DE') }} {{ r.roundTrip ? '(Hin+Rück)' : '(einfach)' }}</span>
          </div>
        }

        <div class="actions">
          <button class="btn btn-primary" type="button" [disabled]="!canSend() || sending()" (click)="send()">
            {{ sending() ? 'Sende…' : (missionMeta(mission()).glyph + ' ' + missionMeta(mission()).label + ' starten') }}
          </button>
        </div>
        @if (!hasSelection()) {
          <p class="hint small">Mindestens ein Schiff auswählen.</p>
        } @else if (rangeInfo(); as r) {
          @if (!r.inRange) {
            <p class="hint small">Außer Reichweite: {{ shipLabel(r.limiting) }} schafft nur {{ r.maxRangeText }} (Hin+Rück). Kürzeres Ziel wählen, das schwächste Schiff weglassen oder per Stationierung vorschieben.</p>
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
        position: relative; width: 100%; max-width: 560px; max-height: 88vh; overflow-y: auto;
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
      .tname { color: var(--text-dim); font-size: var(--fs-sm); }

      .mission-tabs { display: flex; flex-wrap: wrap; gap: var(--sp-1); margin: var(--sp-3) 0; }
      .mtab {
        font-size: var(--fs-sm); padding: var(--sp-1) var(--sp-3); border-radius: var(--r-pill);
        background: rgba(255,255,255,0.04); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer;
        transition: color var(--motion-fast) var(--ease-out), border-color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .mtab:hover { color: var(--text); border-color: var(--border-strong); }
      .mtab.active { background: var(--accent-soft); color: var(--accent); border-color: var(--accent-dim); }

      .ships {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: var(--sp-2); margin-top: var(--sp-1);
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

      .cargo { margin-top: var(--sp-3); }
      .cargo-title { font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); margin-bottom: var(--sp-1); }
      .cargo-row { display: flex; flex-wrap: wrap; gap: var(--sp-3); }
      .cargo-field { display: flex; flex-direction: column; gap: var(--sp-1); flex: 1 1 130px; }
      .cargo-field label { font-size: var(--fs-xs); color: var(--text-dim); }
      .cargo-field input { min-height: 30px; }

      .opts { display: flex; flex-wrap: wrap; gap: var(--sp-3); margin-top: var(--sp-3); }
      .opts .field { flex: 1 1 200px; display: flex; flex-direction: column; gap: var(--sp-1); }
      .opts label { font-size: var(--fs-xs); color: var(--text-dim); }

      .trade-grid { display: flex; flex-wrap: wrap; gap: var(--sp-3); }
      .trade-grid .field { flex: 1 1 200px; display: flex; flex-direction: column; gap: var(--sp-1); }
      .trade-grid select, .trade-grid input { min-height: 30px; }
      .trade-preview { color: var(--accent); margin: var(--sp-2) 0 0; }
      .escorts { margin-top: var(--sp-2); }
      .escort-row { display: flex; align-items: center; gap: var(--sp-1); padding: 2px 0; cursor: pointer; }

      .actions { margin-top: var(--sp-4); }
      .actions .btn { width: 100%; }
      .hint { color: var(--warn); margin: var(--sp-1) 0 0; }
      .range-info { display: flex; flex-wrap: wrap; gap: var(--sp-1) var(--sp-3); margin-top: var(--sp-3); padding: var(--sp-1) var(--sp-3); border: 1px solid var(--border); border-radius: var(--r-sm); color: var(--text-dim); }
      .range-info.out { border-color: var(--warn); color: var(--warn); }

      @media (max-width: 560px) {
        .backdrop { padding: var(--sp-2); }
        .popup { max-width: 100%; max-height: 94vh; padding: var(--sp-4); }
      }
    `,
  ],
})
export class FleetDispatchComponent {
  private readonly api = inject(ApiService);
  private readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly balanceSvc = inject(BalanceService);

  readonly target = input.required<Coordinate>();
  readonly targetName = input<string | null>(null);
  readonly initialMission = input<FleetMission>('attack');
  /** 'moon' -> Angriff/Spionage zielt auf den Mond statt den Planeten an der Koordinate. */
  readonly targetType = input<'moon' | null>(null);

  readonly close = output<void>();
  readonly sent = output<void>();

  /** Missionswahl: am Deep-Space-Slot (Position 16) NUR Expedition, sonst die normalen Missionen. */
  protected readonly missions = computed<FleetMission[]>(() => {
    const deep = this.bnum((this.balanceSvc.value as any)?.expedition?.deep_space_position);
    if (deep && this.target().position === deep) {
      return ['expedition'];
    }
    return ['attack', 'transport', 'spy', 'deploy', 'colonize', 'mine', 'trade'];
  });
  protected readonly mission = linkedSignal<FleetMission>(() => this.initialMission());

  protected readonly cargoFields = [
    { key: 'metal' as const, glyph: '⛏️', label: 'Metall' },
    { key: 'crystal' as const, glyph: '💎', label: 'Kristall' },
    { key: 'deuterium' as const, glyph: '🛢️', label: 'Deuterium' },
  ];

  protected readonly selection = signal<Record<string, number>>({});
  protected readonly cargo = signal<{ metal: number; crystal: number; deuterium: number }>({
    metal: 0, crystal: 0, deuterium: 0,
  });
  protected readonly commanderId = signal<string | null>(null);
  protected readonly speed = signal(100);
  protected readonly armed = signal<Set<string>>(new Set());
  protected readonly abilityCatalog = signal<Record<string, { label: string }>>({});
  protected readonly sending = signal(false);

  /** Erlernte Faehigkeiten des gewaehlten Kommandeurs (fuer die Scharfschalt-Auswahl). */
  protected readonly commanderAbilities = computed(() => {
    const id = this.commanderId();
    const c = this.assignableCommanders().find((x) => x.id === id);
    return c ? { abilities: c.abilities ?? [], slots: c.arm_slots ?? 1 } : { abilities: [], slots: 1 };
  });

  toggleArmed(key: string): void {
    this.armed.update((s) => {
      const next = new Set(s);
      if (next.has(key)) {
        next.delete(key);
      } else if (next.size < this.commanderAbilities().slots) {
        next.add(key);
      }
      return next;
    });
  }

  abilityLabel(key: string): string {
    return this.abilityCatalog()[key]?.label ?? key;
  }

  // --- Handel ---
  protected readonly offerRes = signal<'metal' | 'crystal' | 'deuterium'>('metal');
  protected readonly offerAmount = signal(0);
  protected readonly wantRes = signal<'metal' | 'crystal' | 'deuterium'>('deuterium');
  protected readonly merchantIntel = signal<GalaxyIntel | null>(null);
  /** Oeffentlicher globaler Handelskurs (Handelszentren) — immer verfuegbar. */
  protected readonly globalIndex = signal<TradeIndex | null>(null);
  /** Eskort-Angebote, die die Route decken (nur Handel relevant). */
  protected readonly escortOffers = signal<EscortOffer[]>([]);
  protected readonly chosenEscorts = signal<Set<string>>(new Set());

  /** Eskort-Angebote, deren Station die Route (Origin↔Ziel) im Radius schneidet. */
  protected readonly coveringEscorts = computed<EscortOffer[]>(() => {
    const t = this.target();
    const p = this.state.activePlanet();
    if (!p) {
      return [];
    }
    const lo = Math.min(p.system, t.system);
    const hi = Math.max(p.system, t.system);
    return this.escortOffers().filter(
      (o) => o.galaxy === t.galaxy && p.galaxy === t.galaxy && o.system >= lo - o.radius && o.system <= hi + o.radius,
    );
  });

  protected readonly showTrade = computed(() => this.mission() === 'trade');

  /** Ist das Ziel ein (oeffentliches) Handelszentrum mit globalem Kurs? */
  protected readonly isCenter = computed(() => !!this.merchantIntel()?.trade_center);

  /**
   * Massgebliche Kurse fuer die Vorschau: lokaler Legacy-Haendler-Snapshot, falls
   * vorhanden; sonst der immer verfuegbare globale Index (Handelszentren).
   */
  protected readonly effPrices = computed<{ metal?: number; crystal?: number; deuterium?: number } | null>(() => {
    const local = this.merchantIntel();
    if (local && !local.trade_center && local.prices) {
      return local.prices;
    }
    return this.globalIndex()?.prices ?? local?.prices ?? null;
  });

  /**
   * Grobe Vorschau aus den massgeblichen Kursen (OHNE Slippage/Reputation — der echte
   * Tausch wird serverseitig bei Ankunft berechnet).
   */
  protected readonly tradeEstimate = computed<number | null>(() => {
    const p = this.effPrices();
    if (!p) {
      return null;
    }
    const pIn = p[this.offerRes()] ?? 0;
    const pOut = p[this.wantRes()] ?? 0;
    if (pIn <= 0 || pOut <= 0 || this.offerAmount() <= 0) {
      return null;
    }
    return Math.round(this.offerAmount() * (pIn / pOut) * 0.96); // 0.96 ≈ Standard-Marge
  });

  private readonly missionRequires: Partial<Record<FleetMission, { type: string; label: string }>> = {
    spy: { type: 'spy_probe', label: 'Spionagesonde' },
    colonize: { type: 'colony_ship', label: 'Kolonieschiff' },
    mine: { type: 'miner', label: 'Bergbauschiff' },
    expedition: { type: 'expedition_ship', label: 'Expeditionsschiff' },
  };

  toggleEscort(id: string): void {
    this.chosenEscorts.update((s) => {
      const next = new Set(s);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  constructor() {
    // Globalen Handelskurs laden (immer verfuegbar — keine Aufklaerung noetig).
    this.api.getTradeIndex().subscribe((idx) => this.globalIndex.set(idx));
    // Eskort-Angebote (fuer die Routen-Auswahl im Handel) laden.
    this.api.getEscortOffers().subscribe((list) => this.escortOffers.set(list));
    // Faehigkeiten-Katalog (fuer Labels der Scharfschalt-Auswahl).
    this.api.getAbilityCatalog().subscribe((c) => this.abilityCatalog.set(c.catalog as Record<string, { label: string }>));
    // Astrophysik-Stufe (begrenzt die Expeditions-Verweildauer).
    this.api.getResearch().subscribe((r) => {
      const astro = (r.research ?? []).find((x) => x.type === 'astrophysics');
      this.astroLevel.set(astro?.level ?? 0);
    });
    // Kurs-Schnappschuss/Typ des Zielhaendlers laden (Handelszentrum vs. Legacy).
    effect(() => {
      const t = this.target();
      this.api.getGalaxyTargets().subscribe((list) => {
        const hit = list.find(
          (x) => x.galaxy === t.galaxy && x.system === t.system && x.position === t.position,
        );
        this.merchantIntel.set(hit?.intel?.merchant ? (hit.intel as GalaxyIntel) : null);
      });
    });
  }

  protected readonly availableShips = computed<PlanetUnit[]>(
    () => this.state.activePlanet()?.ships?.filter((s) => s.count > 0) ?? [],
  );
  protected readonly planetRes = computed(() => this.state.activePlanet()?.resources ?? null);
  protected readonly assignableCommanders = computed(() =>
    this.state.commanders().filter((c) => c.status !== 'training' && !c.assigned_fleet_id),
  );

  protected readonly showCargo = computed(
    () => this.mission() === 'transport' || this.mission() === 'deploy',
  );
  protected readonly hasSelection = computed(() =>
    Object.values(this.selection()).some((n) => n > 0),
  );
  protected readonly missionHint = computed<string | null>(() => {
    const req = this.missionRequires[this.mission()];
    if (!req) {
      return null;
    }
    return this.shipCount(req.type) > 0 ? null : `Diese Mission benötigt mindestens ein ${req.label}.`;
  });
  protected readonly canSend = computed(() => {
    if (!this.hasSelection() || !this.state.activePlanetId() || this.missionHint()) {
      return false;
    }
    if (this.rangeInfo()?.inRange === false) {
      return false;
    }
    if (this.mission() === 'expedition') {
      return this.maxExpHours() > 0;
    }
    if (this.mission() === 'trade') {
      return this.offerAmount() > 0 && this.offerRes() !== this.wantRes();
    }
    return true;
  });

  // -- Treibstoff-Tank: Reichweite (Hin+Rück) + Spritkosten, gespiegelt aus fleet/service.py ----
  private bnum(v: unknown, d = 0): number {
    return typeof v === 'number' ? v : d;
  }

  /** Max. einfache Distanz eines Schiffstyps mit vollem Tank (round_trip = Hin+Rück). */
  private shipRange(type: string, roundTrip: boolean): number {
    const bal = this.balanceSvc.value as any;
    const cfg = bal?.ships?.[type];
    if (!cfg) return Infinity;
    const fuel = this.bnum(cfg.fuel);
    if (fuel <= 0) return Infinity; // ortsfest -> keine Begrenzung
    const f = bal.fleet;
    const legs = roundTrip ? 2 : 1;
    return (this.bnum(cfg.fuel_tank) * this.bnum(f.speed_factor)) / (fuel * this.bnum(f.fuel_per_distance_unit) * legs);
  }

  /** OGame-Distanzmodell (balance.fleet.distance), gespiegelt aus compute_distance. */
  private distanceTo(): number | null {
    const p = this.state.activePlanet();
    const t = this.target();
    const bal = this.balanceSvc.value as any;
    const d = bal?.fleet?.distance;
    if (!p || !d) return null;
    if (p.galaxy !== t.galaxy) return this.bnum(d.inter_galaxy_per_galaxy) * Math.abs(p.galaxy - t.galaxy);
    if (p.system !== t.system) return this.bnum(d.same_galaxy_base) + this.bnum(d.same_galaxy_per_system) * Math.abs(p.system - t.system);
    if (p.position !== t.position) return this.bnum(d.same_system_base) + this.bnum(d.same_system_per_position) * Math.abs(p.position - t.position);
    return this.bnum(d.same_position);
  }

  protected readonly rangeInfo = computed<{
    distance: number; maxRange: number; maxRangeText: string;
    limiting: string | null; fuel: number; roundTrip: boolean; inRange: boolean;
  } | null>(() => {
    const entries = Object.entries(this.selection()).filter(([, n]) => n > 0);
    const dist = this.distanceTo();
    if (!entries.length || dist === null) return null;
    const roundTrip = this.mission() !== 'deploy';
    let maxRange = Infinity;
    let limiting: string | null = null;
    for (const [type] of entries) {
      const r = this.shipRange(type, roundTrip);
      if (r < maxRange) { maxRange = r; limiting = type; }
    }
    const bal = this.balanceSvc.value as any;
    const f = bal?.fleet;
    const legs = roundTrip ? 2 : 1;
    let total = 0;
    for (const [type, n] of entries) total += this.bnum(bal?.ships?.[type]?.fuel) * n;
    const fuel = Math.max(1, Math.ceil((total * dist) / this.bnum(f?.speed_factor, 1) * this.bnum(f?.fuel_per_distance_unit, 1) * legs));
    return {
      distance: dist,
      maxRange,
      maxRangeText: maxRange === Infinity ? '∞' : Math.floor(maxRange).toLocaleString('de-DE'),
      limiting,
      fuel,
      roundTrip,
      inRange: dist <= maxRange,
    };
  });

  shipLabel(type: string | null): string {
    return type ? metaFor(SHIP_META, type).label : '';
  }

  // -- Expedition: Verweildauer (1..max, max aus Astrophysik) -------------------
  protected readonly astroLevel = signal(0);
  protected readonly expHours = signal(1);

  /** Maximale Verweildauer = min(astrophysics * per_level, hour_cap); 0 = nicht freigeschaltet. */
  protected readonly maxExpHours = computed(() => {
    const dur = (this.balanceSvc.value as any)?.expedition?.duration ?? {};
    const per = this.bnum(dur.max_hours_per_astro_level, 1);
    const cap = this.bnum(dur.hour_cap, 24);
    return Math.max(0, Math.min(cap, Math.floor(this.astroLevel() * per)));
  });

  setExpHours(v: number): void {
    const mx = this.maxExpHours();
    this.expHours.set(Math.max(1, Math.min(mx || 1, Math.floor(v || 1))));
  }

  shipCount(type: string): number {
    return this.selection()[type] ?? 0;
  }

  setShip(type: string, value: number, max: number): void {
    const n = Math.max(0, Math.min(max, Math.floor(value || 0)));
    this.selection.update((s) => ({ ...s, [type]: n }));
  }

  setCargo(key: 'metal' | 'crystal' | 'deuterium', value: number): void {
    const cap = Math.floor(this.planetRes()?.[key]?.amount ?? 0);
    const n = Math.max(0, Math.min(cap, Math.floor(value || 0)));
    this.cargo.update((c) => ({ ...c, [key]: n }));
  }

  send(): void {
    const origin = this.state.activePlanetId();
    if (!origin || !this.canSend()) {
      return;
    }
    const ships: Record<string, number> = {};
    for (const [type, n] of Object.entries(this.selection())) {
      if (n > 0) {
        ships[type] = n;
      }
    }
    const cargo = this.showCargo()
      ? this.cargo()
      : { metal: 0, crystal: 0, deuterium: 0 };
    const body: FleetSendRequest = {
      origin_planet_id: origin,
      target: this.target(),
      mission: this.mission(),
      ships,
      cargo,
      commander_id: this.commanderId(),
      speed_pct: this.speed(),
      ability_keys: [...this.armed()],
    };
    if (this.mission() === 'expedition') {
      body.expedition_hours = this.expHours();
    }
    if (this.targetType() === 'moon') {
      body.target_type = 'moon';
    }
    if (this.mission() === 'trade') {
      // Angebots-Ressource faehrt als Fracht mit; der Server baut Cargo + mission_data.
      body.offer_res = this.offerRes();
      body.offer_amount = this.offerAmount();
      body.want_res = this.wantRes();
      const escorts = [...this.chosenEscorts()].filter((id) =>
        this.coveringEscorts().some((e) => e.id === id),
      );
      if (escorts.length) {
        body.escort_ids = escorts;
      }
    }
    this.sending.set(true);
    this.api
      .sendFleet(body)
      .subscribe({
        next: () => {
          this.sending.set(false);
          this.notify.success('Flotte gestartet', `Mission ${this.missionMeta(this.mission()).label} unterwegs.`);
          void this.state.reloadFleets();
          void this.state.reloadActivePlanet();
          void this.state.reloadCommanders();
          this.sent.emit();
          this.close.emit();
        },
        error: (err) => {
          this.sending.set(false);
          this.notify.warning('Start fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
        },
      });
  }

  shipMeta = (t: string) => metaFor(SHIP_META, t);
  missionMeta = (m: string) => metaFor(MISSION_META, m);
  rankMeta = (r: string) => metaFor(RANK_META, r);
}
