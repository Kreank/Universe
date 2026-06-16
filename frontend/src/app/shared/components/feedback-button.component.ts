import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { NotificationService } from '../../core/services/notification.service';
import { FeedbackCategory } from '../../core/models/api.models';

/**
 * Global immer sichtbarer Feedback-Knopf (unten rechts) fuer die Testphase.
 *
 * Klick oeffnet ein kurzes Modal: erklaert knapp Zweck + was Tester erwarten muessen und
 * nimmt eine Meldung (Bug / Idee / Sonstiges) entgegen. Das Feedback geht an POST /api/feedback
 * (DB + Telegram-Push an den Entwickler). Nur fuer eingeloggte Spieler sichtbar.
 */
@Component({
  selector: 'app-feedback-button',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule],
  host: { '(document:keydown.escape)': 'close()' },
  template: `
    @if (auth.isAuthenticated()) {
      <button
        class="fab"
        type="button"
        (click)="open()"
        aria-label="Feedback geben"
        title="Feedback / Bug melden"
      >
        <span class="fab-icon">📣</span>
        <span class="fab-label">Feedback</span>
      </button>
    }

    @if (showModal()) {
      <div class="backdrop" (click)="close()">
        <div
          class="popup glass"
          (click)="$event.stopPropagation()"
          role="dialog"
          aria-modal="true"
          aria-labelledby="fb-title"
        >
          <button class="x" type="button" (click)="close()" aria-label="Schliessen">✕</button>

          @if (!done()) {
            <h2 class="title" id="fb-title">📣 Feedback &amp; Bug-Melder</h2>

            <p class="lead">
              Danke, dass du mittestest! Hiermit meldest du Bugs, Ideen oder was dir auffällt –
              direkt an mich.
            </p>

            <ul class="hints">
              <li>⚠️ Frühe Test-Version: Fehler, Aussetzer &amp; <b>Spielstand-Resets</b> sind möglich.</li>
              <li>💾 Behalte nichts „für immer" – noch wird viel umgebaut.</li>
            </ul>

            <div class="ask">
              <b>Damit ich's schnell fixen kann, kurz:</b>
              <span>Was wolltest du tun? · Was ist passiert? · (bei Bug) hilft ein Screenshot per Telegram.</span>
            </div>

            <div class="cats">
              @for (c of categories; track c.key) {
                <button
                  type="button"
                  class="cat"
                  [class.active]="category() === c.key"
                  (click)="category.set(c.key)"
                >
                  {{ c.icon }} {{ c.label }}
                </button>
              }
            </div>

            <textarea
              class="ta"
              [(ngModel)]="message"
              rows="5"
              maxlength="4000"
              [placeholder]="placeholder()"
              autofocus
            ></textarea>

            <div class="actions">
              <button class="btn btn-ghost" type="button" (click)="close()">Abbrechen</button>
              <button
                class="btn btn-primary"
                type="button"
                [disabled]="pending() || message().trim().length < 3"
                (click)="submit()"
              >
                {{ pending() ? 'Senden…' : 'Absenden' }}
              </button>
            </div>
          } @else {
            <div class="thanks">
              <div class="check">✅</div>
              <h2 class="title">Danke!</h2>
              <p class="lead">Deine Meldung ist angekommen. Du kannst jederzeit weiter melden.</p>
              <button class="btn btn-primary" type="button" (click)="close()">Schließen</button>
            </div>
          }
        </div>
      </div>
    }
  `,
  styles: [
    `
      .fab {
        position: fixed;
        right: var(--sp-4);
        bottom: var(--sp-4);
        z-index: 900;
        display: inline-flex;
        align-items: center;
        gap: var(--sp-1);
        padding: var(--sp-2) var(--sp-3);
        border-radius: 999px;
        border: 1px solid var(--border-strong);
        background: linear-gradient(160deg, var(--surface-2), var(--surface-1));
        color: var(--text);
        font-family: var(--font-display);
        font-size: var(--fs-sm);
        font-weight: 600;
        cursor: pointer;
        box-shadow: var(--e2), var(--hairline-top);
        transition:
          transform var(--motion-fast) var(--ease-out),
          box-shadow var(--motion-fast) var(--ease-out),
          border-color var(--motion-fast) var(--ease-out);
      }
      .fab:hover {
        transform: translateY(-2px);
        border-color: var(--accent);
        box-shadow: var(--glow-soft);
      }
      .fab-icon {
        font-size: 1.1em;
      }
      /* Mobile: ueber der fixen Bottom-Tab-Bar (~56px + Safe-Area) parken,
         damit der Button das „Mehr"/Menue-Item der Leiste nicht verdeckt. */
      @media (max-width: 900px) {
        .fab {
          bottom: calc(56px + env(safe-area-inset-bottom) + var(--sp-3));
        }
      }
      @media (max-width: 560px) {
        .fab-label {
          display: none;
        }
        .fab {
          padding: var(--sp-2);
        }
      }

      .backdrop {
        position: fixed;
        inset: 0;
        z-index: 1100;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: var(--sp-4);
        background: rgba(4, 7, 14, 0.72);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
        animation: fade var(--motion-fast) var(--ease-out);
      }
      @keyframes fade {
        from {
          opacity: 0;
        }
        to {
          opacity: 1;
        }
      }
      .popup {
        position: relative;
        width: 100%;
        max-width: 460px;
        max-height: calc(100vh - var(--sp-8));
        overflow-y: auto;
        border-radius: var(--r-lg);
        padding: var(--sp-5);
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
        animation: pop var(--motion-base) var(--ease-out);
      }
      @keyframes pop {
        from {
          transform: translateY(8px) scale(0.98);
          opacity: 0;
        }
        to {
          transform: none;
          opacity: 1;
        }
      }
      .x {
        position: absolute;
        top: var(--sp-3);
        right: var(--sp-3);
        background: none;
        border: none;
        color: var(--text-faint);
        cursor: pointer;
        font-size: var(--fs-base);
        line-height: 1;
        min-height: auto;
        padding: var(--sp-1);
      }
      .x:hover {
        color: var(--text);
      }
      .title {
        margin: 0 0 var(--sp-2);
        font-size: var(--fs-lg);
        padding-right: var(--sp-5);
      }
      .lead {
        margin: 0 0 var(--sp-3);
        color: var(--text-dim);
        font-size: var(--fs-base);
        line-height: 1.45;
      }
      .hints {
        margin: 0 0 var(--sp-3);
        padding-left: var(--sp-4);
        color: var(--text-dim);
        font-size: var(--fs-sm);
        line-height: 1.5;
      }
      .hints li {
        margin-bottom: 2px;
      }
      .ask {
        display: flex;
        flex-direction: column;
        gap: 2px;
        margin-bottom: var(--sp-3);
        padding: var(--sp-2) var(--sp-3);
        border-left: 3px solid var(--accent);
        border-radius: var(--r-sm);
        background: rgba(255, 255, 255, 0.03);
        font-size: var(--fs-sm);
      }
      .ask span {
        color: var(--text-dim);
      }
      .cats {
        display: flex;
        gap: var(--sp-2);
        margin-bottom: var(--sp-3);
        flex-wrap: wrap;
      }
      .cat {
        flex: 1 1 auto;
        padding: var(--sp-2);
        border-radius: var(--r-md);
        border: 1px solid var(--border-strong);
        background: var(--surface-1);
        color: var(--text-dim);
        font-size: var(--fs-sm);
        cursor: pointer;
        transition:
          border-color var(--motion-fast) var(--ease-out),
          color var(--motion-fast) var(--ease-out);
      }
      .cat:hover {
        color: var(--text);
      }
      .cat.active {
        border-color: var(--accent);
        color: var(--text);
        background: linear-gradient(160deg, var(--surface-2), var(--surface-1));
      }
      .ta {
        width: 100%;
        resize: vertical;
        padding: var(--sp-3);
        border-radius: var(--r-md);
        border: 1px solid var(--border-strong);
        background: var(--surface-1);
        color: var(--text);
        font-family: inherit;
        font-size: var(--fs-base);
        line-height: 1.4;
        margin-bottom: var(--sp-4);
      }
      .ta:focus {
        outline: none;
        border-color: var(--accent);
      }
      .actions {
        display: flex;
        gap: var(--sp-2);
        justify-content: flex-end;
      }
      .thanks {
        text-align: center;
        padding: var(--sp-3) 0;
      }
      .check {
        font-size: 2.4rem;
        margin-bottom: var(--sp-2);
      }
      @media (max-width: 480px) {
        .actions {
          flex-direction: column-reverse;
        }
        .actions .btn {
          width: 100%;
        }
      }
    `,
  ],
})
export class FeedbackButtonComponent {
  protected readonly auth = inject(AuthService);
  private readonly api = inject(ApiService);
  private readonly notify = inject(NotificationService);
  private readonly router = inject(Router);

  protected readonly showModal = signal(false);
  protected readonly pending = signal(false);
  protected readonly done = signal(false);
  protected readonly category = signal<FeedbackCategory>('bug');
  protected readonly message = signal('');

  protected readonly categories: { key: FeedbackCategory; icon: string; label: string }[] = [
    { key: 'bug', icon: '🐞', label: 'Bug' },
    { key: 'idea', icon: '💡', label: 'Idee' },
    { key: 'other', icon: '💬', label: 'Sonstiges' },
  ];

  protected placeholder(): string {
    switch (this.category()) {
      case 'bug':
        return 'Was wolltest du tun und was ist stattdessen passiert? (z. B. „Flotte abschicken → Seite hängt")';
      case 'idea':
        return 'Welche Idee hast du? Was würde das Spiel für dich besser machen?';
      default:
        return 'Schreib einfach drauflos – alles, was dir auffällt.';
    }
  }

  protected open(): void {
    this.done.set(false);
    this.message.set('');
    this.category.set('bug');
    this.showModal.set(true);
  }

  protected close(): void {
    this.showModal.set(false);
  }

  protected submit(): void {
    const text = this.message().trim();
    if (text.length < 3 || this.pending()) {
      return;
    }
    this.pending.set(true);
    this.api
      .submitFeedback({ category: this.category(), message: text, page: this.router.url })
      .subscribe({
        next: () => {
          this.pending.set(false);
          this.done.set(true);
        },
        error: () => {
          this.pending.set(false);
          this.notify.warning(
            'Senden fehlgeschlagen',
            'Bitte versuche es gleich nochmal – dein Text bleibt erhalten.',
          );
        },
      });
  }
}
