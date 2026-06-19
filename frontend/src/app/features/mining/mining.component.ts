import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { MiningField, MiningFieldsResponse } from '../../core/models/api.models';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';

type SortKey = 'richness' | 'metal' | 'crystal' | 'expires';

/** Reichtums-Tier -> Sortier-Rang (ergiebig zuerst). */
const RICHNESS_RANK: Record<string, number> = { ergiebig: 3, reich: 2, normal: 1, karg: 0 };

/**
 * Bergbau · Asteroiden-Übersicht. Zeigt alle AKTIVEN Felder in Reichweite der
 * Ortungs-Forschung (Stufe 1 = Heimat-Galaxie, je Stufe +1 Galaxie). Felder wandern
 * alle 24–48h, daher ist diese Liste der Weg, sie zu finden — ohne System für System
 * durch die Galaxie-Ansicht zu klicken. Jede Zeile ist direkt anfliegbar (Minen).
 */
@Component({
  selector: 'app-mining',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DecimalPipe, RouterLink, CountdownComponent, EmptyStateComponent],
  template: `
    <h1>Bergbau · Asteroidenfelder</h1>
    <p class="sub">
      Aktive Felder in Reichweite deiner Ortung. Felder wandern alle 24–48 h — hier siehst du,
      wo gerade was liegt.
    </p>

    @if (loading()) {
      <p class="muted">Lade Felder…</p>
    } @else if (data(); as d) {
      @if (d.prospecting < 1) {
        <div class="card lock">
          <div class="lock-ico">🛰</div>
          <div>
            <strong>Ortung nicht erforscht</strong>
            <p class="muted small">
              Erforsche <strong>Ortung</strong>, um aktive Asteroidenfelder aufzuspüren.
              Stufe 1 zeigt deine Heimat-Galaxie, jede weitere Stufe erweitert die Reichweite.
            </p>
            <a class="btn btn-sm btn-primary" routerLink="/research" [queryParams]="{ focus: 'prospecting' }">Zur Forschung →</a>
          </div>
        </div>
      } @else {
        <div class="bar-row">
          <span class="chip">Ortung Stufe {{ d.prospecting }}</span>
          <span class="chip ghost">Reichweite: {{ rangeLabel(d) }}</span>
          <span class="chip ghost">{{ d.fields.length }} Felder</span>
          <button class="btn btn-sm btn-ghost" (click)="reload()">↻ Aktualisieren</button>
        </div>

        @if (sortedFields().length) {
          <div class="sort-row">
            <span class="muted small">Sortieren:</span>
            <button class="lnk" [class.on]="sortKey() === 'richness'" (click)="sortKey.set('richness')">Reichtum</button>
            <button class="lnk" [class.on]="sortKey() === 'metal'" (click)="sortKey.set('metal')">Metall</button>
            <button class="lnk" [class.on]="sortKey() === 'crystal'" (click)="sortKey.set('crystal')">Kristall</button>
            <button class="lnk" [class.on]="sortKey() === 'expires'" (click)="sortKey.set('expires')">Verfällt</button>
          </div>

          <div class="grid fields">
            @for (f of sortedFields(); track f.coords) {
              <article class="card field">
                <div class="f-top">
                  <a class="coord" [routerLink]="['/galaxy']" [queryParams]="{ g: f.galaxy, s: f.system }" title="Auf der Galaxie-Karte ansehen">[{{ f.coords }}]</a>
                  <span class="rich" [attr.data-r]="f.richness">{{ richnessLabel(f.richness) }} · ×{{ f.mult }}</span>
                </div>
                <div class="f-res">
                  <span class="r metal" title="Metall-Restvorrat">⛏ {{ f.metal | number: '1.0-0' }}<span class="faint"> / {{ f.metal_max | number: '1.0-0' }}</span></span>
                  <span class="r crystal" title="Kristall-Restvorrat">💎 {{ f.crystal | number: '1.0-0' }}<span class="faint"> / {{ f.crystal_max | number: '1.0-0' }}</span></span>
                </div>
                <div class="f-foot">
                  @if (f.expires_at) {
                    <span class="exp muted small">wandert in <app-countdown [target]="f.expires_at" /></span>
                  }
                  <a class="btn btn-sm btn-primary" [routerLink]="['/fleet']" [queryParams]="{ g: f.galaxy, s: f.system, p: f.position, mission: 'mine' }">⛏ Minen</a>
                </div>
              </article>
            }
          </div>
        } @else {
          <app-empty-state art="empty_search">
            Keine aktiven Felder in Reichweite. Höhere Ortungsstufe erweitert die Reichweite.
          </app-empty-state>
        }
      }
    }
  `,
  styles: [
    `
      .sub { color: var(--text-dim); margin-top: calc(-1 * var(--sp-2)); }
      .bar-row { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; margin: var(--sp-3) 0; }
      .chip { font-size: var(--fs-sm); background: var(--surface-2); border: 1px solid var(--border-strong); border-radius: var(--r-sm); padding: 2px var(--sp-2); }
      .chip.ghost { background: transparent; color: var(--text-dim); }
      .lock { display: flex; gap: var(--sp-3); align-items: center; padding: var(--sp-4); }
      .lock-ico { font-size: 2rem; }
      .sort-row { display: flex; align-items: center; gap: var(--sp-2); margin-bottom: var(--sp-2); }
      .lnk { background: none; border: none; color: var(--text-dim); cursor: pointer; font-size: var(--fs-sm); padding: 0; }
      .lnk.on { color: var(--accent); text-decoration: underline; }
      .fields { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--sp-3); }
      .field { display: flex; flex-direction: column; gap: var(--sp-2); padding: var(--sp-3); }
      .f-top { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); }
      .coord { font-family: var(--font-mono); color: var(--text); text-decoration: none; border-bottom: 1px dotted var(--border-strong); }
      .coord:hover { color: var(--accent); }
      .rich { font-size: var(--fs-xs); padding: 1px var(--sp-1); border-radius: var(--r-sm); background: rgba(255,255,255,0.06); color: var(--text-dim); }
      .rich[data-r='reich'] { color: #7fd3ff; }
      .rich[data-r='ergiebig'] { color: #ffd479; }
      .f-res { display: flex; gap: var(--sp-3); font-size: var(--fs-sm); }
      .f-foot { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); margin-top: auto; }
      .faint { color: var(--text-faint); }
    `,
  ],
})
export class MiningComponent {
  private readonly api = inject(ApiService);

  protected readonly loading = signal(true);
  protected readonly data = signal<MiningFieldsResponse | null>(null);
  protected readonly sortKey = signal<SortKey>('richness');

  protected readonly sortedFields = computed(() => {
    const fields = [...(this.data()?.fields ?? [])];
    const key = this.sortKey();
    return fields.sort((a, b) => {
      switch (key) {
        case 'metal': return b.metal - a.metal;
        case 'crystal': return b.crystal - a.crystal;
        case 'expires': return (a.expires_at ?? '').localeCompare(b.expires_at ?? '');
        default: return (RICHNESS_RANK[b.richness] ?? 0) - (RICHNESS_RANK[a.richness] ?? 0)
          || (b.metal + b.crystal) - (a.metal + a.crystal);
      }
    });
  });

  constructor() {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.api.getMiningFields().subscribe({
      next: (d) => { this.data.set(d); this.loading.set(false); },
      error: () => { this.loading.set(false); },
    });
  }

  richnessLabel(r: string): string {
    return ({ karg: 'Karg', normal: 'Normal', reich: 'Reich', ergiebig: 'Ergiebig' } as Record<string, string>)[r] ?? r;
  }

  rangeLabel(d: MiningFieldsResponse): string {
    if (d.range <= 0) return 'Heimat-Galaxie';
    return `Galaxien ±${d.range}`;
  }
}
