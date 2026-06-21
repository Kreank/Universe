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
import { CombatReport, CombatRound, CombatSimTech } from '../../core/models/api.models';
import { DEFENSE_META, SHIP_META, isMk2, metaFor } from '../../core/models/display';
import { defenseIcon, rangeIcon, resourceIcon, shipIcon, statusIcon, uiIcon } from '../../core/models/icon-assets';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';

/** Eine Einheit-Zeile (Bild/Glyph + Name + Anzahl) im Kampfbericht. */
interface UnitRow {
  label: string;
  glyph: string;
  icon: string | null;
  count: number;
  /** Mk2/Elite-Schiff -> goldener Rahmen ueber dem Icon. */
  mk2?: boolean;
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
  /** Verteidigung, die durch Ionen lahmgelegt wurde (überlebt, feuert aber nicht mehr). */
  defenseDisabled: UnitRow[];
  /** Verteidigung, die nach dem Kampf automatisch repariert wurde (70 % der zerstörten). */
  defenseRebuilt: UnitRow[];
  initialTotal: number;
  lossTotal: number;
  /** Aufschlüsselung des Bestands in Schiffe vs. Verteidigungsanlagen (für die Kopfzeile). */
  shipCount: number;
  defenseCount: number;
}

/** Distanz-Band -> Label + Glyph (Doku 03b §6.1). */
const BAND_META: Record<string, { key: string; label: string; glyph: string }> = {
  near: { key: 'near', label: 'Nahkampf', glyph: '🔴' },
  medium: { key: 'medium', label: 'Mittel', glyph: '🟡' },
  far: { key: 'far', label: 'Fernkampf', glyph: '🔵' },
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
  imports: [DatePipe, IconTileComponent, BtnIconComponent],
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
            <span class="rep-glyph"><app-btn-icon [src]="statusIcon('attack')" glyph="⚔️" [size]="24" /></span>
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
            <span class="b-icon"><app-btn-icon [src]="resultIconSrc()" [glyph]="resultIcon()" [size]="24" /></span>
            <span class="b-text">{{ resultText() }}</span>
          </div>

          @if (simMeta(); as m) {
            <div class="sim-meta">
              <div class="sm-title">Simulation ({{ m.role === 'defender' ? 'du verteidigst' : 'du greifst an' }}) — gerechnet mit:</div>
              <div class="sm-row">
                <span class="sm-tag you">DU</span>
                <span class="sm-txt">{{ techLine(m.you.tech) }}@if (m.you.antimatter_forge) {<span> · Antimaterie-Schmiede {{ m.you.antimatter_forge }}</span>}@if (m.you.doctrine) {<span> · Doktrin: {{ m.you.doctrine }}</span>}@if (m.you.commander; as c) {<span class="sm-cmd"> · 🎖 {{ c.name }} (Moral {{ c.morale }})</span>} @else {<span class="faint"> · ohne Commander</span>}</span>
              </div>
              <div class="sm-row">
                <span class="sm-tag foe">GEGNER</span>
                <span class="sm-txt">{{ techLine(m.enemy.tech) }}</span>
              </div>
            </div>
          }

          <!-- Zwei Seiten: Du vs. Gegner ----------------------------------- -->
          <div class="sides">
            @for (s of sides(); track s.title) {
              <section class="side" [class.you]="s.isYou">
                <div class="side-head">
                  <h3>{{ s.title }}</h3>
                  @if (s.isYou) { <span class="you-chip">DU</span> }
                </div>
                <div class="side-stat">
                  <span>
                    <span class="num">{{ s.shipCount }}</span> Schiffe@if (s.defenseCount > 0) { · <span class="num">{{ s.defenseCount }}</span> Verteidigung}
                  </span>
                  <span class="loss"><span class="num">−{{ s.lossTotal }}</span> verloren</span>
                </div>

                @if (s.initial.length) {
                  <div class="urows">
                    @for (u of s.initial; track u.label) {
                      <span class="unit" title="{{ u.label }}">
                        <app-icon-tile class="u-ico" [glyph]="u.glyph" [src]="u.icon" [mk2]="!!u.mk2" [size]="26"
                          [variant]="s.isYou ? 'accent' : 'magenta'" />{{ u.count }}
                      </span>
                    }
                  </div>
                }

                @if (s.losses.length) {
                  <div class="sub-block losses">
                    <span class="sb-label"><app-btn-icon [src]="statusIcon('losses')" glyph="💥" [size]="16" /> Verluste</span>
                    @for (u of s.losses; track u.label) {
                      <span class="unit"><app-icon-tile class="u-ico-sm" [glyph]="u.glyph" [src]="u.icon" [mk2]="!!u.mk2" [size]="18" variant="muted" /> {{ u.count }}× {{ u.label }}</span>
                    }
                  </div>
                }
                @if (s.defenseDisabled.length) {
                  <div class="sub-block disabled">
                    <span class="sb-label"><app-btn-icon [src]="statusIcon('disabled')" glyph="⚡" [size]="16" /> Lahmgelegt (Ionen) — feuert nicht mehr</span>
                    @for (u of s.defenseDisabled; track u.label) {
                      <span class="unit"><app-icon-tile class="u-ico-sm" [glyph]="u.glyph" [src]="u.icon" [mk2]="!!u.mk2" [size]="18" variant="muted" /> {{ u.count }}× {{ u.label }}</span>
                    }
                  </div>
                }
                @if (s.defenseRebuilt.length) {
                  <div class="sub-block rebuilt">
                    <span class="sb-label"><app-btn-icon [src]="statusIcon('repair')" glyph="🔧" [size]="16" /> Nach dem Kampf repariert</span>
                    @for (u of s.defenseRebuilt; track u.label) {
                      <span class="unit"><app-icon-tile class="u-ico-sm" [glyph]="u.glyph" [src]="u.icon" [mk2]="!!u.mk2" [size]="18" variant="muted" /> {{ u.count }}× {{ u.label }}</span>
                    }
                  </div>
                }
                @if (s.captured.length) {
                  <div class="sub-block captured">
                    <span class="sb-label"><app-btn-icon [src]="statusIcon('boarding')" glyph="🪝" [size]="16" /> Gekapert</span>
                    @for (u of s.captured; track u.label) {
                      <span class="unit"><app-icon-tile class="u-ico-sm" [glyph]="u.glyph" [src]="u.icon" [mk2]="!!u.mk2" [size]="18" variant="muted" /> {{ u.count }}× {{ u.label }}</span>
                    }
                  </div>
                }
                @if (s.stranded.length) {
                  <div class="sub-block stranded">
                    <span class="sb-label"><app-btn-icon [src]="statusIcon('stranded')" glyph="⚓" [size]="16" /> Gestrandet (Antrieb tot)</span>
                    @for (u of s.stranded; track u.label) {
                      <span class="unit"><app-icon-tile class="u-ico-sm" [glyph]="u.glyph" [src]="u.icon" [mk2]="!!u.mk2" [size]="18" variant="muted" /> {{ u.count }}× {{ u.label }}</span>
                    }
                  </div>
                }
                @if (s.fled.length) {
                  <div class="sub-block fled">
                    <span class="sb-label"><app-btn-icon [src]="statusIcon('fled')" glyph="🏃" [size]="16" /> Geflohen</span>
                    @for (u of s.fled; track u.label) {
                      <span class="unit"><app-icon-tile class="u-ico-sm" [glyph]="u.glyph" [src]="u.icon" [mk2]="!!u.mk2" [size]="18" variant="muted" /> {{ u.count }}× {{ u.label }}</span>
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
                  <span class="r-no">@if (rd.ambush) {<app-btn-icon [src]="statusIcon('ambush')" glyph="🥷" [size]="14" /> Hinterhalt} @else {Runde {{ rd.round }}}</span>
                  @if (bandOf(rd); as b) {
                    <span class="r-band"><app-btn-icon [src]="rangeIcon(b.key)" [glyph]="b.glyph" [size]="14" /> {{ b.label }}</span>
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
                <span class="sb-label"><app-btn-icon [src]="uiIcon('loot')" glyph="💰" [size]="16" /> Beute</span>
                @for (x of lootRows(); track x.label) {
                  <span class="res"><app-icon-tile class="res-ico" [glyph]="x.glyph" [src]="x.icon" [size]="18" variant="muted" /> {{ fmt(x.count) }} {{ x.label }}</span>
                }
              </div>
            }
            @if (debrisRows().length) {
              <div class="spoil-block">
                <span class="sb-label"><app-btn-icon [src]="'assets/img/backgrounds/debris_field.png'" glyph="🛰" [size]="16" /> Trümmerfeld</span>
                @for (x of debrisRows(); track x.label) {
                  <span class="res"><app-icon-tile class="res-ico" [glyph]="x.glyph" [src]="x.icon" [size]="18" variant="muted" /> {{ fmt(x.count) }} {{ x.label }}</span>
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
      display: flex; align-items: flex-start; justify-content: center; padding: 3vh var(--sp-4); z-index: 80; overflow-y: auto; }
    .panel { position: relative; width: min(820px, 100%);
      background: rgba(14, 22, 38, 0.92);
      backdrop-filter: blur(14px) saturate(1.2); -webkit-backdrop-filter: blur(14px) saturate(1.2);
      border: 1px solid var(--border-strong);
      border-radius: var(--r-lg); padding: var(--sp-5) var(--sp-5) var(--sp-6); box-shadow: var(--e3), var(--hairline-top); }
    .x { position: absolute; top: var(--sp-2); right: var(--sp-3); background: none; border: none; color: var(--text-faint);
      font-size: var(--fs-lg); cursor: pointer; line-height: 1; padding: var(--sp-1); }
    .x:hover { color: var(--text); }
    .state { text-align: center; padding: var(--sp-8); color: var(--text-dim); }
    .state.err { color: var(--danger); }

    .rep-head { display: flex; gap: var(--sp-3); align-items: center; margin-bottom: var(--sp-4); }
    .rep-glyph { font-size: var(--fs-2xl); }
    .rep-head h2 { margin: 0; font-family: var(--font-display); font-size: var(--fs-lg); }
    .faint { color: var(--text-faint); } .small { font-size: var(--fs-sm); }

    /* Ergebnis-Banner: Sieg=ok, Niederlage=danger, Unentschieden=neutral. */
    .banner { display: flex; align-items: center; gap: var(--sp-2); padding: var(--sp-3) var(--sp-4); border-radius: var(--r-md);
      font-family: var(--font-display); font-weight: 600; margin-bottom: var(--sp-5); }
    .b-icon { font-size: var(--fs-xl); }
    .b-win { background: rgba(70, 224, 138, 0.14); border: 1px solid color-mix(in srgb, var(--ok) 40%, transparent); color: var(--ok); }
    .b-loss { background: rgba(255, 77, 125, 0.14); border: 1px solid var(--danger-dim); color: var(--danger); }
    .b-draw { background: rgba(150, 172, 214, 0.10); border: 1px solid var(--border-strong); color: var(--text-dim); }

    /* Simulator-Transparenz: Tech/Commander-Annahmen direkt unter dem Ergebnis-Banner. */
    .sim-meta { margin: calc(-1 * var(--sp-3)) 0 var(--sp-5); padding: var(--sp-2) var(--sp-3);
      border: 1px solid var(--border); border-radius: var(--r-md); background: rgba(255,255,255,0.03); }
    .sm-title { font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase;
      letter-spacing: 0.08em; color: var(--text-dim); margin-bottom: var(--sp-1); }
    .sm-row { display: flex; align-items: baseline; gap: var(--sp-2); font-size: var(--fs-sm);
      color: var(--text-dim); margin-top: 2px; }
    .sm-txt { min-width: 0; }
    .sm-cmd { color: var(--accent); }
    .sm-tag { flex: 0 0 auto; font-family: var(--font-display); font-size: var(--fs-xs); font-weight: 700;
      letter-spacing: 0.06em; padding: 1px var(--sp-2); border-radius: var(--r-sm); }
    .sm-tag.you { background: var(--accent); color: #04201d; }
    .sm-tag.foe { background: color-mix(in srgb, var(--danger) 22%, transparent); color: var(--danger);
      border: 1px solid var(--danger-dim); }

    .sides { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-3); margin-bottom: var(--sp-5); }
    .side { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--r-md); padding: var(--sp-3) var(--sp-4); }
    .side.you { border-color: var(--accent); box-shadow: inset 0 0 0 1px var(--accent-soft); }
    .side-head { display: flex; align-items: center; gap: var(--sp-2); margin-bottom: var(--sp-2); }
    .side-head h3 { margin: 0; font-family: var(--font-display); font-size: var(--fs-base); }
    .you-chip { font-family: var(--font-display); font-size: var(--fs-xs); font-weight: 700; letter-spacing: 0.08em;
      background: var(--accent); color: #04201d; padding: 1px var(--sp-2); border-radius: var(--r-sm); }
    .side-stat { display: flex; justify-content: space-between; font-size: var(--fs-sm); color: var(--text-dim); margin-bottom: var(--sp-2); }
    .side-stat .num { font-family: var(--mono); font-variant-numeric: tabular-nums; font-weight: 700; color: var(--text); }
    .side-stat .loss .num { color: var(--danger); }
    .urows { display: flex; flex-wrap: wrap; gap: var(--sp-1); margin-bottom: var(--sp-2); }
    .urows .unit { background: var(--surface-3); border: 1px solid var(--border); border-radius: var(--r-sm); padding: 2px var(--sp-2);
      font-family: var(--mono); font-variant-numeric: tabular-nums; font-size: var(--fs-sm);
      display: inline-flex; align-items: center; gap: var(--sp-1); }

    .sub-block { display: flex; flex-wrap: wrap; gap: var(--sp-1) var(--sp-2); align-items: center; margin-top: var(--sp-2);
      font-size: var(--fs-sm); }
    .sb-label { font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.1em;
      color: var(--text-dim); width: 100%; }
    .sub-block .unit { color: var(--text-dim); display: inline-flex; align-items: center; gap: var(--sp-1);
      font-variant-numeric: tabular-nums; }
    .u-ico-sm { flex: 0 0 auto; }
    .sub-block.captured .unit { color: var(--crystal); }
    .sub-block.stranded .unit { color: var(--warn); }
    .sub-block.losses .unit { color: var(--danger); }
    .sub-block.disabled .unit { color: var(--deuterium); }
    .sub-block.rebuilt .unit { color: var(--ok); }

    .rounds { margin-bottom: var(--sp-5); }
    .rounds h3, .spoils .sb-label { font-family: var(--font-display); font-size: var(--fs-base); }
    .rounds h3 { margin: 0 0 var(--sp-3); }
    .round { background: var(--surface-1); border: 1px solid var(--border); border-radius: var(--r-md); padding: var(--sp-2) var(--sp-3); margin-bottom: var(--sp-2); }
    .round.ambush { border-color: color-mix(in srgb, var(--deuterium) 40%, transparent); background: color-mix(in srgb, var(--deuterium) 8%, transparent); }
    .r-head { display: flex; justify-content: space-between; align-items: center; margin-bottom: var(--sp-2); }
    .r-no { font-family: var(--font-display); font-weight: 600; font-size: var(--fs-sm); }
    .r-band { font-size: var(--fs-xs); color: var(--text-dim); }
    .fire-row { display: grid; grid-template-columns: 5.5rem 1fr 4rem; align-items: center; gap: var(--sp-2); margin: var(--sp-1) 0; }
    .fl { font-size: var(--fs-xs); color: var(--text-faint); }
    .fv { font-family: var(--mono); font-size: var(--fs-sm); text-align: right; font-variant-numeric: tabular-nums; color: var(--text); }
    .bar { height: 7px; background: rgba(255, 255, 255, 0.07); border-radius: var(--r-pill); overflow: hidden; }
    .fill { display: block; height: 100%; border-radius: var(--r-pill); }
    .fill.atk { background: linear-gradient(90deg, var(--accent-dim), var(--accent)); }
    .fill.def { background: linear-gradient(90deg, color-mix(in srgb, var(--info) 60%, transparent), var(--info)); }
    .r-note { margin: var(--sp-2) 0 0; font-size: var(--fs-xs); color: var(--text-dim); }

    .spoils { display: flex; flex-wrap: wrap; gap: var(--sp-5); border-top: 1px solid var(--border); padding-top: var(--sp-3); }
    .spoil-block { display: flex; flex-wrap: wrap; gap: var(--sp-2); align-items: center; }
    .spoil-block .sb-label { width: auto; }
    .res { font-family: var(--mono); font-variant-numeric: tabular-nums; font-size: var(--fs-sm); color: var(--text);
      display: inline-flex; align-items: center; gap: var(--sp-1); }
    .res-ico { flex: 0 0 auto; }

    @media (max-width: 600px) { .sides { grid-template-columns: 1fr; } }
  `],
})
export class CombatReportComponent {
  private readonly api = inject(ApiService);

  /** Asset-Pfad-Helfer fuers Template (Glyph-Fallback via app-btn-icon). */
  protected readonly statusIcon = statusIcon;
  protected readonly uiIcon = uiIcon;
  protected readonly rangeIcon = rangeIcon;

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

  protected resultIconSrc(): string {
    return { win: statusIcon('victory'), loss: statusIcon('defeat'), draw: statusIcon('draw') }[this.result()];
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
    const atkSplit = splitShipDefense(r.attacker);
    const defSplit = splitShipDefense(r.defender);
    const atk: SideView = {
      title: 'Angreifer',
      isYou: r.role === 'attacker',
      initial: rows(r.attacker),
      survivors: rows(r.attacker_survivors),
      losses: rows(r.attacker_losses),
      captured: rows(r.defender_captured), // vom Verteidiger gekaperte Angreifer-Schiffe
      fled: rows(r.attacker_fled),
      stranded: rows(r.attacker_drive_disabled),
      defenseDisabled: [],
      defenseRebuilt: [],
      initialTotal: total(r.attacker),
      lossTotal: total(r.attacker_losses),
      shipCount: atkSplit.ships,
      defenseCount: atkSplit.defenses,
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
      defenseDisabled: rows(r.defender_defense_disabled), // durch Ionen lahmgelegt
      defenseRebuilt: rows(r.defender_defense_rebuilt),   // nach dem Kampf repariert
      initialTotal: total(r.defender),
      lossTotal: total(r.defender_losses),
      shipCount: defSplit.ships,
      defenseCount: defSplit.defenses,
    };
    // Eigene Seite zuerst anzeigen.
    return r.role === 'defender' ? [def, atk] : [atk, def];
  });

  protected bandOf(rd: CombatRound): { key: string; label: string; glyph: string } | null {
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

  /** Simulator-Transparenz: mit welcher Tech/Commander gerechnet wurde (nur im Sim gesetzt). */
  protected readonly simMeta = computed(() => this.reportData()?.sim_meta ?? null);

  /** Kompakte Tech-Zeile: Kern-Kampftech + Meisterschaften (nur wenn > 0). */
  protected techLine(t: CombatSimTech): string {
    const parts = [`Waffen ${t.weapons_tech}`, `Schild ${t.shield_tech}`, `Panzerung ${t.armor_tech}`];
    if (t.weapons_mastery) { parts.push(`Waffen-M. ${t.weapons_mastery}`); }
    if (t.shield_mastery) { parts.push(`Schild-M. ${t.shield_mastery}`); }
    if (t.armor_mastery) { parts.push(`Panzer-M. ${t.armor_mastery}`); }
    return parts.join(' · ');
  }

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
    // Mk2/Elite-Schiffe (`<parent>_mk2`) stehen nicht in SHIP_META -> ebenfalls als Schiff werten.
    const isShip = !!SHIP_META[key] || isMk2(key);
    const meta = isShip ? metaFor(SHIP_META, key) : metaFor(DEFENSE_META, key);
    const icon = isShip ? shipIcon(key) : defenseIcon(key);
    out.push({ label: meta.label, glyph: meta.glyph, icon, count: n, mk2: isMk2(key) });
  }
  return out.sort((a, b) => b.count - a.count);
}

function total(map: Record<string, number> | undefined | null): number {
  if (!map) {
    return 0;
  }
  return Object.values(map).reduce((s, v) => s + (Number(v) || 0), 0);
}

/** Trennt einen {typ:anzahl}-Bestand in Schiffe vs. Verteidigungsanlagen (für die Kopf-Zeile). */
function splitShipDefense(map: Record<string, number> | undefined | null): { ships: number; defenses: number } {
  const out = { ships: 0, defenses: 0 };
  if (!map) {
    return out;
  }
  for (const [key, value] of Object.entries(map)) {
    const n = Number(value) || 0;
    if (n <= 0) {
      continue;
    }
    if (SHIP_META[key] || isMk2(key)) {
      out.ships += n;
    } else {
      out.defenses += n;
    }
  }
  return out;
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
      out.push({ label: RES_META[k].label, glyph: RES_META[k].glyph, icon: resourceIcon(k), count: n });
    }
  }
  return out;
}
