import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  AbilityCatalog,
  CommanderBonus,
  CommanderDetail,
  CommanderMemoryDossier,
  CommanderMemoryEntry,
  EquipmentCatalog,
  EquipmentItem,
  EquipmentState,
  Planet,
} from '../../core/models/api.models';
import {
  RANK_META,
  SPECIALIZATION_META,
  TRAIT_META,
  commanderFace,
  gradeBadgeClass,
  gradeLabel,
  metaFor,
} from '../../core/models/display';
import {
  abilityCategoryIcon,
  equipmentItemIcon,
  equipmentSetIcon,
  equipmentSlotIcon,
  rankIcon,
  specIcon,
  statIcon,
  statusIcon,
  traitIcon,
  uiIcon,
} from '../../core/models/icon-assets';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { commanderDetailStyles } from './commander-detail.styles';

@Component({
  selector: 'app-commander-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, DatePipe, FormsModule, CountdownComponent, BtnIconComponent],
  template: `
    <a class="back" routerLink="/commanders">← Zurueck zum Roster</a>

    @if (commander(); as c) {
      <!-- Meuterei-Warnung: deutlich sichtbar ueber dem gesamten Profil -->
      @if (mutinyState(c); as ms) {
        <div class="mutiny-banner" [class.acute]="ms === 'acute'">
          @if (ms === 'acute') {
            <div class="mb-title">🔥 MEUTEREI — verweigert Befehle</div>
            <p class="mb-body">{{ c.name }} gehorcht nicht mehr und steht keiner Flotte zur Verfügung.
              Erfülle eine seiner Forderungen (Beförderung / Beuteanteil) im Postfach — das beendet die
              Befehlsverweigerung und hebt die Treue. Ignorieren hält ihn außer Kontrolle.</p>
          } @else {
            <div class="mb-title">⚠️ Kurz vor der Meuterei</div>
            <p class="mb-body">Treue und Unmut sind kritisch. Senke Unmut und Groll, indem du seine
              Forderungen erfüllst — sonst verweigert er bald die Befehle.</p>
          }
        </div>
      }

      <div class="grid layout">
        <section class="card profile">
          <div class="portrait" [class]="bandClass(c.morale)">
            <img [src]="faceFor(c.id)" alt="" (error)="onFaceError($event)" />
          </div>
          <h1>{{ c.name }}</h1>
          <div class="badges">
            <span class="chip grade-chip" [class]="gradeClass(c.grade)">Grad {{ gradeText(c.grade) }}</span>
            <span class="chip"><img class="chip-ico" [src]="rankIcon(c.rank)" alt="" (error)="hideImg($event)" />{{ rank(c.rank).label }}</span>
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
            <p class="faint small">Kampf-Modifikator: {{ (c.morale_band.combat_mod * 100).toFixed(0) }}%</p>
          </div>

          @if (c.bonuses?.length) {
            <div class="bonuses">
              <div class="panel-title">Passive Boni (bei voller Moral){{ c.focus ? ' · Fokus: ' + classLabel(c.focus) : '' }}</div>
              <div class="bonus-chips">
                @for (b of c.bonuses; track b.stat + b.target) {
                  <span class="chip bonus tip" [class.neg]="b.pct < 0" [attr.data-tip]="bonusTip(b)">
                    <app-btn-icon [src]="statIcon(b.stat)" [glyph]="statGlyph(b.stat)" [size]="14" /> {{ signedPct(b.pct) }} {{ targetLabel(b.target) }}
                  </span>
                }
              </div>
              <p class="faint small">Wachsen mit Rang/Güteklasse + Moral (nicht über Skillpunkte). Wirken automatisch im Kampf/Tempo.</p>
              @if (c.equipment_bonuses?.length) {
                <p class="faint small">Davon aus Ausrüstung: {{ equipmentBonusSummary(c) }}</p>
              }
            </div>
          }

          <dl class="stats">
            <div><dt>XP</dt><dd class="mono">{{ c.xp }}</dd></div>
            <div><dt>Loyalitaet</dt><dd class="mono">{{ c.loyalty }}</dd></div>
            <div><dt>Unmut</dt><dd class="mono" [class.warn]="(c.unrest ?? 0) >= 70">{{ c.unrest ?? 0 }}/100</dd></div>
            <div><dt>Span</dt><dd class="mono">{{ c.span_capacity }}</dd></div>
            <div><dt>Status</dt><dd>{{ statusLabel(c) }}</dd></div>
          </dl>
          @if ((c.unrest ?? 0) >= 70) {
            <p class="faint small"><app-btn-icon [src]="statusIcon('alert')" glyph="⚑" [size]="14" /> Wird bald eine Forderung stellen — erfüllen hebt die Treue, ignorieren senkt sie.</p>
          }

          @if (c.training_finishes_at) {
            <div class="train-row">
              <span class="muted small">Ausbildung laeuft</span>
              <app-countdown [target]="c.training_finishes_at" />
            </div>
          }

          <div class="traits">
            @for (t of c.traits; track t) {
              <span class="chip trait tip" [attr.data-tip]="trait(t).label + ' — ' + traitEffect(t)"><img class="chip-ico" [src]="traitIcon(t)" alt="" (error)="hideImg($event)" />{{ trait(t).label }}</span>
            }
          </div>

          <!-- Charakter-Zucht (Trait-Reroll/Ersatz, Ressourcen-Kosten) -->
          <div class="trait-train">
            <div class="panel-title"><app-btn-icon [src]="uiIcon('genetics')" glyph="🧬" [size]="16" /> Charakter-Zucht</div>
            <button class="btn btn-ghost btn-sm" type="button" (click)="reroll()">Traits neu würfeln</button>
            <div class="replace-row">
              <select [ngModel]="desiredTrait()" (ngModelChange)="desiredTrait.set($event)">
                <option [ngValue]="null">— Wunsch-Trait —</option>
                @for (k of allTraits(); track k) { <option [ngValue]="k">{{ trait(k).label }}</option> }
              </select>
              <select [ngModel]="dropTrait()" (ngModelChange)="dropTrait.set($event)">
                <option [ngValue]="null">— ersetzt (beliebig) —</option>
                @for (t of c.traits; track t) { <option [ngValue]="t">{{ trait(t).label }}</option> }
              </select>
              <button class="btn btn-ghost btn-sm" type="button" [disabled]="!desiredTrait()" (click)="replaceTrait()">Ersetzen</button>
            </div>
            <p class="faint small">Reroll = neue Zufalls-Traits; Ersetzen = einen gezielt tauschen. Kostet Ressourcen am Heimatplaneten.</p>
          </div>

          <!-- Gouverneurs-Posten -->
          @if (c.status === 'active') {
            <div class="governor">
              <div class="panel-title"><app-btn-icon [src]="uiIcon('governor')" glyph="🏛️" [size]="16" /> Gouverneur</div>
              @if (governedPlanet(); as gp) {
                <p class="small">Verwaltet <strong>{{ gp.name }}</strong> [{{ gp.galaxy }}:{{ gp.system }}:{{ gp.position }}] — hebt dessen Produktion.</p>
                <button class="btn btn-ghost btn-sm" type="button" (click)="recallGovernor(gp.id)">Abberufen</button>
              } @else {
                <div class="gov-assign">
                  <select [ngModel]="govPlanet()" (ngModelChange)="govPlanet.set($event)">
                    <option [ngValue]="null">— Planet wählen —</option>
                    @for (p of planets(); track p.id) {
                      <option [ngValue]="p.id">{{ p.name }} [{{ p.galaxy }}:{{ p.system }}:{{ p.position }}]</option>
                    }
                  </select>
                  <button class="btn btn-ghost btn-sm" type="button" [disabled]="!govPlanet()" (click)="assignGovernor()">Einsetzen</button>
                </div>
                <p class="faint small">Als Gouverneur eingesetzt führt er keine Flotte; „Verwaltung"-Kommandeure bringen den höchsten Bonus.</p>
              }
            </div>
          }

          <!-- Faehigkeiten (RPG-Entwicklung) -->
          <div class="abilities-panel">
            <div class="ab-head">
              <span class="panel-title"><app-btn-icon [src]="uiIcon('ability')" glyph="⚡" [size]="16" /> Fähigkeiten</span>
              <span class="sp-badge" title="Skillpunkte">{{ c.skill_points ?? 0 }} SP</span>
              <span class="slot-badge" title="gleichzeitig scharfschaltbar">{{ c.arm_slots ?? 1 }} Slots</span>
            </div>
            <div class="ability-grid">
              @for (a of abilityList(); track a.key) {
                <div class="ability-card" [class.learned]="a.level > 0" [class.locked]="!rankOk(c, a.def)">
                  <div class="ac-top">
                    <span class="ac-glyph" [attr.data-cat]="a.def.category">
                      <img class="ac-ico" [src]="catIcon(a.def.category)" alt="" (error)="onCatIcoError($event)" />
                      <span class="ac-glyph-fb">{{ catGlyph(a.def.category) }}</span>
                    </span>
                    <span class="ac-name">{{ a.def.label }}</span>
                    <span class="ac-pips" [attr.title]="'Stufe ' + a.level + '/' + a.def.max_level">
                      @for (i of pipArray(a.def.max_level); track i) {
                        <span class="pip" [class.on]="i < a.level"></span>
                      }
                    </span>
                  </div>
                  <div class="ac-effect">{{ effectText(a.def) }}</div>
                  <div class="ac-foot">
                    @if (!rankOk(c, a.def)) {
                      <span class="ac-req">ab {{ rank(a.def.requires?.min_rank ?? 'cadet').label }}</span>
                    } @else if (a.level < a.def.max_level) {
                      <button class="btn btn-primary btn-sm" type="button"
                        [disabled]="(c.skill_points ?? 0) < a.def.sp_cost"
                        (click)="trainAbility(a.key)">
                        {{ a.level === 0 ? 'Lernen' : 'Steigern' }} · {{ a.def.sp_cost }} SP
                      </button>
                    } @else {
                      <span class="ac-max">★ max</span>
                    }
                    @if (a.level > 0) {
                      <button class="btn btn-ghost btn-sm" type="button" (click)="forgetAbility(a.key)">Verlernen</button>
                    }
                  </div>
                </div>
              }
            </div>
            <p class="faint small">Skillpunkte gibt's beim Rang-Aufstieg. Erlernte Fähigkeiten schaltest du beim Flottenversand scharf (bis Slots).</p>
          </div>

          <!-- Ausruestung (Equipment-System) -->
          <div class="equip-panel">
            <div class="panel-title"><app-btn-icon [src]="uiIcon('equipment')" glyph="🎽" [size]="16" /> Ausrüstung</div>
            @if (equipError(); as err) {
              <p class="faint small warn-text">{{ err }}</p>
            }

            <div class="slot-grid">
              @for (s of equipSlots(); track s.slot) {
                <div class="equip-slot" [class.filled]="!!s.item" [class.open]="openSlot() === s.slot">
                  <button class="slot-btn" type="button" (click)="toggleSlot(s.slot)">
                    <span class="slot-ico">
                      <img [src]="s.item ? itemIcon(s.item.item_key) : slotIcon(s.slot)" alt="" (error)="onCatIcoError($event)" />
                      <span class="slot-glyph-fb">{{ slotGlyph(s.slot) }}</span>
                    </span>
                    <span class="slot-meta">
                      <span class="slot-label">{{ s.label }}</span>
                      @if (s.item; as it) {
                        <span class="item-label rar" [class]="rarityClass(it.rarity)">{{ it.label }}</span>
                        <span class="rar-tag" [class]="rarityClass(it.rarity)">{{ it.rarity_label }}</span>
                      } @else {
                        <span class="faint small">leer</span>
                      }
                    </span>
                  </button>

                  @if (s.item; as it) {
                    <div class="item-bonus">
                      @for (b of it.bonuses; track b.stat + b.target) {
                        <span class="chip bonus"><app-btn-icon [src]="statIcon(b.stat)" [glyph]="statGlyph(b.stat)" [size]="12" /> {{ signedPct(b.pct) }} {{ targetLabel(b.target) }}</span>
                      }
                    </div>
                    <button class="btn btn-ghost btn-sm" type="button" (click)="unequip(s.slot)">Ablegen</button>
                  }

                  @if (openSlot() === s.slot) {
                    <div class="inv-picker">
                      @for (it of inventoryForSlot(s.slot); track it.id) {
                        <button class="inv-opt rar" [class]="rarityClass(it.rarity)" type="button" (click)="equip(it.id)">
                          <span class="slot-ico sm">
                            <img [src]="itemIcon(it.item_key)" alt="" (error)="onCatIcoError($event)" />
                            <span class="slot-glyph-fb">{{ slotGlyph(it.slot) }}</span>
                          </span>
                          <span class="inv-opt-meta">
                            <span class="item-label">{{ it.label }}</span>
                            <span class="faint small">{{ it.rarity_label }} · {{ setLabel(it.set) }}</span>
                          </span>
                        </button>
                      } @empty {
                        <p class="faint small">Kein passendes Teil im Inventar. Fertige Ausrüstung an der Akademie oder finde sie in Quests / Expeditionen / Events.</p>
                      }
                    </div>
                  }
                </div>
              }
            </div>

            <!-- Set-Fortschritt -->
            @if (equipment()?.sets?.length) {
              <div class="set-progress">
                <div class="bonus-head faint small">Set-Boni</div>
                @for (set of equipment()!.sets; track set.key) {
                  <div class="set-row">
                    <span class="set-ico">
                      <img [src]="setIcon(set.key)" alt="" (error)="onCatIcoError($event)" />
                      <span class="slot-glyph-fb">{{ setGlyph(set.key) }}</span>
                    </span>
                    <div class="set-body">
                      <div class="set-head">
                        <strong>{{ set.label }}</strong>
                        <span class="mono">{{ set.count }}/4</span>
                      </div>
                      <div class="set-thresholds">
                        @for (t of setThresholds(set.key); track t.n) {
                          <div class="set-th" [class.active]="t.active">
                            <span class="th-n">{{ t.n }}er</span>
                            @for (b of t.bonuses; track b.stat + b.target) {
                              <span class="chip bonus" [class.off]="!t.active">{{ signedPct(b.pct) }} {{ statLabel(b.stat) }} {{ targetLabel(b.target) }}</span>
                            }
                          </div>
                        }
                      </div>
                    </div>
                  </div>
                }
              </div>
            }
            <p class="faint small">Ausrüstung füllt 4 Slots (Kopf/Hände/Brust/Schuhe) und gibt zusätzliche Boni. Vier Teile desselben Sets schalten starke Set-Boni frei.</p>
          </div>

          <div class="persona">
            <div class="panel-title">Persona</div>
            <p class="small">{{ c.persona.background }}</p>
            <p class="faint small">Sprechstil: {{ c.persona.voice }}</p>
          </div>
        </section>

        <div class="col-right">
          <!-- Innenleben: Gedaechtnis, Meinungen, Beziehungen, Groll (Welle 2) -->
          @if (dossier(); as d) {
            <section class="card innenleben">
              <div class="panel-title"><app-btn-icon [src]="uiIcon('ability')" glyph="🧠" [size]="16" /> Innenleben — Gedächtnis &amp; Beziehungen</div>

              @if (d.memory_summary) {
                <blockquote class="memory-summary">{{ d.memory_summary }}</blockquote>
              }

              @if (d.grievances.length) {
                <div class="il-block">
                  <div class="il-head"><app-btn-icon [src]="statusIcon('alert')" glyph="⚑" [size]="14" /> Offener Groll</div>
                  <ul class="grievance-list">
                    @for (g of d.grievances; track g.grievance_type) {
                      <li class="grievance" [class.sev-high]="g.severity >= 6">
                        <span class="g-dot"></span>
                        <span class="g-label">{{ grievanceLabel(g.grievance_type) }}</span>
                        @if (g.accumulated_count > 1) { <span class="g-count">×{{ g.accumulated_count }}</span> }
                        <span class="g-sev">Schwere {{ g.severity }}</span>
                      </li>
                    }
                  </ul>
                  <p class="faint small">Offener Groll staut sich zu Unmut auf und treibt früher oder später in die Meuterei. Erfüllte Forderungen legen ihn bei.</p>
                </div>
              }

              @if (d.opinions.length) {
                <div class="il-block">
                  <div class="il-head">Meinungen über Gegner</div>
                  @for (o of d.opinions; track o.target_name + o.opinion_type) {
                    <div class="opinion" [class.hated]="o.hated">
                      <div class="op-row">
                        <span class="op-verb" [class]="opinionClass(o.opinion_type)">{{ opinionLabel(o.opinion_type) }}</span>
                        <span class="op-target">{{ o.target_name ?? 'Unbekannt' }}</span>
                        <span class="op-kind faint small">{{ o.target_kind === 'npc' ? 'KI-Imperium' : 'Spieler' }}</span>
                        @if (o.hated) { <span class="archenemy">☠ Erzfeind</span> }
                      </div>
                      <div class="bar op-bar" [class]="opinionClass(o.opinion_type)"><span class="fill" [style.width.%]="pct(o.strength)"></span></div>
                    </div>
                  }
                </div>
              }

              @if (d.relationships.length) {
                <div class="il-block">
                  <div class="il-head">Beziehungen zu anderen Kommandeuren</div>
                  @for (r of d.relationships; track r.other_commander_id) {
                    <a class="relation" [class]="relClass(r.rel_type)" [routerLink]="['/commanders', r.other_commander_id]">
                      <div class="op-row">
                        <span class="op-verb" [class]="relClass(r.rel_type)">{{ relLabel(r.rel_type) }}</span>
                        <span class="op-target">{{ r.other_name ?? 'Unbekannt' }}</span>
                        <span class="rel-arrow">→</span>
                      </div>
                      <div class="bar op-bar" [class]="relClass(r.rel_type)"><span class="fill" [style.width.%]="pct(r.strength)"></span></div>
                    </a>
                  }
                </div>
              }

              @if (d.memories.length) {
                <div class="il-block">
                  <div class="il-head">Gedächtnis</div>
                  <ol class="mem-timeline">
                    @for (m of d.memories; track $index) {
                      <li class="mem" [class]="'sent-' + m.sentiment">
                        <span class="mem-dot"></span>
                        <div class="mem-entry">
                          <div class="row-between">
                            <strong>{{ memoryLabel(m.event_type) }}</strong>
                            @if (m.created_at) { <span class="faint small">{{ m.created_at | date: 'short' }}</span> }
                          </div>
                          @if (memoryContext(m); as ctx) { <p class="small mem-ctx">{{ ctx }}</p> }
                        </div>
                      </li>
                    }
                  </ol>
                </div>
              }

              @if (!d.memory_summary && !d.memories.length && !d.opinions.length && !d.relationships.length && !d.grievances.length) {
                <p class="muted small">Dieser Kommandeur hat noch keine Geschichte geschrieben. Setze ihn ein — Siege, Niederlagen und Forderungen prägen seinen Charakter.</p>
              }
            </section>
          }

          <!-- Funkspruch-Historie -->
          <section class="card history">
            <div class="panel-title"><app-btn-icon [src]="statusIcon('transmission_unread')" glyph="📡" [size]="16" /> Funkspruch-Historie</div>
            @if (c.history.length) {
              <ol class="timeline">
                @for (h of c.history; track h.id) {
                  <li>
                    <div class="dot"></div>
                    <div class="entry">
                      <div class="row-between">
                        <strong>{{ h.subject }}</strong>
                        <span class="faint small">{{ h.created_at | date: 'short' }}</span>
                      </div>
                      <p class="small body">{{ h.body }}</p>
                    </div>
                  </li>
                }
              </ol>
            } @else {
              <p class="muted small">Noch keine Funksprueche von diesem Commander.</p>
            }
          </section>
        </div>
      </div>
    } @else if (loading()) {
      <p class="empty-state">Lade Commander…</p>
    } @else {
      <p class="empty-state">Commander nicht gefunden.</p>
    }
  `,
  styles: [commanderDetailStyles],
})
export class CommanderDetailComponent {
  private readonly api = inject(ApiService);
  private readonly balance = inject(BalanceService);
  private readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  /** Route-Parameter via withComponentInputBinding. */
  readonly id = input<string>('');

  protected readonly commander = signal<CommanderDetail | null>(null);
  protected readonly loading = signal(true);
  protected readonly planets = this.state.planets;
  protected readonly govPlanet = signal<string | null>(null);
  protected readonly abilityCatalog = signal<AbilityCatalog | null>(null);

  /** Gedaechtnis-Dossier (Welle 2): Erinnerungen, Meinungen, Beziehungen, Groll. */
  protected readonly dossier = signal<CommanderMemoryDossier | null>(null);

  // -- Ausruestung (Equipment) --
  protected readonly equipment = signal<EquipmentState | null>(null);
  protected readonly inventory = signal<EquipmentItem[]>([]);
  protected readonly equipCatalog = signal<EquipmentCatalog | null>(null);
  protected readonly openSlot = signal<string | null>(null);
  protected readonly equipError = signal<string | null>(null);
  protected readonly equipSlots = computed(() => this.equipment()?.slots ?? []);

  protected readonly slotIcon = equipmentSlotIcon;
  protected readonly itemIcon = equipmentItemIcon;
  protected readonly setIcon = equipmentSetIcon;

  private readonly SLOT_GLYPH: Record<string, string> = { head: '⛑️', hands: '🧤', chest: '🦺', shoes: '🥾' };
  private readonly SET_GLYPH: Record<string, string> = { fighter: '🛩️', cruiser: '🚀', capital: '🔱', civil: '📦' };
  private readonly SET_LABEL: Record<string, string> = {
    fighter: 'Jäger-Set', cruiser: 'Kreuzer-Set', capital: 'Großkampf-Set', civil: 'Zivil-Set',
  };
  slotGlyph = (s: string) => this.SLOT_GLYPH[s] ?? '📦';
  setGlyph = (s: string) => this.SET_GLYPH[s] ?? '✦';
  setLabel = (s: string) => this.SET_LABEL[s] ?? s;
  rarityClass = (r: string) => `rar-${r}`;

  /** Items im Inventar, die in diesen Slot passen und aktuell von niemandem getragen werden. */
  inventoryForSlot(slot: string): EquipmentItem[] {
    return this.inventory().filter((it) => it.slot === slot && !it.equipped_commander_id);
  }

  /** Set-Schwellen (2er/4er) mit Boni-Texten und Aktiv-Flag aus dem Katalog. */
  setThresholds(setKey: string): { n: number; active: boolean; bonuses: CommanderBonus[] }[] {
    const cat = this.equipCatalog()?.sets?.[setKey];
    if (!cat) {
      return [];
    }
    const set = this.equipment()?.sets.find((s) => s.key === setKey);
    const active = set?.active_thresholds ?? [];
    return Object.keys(cat.bonus)
      .map((k) => Number(k))
      .sort((a, b) => a - b)
      .map((n) => ({ n, active: active.includes(n), bonuses: cat.bonus[String(n)] ?? [] }));
  }

  /** Kurztext, welcher Boni-Anteil aus getragener Ausruestung stammt. */
  equipmentBonusSummary(c: CommanderDetail): string {
    return (c.equipment_bonuses ?? [])
      .map((b) => `${this.signedPct(b.pct)} ${this.statLabel(b.stat)}${b.target === 'all' ? '' : ' ' + this.classLabel(b.target)}`)
      .join(', ');
  }

  toggleSlot(slot: string): void {
    this.equipError.set(null);
    this.openSlot.update((s) => (s === slot ? null : slot));
  }

  equip(itemId: string): void {
    const c = this.commander();
    if (!c) {
      return;
    }
    this.api.equipItem(c.id, itemId).subscribe({
      next: (state) => {
        this.equipment.set(state);
        this.openSlot.set(null);
        this.refreshAfterEquip();
      },
      error: (e) => this.equipError.set(e?.error?.detail ?? 'Anlegen fehlgeschlagen.'),
    });
  }

  unequip(slot: string): void {
    const c = this.commander();
    if (!c) {
      return;
    }
    this.api.unequipItem(c.id, slot).subscribe({
      next: (state) => {
        this.equipment.set(state);
        this.refreshAfterEquip();
      },
      error: (e) => this.equipError.set(e?.error?.detail ?? 'Ablegen fehlgeschlagen.'),
    });
  }

  /** Nach equip/unequip: Boni (Commander) und Inventar-Trage-Status auffrischen. */
  private refreshAfterEquip(): void {
    const c = this.commander();
    if (!c) {
      return;
    }
    this.api.getCommander(c.id).subscribe((u) => this.commander.set(u));
    this.api.getInventory().subscribe((inv) => this.inventory.set(inv));
    void this.state.reloadCommanders();
  }

  private loadEquipment(id: string): void {
    this.openSlot.set(null);
    this.equipError.set(null);
    this.api.getEquipment(id).subscribe({
      next: (e) => this.equipment.set(e),
      error: () => this.equipment.set(null),
    });
    this.api.getInventory().subscribe({
      next: (inv) => this.inventory.set(inv),
      error: () => this.inventory.set([]),
    });
  }

  /** Katalog als sortierte Liste mit aktueller Stufe des Kommandeurs. */
  protected readonly abilityList = computed(() => {
    const cat = this.abilityCatalog()?.catalog ?? {};
    const learned = new Map((this.commander()?.abilities ?? []).map((a) => [a.key, a.level]));
    return Object.entries(cat).map(([key, def]) => ({
      key,
      def,
      level: learned.get(key) ?? 0,
    }));
  });

  protected readonly desiredTrait = signal<string | null>(null);
  protected readonly dropTrait = signal<string | null>(null);

  /** Kurzbeschreibung der echten Trait-Wirkung (Sichtbarkeit). */
  private readonly TRAIT_EFFECT: Record<string, string> = {
    aggressive: '+Angriff, höheres Eigenrisiko (Permadeath)',
    cautious: 'rettet einen Teil eigener Verluste',
    loyal: 'kaum Überlauf, langsamer Moralverfall',
    ambitious: '+25% XP, fordert Beförderung',
    greedy: '+Moral bei Beute, fordert Beuteanteil',
    honorable: '+Moral bei fairem Ziel, Malus bei Bashing',
    charismatic: 'hebt die Team-Moral',
    hot_tempered: '+Angriff, instabil, Meuterei-Risiko',
  };

  protected readonly allTraits = computed(() => Object.keys(this.TRAIT_EFFECT));

  traitEffect(key: string): string {
    return this.TRAIT_EFFECT[key] ?? '';
  }

  reroll(): void {
    const c = this.commander();
    if (!c) return;
    this.api.retrainTraits(c.id, 'reroll').subscribe({
      next: (u) => this.commander.set(u),
      error: (e) => this.notify.warning('Reroll fehlgeschlagen', e?.error?.detail ?? 'Fehler.'),
    });
  }

  replaceTrait(): void {
    const c = this.commander();
    const desired = this.desiredTrait();
    if (!c || !desired) return;
    this.api.retrainTraits(c.id, 'replace', desired, this.dropTrait() ?? undefined).subscribe({
      next: (u) => {
        this.commander.set(u);
        this.desiredTrait.set(null);
        this.dropTrait.set(null);
      },
      error: (e) => this.notify.warning('Ersetzen fehlgeschlagen', e?.error?.detail ?? 'Fehler.'),
    });
  }

  private readonly RANK_ORDER = ['cadet', 'officer', 'veteran', 'elite', 'legend'];

  private readonly STAT_GLYPH: Record<string, string> = { attack: '⚔', shield: '🛡', speed: '💨' };
  private readonly STAT_LABEL: Record<string, string> = { attack: 'Angriff', shield: 'Schild', speed: 'Tempo' };
  private readonly CLASS_LABEL: Record<string, string> = {
    all: 'alle Schiffe', fighter: 'Jaeger', cruiser: 'Kreuzer', capital: 'Grosskampfschiffe', civil: 'zivile Schiffe',
  };
  statGlyph = (s: string) => this.STAT_GLYPH[s] ?? '•';
  statLabel = (s: string) => this.STAT_LABEL[s] ?? s;
  classLabel = (t: string) => this.CLASS_LABEL[t] ?? t;
  targetLabel = (t: string) => (t === 'all' ? '' : '· ' + this.classLabel(t));
  signedPct = (p: number) => (p > 0 ? '+' : '') + Math.round(p * 100) + '%';

  bonusTip(b: { stat: string; target: string; pct: number }): string {
    const stat = this.STAT_LABEL[b.stat] ?? b.stat;
    const tgt = b.target === 'all' ? 'alle Schiffe' : this.classLabel(b.target);
    return `${this.signedPct(b.pct)} ${stat} auf ${tgt}\n(passiver Basiswert — wächst mit Rang/Güteklasse, im Kampf mit Moral skaliert; nicht über Skillpunkte)`;
  }

  private readonly CAT_GLYPH: Record<string, string> = {
    combat: '⚔', logistics: '📦', spy: '🛰️', research: '🔬', admin: '🏛️', general: '✦',
  };
  catGlyph = (c: string) => this.CAT_GLYPH[c] ?? '✦';
  catIcon = abilityCategoryIcon;

  /** Kategorie-Icon nicht ladbar -> Glyph-Fallback einblenden. */
  onCatIcoError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.style.display = 'none';
    const fb = img.nextElementSibling as HTMLElement | null;
    if (fb) {
      fb.style.display = 'inline';
    }
  }
  pipArray = (n: number) => Array.from({ length: n }, (_, i) => i);

  effectText(def: AbilityCatalog['catalog'][string]): string {
    const pct = Math.round(def.per_level * 100);
    switch (def.kind) {
      case 'attack_pct': return `+${pct}% Angriff/Stufe`;
      case 'loss_reduction': return `−${pct}% eigene Verluste/Stufe`;
      case 'flight_pct': return `−${pct}% Flugzeit/Stufe`;
      case 'fuel_pct': return `−${pct}% Sprit/Stufe`;
      default: return `${pct}%/Stufe`;
    }
  }

  rankOk(c: CommanderDetail, def: AbilityCatalog['catalog'][string]): boolean {
    const need = def.requires?.min_rank ?? 'cadet';
    return this.RANK_ORDER.indexOf(c.rank) >= this.RANK_ORDER.indexOf(need);
  }

  trainAbility(key: string): void {
    const c = this.commander();
    if (!c) {
      return;
    }
    this.api.trainAbility(c.id, key).subscribe({
      next: (updated) => this.commander.set(updated),
      error: (err) => this.notify.warning('Nicht möglich', err?.error?.detail ?? 'Fehler.'),
    });
  }

  forgetAbility(key: string): void {
    const c = this.commander();
    if (!c) {
      return;
    }
    this.api.forgetAbility(c.id, key).subscribe({
      next: (updated) => this.commander.set(updated),
      error: (err) => this.notify.warning('Nicht möglich', err?.error?.detail ?? 'Fehler.'),
    });
  }

  /** Planet, den dieser Kommandeur aktuell als Gouverneur verwaltet (falls vorhanden). */
  protected readonly governedPlanet = computed<Planet | null>(() => {
    const c = this.commander();
    if (!c) {
      return null;
    }
    return this.planets().find((p) => p.governor_commander_id === c.id) ?? null;
  });

  constructor() {
    // Reagiert auf den ueber die Route gebundenen :id-Parameter.
    effect(() => this.load(this.id()));
    this.api.getAbilityCatalog().subscribe((c) => this.abilityCatalog.set(c));
    this.api.getEquipmentCatalog().subscribe((c) => this.equipCatalog.set(c));
  }

  assignGovernor(): void {
    const c = this.commander();
    const pid = this.govPlanet();
    if (!c || !pid) {
      return;
    }
    this.api.setGovernor(pid, c.id).subscribe({
      next: () => void this.state.loadPlanets(),
      error: () => void this.state.loadPlanets(),
    });
  }

  recallGovernor(planetId: string): void {
    this.api.setGovernor(planetId, null).subscribe({
      next: () => void this.state.loadPlanets(),
      error: () => void this.state.loadPlanets(),
    });
  }

  private load(id: string): void {
    if (!id) {
      this.loading.set(false);
      return;
    }
    this.loading.set(true);
    this.dossier.set(null);
    this.api.getCommander(id).subscribe({
      next: (c) => {
        this.commander.set(c);
        this.loading.set(false);
        this.loadEquipment(id);
      },
      error: () => this.loading.set(false),
    });
    this.api.getCommanderMemory(id).subscribe({
      next: (d) => this.dossier.set(d),
      error: () => this.dossier.set(null),
    });
  }

  /** Einstufung des Meuterei-Risikos fuer den Warnbanner. */
  mutinyState(c: CommanderDetail): 'acute' | 'risk' | null {
    const d = this.dossier();
    if (c.status === 'mutinous' || d?.mutiny_warning) {
      return 'acute';
    }
    const grievances = d?.grievances?.length ?? 0;
    if (c.loyalty < 35 || (c.unrest ?? 0) >= 70 || grievances >= 2) {
      return 'risk';
    }
    return null;
  }

  // -- Gedaechtnis-Dossier: Labels & Aufbereitung (Welle 2) ---------------
  private readonly MEMORY_LABEL: Record<string, string> = {
    combat_victory: 'Sieg in der Schlacht',
    combat_crushing_victory: 'Vernichtender Sieg',
    combat_close_win: 'Knapper Sieg',
    combat_defeat: 'Niederlage im Kampf',
    heavy_losses: 'Schwere Verluste',
    expedition_success: 'Erfolgreiche Expedition',
    demand_fulfilled: 'Forderung erfüllt',
    demand_ignored: 'Forderung abgewiesen',
    promotion: 'Beförderung',
    mutiny: 'Meuterei',
  };
  private readonly OPINION_LABEL: Record<string, string> = {
    respects: 'respektiert', despises: 'verachtet', fears: 'fürchtet', envies: 'beneidet',
  };
  private readonly REL_LABEL: Record<string, string> = {
    rivalry: 'Rivalität', respect: 'Respekt', grudge: 'Groll', bond: 'Verbundenheit',
  };
  private readonly GRIEVANCE_LABEL: Record<string, string> = {
    risky_missions: 'Riskante Dauereinsätze', ignored_demand: 'Ignorierte Forderung',
    denied_promotion: 'Verwehrte Beförderung',
  };
  private readonly RES_LABEL: Record<string, string> = {
    metal: 'Metall', crystal: 'Kristall', deuterium: 'Deuterium',
  };

  memoryLabel = (k: string) => this.MEMORY_LABEL[k] ?? k;
  opinionLabel = (k: string) => this.OPINION_LABEL[k] ?? k;
  opinionClass = (k: string) => `op-${k}`;
  relLabel = (k: string) => this.REL_LABEL[k] ?? k;
  relClass = (k: string) => `rel-${k}`;
  grievanceLabel = (k: string) => this.GRIEVANCE_LABEL[k] ?? k;
  pct = (s: number) => Math.round(Math.max(0, Math.min(1, s)) * 100);

  /** Lesbarer Kontext-Einzeiler einer Erinnerung (Gegner/Ort/Ausgang/Beute/Rang). */
  memoryContext(m: CommanderMemoryEntry): string {
    const ctx = m.context ?? {};
    const parts: string[] = [];
    if (ctx.enemy_name) {
      parts.push(`Gegner: ${ctx.enemy_name}`);
    }
    if (ctx.planet) {
      parts.push(`Ort: ${ctx.planet}`);
    }
    if (ctx.outcome) {
      parts.push(ctx.outcome === 'win' ? 'Ausgang: Sieg' : 'Ausgang: Niederlage');
    }
    const loot = (ctx.loot ?? {}) as Record<string, number>;
    const lootText = Object.entries(loot)
      .filter(([, v]) => v)
      .map(([k, v]) => `${this.RES_LABEL[k] ?? k} ${v}`)
      .join(', ');
    if (lootText) {
      parts.push(`Beute: ${lootText}`);
    }
    if (ctx.rank) {
      parts.push(`Neuer Rang: ${this.rank(String(ctx.rank)).label}`);
    }
    return parts.join(' · ');
  }

  statusLabel(c: CommanderDetail): string {
    if (c.training_finishes_at) {
      return 'in Ausbildung';
    }
    if (c.assigned_fleet_id) {
      return 'im Einsatz';
    }
    return c.status || 'bereit';
  }

  rank = (r: string) => metaFor(RANK_META, r);
  spec = (s: string) => metaFor(SPECIALIZATION_META, s);
  trait = (t: string) => metaFor(TRAIT_META, t);
  protected readonly rankIcon = rankIcon;
  protected readonly specIcon = specIcon;
  protected readonly traitIcon = traitIcon;
  protected readonly statIcon = statIcon;
  protected readonly statusIcon = statusIcon;
  protected readonly uiIcon = uiIcon;
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
}
