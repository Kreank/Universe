import {
  ChangeDetectionStrategy,
  Component,
  OnDestroy,
  OnInit,
  computed,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { Coordinate, PhalanxMovement } from '../../core/models/api.models';
import { navIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from './btn-icon.component';

/**
 * Sensorphalanx-Panel: scannt beim Öffnen die Flottenbewegungen zu/von einer
 * Koordinate und zeigt sie mit Live-Countdown (ETA) — die Grundlage fürs getimte
 * Abfangen. Schließt per Esc/Backdrop. Scan kostet Deuterium (Backend).
 */
@Component({
  selector: 'app-phalanx-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [BtnIconComponent],
  host: { '(document:keydown.escape)': 'close.emit()' },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup glass" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>
        <header class="head">
          <h2><app-btn-icon [src]="'assets/img/buildings/sensorphalanx.png'" glyph="📡" [size]="16" /> Sensorphalanx</h2>
          <span class="coord mono">[{{ target().galaxy }}:{{ target().system }}:{{ target().position }}]</span>
        </header>

        @if (loading()) {
          <p class="muted small">Scanne…</p>
        } @else if (error(); as e) {
          <p class="err small">{{ e }}</p>
        } @else {
          @if (movements().length === 0) {
            <p class="muted small">Keine Flottenbewegungen zu/von diesem Ziel.</p>
          }
          @for (m of movements(); track m.id) {
            <div class="mv" [class.inc]="m.direction === 'incoming'">
              <div class="mv-top">
                <span class="dir">{{ m.direction === 'incoming' ? '➡ Anflug' : '⬅ Abflug' }}</span>
                <span class="owner">{{ m.owner }}</span>
                <span class="mission mono">{{ m.mission }}</span>
                <span class="ships mono">{{ m.ships_total }} <app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="14" /></span>
              </div>
              <div class="mv-bot small mono">
                {{ m.origin ?? '?' }} → {{ m.target }}
                @if (m.arrive_at) { · Ankunft in <strong>{{ countdown(m.arrive_at) }}</strong> }
                @if (m.return_at) { · zurück {{ countdown(m.return_at) }} }
              </div>
            </div>
          }
        }
      </div>
    </div>
  `,
  styles: [
    `
      .backdrop { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; padding: var(--sp-4); background: rgba(4,7,14,0.72); backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px); animation: fade var(--motion-fast) var(--ease-out); }
      @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
      /* .glass (global) liefert Background/Blur/Border/Elevation; hier nur Layout + Signatur-Ecke. */
      .popup { position: relative; width: 100%; max-width: 540px; max-height: 86vh; overflow-y: auto; border-radius: var(--r-lg); padding: var(--sp-5); clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%); animation: pop var(--motion-base) var(--ease-out); }
      @keyframes pop { from { transform: translateY(8px) scale(0.98); opacity: 0; } to { transform: none; opacity: 1; } }
      .x { position: absolute; top: var(--sp-2); right: var(--sp-2); width: 32px; height: 32px; border-radius: var(--r-sm); background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer; display: flex; align-items: center; justify-content: center; transition: color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out); }
      .x:hover { color: var(--text); background: rgba(255,255,255,0.1); }
      .head { display: flex; align-items: baseline; gap: var(--sp-2); padding-right: var(--sp-8); margin-bottom: var(--sp-2); }
      .head h2 { margin: 0; font-size: var(--fs-lg); }
      .coord { color: var(--accent); font-size: var(--fs-base); }
      .err { color: var(--warn); }
      .mv { border: 1px solid var(--border); border-radius: var(--r-md); padding: var(--sp-2) var(--sp-3); margin-top: var(--sp-2); background: rgba(255,255,255,0.02); }
      .mv.inc { border-color: var(--danger-dim); background: color-mix(in srgb, var(--danger) 8%, transparent); }
      .mv-top { display: flex; flex-wrap: wrap; gap: var(--sp-2); align-items: baseline; }
      .dir { font-size: var(--fs-sm); color: var(--accent); }
      .mv.inc .dir { color: var(--danger); }
      .owner { font-weight: 600; }
      .mission { color: var(--text-dim); font-size: var(--fs-sm); }
      .ships { margin-left: auto; }
      .mv-bot { color: var(--text-dim); margin-top: var(--sp-1); }

      @media (max-width: 560px) {
        .backdrop { padding: var(--sp-2); }
        .popup { max-width: 100%; max-height: 94vh; padding: var(--sp-4); }
      }
    `,
  ],
})
export class PhalanxPanelComponent implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);

  protected readonly navIcon = navIcon;

  readonly target = input.required<Coordinate>();
  readonly close = output<void>();

  protected readonly movements = signal<PhalanxMovement[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  private readonly nowMs = signal(Date.now());
  private timer?: ReturnType<typeof setInterval>;

  ngOnInit(): void {
    const t = this.target();
    this.api.phalanxScan(t.galaxy, t.system, t.position).subscribe({
      next: (r) => {
        this.movements.set(r.movements);
        this.loading.set(false);
      },
      error: (err) => {
        this.error.set(err?.error?.detail ?? 'Scan fehlgeschlagen.');
        this.loading.set(false);
      },
    });
    this.timer = setInterval(() => this.nowMs.set(Date.now()), 1000);
  }

  ngOnDestroy(): void {
    if (this.timer) {
      clearInterval(this.timer);
    }
  }

  countdown(iso: string): string {
    const diff = Math.floor((new Date(iso).getTime() - this.nowMs()) / 1000);
    if (diff <= 0) {
      return 'jetzt';
    }
    const h = Math.floor(diff / 3600);
    const m = Math.floor((diff % 3600) / 60);
    const s = diff % 60;
    return h > 0 ? `${h}h ${m}m ${s}s` : m > 0 ? `${m}m ${s}s` : `${s}s`;
  }
}
