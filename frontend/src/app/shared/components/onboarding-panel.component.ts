import { ChangeDetectionStrategy, Component, computed, inject } from '@angular/core';
import { RouterLink } from '@angular/router';
import { OnboardingService } from '../../core/services/onboarding.service';

/**
 * Gefuehrte Erste-Schritte-Checkliste (FTUE). Zeigt den naechsten Schritt prominent mit
 * Aktion, latcht Fortschritt, ist ausblendbar. Wird oben auf dem Dashboard eingebunden.
 */
@Component({
  selector: 'app-onboarding-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink],
  template: `
    @if (ob.visible()) {
      <section class="ob card">
        <header class="ob-head">
          <div class="ob-heading">
            <span class="ob-spark">✦</span>
            <div>
              <div class="ob-title">Erste Schritte</div>
              <div class="ob-sub mono">{{ ob.completedCount() }} / {{ ob.total() }} erledigt</div>
            </div>
          </div>
          <button class="ob-x" type="button" (click)="ob.dismiss()" title="Ausblenden">✕</button>
        </header>

        <div class="bar"><span class="fill" [style.width.%]="pct()"></span></div>

        <ul class="ob-list">
          @for (r of ob.resolved(); track r.step.id) {
            <li
              class="ob-item"
              [class.done]="r.done"
              [class.next]="!r.done && r.step.id === nextId()"
            >
              <span class="ob-check">{{ r.done ? '✓' : '○' }}</span>
              <div class="ob-main">
                <div class="ob-step-title">{{ r.step.title }}</div>
                @if (!r.done && r.step.id === nextId()) {
                  <div class="ob-hint muted">{{ r.step.hint }}</div>
                  <a
                    class="btn btn-primary btn-sm ob-cta"
                    [routerLink]="r.step.route"
                    (click)="ob.complete(r.step.id)"
                    >{{ r.step.cta }} →</a
                  >
                }
              </div>
            </li>
          }
        </ul>
      </section>
    }
  `,
  styles: [
    `
      .ob {
        position: relative;
        margin-bottom: var(--sp-4);
        border-color: color-mix(in srgb, var(--accent) 30%, transparent);
        background:
          linear-gradient(135deg, var(--accent-soft), var(--surface-1));
        box-shadow: var(--e1), inset 0 0 26px rgba(47, 227, 210, 0.06);
      }
      .ob-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        gap: var(--sp-3);
        margin-bottom: var(--sp-3);
      }
      .ob-heading { display: flex; align-items: center; gap: var(--sp-3); }
      .ob-spark {
        font-size: var(--fs-xl);
        color: var(--accent);
        text-shadow: var(--glow-soft);
        line-height: 1;
      }
      .ob-title {
        font-family: var(--font-display);
        font-size: var(--fs-md);
        font-weight: 600;
        color: #f2f6ff;
        letter-spacing: 0.02em;
      }
      .ob-sub { font-size: var(--fs-xs); color: var(--text-dim); }
      .ob-x {
        flex: 0 0 auto;
        width: 30px;
        height: 30px;
        border-radius: var(--r-sm);
        border: 1px solid var(--border);
        background: transparent;
        color: var(--text-faint);
        cursor: pointer;
        transition: color var(--motion-fast) var(--ease-out), border-color var(--motion-fast) var(--ease-out);
      }
      .ob-x:hover { color: var(--text); border-color: var(--border-strong); }

      .ob .bar { height: 6px; margin-bottom: var(--sp-3); }

      .ob-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--sp-1); }
      .ob-item {
        display: flex;
        align-items: flex-start;
        gap: var(--sp-3);
        padding: var(--sp-2) var(--sp-2);
        border-radius: var(--r-md);
        border: 1px solid transparent;
        transition: background var(--motion-fast) var(--ease-out);
      }
      .ob-item.next {
        background: rgba(255, 255, 255, 0.03);
        border-color: var(--border);
      }
      .ob-check {
        flex: 0 0 auto;
        width: 20px;
        text-align: center;
        font-weight: 700;
        color: var(--text-faint);
      }
      .ob-item.done .ob-check { color: var(--ok); }
      .ob-item.next .ob-check { color: var(--accent); }
      .ob-main { min-width: 0; display: flex; flex-direction: column; gap: var(--sp-2); }
      .ob-step-title { font-size: var(--fs-base); color: var(--text); }
      .ob-item.done .ob-step-title { color: var(--text-dim); text-decoration: line-through; }
      .ob-item.next .ob-step-title { color: var(--accent-strong); font-weight: 600; }
      .ob-hint { font-size: var(--fs-sm); line-height: 1.4; }
      .ob-cta { align-self: flex-start; text-decoration: none; margin-top: 2px; }
    `,
  ],
})
export class OnboardingPanelComponent {
  protected readonly ob = inject(OnboardingService);
  protected readonly nextId = computed(() => this.ob.nextStep()?.id ?? null);
  protected readonly pct = computed(() =>
    this.ob.total() ? (this.ob.completedCount() / this.ob.total()) * 100 : 0,
  );
}
