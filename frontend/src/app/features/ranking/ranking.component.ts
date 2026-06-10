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
    .rank { display: flex; flex-direction: column; gap: 1rem; }
    .rank-head { display: flex; align-items: center; gap: 0.8rem; }
    .head-ico { width: 44px; height: 44px; object-fit: contain; flex: 0 0 auto;
      filter: drop-shadow(0 1px 3px rgba(0,0,0,0.5)); }
    .rank-head h1 { margin: 0; font-size: 1.25rem; }
    .faint { color: var(--text-faint); }
    .small { font-size: 0.82rem; }
    .state { color: var(--text-dim); padding: 1.5rem 0; }
    .state.err { color: #ff9b9b; }

    .table-card { padding: 0.3rem 0.4rem; }
    .rrow {
      display: grid;
      grid-template-columns: 2.6rem 1fr 5rem 4rem 4rem 4rem 4rem;
      align-items: center; gap: 0.4rem;
      padding: 0.4rem 0.5rem; border-radius: 6px;
    }
    .rrow.head {
      font-size: 0.72rem; letter-spacing: 0.04em; text-transform: uppercase;
      color: var(--text-dim); border-bottom: 1px solid var(--border);
    }
    .rrow:not(.head):nth-child(even) { background: rgba(255,255,255,0.02); }
    .rrow.self {
      background: rgba(46,230,214,0.12);
      box-shadow: inset 2px 0 0 var(--accent);
    }
    .rrow.footer-me { margin-top: 0.4rem; border-top: 1px dashed var(--border); }
    .c-rank { text-align: center; color: var(--text-dim); }
    .c-name { display: flex; align-items: center; gap: 0.4rem; min-width: 0; }
    .c-name { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .medal { font-size: 1rem; }
    .you {
      font-size: 0.62rem; text-transform: uppercase; letter-spacing: 0.06em;
      background: var(--accent); color: #06101e; padding: 1px 5px; border-radius: 99px;
    }
    .c-pts { text-align: right; font-weight: 700; color: var(--accent); }
    .c-cat { text-align: right; font-size: 0.82rem; }

    /* Mobil: Kategorie-Spalten ausblenden, nur Rang/Name/Punkte. */
    @media (max-width: 640px) {
      .rrow { grid-template-columns: 2.2rem 1fr 4.5rem; }
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
