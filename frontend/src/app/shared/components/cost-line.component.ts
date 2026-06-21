import { ChangeDetectionStrategy, Component, computed, input, signal } from '@angular/core';
import { ResourceCost } from '../../core/models/api.models';
import { ShortNumberPipe } from '../pipes/short-number.pipe';
import { RESOURCE_META } from '../../core/models/display';

/**
 * Zeigt eine Ressourcen-Kostenzeile mit den echten Rohstoff-Icons (assets/img/resources/*.png).
 * Faellt auf das Emoji-Glyph zurueck, falls ein Bild fehlt. Werte, fuer die der Spieler zu wenig
 * hat, werden magenta markiert (verglichen mit den uebergebenen Bestaenden).
 */
@Component({
  selector: 'app-cost-line',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ShortNumberPipe],
  template: `
    <span class="cost-line">
      @for (c of items(); track c.key) {
        @if (c.value > 0) {
          <span [class.lack]="c.lack" [class.ok]="!c.lack" class="tip" [attr.data-tip]="c.tip">
            @if (broken().has(c.key)) {
              {{ c.glyph }}
            } @else {
              <img class="res-ico" [src]="c.img" alt="" loading="lazy" (error)="markBroken(c.key)" />
            }
            {{ c.value | shortNumber }}
          </span>
        }
      }
    </span>
  `,
  styles: [
    `
      .res-ico { width: 1.05em; height: 1.05em; vertical-align: -0.18em; object-fit: contain; }
    `,
  ],
})
export class CostLineComponent {
  readonly cost = input.required<ResourceCost>();
  /** Aktuelle Bestaende zum Markieren von Engpaessen (optional). */
  readonly available = input<Partial<Record<string, number>> | null>(null);

  protected readonly broken = signal<Set<string>>(new Set());

  markBroken(key: string): void {
    this.broken.update((s) => new Set(s).add(key));
  }

  readonly items = computed(() => {
    const cost = this.cost();
    const avail = this.available();
    // Exoten (antimatter/dark_matter) NACH deuterium: da nur Werte > 0 gerendert werden,
    // erscheinen sie automatisch nur bei Bauobjekten/Forschungen, die sie wirklich kosten.
    const keys: (keyof ResourceCost)[] = ['metal', 'crystal', 'deuterium', 'antimatter', 'dark_matter'];
    return keys.map((key) => {
      const value = cost[key] ?? 0;
      const have = avail ? (avail[key] ?? 0) : Infinity;
      const lack = value > have;
      return {
        key,
        value,
        glyph: RESOURCE_META[key].glyph,
        img: `assets/img/resources/${key}.png`,
        lack,
        tip: `${RESOURCE_META[key].label}: ${Math.round(value)}`,
      };
    });
  });
}
