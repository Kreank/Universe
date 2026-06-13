import { ChangeDetectionStrategy, Component, Input } from '@angular/core';

/**
 * Leerzustand mit cinematic Sci-Fi-Illustration (assets/img/empty/<art>.png) + projiziertem
 * Hinweistext/Aktion. Folgt der Recherche „Empty States als Handlungsfuehrung".
 * Faellt bei fehlendem Bild leise auf reinen Text zurueck.
 */
@Component({
  selector: 'app-empty-state',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="es">
      <img class="es-art" [src]="'assets/img/empty/' + art + '.png'" alt="" (error)="hide($event)" />
      <div class="es-body"><ng-content /></div>
    </div>
  `,
  styles: [
    `
      .es {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: var(--sp-3);
        text-align: center;
        color: var(--text-dim);
        padding: var(--sp-8) var(--sp-4);
      }
      .es-art {
        width: 128px;
        height: 128px;
        object-fit: contain;
        opacity: 0.85;
        filter: drop-shadow(0 6px 24px rgba(47, 227, 210, 0.12));
        animation: es-float 6s var(--ease-out) infinite;
      }
      @keyframes es-float {
        0%, 100% { transform: translateY(0); }
        50% { transform: translateY(-6px); }
      }
      .es-body { font-size: var(--fs-base); line-height: 1.5; max-width: 42ch; }
      @media (prefers-reduced-motion: reduce) {
        .es-art { animation: none; }
      }
    `,
  ],
})
export class EmptyStateComponent {
  /** Dateiname ohne Endung in assets/img/empty/ (empty_fleet, empty_inbox, …). */
  @Input() art = 'empty_generic';

  hide(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
}
