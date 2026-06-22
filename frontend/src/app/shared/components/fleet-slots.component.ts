import { ChangeDetectionStrategy, Component, computed, input } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { FleetSlots } from '../../core/models/api.models';

/**
 * Kapazitäts-Anzeige der Flotten-Slots (belegt/frei) inkl. Aufschlüsselung nach Aktivität.
 *
 * Zwei Darstellungen über `compact`:
 * - `compact=false` (Standard): prominente Karte mit Belegungsbalken + Aktivitäts-Chips
 *   (Flüge/Expeditionen/Bergbau/Recycling/Patrouillen). Für den Flotten-Screen.
 * - `compact=true`: einzeilige Kurzanzeige „🛰 Flotten-Slots used/max · N frei" für
 *   Dashboard/Expedition/Bergbau.
 *
 * Bei 0 freien Slots wird in Warnfarbe (--warn) markiert. Expeditionen & Bergbau sind normale
 * Flotten und teilen sich denselben Slot-Pool — es gibt keinen separaten Cap.
 */
@Component({
  selector: 'app-fleet-slots',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DecimalPipe],
  template: `
    @if (slots(); as s) {
      @if (compact()) {
        <span class="slots-inline" [class.full]="s.free <= 0" [attr.title]="chipTitle()">
          🛰 Flotten-Slots <span class="mono">{{ s.used }}/{{ s.max }}</span>
          @if (s.free > 0) {
            · {{ s.free }} frei
          } @else {
            · <span class="warn-text">keine frei</span>
          }
        </span>
      } @else {
        <section class="card slots-card" [class.full]="s.free <= 0">
          <div class="slots-head">
            <span class="slots-title">🛰 Flotten-Slots</span>
            <span class="slots-count mono">
              {{ s.used }}/{{ s.max }} belegt ·
              @if (s.free > 0) {
                <span class="free">{{ s.free }} frei</span>
              } @else {
                <span class="warn-text">keine frei</span>
              }
            </span>
          </div>
          <div class="slots-bar" role="img" [attr.aria-label]="s.used + ' von ' + s.max + ' Flotten-Slots belegt'">
            <div class="slots-fill" [class.warn]="s.free <= 0" [style.width.%]="fillPct()"></div>
          </div>
          @if (chips().length) {
            <div class="slots-chips">
              @for (c of chips(); track c.label) {
                <span class="slot-chip">{{ c.label }} <b class="mono">{{ c.count | number: '1.0-0' }}</b></span>
              }
            </div>
          } @else {
            <p class="slots-empty">Aktuell keine Flotte unterwegs.</p>
          }
          @if (limits().length) {
            <div class="slots-limits">
              @for (l of limits(); track l.label) {
                <span class="slot-limit" [class.full]="l.used >= l.cap"
                  [attr.title]="'Max. ' + l.cap + ' ' + l.label + ' gleichzeitig — erhöhbar via ' + l.hint">
                  {{ l.label }}-Limit <b class="mono">{{ l.used }}/{{ l.cap }}</b>
                </span>
              }
            </div>
          }
        </section>
      }
    }
  `,
  styles: [
    `
      .mono { font-variant-numeric: tabular-nums; }
      .warn-text { color: var(--warn); font-weight: 600; }

      /* --- Kompakt (einzeilig) --- */
      .slots-inline { font-size: var(--fs-sm, 0.9em); color: var(--text-dim); }
      .slots-inline.full { color: var(--warn); }

      /* --- Karte (prominent) --- */
      .slots-card { margin-bottom: var(--sp-4); }
      .slots-card.full { border-color: color-mix(in srgb, var(--warn) 50%, transparent); }
      .slots-head {
        display: flex; align-items: baseline; justify-content: space-between;
        gap: var(--sp-3); flex-wrap: wrap; margin-bottom: var(--sp-2);
      }
      .slots-title { font-family: var(--font-display); font-weight: 700; }
      .slots-count { color: var(--text-dim); }
      .slots-count .free { color: var(--accent); font-weight: 600; }
      .slots-bar {
        height: 8px; border-radius: 999px; overflow: hidden;
        background: var(--surface-3, var(--surface-2));
        margin-bottom: var(--sp-3);
      }
      .slots-fill {
        height: 100%; border-radius: 999px;
        background: var(--accent);
        transition: width .2s ease;
      }
      .slots-fill.warn { background: var(--warn); }
      .slots-chips { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
      .slot-chip {
        font-size: var(--fs-xs, 0.8em);
        padding: 2px var(--sp-2);
        border-radius: var(--radius-sm, 6px);
        background: var(--surface-2);
        border: 1px solid var(--border);
        color: var(--text-dim);
      }
      .slot-chip b { color: var(--text); }
      .slots-empty { margin: 0; color: var(--text-faint); font-size: var(--fs-xs, 0.8em); }
      .slots-limits { display: flex; flex-wrap: wrap; gap: var(--sp-2); margin-top: var(--sp-2); }
      .slot-limit {
        font-size: var(--fs-xs, 0.8em); padding: 2px var(--sp-2); border-radius: var(--radius-sm, 6px);
        background: transparent; border: 1px dashed var(--border); color: var(--text-dim);
      }
      .slot-limit b { color: var(--text); }
      .slot-limit.full { border-color: var(--warn); color: var(--warn); }
      .slot-limit.full b { color: var(--warn); }
    `,
  ],
})
export class FleetSlotsComponent {
  readonly slots = input<FleetSlots | null>(null);
  /** Kompakte, einzeilige Darstellung statt der prominenten Karte. */
  readonly compact = input(false);

  protected readonly fillPct = computed(() => {
    const s = this.slots();
    if (!s || s.max <= 0) return 0;
    return Math.min(100, Math.round((s.used / s.max) * 100));
  });

  /** Aktivitäts-Aufschlüsselung als sichtbare Chips (nur Kategorien mit Anzahl > 0). */
  protected readonly chips = computed(() => {
    const s = this.slots();
    if (!s) return [];
    const b = s.breakdown;
    const all = [
      { label: 'Flüge', count: b.flights },
      { label: 'Expeditionen', count: b.expeditions },
      { label: 'Bergbau', count: b.mining },
      { label: 'Recycling', count: b.recycling },
      { label: 'Patrouillen', count: b.patrols },
    ];
    return all.filter((c) => c.count > 0);
  });

  /** Tooltip für die Kompaktzeile: volle Aufschlüsselung. */
  protected readonly chipTitle = computed(() =>
    this.chips()
      .map((c) => `${c.label}: ${c.count}`)
      .join(' · ') || 'Keine Flotte unterwegs',
  );

  /** Per-Kategorie-Limits (belegt/Obergrenze) — zeigt, wie viele Slots Expeditionen/Bergbau
   * sein dürfen (erhöhbar via Astrophysik bzw. Ortung, gedeckelt auf die Gesamt-Flottenzahl). */
  protected readonly limits = computed(() => {
    const s = this.slots();
    if (!s?.caps) return [];
    return [
      { label: 'Expeditionen', used: s.breakdown.expeditions, cap: s.caps.expeditions, hint: 'Astrophysik' },
      { label: 'Bergbau', used: s.breakdown.mining, cap: s.caps.mining, hint: 'Ortung' },
    ];
  });
}
