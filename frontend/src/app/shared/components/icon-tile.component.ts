import { ChangeDetectionStrategy, Component, input, signal } from '@angular/core';

/**
 * Konsistente Icon-Kachel fuer Schiffe/Gebaeude/Verteidigung/Ressourcen.
 * Rendert ein echtes Asset-Bild (``src``), faellt bei fehlendem/kaputtem Bild
 * automatisch auf den Emoji-``glyph`` zurueck. Asset-Pfad-Konvention:
 * ``assets/img/<kind>/<key>.png`` (Key = balance.json-Key).
 */
@Component({
  selector: 'app-icon-tile',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="tile" [class]="'tile-' + variant()" [style.--size.px]="size()">
    @if (src() && !broken()) {
      <img class="img" [src]="src()" alt="" loading="lazy" (error)="broken.set(true)" />
    } @else {
      <span class="glyph">{{ glyph() }}</span>
    }
  </span>`,
  styles: [
    `
      .tile {
        position: relative;
        display: inline-flex;
        align-items: center;
        justify-content: center;
        width: var(--size, 44px);
        height: var(--size, 44px);
        border-radius: 10px;
        background: linear-gradient(145deg, rgba(46, 230, 214, 0.14), rgba(13, 22, 41, 0.9));
        border: 1px solid rgba(46, 230, 214, 0.3);
        box-shadow: inset 0 0 14px rgba(46, 230, 214, 0.12);
        flex: 0 0 auto;
        overflow: hidden;
      }
      .img {
        width: 100%;
        height: 100%;
        object-fit: contain;
        padding: 8%;
        filter: drop-shadow(0 1px 3px rgba(0, 0, 0, 0.5));
      }
      .glyph {
        font-size: calc(var(--size, 44px) * 0.52);
        line-height: 1;
        filter: drop-shadow(0 0 4px rgba(46, 230, 214, 0.4));
      }
      .tile-magenta {
        background: linear-gradient(145deg, rgba(255, 64, 160, 0.16), rgba(13, 22, 41, 0.9));
        border-color: rgba(255, 64, 160, 0.35);
        box-shadow: inset 0 0 14px rgba(255, 64, 160, 0.14);
      }
      .tile-muted {
        background: linear-gradient(145deg, rgba(120, 150, 200, 0.12), rgba(13, 22, 41, 0.9));
        border-color: rgba(120, 150, 200, 0.25);
        box-shadow: none;
      }
    `,
  ],
})
export class IconTileComponent {
  readonly glyph = input<string>('◆');
  readonly size = input<number>(44);
  readonly variant = input<'accent' | 'magenta' | 'muted'>('accent');
  /** Optionaler Asset-Pfad; faellt bei Ladefehler auf den Glyph zurueck. */
  readonly src = input<string | null>(null);
  protected readonly broken = signal(false);
}
