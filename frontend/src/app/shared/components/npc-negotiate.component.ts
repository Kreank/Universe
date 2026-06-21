import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  output,
  signal,
} from '@angular/core';
import { DatePipe } from '@angular/common';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { NotificationService } from '../../core/services/notification.service';
import { BtnIconComponent } from './btn-icon.component';
import { navIcon } from '../../core/models/icon-assets';
import {
  NegotiateRequest,
  NpcOfferType,
  NpcRelation,
  NpcRelationStatus,
} from '../../core/models/api.models';

/** Anzeige-Metadaten je Beziehungsstatus (Glyph, Label, CSS-Klasse). */
const STATUS_META: Record<NpcRelationStatus, { glyph: string; label: string; cls: string }> = {
  neutral: { glyph: '◌', label: 'Neutral', cls: 'st-neutral' },
  allied: { glyph: '🤝', label: 'Verbündet', cls: 'st-allied' },
  ceasefire: { glyph: '🕊', label: 'Waffenstillstand', cls: 'st-ceasefire' },
  hostile: { glyph: '⚔', label: 'Feindlich', cls: 'st-hostile' },
  broken_pact: { glyph: '💔', label: 'Pakt gebrochen', cls: 'st-broken' },
};

const OFFER_META: Record<NpcOfferType, { glyph: string; label: string; blurb: string }> = {
  alliance: {
    glyph: '🤝',
    label: 'Bündnis',
    blurb: 'Ein festes Bündnis — das Imperium greift dich nicht mehr an. Schwer zu bekommen.',
  },
  ceasefire: {
    glyph: '🕊',
    label: 'Waffenstillstand',
    blurb: 'Befristeter Frieden ohne Gegenleistung. Läuft nach Ablauf der Frist aus.',
  },
  tribute: {
    glyph: '💰',
    label: 'Tribut',
    blurb: 'Du bietest Metall je Zyklus und erkaufst dir so anhaltenden Frieden.',
  },
};

/**
 * Verhandlungs-Overlay (Welle 1: verhandelbare KI-Imperien). Aus dem Galaxie-NPC-Popup
 * geoeffnet. Zeigt den Beziehungsstatus, laesst eine Angebotsart waehlen (Bündnis/
 * Waffenstillstand/Tribut) mit passenden Eingaben und sendet den Funkspruch.
 *
 * Die Antwort des Imperiums kommt ASYNCHRON als Funkspruch ins Postfach (KI-Funkverzoegerung
 * = Lore). Nach dem Senden zeigt das Panel deshalb klar „Funkspruch unterwegs…".
 *
 * Bei aktivem Pakt (Bündnis/Waffenstillstand) gibt es einen „Pakt brechen"-Button mit
 * Bestaetigung — Verrat hat Ruf-Konsequenzen.
 */
@Component({
  selector: 'app-npc-negotiate',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, DatePipe, BtnIconComponent],
  host: { '(document:keydown.escape)': 'close.emit()' },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup glass" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>

        <header class="head">
          <h2><app-btn-icon [src]="navIcon('diplomacy')" glyph="🕊" [size]="22" /> Kontakt aufnehmen</h2>
          @if (npcName()) { <span class="tname">🤖 {{ npcName() }}</span> }
        </header>

        <!-- Beziehungsstatus ------------------------------------------------- -->
        @if (relationLoading()) {
          <p class="muted small">Lade Beziehungsstatus…</p>
        } @else if (relation(); as rel) {
          <div class="rel" [class]="statusMeta(rel.status).cls">
            <div class="rel-top">
              <span class="rel-badge">{{ statusMeta(rel.status).glyph }} {{ statusMeta(rel.status).label }}</span>
              @if (rel.betrayed_by_player) { <span class="rel-flag warn">Du hast einen Pakt gebrochen</span> }
              @if (rel.betrayed_by_npc) { <span class="rel-flag warn">Das Imperium hat dich verraten</span> }
            </div>
            <div class="rel-facts small">
              @if (rel.alliance_since) { <span>Bündnis seit {{ rel.alliance_since | date: 'short' }}</span> }
              @if (rel.ceasefire_until) { <span>Frieden bis {{ rel.ceasefire_until | date: 'short' }}</span> }
              @if (rel.tribute_metal_per_cycle > 0) { <span>Tribut: {{ fmt(rel.tribute_metal_per_cycle) }} Metall/Zyklus</span> }
              @if (rel.message_count > 0) { <span class="faint">{{ rel.message_count }} Funksprüche</span> }
            </div>
          </div>
        }

        @if (sentOk()) {
          <!-- Funkspruch unterwegs (asynchrone KI-Antwort) ------------------- -->
          <div class="transmitting">
            <div class="tx-glyph">📡</div>
            <h3>Funkspruch unterwegs…</h3>
            <p class="muted">
              Dein Angebot wurde an {{ npcName() ?? 'das Imperium' }} gesendet. Das Imperium
              berät und antwortet selbst — die Antwort trifft in Kürze als Funkspruch in deinem
              Postfach ein.
            </p>
            <div class="tx-actions">
              <button class="btn btn-primary" type="button" (click)="goInbox()">📨 Zum Postfach</button>
              <button class="btn btn-ghost" type="button" (click)="close.emit()">Schließen</button>
            </div>
          </div>
        } @else {
          <!-- Angebotsart ---------------------------------------------------- -->
          <div class="section-label">Angebot</div>
          <div class="offer-tabs">
            @for (o of offers; track o) {
              <button type="button" class="otab" [class.active]="offer() === o" (click)="offer.set(o)">
                {{ offerMeta(o).glyph }} {{ offerMeta(o).label }}
              </button>
            }
          </div>
          <p class="blurb small">{{ offerMeta(offer()).blurb }}</p>

          <!-- Waffenstillstand: Dauer ---------------------------------------- -->
          @if (offer() === 'ceasefire') {
            <div class="field">
              <label>Dauer: <strong>{{ ceasefireHours() }} h</strong> <span class="faint">(max. {{ ceasefireMax() }} h)</span></label>
              <input type="range" min="1" [max]="ceasefireMax()" step="1"
                [ngModel]="ceasefireHours()" (ngModelChange)="ceasefireHours.set(+$event)" />
            </div>
          }

          <!-- Tribut: Metall je Zyklus --------------------------------------- -->
          @if (offer() === 'tribute') {
            <div class="field">
              <label>Tribut je Zyklus: <strong>{{ fmt(tributeMetal()) }} Metall</strong> <span class="faint">(max. {{ fmt(tributeMax()) }})</span></label>
              <input type="range" min="0" [max]="tributeMax()" [step]="tributeStep()"
                [ngModel]="tributeMetal()" (ngModelChange)="tributeMetal.set(+$event)" />
              <span class="faint small">Dein Planetenbestand begrenzt den tatsächlich gezahlten Tribut zusätzlich.</span>
            </div>
          }

          <!-- Freitext-Nachricht --------------------------------------------- -->
          <div class="field">
            <label>Nachricht <span class="faint">(optional)</span></label>
            <textarea rows="2" maxlength="280" placeholder="Ein paar Worte an das Imperium…"
              [ngModel]="message()" (ngModelChange)="message.set($event)"></textarea>
          </div>

          @if (errorHint(); as e) {
            <p class="hint small">{{ e }}</p>
          }

          <div class="actions">
            <button class="btn btn-primary" type="button" [disabled]="sending()" (click)="send()">
              {{ sending() ? 'Sende…' : (offerMeta(offer()).glyph + ' Funkspruch senden') }}
            </button>
          </div>

          <!-- Pakt brechen (nur bei aktivem Pakt) ---------------------------- -->
          @if (canBreak()) {
            <div class="break">
              @if (!confirmBreak()) {
                <button class="btn btn-danger btn-sm" type="button" (click)="confirmBreak.set(true)">
                  💔 Pakt brechen
                </button>
                <span class="faint small">Verrat macht das Imperium feindlich und schadet deinem Ruf.</span>
              } @else {
                <span class="warn small">Pakt wirklich brechen? Das ist Verrat — der Ruf-Schaden bleibt.</span>
                <div class="break-confirm">
                  <button class="btn btn-danger btn-sm" type="button" [disabled]="breaking()" (click)="doBreak()">
                    {{ breaking() ? 'Breche…' : 'Ja, verraten' }}
                  </button>
                  <button class="btn btn-ghost btn-sm" type="button" (click)="confirmBreak.set(false)">Abbrechen</button>
                </div>
              }
            </div>
          }
        }
      </div>
    </div>
  `,
  styles: [
    `
      .backdrop {
        position: fixed; inset: 0; z-index: 100; display: flex; align-items: center; justify-content: center;
        padding: var(--sp-4); background: rgba(4, 7, 14, 0.72);
        backdrop-filter: blur(4px); -webkit-backdrop-filter: blur(4px);
        animation: fade var(--motion-fast) var(--ease-out);
      }
      @keyframes fade { from { opacity: 0; } to { opacity: 1; } }
      .popup {
        position: relative; width: 100%; max-width: 520px; max-height: 88vh; overflow-y: auto;
        border-radius: var(--r-lg); padding: var(--sp-5);
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
        animation: pop var(--motion-base) var(--ease-out);
      }
      @keyframes pop { from { transform: translateY(8px) scale(0.98); opacity: 0; } to { transform: none; opacity: 1; } }
      .x {
        position: absolute; top: var(--sp-2); right: var(--sp-2); width: 32px; height: 32px; border-radius: var(--r-sm);
        background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text-dim);
        cursor: pointer; display: flex; align-items: center; justify-content: center;
        transition: color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .x:hover { color: var(--text); background: rgba(255,255,255,0.1); }
      .head { display: flex; align-items: baseline; flex-wrap: wrap; gap: var(--sp-2) var(--sp-3); padding-right: var(--sp-8); }
      .head h2 { margin: 0; font-size: var(--fs-lg); }
      .tname { color: var(--text-dim); font-size: var(--fs-sm); }

      .rel {
        margin-top: var(--sp-3); padding: var(--sp-3); border-radius: var(--r-md);
        border: 1px solid var(--border); background: rgba(255,255,255,0.02);
      }
      .rel-top { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-2); }
      .rel-badge {
        font-family: var(--font-display); font-size: var(--fs-sm); padding: 2px 10px; border-radius: var(--r-pill);
        border: 1px solid var(--border-strong); color: var(--text);
      }
      .rel.st-allied .rel-badge { color: var(--accent); border-color: var(--accent-dim); background: var(--accent-soft); }
      .rel.st-ceasefire .rel-badge { color: var(--success, #6fd08a); border-color: var(--border-strong); }
      .rel.st-hostile .rel-badge,
      .rel.st-broken .rel-badge { color: var(--danger); border-color: var(--danger); }
      .rel-flag { font-size: var(--fs-xs); }
      .rel-flag.warn { color: var(--warn); }
      .rel-facts { display: flex; flex-wrap: wrap; gap: var(--sp-1) var(--sp-3); margin-top: var(--sp-2); color: var(--text-dim); }

      .section-label,
      .field label { font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); }
      .section-label { margin: var(--sp-4) 0 var(--sp-2); }

      .offer-tabs { display: flex; flex-wrap: wrap; gap: var(--sp-1); }
      .otab {
        font-size: var(--fs-sm); padding: var(--sp-1) var(--sp-3); border-radius: var(--r-pill);
        background: rgba(255,255,255,0.04); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer;
        transition: color var(--motion-fast) var(--ease-out), border-color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .otab:hover { color: var(--text); border-color: var(--border-strong); }
      .otab.active { background: var(--accent-soft); color: var(--accent); border-color: var(--accent-dim); }
      .blurb { color: var(--text-dim); margin: var(--sp-2) 0 0; }

      .field { display: flex; flex-direction: column; gap: var(--sp-1); margin-top: var(--sp-3); }
      .field input[type='range'] { width: 100%; }
      .field textarea { width: 100%; resize: vertical; min-height: 48px; }

      .actions { margin-top: var(--sp-4); }
      .actions .btn { width: 100%; }
      .hint { color: var(--warn); margin: var(--sp-2) 0 0; }
      .small { font-size: var(--fs-sm); }
      .warn { color: var(--warn); }

      .break { margin-top: var(--sp-4); padding-top: var(--sp-3); border-top: 1px dashed var(--border); display: flex; flex-direction: column; gap: var(--sp-2); }
      .break-confirm { display: flex; gap: var(--sp-2); }

      .transmitting { text-align: center; padding: var(--sp-4) var(--sp-2) var(--sp-2); }
      .transmitting h3 { margin: var(--sp-2) 0; }
      .transmitting .muted { margin: 0 auto; max-width: 38ch; }
      .tx-glyph { font-size: 2.4rem; animation: pulse 1.6s var(--ease-out) infinite; }
      @keyframes pulse { 0%, 100% { opacity: 0.5; transform: scale(0.96); } 50% { opacity: 1; transform: scale(1.04); } }
      .tx-actions { display: flex; gap: var(--sp-2); justify-content: center; margin-top: var(--sp-4); }

      @media (max-width: 520px) {
        .backdrop { padding: var(--sp-2); }
        .popup { max-width: 100%; max-height: 94vh; padding: var(--sp-4); }
      }
    `,
  ],
})
export class NpcNegotiateComponent {
  protected readonly navIcon = navIcon;
  private readonly api = inject(ApiService);
  private readonly balanceSvc = inject(BalanceService);
  private readonly notify = inject(NotificationService);

  readonly npcId = input.required<string>();
  readonly npcName = input<string | null>(null);

  readonly close = output<void>();
  /** Beziehung hat sich geaendert (Pakt gebrochen / Kontakt) -> Aufrufer aktualisiert Badges. */
  readonly changed = output<void>();

  protected readonly offers: NpcOfferType[] = ['ceasefire', 'tribute', 'alliance'];
  protected readonly relation = signal<NpcRelation | null>(null);
  protected readonly relationLoading = signal(true);
  protected readonly offer = signal<NpcOfferType>('ceasefire');
  protected readonly ceasefireHours = signal(24);
  protected readonly tributeMetal = signal(0);
  protected readonly message = signal('');
  protected readonly sending = signal(false);
  protected readonly sentOk = signal(false);
  protected readonly errorHint = signal<string | null>(null);
  protected readonly confirmBreak = signal(false);
  protected readonly breaking = signal(false);

  protected statusMeta(s: NpcRelationStatus) {
    return STATUS_META[s] ?? STATUS_META.neutral;
  }
  protected offerMeta(o: NpcOfferType) {
    return OFFER_META[o];
  }

  /** Leitplanken aus balance.json (diplomacy-Block) — Slider-Limits. */
  private dipl(): Record<string, unknown> {
    return ((this.balanceSvc.value as Record<string, unknown>)?.['diplomacy'] as Record<string, unknown>) ?? {};
  }
  protected ceasefireMax(): number {
    return Number(this.dipl()['ceasefire_max_hours'] ?? 168);
  }
  protected tributeMax(): number {
    return Number(this.dipl()['tribute_max'] ?? 500000);
  }
  protected tributeStep(): number {
    return Math.max(1000, Math.round(this.tributeMax() / 50));
  }

  /** Aktiver Pakt -> brechbar (Verrat). */
  protected readonly canBreak = computed(() => {
    const s = this.relation()?.status;
    return s === 'allied' || s === 'ceasefire';
  });

  constructor() {
    // Beziehungsstatus laden, sobald die NPC-ID feststeht.
    effect(() => {
      const id = this.npcId();
      this.relationLoading.set(true);
      this.api.getNpcRelation(id).subscribe({
        next: (rel) => {
          this.relation.set(rel);
          this.relationLoading.set(false);
          // Sinnvolle Default-Angebotsart je nach Lage.
          if (rel.status === 'neutral' || rel.status === 'hostile' || rel.status === 'broken_pact') {
            this.offer.set('ceasefire');
          }
        },
        error: () => {
          this.relation.set(null);
          this.relationLoading.set(false);
        },
      });
      // Defaults setzen, sobald balance verfuegbar ist.
      this.ceasefireHours.set(Math.min(24, this.ceasefireMax()));
      this.tributeMetal.set(Math.min(this.tributeStep() * 5, this.tributeMax()));
    });
  }

  send(): void {
    if (this.sending()) {
      return;
    }
    this.errorHint.set(null);
    const offer = this.offer();
    const body: NegotiateRequest = { offer_type: offer };
    if (offer === 'ceasefire') {
      body.ceasefire_hours = this.ceasefireHours();
    } else if (offer === 'tribute') {
      body.tribute_metal = this.tributeMetal();
    }
    const msg = this.message().trim();
    if (msg) {
      body.message = msg;
    }
    this.sending.set(true);
    this.api.negotiateNpc(this.npcId(), body).subscribe({
      next: (res) => {
        this.sending.set(false);
        this.sentOk.set(true);
        this.notify.success(
          'Funkspruch gesendet',
          res.message ?? 'Die Antwort des Imperiums folgt in Kürze im Postfach.',
          '/transmissions',
        );
        this.changed.emit();
      },
      error: (err) => {
        this.sending.set(false);
        const status = err?.status;
        const detail = err?.error?.detail;
        if (status === 429) {
          this.errorHint.set(detail ?? 'Zu schnell — warte, bis das Imperium auf deinen letzten Funkspruch reagiert hat.');
        } else if (status === 403) {
          this.errorHint.set(detail ?? 'Dieses Imperium ist dir noch nicht bekannt — kläre es zuerst per Sonde auf.');
        } else {
          this.errorHint.set(detail ?? 'Verhandlung nicht möglich.');
        }
      },
    });
  }

  doBreak(): void {
    if (this.breaking()) {
      return;
    }
    this.breaking.set(true);
    this.api.breakNpcPact(this.npcId()).subscribe({
      next: (rel) => {
        this.breaking.set(false);
        this.confirmBreak.set(false);
        this.relation.set(rel);
        this.notify.warning('Pakt gebrochen', `Du hast ${this.npcName() ?? 'das Imperium'} verraten — der Ruf-Schaden bleibt.`);
        this.changed.emit();
      },
      error: (err) => {
        this.breaking.set(false);
        this.notify.warning('Fehler', err?.error?.detail ?? 'Pakt konnte nicht gebrochen werden.');
      },
    });
  }

  goInbox(): void {
    this.notify.info('Postfach', 'Die Antwort des Imperiums erscheint dort, sobald sie eintrifft.', '/transmissions');
    this.close.emit();
  }

  fmt(n: number): string {
    return Math.round(n).toLocaleString('de-DE');
  }
}
