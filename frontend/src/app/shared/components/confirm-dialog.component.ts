import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

/**
 * Wiederverwendbarer Ja/Nein-Sicherheitsdialog (Glas/Backdrop-Stil wie die uebrigen Modals).
 *
 * Bewusst „dumm": kennt keine Spiel-Logik, fuehrt nichts selbst aus. Der Aufrufer haelt die
 * auszufuehrende Aktion (siehe `ConfirmRequest`) und ruft sie bei `(confirm)` auf, schliesst
 * bei `(dismiss)`. Fuer destruktive Aktionen (Abbrechen/Abreissen) ist `tone="danger"` Standard.
 */
@Component({
  selector: 'app-confirm-dialog',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '(document:keydown.escape)': 'dismiss.emit()' },
  template: `
    <div class="backdrop" (click)="dismiss.emit()">
      <div class="popup glass" (click)="$event.stopPropagation()" role="alertdialog" aria-modal="true">
        <h2 class="title">{{ title() }}</h2>
        <p class="msg">{{ message() }}</p>
        <div class="actions">
          <button class="btn btn-ghost" type="button" (click)="dismiss.emit()">{{ cancelLabel() }}</button>
          <button
            class="btn"
            [class.btn-danger]="tone() === 'danger'"
            [class.btn-primary]="tone() !== 'danger'"
            type="button"
            [disabled]="pending()"
            (click)="confirm.emit()"
          >
            {{ pending() ? '…' : confirmLabel() }}
          </button>
        </div>
      </div>
    </div>
  `,
  styles: [
    `
      .backdrop {
        position: fixed; inset: 0; z-index: 110; display: flex; align-items: center; justify-content: center;
        padding: var(--sp-4); background: rgba(4, 7, 14, 0.72);
        backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
        animation: fade var(--motion-fast) var(--ease-out);
      }
      @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
      .popup {
        position: relative; width: 100%; max-width: 420px;
        border-radius: var(--r-lg); padding: var(--sp-5);
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
        animation: pop var(--motion-base) var(--ease-out);
      }
      @keyframes pop { from { transform: translateY(8px) scale(0.98); opacity: 0; } to { transform: none; opacity: 1; } }
      .title { margin: 0 0 var(--sp-2); font-size: var(--fs-lg); }
      .msg { margin: 0 0 var(--sp-4); color: var(--text-dim); font-size: var(--fs-base); line-height: 1.4; }
      .actions { display: flex; gap: var(--sp-2); justify-content: flex-end; }
      @media (max-width: 480px) {
        .actions { flex-direction: column-reverse; }
        .actions .btn { width: 100%; }
      }
    `,
  ],
})
export class ConfirmDialogComponent {
  readonly title = input('Sicher?');
  readonly message = input('');
  readonly confirmLabel = input('Bestätigen');
  readonly cancelLabel = input('Abbrechen');
  readonly tone = input<'danger' | 'default'>('danger');
  /** In-Flight-Zustand: deaktiviert den Bestaetigen-Button waehrend die Aktion laeuft. */
  readonly pending = input(false);

  readonly confirm = output<void>();
  readonly dismiss = output<void>();
}

/** Vom Aufrufer gehaltene, ausstehende Bestaetigung: Texte + die bei „Ja" auszufuehrende Aktion. */
export interface ConfirmRequest {
  title: string;
  message: string;
  confirmLabel: string;
  action: () => void;
}
