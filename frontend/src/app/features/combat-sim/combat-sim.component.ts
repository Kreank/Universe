import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { GameStateService } from '../../core/services/game-state.service';
import { CombatSimPreloadService } from '../../core/services/combat-sim-preload.service';
import { CombatReport, Commander } from '../../core/models/api.models';
import { DEFENSE_META, SHIP_META, metaFor } from '../../core/models/display';
import { navIcon, statIcon, statusIcon, uiIcon } from '../../core/models/icon-assets';
import { CombatReportComponent } from '../transmissions/combat-report.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';

/** Eine waehlbare Einheit im Picker (Schiff oder Verteidigung). */
interface PickRow {
  type: string;
  label: string;
  glyph: string;
  /** Asset-Pfad des echten Einheiten-Bildes (Fallback: glyph via icon-tile). */
  icon: string;
}

/**
 * Kampf-Simulator: eine Was-waere-wenn-Schlacht ohne jeden Spielstand-Effekt.
 *
 * Der Spieler stellt eine eigene Flotte und einen Gegner (Schiffe + Verteidigung)
 * zusammen; der Server rechnet mit der ECHTEN Forschung des Spielers (Gegner-Tech = 0)
 * und liefert einen vollwertigen Kampfbericht, den der bestehende Viewer rendert.
 */
@Component({
  selector: 'app-combat-sim',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, CombatReportComponent, IconTileComponent, BtnIconComponent],
  template: `
    <section class="sim">
      <header class="sim-head">
        <h1><app-btn-icon [src]="navIcon('simulator')" glyph="⚔️" [size]="18" /> Kampf-Simulator</h1>
        <p class="faint small">
          Nutzt deine aktuelle Forschung; Gegner-Tech = 0. Das Ergebnis ist eine Stichprobe —
          erneut simulieren für Varianz.
        </p>
      </header>

      @if (!balanceLoaded()) {
        <p class="state">Balance lädt …</p>
      } @else {
        <!-- Kampfrichtung: greife ich an oder verteidige ich? -->
        <div class="mode-switch" role="tablist">
          <button type="button" class="ms-btn" [class.active]="mode() === 'attack'" (click)="setMode('attack')">🗡 Ich greife an</button>
          <button type="button" class="ms-btn" [class.active]="mode() === 'defense'" (click)="setMode('defense')">🛡 Ich verteidige mich</button>
        </div>
        <p class="faint small mode-hint">
          {{ mode() === 'defense'
            ? 'Du wirst angegriffen: stelle deine verteidigenden Schiffe + Verteidigungsanlagen ein, der Gegner greift mit seiner Flotte an.'
            : 'Du greifst an: stelle deine Angriffsflotte ein, der Gegner verteidigt mit Schiffen + Verteidigung.' }}
        </p>

        <div class="cols">
          <!-- DEINE Seite: Schiffe (+ Verteidigung im Verteidigungs-Modus) -->
          <div class="card col side-own">
            <div class="panel-title">
              <app-btn-icon [src]="statIcon('shield')" glyph="🛡" [size]="16" /> {{ mode() === 'defense' ? 'Deine Verteidigung' : 'Deine Flotte' }}
              @if (ownTotal()) { <span class="ptotal mono">{{ ownTotal() }}</span> }
              <button class="mini" type="button" [disabled]="!garrisonCombat().length"
                title="Schiffe vom aktiven Planeten übernehmen" (click)="fillOwnFromFleet()"><app-btn-icon [src]="navIcon('fleet')" glyph="🚀" /> Meine Flotte</button>
            </div>

            @if (mode() === 'defense') { <div class="sub-head">Schiffe (Garnison)</div> }
            @for (s of combatShips(); track s.type) {
              <label class="row">
                <app-icon-tile class="r-ico" [glyph]="s.glyph" [src]="s.icon" [size]="36" variant="accent" />
                <span class="r-label">{{ s.label }}</span>
                <input
                  type="number"
                  min="0"
                  class="r-num"
                  [ngModel]="ownCounts()[s.type] ?? null"
                  (ngModelChange)="setCount('own', s.type, $event)"
                  placeholder="0"
                />
              </label>
            }

            @if (mode() === 'defense') {
              <div class="sub-head">
                Verteidigung
                <button class="mini" type="button" [disabled]="!garrisonDefense().length"
                  title="Verteidigung vom aktiven Planeten übernehmen" (click)="fillOwnDefFromPlanet()"><app-btn-icon [src]="navIcon('defense')" glyph="🛡" /> Meine Verteidigung</button>
              </div>
              @for (d of defenses(); track d.type) {
                <label class="row">
                  <app-icon-tile class="r-ico" [glyph]="d.glyph" [src]="d.icon" [size]="36" variant="accent" />
                  <span class="r-label">{{ d.label }}</span>
                  <input
                    type="number"
                    min="0"
                    class="r-num"
                    [ngModel]="ownDefCounts()[d.type] ?? null"
                    (ngModelChange)="setCount('ownDef', d.type, $event)"
                    placeholder="0"
                  />
                </label>
              }
            }
          </div>

          <!-- GEGNER-Seite: Schiffe (+ Verteidigung nur wenn du angreifst) + Tech -->
          <div class="card col side-enemy">
            <div class="panel-title">
              <app-btn-icon [src]="statusIcon('attack')" glyph="⚔" [size]="16" /> {{ mode() === 'defense' ? 'Angreifer' : 'Gegner' }}
              @if (enemyTotal()) { <span class="ptotal mono">{{ enemyTotal() }}</span> }
            </div>
            @if (presetLabel(); as pl) {
              <p class="tech-hint faint">📡 Aus Spionagebericht übernommen: {{ pl }} — Werte ggf. anpassen.</p>
            }

            <div class="sub-head">Schiffe</div>
            @for (s of combatShips(); track s.type) {
              <label class="row">
                <app-icon-tile class="r-ico" [glyph]="s.glyph" [src]="s.icon" [size]="36" variant="magenta" />
                <span class="r-label">{{ s.label }}</span>
                <input
                  type="number"
                  min="0"
                  class="r-num"
                  [ngModel]="enemyShipCounts()[s.type] ?? null"
                  (ngModelChange)="setCount('enemyShip', s.type, $event)"
                  placeholder="0"
                />
              </label>
            }

            @if (mode() === 'attack') {
              <div class="sub-head">Verteidigung</div>
              @for (d of defenses(); track d.type) {
                <label class="row">
                  <app-icon-tile class="r-ico" [glyph]="d.glyph" [src]="d.icon" [size]="36" variant="magenta" />
                  <span class="r-label">{{ d.label }}</span>
                  <input
                    type="number"
                    min="0"
                    class="r-num"
                    [ngModel]="enemyDefCounts()[d.type] ?? null"
                    (ngModelChange)="setCount('enemyDef', d.type, $event)"
                    placeholder="0"
                  />
                </label>
              }
            }

            <div class="sub-head">Forschung des {{ mode() === 'defense' ? 'Angreifers' : 'Gegners' }}</div>
            <p class="tech-hint faint">Leer = Stufe 0 (unerforscht). Bestimmt Angriff/Schild/Hülle des Gegners.</p>
            <div class="tech-grid">
              @for (t of enemyTechFields; track t.key) {
                <label class="tech-row">
                  <span class="tech-label">{{ t.label }}</span>
                  <input
                    type="number"
                    min="0"
                    class="tech-num"
                    [ngModel]="enemyTech()[t.key] ?? null"
                    (ngModelChange)="setEnemyTech(t.key, $event)"
                    placeholder="0"
                  />
                </label>
              }
            </div>
          </div>
        </div>

        <!-- Optionaler eigener Commander (Moral-Bonus + Schiffsboni wie im echten Kampf) -->
        @if (commanders().length) {
          <div class="card cmd-box">
            <label class="cmd-toggle">
              <input type="checkbox" [ngModel]="useCommander()" (ngModelChange)="useCommander.set($event)" />
              <span><app-btn-icon [src]="navIcon('commanders')" glyph="🎖" [size]="16" /> Mit Commander rechnen</span>
            </label>
            @if (useCommander()) {
              <select class="cmd-select" [ngModel]="selectedCommanderId()" (ngModelChange)="selectedCommanderId.set($event)">
                @for (c of commanders(); track c.id) {
                  <option [value]="c.id">{{ c.name }} · {{ c.specialization }} · Moral {{ c.morale }}</option>
                }
              </select>
              <p class="tech-hint faint">Rechnet Moral-Band + schiffsklassen-spezifische Boni des Commanders auf deine Flotte.</p>
            }
          </div>
        }

        <div class="actions">
          <button
            class="btn btn-primary"
            [disabled]="!canSimulate() || pending()"
            (click)="simulate()"
          >
            <app-btn-icon [src]="navIcon('simulator')" glyph="⚔️" [size]="18" /> {{ pending() ? 'Simuliere …' : 'Simulieren' }}
          </button>
          <button class="btn btn-ghost" type="button" (click)="clearAll()"><app-btn-icon [src]="uiIcon('broom')" glyph="🧹" /> Leeren</button>
          @if (error()) {
            <span class="err">{{ error() }}</span>
          }
        </div>
      }
    </section>

    @if (result(); as r) {
      <app-combat-report [report]="r" (close)="result.set(null)" />
    }
  `,
  styles: [`
    .sim { display: flex; flex-direction: column; gap: var(--sp-4); }
    .sim-head h1 { font-family: var(--font-display); }
    .small { font-size: var(--fs-sm); }
    .state { color: var(--text-dim); padding: var(--sp-5) 0; }

    /* Kampfrichtung-Umschalter (segmentiert). */
    .mode-switch { display: inline-flex; gap: 2px; padding: 3px; border-radius: var(--r-md);
      background: rgba(255,255,255,0.04); border: 1px solid var(--border); }
    .ms-btn { padding: var(--sp-2) var(--sp-4); min-height: 40px; border: none; cursor: pointer;
      border-radius: var(--r-sm); background: transparent; color: var(--text-dim);
      font-family: var(--font); font-size: var(--fs-sm); font-weight: 600;
      transition: background var(--motion-fast) var(--ease-out), color var(--motion-fast) var(--ease-out); }
    .ms-btn:hover { color: var(--text); }
    .ms-btn.active { background: var(--accent); color: #04201d; }
    .mode-hint { margin: var(--sp-2) 0 0; }

    .cols { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-4); align-items: start; }
    .col { display: flex; flex-direction: column; gap: var(--sp-1); min-width: 0; }

    /* Seiten-Semantik: eigene Flotte = Akzent (Cyan), Gegner = Gefahr (Magenta). */
    .side-own { border-top: 2px solid var(--accent); }
    .side-enemy { border-top: 2px solid var(--danger-dim); }

    .sub-head {
      font-family: var(--font-display);
      font-size: var(--fs-xs); letter-spacing: 0.1em; text-transform: uppercase;
      color: var(--text-dim); margin: var(--sp-3) 0 var(--sp-2);
    }

    /* Panel-Überschrift mit Summen-Badge + Mini-Aktion rechts. */
    .panel-title { justify-content: flex-start; }
    .ptotal {
      margin-left: var(--sp-1);
      font-family: var(--mono); font-variant-numeric: tabular-nums;
      font-size: var(--fs-xs); color: var(--accent);
      background: var(--accent-soft);
      border: 1px solid var(--accent-dim); border-radius: var(--r-pill);
      padding: 2px var(--sp-2);
    }
    .side-enemy .ptotal {
      color: var(--danger);
      background: color-mix(in srgb, var(--danger) 12%, transparent);
      border-color: var(--danger-dim);
    }
    .mini {
      margin-left: auto; text-transform: none; letter-spacing: 0;
      font-family: var(--font); font-size: var(--fs-xs); font-weight: 600;
      color: var(--accent); background: var(--accent-soft);
      border: 1px solid var(--accent-dim); border-radius: var(--r-md);
      min-height: 44px; padding: var(--sp-1) var(--sp-3); cursor: pointer;
      transition: background var(--motion-fast) var(--ease-out),
        box-shadow var(--motion-fast) var(--ease-out);
    }
    .mini:hover:not(:disabled) { background: rgba(47,227,210,0.18); box-shadow: var(--glow-soft); }
    .mini:disabled { opacity: 0.4; cursor: not-allowed; }

    .row { display: grid; grid-template-columns: 40px 1fr 5rem; align-items: center;
      gap: var(--sp-3); padding: var(--sp-1); border-radius: var(--r-sm);
      transition: background var(--motion-fast) var(--ease-out); cursor: pointer; }
    .row:hover { background: rgba(255,255,255,0.03); }
    .r-ico { display: inline-flex; justify-self: center; }
    .r-label { font-size: var(--fs-base); color: var(--text); }
    .r-num { width: 100%; text-align: right;
      font-family: var(--mono); font-variant-numeric: tabular-nums; }

    .actions { display: flex; align-items: center; gap: var(--sp-3); flex-wrap: wrap;
      position: sticky; bottom: 0; padding-top: var(--sp-2); margin-top: var(--sp-2); }
    .err { color: var(--danger); font-size: var(--fs-sm); }

    /* Gegner-Forschung: kompaktes Label-+-Zahl-Raster. */
    .tech-hint { font-size: var(--fs-xs); margin: 0 0 var(--sp-2); }
    .tech-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-1) var(--sp-3); }
    .tech-row { display: grid; grid-template-columns: 1fr 4rem; align-items: center; gap: var(--sp-2);
      padding: var(--sp-1); border-radius: var(--r-sm); }
    .tech-label { font-size: var(--fs-sm); color: var(--text-dim); }
    .tech-num { width: 100%; text-align: right;
      font-family: var(--mono); font-variant-numeric: tabular-nums; }

    /* Commander-Box (volle Breite unter den beiden Spalten). */
    .cmd-box { display: flex; flex-direction: column; gap: var(--sp-2); border-top: 2px solid var(--accent); }
    .cmd-toggle { display: flex; align-items: center; gap: var(--sp-2); cursor: pointer;
      font-size: var(--fs-base); color: var(--text); }
    .cmd-toggle input { width: 18px; height: 18px; flex: 0 0 auto; }
    .cmd-select { max-width: 360px; min-height: 40px; }

    @media (max-width: 700px) {
      .tech-grid { grid-template-columns: 1fr; }
    }

    @media (max-width: 700px) {
      .cols { grid-template-columns: 1fr; }
      .row { grid-template-columns: 40px 1fr 4.5rem; }
    }

    /* Desktop-Dichte (OGame-Stil): kompaktere Mini-Aktion ab Maus-Breite. */
    @media (min-width: 900px) {
      .mini { min-height: 32px; }
    }
  `],
})
export class CombatSimComponent {
  private readonly api = inject(ApiService);
  private readonly balance = inject(BalanceService);
  private readonly state = inject(GameStateService);
  private readonly preload = inject(CombatSimPreloadService);

  /** Asset-Pfad-Helfer fuers Template (Buttons mit Glyph-Fallback via app-btn-icon). */
  protected readonly navIcon = navIcon;
  protected readonly uiIcon = uiIcon;
  protected readonly statIcon = statIcon;
  protected readonly statusIcon = statusIcon;

  /** Kampfrichtung: greife ich an, oder werde ich angegriffen (verteidige ich)? */
  protected readonly mode = signal<'attack' | 'defense'>('attack');

  protected readonly ownCounts = signal<Record<string, number>>({});
  /** Eigene Verteidigungsanlagen — nur im Verteidigungs-Modus relevant. */
  protected readonly ownDefCounts = signal<Record<string, number>>({});
  protected readonly enemyShipCounts = signal<Record<string, number>>({});
  protected readonly enemyDefCounts = signal<Record<string, number>>({});

  /** Gegner-Forschung (Default 0 = unerforscht). Schlüssel = Tech-Keys der Engine. */
  protected readonly enemyTech = signal<Record<string, number>>({});

  /** Eigene Commander (nur einsatzbereite) für den optionalen Commander-Bonus. */
  protected readonly commanders = signal<Commander[]>([]);
  protected readonly useCommander = signal(false);
  protected readonly selectedCommanderId = signal<string | null>(null);

  protected readonly result = signal<CombatReport | null>(null);
  protected readonly pending = signal(false);
  protected readonly error = signal<string | null>(null);

  /** Einstellbare Gegner-Forschung (Kern-Kampftech + optionale Meisterschaften). */
  protected readonly enemyTechFields: { key: string; label: string }[] = [
    { key: 'weapons_tech', label: 'Waffentechnik' },
    { key: 'shield_tech', label: 'Schildtechnik' },
    { key: 'armor_tech', label: 'Panzerung' },
    { key: 'weapons_mastery', label: 'Waffen-Meisterschaft' },
    { key: 'shield_mastery', label: 'Schild-Meisterschaft' },
    { key: 'armor_mastery', label: 'Panzer-Meisterschaft' },
  ];

  constructor() {
    // Einsatzbereite eigene Commander laden (für den optionalen Commander-Bonus im Sim).
    this.api.getCommanders().subscribe({
      next: (list) => {
        const active = (list ?? []).filter((c) => c.status === 'active');
        this.commanders.set(active);
        this.selectedCommanderId.set(active[0]?.id ?? null);
      },
      error: () => this.commanders.set([]),
    });

    // Gegner-Voreinstellung aus einem Spionagebericht übernehmen (einmalig).
    const preset = this.preload.consume();
    if (preset) {
      this.mode.set('attack');
      this.enemyShipCounts.set({ ...preset.ships });
      this.enemyDefCounts.set({ ...preset.defenses });
      this.enemyTech.set({ ...preset.tech });
      this.presetLabel.set(preset.label ?? null);
    }
  }

  /** Notiz, woher die Gegner-Werte stammen (Spionagebericht), bis der Spieler etwas ändert. */
  protected readonly presetLabel = signal<string | null>(null);

  protected readonly balanceLoaded = computed(() => this.balance.value !== null);

  /** Kampf-Schiffe = bewaffnete Schiffe (combat_roster[typ].weapon_type gesetzt). */
  protected readonly combatShips = computed<PickRow[]>(() => {
    const bal = this.balance.value;
    if (!bal) {
      return [];
    }
    const roster = (bal as any)?.combat_roster ?? {};
    const out: PickRow[] = [];
    for (const type of Object.keys(bal.ships ?? {})) {
      const prof = roster[type];
      // Nur echte, bewaffnete Schiffe (Notiz-Keys wie `_note` haben kein Profil/Waffentyp).
      if (prof && typeof prof === 'object' && prof.weapon_type) {
        const meta = metaFor(SHIP_META, type);
        out.push({ type, label: meta.label, glyph: meta.glyph, icon: `assets/img/ships/${type}.png` });
      }
    }
    return out;
  });

  /** Verteidigungsanlagen (nur echte Konfigurationen, Notiz-Keys ausgefiltert). */
  protected readonly defenses = computed<PickRow[]>(() => {
    const bal = this.balance.value;
    if (!bal) {
      return [];
    }
    const out: PickRow[] = [];
    for (const [type, cfg] of Object.entries(bal.defenses ?? {})) {
      // Virtuelle Einheiten (z. B. Mond-Orbitalbatterie) sind nicht direkt baubar/wählbar.
      if (cfg && typeof cfg === 'object' && !(cfg as { virtual?: boolean }).virtual) {
        const meta = metaFor(DEFENSE_META, type);
        out.push({ type, label: meta.label, glyph: meta.glyph, icon: `assets/img/defenses/${type}.png` });
      }
    }
    return out;
  });

  protected readonly canSimulate = computed(() => {
    const defending = this.mode() === 'defense';
    const own = hasUnit(this.ownCounts()) || (defending && hasUnit(this.ownDefCounts()));
    // Im Verteidigungs-Modus bringt der Angreifer keine Verteidigung mit.
    const enemy = hasUnit(this.enemyShipCounts()) || (!defending && hasUnit(this.enemyDefCounts()));
    return own && enemy;
  });

  /** Summe ausgewählter Einheiten je Seite (für die Spalten-Überschrift). */
  protected readonly ownTotal = computed(
    () => sumCounts(this.ownCounts()) + (this.mode() === 'defense' ? sumCounts(this.ownDefCounts()) : 0),
  );
  protected readonly enemyTotal = computed(
    () => sumCounts(this.enemyShipCounts()) + (this.mode() === 'attack' ? sumCounts(this.enemyDefCounts()) : 0),
  );

  /** Kampf-Schiffe der aktiven Garnison (für „Meine Flotte übernehmen"). */
  protected readonly garrisonCombat = computed(() => {
    const valid = new Set(this.combatShips().map((s) => s.type));
    return (this.state.activePlanet()?.ships ?? []).filter((s) => s.count > 0 && valid.has(s.type));
  });

  /** Übernimmt die eigene Garnison als „Deine Flotte". */
  fillOwnFromFleet(): void {
    const next: Record<string, number> = {};
    for (const s of this.garrisonCombat()) {
      next[s.type] = s.count;
    }
    this.ownCounts.set(next);
  }

  /** Verteidigungsanlagen des aktiven Planeten (für „Meine Verteidigung übernehmen"). */
  protected readonly garrisonDefense = computed(() => {
    const valid = new Set(this.defenses().map((d) => d.type));
    return (this.state.activePlanet()?.defenses ?? []).filter((d) => d.count > 0 && valid.has(d.type));
  });

  /** Übernimmt die Planeten-Verteidigung als „Deine Verteidigung" (Verteidigungs-Modus). */
  fillOwnDefFromPlanet(): void {
    const next: Record<string, number> = {};
    for (const d of this.garrisonDefense()) {
      next[d.type] = d.count;
    }
    this.ownDefCounts.set(next);
  }

  /** Kampfrichtung umschalten; vorhandenes Ergebnis verwerfen (sonst irreführend). */
  setMode(m: 'attack' | 'defense'): void {
    this.mode.set(m);
    this.result.set(null);
  }

  /** Setzt beide Seiten (inkl. Gegner-Tech) zurück. */
  clearAll(): void {
    this.ownCounts.set({});
    this.ownDefCounts.set({});
    this.enemyShipCounts.set({});
    this.enemyDefCounts.set({});
    this.enemyTech.set({});
    this.result.set(null);
  }

  /** Gegner-Forschungsstufe setzen (negatives/leeres -> 0). */
  setEnemyTech(key: string, value: unknown): void {
    const n = Math.max(0, Math.floor(Number(value) || 0));
    this.enemyTech.update((m) => ({ ...m, [key]: n }));
  }

  /** Number-Input -> Signal (negatives/leeres wird zu 0). */
  setCount(side: 'own' | 'ownDef' | 'enemyShip' | 'enemyDef', type: string, value: unknown): void {
    const n = Math.max(0, Math.floor(Number(value) || 0));
    const target =
      side === 'own' ? this.ownCounts
      : side === 'ownDef' ? this.ownDefCounts
      : side === 'enemyShip' ? this.enemyShipCounts
      : this.enemyDefCounts;
    target.update((m) => ({ ...m, [type]: n }));
  }

  simulate(): void {
    if (!this.canSimulate() || this.pending()) {
      return;
    }
    this.pending.set(true);
    this.error.set(null);
    const commanderId = this.useCommander() ? this.selectedCommanderId() : null;
    const defending = this.mode() === 'defense';
    this.api
      .simulateCombat({
        attacker_ships: prune(this.ownCounts()),                       // immer DEINE Schiffe
        own_defenses: defending ? prune(this.ownDefCounts()) : {},     // nur beim Verteidigen
        defender_ships: prune(this.enemyShipCounts()),                 // immer GEGNER-Schiffe
        defender_defenses: defending ? {} : prune(this.enemyDefCounts()), // Angreifer bringt keine
        defender_tech: prune(this.enemyTech()),
        commander_id: commanderId,
        mode: this.mode(),
      })
      .subscribe({
        next: (r) => {
          this.result.set(r);
          this.pending.set(false);
        },
        error: (err) => {
          this.error.set(err?.error?.detail ?? 'Simulation fehlgeschlagen.');
          this.pending.set(false);
        },
      });
  }
}

/** Gibt es mindestens eine Einheit (count > 0)? */
function hasUnit(map: Record<string, number>): boolean {
  return Object.values(map).some((n) => n > 0);
}

function sumCounts(map: Record<string, number>): number {
  return Object.values(map).reduce((a, b) => a + (b > 0 ? b : 0), 0);
}

/** Entfernt 0-/Leer-Eintraege fuer den Request. */
function prune(map: Record<string, number>): Record<string, number> {
  const out: Record<string, number> = {};
  for (const [k, v] of Object.entries(map)) {
    if (v > 0) {
      out[k] = v;
    }
  }
  return out;
}
