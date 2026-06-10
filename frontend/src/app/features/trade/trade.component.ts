import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { NotificationService } from '../../core/services/notification.service';
import { Coordinate, TradeIndex, TradePartner, TradeProfile } from '../../core/models/api.models';
import { MessageComposeComponent } from '../../shared/components/message-compose.component';
import { FleetDispatchComponent } from '../../shared/components/fleet-dispatch.component';

type Res = 'metal' | 'crystal' | 'deuterium';

/**
 * Handel-Hub (P2P): eigenes Handelsprofil pflegen (unverbindlicher Werbe-Kurs + an/aus)
 * und das Verzeichnis aktiver Handelspartner durchstoebern. Handel laeuft klassisch —
 * Kurs per Nachricht aushandeln, Lieferung mit normalen Transport-Flotten.
 */
@Component({
  selector: 'app-trade',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, MessageComposeComponent, FleetDispatchComponent],
  template: `
    <section class="trade">
      <header class="page-head">
        <h1>💱 Handel</h1>
        <p class="muted">
          Globaler Handelskurs (Handelszentren):
          @if (index(); as ix) {
            <span class="mono">⛏️ {{ ix.prices.metal }} · 💎 {{ ix.prices.crystal }} · 🛢️ {{ ix.prices.deuterium }}</span>
          } @else { <span class="muted">…</span> }
        </p>
      </header>

      <!-- Eigenes Profil -->
      <div class="card">
        <div class="card-title">Mein Handelsangebot</div>
        <label class="toggle">
          <input type="checkbox" [ngModel]="enabled()" (ngModelChange)="enabled.set($event)" />
          <span>Handel aktiviert — andere sehen mein Angebot in der Galaxie</span>
        </label>

        @if (enabled()) {
          <div class="grid">
            <div class="field">
              <label>Ich biete</label>
              <select [ngModel]="offer()" (ngModelChange)="offer.set($event)">
                @for (r of resList; track r.key) { <option [ngValue]="r.key">{{ r.glyph }} {{ r.label }}</option> }
              </select>
            </div>
            <div class="field">
              <label>Ich suche</label>
              <select [ngModel]="want()" (ngModelChange)="want.set($event)">
                @for (r of resList; track r.key) { <option [ngValue]="r.key">{{ r.glyph }} {{ r.label }}</option> }
              </select>
            </div>
            <div class="field">
              <label>Richtkurs (suche je 1 biete)</label>
              <input type="number" min="0" step="0.01" [ngModel]="rate()" (ngModelChange)="rate.set(+$event || null)"
                [placeholder]="suggestedRate() ? ('Vorschlag ' + suggestedRate()) : 'z. B. 0.66'" />
              @if (suggestedRate(); as sr) {
                <button class="link" type="button" (click)="rate.set(sr)">Globalen Kurs übernehmen ({{ sr }})</button>
              }
            </div>
          </div>
          @if (offer() === want()) {
            <p class="hint">Biete und Suche müssen verschieden sein.</p>
          }
          <div class="field">
            <label>Notiz (optional, frei verhandelbar)</label>
            <input type="text" maxlength="280" [ngModel]="note()" (ngModelChange)="note.set($event)"
              placeholder="z. B. Stammkunden bevorzugt, regelmäßige Lieferung gesucht" />
          </div>
        }

        <div class="actions">
          <button class="btn btn-primary btn-sm" type="button" [disabled]="!canSave() || saving()" (click)="save()">
            {{ saving() ? 'Speichere…' : 'Profil speichern' }}
          </button>
        </div>
        <p class="muted small">
          Der Kurs ist nur ein Richtwert. Den finalen Tausch handelst du per Nachricht aus; geliefert
          wird klassisch mit Transport-Flotten (hin und zurück).
        </p>
      </div>

      <!-- Partner-Verzeichnis -->
      <div class="card">
        <div class="card-title">Handelspartner ({{ partners().length }})</div>
        @if (partners().length === 0) {
          <p class="muted small">Aktuell bietet kein anderer Spieler Handel an.</p>
        }
        @for (p of partners(); track p.player_id) {
          <div class="partner">
            <div class="partner-main">
              <span class="pname">🧑‍🚀 {{ p.name }}</span>
              @if (p.coords) { <span class="mono small muted">[{{ p.coords }}]</span> }
            </div>
            <div class="partner-offer small">
              @if (p.offer && p.want) {
                {{ glyph(p.offer) }} {{ p.offer }} → {{ glyph(p.want) }} {{ p.want }}
                @if (p.rate) { <span class="mono">@ {{ p.rate }}</span> }
              } @else { <span class="muted">offen für Angebote</span> }
            </div>
            @if (p.note) { <div class="partner-note small muted">„{{ p.note }}"</div> }
            <div class="partner-act">
              <button class="btn btn-ghost btn-sm" type="button" (click)="message(p)">✉ Nachricht</button>
              @if (p.coords) {
                <button class="btn btn-trade btn-sm" type="button" (click)="trade(p)">💱 Transport schicken</button>
              }
            </div>
          </div>
        }
      </div>
    </section>

    @if (composeTo(); as c) {
      <app-message-compose
        [toPlayerId]="c.id"
        [toName]="c.name"
        [initialSubject]="c.subject"
        (close)="composeTo.set(null)"
      />
    }
    @if (dispatch(); as d) {
      <app-fleet-dispatch
        [target]="d.target"
        [targetName]="d.name"
        [initialMission]="'transport'"
        (close)="dispatch.set(null)"
      />
    }
  `,
  styles: [
    `
      .trade { max-width: 880px; margin: 0 auto; padding-bottom: 2rem; }
      .page-head h1 { margin: 0 0 0.2rem; }
      .page-head .muted { margin: 0 0 1rem; }
      .card {
        background: var(--surface-2); border: 1px solid var(--border); border-radius: var(--radius);
        padding: 1rem 1.1rem; margin-bottom: 1rem;
      }
      .card-title { font-size: 0.8rem; text-transform: uppercase; letter-spacing: 0.08em; color: var(--accent); margin-bottom: 0.7rem; }
      .toggle { display: flex; align-items: center; gap: 0.5rem; cursor: pointer; font-size: 0.9rem; }
      .toggle input { width: 18px; height: 18px; }
      .grid { display: flex; flex-wrap: wrap; gap: 0.8rem; margin: 0.8rem 0; }
      .field { display: flex; flex-direction: column; gap: 0.25rem; flex: 1 1 200px; }
      .field label { font-size: 0.74rem; color: var(--text-dim); }
      .field input, .field select { min-height: 32px; }
      .link { background: none; border: none; color: var(--accent); cursor: pointer; font-size: 0.74rem; padding: 0; text-align: left; }
      .hint { color: var(--warn); font-size: 0.8rem; margin: 0.2rem 0; }
      .actions { margin-top: 0.6rem; }

      .partner { border-top: 1px solid var(--border); padding: 0.6rem 0; }
      .partner:first-of-type { border-top: none; }
      .partner-main { display: flex; align-items: baseline; gap: 0.5rem; }
      .pname { font-weight: 600; }
      .partner-offer { margin: 0.2rem 0; }
      .partner-note { margin-bottom: 0.3rem; }
      .partner-act { display: flex; flex-wrap: wrap; gap: 0.4rem; }
      .small { font-size: 0.8rem; }
    `,
  ],
})
export class TradeComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly notify = inject(NotificationService);

  protected readonly resList = [
    { key: 'metal' as const, glyph: '⛏️', label: 'Metall' },
    { key: 'crystal' as const, glyph: '💎', label: 'Kristall' },
    { key: 'deuterium' as const, glyph: '🛢️', label: 'Deuterium' },
  ];

  protected readonly index = signal<TradeIndex | null>(null);
  protected readonly partners = signal<TradePartner[]>([]);

  protected readonly enabled = signal(false);
  protected readonly offer = signal<Res>('crystal');
  protected readonly want = signal<Res>('deuterium');
  protected readonly rate = signal<number | null>(null);
  protected readonly note = signal('');
  protected readonly saving = signal(false);

  protected readonly composeTo = signal<{ id: string; name: string; subject: string } | null>(null);
  protected readonly dispatch = signal<{ target: Coordinate; name: string } | null>(null);

  /** Globaler Richtkurs: gesuchte Ressource je 1 angebotener (price[offer]/price[want]). */
  protected readonly suggestedRate = computed<number | null>(() => {
    const p = this.index()?.prices;
    if (!p) {
      return null;
    }
    const pIn = p[this.offer()];
    const pOut = p[this.want()];
    if (!pIn || !pOut) {
      return null;
    }
    return Math.round((pIn / pOut) * 100) / 100;
  });

  ngOnInit(): void {
    this.api.getTradeIndex().subscribe((ix) => this.index.set(ix));
    this.api.getTradeProfile().subscribe((pr) => {
      this.enabled.set(pr.enabled);
      if (pr.offer) this.offer.set(pr.offer);
      if (pr.want) this.want.set(pr.want);
      this.rate.set(pr.rate);
      this.note.set(pr.note ?? '');
    });
    this.reloadPartners();
  }

  private reloadPartners(): void {
    this.api.getTradePartners().subscribe((list) => this.partners.set(list));
  }

  protected canSave(): boolean {
    return !this.enabled() || this.offer() !== this.want();
  }

  glyph(res: string | null): string {
    return this.resList.find((r) => r.key === res)?.glyph ?? '';
  }

  save(): void {
    if (!this.canSave() || this.saving()) {
      return;
    }
    this.saving.set(true);
    const body: TradeProfile = {
      enabled: this.enabled(),
      offer: this.enabled() ? this.offer() : null,
      want: this.enabled() ? this.want() : null,
      rate: this.enabled() ? this.rate() : null,
      note: this.note().trim() || null,
    };
    this.api.putTradeProfile(body).subscribe({
      next: () => {
        this.saving.set(false);
        this.notify.success('Gespeichert', this.enabled() ? 'Dein Handel ist aktiv.' : 'Handel deaktiviert.');
      },
      error: (err) => {
        this.saving.set(false);
        this.notify.warning('Speichern fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
      },
    });
  }

  message(p: TradePartner): void {
    const subj = p.offer && p.want
      ? `Handel: dein ${p.offer} gegen mein ${p.want}`
      : 'Handelsanfrage';
    this.composeTo.set({ id: p.player_id, name: p.name, subject: subj });
  }

  trade(p: TradePartner): void {
    if (!p.coords) {
      return;
    }
    const [g, s, pos] = p.coords.split(':').map((n) => parseInt(n, 10));
    this.dispatch.set({ target: { galaxy: g, system: s, position: pos }, name: p.name });
  }
}
