import {
  Component,
  OnDestroy,
  computed,
  input,
  signal,
  ChangeDetectionStrategy,
} from '@angular/core';

/**
 * Live-Countdown auf einen absoluten ISO-Zeitstempel (`*_finishes_at`).
 * Zaehlt lokal im Sekundentakt runter — der Server bleibt autoritativ.
 */
@Component({
  selector: 'app-countdown',
  changeDetection: ChangeDetectionStrategy.OnPush,
  template: `<span class="countdown" [class.done]="remaining() <= 0">{{ display() }}</span>`,
  styles: [
    `
      .countdown {
        font-variant-numeric: tabular-nums;
        letter-spacing: 0.04em;
        color: var(--accent);
      }
      .countdown.done {
        color: var(--text-dim);
      }
    `,
  ],
})
export class CountdownComponent implements OnDestroy {
  /** Ziel-Zeitstempel (ISO). null = nichts laeuft. */
  readonly target = input<string | null>(null);
  /** Text, wenn kein Countdown aktiv ist. */
  readonly idleLabel = input<string>('–');

  private readonly now = signal(Date.now());
  private readonly timer: ReturnType<typeof setInterval>;

  readonly remaining = computed(() => {
    const t = this.target();
    if (!t) {
      return 0;
    }
    return new Date(t).getTime() - this.now();
  });

  readonly display = computed(() => {
    const t = this.target();
    if (!t) {
      return this.idleLabel();
    }
    const ms = this.remaining();
    if (ms <= 0) {
      return 'fertig';
    }
    const total = Math.floor(ms / 1000);
    const h = Math.floor(total / 3600);
    const m = Math.floor((total % 3600) / 60);
    const s = total % 60;
    const pad = (n: number) => n.toString().padStart(2, '0');
    return h > 0 ? `${h}:${pad(m)}:${pad(s)}` : `${pad(m)}:${pad(s)}`;
  });

  constructor() {
    this.timer = setInterval(() => this.now.set(Date.now()), 1000);
  }

  ngOnDestroy(): void {
    clearInterval(this.timer);
  }
}
