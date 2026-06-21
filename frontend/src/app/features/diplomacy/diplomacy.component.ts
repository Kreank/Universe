import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  DiplomacyCounterPayload,
  NegotiateRequest,
  NpcRelationListItem,
  NpcRelationStatus,
  Transmission,
} from '../../core/models/api.models';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { NpcNegotiateComponent } from '../../shared/components/npc-negotiate.component';

/** Anzeige-Metadaten je Beziehungsstatus (Glyph, Label, CSS-Klasse). */
const STATUS_META: Record<NpcRelationStatus, { glyph: string; label: string; cls: string }> = {
  neutral: { glyph: '◌', label: 'Neutral', cls: 'st-neutral' },
  allied: { glyph: '🤝', label: 'Verbündet', cls: 'st-allied' },
  ceasefire: { glyph: '🕊', label: 'Waffenstillstand', cls: 'st-ceasefire' },
  hostile: { glyph: '⚔', label: 'Feindlich', cls: 'st-hostile' },
  broken_pact: { glyph: '💔', label: 'Pakt gebrochen', cls: 'st-broken' },
};

/**
 * Diplomatie-Reiter (Welle 1+: verhandelbare KI-Imperien). Der zentrale Diplomatie-Hub:
 *
 * (a) BEZIEHUNGEN — alle Pakte/Spannungen des Spielers mit den KI-Imperien
 *     (Status, Tribut, Verrats-Flags, Fristen, Koordinaten). Pro Eintrag „Verhandeln"
 *     (oeffnet das npc-negotiate-Overlay) und bei aktivem Pakt „Pakt brechen".
 * (b) FUNKVERKEHR — die ``npc_diplomacy``-Funksprueche (KI-Antworten) chronologisch.
 *     Gegenangebote (decision_payload.kind == 'diplomacy_counter') tragen die Aktionen
 *     „Gegenangebot annehmen" (-> erneuter /negotiate mit proposed_terms) und „Ablehnen".
 *
 * Diese Diplomatie-Interaktion lebte frueher im Postfach — sie ist hierher gewandert.
 */
@Component({
  selector: 'app-diplomacy',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, RouterLink, EmptyStateComponent, NpcNegotiateComponent],
  template: `
    <section class="dipl">
      <header class="dipl-head">
        <span class="head-glyph" aria-hidden="true">🕊️</span>
        <div>
          <h1>Diplomatie</h1>
          <p class="faint small">
            Pakte, Tribute und der Funkverkehr mit den fremden KI-Imperien der Galaxie. Hier
            schliesst du Bündnisse, erkaufst Frieden — oder brichst dein Wort.
          </p>
        </div>
      </header>

      @if (loading() && !relations().length && !feed().length) {
        <p class="state">Diplomatische Kanäle werden geöffnet …</p>
      } @else if (!relations().length && !feed().length) {
        <app-empty-state art="empty_generic">
          Noch unterhältst du keine diplomatischen Beziehungen. Nimm in der
          <a routerLink="/galaxy">Galaxie</a> Kontakt zu einem entdeckten KI-Imperium auf, um zu
          verhandeln — über Bündnis, Waffenstillstand oder Tribut.
        </app-empty-state>
      } @else {
        <!-- (a) Beziehungen -------------------------------------------------- -->
        @if (relations().length) {
          <h2 class="sec">Beziehungen <span class="count">{{ relations().length }}</span></h2>
          <div class="rel-grid">
            @for (r of relations(); track r.npc_id) {
              <article class="card rel" [class]="statusMeta(r.status).cls">
                <div class="rel-top">
                  <div class="rel-name">
                    <span class="npc-glyph" aria-hidden="true">🤖</span>
                    <strong>{{ r.npc_name }}</strong>
                  </div>
                  <span class="rel-badge">{{ statusMeta(r.status).glyph }} {{ statusMeta(r.status).label }}</span>
                </div>

                <a class="coords mono" routerLink="/galaxy" [queryParams]="{ g: r.galaxy, s: r.system }"
                  title="Im Galaxie-Scanner ansteuern">📍 {{ r.coords }}</a>

                <div class="rel-facts small">
                  @if (r.alliance_since) { <span>🤝 Bündnis seit {{ r.alliance_since | date: 'short' }}</span> }
                  @if (r.ceasefire_until) { <span>🕊 Frieden bis {{ r.ceasefire_until | date: 'short' }}</span> }
                  @if (r.tribute_metal_per_cycle > 0) { <span>💰 Tribut {{ fmt(r.tribute_metal_per_cycle) }} Metall/Zyklus</span> }
                  @if (r.broken_at) { <span class="warn">💔 Gebrochen {{ r.broken_at | date: 'short' }}</span> }
                  @if (r.last_decision_at) { <span class="faint">Letzter Kontakt {{ r.last_decision_at | date: 'short' }}</span> }
                </div>

                @if (r.betrayed_by_player || r.betrayed_by_npc) {
                  <div class="rel-flags small">
                    @if (r.betrayed_by_player) { <span class="flag warn">Du hast einen Pakt gebrochen</span> }
                    @if (r.betrayed_by_npc) { <span class="flag warn">Das Imperium hat dich verraten</span> }
                  </div>
                }

                <div class="rel-actions">
                  <button class="btn btn-sm btn-primary" type="button" (click)="openNegotiate(r)">🕊 Verhandeln</button>
                  @if (canBreak(r)) {
                    @if (confirmBreak() === r.npc_id) {
                      <button class="btn btn-sm btn-danger" type="button" [disabled]="breaking()" (click)="doBreak(r)">
                        {{ breaking() ? 'Breche…' : 'Ja, verraten' }}
                      </button>
                      <button class="btn btn-sm btn-ghost" type="button" (click)="confirmBreak.set(null)">Abbrechen</button>
                    } @else {
                      <button class="btn btn-sm btn-danger" type="button" (click)="confirmBreak.set(r.npc_id)">💔 Pakt brechen</button>
                    }
                  }
                </div>
              </article>
            }
          </div>
        }

        <!-- (b) Funkverkehr -------------------------------------------------- -->
        <h2 class="sec">Diplomatischer Funkverkehr @if (feed().length) { <span class="count">{{ feed().length }}</span> }</h2>
        @if (feed().length) {
          <div class="feed">
            @for (t of feed(); track t.id) {
              <article class="card msg" [class.unread]="!t.read" [class.counter]="!!diplomacyCounter(t)">
                <div class="msg-head">
                  <span class="msg-glyph" aria-hidden="true">🕊️</span>
                  <div class="msg-meta">
                    <h3>{{ t.subject }}</h3>
                    <span class="faint small">{{ t.from_name ?? 'KI-Imperium' }} · {{ t.created_at | date: 'short' }}</span>
                  </div>
                  @if (!t.read) { <span class="dot-new" title="ungelesen"></span> }
                </div>

                <p class="body">{{ t.body }}</p>

                @if (diplomacyCounter(t); as counter) {
                  <div class="decision">
                    <span class="muted small">🕊 Gegenangebot des Imperiums — {{ counterSummary(counter) }}:</span>
                    <div class="dec-buttons">
                      <button class="btn btn-sm btn-primary" [disabled]="deciding() === t.id" (click)="acceptCounter(t, counter)">Gegenangebot annehmen</button>
                      <button class="btn btn-sm btn-ghost" [disabled]="deciding() === t.id" (click)="declineCounter(t)">Ablehnen</button>
                    </div>
                  </div>
                } @else if (!t.read) {
                  <div class="msg-actions">
                    <button class="btn btn-sm btn-ghost" (click)="markRead(t)">Als gelesen markieren</button>
                  </div>
                }
              </article>
            }
          </div>
        } @else {
          <p class="faint small empty-feed">Noch kein Funkverkehr. Antworten der Imperien auf deine Angebote erscheinen hier.</p>
        }
      }
    </section>

    @if (negotiate(); as n) {
      <app-npc-negotiate
        [npcId]="n.npcId"
        [npcName]="n.name"
        (changed)="reload()"
        (close)="negotiate.set(null)"
      />
    }
  `,
  styles: [
    `
      .dipl { display: flex; flex-direction: column; gap: var(--sp-4); }
      .dipl-head { display: flex; align-items: center; gap: var(--sp-3); }
      .head-glyph { font-size: 2rem; filter: drop-shadow(0 4px 16px rgba(47, 227, 210, 0.25)); }
      .dipl-head h1 { margin: 0; }
      .dipl-head p { margin: var(--sp-1) 0 0; max-width: 64ch; }

      .state { color: var(--text-dim); }
      .empty-feed { margin: 0; }

      .sec {
        font-family: var(--font-display); font-size: var(--fs-md); margin: var(--sp-2) 0 0;
        display: flex; align-items: center; gap: var(--sp-2);
        padding-bottom: var(--sp-2); border-bottom: 1px solid var(--border);
      }
      .count {
        font-size: var(--fs-xs); padding: 1px 8px; border-radius: var(--r-pill);
        background: rgba(255,255,255,0.06); border: 1px solid var(--border); color: var(--text-dim);
      }

      /* Beziehungen ---------------------------------------------------------- */
      .rel-grid {
        display: grid; gap: var(--sp-3);
        grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      }
      .rel { display: flex; flex-direction: column; gap: var(--sp-2); position: relative; overflow: hidden; }
      .rel::before {
        content: ''; position: absolute; inset: 0 auto 0 0; width: 3px; background: var(--border-strong);
      }
      .rel.st-allied::before { background: var(--accent); }
      .rel.st-ceasefire::before { background: var(--success, #6fd08a); }
      .rel.st-hostile::before,
      .rel.st-broken::before { background: var(--danger); }

      .rel-top { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); flex-wrap: wrap; }
      .rel-name { display: flex; align-items: center; gap: var(--sp-2); }
      .rel-name strong { font-size: var(--fs-base); }
      .npc-glyph { opacity: 0.8; }
      .rel-badge {
        font-family: var(--font-display); font-size: var(--fs-xs); padding: 2px 10px; border-radius: var(--r-pill);
        border: 1px solid var(--border-strong); color: var(--text); white-space: nowrap;
      }
      .rel.st-allied .rel-badge { color: var(--accent); border-color: var(--accent-dim); background: var(--accent-soft); }
      .rel.st-ceasefire .rel-badge { color: var(--success, #6fd08a); border-color: var(--border-strong); }
      .rel.st-hostile .rel-badge,
      .rel.st-broken .rel-badge { color: var(--danger); border-color: var(--danger); }

      .coords { color: var(--text-dim); text-decoration: none; font-size: var(--fs-sm); width: fit-content; }
      .coords:hover { color: var(--accent); }

      .rel-facts { display: flex; flex-wrap: wrap; gap: var(--sp-1) var(--sp-3); color: var(--text-dim); }
      .rel-flags { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
      .flag.warn, .warn { color: var(--warn); }
      .faint { color: var(--text-dim); opacity: 0.8; }

      .rel-actions { display: flex; flex-wrap: wrap; gap: var(--sp-2); margin-top: auto; padding-top: var(--sp-2); }

      /* Funkverkehr ---------------------------------------------------------- */
      .feed { display: flex; flex-direction: column; gap: var(--sp-2); }
      .msg { display: flex; flex-direction: column; gap: var(--sp-2); }
      .msg.unread { border-color: var(--accent-dim); }
      .msg.counter { border-color: var(--accent); box-shadow: 0 0 0 1px var(--accent-soft) inset; }
      .msg-head { display: flex; align-items: flex-start; gap: var(--sp-2); }
      .msg-glyph { font-size: 1.1rem; }
      .msg-meta { flex: 1; min-width: 0; }
      .msg-meta h3 { margin: 0; font-size: var(--fs-base); }
      .msg .body { margin: 0; white-space: pre-line; line-height: 1.5; }
      .dot-new { width: 8px; height: 8px; border-radius: 50%; background: var(--accent); flex: none; margin-top: 6px; }

      .decision { margin-top: var(--sp-1); padding-top: var(--sp-2); border-top: 1px dashed var(--border); }
      .dec-buttons { display: flex; flex-wrap: wrap; gap: var(--sp-2); margin-top: var(--sp-2); }
      .msg-actions { display: flex; gap: var(--sp-2); }
      .small { font-size: var(--fs-sm); }
      .muted { color: var(--text-dim); }

      @media (max-width: 560px) {
        .rel-grid { grid-template-columns: 1fr; }
      }
    `,
  ],
})
export class DiplomacyComponent {
  private readonly api = inject(ApiService);
  private readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  protected readonly relations = signal<NpcRelationListItem[]>([]);
  protected readonly loading = signal(true);

  protected readonly negotiate = signal<{ npcId: string; name: string | null } | null>(null);
  protected readonly confirmBreak = signal<string | null>(null);
  protected readonly breaking = signal(false);
  protected readonly deciding = signal<string | null>(null);

  /** Der diplomatische Funkverkehr: die ``npc_diplomacy``-Funksprueche, chronologisch (neueste zuerst). */
  protected readonly feed = computed(() =>
    this.state
      .transmissions()
      .filter((t) => t.type === 'npc_diplomacy')
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime()),
  );

  constructor() {
    this.reload();
    // Funkverkehr-Quelle aktuell halten (WS speist state.transmissions).
    void this.state.reloadTransmissions();
  }

  /** Beziehungs-Liste (neu) laden. */
  reload(): void {
    this.loading.set(true);
    this.api.getNpcRelations().subscribe({
      next: (rels) => {
        this.relations.set(rels);
        this.loading.set(false);
      },
      error: () => {
        this.relations.set([]);
        this.loading.set(false);
      },
    });
  }

  protected statusMeta(s: NpcRelationStatus) {
    return STATUS_META[s] ?? STATUS_META.neutral;
  }

  /** Aktiver Pakt -> brechbar (Verrat). */
  protected canBreak(r: NpcRelationListItem): boolean {
    return r.status === 'allied' || r.status === 'ceasefire';
  }

  openNegotiate(r: NpcRelationListItem): void {
    this.confirmBreak.set(null);
    this.negotiate.set({ npcId: r.npc_id, name: r.npc_name });
  }

  doBreak(r: NpcRelationListItem): void {
    if (this.breaking()) {
      return;
    }
    this.breaking.set(true);
    this.api.breakNpcPact(r.npc_id).subscribe({
      next: () => {
        this.breaking.set(false);
        this.confirmBreak.set(null);
        this.notify.warning('Pakt gebrochen', `Du hast ${r.npc_name} verraten — der Ruf-Schaden bleibt.`);
        this.reload();
      },
      error: (err) => {
        this.breaking.set(false);
        this.notify.warning('Fehler', err?.error?.detail ?? 'Pakt konnte nicht gebrochen werden.');
      },
    });
  }

  /** Liefert das Gegenangebot-Payload eines NPC-Diplomatie-Funkspruchs (sonst null). */
  diplomacyCounter(t: Transmission): DiplomacyCounterPayload | null {
    if (!t.requires_decision) {
      return null;
    }
    const p = t.decision_payload as Record<string, unknown> | null;
    if (!p || typeof p !== 'object' || p['kind'] !== 'diplomacy_counter') {
      return null;
    }
    return p as unknown as DiplomacyCounterPayload;
  }

  /** Kurze, lesbare Zusammenfassung der vom NPC geforderten Bedingungen. */
  counterSummary(c: DiplomacyCounterPayload): string {
    const t = c.proposed_terms ?? {};
    const bits: string[] = [];
    if (t.tribute_metal) {
      bits.push(`${this.fmt(t.tribute_metal)} Metall Tribut/Zyklus`);
    }
    if (t.ceasefire_hours) {
      bits.push(`${t.ceasefire_hours} Std. Waffenstillstand`);
    }
    return bits.length ? bits.join(', ') : 'neue Bedingungen';
  }

  /** Gegenangebot annehmen: ruft /negotiate erneut mit den vorgeschlagenen Konditionen. */
  acceptCounter(t: Transmission, c: DiplomacyCounterPayload): void {
    this.deciding.set(t.id);
    const body: NegotiateRequest = { offer_type: c.offer_type };
    if (c.proposed_terms?.tribute_metal) {
      body.tribute_metal = c.proposed_terms.tribute_metal;
    }
    if (c.proposed_terms?.ceasefire_hours) {
      body.ceasefire_hours = c.proposed_terms.ceasefire_hours;
    }
    this.api.negotiateNpc(c.npc_id, body).subscribe({
      next: (res) => {
        this.deciding.set(null);
        this.notify.success('Gegenangebot angenommen',
          res.message ?? 'Funkspruch unterwegs — die Bestätigung des Imperiums folgt in Kürze.');
        this.state.upsertTransmission({ ...t, read: true, requires_decision: false });
        this.reload();
      },
      error: (err) => {
        this.deciding.set(null);
        this.notify.warning('Annahme fehlgeschlagen', err?.error?.detail ?? 'Bitte später erneut.');
      },
    });
  }

  /** Gegenangebot ablehnen: Funkspruch nur als erledigt markieren (kein erneuter Kontakt). */
  declineCounter(t: Transmission): void {
    this.api.markTransmissionRead(t.id).subscribe({
      next: () => this.state.upsertTransmission({ ...t, read: true, requires_decision: false }),
      error: () => this.state.upsertTransmission({ ...t, read: true, requires_decision: false }),
    });
  }

  markRead(t: Transmission): void {
    this.api.markTransmissionRead(t.id).subscribe({
      next: () => this.state.upsertTransmission({ ...t, read: true }),
      error: () => this.state.upsertTransmission({ ...t, read: true }),
    });
  }

  /** Tausenderpunkt-Formatierung (de-DE). */
  fmt(n: number): string {
    return Math.round(n).toLocaleString('de-DE');
  }
}
