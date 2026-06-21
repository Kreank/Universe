import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { ResourceCost } from '../../core/models/api.models';
import { BalanceService } from '../../core/services/balance.service';
import { GameStateService } from '../../core/services/game-state.service';
import {
  BUILDING_META,
  DEFENSE_META,
  RANGE_META,
  SHIP_META,
  TECH_META,
  isMk2,
  metaFor,
  TECH_EFFECTS,
} from '../../core/models/display';
import { shipIcon, statIcon, techIcon, uiIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from './btn-icon.component';
import { CostLineComponent } from './cost-line.component';
import { IconTileComponent } from './icon-tile.component';

export type DetailKind = 'ship' | 'building' | 'tech' | 'defense';

/** Eine Voraussetzung mit optionalem Erfuellt-Status (vom aufrufenden Screen). */
export interface DetailRequirement {
  type: string;
  level: number;
  met?: boolean;
}

interface StatRow {
  glyph: string;
  label: string;
  value: string;
  iconKey?: string;
}

/** Kurz-Tag (z. B. Waffentyp, Reichweite, Antrieb) — vom aufrufenden Screen. */
export interface DetailTag {
  glyph: string;
  label: string;
  tip?: string;
  /** Optionales Icon-Asset; ersetzt den Glyph, faellt bei Ladefehler darauf zurueck. */
  icon?: string | null;
}

interface RapidFireRow {
  type: string;
  glyph: string;
  label: string;
  mult: number;
  img: string;
}

/**
 * OGame-artiges Overlay-Popup mit allen Details zu einem Bauobjekt
 * (Schiff/Gebaeude/Forschung/Verteidigung): Artwork, "kleine Geschichte",
 * Stat-Tabelle, Schnellfeuer-Liste, Voraussetzungen + Techbaum-Link, Aktion.
 *
 * Statische Werte (Stats, Schnellfeuer, Voraussetzungen) liest das Popup
 * selbst aus `balance.json`; der aufrufende Screen reicht nur die Live-Bits
 * (Kosten der naechsten Stufe, Erfuellt-Status, Aktions-Label) hinein.
 */
@Component({
  selector: 'app-detail-popup',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, CostLineComponent, IconTileComponent, BtnIconComponent],
  host: {
    '(document:keydown.escape)': 'close.emit()',
  },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup glass" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>

        <header class="head">
          <app-icon-tile
            [glyph]="meta().glyph"
            [src]="imgSrc()"
            [size]="84"
            [mk2]="isMk2Ship()"
            [variant]="kind() === 'defense' ? 'magenta' : 'accent'"
          />
          <div class="head-text">
            <h2>{{ meta().label }}</h2>
            @if (level() !== null) {
              <span class="lvl-chip">Stufe {{ level() }}</span>
            }
            <span class="kind-chip">{{ kindLabel() }}</span>
            @if (techEffect(); as te) {
              <span class="branch-chip">{{ te.branch }}</span>
            }
          </div>
        </header>

        @if (tags()?.length) {
          <div class="tag-row">
            @for (t of tags()!; track t.label) {
              <span class="tag" [class.tip]="t.tip" [attr.data-tip]="t.tip ?? null">@if (t.icon) {<img class="tag-ico" [src]="t.icon" alt="" (error)="hideImg($event)" />} @else {{{ t.glyph }} }{{ t.label }}</span>
            }
          </div>
        }

        @if (description(); as d) {
          <p class="story">{{ d }}</p>
        }

        @if (rangeBand(); as rb) {
          <div class="range-info">
            <div class="ri-head"><span class="ri-dot">{{ rb.dot }}</span> Reichweite: <strong>{{ rb.label }}</strong> · {{ rb.phase }}</div>
            <p class="ri-tip">{{ rb.tip }}</p>
          </div>
        }

        @if (!techEffect() && effect(); as e) {
          <div class="effect">★ {{ e }}</div>
        }

        @if (techEffect(); as te) {
          <div class="effect">★ {{ te.summary }}</div>
          @if (levelEffectLine(); as le) {
            <div class="lvl-effect">
              <span class="le-label">{{ le.label }}</span>
              <span class="mono">{{ le.current }}</span>
              <span class="le-arrow">→</span>
              <span class="mono le-next">{{ le.next }}</span>
              <span class="le-hint faint">(nächste Stufe)</span>
            </div>
          }
        }

        @if (stats().length) {
          <div class="stat-grid">
            @for (s of stats(); track s.label) {
              <div class="stat">
                <span class="stat-glyph">
                  @if (s.iconKey) {
                    <img class="stat-ico" [src]="statIconFn(s.iconKey)" alt="" (error)="onStatIcoError($event)" />
                    <span class="stat-glyph-fb">{{ s.glyph }}</span>
                  } @else {
                    {{ s.glyph }}
                  }
                </span>
                <span class="stat-label">{{ s.label }}</span>
                <span class="stat-val mono">{{ s.value }}</span>
              </div>
            }
          </div>
        }

        @if (nextLevels(); as nl) {
          <section class="block">
            <div class="block-title"><app-btn-icon [src]="uiIcon('levels')" glyph="📈" [size]="16" /> Nächste Stufen{{ nl.note }}</div>
            <table class="next-levels">
              <thead>
                <tr><th>Stufe</th><th><app-icon-tile [glyph]="nl.glyph" [src]="nl.img" [size]="16" variant="muted" /> {{ nl.outLabel }}</th><th>Zuwachs</th></tr>
              </thead>
              <tbody>
                @for (r of nl.rows; track r.level) {
                  <tr>
                    <td class="mono">{{ r.level }}</td>
                    <td class="mono">{{ r.value }}{{ nl.unit }}</td>
                    <td class="mono delta">+{{ r.delta }}{{ nl.unit }}</td>
                  </tr>
                }
              </tbody>
            </table>
          </section>
        }

        @if (rapidfire().length) {
          <section class="block">
            <div class="block-title tip" data-tip="Schnellfeuer: diese Einheit darf nach einem Treffer sofort erneut auf das genannte Ziel feuern (Wahrscheinlichkeit (n−1)/n).">
              <app-btn-icon [src]="uiIcon('rapidfire')" glyph="💥" [size]="16" /> Schnellfeuer gegen
            </div>
            <div class="rf-list">
              @for (r of rapidfire(); track r.type) {
                <span class="rf">
                  <app-icon-tile [glyph]="r.glyph" [src]="r.img" [size]="26" variant="muted" />
                  {{ r.label }}
                  <span class="rf-mult mono">×{{ r.mult }}</span>
                </span>
              }
            </div>
          </section>
        }

        @if (rapidfireFrom().length) {
          <section class="block">
            <div class="block-title tip" data-tip="Diese Einheiten haben Schnellfeuer GEGEN dieses Objekt — sie feuern nach einem Treffer sofort erneut darauf. (Gegenrichtung)">
              <app-btn-icon [src]="uiIcon('target')" glyph="🎯" [size]="16" /> Anfällig für Schnellfeuer von
            </div>
            <div class="rf-list">
              @for (r of rapidfireFrom(); track r.type) {
                <span class="rf danger">
                  <app-icon-tile [glyph]="r.glyph" [src]="r.img" [size]="26" variant="muted" />
                  {{ r.label }}
                  <span class="rf-mult mono">×{{ r.mult }}</span>
                </span>
              }
            </div>
          </section>
        }

        @if (requirementRows().length) {
          <section class="block">
            <div class="block-title"><app-btn-icon [src]="uiIcon('requirements')" glyph="🔗" [size]="16" /> Voraussetzungen</div>
            <div class="req-list">
              @for (r of requirementRows(); track r.type) {
                <span class="req" [class.met]="r.met === true" [class.unmet]="r.met === false">
                  @if (r.met === true) {
                    <span class="mark ok">✓</span>
                  } @else if (r.met === false) {
                    <span class="mark no">✕</span>
                  } @else {
                    <span class="mark">•</span>
                  }
                  {{ r.label }} {{ r.level }}
                </span>
              }
            </div>
            <a class="tree-link" [routerLink]="['/techtree']" [queryParams]="{ focus: type() }" (click)="close.emit()">Im Techbaum ansehen →</a>
          </section>
        }

        @if (unlocks().length) {
          <section class="block">
            <div class="block-title"><app-btn-icon [src]="uiIcon('unlock')" glyph="🔓" [size]="16" /> Schaltet frei</div>
            <div class="req-list">
              @for (u of unlocks(); track u.type) {
                <span class="req unlock" [attr.data-tip]="u.kind + (u.reqLevel > 1 ? ' · ab Stufe ' + u.reqLevel : '')">
                  <app-icon-tile [glyph]="u.glyph" [src]="u.img" [size]="18" variant="muted" /> {{ u.label }}
                  @if (u.reqLevel > 1) { <span class="req-lvl mono">St. {{ u.reqLevel }}</span> }
                </span>
              }
            </div>
          </section>
        }

        @if (shownCost(); as c) {
          <div class="cost-row">
            <app-cost-line [cost]="c" [available]="available()" />
            @if (buildSeconds() !== null) {
              <span class="time mono"><app-btn-icon [src]="uiIcon('time')" glyph="⏱" [size]="14" /> {{ formatTime(buildSeconds()!) }}</span>
            }
          </div>
        }

        @if (actionLabel(); as label) {
          <div class="actions">
            @if (quantity()) {
              <input
                class="qty"
                type="number"
                min="1"
                [value]="qty()"
                (input)="onQty($event)"
                [disabled]="actionDisabled()"
                aria-label="Anzahl"
              />
            }
            <button
              class="btn btn-primary"
              type="button"
              [disabled]="actionDisabled() || pending()"
              (click)="confirm.emit(quantity() ? qty() : 1)"
            >
              {{ pending() ? '…' : label }}
            </button>
          </div>
          @if (actionHint(); as h) {
            <p class="hint">{{ h }}</p>
          }
        }
      </div>
    </div>
  `,
  styles: [
    `
      .backdrop {
        position: fixed;
        inset: 0;
        z-index: 100;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: var(--sp-4);
        background: rgba(4, 7, 14, 0.72);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        animation: fade var(--motion-fast) var(--ease-out);
      }
      @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
      /* .glass (global) liefert Background/Blur/Border/Elevation; hier nur Layout + Signatur-Ecke. */
      .popup {
        position: relative;
        width: 100%;
        max-width: 540px;
        max-height: 88vh;
        overflow-y: auto;
        border-radius: var(--r-lg);
        padding: var(--sp-5);
        /* Marken-Signatur: abgeschraegte Ecke oben-rechts (konsistent ueber alle Dialoge). */
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
        animation: pop var(--motion-base) var(--ease-out);
      }
      @keyframes pop { from { transform: translateY(8px) scale(0.98); opacity: 0; } to { transform: none; opacity: 1; } }
      .x {
        position: absolute; top: var(--sp-2); right: var(--sp-2);
        width: 32px; height: 32px; border-radius: var(--r-sm);
        background: rgba(255,255,255,0.05); border: 1px solid var(--border);
        color: var(--text-dim); cursor: pointer; font-size: var(--fs-sm);
        display: flex; align-items: center; justify-content: center;
        transition: color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .x:hover { color: var(--text); background: rgba(255,255,255,0.1); }

      .head { display: flex; align-items: center; gap: var(--sp-3); padding-right: var(--sp-8); }
      .head-text { display: flex; align-items: center; flex-wrap: wrap; gap: var(--sp-2); }
      .head-text h2 { margin: 0; font-size: var(--fs-lg); }
      .lvl-chip, .kind-chip, .branch-chip {
        font-family: var(--font-display);
        font-size: var(--fs-xs); letter-spacing: 0.06em; text-transform: uppercase;
        padding: 2px var(--sp-2); border-radius: var(--r-pill); border: 1px solid var(--border);
        color: var(--text-dim); background: rgba(255,255,255,0.04);
      }
      .lvl-chip { color: var(--accent); border-color: var(--accent-dim); background: var(--accent-soft); }
      .branch-chip {
        color: var(--warn);
        border-color: color-mix(in srgb, var(--warn) 40%, transparent);
        background: color-mix(in srgb, var(--warn) 8%, transparent);
      }

      .lvl-effect {
        margin-top: var(--sp-2); display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap;
        font-size: var(--fs-base);
      }
      .le-label { color: var(--text-dim); }
      .le-arrow { color: var(--text-dim); }
      .le-next { color: var(--accent); font-weight: 700; }
      .le-hint { font-size: var(--fs-xs); }
      .req-lvl {
        margin-left: var(--sp-1); font-size: var(--fs-xs); color: var(--accent);
        border: 1px solid var(--accent-dim); border-radius: var(--r-pill); padding: 0 var(--sp-1);
      }

      .tag-row { display: flex; flex-wrap: wrap; gap: var(--sp-1); margin-top: var(--sp-3); }
      .tag {
        font-size: var(--fs-xs); padding: 2px var(--sp-2); border-radius: var(--r-sm);
        background: rgba(255,255,255,0.05); color: var(--text-dim); border: 1px solid var(--border);
      }
      .tag-ico {
        width: 1.2em; height: 1.2em; object-fit: contain;
        vertical-align: -0.25em; margin-right: 0.25em;
      }
      .story {
        margin: var(--sp-3) 0 0; font-size: var(--fs-base); line-height: 1.55;
        color: var(--text); opacity: 0.9;
        border-left: 2px solid var(--accent-dim); padding-left: var(--sp-3);
      }
      .effect {
        margin-top: var(--sp-3); font-size: var(--fs-sm); color: var(--accent);
        background: var(--accent-soft); border: 1px solid var(--border);
        border-radius: var(--r-md); padding: var(--sp-2) var(--sp-3);
      }
      .range-info {
        margin-top: var(--sp-3); border: 1px solid var(--border); border-radius: var(--r-md);
        padding: var(--sp-2) var(--sp-3); background: rgba(255,255,255,0.03);
      }
      .ri-head { font-size: var(--fs-sm); color: var(--text); }
      .ri-head strong { color: var(--accent); }
      .ri-dot { margin-right: 0.2em; }
      .ri-tip { margin: var(--sp-1) 0 0; font-size: var(--fs-sm); color: var(--text-dim); line-height: 1.5; }

      .stat-grid {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: var(--sp-2); margin-top: var(--sp-4);
      }
      .stat {
        display: flex; align-items: center; gap: var(--sp-2);
        background: rgba(255,255,255,0.03); border: 1px solid var(--border);
        border-radius: var(--r-md); padding: var(--sp-2) var(--sp-3);
      }
      .stat-glyph { font-size: var(--fs-md); display: inline-flex; align-items: center; }
      .stat-ico { width: 18px; height: 18px; object-fit: contain; }
      .stat-glyph-fb { display: none; }
      .stat-label { font-size: var(--fs-sm); color: var(--text-dim); flex: 1; }
      .stat-val { font-size: var(--fs-base); font-weight: 600; }

      .block { margin-top: var(--sp-4); }
      .block-title {
        font-family: var(--font-display);
        font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.1em;
        color: var(--text-dim); margin-bottom: var(--sp-2);
      }
      .next-levels { width: 100%; border-collapse: collapse; font-size: var(--fs-sm); }
      .next-levels th {
        text-align: left; font-weight: 600; color: var(--text-dim); padding: var(--sp-1) var(--sp-2);
        border-bottom: 1px solid var(--border);
      }
      .next-levels td { padding: var(--sp-1) var(--sp-2); border-bottom: 1px solid rgba(255,255,255,0.05); }
      .next-levels td.delta { color: var(--ok); }
      .rf-list, .req-list { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
      .rf, .req {
        display: inline-flex; align-items: center; gap: var(--sp-1);
        font-size: var(--fs-sm); padding: var(--sp-1) var(--sp-2); border-radius: var(--r-pill);
        background: rgba(255,255,255,0.04); border: 1px solid var(--border);
        color: var(--text-dim);
      }
      .rf-glyph { font-size: var(--fs-base); }
      .rf { padding-left: var(--sp-1); }
      .rf-mult { color: var(--accent); font-weight: 700; }
      .rf.danger { border-color: var(--danger-dim); color: var(--danger); }
      .rf.danger .rf-mult { color: var(--danger); }
      .req .mark { font-weight: 700; }
      .req .mark.ok { color: var(--ok); }
      .req .mark.no { color: var(--danger); }
      .req.met { color: var(--text); border-color: var(--accent-dim); }
      .req.unmet { color: var(--danger); border-color: var(--danger-dim); }
      .req.unlock { color: var(--text-dim); }
      .tree-link { display: inline-block; margin-top: var(--sp-2); font-size: var(--fs-sm); }

      .cost-row {
        display: flex; align-items: center; justify-content: space-between; gap: var(--sp-3);
        flex-wrap: wrap; margin-top: var(--sp-4);
        padding-top: var(--sp-3); border-top: 1px solid var(--border);
      }
      .cost-row .cost-line { font-size: var(--fs-base); }
      .time { font-size: var(--fs-sm); color: var(--text-dim); }

      .actions { display: flex; align-items: center; gap: var(--sp-2); margin-top: var(--sp-3); }
      .actions .qty { width: 90px; text-align: center; flex: 0 0 auto; }
      .actions .btn { flex: 1; }
      .hint { margin: var(--sp-2) 0 0; font-size: var(--fs-sm); color: var(--warn); }

      @media (max-width: 560px) {
        .backdrop { padding: var(--sp-2); }
        .popup { max-width: 100%; max-height: 94vh; padding: var(--sp-4); }
        .head-text h2 { font-size: var(--fs-md); }
      }
    `,
  ],
})
export class DetailPopupComponent {
  private readonly balance = inject(BalanceService);
  private readonly gameState = inject(GameStateService);

  readonly kind = input.required<DetailKind>();
  readonly type = input.required<string>();
  /** Aktuelle Stufe (Gebaeude/Forschung). null = nicht stufenbasiert. */
  readonly level = input<number | null>(null);
  /** Kosten der naechsten Aktion; ohne Angabe Basis-Kosten aus balance.json. */
  readonly cost = input<ResourceCost | null>(null);
  readonly available = input<Partial<Record<string, number>> | null>(null);
  readonly buildSeconds = input<number | null>(null);
  /** Voraussetzungen inkl. Erfuellt-Status; ohne Angabe aus balance.json abgeleitet. */
  readonly requirements = input<DetailRequirement[] | null>(null);
  readonly actionLabel = input<string | null>(null);
  readonly actionDisabled = input<boolean>(false);
  readonly actionHint = input<string | null>(null);
  readonly pending = input<boolean>(false);
  /** Zeigt ein Mengen-Eingabefeld (Schiffe/Verteidigung). */
  readonly quantity = input<boolean>(false);
  /** Kurz-Tags (Waffentyp, Reichweite, Antrieb …). */
  readonly tags = input<DetailTag[] | null>(null);

  readonly close = output<void>();
  readonly confirm = output<number>();

  protected readonly qty = signal(1);

  onQty(event: Event): void {
    const v = Math.max(1, Math.floor(Number((event.target as HTMLInputElement).value) || 1));
    this.qty.set(v);
  }

  private readonly metaMap = computed<Record<string, { label: string; glyph: string; desc?: string }>>(() => {
    switch (this.kind()) {
      case 'ship': return SHIP_META;
      case 'building': return BUILDING_META;
      case 'tech': return TECH_META;
      case 'defense': return DEFENSE_META;
    }
  });

  protected readonly meta = computed(() => metaFor(this.metaMap(), this.type()));

  /** Mk2/Elite-Schiff -> goldener Rahmen ueber dem Header-Icon. */
  protected readonly isMk2Ship = computed(() => this.kind() === 'ship' && isMk2(this.type()));

  /** Beschreibung erbt fuer Mk2-Schiffe automatisch vom Parent (via metaFor). */
  protected readonly description = computed(() => this.meta().desc ?? null);

  /**
   * Reichweite/Gefechtsphase der Einheit (Nah/Mittel/Fern) für die taktische Aufschlüsselung —
   * direkt aus ``combat_roster``. Nur für bewaffnete Schiffe + Verteidigung; unbewaffnete
   * Einheiten (Frachter, Sonde) nehmen nicht am Feuergefecht teil, daher kein Band.
   */
  protected readonly rangeBand = computed<{ label: string; dot: string; phase: string; tip: string } | null>(() => {
    if (this.kind() !== 'ship' && this.kind() !== 'defense') {
      return null;
    }
    const e = this.entry();
    if (this.kind() === 'ship' && !(typeof e?.['attack'] === 'number' && (e['attack'] as number) > 0)) {
      return null; // unbewaffnetes Schiff -> kein Gefechts-Band
    }
    const roster = (this.balance.value as { combat_roster?: Record<string, { range?: string }> } | null)?.combat_roster;
    const key = roster?.[this.type()]?.range ?? (this.kind() === 'defense' ? 'far' : 'near');
    return RANGE_META[key] ?? null;
  });

  protected readonly kindLabel = computed(() => {
    switch (this.kind()) {
      case 'ship': return 'Schiff';
      case 'building': return 'Gebäude';
      case 'tech': return 'Forschung';
      case 'defense': return 'Verteidigung';
    }
  });

  protected readonly imgSrc = computed<string | null>(() => {
    switch (this.kind()) {
      case 'ship': return shipIcon(this.type());
      case 'building': return `assets/img/buildings/${this.type()}.png`;
      case 'defense': return `assets/img/defenses/${this.type()}.png`;
      case 'tech': return techIcon(this.type());
    }
  });

  /** Blendet ein nicht ladbares Inline-Tag-Icon aus (Label bleibt sichtbar). */
  hideImg(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }

  protected readonly statIconFn = statIcon;
  protected readonly uiIcon = uiIcon;

  /** Stat-Icon nicht ladbar -> Glyph-Fallback (Geschwister-Span) einblenden. */
  onStatIcoError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.style.display = 'none';
    const fb = img.nextElementSibling as HTMLElement | null;
    if (fb) {
      fb.style.display = 'inline';
    }
  }

  /** Roh-Eintrag aus balance.json fuer dieses Objekt. */
  private readonly entry = computed<Record<string, unknown> | null>(() => {
    const b = this.balance.value;
    if (!b) {
      return null;
    }
    const t = this.type();
    switch (this.kind()) {
      case 'ship': return (b.ships as Record<string, Record<string, unknown>>)[t] ?? null;
      case 'building': return (b.buildings as Record<string, Record<string, unknown>>)[t] ?? null;
      case 'defense': return (b.defenses as Record<string, Record<string, unknown>>)[t] ?? null;
      case 'tech': return (b.research?.techs as Record<string, Record<string, unknown>>)?.[t] ?? null;
    }
  });

  protected readonly effect = computed(() => {
    const e = this.entry()?.['effect'];
    return typeof e === 'string' ? e : null;
  });

  /** Effekt-Metadaten einer Forschung (Zweig + Zusammenfassung + Pro-Stufe-Effekt). */
  protected readonly techEffect = computed(() =>
    this.kind() === 'tech' ? (TECH_EFFECTS[this.type()] ?? null) : null,
  );

  /** "Aktuell -> naechste Stufe" fuer numerische Forschungs-Effekte. */
  protected readonly levelEffectLine = computed<{ label: string; current: string; next: string } | null>(() => {
    const te = this.techEffect();
    if (!te?.levelEffect) {
      return null;
    }
    const { label, perLevel, unit, base = 0 } = te.levelEffect;
    const lvl = this.level() ?? 0;
    const fmt = (n: number) => (unit === '%' ? `+${n}${unit}` : `${n}${unit}`);
    return { label, current: fmt(base + perLevel * lvl), next: fmt(base + perLevel * (lvl + 1)) };
  });

  /** Produktions-Vorschau der naechsten 5 Stufen (nur Produktionsgebaeude: Minen/Solar/Fusion). */
  protected readonly nextLevels = computed<
    { glyph: string; img: string; outLabel: string; unit: string; note: string; rows: { level: number; value: string; delta: string }[] } | null
  >(() => {
    if (this.kind() !== 'building') {
      return null;
    }
    const e = this.entry();
    const b = this.balance.value as any;
    if (!e || !b) {
      return null;
    }
    const n = (k: string) => (typeof e[k] === 'number' ? (e[k] as number) : null);
    const speed = typeof b.universe?.speed === 'number' ? b.universe.speed : 1;

    let base: number | null = null;
    let growth = 1;
    let glyph = '📦';
    let img = '';
    let outLabel = 'Produktion';
    let unit = '';
    let note = '';
    let useSpeed = false;

    if (n('prod_base') != null && n('prod_growth') != null) {
      // Minen: prod_base * Stufe * growth^Stufe * Universums-Speed (pro Stunde).
      base = n('prod_base');
      growth = n('prod_growth')!;
      useSpeed = true;
      unit = '/h';
      const map: Record<string, [string, string, string]> = {
        metal_mine: ['⛏️', 'Metall', 'metal'],
        crystal_mine: ['💎', 'Kristall', 'crystal'],
        deuterium_synth: ['🛢️', 'Deuterium', 'deuterium'],
      };
      const m = map[this.type()];
      if (m) {
        glyph = m[0];
        outLabel = m[1];
        img = `assets/img/resources/${m[2]}.png`;
      }
      if (this.type() === 'deuterium_synth') {
        note = ' (ohne Temperatur-Faktor)';
      }
    } else if (n('energy_prod_base') != null && n('energy_prod_growth') != null) {
      // Solarkraftwerk: Energie (nicht speed-skaliert). Fusionsreaktor ausgenommen — sein
      // Wachstum haengt an der Energietechnik, nicht an energy_prod_growth.
      base = n('energy_prod_base');
      growth = n('energy_prod_growth')!;
      glyph = '⚡';
      img = 'assets/img/resources/energy.png';
      outLabel = 'Energie';
    }
    if (base == null) {
      return null; // kein Produktionsgebaeude
    }

    const at = (lvl: number): number => {
      if (lvl <= 0) {
        return 0;
      }
      const raw = base! * lvl * Math.pow(growth, lvl);
      return useSpeed ? raw * speed : raw;
    };
    const cur = this.level() ?? 0;
    const rows = [];
    for (let i = 1; i <= 5; i++) {
      const lvl = cur + i;
      const value = at(lvl);
      const delta = value - at(lvl - 1);
      rows.push({
        level: lvl,
        value: Math.round(value).toLocaleString('de-DE'),
        delta: Math.round(delta).toLocaleString('de-DE'),
      });
    }
    return { glyph, img, outLabel, unit, note, rows };
  });

  protected readonly stats = computed<StatRow[]>(() => {
    const e = this.entry();
    if (!e) {
      return [];
    }
    const num = (k: string) => (typeof e[k] === 'number' ? (e[k] as number) : null);
    const rows: StatRow[] = [];
    const push = (glyph: string, iconKey: string, label: string, v: number | null, suffix = '') => {
      if (v !== null && v !== 0) {
        rows.push({ glyph, iconKey, label, value: this.fmt(v) + suffix });
      }
    };
    if (this.kind() === 'ship' || this.kind() === 'defense') {
      push('⚔️', 'attack', 'Angriff', num('attack'));
      push('🛡️', 'shield', 'Schild', num('shield'));
      // Huelle = (Metall + Kristall) / 10 (wie Kampf-Engine; kein eigenes balance-Feld).
      const cost = e['cost'] as Record<string, number> | undefined;
      const hull = cost ? Math.round(((cost['metal'] ?? 0) + (cost['crystal'] ?? 0)) / 10) : null;
      push('🩹', 'hull', 'Hülle', hull);
    }
    if (this.kind() === 'ship') {
      push('📦', 'cargo', 'Frachtraum', num('cargo'));
      push('🚀', 'speed', 'Speed', num('speed'));
      push('⛽', 'fuel', 'Sprit/Distanz', num('fuel'));
      // Treibstofftank = mitgeführter Sprit-Vorrat (Reichweiten-Reserve), getrennt vom Verbrauch oben.
      push('🛢️', '', 'Treibstofftank', num('fuel_tank'));
    }
    // Solarsatellit: temperaturabhaengige Energie je Einheit (am aktuell gewaehlten Planeten).
    if (this.type() === 'solar_satellite') {
      const cfg = e['energy_prod'] as { temp_offset?: number; divisor?: number } | undefined;
      if (cfg) {
        const planet = this.gameState.activePlanet();
        const temp = planet?.temp_max ?? 0;
        const per = Math.max(0, Math.floor((temp + (cfg.temp_offset ?? 0)) / (cfg.divisor ?? 1)));
        rows.push({
          glyph: '⚡',
          label: 'Energie/Einheit',
          value: planet ? `+${per} (bei ${temp}°C)` : `+${per}`,
        });
      }
    }
    return rows;
  });

  /** Bild-Pfad einer Einheit (Verteidigung vs. Schiff anhand balance.json). */
  private unitImg(type: string): string {
    const isDef = !!(this.balance.value?.defenses as Record<string, unknown> | undefined)?.[type];
    return isDef ? `assets/img/defenses/${type}.png` : `assets/img/ships/${type}.png`;
  }

  private rfRow(type: string, mult: number): RapidFireRow {
    const m = metaFor({ ...SHIP_META, ...DEFENSE_META }, type);
    return { type, glyph: m.glyph, label: m.label, mult, img: this.unitImg(type) };
  }

  /** Schnellfeuer, das DIESE Einheit austeilt (Schiffe: rapidfire, Verteidigung: rapidfire_against). */
  protected readonly rapidfire = computed<RapidFireRow[]>(() => {
    const e = this.entry();
    const rf = e?.['rapidfire'] ?? e?.['rapidfire_against'];
    if (!rf || typeof rf !== 'object') {
      return [];
    }
    return Object.entries(rf as Record<string, number>)
      .map(([target, mult]) => this.rfRow(target, mult))
      .sort((a, b) => b.mult - a.mult);
  });

  /** Gegenrichtung: Einheiten, die Schnellfeuer GEGEN dieses Objekt haben (wer es kontert). */
  protected readonly rapidfireFrom = computed<RapidFireRow[]>(() => {
    const b = this.balance.value;
    if (!b) {
      return [];
    }
    const me = this.type();
    const rows: RapidFireRow[] = [];
    const scan = (map: Record<string, Record<string, unknown>> | undefined, key: string) => {
      for (const [unit, cfg] of Object.entries(map ?? {})) {
        if (unit.startsWith('_')) {
          continue;
        }
        const rf = cfg?.[key];
        if (rf && typeof rf === 'object') {
          const mult = (rf as Record<string, number>)[me];
          if (typeof mult === 'number') {
            rows.push(this.rfRow(unit, mult));
          }
        }
      }
    };
    scan(b.ships as Record<string, Record<string, unknown>>, 'rapidfire');
    scan(b.defenses as Record<string, Record<string, unknown>>, 'rapidfire_against');
    return rows.sort((a, b) => b.mult - a.mult);
  });

  protected readonly requirementRows = computed<{ type: string; level: number; met?: boolean; label: string }[]>(() => {
    const reqMeta = { ...BUILDING_META, ...TECH_META };
    const provided = this.requirements();
    if (provided && provided.length) {
      return provided.map((r) => ({ ...r, label: metaFor(reqMeta, r.type).label }));
    }
    // Fallback: aus balance.json ableiten (ohne Erfuellt-Status).
    const req = this.entry()?.['requires'];
    if (!req || typeof req !== 'object') {
      return [];
    }
    return Object.entries(req as Record<string, number>).map(([type, level]) => ({
      type,
      level,
      met: undefined,
      label: metaFor(reqMeta, type).label,
    }));
  });

  /** Items, die dieses Objekt als Voraussetzung haben (Vorwaerts-Abhaengigkeiten). */
  protected readonly unlocks = computed<{ type: string; label: string; glyph: string; img: string; reqLevel: number; kind: string }[]>(() => {
    const b = this.balance.value;
    if (!b) {
      return [];
    }
    const t = this.type();
    const out: { type: string; label: string; glyph: string; img: string; reqLevel: number; kind: string }[] = [];
    const seen = new Set<string>();
    const scan = (
      map: Record<string, Record<string, unknown>> | undefined,
      metaMap: Record<string, { label: string; glyph: string }>,
      kind: string,
      imgBase: string,
    ) => {
      for (const [key, entry] of Object.entries(map ?? {})) {
        if (key === t || seen.has(key)) {
          continue;
        }
        const req = entry?.['requires'];
        if (req && typeof req === 'object' && (req as Record<string, unknown>)[t] != null) {
          const m = metaFor(metaMap, key);
          const reqLevel = Number((req as Record<string, unknown>)[t]) || 1;
          out.push({ type: key, label: m.label, glyph: m.glyph, img: `assets/img/${imgBase}/${key}.png`, reqLevel, kind });
          seen.add(key);
        }
      }
    };
    scan(b.research?.techs as Record<string, Record<string, unknown>>, TECH_META, 'Forschung', 'tech');
    scan(b.ships as Record<string, Record<string, unknown>>, SHIP_META, 'Schiff', 'ships');
    scan(b.defenses as Record<string, Record<string, unknown>>, DEFENSE_META, 'Verteidigung', 'defenses');
    scan(b.buildings as Record<string, Record<string, unknown>>, BUILDING_META, 'Gebäude', 'buildings');
    return out;
  });

  /** Anzuzeigende Kosten: explizit gereicht oder Basis aus balance.json. */
  protected readonly shownCost = computed<ResourceCost | null>(() => {
    const c = this.cost();
    if (c) {
      return c;
    }
    const raw = this.entry()?.['cost'];
    if (raw && typeof raw === 'object') {
      const r = raw as Record<string, number>;
      return { metal: r['metal'] ?? 0, crystal: r['crystal'] ?? 0, deuterium: r['deuterium'] ?? 0 };
    }
    return null;
  });

  private fmt(n: number): string {
    return Math.round(n).toLocaleString('de-DE');
  }

  formatTime(seconds: number): string {
    const s = Math.max(0, Math.round(seconds));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${sec}s`;
    return `${sec}s`;
  }
}
