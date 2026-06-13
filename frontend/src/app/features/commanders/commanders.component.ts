import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CommanderBonus } from '../../core/models/api.models';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { BalanceService } from '../../core/services/balance.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  RANK_META,
  SPECIALIZATION_META,
  TRAIT_META,
  commanderFace,
  gradeBadgeClass,
  gradeLabel,
  metaFor,
} from '../../core/models/display';
import { rankIcon, specIcon, traitIcon } from '../../core/models/icon-assets';
import { commanderStyles } from './commander.styles';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';

/** Eine waehlbare Investitions-Stufe (aus balance.json abgeleitet). */
interface TierOption {
  key: string;
  label: string;
  cost: { metal: number; crystal: number; deuterium: number };
  hint: string;
}

/** Ausschnitt der `commander.grades`-Sektion aus balance.json (nur Anzeige). */
interface GradesConfig {
  order: string[];
  training_base_cost: { metal: number; crystal: number; deuterium: number };
  training_tiers: { key: string; label: string; cost_mult: number; weights: Record<string, number> }[];
}

@Component({
  selector: 'app-commanders',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, FormsModule, BtnIconComponent, EmptyStateComponent],
  template: `
    <div class="head">
      <div>
        <h1>Kommandozentrale</h1>
        <p class="muted sub">Deine Crew ist das Herz des Imperiums. Fuehre sie gut.</p>
      </div>
      <button
        class="btn btn-primary"
        type="button"
        [disabled]="!canTrain()"
        (click)="toggleTrain()"
      >
        <app-btn-icon [src]="rankIcon('cadet')" glyph="🎖️" /> {{ showTrain() ? 'Abbrechen' : 'Kadett ausbilden' }}
      </button>
    </div>

    @if (showTrain()) {
      <div class="card train-panel">
        <div class="panel-title">🎓 Neuen Commander ausbilden</div>
        <p class="faint small">Waehle Ausrichtung und Schiffs-Fokus — so formst du gezielt
          Offensiv-, Defensiv- oder Tempo-Commander. (Traits kommen zufaellig dazu.)</p>

        <div class="train-grid">
          <label class="field">
            <span>Spezialisierung</span>
            <select [ngModel]="selSpec()" (ngModelChange)="onSpecChange($event)">
              @for (s of specOptions; track s) {
                <option [value]="s">{{ spec(s).glyph }} {{ spec(s).label }}</option>
              }
            </select>
          </label>

          <label class="field">
            <span>Fokus-Schiffsklasse</span>
            <select [ngModel]="selFocus()" (ngModelChange)="onFocusChange($event)">
              <option value="">✨ automatisch (typisch)</option>
              @for (c of focusOptions; track c) {
                <option [value]="c">{{ classLabel(c) }}</option>
              }
            </select>
          </label>
        </div>

        @if (tierOptions().length) {
          <div class="tier-block">
            <span class="bonus-head faint small">Investitions-Stufe (bestimmt Grad-Chancen)</span>
            <div class="tier-row">
              @for (t of tierOptions(); track t.key) {
                <button
                  type="button"
                  class="tier-card"
                  [class.active]="selTier() === t.key"
                  (click)="onTierChange(t.key)"
                >
                  <span class="tier-name">{{ t.label }}</span>
                  <span class="tier-cost mono">
                    ⛏️ {{ t.cost.metal }} · 💎 {{ t.cost.crystal }} · 🛢️ {{ t.cost.deuterium }}
                  </span>
                  <span class="tier-hint faint">{{ t.hint }}</span>
                </button>
              }
            </div>
            <p class="faint small">Hoehere Stufe = bessere Grad-Chancen. SSS bleibt selten
              (max 5%, nur Experimentell) — ein echtes Prestige-Ereignis.</p>
          </div>
        }

        <div class="preview">
          <span class="bonus-head faint small">Erwartetes Profil (Kadett, ohne Traits)</span>
          <div class="bonus-chips">
            @for (b of preview(); track b.stat + b.target) {
              <span class="chip bonus tip" [class.neg]="b.pct < 0" [attr.data-tip]="bonusTip(b)">
                {{ statGlyph(b.stat) }} {{ signedPct(b.pct) }} {{ targetLabel(b.target) }}
              </span>
            } @empty {
              <span class="faint small">—</span>
            }
          </div>
        </div>

        <button class="btn btn-primary" type="button" [disabled]="training()" (click)="train()">
          {{ training() ? 'Bildet aus…' : '🎖️ Ausbildung starten' }}
        </button>
      </div>
    }

    @if (span(); as s) {
      <div class="card span-card">
        <div class="span-head">
          <span class="panel-title" style="margin:0">📡 Span of Control</span>
          <span class="mono span-big" [class.over]="s.in_use > s.total">{{ s.in_use }} / {{ s.total }}</span>
        </div>
        <div class="bar" [class.full]="s.in_use >= s.total">
          <span class="fill" [style.width.%]="spanPct(s.in_use, s.total)"></span>
        </div>
        <div class="span-detail faint small">
          Basis {{ s.base }} · Kommandozentrale +{{ s.from_command_center }} · Doktrin +{{ s.from_doctrine }}
        </div>
      </div>
    }

    @if (commanders().length) {
      <div class="grid roster">
        @for (c of commanders(); track c.id) {
          <a class="card cmd-card" [routerLink]="['/commanders', c.id]">
            <div class="portrait" [class]="bandClass(c.morale)">
              <img [src]="faceFor(c.id)" alt="" (error)="onFaceError($event)" />
              <span class="grade-badge" [class]="gradeClass(c.grade)" [attr.data-tip]="'Gueteklasse ' + gradeText(c.grade)">{{ gradeText(c.grade) }}</span>
              <span class="rank-badge"><img class="chip-ico" [src]="rankIcon(c.rank)" alt="" (error)="hideImg($event)" />{{ rank(c.rank).label }}</span>
              @if (c.training_finishes_at) {
                <span class="status-tag">in Ausbildung</span>
              } @else if (c.assigned_fleet_id) {
                <span class="status-tag">im Einsatz</span>
              }
            </div>

            <div class="cmd-body">
              <div class="row-between">
                <h3>{{ c.name }}</h3>
                <span class="chip"><img class="chip-ico" [src]="specIcon(c.specialization)" alt="" (error)="hideImg($event)" />{{ spec(c.specialization).label }}</span>
              </div>

              <div class="morale">
                <div class="row-between small">
                  <span class="muted">Moral</span>
                  <span class="mono" [class]="bandClass(c.morale)">{{ c.morale }} · {{ c.morale_band.label }}</span>
                </div>
                <div class="bar morale-bar" [class]="bandClass(c.morale)">
                  <span class="fill" [style.width.%]="c.morale"></span>
                </div>
              </div>
              @if (c.loyalty < 30 || (c.unrest ?? 0) >= 80) {
                <div class="risk small">
                  @if (c.loyalty < 30) { <span class="chip warn">⚠ Treue {{ c.loyalty }} — Meuterei/Überlauf-Risiko</span> }
                  @if ((c.unrest ?? 0) >= 80) { <span class="chip warn">⚑ Forderung steht bevor</span> }
                </div>
              }

              <div class="traits">
                @for (t of c.traits; track t) {
                  <span class="chip trait"><img class="chip-ico" [src]="traitIcon(t)" alt="" (error)="hideImg($event)" />{{ trait(t).label }}</span>
                }
              </div>

              @if (c.bonuses.length) {
                <div class="bonuses">
                  <span class="bonus-head faint small">Boni (bei voller Moral){{ c.focus ? ' · Fokus: ' + classLabel(c.focus) : '' }}</span>
                  <div class="bonus-chips">
                    @for (b of c.bonuses; track b.stat + b.target) {
                      <span class="chip bonus tip" [class.neg]="b.pct < 0" [attr.data-tip]="bonusTip(b)">
                        {{ statGlyph(b.stat) }} {{ signedPct(b.pct) }} {{ targetLabel(b.target) }}
                      </span>
                    }
                  </div>
                </div>
              }

              <div class="cmd-foot faint small">
                <span class="tip" [attr.data-tip]="c.persona.background">XP {{ c.xp }}</span>
                <span>· Loyalitaet {{ c.loyalty }}</span>
                <span>· Span {{ c.span_capacity }}</span>
              </div>
            </div>
          </a>
        }
      </div>
    } @else {
      <app-empty-state art="empty_commanders">
        Noch keine Commander. Baue eine Kommando-Akademie und bilde deinen ersten Offizier aus.
      </app-empty-state>
    }
  `,
  styles: [commanderStyles],
})
export class CommandersComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly balance = inject(BalanceService);
  private readonly notify = inject(NotificationService);

  protected readonly commanders = this.state.commanders;
  protected readonly span = this.state.span;
  protected readonly training = signal(false);

  // Ausbildungs-Auswahl.
  protected readonly showTrain = signal(false);
  protected readonly selSpec = signal('combat');
  protected readonly selFocus = signal(''); // '' = automatisch
  protected readonly selTier = signal('standard');
  protected readonly preview = signal<CommanderBonus[]>([]);
  protected readonly specOptions = ['combat', 'logistics', 'spy', 'research', 'trade', 'admin'];
  protected readonly focusOptions = ['fighter', 'cruiser', 'capital', 'civil'];

  // Investitions-Stufen aus balance.json (Kosten + Grad-Chance-Andeutung).
  protected readonly tierOptions = computed<TierOption[]>(() => {
    const grades = (this.balance.value?.commander as Record<string, unknown> | undefined)?.[
      'grades'
    ] as GradesConfig | undefined;
    if (!grades) {
      return [];
    }
    const base = grades.training_base_cost;
    const order = grades.order;
    return grades.training_tiers.map((t) => {
      const mult = Number(t.cost_mult ?? 1);
      const weights = t.weights ?? {};
      const total = order.reduce((s, k) => s + (Number(weights[k]) || 0), 0);
      let best = 'C';
      for (const k of order) {
        if ((Number(weights[k]) || 0) > 0) {
          best = k;
        }
      }
      const sss = total > 0 ? Math.round(((Number(weights['SSS']) || 0) / total) * 100) : 0;
      const hint = sss > 0 ? `bis ${best} · SSS bis ${sss}%` : `bis ${best}`;
      return {
        key: t.key,
        label: t.label,
        cost: {
          metal: Math.round(base.metal * mult),
          crystal: Math.round(base.crystal * mult),
          deuterium: Math.round(base.deuterium * mult),
        },
        hint,
      };
    });
  });

  protected readonly canTrain = computed(() => !!this.state.activePlanetId());

  constructor() {
    void this.state.reloadCommanders();
  }

  toggleTrain(): void {
    this.showTrain.update((v) => !v);
    if (this.showTrain()) {
      this.loadPreview();
    }
  }

  onSpecChange(spec: string): void {
    this.selSpec.set(spec);
    this.loadPreview();
  }

  onFocusChange(focus: string): void {
    this.selFocus.set(focus);
    this.loadPreview();
  }

  onTierChange(tier: string): void {
    this.selTier.set(tier);
  }

  private loadPreview(): void {
    this.api.getBonusPreview(this.selSpec(), this.selFocus() || null).subscribe({
      next: (b) => this.preview.set(b),
      error: () => this.preview.set([]),
    });
  }

  train(): void {
    const planetId = this.state.activePlanetId();
    if (!planetId) {
      return;
    }
    this.training.set(true);
    this.api.trainCommander(planetId, this.selSpec(), this.selFocus() || null, this.selTier()).subscribe({
      next: () => {
        this.training.set(false);
        this.showTrain.set(false);
        this.notify.success(
          'Ausbildung gestartet',
          `${this.spec(this.selSpec()).label}-Commander tritt der Akademie bei.`,
        );
        void this.state.reloadCommanders();
      },
      error: (err) => {
        this.training.set(false);
        this.notify.warning('Ausbildung nicht moeglich', err?.error?.detail ?? 'Kommando-Akademie noetig.');
      },
    });
  }

  spanPct(used: number, total: number): number {
    return total > 0 ? Math.min(100, (used / total) * 100) : 0;
  }

  rank = (r: string) => metaFor(RANK_META, r);
  spec = (s: string) => metaFor(SPECIALIZATION_META, s);
  trait = (t: string) => metaFor(TRAIT_META, t);
  protected readonly rankIcon = rankIcon;
  protected readonly specIcon = specIcon;
  protected readonly traitIcon = traitIcon;
  /** Blendet ein nicht ladbares Inline-Icon aus (Label bleibt sichtbar). */
  hideImg(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
  bandClass = (m: number) => this.balance.moraleBandClass(m);
  gradeClass = (g?: string | null) => gradeBadgeClass(g);
  gradeText = (g?: string | null) => gradeLabel(g);

  faceFor = (id: string) => commanderFace(id);
  onFaceError(event: Event): void {
    (event.target as HTMLImageElement).src = 'assets/img/commanders/silhouette_unknown.png';
  }

  // -- Boni-Darstellung ---------------------------------------------------
  private static readonly STAT_GLYPH: Record<string, string> = {
    attack: '⚔', shield: '🛡', speed: '💨',
  };
  private static readonly STAT_LABEL: Record<string, string> = {
    attack: 'Angriff', shield: 'Schild', speed: 'Tempo',
  };
  private static readonly CLASS_LABEL: Record<string, string> = {
    all: 'alle Schiffe', fighter: 'Jaeger', cruiser: 'Kreuzer',
    capital: 'Grosskampfschiffe', civil: 'zivile Schiffe',
  };

  statGlyph = (s: string) => CommandersComponent.STAT_GLYPH[s] ?? '•';
  classLabel = (t: string) => CommandersComponent.CLASS_LABEL[t] ?? t;
  targetLabel = (t: string) => (t === 'all' ? '' : '· ' + this.classLabel(t));
  signedPct = (p: number) => (p > 0 ? '+' : '') + Math.round(p * 100) + '%';

  bonusTip(b: { stat: string; target: string; pct: number }): string {
    const stat = CommandersComponent.STAT_LABEL[b.stat] ?? b.stat;
    const tgt = b.target === 'all' ? 'alle Schiffe' : this.classLabel(b.target);
    return `${this.signedPct(b.pct)} ${stat} auf ${tgt}\n(passiver Basiswert — wächst mit Rang/Güteklasse, im Kampf mit Moral skaliert; nicht über Skillpunkte)`;
  }
}
