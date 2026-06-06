import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { ResourceCost } from '../../core/models/api.models';
import { ShortNumberPipe } from '../pipes/short-number.pipe';
import { RESOURCE_META } from '../../core/models/display';

/**
 * Zeigt eine Ressourcen-Kostenzeile. Werte, fuer die der Spieler zu wenig hat,
 * werden magenta markiert (verglichen mit den uebergebenen Bestaenden).
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
            {{ c.glyph }} {{ c.value | shortNumber }}
          </span>
        }
      }
    </span>
  `,
})
export class CostLineComponent {
  readonly cost = input.required<ResourceCost>();
  /** Aktuelle Bestaende zum Markieren von Engpaessen (optional). */
  readonly available = input<Partial<Record<string, number>> | null>(null);

  readonly items = computed(() => {
    const cost = this.cost();
    const avail = this.available();
    const keys: (keyof ResourceCost)[] = ['metal', 'crystal', 'deuterium'];
    return keys.map((key) => {
      const value = cost[key] ?? 0;
      const have = avail ? (avail[key] ?? 0) : Infinity;
      const lack = value > have;
      return {
        key,
        value,
        glyph: RESOURCE_META[key].glyph,
        lack,
        tip: `${RESOURCE_META[key].label}: ${Math.round(value)}`,
      };
    });
  });
}
