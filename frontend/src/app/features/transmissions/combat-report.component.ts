import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { CombatReport, CombatRound } from '../../core/models/api.models';
import { DEFENSE_META, SHIP_META, metaFor } from '../../core/models/display';
import { IconTileComponent } from '../../shared/components/icon-tile.component';

/** Eine Einheit-Zeile (Bild/Glyph + Name + Anzahl) im Kampfbericht. */
interface UnitRow {
  label: string;
  glyph: string;
  icon: string | null;
  count: number;
}

/** Aufbereitete Sicht auf eine Kampfseite (Anfang -> Verluste -> Überlebende …). */
interface SideView {
  title: string;
  isYou: boolean;
  initial: UnitRow[];
  survivors: UnitRow[];
  losses: UnitRow[];
  captured: UnitRow[];
  fled: UnitRow[];
  stranded: UnitRow[];
  initialTotal: number;
  lossTotal: number;
}

/** Distanz-Band -> Label + Glyph (Doku 03b §6.1). */
const BAND_META: Record<string, { label: string; glyph: string }> = {
  near: { label: 'Nahkampf', glyph: '🔴' },
  medium: { label: 'Mittel', glyph: '🟡' },
  far: { label: 'Fernkampf', glyph: '🔵' },
};

/**
 * Kampfbericht-Viewer (Modal). Lädt den vollen Report (`GET /api/combat-reports/:id`)
 * und rendert die reiche Engine-Ausgabe: Ausgangsflotten, Runden-für-Runde-Verlauf
 * mit Distanz-Band/Feueraustausch/Verlusten/Fliehen, sowie das Endergebnis inkl.
 * Überlebende, gekaperte und gestrandete Schiffe, Beute und Trümmerfeld.
 *
 * Perspektivisch: `role` (vom Server) markiert, welche Seite der Spieler ist —
 * wichtig, weil man bei eingehenden Angriffen NICHT selbst am Kampf teilnimmt und
 * den Bericht nur nachträglich liest.
 */
@Component({
  selector: 'app-combat-report',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, IconTileComponent],
  template: `
    <div class="overlay" (click)="close.emit()">
      <div class="panel" (click)="$event.stopPropagation()">
        <button class="x" (click)="close.emit()" title="Schließen">✕</button>

        @if (loading()) {
          <p class="state">Lade Kampfbericht …</p>
        } @else if (error()) {
          <p class="state err">{{ error() }}</p>
        } @else if (reportData(); as r) {
          <!-- Kopf + Ergebnis-Banner -------------------------------------- -->
          <header class="rep-head">
            <span class="rep-glyph">⚔️</span>
            <div>
              <h2>Kampfbericht — {{ r.location }}</h2>
              <p class="faint small">
                {{ youAttacked() ? 'Du hast angegriffen' : 'Du wurdest angegriffen' }}
                @if (r.npc_name) { · Gegner: {{ r.npc_name }} }
                · {{ r.created_at | date: 'short' }}
              </p>
            </div>
          </header>

          <div class="banner" [class]="'b-' + result()">
            <span class="b-icon">{{ resultIcon() }}</span>
            <span class="b-text">{{ resultText() }}</span>
          </div>

          <!-- Zwei Seiten: Du vs. Gegner ----------------------------------- -->
          <div class="sides">
            @for (s of sides(); track s.title) {
              <section class="side" [class.you]="s.isYou">
                <div class="side-head">
                  <h3>{{ s.title }}</h3>
                  @if (s.isYou) { <span class="you-chip">DU</span> }
                </div>
                <div class="side-stat">
                  <span><span class="num">{{ s.initialTotal }}</span> Schiffe</span>
                  <span class="loss"><span class="num">−{{ s.lossTotal }}</span> verloren</span>
                </div>

                @if (s.initial.length) {
                  <div class="urows">
                    @for (u of s.initial; track u.label) {
                      <span class="unit" title="{{ u.label }}">
                        <app-icon-tile class="u-ico" [glyph]="u.glyph" [src]="u.icon" [size]="26"
                          [variant]="s.isYou ? 'accent' : 'magenta'" />{{ u.count }}
                      </span>
                    }
                  </div>
                }

                @if (s.losses.length) {
                  <div class="sub-block losses">
                    <span class="sb-label">💥 Verluste</span>
                    @for (u of s.losses; track u.label) {
                      <span class="unit"><app-icon-tile class="u-ico-sm" [glyph]="u.glyph" [src]="u.icon" [size]="18" variant="muted" /> {{ u.count }}× {{ u.label }}</span>
                    }
                  </div>
                }
                @if (s.captured.length) {
                  <div class="sub-block captured">
                    <span class="sb-label">🪝 Gekapert</span>
                    @for (u of s.captured; track u.label) {
                      <span class="unit"><app-icon-tile class="u-ico-sm" [glyph]="u.glyph" [src]="u.icon" [size]="18" variant="muted" /> {{ u.count }}× {{ u.label }}</span>
                    }
                  </div>
                }
                @if (s.stranded.length) {
                  <div class="sub-block stranded">
                    <span class="sb-label">⚓ Gestrandet (Antrieb tot)</span>
                    @for (u of s.stranded; track u.label) {
                      <span class="unit"><app-icon-tile class="u-ico-sm" [glyph]="u.glyph" [src]="u.icon" [size]="18" variant="muted" /> {{ u.count }}× {{ u.label }}</span>
                    }
                  </div>
                }
                @if (s.fled.length) {
                  <div class="sub-block fled">
                    <span class="sb-label">🏃 Geflohen</span>
                    @for (u of s.fled; track u.label) {
                      <span class="unit"><app-icon-tile class="u-ico-sm" [glyph]="u.glyph" [src]="u.icon" [size]="18" variant="muted" /> {{ u.count }}× {{ u.label }}</span>
                    }
                  </div>
                }
              </section>
            }
          </div>

          <!-- Runden-Verlauf ----------------------------------------------- -->
          <section class="rounds">
            <h3>Gefechtsverlauf</h3>
            @for (rd of reportData()!.rounds; track $index) {
              <div class="round" [class.ambush]="rd.ambush">
                <div class="r-head">
                  <span class="r-no">{{ rd.ambush ? '🥷 Hinterhalt' : 'Runde ' + rd.round }}</span>
                  @if (bandOf(rd); as b) {
                    <span class="r-band">{{ b.glyph }} {{ b.label }}</span>
                  }
                </div>
                <div class="fire">
                  <div class="fire-row">
                    <span class="fl">{{ attackerLabel() }}</span>
                    <div class="bar"><span class="fill atk" [style.width.%]="firePct(rd.attacker_fire)"></span></div>
                    <span class="fv">{{ fmt(rd.attacker_fire) }}</span>
                  </div>
                  <div class="fire-row">
                    <span class="fl">{{ defenderLabel() }}</span>
                    <div class="bar"><span class="fill def" [style.width.%]="firePct(rd.defender_fire)"></span></div>
                    <span class="fv">{{ fmt(rd.defender_fire) }}</span>
                  </div>
                </div>
                @if (roundNote(rd); as note) {
                  <p class="r-note">{{ note }}</p>
                }
              </div>
            }
          </section>

          <!-- Beute / Trümmer ---------------------------------------------- -->
          <footer class="spoils">
            @if (lootRows().length) {
              <div class="spoil-block">
                <span class="sb-label">💰 Beute</span>
                @for (x of lootRows(); track x.label) {
                  <span class="res">{{ x.glyph }} {{ fmt(x.count) }} {{ x.label }}</span>
                }
              </div>
            }
            @if (debrisRows().length) {
              <div class="spoil-block">
                <span class="sb-label">🛰 Trümmerfeld</span>
                @for (x of debrisRows(); track x.label) {
                  <span class="res">{{ x.glyph }} {{ fmt(x.count) }} {{ x.label }}</span>
                }
              </div>
            }
          </footer>
        }
      </div>
    </div>
  `,
  styles: [`
    .overlay { position: fixed; inset: 0; background: rgba(2, 6, 18, 0.72); backdrop-filter: blur(3px);
      display: flex; align-items: flex-start; justify-content: center; padding: 3vh 1rem; z-index: 80; overflow-y: auto; }
    .panel { position: relative; width: min(820px, 100%); background: #0d1326; border: 1px solid #243049;
      border-radius: 14px; padding: 1.4rem 1.5rem 1.5rem; box-shadow: 0 20px 60px rgba(0,0,0,0.5); }
    .x { position: absolute; top: 0.7rem; right: 0.8rem; background: none; border: none; color: #8b96ad;
      font-size: 1.1rem; cursor: pointer; line-height: 1; padding: 0.3rem; }
    .x:hover { color: #fff; }
    .state { text-align: center; padding: 2rem; color: #8b96ad; }
    .state.err { color: #ff8d8d; }

    .rep-head { display: flex; gap: 0.8rem; align-items: center; margin-bottom: 1rem; }
    .rep-glyph { font-size: 1.8rem; }
    .rep-head h2 { margin: 0; font-size: 1.15rem; }
    .faint { color: #8b96ad; } .small { font-size: 0.8rem; }

    .banner { display: flex; align-items: center; gap: 0.6rem; padding: 0.7rem 1rem; border-radius: 10px;
      font-weight: 600; margin-bottom: 1.1rem; }
    .b-icon { font-size: 1.3rem; }
    .b-win { background: rgba(46, 160, 87, 0.16); border: 1px solid #2ea05766; color: #6ee7a0; }
    .b-loss { background: rgba(208, 64, 64, 0.16); border: 1px solid #d0404066; color: #ff9b9b; }
    .b-draw { background: rgba(120, 130, 160, 0.16); border: 1px solid #5b667f66; color: #c3cce0; }

    .sides { display: grid; grid-template-columns: 1fr 1fr; gap: 0.8rem; margin-bottom: 1.2rem; }
    .side { background: #0a0f1f; border: 1px solid #1e2740; border-radius: 10px; padding: 0.8rem 0.9rem; }
    .side.you { border-color: #34507e; box-shadow: inset 0 0 0 1px #34507e44; }
    .side-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.5rem; }
    .side-head h3 { margin: 0; font-size: 0.95rem; }
    .you-chip { font-size: 0.62rem; font-weight: 700; letter-spacing: 0.06em; background: #34507e; color: #cfe0ff;
      padding: 0.1rem 0.4rem; border-radius: 5px; }
    .side-stat { display: flex; justify-content: space-between; font-size: 0.82rem; color: #aab4ca; margin-bottom: 0.55rem; }
    .side-stat .num { font-weight: 700; color: #e6ecf7; }
    .side-stat .loss .num { color: #ff9b9b; }
    .urows { display: flex; flex-wrap: wrap; gap: 0.3rem; margin-bottom: 0.5rem; }
    .urows .unit { background: #131c33; border: 1px solid #233052; border-radius: 6px; padding: 0.15rem 0.4rem;
      font-size: 0.8rem; display: inline-flex; align-items: center; gap: 0.2rem; }
    .ug { font-size: 0.95rem; }

    .sub-block { display: flex; flex-wrap: wrap; gap: 0.35rem 0.55rem; align-items: center; margin-top: 0.4rem;
      font-size: 0.78rem; }
    .sb-label { font-size: 0.72rem; color: #8b96ad; width: 100%; }
    .sub-block .unit { color: #c3cce0; display: inline-flex; align-items: center; gap: 0.28rem; }
    .u-ico-sm { flex: 0 0 auto; }
    .sub-block.captured .unit { color: #9ad7ff; }
    .sub-block.stranded .unit { color: #ffd28a; }
    .sub-block.losses .unit { color: #ff9b9b; }

    .rounds { margin-bottom: 1.1rem; }
    .rounds h3, .spoils .sb-label { font-size: 0.95rem; }
    .rounds h3 { margin: 0 0 0.6rem; }
    .round { background: #0a0f1f; border: 1px solid #1a2238; border-radius: 9px; padding: 0.6rem 0.8rem; margin-bottom: 0.5rem; }
    .round.ambush { border-color: #6b4ea033; background: rgba(80, 50, 130, 0.12); }
    .r-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: 0.45rem; }
    .r-no { font-weight: 600; font-size: 0.86rem; }
    .r-band { font-size: 0.76rem; color: #aab4ca; }
    .fire-row { display: grid; grid-template-columns: 5.5rem 1fr 4rem; align-items: center; gap: 0.5rem; margin: 0.18rem 0; }
    .fl { font-size: 0.74rem; color: #8b96ad; }
    .fv { font-size: 0.78rem; text-align: right; font-variant-numeric: tabular-nums; color: #cdd6e8; }
    .bar { height: 7px; background: #131c33; border-radius: 4px; overflow: hidden; }
    .fill { display: block; height: 100%; }
    .fill.atk { background: linear-gradient(90deg, #3d7dff, #5a93ff); }
    .fill.def { background: linear-gradient(90deg, #d04040, #e06060); }
    .r-note { margin: 0.35rem 0 0; font-size: 0.75rem; color: #9aa6bf; }

    .spoils { display: flex; flex-wrap: wrap; gap: 1.2rem; border-top: 1px solid #1a2238; padding-top: 0.9rem; }
    .spoil-block { display: flex; flex-wrap: wrap; gap: 0.4rem; align-items: center; }
    .spoil-block .sb-label { width: auto; }
    .res { font-size: 0.82rem; color: #cdd6e8; }

    @media (max-width: 600px) { .sides { grid-template-columns: 1fr; } }
  `],
})
export class CombatReportComponent {
  private readonly api = inject(ApiService);

  /** Lade-Modus: Report per ID vom Server holen (Postfach). */
  readonly reportId = input<string | null>(null);
  /** Direkt-Modus: bereits geladener Report (z. B. aus dem Simulator) — kein Fetch. */
  readonly report = input<CombatReport | null>(null);
  readonly close = output<void>();

  // Internes State-Signal (NICHT mit dem `report`-Input verwechseln): haelt den
  // tatsaechlich angezeigten Report, egal ob vorgeladen oder per ID gefetcht.
  protected readonly reportData = signal<CombatReport | null>(null);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  constructor() {
    effect(() => {
      // Direkt-Modus hat Vorrang: vorgeladenen Report ohne Netzaufruf uebernehmen.
      const preloaded = this.report();
      if (preloaded) {
        this.reportData.set(preloaded);
        this.error.set(null);
        this.loading.set(false);
        return;
      }
      const id = this.reportId();
      if (!id) {
        return;
      }
      this.loading.set(true);
      this.error.set(null);
      this.reportData.set(null);
      this.api.getCombatReport(id).subscribe({
        next: (r) => {
          this.reportData.set(r);
          this.loading.set(false);
        },
        error: (err) => {
          this.error.set(err?.error?.detail ?? 'Kampfbericht konnte nicht geladen werden.');
          this.loading.set(false);
        },
      });
    });
  }

  /** War der abrufende Spieler der Angreifer? */
  protected readonly youAttacked = computed(() => this.reportData()?.role === 'attacker');

  /** Ergebnis aus Spieler-Perspektive: 'win' | 'loss' | 'draw'. */
  protected readonly result = computed<'win' | 'loss' | 'draw'>(() => {
    const r = this.reportData();
    if (!r || r.winner === 'draw') {
      return 'draw';
    }
    return r.winner === r.role ? 'win' : 'loss';
  });

  protected resultIcon(): string {
    return { win: '🏆', loss: '☠️', draw: '🤝' }[this.result()];
  }

  protected resultText(): string {
    const r = this.reportData();
    if (!r) {
      return '';
    }
    if (this.result() === 'draw') {
      return 'Unentschieden — beide Flotten halten das Feld.';
    }
    if (this.result() === 'win') {
      return r.role === 'defender' ? 'Angriff abgewehrt!' : 'Sieg — das Feld gehört dir!';
    }
    return r.role === 'defender' ? 'Verteidigung durchbrochen!' : 'Niederlage — Flotte zerschlagen.';
  }

  protected attackerLabel(): string {
    return this.youAttacked() ? 'Du →' : 'Gegner →';
  }
  protected defenderLabel(): string {
    return this.youAttacked() ? 'Gegner →' : 'Du →';
  }

  /** Beide Seiten als aufbereitete Sicht (Spieler-Seite zuerst). */
  protected readonly sides = computed<SideView[]>(() => {
    const r = this.reportData();
    if (!r) {
      return [];
    }
    const atk: SideView = {
      title: 'Angreifer',
      isYou: r.role === 'attacker',
      initial: rows(r.attacker),
      survivors: rows(r.attacker_survivors),
      losses: rows(r.attacker_losses),
      captured: rows(r.defender_captured), // vom Verteidiger gekaperte Angreifer-Schiffe
      fled: rows(r.attacker_fled),
      stranded: rows(r.attacker_drive_disabled),
      initialTotal: total(r.attacker),
      lossTotal: total(r.attacker_losses),
    };
    const def: SideView = {
      title: 'Verteidiger',
      isYou: r.role === 'defender',
      initial: rows(r.defender),
      survivors: rows(r.defender_survivors),
      losses: rows(r.defender_losses),
      captured: rows(r.attacker_captured), // vom Angreifer gekaperte Verteidiger-Schiffe
      fled: rows(r.defender_fled),
      stranded: rows(r.defender_drive_disabled),
      initialTotal: total(r.defender),
      lossTotal: total(r.defender_losses),
    };
    // Eigene Seite zuerst anzeigen.
    return r.role === 'defender' ? [def, atk] : [atk, def];
  });

  protected bandOf(rd: CombatRound): { label: string; glyph: string } | null {
    return rd.distance ? BAND_META[rd.distance] ?? null : null;
  }

  /** Größtes Feuer im Bericht -> Skala für die Balken. */
  private readonly maxFire = computed(() => {
    const r = this.reportData();
    if (!r) {
      return 1;
    }
    let m = 1;
    for (const rd of r.rounds) {
      m = Math.max(m, rd.attacker_fire, rd.defender_fire);
    }
    return m;
  });

  protected firePct(v: number): number {
    return Math.min(100, (v / this.maxFire()) * 100);
  }

  protected roundNote(rd: CombatRound): string | null {
    const parts: string[] = [];
    if (rd.ambush) {
      parts.push('Überraschungsrunde — nur der Angreifer feuert.');
    }
    if (rd.attacker_fled) {
      parts.push(`${rd.attacker_fled} Angreifer-Schiff(e) fliehen.`);
    }
    if (rd.defender_fled) {
      parts.push(`${rd.defender_fled} Verteidiger-Schiff(e) fliehen.`);
    }
    return parts.length ? parts.join(' ') : null;
  }

  protected readonly lootRows = computed(() => resRows(this.reportData()?.loot));
  protected readonly debrisRows = computed(() => resRows(this.reportData()?.debris));

  fmt(n: number): string {
    return Math.round(n).toLocaleString('de-DE');
  }
}

/** Wandelt {type: count} in sortierte Anzeige-Zeilen (Schiffe + Verteidigung). */
function rows(map: Record<string, number> | undefined | null): UnitRow[] {
  if (!map) {
    return [];
  }
  const out: UnitRow[] = [];
  for (const [key, value] of Object.entries(map)) {
    const n = Number(value) || 0;
    if (n <= 0) {
      continue;
    }
    const isShip = !!SHIP_META[key];
    const meta = isShip ? metaFor(SHIP_META, key) : metaFor(DEFENSE_META, key);
    const icon = `assets/img/${isShip ? 'ships' : 'defenses'}/${key}.png`;
    out.push({ label: meta.label, glyph: meta.glyph, icon, count: n });
  }
  return out.sort((a, b) => b.count - a.count);
}

function total(map: Record<string, number> | undefined | null): number {
  if (!map) {
    return 0;
  }
  return Object.values(map).reduce((s, v) => s + (Number(v) || 0), 0);
}

const RES_META: Record<string, { label: string; glyph: string }> = {
  metal: { label: 'Metall', glyph: '⛏' },
  crystal: { label: 'Kristall', glyph: '💎' },
  deuterium: { label: 'Deuterium', glyph: '🧪' },
};

function resRows(map: Record<string, number> | undefined | null): UnitRow[] {
  if (!map) {
    return [];
  }
  const out: UnitRow[] = [];
  for (const k of ['metal', 'crystal', 'deuterium'] as const) {
    const n = Number(map[k]) || 0;
    if (n > 0) {
      out.push({ label: RES_META[k].label, glyph: RES_META[k].glyph, icon: null, count: n });
    }
  }
  return out;
}
