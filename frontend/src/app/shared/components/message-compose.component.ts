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
import { BtnIconComponent } from './btn-icon.component';
import { navIcon } from '../../core/models/icon-assets';

/**
 * Kompaktes Overlay zum Verschicken einer Spieler-zu-Spieler-Nachricht (klassisch,
 * async) — fuer Handels-Verhandlungen. Empfaenger + optionaler Betreff/Bezug werden
 * hineingereicht; sendet via ApiService und schliesst nach Erfolg.
 */
@Component({
  selector: 'app-message-compose',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, BtnIconComponent],
  host: { '(document:keydown.escape)': 'close.emit()' },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup glass" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>
        <header class="head">
          <h2><app-btn-icon [src]="navIcon('mail')" glyph="✉" [size]="16" /> Nachricht an {{ toName() }}</h2>
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
<app-btn-icon [src]="navIcon('mail')" glyph="✉" [size]="18" /> {{ sending() ? 'Sende…' : 'Senden' }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .backdrop {
        position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center;
        padding: var(--sp-4); background: rgba(4, 7, 14, 0.72);
        backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
        animation: fade var(--motion-fast) var(--ease-out);
      }
      @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
      /* .glass (global) liefert Background/Blur/Border/Elevation; hier nur Layout + Signatur-Ecke. */
      .popup {
        position: relative; width: 100%; max-width: 520px; max-height: 88vh; overflow-y: auto;
        border-radius: var(--r-lg); padding: var(--sp-5);
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
        animation: pop var(--motion-base) var(--ease-out);
      }
      @keyframes pop { from { transform: translateY(8px) scale(0.98); opacity: 0; } to { transform: none; opacity: 1; } }
      .x {
        position: absolute; top: var(--sp-2); right: var(--sp-2); width: 32px; height: 32px; border-radius: var(--r-sm);
        background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text-dim);
        cursor: pointer; display: flex; align-items: center; justify-content: center;
        transition: color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .x:hover { color: var(--text); background: rgba(255,255,255,0.1); }
      .head h2 { margin: 0 var(--sp-8) var(--sp-3) 0; font-size: var(--fs-lg); }
      .field { display: flex; flex-direction: column; gap: var(--sp-1); margin-bottom: var(--sp-2); }
      .field label { font-family: var(--font-display); font-size: var(--fs-xs); letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-dim); }
      .field input, .field textarea { min-height: 32px; width: 100%; resize: vertical; }
      textarea {
        font-family: inherit; font-size: var(--fs-base); color: var(--text);
        background: rgba(0, 0, 0, 0.28); border: 1px solid var(--border); border-radius: var(--r-md);
        padding: var(--sp-3); line-height: 1.5;
        transition: border-color var(--motion-fast) var(--ease-out), box-shadow var(--motion-fast) var(--ease-out);
      }
      textarea:focus { outline: none; border-color: var(--accent); box-shadow: var(--glow-soft); }
      textarea::placeholder { color: var(--text-faint); }
      .actions { margin-top: var(--sp-2); }
      .actions .btn { width: 100%; }

      @media (max-width: 560px) {
        .backdrop { padding: var(--sp-2); }
        .popup { max-width: 100%; max-height: 94vh; padding: var(--sp-4); }
      }
    `,
  ],
})
export class MessageComposeComponent {
  private readonly api = inject(ApiService);
  private readonly notify = inject(NotificationService);

  /** Asset-Pfad-Helfer fuers Template (Glyph-Fallback via app-btn-icon). */
  protected readonly navIcon = navIcon;

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
