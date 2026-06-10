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
import {
  BUILDING_META,
  DEFENSE_META,
  SHIP_META,
  TECH_META,
  metaFor,
  TECH_EFFECTS,
} from '../../core/models/display';
import { techIcon } from '../../core/models/icon-assets';
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
  glyph: string;
  label: string;
  mult: number;
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
  imports: [RouterLink, CostLineComponent, IconTileComponent],
  host: {
    '(document:keydown.escape)': 'close.emit()',
  },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>

        <header class="head">
          <app-icon-tile
            [glyph]="meta().glyph"
            [src]="imgSrc()"
            [size]="84"
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

        @if (effect(); as e) {
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
                <span class="stat-glyph">{{ s.glyph }}</span>
                <span class="stat-label">{{ s.label }}</span>
                <span class="stat-val mono">{{ s.value }}</span>
              </div>
            }
          </div>
        }

        @if (rapidfire().length) {
          <section class="block">
            <div class="block-title tip" data-tip="Schnellfeuer: dieses Schiff darf nach einem Treffer sofort erneut auf das genannte Ziel feuern.">
              💥 Schnellfeuer gegen
            </div>
            <div class="rf-list">
              @for (r of rapidfire(); track r.label) {
                <span class="rf">
                  <span class="rf-glyph">{{ r.glyph }}</span> {{ r.label }}
                  <span class="rf-mult mono">×{{ r.mult }}</span>
                </span>
              }
            </div>
          </section>
        }

        @if (requirementRows().length) {
          <section class="block">
            <div class="block-title">🔗 Voraussetzungen</div>
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
            <div class="block-title">🔓 Schaltet frei</div>
            <div class="req-list">
              @for (u of unlocks(); track u.type) {
                <span class="req unlock" [attr.data-tip]="u.kind + (u.reqLevel > 1 ? ' · ab Stufe ' + u.reqLevel : '')">
                  <span class="rf-glyph">{{ u.glyph }}</span> {{ u.label }}
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
              <span class="time mono">⏱ {{ formatTime(buildSeconds()!) }}</span>
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
        padding: 1rem;
        background: rgba(4, 7, 14, 0.72);
        backdrop-filter: blur(4px);
        animation: fade 0.12s ease;
      }
      @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
      .popup {
        position: relative;
        width: 100%;
        max-width: 540px;
        max-height: 88vh;
        overflow-y: auto;
        background: linear-gradient(160deg, var(--surface-2), var(--surface));
        border: 1px solid var(--border-strong);
        border-radius: var(--radius);
        box-shadow: var(--shadow), var(--glow);
        padding: 1.2rem 1.3rem 1.3rem;
        /* Marken-Signatur: abgeschraegte Ecke oben-rechts (Style Bible). */
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
        animation: pop 0.14s ease;
      }
      @keyframes pop { from { transform: translateY(8px) scale(0.98); opacity: 0; } to { transform: none; opacity: 1; } }
      .x {
        position: absolute; top: 0.6rem; right: 0.7rem;
        width: 30px; height: 30px; border-radius: 8px;
        background: rgba(255,255,255,0.05); border: 1px solid var(--border);
        color: var(--text-dim); cursor: pointer; font-size: 0.85rem;
        display: flex; align-items: center; justify-content: center;
      }
      .x:hover { color: var(--text); background: rgba(255,255,255,0.1); }

      .head { display: flex; align-items: center; gap: 0.9rem; padding-right: 2rem; }
      .head-text { display: flex; align-items: center; flex-wrap: wrap; gap: 0.5rem; }
      .head-text h2 { margin: 0; font-size: 1.25rem; }
      .lvl-chip, .kind-chip {
        font-size: 0.7rem; letter-spacing: 0.06em; text-transform: uppercase;
        padding: 0.12rem 0.5rem; border-radius: 99px; border: 1px solid var(--border);
        color: var(--text-dim); background: rgba(255,255,255,0.04);
      }
      .lvl-chip { color: var(--accent); border-color: var(--accent-dim); }
      .branch-chip {
        font-size: 0.7rem; letter-spacing: 0.06em; text-transform: uppercase;
        padding: 0.12rem 0.5rem; border-radius: 99px;
        color: #ffd24a; border: 1px solid rgba(255,210,74,0.4); background: rgba(255,210,74,0.08);
      }

      .lvl-effect {
        margin-top: 0.4rem; display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap;
        font-size: 0.9rem;
      }
      .le-label { color: var(--text-dim); }
      .le-arrow { color: var(--text-dim); }
      .le-next { color: var(--accent); font-weight: 700; }
      .le-hint { font-size: 0.74rem; }
      .req-lvl {
        margin-left: 0.3rem; font-size: 0.72rem; color: var(--accent);
        border: 1px solid var(--accent-dim); border-radius: 99px; padding: 0 0.35rem;
      }

      .tag-row { display: flex; flex-wrap: wrap; gap: 0.35rem; margin-top: 0.8rem; }
      .tag {
        font-size: 0.74rem; padding: 0.18rem 0.5rem; border-radius: 6px;
        background: rgba(255,255,255,0.05); color: #b9c6de; border: 1px solid var(--border);
      }
      .tag-ico {
        width: 1.2em; height: 1.2em; object-fit: contain;
        vertical-align: -0.25em; margin-right: 0.25em;
      }
      .story {
        margin: 0.9rem 0 0; font-size: 0.9rem; line-height: 1.55;
        color: var(--text); opacity: 0.9;
        border-left: 2px solid var(--accent-dim); padding-left: 0.8rem;
      }
      .effect {
        margin-top: 0.8rem; font-size: 0.85rem; color: var(--accent);
        background: rgba(46,230,214,0.08); border: 1px solid var(--border);
        border-radius: var(--radius-sm); padding: 0.45rem 0.65rem;
      }

      .stat-grid {
        display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr));
        gap: 0.4rem; margin-top: 1rem;
      }
      .stat {
        display: flex; align-items: center; gap: 0.45rem;
        background: rgba(255,255,255,0.03); border: 1px solid var(--border);
        border-radius: var(--radius-sm); padding: 0.45rem 0.6rem;
      }
      .stat-glyph { font-size: 1rem; }
      .stat-label { font-size: 0.78rem; color: var(--text-dim); flex: 1; }
      .stat-val { font-size: 0.92rem; font-weight: 600; }

      .block { margin-top: 1rem; }
      .block-title {
        font-size: 0.72rem; text-transform: uppercase; letter-spacing: 0.1em;
        color: #b9c6de; margin-bottom: 0.5rem;
      }
      .rf-list, .req-list { display: flex; flex-wrap: wrap; gap: 0.4rem; }
      .rf, .req {
        display: inline-flex; align-items: center; gap: 0.3rem;
        font-size: 0.8rem; padding: 0.22rem 0.55rem; border-radius: 99px;
        background: rgba(255,255,255,0.04); border: 1px solid var(--border);
        color: var(--text-dim);
      }
      .rf-glyph { font-size: 0.9rem; }
      .rf-mult { color: var(--accent); font-weight: 700; }
      .req .mark { font-weight: 700; }
      .req .mark.ok { color: var(--ok); }
      .req .mark.no { color: var(--magenta); }
      .req.met { color: var(--text); border-color: var(--accent-dim); }
      .req.unmet { color: #ffd6ec; border-color: var(--magenta-dim); }
      .req.unlock { color: var(--text-dim); }
      .tree-link { display: inline-block; margin-top: 0.55rem; font-size: 0.82rem; }

      .cost-row {
        display: flex; align-items: center; justify-content: space-between; gap: 0.8rem;
        flex-wrap: wrap; margin-top: 1rem;
        padding-top: 0.8rem; border-top: 1px solid var(--border);
      }
      .cost-row .cost-line { font-size: 0.92rem; }
      .time { font-size: 0.84rem; color: var(--text-dim); }

      .actions { display: flex; align-items: center; gap: 0.6rem; margin-top: 0.9rem; }
      .actions .qty { width: 90px; text-align: center; flex: 0 0 auto; }
      .actions .btn { flex: 1; }
      .hint { margin: 0.5rem 0 0; font-size: 0.8rem; color: var(--warn); }

      @media (max-width: 560px) {
        .popup { padding: 1rem; }
        .head-text h2 { font-size: 1.1rem; }
      }
    `,
  ],
})
export class DetailPopupComponent {
  private readonly balance = inject(BalanceService);

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

  protected readonly description = computed(() => this.metaMap()[this.type()]?.desc ?? null);

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
      case 'ship': return `assets/img/ships/${this.type()}.png`;
      case 'building': return `assets/img/buildings/${this.type()}.png`;
      case 'defense': return `assets/img/defenses/${this.type()}.png`;
      case 'tech': return techIcon(this.type());
    }
  });

  /** Blendet ein nicht ladbares Inline-Tag-Icon aus (Label bleibt sichtbar). */
  hideImg(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
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

  protected readonly stats = computed<StatRow[]>(() => {
    const e = this.entry();
    if (!e) {
      return [];
    }
    const num = (k: string) => (typeof e[k] === 'number' ? (e[k] as number) : null);
    const rows: StatRow[] = [];
    const push = (glyph: string, label: string, v: number | null, suffix = '') => {
      if (v !== null && v !== 0) {
        rows.push({ glyph, label, value: this.fmt(v) + suffix });
      }
    };
    if (this.kind() === 'ship' || this.kind() === 'defense') {
      push('⚔️', 'Angriff', num('attack'));
      push('🛡️', 'Schild', num('shield'));
    }
    if (this.kind() === 'ship') {
      push('📦', 'Frachtraum', num('cargo'));
      push('🚀', 'Speed', num('speed'));
      push('⛽', 'Treibstoff', num('fuel'));
    }
    return rows;
  });

  protected readonly rapidfire = computed<RapidFireRow[]>(() => {
    const rf = this.entry()?.['rapidfire'];
    if (!rf || typeof rf !== 'object') {
      return [];
    }
    const targetMeta = { ...SHIP_META, ...DEFENSE_META };
    return Object.entries(rf as Record<string, number>)
      .map(([target, mult]) => {
        const m = metaFor(targetMeta, target);
        return { glyph: m.glyph, label: m.label, mult };
      })
      .sort((a, b) => b.mult - a.mult);
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
  protected readonly unlocks = computed<{ type: string; label: string; glyph: string; reqLevel: number; kind: string }[]>(() => {
    const b = this.balance.value;
    if (!b) {
      return [];
    }
    const t = this.type();
    const out: { type: string; label: string; glyph: string; reqLevel: number; kind: string }[] = [];
    const seen = new Set<string>();
    const scan = (
      map: Record<string, Record<string, unknown>> | undefined,
      metaMap: Record<string, { label: string; glyph: string }>,
      kind: string,
    ) => {
      for (const [key, entry] of Object.entries(map ?? {})) {
        if (key === t || seen.has(key)) {
          continue;
        }
        const req = entry?.['requires'];
        if (req && typeof req === 'object' && (req as Record<string, unknown>)[t] != null) {
          const m = metaFor(metaMap, key);
          const reqLevel = Number((req as Record<string, unknown>)[t]) || 1;
          out.push({ type: key, label: m.label, glyph: m.glyph, reqLevel, kind });
          seen.add(key);
        }
      }
    };
    scan(b.research?.techs as Record<string, Record<string, unknown>>, TECH_META, 'Forschung');
    scan(b.ships as Record<string, Record<string, unknown>>, SHIP_META, 'Schiff');
    scan(b.defenses as Record<string, Record<string, unknown>>, DEFENSE_META, 'Verteidigung');
    scan(b.buildings as Record<string, Record<string, unknown>>, BUILDING_META, 'Gebäude');
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
