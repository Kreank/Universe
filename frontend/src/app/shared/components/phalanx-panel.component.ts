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

/**
 * Sensorphalanx-Panel: scannt beim Öffnen die Flottenbewegungen zu/von einer
 * Koordinate und zeigt sie mit Live-Countdown (ETA) — die Grundlage fürs getimte
 * Abfangen. Schließt per Esc/Backdrop. Scan kostet Deuterium (Backend).
 */
@Component({
  selector: 'app-phalanx-panel',
  changeDetection: ChangeDetectionStrategy.OnPush,
  host: { '(document:keydown.escape)': 'close.emit()' },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>
        <header class="head">
          <h2>📡 Sensorphalanx</h2>
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
                <span class="ships mono">{{ m.ships_total }} 🚀</span>
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
      .backdrop { position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center; padding: 1rem; background: rgba(4,7,14,0.72); backdrop-filter: blur(4px); }
      .popup { position: relative; width: 100%; max-width: 540px; max-height: 86vh; overflow-y: auto; background: linear-gradient(160deg, var(--surface-2), var(--surface)); border: 1px solid var(--border-strong); border-radius: var(--radius); box-shadow: var(--shadow), var(--glow); padding: 1.1rem 1.2rem 1.2rem; clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%); }
      .x { position: absolute; top: 0.5rem; right: 0.6rem; width: 30px; height: 30px; border-radius: 8px; background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer; }
      .head { display: flex; align-items: baseline; gap: 0.6rem; padding-right: 2rem; margin-bottom: 0.6rem; }
      .head h2 { margin: 0; font-size: 1.1rem; }
      .coord { color: var(--accent); font-size: 0.9rem; }
      .err { color: var(--warn); }
      .mv { border: 1px solid var(--border); border-radius: var(--radius-sm); padding: 0.5rem 0.6rem; margin-top: 0.5rem; background: rgba(255,255,255,0.02); }
      .mv.inc { border-color: var(--magenta-dim); background: rgba(255,64,160,0.06); }
      .mv-top { display: flex; flex-wrap: wrap; gap: 0.5rem; align-items: baseline; }
      .dir { font-size: 0.78rem; color: var(--accent); }
      .mv.inc .dir { color: var(--magenta); }
      .owner { font-weight: 600; }
      .mission { color: var(--text-dim); font-size: 0.8rem; }
      .ships { margin-left: auto; }
      .mv-bot { color: var(--text-dim); margin-top: 0.25rem; }
    `,
  ],
})
export class PhalanxPanelComponent implements OnInit, OnDestroy {
  private readonly api = inject(ApiService);

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
