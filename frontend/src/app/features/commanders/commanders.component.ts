import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { CommanderBonus, EquipmentCatalog, EquipmentItem } from '../../core/models/api.models';
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
  gradeCanonical,
  gradeLabel,
  metaFor,
} from '../../core/models/display';
import { forkJoin } from 'rxjs';
import { equipmentItemIcon, navIcon, rankIcon, specIcon, statIcon, statusIcon, traitIcon } from '../../core/models/icon-assets';
import { commanderStyles } from './commander.styles';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { CostLineComponent } from '../../shared/components/cost-line.component';

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
  potency?: Record<string, number>;
  training_base_cost: { metal: number; crystal: number; deuterium: number };
  training_tiers: { key: string; label: string; cost_mult: number; weights: Record<string, number> }[];
}

/** Eine Bonus-Zeile der Vorschau als Spanne ueber die erreichbaren Gueten. */
interface RangeBonus {
  stat: string;
  target: string;
  pctLow: number;
  pctHigh: number;
}

@Component({
  selector: 'app-commanders',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, FormsModule, BtnIconComponent, EmptyStateComponent, CostLineComponent],
  template: `
    <div class="head">
      <div>
        <h1>Kommandozentrale</h1>
        <p class="muted sub">Deine Crew ist das Herz des Imperiums. Fuehre sie gut.</p>
      </div>
      <div class="head-actions">
        <button class="btn btn-ghost" type="button" (click)="toggleHelp()">
          ❓ {{ showHelp() ? 'Hilfe schließen' : 'Was sind Kommandeure?' }}
        </button>
        <button
          class="btn btn-primary"
          type="button"
          [disabled]="!canTrain()"
          (click)="toggleTrain()"
        >
          <app-btn-icon [src]="rankIcon('cadet')" glyph="🎖️" /> {{ showTrain() ? 'Abbrechen' : 'Kadett ausbilden' }}
        </button>
      </div>
    </div>

    @if (showHelp()) {
      <div class="card help-panel">
        <div class="panel-title">🧭 Was sind Kommandeure?</div>
        <div class="help-grid">
          <div class="help-block">
            <h4>Wozu?</h4>
            <p class="small">Kommandeure <strong>führen deine Flotten</strong> und geben dabei Kampfboni — aus
              Spezialisierung, Rang, Güteklasse und <strong>Ausrüstung</strong>. Statt einer Flotte können sie
              als <strong>Gouverneur</strong> einen Planeten verwalten und dessen Produktion steigern.</p>
          </div>
          <div class="help-block">
            <h4>Wie verbessern?</h4>
            <ul class="small">
              <li><strong>Rang</strong> steigt durch XP/Einsätze.</li>
              <li><strong>Skillpunkte</strong> → Fähigkeiten (beim Rang-Aufstieg).</li>
              <li><strong>Charakter-Zucht</strong> formt die Traits.</li>
              <li><strong>Ausrüstung &amp; Sets</strong> füllen 4 Slots mit Extra-Boni.</li>
              <li><strong>Bessere Güteklasse</strong> über das Ausbildungs-Programm.</li>
            </ul>
          </div>
          <div class="help-block">
            <h4>Güteklassen</h4>
            <p class="small"><strong>E &lt; D &lt; C &lt; B &lt; A &lt; S</strong> — E schwach, S Spitze.
              Höhere Klasse = stärkere Boni. Programme:</p>
            <ul class="small">
              <li>Standard → E/D</li>
              <li>Gehoben → D/C</li>
              <li>Elite → C/B/A</li>
              <li>Experimentell → A/S</li>
            </ul>
          </div>
          <div class="help-block">
            <h4>Neue bekommen?</h4>
            <p class="small">Kommandeure bildest du an der <strong>Kommando-Akademie</strong> aus.
              <strong>Ausrüstung</strong> bekommst du zusätzlich aus Quests, Expeditionen, globalen Events
              oder per <strong>Akademie-Fertigung</strong> (siehe Arsenal unten).</p>
          </div>
        </div>
      </div>
    }

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
                  <app-cost-line class="tier-cost" [cost]="t.cost" />
                  <span class="tier-hint faint">{{ t.hint }}</span>
                </button>
              }
            </div>
            <p class="faint small">Glatte Leiter E → D → C → B → A → S (E schwach, S Spitze).
              Höhere Stufe = bessere Grad-Chancen: Standard (E/D), Gehoben (D/C),
              Elite (C/B/A), Experimentell (A/S). Ein S-Kommandeur bleibt ein echtes Prestige-Ereignis.</p>
          </div>
        }

        <div class="preview">
          <span class="bonus-head faint small">Erwartetes Profil (Kadett, ohne Traits{{ previewGradeLabel() ? ' · ' + previewGradeLabel() : '' }})</span>
          <div class="bonus-chips">
            @for (b of preview(); track b.stat + b.target) {
              <span class="chip bonus tip" [class.neg]="b.pctHigh < 0" [attr.data-tip]="rangeTip(b)">
                <app-btn-icon [src]="statIcon(b.stat)" [glyph]="statGlyph(b.stat)" [size]="14" /> {{ rangeText(b) }} {{ targetLabel(b.target) }}
              </span>
            } @empty {
              <span class="faint small">—</span>
            }
          </div>
        </div>

        <button class="btn btn-primary" type="button" [disabled]="training()" (click)="train()">
          <app-btn-icon [src]="navIcon('command')" glyph="🎖️" [size]="18" /> {{ training() ? 'Bildet aus…' : 'Ausbildung starten' }}
        </button>
      </div>
    }

    @if (span(); as s) {
      <div class="card span-card">
        <div class="span-head">
          <span class="panel-title" style="margin:0"><app-btn-icon [src]="statusIcon('span_of_control')" glyph="📡" [size]="16" /> Span of Control</span>
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

    <div class="card arsenal">
      <div class="panel-title">🎽 Arsenal — Ausrüstung &amp; Akademie-Fertigung</div>
      @if (craftError(); as err) {
        <p class="faint small warn-text">{{ err }}</p>
      }

      @if (craftCost(); as cost) {
        <p class="faint small craft-cost">Akademie-Fertigung · Kosten je Teil: <app-cost-line [cost]="cost" /> · benötigt Kommando-Akademie Stufe {{ craftMin() }}.</p>
      }
      <div class="workshop">
        @for (set of craftSets(); track set.key) {
          <div class="ws-set">
            <div class="ws-set-head">{{ set.label }}</div>
            <div class="ws-grid">
              @for (it of set.items; track it.key) {
                <div class="ws-card">
                  <span class="ws-ico">
                    <img [src]="itemIcon(it.key)" alt="" (error)="onIcoError($event)" />
                    <span class="inv-glyph-fb">🎽</span>
                  </span>
                  <span class="ws-name">{{ it.label }}</span>
                  <span class="faint small">{{ slotLabel(it.slot) }}</span>
                  @if (it.bonusText) {
                    <span class="ws-bonus small">{{ it.bonusText }}</span>
                  }
                  <button class="btn btn-sm btn-primary ws-craft" type="button"
                    [disabled]="craftingKey() !== null || !canTrain()" (click)="craft(it.key)">
                    {{ craftingKey() === it.key ? 'Fertigt…' : 'Fertigen' }}
                  </button>
                </div>
              }
            </div>
          </div>
        }
      </div>

      <div class="bonus-head faint small inv-title">Inventar ({{ inventory().length }})</div>
      @if (inventory().length) {
        <ul class="inv-list">
          @for (it of inventory(); track it.id) {
            <li class="inv-item">
              <span class="inv-ico">
                <img [src]="itemIcon(it.item_key)" alt="" (error)="onIcoError($event)" />
                <span class="inv-glyph-fb">🎽</span>
              </span>
              <span class="inv-name">{{ it.label }}</span>
              <span class="rar-tag" [class]="'rar-' + it.rarity">{{ it.rarity_label }}</span>
              <span class="faint small">{{ slotLabel(it.slot) }}</span>
              @if (it.equipped_commander_id) {
                <span class="chip worn">getragen</span>
              } @else {
                <span class="faint small">frei</span>
              }
            </li>
          }
        </ul>
      } @else {
        <p class="faint small">Noch keine Ausrüstung. Fertige Teile an der Akademie oder finde sie in Quests, Expeditionen und Events.</p>
      }
    </div>

    @if (commanders().length) {
      <div class="grid roster">
        @for (c of commanders(); track c.id) {
          <a class="card cmd-card" [routerLink]="['/commanders', c.id]">
            <div class="portrait" [class]="bandClass(c.morale) + ' ' + gradeClass(c.grade)">
              <img [src]="faceFor(c.id)" alt="" (error)="onFaceError($event)" />
              <span class="grade-badge tip" [class]="gradeClass(c.grade)" [attr.data-tip]="gradeTip(c.grade)">{{ gradeText(c.grade) }}</span>
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
              @if (c.status === 'mutinous' || c.loyalty < 30 || (c.unrest ?? 0) >= 80) {
                <div class="risk small">
                  @if (c.status === 'mutinous') { <span class="chip warn mutiny"><app-btn-icon [src]="statusIcon('alert')" glyph="🔥" [size]="14" /> MEUTEREI — verweigert Befehle</span> }
                  @if (c.loyalty < 30) { <span class="chip warn"><app-btn-icon [src]="statusIcon('alert')" glyph="⚠" [size]="14" /> Treue {{ c.loyalty }} — Meuterei/Überlauf-Risiko</span> }
                  @if ((c.unrest ?? 0) >= 80) { <span class="chip warn"><app-btn-icon [src]="statusIcon('alert')" glyph="⚑" [size]="14" /> Forderung steht bevor</span> }
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
                        <app-btn-icon [src]="statIcon(b.stat)" [glyph]="statGlyph(b.stat)" [size]="14" /> {{ signedPct(b.pct) }} {{ targetLabel(b.target) }}
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

  // Hilfe-/Onboarding-Panel.
  protected readonly showHelp = signal(false);

  // Arsenal: Inventar + Akademie-Fertigung.
  protected readonly inventory = signal<EquipmentItem[]>([]);
  protected readonly equipCatalog = signal<EquipmentCatalog | null>(null);
  protected readonly craftingKey = signal<string | null>(null);
  protected readonly craftError = signal<string | null>(null);
  protected readonly itemIcon = equipmentItemIcon;

  private readonly STAT_LABELS: Record<string, string> = {
    attack: 'Angriff', shield: 'Schild', speed: 'Tempo', mining_yield: 'Erz-Ertrag',
    trade_margin: 'Handelsgewinn', spy_success: 'Spionage', expedition_yield: 'Expeditions-Ertrag',
    research_speed: 'Forschung', production: 'Produktion', shipbuild_speed: 'Schiffbau',
  };
  private readonly TARGET_LABELS: Record<string, string> = {
    fighter: 'Jäger', cruiser: 'Kreuzer', capital: 'Großkampf', civil: 'Zivil',
  };

  private bonusText(bonuses: { stat: string; target: string; pct: number }[] | undefined): string {
    return (bonuses ?? []).map((b) => {
      const t = b.target && b.target !== 'all' ? ` (${this.TARGET_LABELS[b.target] ?? b.target})` : '';
      return `+${Math.round(b.pct * 100)}% ${this.STAT_LABELS[b.stat] ?? b.stat}${t}`;
    }).join(', ');
  }

  /** Fertigbare Items, nach Set gruppiert (Werkstatt-Raster). */
  protected readonly craftSets = computed(() => {
    const cat = this.equipCatalog() as { items?: Record<string, { label: string; slot: string; set: string; bonuses?: { stat: string; target: string; pct: number }[] }>; sets?: Record<string, { label?: string }> } | null;
    if (!cat?.items || !cat?.sets) return [];
    const items = cat.items;
    const order = ['head', 'chest', 'hands', 'legs', 'shoes'];
    return Object.entries(cat.sets).map(([key, sdef]) => ({
      key,
      label: sdef.label ?? key,
      items: Object.entries(items)
        .filter(([, d]) => d.set === key)
        .map(([k, d]) => ({ key: k, label: d.label, slot: d.slot, bonusText: this.bonusText(d.bonuses) }))
        .sort((a, b) => order.indexOf(a.slot) - order.indexOf(b.slot)),
    }));
  });
  protected readonly craftCost = computed(() => this.equipCatalog()?.craft?.cost ?? null);
  protected readonly craftMin = computed(() => this.equipCatalog()?.craft?.academy_min ?? 2);

  slotLabel = (slot: string) => this.equipCatalog()?.slot_labels?.[slot] ?? slot;

  // Ausbildungs-Auswahl.
  protected readonly showTrain = signal(false);
  protected readonly selSpec = signal('combat');
  protected readonly selFocus = signal(''); // '' = automatisch
  protected readonly selTier = signal('standard');
  protected readonly preview = signal<RangeBonus[]>([]);
  protected readonly specOptions = ['combat', 'logistics', 'spy', 'research', 'trade', 'admin'];
  protected readonly focusOptions = ['fighter', 'cruiser', 'capital', 'civil'];

  /** `commander.grades`-Sektion aus balance.json (oder undefined, falls noch nicht geladen). */
  private gradesConfig(): GradesConfig | undefined {
    return (this.balance.value?.commander as Record<string, unknown> | undefined)?.[
      'grades'
    ] as GradesConfig | undefined;
  }

  /** In der gewaehlten Investitions-Stufe erreichbare Gueten (E..S, Gewicht > 0). */
  protected readonly reachableGrades = computed<string[]>(() => {
    const grades = this.gradesConfig();
    if (!grades) {
      return [];
    }
    const tier = grades.training_tiers.find((t) => t.key === this.selTier());
    const weights = tier?.weights ?? {};
    return grades.order.filter((k) => (Number(weights[k]) || 0) > 0);
  });

  /** Label fuer die Vorschau-Ueberschrift, z. B. "Güte E–D" oder "Güte C". */
  protected readonly previewGradeLabel = computed<string>(() => {
    const r = this.reachableGrades();
    if (!r.length) {
      return '';
    }
    const lo = gradeLabel(r[0]);
    const hi = gradeLabel(r[r.length - 1]);
    return lo === hi ? `Güte ${lo}` : `Güte ${lo}–${hi}`;
  });

  // Investitions-Stufen aus balance.json (Kosten + Grad-Chance-Andeutung).
  protected readonly tierOptions = computed<TierOption[]>(() => {
    const grades = this.gradesConfig();
    if (!grades) {
      return [];
    }
    const base = grades.training_base_cost;
    const order = grades.order;
    return grades.training_tiers.map((t) => {
      const mult = Number(t.cost_mult ?? 1);
      const weights = t.weights ?? {};
      // Niedrigste und hoechste erreichbare Gueteklasse dieser Stufe (E..S-Leiter).
      const reachable = order.filter((k) => (Number(weights[k]) || 0) > 0);
      const hint = reachable.length
        ? reachable.length > 1
          ? `${reachable[0]}–${reachable[reachable.length - 1]}`
          : reachable[0]
        : '—';
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
    this.api.getEquipmentCatalog().subscribe((c) => this.equipCatalog.set(c));
    this.loadInventory();
  }

  toggleHelp(): void {
    this.showHelp.update((v) => !v);
  }

  private loadInventory(): void {
    this.api.getInventory().subscribe({
      next: (inv) => this.inventory.set(inv),
      error: () => this.inventory.set([]),
    });
  }

  craft(key: string): void {
    const planetId = this.state.activePlanetId();
    if (!planetId || !key || this.craftingKey() !== null) {
      return;
    }
    this.craftingKey.set(key);
    this.craftError.set(null);
    this.api.craftItem(planetId, key).subscribe({
      next: (item) => {
        this.craftingKey.set(null);
        this.notify.success('Gefertigt', `${item.label} (${item.rarity_label}) liegt im Arsenal.`);
        this.loadInventory();
      },
      error: (err) => {
        this.craftingKey.set(null);
        this.craftError.set(err?.error?.detail ?? 'Fertigung fehlgeschlagen.');
      },
    });
  }

  /** Item-Icon nicht ladbar -> Glyph-Fallback (Geschwister-Span) einblenden. */
  onIcoError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.style.display = 'none';
    const fb = img.nextElementSibling as HTMLElement | null;
    if (fb) {
      fb.style.display = 'inline';
    }
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
    this.loadPreview();
  }

  /**
   * Vorschau als Spanne ueber die in der Stufe erreichbaren Gueten: ruft die
   * Bonus-Preview fuer die NIEDRIGSTE und HOECHSTE erreichbare Guete (Spez + Fokus
   * fliessen serverseitig ein) und zippt sie zu "+x% … +y%"-Zeilen.
   */
  private loadPreview(): void {
    const spec = this.selSpec();
    const focus = this.selFocus() || null;
    const reachable = this.reachableGrades();
    const lo = reachable[0] ?? null;
    const hi = reachable.length ? reachable[reachable.length - 1] : null;

    forkJoin({
      low: this.api.getBonusPreview(spec, focus, lo),
      high: this.api.getBonusPreview(spec, focus, hi),
    }).subscribe({
      next: ({ low, high }) => this.preview.set(this.mergePreview(low, high)),
      error: () => this.preview.set([]),
    });
  }

  /**
   * Zippt zwei Bonus-Listen (niedrigste/hoechste Guete) zu Spannen-Zeilen.
   * Defensiv ueber stat+target gematcht, falls die Listen abweichen sollten.
   */
  private mergePreview(low: CommanderBonus[], high: CommanderBonus[]): RangeBonus[] {
    const key = (b: CommanderBonus) => `${b.stat}|${b.target}`;
    const highMap = new Map(high.map((b) => [key(b), b.pct]));
    return low.map((b) => {
      const hp = highMap.get(key(b)) ?? b.pct;
      return {
        stat: b.stat,
        target: b.target,
        pctLow: Math.min(b.pct, hp),
        pctHigh: Math.max(b.pct, hp),
      };
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
  protected readonly navIcon = navIcon;
  protected readonly statIcon = statIcon;
  protected readonly statusIcon = statusIcon;
  /** Blendet ein nicht ladbares Inline-Icon aus (Label bleibt sichtbar). */
  hideImg(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
  bandClass = (m: number) => this.balance.moraleBandClass(m);
  gradeClass = (g?: string | null) => gradeBadgeClass(g);
  gradeText = (g?: string | null) => gradeLabel(g);

  /** Bonus-Faktor (potency) einer Guete aus balance.json, oder null. */
  private gradePotency(g?: string | null): number | null {
    const pot = this.gradesConfig()?.potency?.[gradeCanonical(g)];
    return typeof pot === 'number' ? pot : null;
  }

  /** Tooltip am Grad-Badge: "Güteklasse X (Bonus-Faktor ×Y)". */
  gradeTip(g?: string | null): string {
    const pot = this.gradePotency(g);
    const base = `Güteklasse ${gradeLabel(g)}`;
    return pot != null ? `${base} (Bonus-Faktor ×${pot})` : base;
  }

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

  // -- Vorschau-Spanne (Erwartetes Profil) --------------------------------
  /** "+x%" bei einer Guete, sonst "+x% … +y%" ueber die erreichbaren Gueten. */
  rangeText(b: RangeBonus): string {
    const lo = this.signedPct(b.pctLow);
    return Math.round(b.pctLow * 100) === Math.round(b.pctHigh * 100)
      ? lo
      : `${lo} … ${this.signedPct(b.pctHigh)}`;
  }

  rangeTip(b: RangeBonus): string {
    const stat = CommandersComponent.STAT_LABEL[b.stat] ?? b.stat;
    const tgt = b.target === 'all' ? 'alle Schiffe' : this.classLabel(b.target);
    const range = this.rangeText(b);
    const gueteHint = this.previewGradeLabel() ? ` über ${this.previewGradeLabel()}` : '';
    return `${range} ${stat} auf ${tgt}\n(erwarteter Basiswert${gueteHint} — skaliert mit Güteklasse, Rang und im Kampf mit Moral)`;
  }
}
