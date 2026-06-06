import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NotificationService } from '../../core/services/notification.service';

/**
 * Globaler Toast-Stack. Eingehende Funksprueche bekommen eine eigene
 * "Eingehende Transmission"-Animation (Doku 11 §3).
 */
@Component({
  selector: 'app-toast-container',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    <div class="toast-stack" aria-live="polite">
      @for (t of notify.toasts(); track t.id) {
        <div class="toast" [class]="'toast-' + t.kind">
          <div class="toast-head">
            <span class="toast-title">
              @if (t.kind === 'transmission') {
                <span class="pulse">📡</span>
              }
              {{ t.title }}
            </span>
            <button class="x" type="button" (click)="notify.dismiss(t.id)" aria-label="Schliessen">
              ✕
            </button>
          </div>
          <div class="toast-body">{{ t.message }}</div>
          @if (t.transmissionId) {
            <a class="toast-link" routerLink="/transmissions" (click)="notify.dismiss(t.id)"
              >Funkspruch oeffnen →</a
            >
          }
        </div>
      }
    </div>
  `,
  styles: [
    `
      .toast-stack {
        position: fixed;
        top: 1rem;
        right: 1rem;
        z-index: 1000;
        display: flex;
        flex-direction: column;
        gap: 0.6rem;
        width: min(360px, calc(100vw - 2rem));
      }
      .toast {
        background: linear-gradient(160deg, var(--surface-2), var(--surface));
        border: 1px solid var(--border-strong);
        border-left: 3px solid var(--accent);
        border-radius: var(--radius-sm);
        padding: 0.7rem 0.8rem;
        box-shadow: var(--shadow);
        animation: slide-in 0.28s ease;
      }
      .toast-success {
        border-left-color: var(--ok);
      }
      .toast-warning {
        border-left-color: var(--magenta);
        box-shadow: 0 0 22px rgba(255, 64, 160, 0.3);
      }
      .toast-transmission {
        border-left-color: var(--accent);
        animation:
          slide-in 0.28s ease,
          glow-pulse 1.4s ease infinite;
      }
      .toast-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: 0.5rem;
      }
      .toast-title {
        font-weight: 600;
        font-size: 0.9rem;
        display: inline-flex;
        align-items: center;
        gap: 0.4rem;
      }
      .toast-body {
        color: var(--text-dim);
        font-size: 0.84rem;
        margin-top: 0.2rem;
      }
      .toast-link {
        display: inline-block;
        margin-top: 0.4rem;
        font-size: 0.8rem;
      }
      .x {
        background: none;
        border: none;
        color: var(--text-faint);
        cursor: pointer;
        font-size: 0.85rem;
        min-height: auto;
        padding: 0;
      }
      .pulse {
        animation: blink 0.9s ease infinite;
      }
      @keyframes slide-in {
        from {
          transform: translateX(40px);
          opacity: 0;
        }
        to {
          transform: translateX(0);
          opacity: 1;
        }
      }
      @keyframes glow-pulse {
        0%,
        100% {
          box-shadow: var(--shadow);
        }
        50% {
          box-shadow: 0 0 22px rgba(46, 230, 214, 0.45);
        }
      }
      @keyframes blink {
        0%,
        100% {
          opacity: 1;
        }
        50% {
          opacity: 0.3;
        }
      }
    `,
  ],
})
export class ToastContainerComponent {
  protected readonly notify = inject(NotificationService);
}
