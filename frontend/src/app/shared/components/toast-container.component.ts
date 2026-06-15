import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { NotificationService } from '../../core/services/notification.service';
import { BtnIconComponent } from './btn-icon.component';
import { statusIcon } from '../../core/models/icon-assets';

/**
 * Globaler Toast-Stack. Eingehende Funksprueche bekommen eine eigene
 * "Eingehende Transmission"-Animation (Doku 11 §3).
 */
@Component({
  selector: 'app-toast-container',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, BtnIconComponent],
  template: `
    <div class="toast-stack" aria-live="polite">
      @for (t of notify.toasts(); track t.id) {
        <div class="toast" [class]="'toast-' + t.kind">
          <div class="toast-head">
            <span class="toast-title">
              @if (t.kind === 'transmission') {
                <span class="pulse"><app-btn-icon [src]="statusIcon('transmission_unread')" glyph="📡" [size]="16" /></span>
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
        top: var(--sp-4);
        right: var(--sp-4);
        z-index: 1000;
        display: flex;
        flex-direction: column;
        gap: var(--sp-2);
        width: min(360px, calc(100vw - var(--sp-8)));
      }
      .toast {
        background: linear-gradient(160deg, var(--surface-2), var(--surface-1));
        border: 1px solid var(--border-strong);
        border-left: 3px solid var(--accent);
        border-radius: var(--r-md);
        padding: var(--sp-3);
        box-shadow: var(--e2), var(--hairline-top);
        animation: slide-in var(--motion-slow) var(--ease-out);
      }
      .toast-success {
        border-left-color: var(--ok);
      }
      .toast-warning {
        border-left-color: var(--danger);
        box-shadow: 0 0 22px rgba(255, 77, 125, 0.3);
      }
      .toast-transmission {
        border-left-color: var(--accent);
        animation:
          slide-in var(--motion-slow) var(--ease-out),
          glow-pulse 1.4s ease infinite;
      }
      .toast-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--sp-2);
      }
      .toast-title {
        font-family: var(--font-display);
        font-weight: 600;
        font-size: var(--fs-base);
        display: inline-flex;
        align-items: center;
        gap: var(--sp-1);
      }
      .toast-body {
        color: var(--text-dim);
        font-size: var(--fs-sm);
        margin-top: var(--sp-1);
      }
      .toast-link {
        display: inline-block;
        margin-top: var(--sp-1);
        font-size: var(--fs-sm);
      }
      .x {
        background: none;
        border: none;
        color: var(--text-faint);
        cursor: pointer;
        font-size: var(--fs-sm);
        min-height: auto;
        padding: 0;
        transition: color var(--motion-fast) var(--ease-out);
      }
      .x:hover {
        color: var(--text);
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
          box-shadow: var(--e2), var(--hairline-top);
        }
        50% {
          box-shadow: var(--glow-soft);
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

  /** Asset-Pfad-Helfer fuers Template (Glyph-Fallback via app-btn-icon). */
  protected readonly statusIcon = statusIcon;
}
