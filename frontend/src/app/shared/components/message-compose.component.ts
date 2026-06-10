import {
  ChangeDetectionStrategy,
  Component,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { NotificationService } from '../../core/services/notification.service';

/**
 * Kompaktes Overlay zum Verschicken einer Spieler-zu-Spieler-Nachricht (klassisch,
 * async) — fuer Handels-Verhandlungen. Empfaenger + optionaler Betreff/Bezug werden
 * hineingereicht; sendet via ApiService und schliesst nach Erfolg.
 */
@Component({
  selector: 'app-message-compose',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule],
  host: { '(document:keydown.escape)': 'close.emit()' },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>
        <header class="head">
          <h2>✉ Nachricht an {{ toName() }}</h2>
        </header>
        <div class="field">
          <label>Betreff</label>
          <input type="text" [ngModel]="subject()" (ngModelChange)="subject.set($event)" maxlength="140"
            placeholder="z. B. Handelsangebot: Kristall gegen Deuterium" />
        </div>
        <div class="field">
          <label>Nachricht</label>
          <textarea rows="6" [ngModel]="text()" (ngModelChange)="text.set($event)" maxlength="4000"
            placeholder="Schlage einen Kurs vor und sprich die Lieferung ab…"></textarea>
        </div>
        <div class="actions">
          <button class="btn btn-primary" type="button" [disabled]="!canSend() || sending()" (click)="send()">
            {{ sending() ? 'Sende…' : '✉ Senden' }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .backdrop {
        position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center;
        padding: 1rem; background: rgba(4, 7, 14, 0.72); backdrop-filter: blur(4px);
      }
      .popup {
        position: relative; width: 100%; max-width: 520px; max-height: 88vh; overflow-y: auto;
        background: linear-gradient(160deg, var(--surface-2), var(--surface));
        border: 1px solid var(--border-strong); border-radius: var(--radius);
        box-shadow: var(--shadow), var(--glow); padding: 1.1rem 1.2rem 1.2rem;
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
      }
      .x {
        position: absolute; top: 0.5rem; right: 0.6rem; width: 30px; height: 30px; border-radius: 8px;
        background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text-dim);
        cursor: pointer; display: flex; align-items: center; justify-content: center;
      }
      .x:hover { color: var(--text); background: rgba(255,255,255,0.1); }
      .head h2 { margin: 0 2rem 0.8rem 0; font-size: 1.1rem; }
      .field { display: flex; flex-direction: column; gap: 0.25rem; margin-bottom: 0.7rem; }
      .field label { font-size: 0.74rem; color: var(--text-dim); }
      .field input, .field textarea { min-height: 32px; width: 100%; resize: vertical; }
      .actions { margin-top: 0.6rem; }
      .actions .btn { width: 100%; }
    `,
  ],
})
export class MessageComposeComponent {
  private readonly api = inject(ApiService);
  private readonly notify = inject(NotificationService);

  readonly toPlayerId = input.required<string>();
  readonly toName = input<string>('Spieler');
  readonly initialSubject = input<string>('');
  readonly replyTo = input<string | null>(null);

  readonly close = output<void>();
  readonly sent = output<void>();

  protected readonly subject = signal('');
  protected readonly text = signal('');
  protected readonly sending = signal(false);

  constructor() {
    queueMicrotask(() => this.subject.set(this.initialSubject()));
  }

  protected canSend(): boolean {
    return this.text().trim().length > 0;
  }

  send(): void {
    if (!this.canSend() || this.sending()) {
      return;
    }
    this.sending.set(true);
    this.api
      .sendMessage({
        to_player_id: this.toPlayerId(),
        subject: this.subject().trim(),
        body: this.text().trim(),
        reply_to: this.replyTo(),
      })
      .subscribe({
        next: () => {
          this.sending.set(false);
          this.notify.success('Nachricht gesendet', `An ${this.toName()} verschickt.`);
          this.sent.emit();
          this.close.emit();
        },
        error: (err) => {
          this.sending.set(false);
          this.notify.warning('Senden fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
        },
      });
  }
}
