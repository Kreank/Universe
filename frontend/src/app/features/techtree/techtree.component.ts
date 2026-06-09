import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import {
  Requirement,
  ResearchOption,
  ResearchResponse,
  ResearchState,
} from '../../core/models/api.models';
import { TECH_META, metaFor } from '../../core/models/display';
import { IconTileComponent } from '../../shared/components/icon-tile.component';

/** Labor-(Gebaeude-)Voraussetzung, als Chip in der Kachel. */
interface LabReq {
  level: number;
  met: boolean;
}

/** Eine positionierte Tech-Kachel im Graphen. */
interface PNode {
  type: string;
  label: string;
  glyph: string;
  blurb: string;
  level: number;
  tier: number;
  x: number;
  y: number;
  labReq: LabReq | null;
}

/** Eine gezeichnete Abhaengigkeits-Kante (Tech -> Tech). */
interface Edge {
  id: string;
  from: string;
  to: string;
  d: string;
  met: boolean;
}

/** Spaltentitel (eine Tiefe = eine Spalte). */
interface TierTitle {
  x: number;
  title: string;
}

/** Vollstaendiges Graph-Layout fuer das Template. */
interface Graph {
  nodes: PNode[];
  edges: Edge[];
  tierTitles: TierTitle[];
  adj: Map<string, Set<string>>;
  width: number;
  height: number;
}

/**
 * Tech-Tree-Ansicht: visualisiert den Forschungs-Abhaengigkeitsbaum aus
 * `balance.research.techs` als echten Graphen mit gezeichneten Linien.
 *
 * - Spalten = Tiefe (laengster Pfad ueber Tech->Tech-Kanten).
 * - Linien = Tech->Tech-Abhaengigkeiten (Gebaeude-Reqs bleiben als Chip).
 * - Linienfarbe = erfuellt (eigene Stufe >= verlangte Stufe) vs. offen.
 * - Hover hebt die mit einer Tech verbundenen Kanten/Kacheln hervor.
 */
@Component({
  selector: 'app-techtree',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconTileComponent],
  template: `
    <h1>🌳 Techbaum</h1>
    <p class="muted sub">
      Abhaengigkeitsgraph der Forschung. Linien zeigen, was welche Technologie voraussetzt —
      <span class="legend met">erfuellt</span> /
      <span class="legend open">offen</span>. Fahre ueber eine Kachel, um ihre Abhaengigkeiten
      hervorzuheben; Klick oeffnet die Forschung.
    </p>

    @if (loading()) {
      <p class="empty-state">Lade Techbaum…</p>
    } @else if (graph().nodes.length === 0) {
      <p class="empty-state">Keine Technologien gefunden.</p>
    } @else {
      <div class="canvas-scroll">
        <div
          class="canvas"
          [style.width.px]="graph().width"
          [style.height.px]="graph().height"
        >
          @for (tt of graph().tierTitles; track tt.x) {
            <div class="tier-title" [style.left.px]="tt.x" [style.width.px]="NODE_W">
              {{ tt.title }}
            </div>
          }

          <svg
            class="edges"
            [attr.width]="graph().width"
            [attr.height]="graph().height"
            [attr.viewBox]="'0 0 ' + graph().width + ' ' + graph().height"
          >
            @for (e of graph().edges; track e.id) {
              <path
                [attr.d]="e.d"
                class="edge"
                [class.met]="e.met"
                [class.active]="isEdgeActive(e)"
                [class.dim]="hovered() && !isEdgeActive(e)"
              />
            }
          </svg>

          @for (n of graph().nodes; track n.type) {
            <button
              class="card node"
              type="button"
              [style.left.px]="n.x"
              [style.top.px]="n.y"
              [style.width.px]="NODE_W"
              [style.height.px]="NODE_H"
              [class.researched]="n.level > 0"
              [class.dim]="hovered() && !isNodeActive(n.type)"
              [class.focus]="hovered() === n.type"
              (mouseenter)="hovered.set(n.type)"
              (mouseleave)="hovered.set(null)"
              (focus)="hovered.set(n.type)"
              (blur)="hovered.set(null)"
              (click)="open(n.type)"
              [attr.title]="n.blurb"
            >
              <div class="node-head">
                <app-icon-tile [glyph]="n.glyph" [size]="40" variant="muted" />
                <div class="node-id">
                  <span class="node-name">{{ n.label }}</span>
                  <span class="chip lvl" [class.zero]="n.level === 0">Stufe {{ n.level }}</span>
                </div>
              </div>

              @if (n.labReq) {
                <span class="chip lab" [class.ok]="n.labReq.met" [class.warn]="!n.labReq.met">
                  🏛 Labor {{ n.labReq.level }}
                </span>
              } @else {
                <span class="chip base">Basis-Tech</span>
              }
            </button>
          }
        </div>
      </div>
    }
  `,
  styles: [
    `
      .sub { margin-top: -0.3rem; font-size: 0.85rem; max-width: 62ch; }
      .legend { font-weight: 600; }
      .legend.met { color: var(--accent); }
      .legend.open { color: var(--text-dim); }

      .canvas-scroll {
        overflow: auto;
        padding-bottom: 1rem;
        /* dezentes Raster im Hintergrund fuer "Tech-Konsolen"-Look */
        background-image: radial-gradient(rgba(120, 150, 200, 0.07) 1px, transparent 1px);
        background-size: 28px 28px;
        border-radius: 12px;
      }
      .canvas { position: relative; }

      .tier-title {
        position: absolute;
        top: 0;
        font-size: 0.74rem;
        text-transform: uppercase;
        letter-spacing: 0.07em;
        color: #b9c6de;
        text-align: center;
        padding-bottom: 0.3rem;
        border-bottom: 1px solid var(--border);
        white-space: nowrap;
      }

      .edges {
        position: absolute;
        top: 0;
        left: 0;
        pointer-events: none;
        overflow: visible;
      }
      .edge {
        fill: none;
        stroke: var(--border-strong);
        stroke-width: 2;
        opacity: 0.5;
        transition: opacity 0.15s, stroke 0.15s, stroke-width 0.15s;
      }
      .edge.met { stroke: var(--accent); opacity: 0.6; }
      .edge.active {
        stroke: var(--accent);
        stroke-width: 3;
        opacity: 1;
        filter: drop-shadow(0 0 5px rgba(46, 230, 214, 0.7));
      }
      .edge.dim { opacity: 0.1; }

      .node {
        position: absolute;
        display: flex;
        flex-direction: column;
        justify-content: space-between;
        gap: 0.4rem;
        padding: 0.6rem 0.65rem;
        text-align: left;
        cursor: pointer;
        background: var(--surface);
        box-sizing: border-box;
        z-index: 2;
        transition: border-color 0.15s, box-shadow 0.15s, opacity 0.15s, transform 0.15s;
      }
      .node:hover,
      .node.focus { border-color: var(--border-strong); box-shadow: var(--glow); transform: translateY(-1px); }
      .node.researched { border-color: var(--accent); }
      .node.dim { opacity: 0.28; }

      .node-head { display: flex; align-items: center; gap: 0.5rem; min-width: 0; }
      .node-id { display: flex; flex-direction: column; gap: 0.2rem; min-width: 0; }
      .node-name {
        font-weight: 600;
        font-size: 0.88rem;
        line-height: 1.1;
        overflow: hidden;
        text-overflow: ellipsis;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
      }
      .chip.lvl { align-self: flex-start; background: var(--accent); color: #04121a; font-weight: 700; }
      .chip.lvl.zero {
        background: var(--surface-2);
        color: var(--text-dim);
        border: 1px solid var(--border);
      }
      .chip.lab { align-self: flex-start; font-size: 0.72rem; }
      .chip.lab.ok { color: var(--ok, #2ee6d6); border-color: rgba(46, 230, 214, 0.4); }
      .chip.lab.warn { color: var(--warn); border-color: rgba(255, 170, 60, 0.4); }
      .chip.base {
        align-self: flex-start;
        font-size: 0.72rem;
        color: var(--text-dim);
        border: 1px dashed var(--border);
      }
    `,
  ],
})
export class TechtreeComponent {
  private readonly api = inject(ApiService);
  private readonly balanceService = inject(BalanceService);
  private readonly router = inject(Router);

  /** Kachel-Maße — fix, damit die Linien-Endpunkte exakt sitzen. */
  protected readonly NODE_W = 200;
  protected readonly NODE_H = 104;
  private readonly COL_GAP = 84;
  private readonly ROW_GAP = 22;
  private readonly TOP = 30;

  protected readonly loading = signal(true);
  protected readonly hovered = signal<string | null>(null);
  private readonly research = signal<ResearchResponse | null>(null);
  /** Roh-Tech-Definitionen aus balance.json (key -> { requires, ... }). */
  private readonly techDefs = signal<Record<string, { requires?: Record<string, number> }>>({});

  protected readonly graph = computed<Graph>(() => {
    const defs = this.techDefs();
    const keys = Object.keys(defs);
    const empty: Graph = {
      nodes: [],
      edges: [],
      tierTitles: [],
      adj: new Map(),
      width: 0,
      height: 0,
    };
    if (keys.length === 0) {
      return empty;
    }

    const res = this.research();
    const levelByType = new Map<string, number>(
      (res?.research ?? []).map((r: ResearchState) => [r.type, r.level]),
    );
    const optByType = new Map<string, ResearchOption>(
      (res?.available ?? []).map((o) => [o.type, o]),
    );

    const techKeys = new Set(keys);
    const tierOf = this.computeTiers(defs, techKeys);

    // Techs nach Tier (Spalte) gruppieren.
    const byTier = new Map<number, string[]>();
    for (const k of keys) {
      const t = tierOf.get(k) ?? 0;
      const arr = byTier.get(t) ?? [];
      arr.push(k);
      byTier.set(t, arr);
    }
    const tierList = [...byTier.keys()].sort((a, b) => a - b);
    const colIndex = new Map<number, number>(tierList.map((t, i) => [t, i]));

    // Zeilen-Reihenfolge: Tier 0 alphabetisch, danach Barycenter der
    // Tech-Vorgaenger (reduziert Linien-Ueberkreuzungen).
    const rowOf = new Map<string, number>();
    const labelOf = (k: string) => metaFor(TECH_META, k).label;
    const bary = (k: string): number => {
      const reqs = defs[k]?.requires ?? {};
      const rows = Object.keys(reqs)
        .filter((d) => techKeys.has(d))
        .map((d) => rowOf.get(d) ?? 0);
      return rows.length ? rows.reduce((s, v) => s + v, 0) / rows.length : 0;
    };
    for (const t of tierList) {
      const arr = byTier.get(t) ?? [];
      if (t === tierList[0]) {
        arr.sort((a, b) => labelOf(a).localeCompare(labelOf(b)));
      } else {
        arr.sort((a, b) => bary(a) - bary(b) || labelOf(a).localeCompare(labelOf(b)));
      }
      arr.forEach((k, i) => rowOf.set(k, i));
    }

    const xOf = (t: number) => (colIndex.get(t) ?? 0) * (this.NODE_W + this.COL_GAP);
    const yOf = (row: number) => this.TOP + row * (this.NODE_H + this.ROW_GAP);

    // Kacheln aufbauen.
    const nodes: PNode[] = keys.map((type) => {
      const meta = metaFor(TECH_META, type);
      const t = tierOf.get(type) ?? 0;
      const level = levelByType.get(type) ?? 0;
      const reqLab = (defs[type]?.requires ?? {})['research_lab'];
      let labReq: LabReq | null = null;
      if (reqLab) {
        const fromOpt = optByType
          .get(type)
          ?.requirements?.find((r: Requirement) => r.type === 'research_lab');
        labReq = { level: reqLab, met: level > 0 ? true : (fromOpt?.met ?? false) };
      }
      return {
        type,
        label: meta.label,
        glyph: meta.glyph,
        blurb: meta.blurb ?? '',
        level,
        tier: t,
        x: xOf(t),
        y: yOf(rowOf.get(type) ?? 0),
        labReq,
      };
    });

    // Kanten: je Tech-Voraussetzung eine Bezierkurve (Vorgaenger rechts -> Tech links).
    const edges: Edge[] = [];
    const adj = new Map<string, Set<string>>();
    const link = (a: string, b: string) => {
      (adj.get(a) ?? adj.set(a, new Set()).get(a)!).add(b);
      (adj.get(b) ?? adj.set(b, new Set()).get(b)!).add(a);
    };
    for (const type of keys) {
      const reqs = defs[type]?.requires ?? {};
      for (const dep of Object.keys(reqs)) {
        if (!techKeys.has(dep)) {
          continue;
        }
        const x1 = xOf(tierOf.get(dep) ?? 0) + this.NODE_W;
        const y1 = yOf(rowOf.get(dep) ?? 0) + this.NODE_H / 2;
        const x2 = xOf(tierOf.get(type) ?? 0);
        const y2 = yOf(rowOf.get(type) ?? 0) + this.NODE_H / 2;
        const dx = Math.max(30, (x2 - x1) / 2);
        const d = `M ${x1} ${y1} C ${x1 + dx} ${y1}, ${x2 - dx} ${y2}, ${x2} ${y2}`;
        const met = (levelByType.get(dep) ?? 0) >= reqs[dep];
        edges.push({ id: `${dep}->${type}`, from: dep, to: type, d, met });
        link(dep, type);
      }
    }

    const maxRow = Math.max(0, ...keys.map((k) => rowOf.get(k) ?? 0));
    const width = colIndex.size * (this.NODE_W + this.COL_GAP) - this.COL_GAP;
    const height = this.TOP + (maxRow + 1) * (this.NODE_H + this.ROW_GAP);
    const tierTitles: TierTitle[] = tierList.map((t) => ({ x: xOf(t), title: `Stufe ${t}` }));

    return { nodes, edges, tierTitles, adj, width, height };
  });

  constructor() {
    void this.init();
  }

  private async init(): Promise<void> {
    this.loading.set(true);
    try {
      await this.balanceService.load();
      const techs = this.balanceService.value?.research?.techs ?? {};
      this.techDefs.set(techs as Record<string, { requires?: Record<string, number> }>);
      this.api.getResearch().subscribe({
        next: (res) => {
          this.research.set(res);
          this.loading.set(false);
        },
        error: () => this.loading.set(false),
      });
    } catch {
      this.loading.set(false);
    }
  }

  /** Kante gehoert zur aktuell ueberfahrenen Tech? */
  protected isEdgeActive(e: Edge): boolean {
    const h = this.hovered();
    return h !== null && (e.from === h || e.to === h);
  }

  /** Kachel ist die ueberfahrene Tech oder direkt mit ihr verbunden? */
  protected isNodeActive(type: string): boolean {
    const h = this.hovered();
    if (h === null) {
      return true;
    }
    return type === h || (this.graph().adj.get(h)?.has(type) ?? false);
  }

  /**
   * Berechnet je Tech die Tiefe = laengster Pfad ueber Tech->Tech-Kanten.
   * Gebaeude-Voraussetzungen (z. B. research_lab) zaehlen NICHT zur Tiefe.
   */
  private computeTiers(
    defs: Record<string, { requires?: Record<string, number> }>,
    techKeys: Set<string>,
  ): Map<string, number> {
    const memo = new Map<string, number>();
    const visiting = new Set<string>();
    const depth = (key: string): number => {
      if (memo.has(key)) {
        return memo.get(key) as number;
      }
      if (visiting.has(key)) {
        return 0; // Zyklus-Schutz
      }
      visiting.add(key);
      const requires = defs[key]?.requires ?? {};
      let d = 0;
      for (const dep of Object.keys(requires)) {
        if (techKeys.has(dep)) {
          d = Math.max(d, depth(dep) + 1);
        }
      }
      visiting.delete(key);
      memo.set(key, d);
      return d;
    };
    for (const k of techKeys) {
      depth(k);
    }
    return memo;
  }

  open(_type: string): void {
    void this.router.navigate(['/research']);
  }
}
