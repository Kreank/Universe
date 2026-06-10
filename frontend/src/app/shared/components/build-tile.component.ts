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
      display: flex; flex-direction: column; align-items: center; gap: 0.45rem;
      padding: 0.7rem 0.6rem 0.6rem;
      border-radius: var(--radius-sm);
      border: 1px solid var(--border);
      background: linear-gradient(180deg, rgba(255,255,255,0.025), rgba(255,255,255,0.01));
      height: 100%;
      transition: border-color 0.12s ease, box-shadow 0.12s ease, transform 0.08s ease;
    }
    .tile:hover { border-color: var(--border-strong); }
    .tile.busy { border-color: var(--accent-dim); box-shadow: inset 0 0 0 1px var(--accent-dim); }
    .tile.locked { opacity: 0.6; }

    .art {
      position: relative; padding: 0; border: 0; background: none; cursor: pointer; line-height: 0;
    }
    .art:hover .info-dot { opacity: 1; }
    .badge-corner {
      position: absolute; right: -5px; bottom: -5px;
      min-width: 20px; text-align: center;
      font-size: 0.72rem; font-weight: 700; font-family: var(--mono);
      padding: 0 5px; border-radius: 6px;
      background: var(--accent); color: #06101e;
      border: 1px solid var(--bg); box-shadow: 0 0 6px rgba(46,230,214,0.4);
    }
    .badge-corner.zero { background: var(--surface-3); color: var(--text-dim); box-shadow: none; }
    .info-dot {
      position: absolute; top: -4px; right: -4px; font-size: 0.78rem; color: var(--text-faint);
      opacity: 0.55; transition: opacity 0.12s ease;
    }

    .name {
      padding: 0; border: 0; background: none; cursor: pointer;
      font-weight: 600; font-size: 0.9rem; color: var(--text); text-align: center; line-height: 1.15;
      max-width: 100%;
    }
    .name:hover { color: var(--accent); }

    .stats {
      display: flex; flex-direction: column; align-items: center; gap: 0.25rem;
      font-size: 0.8rem; min-height: 1.2rem;
    }
    .stats .time { white-space: nowrap; }

    .action {
      margin-top: auto; padding-top: 0.35rem; width: 100%;
      display: flex; flex-direction: column; align-items: stretch; gap: 0.3rem;
    }
    .muted { color: var(--text-dim); }
    .small { font-size: 0.78rem; }
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
