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
import { BUILDING_META, TECH_META, metaFor } from '../../core/models/display';
import { IconTileComponent } from '../../shared/components/icon-tile.component';

/** Eine Voraussetzung mit Klarnamen + Erfuellungs-Status fuer die Anzeige. */
interface ReqView {
  type: string;
  label: string;
  level: number;
  met: boolean;
}

/** Eine Tech-Kachel im Baum. */
interface TechNode {
  type: string;
  label: string;
  glyph: string;
  blurb: string;
  level: number;
  tier: number;
  reqs: ReqView[];
}

/** Eine Tier-Spalte (gleiche Tiefe im Abhaengigkeitsbaum). */
interface Tier {
  tier: number;
  title: string;
  nodes: TechNode[];
}

/**
 * Tech-Tree-Ansicht: visualisiert den Forschungs-Abhaengigkeitsbaum aus
 * `balance.research.techs`. Je Tech wird eine Tiefe (longest path ueber
 * Tech->Tech-Kanten) berechnet und nach Tiers (Spalten) gruppiert. Aktuelle
 * Stufen kommen aus `getResearch()`. Klick auf eine Kachel fuehrt zu /research.
 */
@Component({
  selector: 'app-techtree',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconTileComponent],
  template: `
    <h1>🌳 Techbaum</h1>
    <p class="muted sub">
      Abhaengigkeitsbaum der Forschung. Spalten = Tiefe (Voraussetzungs-Stufe).
      Klick auf eine Technologie oeffnet die Forschung.
    </p>

    @if (loading()) {
      <p class="empty-state">Lade Techbaum…</p>
    } @else if (tiers().length === 0) {
      <p class="empty-state">Keine Technologien gefunden.</p>
    } @else {
      <div class="tree">
        @for (tier of tiers(); track tier.tier) {
          <section class="tier">
            <h2 class="tier-title">{{ tier.title }}</h2>
            <div class="tier-col">
              @for (n of tier.nodes; track n.type) {
                <button
                  class="card node"
                  type="button"
                  [class.researched]="n.level > 0"
                  (click)="open()"
                  [attr.title]="n.blurb"
                >
                  <div class="node-head">
                    <app-icon-tile [glyph]="n.glyph" [size]="46" variant="muted" />
                    <div class="node-id">
                      <span class="node-name">{{ n.label }}</span>
                      <span class="chip lvl" [class.zero]="n.level === 0">Stufe {{ n.level }}</span>
                    </div>
                  </div>

                  @if (n.reqs.length) {
                    <div class="reqs">
                      <span class="muted small">Voraussetzungen:</span>
                      @for (r of n.reqs; track r.type) {
                        <span class="chip req" [class.ok]="r.met" [class.warn]="!r.met">
                          {{ r.met ? '✓' : '✗' }} {{ r.label }} {{ r.level }}
                        </span>
                      }
                    </div>
                  } @else {
                    <span class="muted small">Keine Voraussetzung</span>
                  }
                </button>
              }
            </div>
          </section>
        }
      </div>
    }
  `,
  styles: [
    `
      .sub { margin-top: -0.3rem; font-size: 0.85rem; }
      /* Horizontal scrollbare Tier-Spalten (OGame-Techtree-Stil). */
      .tree {
        display: flex;
        gap: 1.1rem;
        align-items: flex-start;
        overflow-x: auto;
        padding-bottom: 1rem;
      }
      .tier { flex: 0 0 auto; min-width: 240px; }
      .tier-title {
        font-size: 0.82rem;
        text-transform: uppercase;
        letter-spacing: 0.06em;
        color: var(--accent);
        margin: 0 0 0.6rem;
        padding-bottom: 0.35rem;
        border-bottom: 1px solid var(--border);
        white-space: nowrap;
      }
      .tier-col { display: flex; flex-direction: column; gap: 0.7rem; }
      .node {
        display: flex;
        flex-direction: column;
        gap: 0.55rem;
        padding: 0.7rem;
        text-align: left;
        cursor: pointer;
        background: var(--surface);
        transition: border-color 0.15s, box-shadow 0.15s;
      }
      .node:hover { border-color: var(--border-strong); box-shadow: var(--glow); }
      .node.researched { border-color: var(--accent); }
      .node-head { display: flex; align-items: center; gap: 0.55rem; }
      .node-id { display: flex; flex-direction: column; gap: 0.25rem; min-width: 0; }
      .node-name { font-weight: 600; font-size: 0.92rem; }
      .chip.lvl { align-self: flex-start; background: var(--accent); color: #04121a; font-weight: 700; }
      .chip.lvl.zero {
        background: var(--surface-2);
        color: var(--text-dim);
        border: 1px solid var(--border);
      }
      .reqs { display: flex; flex-wrap: wrap; gap: 0.3rem; align-items: center; }
      .chip.req { font-size: 0.72rem; }
      .chip.req.ok { color: var(--ok, #2ee6d6); border-color: rgba(46, 230, 214, 0.4); }
      .chip.req.warn { color: var(--warn); border-color: rgba(255, 170, 60, 0.4); }
      .small { font-size: 0.76rem; }
    `,
  ],
})
export class TechtreeComponent {
  private readonly api = inject(ApiService);
  private readonly balanceService = inject(BalanceService);
  private readonly router = inject(Router);

  protected readonly loading = signal(true);
  private readonly research = signal<ResearchResponse | null>(null);
  /** Roh-Tech-Definitionen aus balance.json (key -> { requires, ... }). */
  private readonly techDefs = signal<Record<string, { requires?: Record<string, number> }>>({});

  protected readonly tiers = computed<Tier[]>(() => {
    const defs = this.techDefs();
    const keys = Object.keys(defs);
    if (keys.length === 0) {
      return [];
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

    const nodes: TechNode[] = keys.map((type) => {
      const meta = metaFor(TECH_META, type);
      return {
        type,
        label: meta.label,
        glyph: meta.glyph,
        blurb: meta.blurb ?? '',
        level: levelByType.get(type) ?? 0,
        tier: tierOf.get(type) ?? 0,
        reqs: this.buildReqs(type, defs[type]?.requires ?? {}, optByType.get(type), levelByType),
      };
    });

    const byTier = new Map<number, TechNode[]>();
    for (const n of nodes) {
      const arr = byTier.get(n.tier) ?? [];
      arr.push(n);
      byTier.set(n.tier, arr);
    }

    return [...byTier.keys()]
      .sort((a, b) => a - b)
      .map((tier) => ({
        tier,
        title: `Stufe ${tier}`,
        nodes: (byTier.get(tier) ?? []).sort((a, b) => a.label.localeCompare(b.label)),
      }));
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

  /**
   * Voraussetzungs-Ansicht: nutzt bevorzugt `requirements` aus `available`
   * (Server-autoritativ), sonst Vergleich balance `requires` gegen eigene Stufen.
   */
  private buildReqs(
    type: string,
    requires: Record<string, number>,
    option: ResearchOption | undefined,
    levelByType: Map<string, number>,
  ): ReqView[] {
    const labelMap = { ...BUILDING_META, ...TECH_META };
    if (option?.requirements?.length) {
      return option.requirements.map((r: Requirement) => ({
        type: r.type,
        label: metaFor(labelMap, r.type).label,
        level: r.level,
        met: r.met,
      }));
    }
    return Object.entries(requires).map(([dep, lvl]) => ({
      type: dep,
      label: metaFor(labelMap, dep).label,
      level: lvl,
      met: (levelByType.get(dep) ?? this.ownLevelFallback(dep)) >= lvl,
    }));
  }

  /** Gebaeude-Stufen sind hier nicht bekannt -> als unerfuellt behandeln (0). */
  private ownLevelFallback(_dep: string): number {
    return 0;
  }

  open(): void {
    void this.router.navigate(['/research']);
  }
}
