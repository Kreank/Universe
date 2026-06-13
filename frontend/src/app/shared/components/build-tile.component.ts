import { ChangeDetectionStrategy, Component, input, output } from '@angular/core';
import { IconTileComponent } from './icon-tile.component';
import { CostLineComponent } from './cost-line.component';
import { ResourceCost } from '../../core/models/api.models';

/**
 * Einzelne quadratische Bau-/Item-Kachel (OGame-Stil) — fuer Gebaeude, Forschung,
 * Schiffe, Verteidigung. Aufbau (von oben): grosses Artwork (mit Eck-Badge für Stufe/
 * Bestand) · Name ⓘ · Kosten · Zeit · projizierte Extra-Stats · Aktion.
 *
 * Screen-spezifisches kommt per Content-Projection:
 * - ``[stats]``  — Zusatz-Chips (Energie, Waffentyp …).
 * - ``[action]`` — Button(s)/Badge/Countdown unten.
 * Tiles werden vom Screen in einem ``.tile-grid``-Container angeordnet (global).
 */
@Component({
  selector: 'app-build-tile',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [IconTileComponent, CostLineComponent],
  template: `
    <div class="tile" [class.busy]="busy()" [class.locked]="locked()">
      <button type="button" class="art" (click)="openDetail.emit()" [attr.aria-label]="name() + ' – Details'">
        <app-icon-tile [glyph]="glyph()" [src]="iconSrc()" [size]="76" [variant]="variant()" />
        @if (badge() !== null) {
          <span class="badge-corner" [class.zero]="badge() === 0 || badge() === '0'" [attr.title]="badgeTip()">{{ badge() }}</span>
        }
        <span class="info-dot">ⓘ</span>
      </button>

      <button type="button" class="name" (click)="openDetail.emit()">{{ name() }}</button>

      <div class="stats">
        @if (cost(); as c) {
          <app-cost-line [cost]="c" [available]="available()" />
        }
        @if (timeSeconds() !== null) {
          <span class="muted small time">⏱ {{ fmtTime(timeSeconds()!) }}</span>
        }
        <ng-content select="[stats]" />
      </div>

      <div class="action">
        <ng-content select="[action]" />
      </div>
    </div>
  `,
  styles: [`
    .tile {
      position: relative;
      display: flex; flex-direction: column; align-items: center; gap: var(--sp-2);
      padding: var(--sp-3) var(--sp-2) var(--sp-2);
      border-radius: var(--r-md);
      border: 1px solid var(--border);
      background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0.01));
      height: 100%;
      box-shadow: var(--hairline-top);
      transition: border-color var(--motion-fast) var(--ease-out), box-shadow var(--motion-fast) var(--ease-out), transform var(--motion-fast) var(--ease-out);
    }
    .tile:hover { border-color: var(--border-strong); }
    .tile.locked { opacity: 0.6; }

    /* "In Arbeit": pulsierender Akzent-Ring (nur bei aktivem Bau/Forschung sichtbar). */
    .tile.busy { border-color: var(--accent); }
    .tile.busy::after {
      content: ''; position: absolute; inset: -1px; border-radius: inherit; pointer-events: none;
      box-shadow: 0 0 14px var(--accent-soft), inset 0 0 0 1px var(--accent-dim);
      animation: tileBusy 1.9s ease-in-out infinite;
    }
    @keyframes tileBusy { 0%, 100% { opacity: 0.3; } 50% { opacity: 0.95; } }
    @media (prefers-reduced-motion: reduce) { .tile.busy::after { animation: none; opacity: 0.6; } }

    .art {
      position: relative; padding: 0; border: 0; background: none; cursor: pointer; line-height: 0;
    }
    .art:hover .info-dot { opacity: 1; }
    .badge-corner {
      position: absolute; right: -5px; bottom: -5px;
      min-width: 20px; text-align: center;
      font-size: var(--fs-xs); font-weight: 700; font-family: var(--mono); font-variant-numeric: tabular-nums;
      padding: 0 5px; border-radius: var(--r-sm);
      background: var(--accent); color: #06101e;
      border: 1px solid var(--bg); box-shadow: var(--glow-soft);
    }
    .badge-corner.zero { background: var(--surface-3); color: var(--text-dim); box-shadow: none; }
    .info-dot {
      position: absolute; top: -4px; right: -4px; font-size: var(--fs-sm); color: var(--text-faint);
      opacity: 0.55; transition: opacity var(--motion-fast) var(--ease-out);
    }

    .name {
      padding: 0; border: 0; background: none; cursor: pointer;
      font-weight: 600; font-size: var(--fs-base); color: var(--text); text-align: center; line-height: 1.15;
      max-width: 100%;
      transition: color var(--motion-fast) var(--ease-out);
    }
    .name:hover { color: var(--accent); }

    .stats {
      display: flex; flex-direction: column; align-items: center; gap: var(--sp-1);
      font-size: var(--fs-sm); min-height: 1.2rem;
    }
    .stats .time { white-space: nowrap; }

    .action {
      margin-top: auto; padding-top: var(--sp-1); width: 100%;
      display: flex; flex-direction: column; align-items: stretch; gap: var(--sp-1);
    }
    .muted { color: var(--text-dim); }
    .small { font-size: var(--fs-sm); }
  `],
})
export class BuildTileComponent {
  readonly iconSrc = input<string | null>(null);
  readonly glyph = input<string>('◆');
  readonly name = input.required<string>();
  /** Eck-Badge (Stufe bei Gebaeuden/Forschung, Bestand bei Schiffen). null = aus. */
  readonly badge = input<number | string | null>(null);
  readonly badgeTip = input<string>('');
  readonly cost = input<ResourceCost | null>(null);
  readonly available = input<Partial<Record<string, number>> | null>(null);
  readonly timeSeconds = input<number | null>(null);
  readonly variant = input<'accent' | 'magenta' | 'muted'>('accent');
  readonly busy = input<boolean>(false);
  readonly locked = input<boolean>(false);

  readonly openDetail = output<void>();

  protected fmtTime(s: number): string {
    s = Math.max(0, Math.floor(s));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    if (h > 0) return `${h}h ${m}m`;
    if (m > 0) return `${m}m ${sec}s`;
    return `${sec}s`;
  }
}
