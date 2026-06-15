import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { MegastructureListResponse, MegastructureOption } from '../../core/models/api.models';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { NotificationService } from '../../core/services/notification.service';
import { navIcon, resourceIcon, uiIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';

@Component({
  selector: 'app-megastructures',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [CountdownComponent, DecimalPipe, BtnIconComponent],
  template: `
    <h1>Megastrukturen</h1>
    <p class="muted sub">
      Gewaltige Endgame-Bauwerke — kontoweit, stufenweise, <strong>nur ein Projekt
      gleichzeitig</strong>. Haupt-Senke für <strong>Dunkle Materie</strong>.
    </p>

    <div class="exotic-bar card">
      <span>
        <img class="res-ic" [src]="resIcon('dark_matter')" alt="" />
        Dunkle Materie: <strong>{{ darkMatter() | number: '1.0-0' }}</strong>
      </span>
      <span>
        <img class="res-ic" [src]="resIcon('antimatter')" alt="" />
        Antimaterie: <strong>{{ antimatter() | number: '1.0-0' }}</strong>
      </span>
    </div>

    @if (loading()) {
      <p class="empty-state">Lade Megastrukturen…</p>
    } @else {
      <div class="mega-grid">
        @for (m of structures(); track m.type) {
          <div class="card mega" [class.building]="m.building_until">
            <div class="art-banner">
              <app-btn-icon class="glyph" [src]="navIcon('megastructures')" glyph="🌌" [size]="48" />
              <img [src]="megaIcon(m.type)" alt="" class="art" (error)="$any($event.target).remove()" />
            </div>
            <div class="mega-head">
              <h3>{{ m.name }}</h3>
              <span class="lvl">Stufe {{ m.level }}<span class="muted"> / {{ m.max_level }}</span></span>
            </div>
            <p class="blurb">{{ m.blurb }}</p>

            <div class="cost">
              <span><img class="res-ic" [src]="resIcon('metal')" alt="" /> {{ m.cost.metal | number: '1.0-0' }}</span>
              <span><img class="res-ic" [src]="resIcon('crystal')" alt="" /> {{ m.cost.crystal | number: '1.0-0' }}</span>
              <span><img class="res-ic" [src]="resIcon('deuterium')" alt="" /> {{ m.cost.deuterium | number: '1.0-0' }}</span>
              @if (m.cost.dark_matter > 0) {
                <span class="dm"><img class="res-ic" [src]="resIcon('dark_matter')" alt="" /> {{ m.cost.dark_matter | number: '1.0-0' }}</span>
              }
              @if (m.cost.antimatter > 0) {
                <span class="am"><img class="res-ic" [src]="resIcon('antimatter')" alt="" /> {{ m.cost.antimatter | number: '1.0-0' }}</span>
              }
            </div>

            @if (m.building_until) {
              <div class="status building-status">
                <app-btn-icon [src]="uiIcon('time')" glyph="⏳" [size]="16" /> Im Bau · <app-countdown [target]="m.building_until" />
              </div>
            } @else if (m.maxed) {
              <div class="status done">✓ Höchststufe erreicht</div>
            } @else {
              <button
                class="btn btn-primary full"
                type="button"
                [disabled]="!m.can_afford || m.busy || pending() === m.type"
                (click)="build(m)"
              >
                {{ pending() === m.type ? '…' : 'Stufe ' + m.next_level + ' bauen' }}
              </button>
              @if (m.busy) {
                <span class="hint small">Anderes Megastruktur-Projekt läuft</span>
              } @else if (!m.can_afford) {
                <span class="hint small warn">Nicht genug Ressourcen / Dunkle Materie</span>
              }
            }
          </div>
        }
      </div>
    }
  `,
  styles: [
    `
      .sub { margin-top: calc(-1 * var(--sp-1)); font-size: var(--fs-sm); }
      .exotic-bar { display: flex; gap: var(--sp-5); padding: var(--sp-3) var(--sp-4); margin-bottom: var(--sp-4); }
      .exotic-bar span { display: inline-flex; align-items: center; gap: var(--sp-2); }
      .res-ic { width: 22px; height: 22px; object-fit: contain; }
      .mega-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(260px, 1fr)); gap: var(--sp-4); }
      .mega { display: flex; flex-direction: column; gap: var(--sp-3); }
      .mega.building { border-color: color-mix(in srgb, var(--accent) 40%, transparent); box-shadow: var(--e1), var(--glow-soft); }
      .art-banner {
        position: relative; width: 100%; height: 160px;
        display: flex; align-items: center; justify-content: center;
        margin-bottom: var(--sp-2);
        border-radius: var(--radius, 10px);
        background: radial-gradient(circle at 50% 40%, color-mix(in srgb, var(--accent) 10%, transparent), transparent 70%);
      }
      .art-banner .glyph { font-size: 3.2rem; position: absolute; opacity: 0.5; }
      .art-banner .art { max-width: 100%; max-height: 100%; object-fit: contain; position: relative; z-index: 1; filter: drop-shadow(0 4px 14px rgba(0,0,0,0.45)); }
      .mega-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-3); }
      .mega-head h3 { margin: 0; font-family: var(--font-display); }
      .lvl { font-size: var(--fs-sm); }
      .blurb { font-size: var(--fs-sm); color: var(--text-faint); flex: 1; }
      .cost { display: flex; flex-wrap: wrap; gap: var(--sp-2) var(--sp-3); font-size: var(--fs-sm); }
      .cost span { display: inline-flex; align-items: center; gap: 5px; }
      .cost .res-ic { width: 18px; height: 18px; }
      .cost .dm { color: var(--accent); }
      .cost .am { color: var(--warn); }
      .full { width: 100%; }
      .status { font-family: var(--font-display); font-size: var(--fs-sm); text-align: center; padding: var(--sp-2); }
      .building-status { color: var(--accent); }
      .done { color: var(--ok); }
      .hint { display: block; text-align: center; color: var(--text-faint); margin-top: var(--sp-1); }
      .hint.warn { color: var(--warn); }
      .small { font-size: var(--fs-xs); }
    `,
  ],
})
export class MegastructuresComponent {
  private readonly api = inject(ApiService);
  private readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  private readonly data = signal<MegastructureListResponse | null>(null);
  protected readonly loading = signal(true);
  protected readonly pending = signal<string | null>(null);

  protected readonly resIcon = resourceIcon;
  protected readonly navIcon = navIcon;
  protected readonly uiIcon = uiIcon;
  megaIcon = (type: string) => `assets/img/megastructures/${type}.png`;

  protected readonly structures = computed(() => this.data()?.structures ?? []);
  protected readonly darkMatter = computed(() => this.data()?.dark_matter ?? 0);
  protected readonly antimatter = computed(() => this.data()?.antimatter ?? 0);

  constructor() {
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.api.getMegastructures().subscribe({
      next: (res) => {
        this.data.set(res);
        this.loading.set(false);
      },
      error: () => this.loading.set(false),
    });
  }

  build(m: MegastructureOption): void {
    this.pending.set(m.type);
    this.api.buildMegastructure(m.type).subscribe({
      next: () => {
        this.pending.set(null);
        this.notify.info('Bau gestartet', `${m.name} → Stufe ${m.next_level}.`);
        this.load();
        void this.state.reloadActivePlanet();
      },
      error: (err) => {
        this.pending.set(null);
        this.notify.warning('Bau nicht möglich', err?.error?.detail ?? 'Fehler.');
      },
    });
  }
}
