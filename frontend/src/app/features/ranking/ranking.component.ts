import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { RankingEntry, RankingResponse } from '../../core/models/api.models';
import { ShortNumberPipe } from '../../shared/pipes/short-number.pipe';

/**
 * Rangliste (Punktesystem, OGame-Stil). Punkte = aktueller Imperiumswert / 1000
 * (Gebaeude + Forschung + Flotte + Verteidigung). Der Server rechnet bei jedem
 * Abruf frisch; verlorene Flotten/Gebaeude senken die Punkte automatisch.
 */
@Component({
  selector: 'app-ranking',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ShortNumberPipe],
  template: `
    <section class="rank">
      <header class="rank-head">
        <img class="head-ico" src="assets/img/nav/ranking.png" alt="" (error)="onIcoError($event)" />
        <div>
          <h1>Rangliste</h1>
          <p class="faint small">
            Punkte = investierter Imperiumswert ÷ 1000 (Gebäude, Forschung, Flotte, Verteidigung).
            Verluste senken die Punkte — wie bei OGame.
          </p>
        </div>
      </header>

      @if (loading()) {
        <p class="state">Rangliste lädt …</p>
      } @else if (error()) {
        <p class="state err">{{ error() }}</p>
      } @else {
        <div class="card table-card">
          <div class="rrow head">
            <span class="c-rank">#</span>
            <span class="c-name">Spieler</span>
            <span class="c-pts">Punkte</span>
            <span class="c-cat tip" data-tip="Gebäude">🏗️</span>
            <span class="c-cat tip" data-tip="Forschung">🔬</span>
            <span class="c-cat tip" data-tip="Flotte">🚀</span>
            <span class="c-cat tip" data-tip="Verteidigung">🛡️</span>
          </div>

          @for (e of entries(); track e.player_id) {
            <div class="rrow" [class.self]="e.is_self">
              <span class="c-rank mono">{{ e.rank }}</span>
              <span class="c-name">
                @if (e.rank <= 3) { <span class="medal">{{ medal(e.rank) }}</span> }
                {{ e.display_name }}
                @if (e.is_self) { <span class="you">du</span> }
              </span>
              <span class="c-pts mono">{{ e.points | shortNumber }}</span>
              <span class="c-cat mono faint">{{ e.buildings | shortNumber }}</span>
              <span class="c-cat mono faint">{{ e.research | shortNumber }}</span>
              <span class="c-cat mono faint">{{ e.fleet | shortNumber }}</span>
              <span class="c-cat mono faint">{{ e.defense | shortNumber }}</span>
            </div>
          }

          @if (showMeFooter()) {
            <div class="rrow self footer-me">
              <span class="c-rank mono">{{ me()!.rank }}</span>
              <span class="c-name">{{ me()!.display_name }} <span class="you">du</span></span>
              <span class="c-pts mono">{{ me()!.points | shortNumber }}</span>
              <span class="c-cat mono faint">{{ me()!.buildings | shortNumber }}</span>
              <span class="c-cat mono faint">{{ me()!.research | shortNumber }}</span>
              <span class="c-cat mono faint">{{ me()!.fleet | shortNumber }}</span>
              <span class="c-cat mono faint">{{ me()!.defense | shortNumber }}</span>
            </div>
          }
        </div>
        <p class="faint small count">{{ total() }} Imperien gewertet</p>
      }
    </section>
  `,
  styles: [`
    .rank { display: flex; flex-direction: column; gap: var(--sp-4); }
    .rank-head { display: flex; align-items: center; gap: var(--sp-3); }
    .head-ico { width: 44px; height: 44px; object-fit: contain; flex: 0 0 auto;
      filter: drop-shadow(0 2px 5px rgba(0,0,0,0.6)); }
    .rank-head h1 { margin: 0; font-family: var(--font-display); }
    .faint { color: var(--text-faint); }
    .small { font-size: var(--fs-sm); }
    .state { color: var(--text-dim); padding: var(--sp-6) 0; }
    .state.err { color: var(--danger); }

    /* Datenreiche Tabelle: scanbares Raster, Zahlen tabular + rechtsbuendig. */
    .table-card { padding: var(--sp-1) var(--sp-2); overflow: hidden; }
    .rrow {
      display: grid;
      grid-template-columns: 2.6rem minmax(0, 1fr) 5.5rem 4rem 4rem 4rem 4rem;
      align-items: center; gap: var(--sp-2);
      padding: var(--sp-2) var(--sp-3); border-radius: var(--r-sm);
    }
    .rrow.head {
      position: sticky; top: 0; z-index: 2;
      font-family: var(--font-display);
      font-size: var(--fs-xs); letter-spacing: 0.12em; text-transform: uppercase;
      color: var(--text-dim);
      background: var(--surface-2);
      border-bottom: 1px solid var(--border);
    }
    .rrow:not(.head):nth-child(even) { background: rgba(255,255,255,0.02); }
    .rrow:not(.head):hover { background: rgba(255,255,255,0.05); }
    .rrow.self {
      background: var(--accent-soft);
      box-shadow: inset 2px 0 0 var(--accent);
    }
    .rrow.self:hover { background: rgba(47,227,210,0.18); }
    .rrow.footer-me { margin-top: var(--sp-2); border-top: 1px dashed var(--border-strong); }

    .c-rank { text-align: center; color: var(--text-dim); }
    .c-name {
      display: flex; align-items: center; gap: var(--sp-2); min-width: 0;
      overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
    }
    .rrow.self .c-name { color: var(--text); font-weight: 600; }
    .medal { font-size: var(--fs-md); flex: 0 0 auto; }
    .you {
      font-family: var(--font-display);
      font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.08em;
      background: var(--accent); color: #04201d;
      padding: 1px var(--sp-2); border-radius: var(--r-pill); font-weight: 600;
    }
    .c-pts { text-align: right; font-weight: 700; color: var(--accent); }
    .c-cat { text-align: right; font-size: var(--fs-sm); }

    /* Mobil: nur Rang/Name/Punkte, dafuer komfortable Touch-Hoehe (>=44px). */
    @media (max-width: 640px) {
      .rrow { grid-template-columns: 2.2rem minmax(0, 1fr) 5rem; min-height: 44px; }
      .rrow.head { min-height: 0; }
      .c-cat { display: none; }
    }
    .count { text-align: right; margin: 0; }
  `],
})
export class RankingComponent implements OnInit {
  private readonly api = inject(ApiService);

  protected readonly entries = signal<RankingEntry[]>([]);
  protected readonly me = signal<RankingEntry | null>(null);
  protected readonly total = signal(0);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  /** Eigene Zeile separat anzeigen, wenn sie nicht in der Top-Liste steht. */
  protected readonly showMeFooter = computed(() => {
    const m = this.me();
    return !!m && !this.entries().some((e) => e.is_self);
  });

  ngOnInit(): void {
    this.api.getRanking().subscribe({
      next: (r: RankingResponse) => {
        this.entries.set(r.entries);
        this.me.set(r.me);
        this.total.set(r.total_players);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Rangliste konnte nicht geladen werden.');
        this.loading.set(false);
      },
    });
  }

  protected medal(rank: number): string {
    return rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
  }

  protected onIcoError(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
}
