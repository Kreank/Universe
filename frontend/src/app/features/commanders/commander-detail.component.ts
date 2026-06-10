import { ChangeDetectionStrategy, Component, computed, effect, inject, input, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import { AbilityCatalog, CommanderDetail, Planet } from '../../core/models/api.models';
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
import { CountdownComponent } from '../../shared/components/countdown.component';
import { commanderDetailStyles } from './commander-detail.styles';

@Component({
  selector: 'app-commander-detail',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, DatePipe, FormsModule, CountdownComponent],
  template: `
    <a class="back" routerLink="/commanders">← Zurueck zum Roster</a>

    @if (commander(); as c) {
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
                    {{ statGlyph(b.stat) }} {{ signedPct(b.pct) }} {{ targetLabel(b.target) }}
                  </span>
                }
              </div>
              <p class="faint small">Wachsen mit Rang/Güteklasse + Moral (nicht über Skillpunkte). Wirken automatisch im Kampf/Tempo.</p>
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
            <p class="faint small">⚑ Wird bald eine Forderung stellen — erfüllen hebt die Treue, ignorieren senkt sie.</p>
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
            <div class="panel-title">🧬 Charakter-Zucht</div>
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
              <div class="panel-title">🏛️ Gouverneur</div>
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
              <span class="panel-title">⚡ Fähigkeiten</span>
              <span class="sp-badge" title="Skillpunkte">{{ c.skill_points ?? 0 }} SP</span>
              <span class="slot-badge" title="gleichzeitig scharfschaltbar">{{ c.arm_slots ?? 1 }} Slots</span>
            </div>
            <div class="ability-grid">
              @for (a of abilityList(); track a.key) {
                <div class="ability-card" [class.learned]="a.level > 0" [class.locked]="!rankOk(c, a.def)">
                  <div class="ac-top">
                    <span class="ac-glyph" [attr.data-cat]="a.def.category">{{ catGlyph(a.def.category) }}</span>
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

          <div class="persona">
            <div class="panel-title">Persona</div>
            <p class="small">{{ c.persona.background }}</p>
            <p class="faint small">Sprechstil: {{ c.persona.voice }}</p>
          </div>
        </section>

        <!-- Funkspruch-Historie -->
        <section class="card history">
          <div class="panel-title">📡 Funkspruch-Historie</div>
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
    this.api.getCommander(id).subscribe({
      next: (c) => {
        this.commander.set(c);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
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
