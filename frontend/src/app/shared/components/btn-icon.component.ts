import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';

/**
 * Schlankes Inline-Icon fuer Buttons/Chips: rendert ein echtes Asset-Bild
 * (``src``) und faellt bei fehlendem/kaputtem Bild automatisch auf den
 * Emoji-``glyph`` zurueck. Anders als ``app-icon-tile`` OHNE Kachel-Rahmen —
 * fuegt sich nahtlos als fuehrendes Symbol in einen Button ein.
 *
 * Verwendung: ``<app-btn-icon [src]="missionIcon('attack')" glyph="⚔" /> Angreifen``
 */
@Component({
  selector: 'app-btn-icon',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `@if (src() && !broken()) {
      <img class="bi" [src]="src()" alt="" [style.--bi.px]="size()" (error)="broken.set(true)" />
    } @else {
      <span class="bi-g" [style.font-size.px]="size()">{{ glyph() }}</span>
    }`,
  styles: [
    `
      :host { display: inline-flex; align-items: center; flex: 0 0 auto; }
      .bi { width: var(--bi, 16px); height: var(--bi, 16px); object-fit: contain; }
      .bi-g { line-height: 1; }
    `,
  ],
})
export class BtnIconComponent {
  /** Asset-Pfad; ``null`` => sofort Glyph. */
  readonly src = input<string | null>(null);
  readonly glyph = input<string>('◆');
  readonly size = input<number>(16);
  protected readonly broken = signal(false);
}
