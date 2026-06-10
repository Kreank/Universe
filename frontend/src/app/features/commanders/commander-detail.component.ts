import { ChangeDetectionStrategy, Component, effect, inject, input, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { CommanderDetail } from '../../core/models/api.models';
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
  imports: [RouterLink, DatePipe, CountdownComponent],
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
              <span class="chip trait tip" [attr.data-tip]="trait(t).label"><img class="chip-ico" [src]="traitIcon(t)" alt="" (error)="hideImg($event)" />{{ trait(t).label }}</span>
            }
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

  /** Route-Parameter via withComponentInputBinding. */
  readonly id = input<string>('');

  protected readonly commander = signal<CommanderDetail | null>(null);
  protected readonly loading = signal(true);

  constructor() {
    // Reagiert auf den ueber die Route gebundenen :id-Parameter.
    effect(() => this.load(this.id()));
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
