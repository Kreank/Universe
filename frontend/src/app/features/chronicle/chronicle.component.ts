import { ChangeDetectionStrategy, Component, OnInit, inject, signal } from '@angular/core';
import { ApiService } from '../../core/services/api.service';
import { ChronicleEntry, ChronicleEventType, ChronicleKeyEvent } from '../../core/models/api.models';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';

interface EventMeta {
  label: string;
  glyph: string;
}

/** Deutsche Labels + Glyphen je key_event-Typ. */
const EVENT_META: Record<ChronicleEventType, EventMeta> = {
  battle: { label: 'Schlacht', glyph: '⚔️' },
  power: { label: 'Großmacht', glyph: '👑' },
  rise: { label: 'Aufstieg', glyph: '📈' },
  fall: { label: 'Niedergang', glyph: '📉' },
  betrayal: { label: 'Verrat', glyph: '🗡️' },
  diplomacy: { label: 'Diplomatie', glyph: '🤝' },
  cosmic_event: { label: 'Kosmisches Ereignis', glyph: '🌌' },
  quiet: { label: 'Ruhige Zeiten', glyph: '🕊️' },
};

/**
 * Chronik der Galaxie (Welle 3). Das lebendige Geschichtsbuch des Universums: Die KI-Historiker-Saga
 * der echten Server-Ereignisse als zeitliche Karten/Timeline. Pro Kapitel prominenter Titel + Zeitraum,
 * der erzaehlte body als gut lesbarer Fliesstext (Serifen-Typo), und aufklappbar die zugrundeliegenden
 * key_events als „Quellen dieses Kapitels". Keine nuechterne Logliste — eine epische Erzaehlung.
 */
@Component({
  selector: 'app-chronicle',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [EmptyStateComponent],
  template: `
    <section class="chron">
      <header class="chron-head">
        <span class="head-glyph" aria-hidden="true">📜</span>
        <div>
          <h1>Chronik der Galaxie</h1>
          <p class="faint small">
            Die niedergeschriebene Saga unseres Universums — Kapitel für Kapitel, von den Historikern
            aus den wahren Begebenheiten dieses Servers verfasst.
          </p>
        </div>
      </header>

      @if (loading() && !entries().length) {
        <p class="state">Die Chronik wird aufgeschlagen …</p>
      } @else if (error()) {
        <p class="state err">{{ error() }}</p>
      } @else if (!entries().length) {
        <app-empty-state art="empty_generic">
          Die Chronik beginnt gerade erst … Noch ruht die Feder der Historiker. Schreibe Geschichte,
          und die ersten Kapitel werden erscheinen.
        </app-empty-state>
      } @else {
        <ol class="timeline">
          @for (e of entries(); track e.id) {
            <li class="chapter">
              <span class="dot" aria-hidden="true"></span>
              <article class="card entry">
                <div class="when">{{ spanLabel(e) }}</div>
                <h2 class="title">{{ e.title }}</h2>
                <p class="byline faint small">Verfasst von den {{ narratorLabel(e.narrator) }}</p>

                <div class="prose">
                  @for (para of paragraphs(e.body); track $index) {
                    <p>{{ para }}</p>
                  }
                </div>

                @if (e.key_events.length) {
                  <div class="sources">
                    <button
                      class="src-toggle"
                      type="button"
                      [attr.aria-expanded]="isOpen(e.id)"
                      (click)="toggle(e.id)"
                    >
                      <span class="caret" [class.open]="isOpen(e.id)" aria-hidden="true">▸</span>
                      📜 Ereignisse dieses Kapitels
                      <span class="src-count">{{ e.key_events.length }}</span>
                    </button>

                    @if (isOpen(e.id)) {
                      <ul class="src-list">
                        @for (ev of e.key_events; track $index) {
                          <li class="src">
                            <span class="src-glyph" aria-hidden="true">{{ glyph(ev) }}</span>
                            <span class="src-body">
                              <span class="src-label">{{ label(ev) }}</span>
                              @if (facts(ev); as fs) {
                                @if (fs.length) {
                                  <span class="src-facts">
                                    @for (f of fs; track f.key) {
                                      <span class="fact"><span class="fk faint">{{ f.key }}:</span> {{ f.value }}</span>
                                    }
                                  </span>
                                }
                              }
                            </span>
                          </li>
                        }
                      </ul>
                    }
                  </div>
                }
              </article>
            </li>
          }
        </ol>

        @if (canLoadMore()) {
          <div class="more-row">
            <button class="btn btn-ghost" type="button" [disabled]="loading()" (click)="loadMore()">
              {{ loading() ? 'Lädt …' : 'Ältere Kapitel laden' }}
            </button>
          </div>
        }
      }
    </section>
  `,
  styles: [
    `
      .chron { display: flex; flex-direction: column; gap: var(--sp-4); max-width: 860px; }
      .chron-head { display: flex; align-items: center; gap: var(--sp-3); }
      .head-glyph { font-size: 2rem; flex: 0 0 auto; filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.6)); }
      .chron-head h1 { margin: 0; font-family: var(--font-display); }
      .faint { color: var(--text-faint); }
      .small { font-size: var(--fs-sm); }
      .state { color: var(--text-dim); padding: var(--sp-6) 0; }
      .state.err { color: var(--danger); }

      /* Vertikale Zeitleiste */
      .timeline { list-style: none; margin: 0; padding: 0; position: relative; }
      .timeline::before {
        content: '';
        position: absolute;
        left: 7px;
        top: 6px;
        bottom: 6px;
        width: 2px;
        background: linear-gradient(to bottom, var(--accent), transparent);
        opacity: 0.4;
      }
      .chapter { position: relative; padding-left: var(--sp-6); margin-bottom: var(--sp-5); }
      .dot {
        position: absolute;
        left: 0;
        top: var(--sp-4);
        width: 16px;
        height: 16px;
        border-radius: 50%;
        background: var(--surface-1);
        border: 2px solid var(--accent);
        box-shadow: 0 0 10px rgba(47, 227, 210, 0.5);
      }

      .entry { padding: var(--sp-5); }
      .when {
        font-family: var(--font-display);
        font-size: var(--fs-xs);
        text-transform: uppercase;
        letter-spacing: 0.14em;
        color: var(--accent);
        margin-bottom: var(--sp-1);
      }
      .title {
        margin: 0;
        font-family: var(--font-display);
        font-size: var(--fs-xl);
        line-height: 1.2;
      }
      .byline { margin: var(--sp-1) 0 var(--sp-3); }

      /* Erzaehlter Text: elegante Serifen-Typo, ruhig lesbar */
      .prose {
        font-family: Georgia, 'Times New Roman', 'Iowan Old Style', serif;
        font-size: 1.05rem;
        line-height: 1.75;
        color: var(--text);
      }
      .prose p { margin: 0 0 var(--sp-3); }
      .prose p:last-child { margin-bottom: 0; }
      .prose p:first-child::first-letter {
        font-size: 2.6em;
        line-height: 0.9;
        float: left;
        padding: 4px var(--sp-2) 0 0;
        color: var(--accent);
        font-weight: 700;
      }

      /* Quellen-Aufklapper */
      .sources { margin-top: var(--sp-4); border-top: 1px solid var(--border); padding-top: var(--sp-3); }
      .src-toggle {
        display: inline-flex;
        align-items: center;
        gap: var(--sp-2);
        cursor: pointer;
        background: transparent;
        border: none;
        padding: 0;
        font-family: var(--font-display);
        font-size: var(--fs-sm);
        color: var(--text-dim);
        transition: color var(--motion-fast) var(--ease-out);
      }
      .src-toggle:hover { color: var(--text); }
      .caret { display: inline-block; transition: transform var(--motion-fast) var(--ease-out); }
      .caret.open { transform: rotate(90deg); }
      .src-count {
        font-family: var(--font-mono);
        font-size: var(--fs-xs);
        background: var(--surface-2);
        border: 1px solid var(--border-strong);
        border-radius: var(--r-pill);
        padding: 0 var(--sp-2);
        color: var(--text-dim);
      }

      .src-list { list-style: none; margin: var(--sp-3) 0 0; padding: 0; display: flex; flex-direction: column; gap: var(--sp-2); }
      .src {
        display: flex;
        gap: var(--sp-2);
        align-items: flex-start;
        padding: var(--sp-2) var(--sp-3);
        background: rgba(255, 255, 255, 0.03);
        border: 1px solid var(--border);
        border-radius: var(--r-sm);
      }
      .src-glyph { flex: 0 0 auto; font-size: var(--fs-md); }
      .src-body { display: flex; flex-direction: column; gap: 2px; min-width: 0; }
      .src-label { font-weight: 600; color: var(--text); font-size: var(--fs-sm); }
      .src-facts { display: flex; flex-wrap: wrap; gap: var(--sp-1) var(--sp-3); font-size: var(--fs-xs); color: var(--text-dim); }
      .fact .fk { text-transform: capitalize; }

      .more-row { display: flex; justify-content: center; padding: var(--sp-2) 0 var(--sp-6); }

      @media (max-width: 640px) {
        .entry { padding: var(--sp-4); }
        .title { font-size: var(--fs-lg); }
        .prose { font-size: 1rem; }
      }
    `,
  ],
})
export class ChronicleComponent implements OnInit {
  private readonly api = inject(ApiService);

  private static readonly PAGE = 20;

  protected readonly entries = signal<ChronicleEntry[]>([]);
  protected readonly loading = signal(true);
  protected readonly error = signal<string | null>(null);
  /** true, solange die letzte Seite voll war (es koennten weitere Kapitel folgen). */
  protected readonly canLoadMore = signal(false);
  /** IDs der aktuell aufgeklappten „Quellen"-Bereiche. */
  protected readonly openIds = signal<Set<string>>(new Set());

  ngOnInit(): void {
    this.load(0);
  }

  protected loadMore(): void {
    this.load(this.entries().length);
  }

  private load(offset: number): void {
    this.loading.set(true);
    this.error.set(null);
    this.api.getChronicle(ChronicleComponent.PAGE, offset).subscribe({
      next: (list) => {
        this.entries.update((prev) => (offset === 0 ? list : [...prev, ...list]));
        this.canLoadMore.set(list.length >= ChronicleComponent.PAGE);
        this.loading.set(false);
      },
      error: () => {
        this.error.set('Die Chronik konnte nicht geladen werden.');
        this.loading.set(false);
      },
    });
  }

  protected isOpen(id: string): boolean {
    return this.openIds().has(id);
  }

  protected toggle(id: string): void {
    this.openIds.update((set) => {
      const next = new Set(set);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }

  /** Zeitraum bzw. Veroeffentlichungsdatum schoen formatiert. */
  protected spanLabel(e: ChronicleEntry): string {
    const start = this.fmt(e.span_start);
    const end = this.fmt(e.span_end);
    if (start && end) {
      return start === end ? start : `${start} – ${end}`;
    }
    return start || end || this.fmt(e.published_at) || 'Zeitloses Kapitel';
  }

  private fmt(iso: string | null): string {
    if (!iso) {
      return '';
    }
    const d = new Date(iso);
    if (Number.isNaN(d.getTime())) {
      return '';
    }
    return d.toLocaleDateString('de-DE', { day: '2-digit', month: 'long', year: 'numeric' });
  }

  protected narratorLabel(narrator: string): string {
    return narrator === 'historian' ? 'Historikern' : narrator;
  }

  /** Body in Absaetze zerlegen (Doppel-Umbruch bevorzugt, sonst Einzel-Umbruch). */
  protected paragraphs(body: string): string[] {
    const text = (body ?? '').trim();
    if (!text) {
      return [];
    }
    const parts = text.split(/\n{2,}/).map((p) => p.trim()).filter(Boolean);
    if (parts.length > 1) {
      return parts;
    }
    return text.split(/\n+/).map((p) => p.trim()).filter(Boolean);
  }

  protected glyph(ev: ChronicleKeyEvent): string {
    return EVENT_META[ev.type]?.glyph ?? '✶';
  }

  protected label(ev: ChronicleKeyEvent): string {
    return EVENT_META[ev.type]?.label ?? ev.type;
  }

  /** Freie Fakten-Felder eines key_event (alles ausser `type`) als lesbare Paare. */
  protected facts(ev: ChronicleKeyEvent): { key: string; value: string }[] {
    return Object.entries(ev)
      .filter(([k, v]) => k !== 'type' && v !== null && v !== undefined && v !== '')
      .map(([k, v]) => ({
        key: k.replace(/_/g, ' '),
        value: typeof v === 'object' ? JSON.stringify(v) : String(v),
      }));
  }
}
