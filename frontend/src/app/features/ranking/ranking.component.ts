import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { RankBoard, RankBoardEntry, RankCategory } from '../../core/models/api.models';
import { ShortNumberPipe } from '../../shared/pipes/short-number.pipe';
import { navIcon, statIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { MessageComposeComponent } from '../../shared/components/message-compose.component';

interface CatMeta {
  key: RankCategory;
  label: string;
  icon: string;
  glyph: string;
}

/**
 * Rangliste (OGame-Stil). Zwei Reiter (Spieler / Allianzen) und fuenf Kategorie-Wertungen
 * (Gesamt, Gebaeude, Forschung, Flotte, Verteidigung) mit jeweils eigenem Rang. „Dein Platz"
 * zeigt den eigenen Rang in JEDER Kategorie. Punkte = aktueller Imperiumswert / 1000; der
 * Server rechnet bei jedem Abruf frisch (Verluste senken die Punkte automatisch).
 */
@Component({
  selector: 'app-ranking',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [ShortNumberPipe, BtnIconComponent, MessageComposeComponent],
  template: `
    <section class="rank">
      <header class="rank-head">
        <img class="head-ico" src="assets/img/nav/ranking.png" alt="" (error)="onIcoError($event)" />
        <div>
          <h1>Rangliste</h1>
          <p class="faint small">
            Punkte = investierter Imperiumswert ÷ 1000. Verluste senken die Punkte — wie bei OGame.
          </p>
        </div>
      </header>

      <!-- Reiter: Spieler / Allianzen -->
      <div class="tabs" role="tablist">
        <button class="tab" [class.active]="board() === 'players'" type="button" role="tab" (click)="setBoard('players')">
          👤 Spieler
        </button>
        <button class="tab" [class.active]="board() === 'alliances'" type="button" role="tab" (click)="setBoard('alliances')">
          🛡️ Allianzen
        </button>
      </div>

      <!-- Kategorie-Auswahl (sortiert die Liste; „Dein Platz" zeigt alle Kategorien) -->
      <div class="cats">
        @for (c of CATS; track c.key) {
          <button class="catchip" [class.active]="category() === c.key" type="button" (click)="setCategory(c.key)">
            <app-btn-icon [src]="c.icon" [glyph]="c.glyph" [size]="14" /> {{ c.label }}
          </button>
        }
      </div>

      <!-- „Dein Platz" in JEDER Kategorie -->
      @if (myRanks(); as mr) {
        <div class="card myplace">
          <span class="myplace-label">Dein Platz</span>
          @for (c of CATS; track c.key) {
            <button class="place" [class.active]="category() === c.key" type="button" (click)="setCategory(c.key)">
              <span class="place-cat"><app-btn-icon [src]="c.icon" [glyph]="c.glyph" [size]="13" /> {{ c.label }}</span>
              <span class="place-rank mono">#{{ mr[c.key] }}</span>
            </button>
          }
        </div>
      }

      @if (loading()) {
        <p class="state">Rangliste lädt …</p>
      } @else if (error()) {
        <p class="state err">{{ error() }}</p>
      } @else if (!entries().length) {
        <p class="state">
          @if (board() === 'alliances') { Noch keine Allianzen gewertet. } @else { Noch keine Spieler gewertet. }
        </p>
      } @else {
        <div class="card table-card">
          <div class="rrow head" [class.alliance]="board() === 'alliances'">
            <span class="c-rank">#</span>
            <span class="c-name">{{ board() === 'alliances' ? 'Allianz' : 'Spieler' }}</span>
            <span class="c-pts">{{ catLabel(category()) }}</span>
            <span class="c-cat tip" data-tip="Gebäude"><app-btn-icon [src]="navIcon('buildings')" glyph="🏗️" [size]="14" /></span>
            <span class="c-cat tip" data-tip="Forschung"><app-btn-icon [src]="navIcon('research')" glyph="🔬" [size]="14" /></span>
            <span class="c-cat tip" data-tip="Flotte"><app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="14" /></span>
            <span class="c-cat tip" data-tip="Verteidigung"><app-btn-icon [src]="statIcon('shield')" glyph="🛡️" [size]="14" /></span>
          </div>

          @for (e of entries(); track e.id) {
            <div class="rrow" [class.self]="e.is_self" [class.alliance]="board() === 'alliances'">
              <span class="c-rank mono">{{ e.rank }}</span>
              <span class="c-name">
                @if (e.rank <= 3) { <span class="medal">{{ medal(e.rank) }}</span> }
                @if (board() === 'alliances' && e.tag) { <span class="tag mono">[{{ e.tag }}]</span> }
                <span class="nm">{{ e.name }}</span>
                @if (board() === 'alliances') {
                  <span class="members faint">· {{ e.member_count }} Mitgl.</span>
                }
                @if (e.is_self) { <span class="you">du</span> }
                @if (board() === 'players' && !e.is_self) {
                  <button
                    class="msg-btn tip"
                    data-tip="Anschreiben"
                    type="button"
                    (click)="compose.set({ id: e.id, name: e.name })"
                    [attr.aria-label]="'Nachricht an ' + e.name"
                  >
                    <app-btn-icon [src]="navIcon('mail')" glyph="✉" [size]="14" />
                  </button>
                }
              </span>
              <span class="c-pts mono">{{ e.value | shortNumber }}</span>
              <span class="c-cat mono faint" [class.hl]="category() === 'buildings'">{{ e.buildings | shortNumber }}</span>
              <span class="c-cat mono faint" [class.hl]="category() === 'research'">{{ e.research | shortNumber }}</span>
              <span class="c-cat mono faint" [class.hl]="category() === 'fleet'">{{ e.fleet | shortNumber }}</span>
              <span class="c-cat mono faint" [class.hl]="category() === 'defense'">{{ e.defense | shortNumber }}</span>
            </div>
          }

          @if (showMeFooter()) {
            <div class="rrow self footer-me" [class.alliance]="board() === 'alliances'">
              <span class="c-rank mono">{{ me()!.rank }}</span>
              <span class="c-name">
                @if (board() === 'alliances' && me()!.tag) { <span class="tag mono">[{{ me()!.tag }}]</span> }
                <span class="nm">{{ me()!.name }}</span>
                <span class="you">du</span>
              </span>
              <span class="c-pts mono">{{ me()!.value | shortNumber }}</span>
              <span class="c-cat mono faint" [class.hl]="category() === 'buildings'">{{ me()!.buildings | shortNumber }}</span>
              <span class="c-cat mono faint" [class.hl]="category() === 'research'">{{ me()!.research | shortNumber }}</span>
              <span class="c-cat mono faint" [class.hl]="category() === 'fleet'">{{ me()!.fleet | shortNumber }}</span>
              <span class="c-cat mono faint" [class.hl]="category() === 'defense'">{{ me()!.defense | shortNumber }}</span>
            </div>
          }
        </div>
        <p class="faint small count">
          {{ total() }} {{ board() === 'alliances' ? 'Allianzen' : 'Imperien' }} gewertet
        </p>
      }
    </section>

    @if (compose(); as c) {
      <app-message-compose [toPlayerId]="c.id" [toName]="c.name" (close)="compose.set(null)" />
    }
  `,
  styles: [`
    .rank { display: flex; flex-direction: column; gap: var(--sp-3); }
    .rank-head { display: flex; align-items: center; gap: var(--sp-3); }
    .head-ico { width: 44px; height: 44px; object-fit: contain; flex: 0 0 auto;
      filter: drop-shadow(0 2px 5px rgba(0,0,0,0.6)); }
    .rank-head h1 { margin: 0; font-family: var(--font-display); }
    .faint { color: var(--text-faint); }
    .small { font-size: var(--fs-sm); }
    .state { color: var(--text-dim); padding: var(--sp-6) 0; }
    .state.err { color: var(--danger); }

    /* Reiter Spieler/Allianzen */
    .tabs { display: flex; gap: var(--sp-2); }
    .tab {
      flex: 0 0 auto; padding: var(--sp-2) var(--sp-4); cursor: pointer;
      font-family: var(--font-display); font-size: var(--fs-sm); font-weight: 600;
      color: var(--text-dim); background: var(--surface-1);
      border: 1px solid var(--border-strong); border-radius: var(--r-md);
      transition: color var(--motion-fast) var(--ease-out), border-color var(--motion-fast) var(--ease-out),
        background var(--motion-fast) var(--ease-out);
    }
    .tab:hover { color: var(--text); }
    .tab.active { color: #04201d; background: var(--accent); border-color: var(--accent); }

    /* Kategorie-Chips */
    .cats { display: flex; gap: var(--sp-2); flex-wrap: wrap; }
    .catchip {
      display: inline-flex; align-items: center; gap: 5px;
      padding: var(--sp-1) var(--sp-3); cursor: pointer;
      font-size: var(--fs-sm); color: var(--text-dim);
      background: var(--surface-1); border: 1px solid var(--border-strong); border-radius: var(--r-pill);
      transition: color var(--motion-fast) var(--ease-out), border-color var(--motion-fast) var(--ease-out);
    }
    .catchip:hover { color: var(--text); }
    .catchip.active { color: var(--text); border-color: var(--accent); background: var(--accent-soft); }

    /* „Dein Platz" */
    .myplace { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; padding: var(--sp-2) var(--sp-3); }
    .myplace-label {
      font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase;
      letter-spacing: 0.1em; color: var(--text-faint); margin-right: var(--sp-1);
    }
    .place {
      display: inline-flex; align-items: center; gap: var(--sp-2); cursor: pointer;
      padding: var(--sp-1) var(--sp-2); border-radius: var(--r-sm);
      background: transparent; border: 1px solid transparent; color: var(--text-dim);
    }
    .place:hover { color: var(--text); }
    .place.active { border-color: var(--border-strong); background: rgba(255,255,255,0.03); color: var(--text); }
    .place-cat { display: inline-flex; align-items: center; gap: 4px; font-size: var(--fs-sm); }
    .place-rank { font-weight: 700; color: var(--accent); }

    /* Tabelle */
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
      color: var(--text-dim); background: var(--surface-2); border-bottom: 1px solid var(--border);
    }
    .rrow:not(.head):nth-child(even) { background: rgba(255,255,255,0.02); }
    .rrow:not(.head):hover { background: rgba(255,255,255,0.05); }
    .rrow.self { background: var(--accent-soft); box-shadow: inset 2px 0 0 var(--accent); }
    .rrow.self:hover { background: rgba(47,227,210,0.18); }
    .rrow.footer-me { margin-top: var(--sp-2); border-top: 1px dashed var(--border-strong); }

    .c-rank { text-align: center; color: var(--text-dim); }
    .c-name {
      display: flex; align-items: center; gap: var(--sp-2); min-width: 0;
      overflow: hidden; white-space: nowrap;
    }
    .c-name .nm { overflow: hidden; text-overflow: ellipsis; min-width: 0; }
    .rrow.self .c-name { color: var(--text); font-weight: 600; }
    .medal { font-size: var(--fs-md); flex: 0 0 auto; }
    .tag { color: var(--accent); flex: 0 0 auto; font-size: var(--fs-sm); }
    .members { flex: 0 0 auto; font-size: var(--fs-xs); }
    .you {
      font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase;
      letter-spacing: 0.08em; background: var(--accent); color: #04201d;
      padding: 1px var(--sp-2); border-radius: var(--r-pill); font-weight: 600; flex: 0 0 auto;
    }
    .msg-btn {
      flex: 0 0 auto; display: inline-flex; align-items: center; justify-content: center;
      width: 26px; height: 26px; padding: 0; border-radius: var(--r-sm);
      border: 1px solid transparent; background: transparent; color: var(--text-faint);
      cursor: pointer; opacity: 0.55;
      transition: opacity var(--motion-fast) var(--ease-out), color var(--motion-fast) var(--ease-out),
        border-color var(--motion-fast) var(--ease-out);
    }
    .rrow:hover .msg-btn { opacity: 1; }
    .msg-btn:hover { color: var(--accent); border-color: var(--border-strong); background: rgba(255,255,255,0.04); }
    .c-pts { text-align: right; font-weight: 700; color: var(--accent); }
    .c-cat { text-align: right; font-size: var(--fs-sm); }
    .c-cat.hl { color: var(--text); font-weight: 600; }

    /* Mobil: nur Rang/Name/Wert, dafuer komfortable Touch-Hoehe (>=44px). */
    @media (max-width: 640px) {
      .rrow { grid-template-columns: 2.2rem minmax(0, 1fr) 5rem; min-height: 44px; }
      .rrow.head { min-height: 0; }
      .c-cat { display: none; }
      .myplace { gap: var(--sp-1); }
    }
    .count { text-align: right; margin: 0; }
  `],
})
export class RankingComponent implements OnInit {
  private readonly api = inject(ApiService);

  protected readonly statIcon = statIcon;
  protected readonly navIcon = navIcon;

  protected readonly CATS: CatMeta[] = [
    { key: 'total', label: 'Gesamt', icon: navIcon('ranking'), glyph: '🏆' },
    { key: 'buildings', label: 'Gebäude', icon: navIcon('buildings'), glyph: '🏗️' },
    { key: 'research', label: 'Forschung', icon: navIcon('research'), glyph: '🔬' },
    { key: 'fleet', label: 'Flotte', icon: navIcon('fleet'), glyph: '🚀' },
    { key: 'defense', label: 'Verteidigung', icon: statIcon('shield'), glyph: '🛡️' },
  ];

  protected readonly board = signal<RankBoard>('players');
  protected readonly category = signal<RankCategory>('total');

  /** Offene „Anschreiben"-Maske (Spieler direkt aus der Rangliste anschreiben). */
  protected readonly compose = signal<{ id: string; name: string } | null>(null);

  protected readonly entries = signal<RankBoardEntry[]>([]);
  protected readonly me = signal<RankBoardEntry | null>(null);
  protected readonly myRanks = signal<Record<RankCategory, number> | null>(null);
  protected readonly total = signal(0);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);

  protected readonly showMeFooter = computed(() => {
    const m = this.me();
    return !!m && !this.entries().some((e) => e.is_self);
  });

  ngOnInit(): void {
    this.load();
  }

  protected setBoard(b: RankBoard): void {
    if (this.board() === b) {
      return;
    }
    this.board.set(b);
    this.load();
  }

  protected setCategory(c: RankCategory): void {
    if (this.category() === c) {
      return;
    }
    this.category.set(c);
    this.load();
  }

  private load(): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getRanking(this.board(), this.category()).subscribe({
      next: (r) => {
        this.entries.set(r.entries);
        this.me.set(r.me);
        this.myRanks.set(r.my_ranks);
        this.total.set(r.total);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Rangliste konnte nicht geladen werden.');
        this.loading.set(false);
      },
    });
  }

  protected catLabel(c: RankCategory): string {
    return this.CATS.find((x) => x.key === c)?.label ?? 'Punkte';
  }

  protected medal(rank: number): string {
    return rank === 1 ? '🥇' : rank === 2 ? '🥈' : rank === 3 ? '🥉' : '';
  }

  protected onIcoError(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
}
