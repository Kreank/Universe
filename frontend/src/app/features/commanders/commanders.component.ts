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
  metaFor,
} from '../../core/models/display';
import { commanderStyles } from './commander.styles';

@Component({
  selector: 'app-commanders',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, FormsModule],
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
        🎖️ {{ showTrain() ? 'Abbrechen' : 'Kadett ausbilden' }}
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

        <div class="preview">
          <span class="bonus-head faint small">Erwartetes Profil (Kadett, ohne Traits)</span>
          <div class="bonus-chips">
            @for (b of preview(); track b.stat + b.target) {
              <span class="chip bonus" [class.neg]="b.pct < 0" [attr.data-tip]="bonusTip(b)">
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
              <img src="assets/img/commanders/portrait.svg" alt="" />
              <span class="rank-badge">{{ rank(c.rank).glyph }} {{ rank(c.rank).label }}</span>
              @if (c.training_finishes_at) {
                <span class="status-tag">in Ausbildung</span>
              } @else if (c.assigned_fleet_id) {
                <span class="status-tag">im Einsatz</span>
              }
            </div>

            <div class="cmd-body">
              <div class="row-between">
                <h3>{{ c.name }}</h3>
                <span class="chip">{{ spec(c.specialization).glyph }} {{ spec(c.specialization).label }}</span>
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

              <div class="traits">
                @for (t of c.traits; track t) {
                  <span class="chip trait">{{ trait(t).glyph }} {{ trait(t).label }}</span>
                }
              </div>

              @if (c.bonuses.length) {
                <div class="bonuses">
                  <span class="bonus-head faint small">Boni (bei voller Moral){{ c.focus ? ' · Fokus: ' + classLabel(c.focus) : '' }}</span>
                  <div class="bonus-chips">
                    @for (b of c.bonuses; track b.stat + b.target) {
                      <span class="chip bonus" [class.neg]="b.pct < 0" [attr.data-tip]="bonusTip(b)">
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
      <p class="empty-state">
        Noch keine Commander. Baue eine Kommando-Akademie und bilde deinen ersten Offizier aus.
      </p>
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
  protected readonly preview = signal<CommanderBonus[]>([]);
  protected readonly specOptions = ['combat', 'logistics', 'spy', 'research', 'trade'];
  protected readonly focusOptions = ['fighter', 'cruiser', 'capital', 'civil'];

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
    this.api.trainCommander(planetId, this.selSpec(), this.selFocus() || null).subscribe({
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
  bandClass = (m: number) => this.balance.moraleBandClass(m);

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
    return `${this.signedPct(b.pct)} ${stat} auf ${tgt}\n(Basiswert — im Kampf mit der Moral skaliert)`;
  }
}
