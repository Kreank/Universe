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
import { Coordinate, EscortOffer, StationedFleet, TradeIndex, TradePartner, TradeProfile } from '../../core/models/api.models';
import { missionIcon, navIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
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
  imports: [FormsModule, BtnIconComponent, MessageComposeComponent, FleetDispatchComponent],
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
        <div class="panel-title">Mein Handelsangebot</div>
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
        <div class="panel-title">Handelspartner ({{ partners().length }})</div>
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
              <button class="btn btn-ghost btn-sm" type="button" (click)="message(p)"><app-btn-icon [src]="navIcon('mail')" glyph="✉" /> Nachricht</button>
              @if (p.coords) {
                <button class="btn btn-trade btn-sm" type="button" (click)="trade(p)"><app-btn-icon [src]="missionIcon('transport')" glyph="💱" /> Transport schicken</button>
              }
            </div>
          </div>
        }
      </div>

      <!-- Meine Patrouillen (Stationierung + Eskort-Angebot) -->
      <div class="card">
        <div class="panel-title">🛡 Meine Patrouillen ({{ stationed().length }})</div>
        @if (stationed().length === 0) {
          <p class="muted small">Keine stationierten Flotten. Schicke in der Galaxie eine Flotte mit Mission „Stationierung" (🚚 → Versand → Stationierung) in eine Region, die du schützen willst.</p>
        }
        @for (s of stationed(); track s.id) {
          <div class="partner">
            <div class="partner-main">
              <span class="mono">[{{ s.coords }}]</span>
              <span class="small muted">{{ s.ships_total }} 🚀</span>
              @if (s.fuel === null) {
                <span class="small tag-ok" title="Eigenes Gebiet — kein Treibstoff-Unterhalt">🏠 gratis</span>
              } @else {
                <span class="small" [class.tag-warn]="s.fuel < 1000" title="Vorgeschoben: Deuterium-Vorrat. Leer → automatische Rückkehr.">⛽ {{ s.fuel }} Deut</span>
              }
            </div>
            <div class="escort-edit">
              <label class="toggle small">
                <input type="checkbox" [ngModel]="s.escort_enabled" (ngModelChange)="updateEscort(s, { escort_enabled: $event })" />
                Eskorte anbieten
              </label>
              @if (s.escort_enabled) {
                <span class="small">Radius
                  <input class="mini" type="number" min="0" max="50" [ngModel]="s.escort_radius" (ngModelChange)="updateEscort(s, { escort_radius: +$event || 0 })" />
                  Sys · Gebühr
                  <input class="mini" type="number" min="0" max="10" step="0.5" [ngModel]="s.escort_fee_pct * 100" (ngModelChange)="updateEscort(s, { escort_fee_pct: (+$event || 0) / 100 })" />%
                </span>
              }
              @if (s.intercept_enabled) {
                <span class="small tag-ok" title="Aktive Abfang-Patrouille — gestartet über die Flotten-Mission „Abfangen“. Zum Beenden zurückrufen.">
                  📡 Abfang-Patrouille · Radius {{ s.intercept_radius }} Sys
                  @if (s.has_interdictor) { · Interdiktor (Pin) }
                  @else if (s.interceptors > 0) { · {{ s.interceptors }}× Abfangjäger }
                </span>
              }
              <button class="btn btn-ghost btn-sm" type="button" (click)="recall(s)"><app-btn-icon [src]="missionIcon('return')" glyph="↩" /> Zurückrufen</button>
            </div>
          </div>
        }
      </div>

      <!-- Eskort-Angebote anderer Spieler -->
      <div class="card">
        <div class="panel-title">🛰 Eskort-Angebote ({{ offers().length }})</div>
        @if (offers().length === 0) {
          <p class="muted small">Aktuell bietet niemand Geleitschutz an.</p>
        }
        @for (o of offers(); track o.id) {
          <div class="partner">
            <div class="partner-main">
              <span class="pname">🛡 {{ o.owner }}</span>
              <span class="mono small muted">[{{ o.coords }}] · Radius {{ o.radius }} Sys</span>
            </div>
            <div class="small muted">Kampfkraft ~{{ o.power }} · Gebühr {{ (o.fee_pct * 100).toFixed(1) }}% des Frachtwerts</div>
          </div>
        }
        <p class="muted small">Beim Handels-Versand kannst du deckende Eskorten auf deiner Route auswählen — sie senken das Routenrisiko gegen Gebühr.</p>
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
      /* Layout: Karten via globaler .card; gleichmaessige Abstaende ueber den Flow. */
      .trade {
        max-width: 880px;
        margin: 0 auto;
        padding-bottom: var(--sp-8);
        display: flex;
        flex-direction: column;
        gap: var(--sp-4);
      }
      .page-head h1 { margin: 0 0 var(--sp-1); }
      .page-head .muted { margin: 0; }

      /* Eigenes Angebots-Formular: responsives Raster, auf Mobile gestapelt. */
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
        gap: var(--sp-3);
        margin: var(--sp-3) 0;
      }

      /* Toggle-Reihe (Handel an/aus, Eskorte anbieten). */
      .toggle {
        display: inline-flex;
        align-items: center;
        gap: var(--sp-2);
        cursor: pointer;
        font-size: var(--fs-base);
        color: var(--text);
      }
      .toggle.small { font-size: var(--fs-sm); }
      .toggle input {
        width: 18px;
        height: 18px;
        flex: 0 0 auto;
        accent-color: var(--accent);
        cursor: pointer;
      }

      /* Inline-Textbutton "Globalen Kurs uebernehmen". */
      .link {
        background: none;
        border: none;
        color: var(--accent);
        cursor: pointer;
        font-family: var(--font-display);
        font-size: var(--fs-xs);
        letter-spacing: 0.04em;
        padding: 0;
        text-align: left;
        align-self: flex-start;
      }
      .link:hover { color: var(--accent-strong); text-decoration: underline; }

      .hint { color: var(--warn); font-size: var(--fs-sm); margin: var(--sp-1) 0; }
      .actions { margin-top: var(--sp-3); }

      /* Partner-/Listenzeilen mit Hairline-Trennern. */
      .partner { border-top: 1px solid var(--border); padding: var(--sp-3) 0; }
      .partner:first-of-type { border-top: none; }
      .partner-main { display: flex; align-items: baseline; flex-wrap: wrap; gap: var(--sp-2); }
      .pname { font-family: var(--font-display); font-weight: 600; color: var(--text); }
      .partner-offer { margin: var(--sp-1) 0; }
      .partner-note { margin-bottom: var(--sp-1); }
      .partner-act { display: flex; flex-wrap: wrap; gap: var(--sp-2); margin-top: var(--sp-1); }
      .small { font-size: var(--fs-sm); }

      /* Eskort-Einstellungen: dichte Inline-Steuerung, bricht auf Mobile um. */
      .escort-edit { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-3); margin-top: var(--sp-2); }
      .escort-edit .toggle { gap: var(--sp-1); }
      .mini { width: 56px; }

      /* Status-Pills: gratis (Akzent) / knapper Treibstoff (Warn). */
      .tag-ok {
        font-size: var(--fs-xs);
        font-weight: 600;
        color: var(--bg-deep);
        background: var(--accent);
        padding: 1px var(--sp-2);
        border-radius: var(--r-pill);
      }
      .tag-warn { color: var(--warn); font-weight: 600; }
    `,
  ],
})
export class TradeComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly notify = inject(NotificationService);

  /** Asset-Pfad-Helfer fuers Template (Buttons mit Glyph-Fallback via app-btn-icon). */
  protected readonly missionIcon = missionIcon;
  protected readonly navIcon = navIcon;

  protected readonly resList = [
    { key: 'metal' as const, glyph: '⛏️', label: 'Metall' },
    { key: 'crystal' as const, glyph: '💎', label: 'Kristall' },
    { key: 'deuterium' as const, glyph: '🛢️', label: 'Deuterium' },
  ];

  protected readonly index = signal<TradeIndex | null>(null);
  protected readonly partners = signal<TradePartner[]>([]);
  protected readonly stationed = signal<StationedFleet[]>([]);
  protected readonly offers = signal<EscortOffer[]>([]);

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
    this.reloadStationed();
    this.api.getEscortOffers().subscribe((list) => this.offers.set(list));
  }

  private reloadPartners(): void {
    this.api.getTradePartners().subscribe((list) => this.partners.set(list));
  }

  private reloadStationed(): void {
    this.api.getStationed().subscribe((list) => this.stationed.set(list));
  }

  updateEscort(s: StationedFleet, patch: Partial<StationedFleet>): void {
    const merged = { ...s, ...patch };
    this.api
      .setEscortOffer(s.id, {
        enabled: merged.escort_enabled,
        radius: merged.escort_radius,
        fee_pct: merged.escort_fee_pct,
      })
      .subscribe({
        next: (updated) => {
          this.stationed.update((list) => list.map((x) => (x.id === updated.id ? updated : x)));
        },
        error: (err) => this.notify.warning('Eskorte fehlgeschlagen', err?.error?.detail ?? 'Fehler.'),
      });
  }

  recall(s: StationedFleet): void {
    this.api.recallStation(s.id).subscribe({
      next: () => {
        this.notify.success('Rückruf gestartet', `Patrouille von [${s.coords}] kehrt heim.`);
        this.reloadStationed();
      },
      error: (err) => this.notify.warning('Rückruf fehlgeschlagen', err?.error?.detail ?? 'Fehler.'),
    });
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
