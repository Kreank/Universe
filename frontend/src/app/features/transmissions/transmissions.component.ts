import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import { Commander, DecisionChoice, Transmission } from '../../core/models/api.models';
import { transmissionStyles } from './transmission.styles';

@Component({
  selector: 'app-transmissions',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe],
  template: `
    <div class="head">
      <div>
        <h1>Postfach · Funksprueche</h1>
        <p class="muted sub">Eingehende Transmissionen und Crew-Forderungen.</p>
      </div>
      <div class="filters">
        <button class="btn btn-sm" [class.btn-primary]="!onlyUnread()" (click)="onlyUnread.set(false)">Alle</button>
        <button class="btn btn-sm" [class.btn-primary]="onlyUnread()" (click)="onlyUnread.set(true)">
          Ungelesen ({{ state.unreadTransmissions() }})
        </button>
      </div>
    </div>

    @if (visible().length) {
      <div class="grid list">
        @for (t of visible(); track t.id) {
          <article class="card msg" [class.unread]="!t.read" [class.demand]="t.requires_decision">
            <div class="msg-head">
              <span class="type-glyph">{{ typeGlyph(t) }}</span>
              <div class="msg-meta">
                <h3>{{ t.subject }}</h3>
                <span class="faint small">
                  {{ commanderName(t.commander_id) }} · {{ t.created_at | date: 'short' }}
                </span>
              </div>
              @if (!t.read) {
                <span class="dot-new" title="ungelesen"></span>
              }
            </div>

            <p class="body">{{ t.body }}</p>

            @if (t.requires_decision) {
              <div class="decision">
                <span class="muted small">Forderung — deine Entscheidung:</span>
                <div class="dec-buttons">
                  <button
                    class="btn btn-sm btn-primary"
                    [disabled]="deciding() === t.id"
                    (click)="decide(t, 'accept')"
                  >Erfuellen</button>
                  <button
                    class="btn btn-sm btn-ghost"
                    [disabled]="deciding() === t.id"
                    (click)="decide(t, 'negotiate')"
                  >Verhandeln</button>
                  <button
                    class="btn btn-sm btn-danger"
                    [disabled]="deciding() === t.id"
                    (click)="decide(t, 'reject')"
                  >Ablehnen</button>
                </div>
              </div>
            } @else if (!t.read) {
              <button class="btn btn-sm btn-ghost mark" (click)="markRead(t)">Als gelesen markieren</button>
            }
          </article>
        }
      </div>
    } @else {
      <p class="empty-state">
        {{ onlyUnread() ? 'Keine ungelesenen Funksprueche.' : 'Funkstille. Keine Transmissionen.' }}
      </p>
    }
  `,
  styles: [transmissionStyles],
})
export class TransmissionsComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  protected readonly onlyUnread = signal(false);
  protected readonly deciding = signal<string | null>(null);

  private readonly commanderMap = computed(
    () => new Map<string, Commander>(this.state.commanders().map((c) => [c.id, c])),
  );

  protected readonly visible = computed(() => {
    const all = [...this.state.transmissions()].sort(
      (a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime(),
    );
    return this.onlyUnread() ? all.filter((t) => !t.read) : all;
  });

  constructor() {
    void this.state.reloadTransmissions();
  }

  decide(t: Transmission, choice: DecisionChoice): void {
    this.deciding.set(t.id);
    this.api.decideTransmission(t.id, choice).subscribe({
      next: (res) => {
        this.deciding.set(null);
        const sign = res.morale_delta > 0 ? '+' : '';
        this.notify.success('Entscheidung getroffen', `${res.message} (Moral ${sign}${res.morale_delta})`);
        this.state.upsertTransmission({ ...t, read: true, requires_decision: false });
        void this.state.reloadCommanders();
      },
      error: (err) => {
        this.deciding.set(null);
        this.notify.warning('Fehler', err?.error?.detail ?? 'Entscheidung fehlgeschlagen.');
      },
    });
  }

  markRead(t: Transmission): void {
    this.api.markTransmissionRead(t.id).subscribe({
      next: () => this.state.upsertTransmission({ ...t, read: true }),
      error: () => this.state.upsertTransmission({ ...t, read: true }),
    });
  }

  commanderName(id: string | null): string {
    if (!id) {
      return 'Kommandostab';
    }
    return this.commanderMap().get(id)?.name ?? 'Unbekannter Commander';
  }

  typeGlyph(t: Transmission): string {
    if (t.requires_decision) {
      return '⚠️';
    }
    switch (t.type) {
      case 'combat_report':
        return '⚔️';
      case 'victory':
        return '🏆';
      case 'defeat':
        return '💥';
      case 'lore':
        return '📖';
      default:
        return '📡';
    }
  }
}
