import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';

export interface TabDef {
  key: string;
  label: string;
  glyph?: string;
  count?: number | null;
}

/**
 * Gemeinsame Reiter-/Kategorie-Leiste (OGame-artig). Nutzt die globalen
 * ``.tab-bar``-Styles, damit alle Screens identische Tabs haben.
 */
@Component({
  selector: 'app-tab-bar',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `
    <div class="tab-bar" role="tablist">
      @for (t of tabs(); track t.key) {
        <button
          type="button"
          class="tab"
          role="tab"
          [class.active]="t.key === active()"
          [attr.aria-selected]="t.key === active()"
          (click)="select.emit(t.key)"
        >
          @if (t.glyph) { <span class="tab-glyph">{{ t.glyph }}</span> }
          {{ t.label }}
          @if (t.count != null) { <span class="tab-count">{{ t.count }}</span> }
        </button>
      }
    </div>
  `,
})
export class TabBarComponent {
  readonly tabs = input.required<TabDef[]>();
  readonly active = input.required<string>();
  readonly select = output<string>();
}
