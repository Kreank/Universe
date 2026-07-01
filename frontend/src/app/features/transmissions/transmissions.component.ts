import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DatePipe } from '@angular/common';
import { Router } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import { CombatSimPreloadService } from '../../core/services/combat-sim-preload.service';
import { Commander, DecisionChoice, Transmission } from '../../core/models/api.models';
import { BUILDING_META, DEFENSE_META, RESOURCE_META, SHIP_META, TECH_META, metaFor } from '../../core/models/display';
import { buildingIcon, defenseIcon, missionIcon, navIcon, resourceIcon, shipIcon, statIcon, statusIcon, techIcon, uiIcon } from '../../core/models/icon-assets';
import { transmissionStyles } from './transmission.styles';
import { CombatReportComponent } from './combat-report.component';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { MessageComposeComponent } from '../../shared/components/message-compose.component';
import { TabBarComponent } from '../../shared/components/tab-bar.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';

/** Eine Einheit-Zeile im Spionagebericht (Bild/Glyph + deutscher Name + Anzahl). */
interface IntelUnit {
  label: string;
  glyph: string;
  /** Echtes Asset-Bild; faellt via icon-tile auf den Glyph zurueck. */
  icon: string | null;
  count: number;
}

/** Aufbereitete Sicht auf einen Spionagebericht (aus transmission.decision_payload). */
interface SpyIntelView {
  name: string;
  kind: string;
  level: number;
  /** Ziel-Koordinaten (für Angreifen/Simulator-Buttons), falls im Intel enthalten. */
  coords: [number, number, number] | null;
  shipsTotal: number;
  defensesTotal: number;
  fleet: IntelUnit[] | null;
  defenses: IntelUnit[] | null;
  resources: IntelUnit[] | null;
  /** Gebäude-/Forschungsstufen (L3, nur Spieler-Ziele). */
  buildings: IntelUnit[] | null;
  research: IntelUnit[] | null;
  /** Aufgeklaerte Kampfforschung (ab Stufe 2, Spieler UND NPC). */
  combatTech: IntelUnit[] | null;
  /** NPC-Wirtschaft (abgeleitete Ausbau-/Forschungsstufe), sonst null. */
  economy: { development: number; research: number } | null;
  scannedAt: string | null;
  /** Roh-Maps (type→count/level) für den Simulator-Preload. */
  rawFleet: Record<string, number>;
  rawDefenses: Record<string, number>;
  rawResearch: Record<string, number>;
  rawCombatTech: Record<string, number>;
}

/**
 * Postfach / Funksprueche. Rendert Transmissionen typ-bewusst:
 * - ``spy_report`` wird aus dem strukturierten Payload als Aufklaerungs-Karte
 *   dargestellt (Gesamtstaerke + Flotte/Verteidigung/Ressourcen je Detailstufe),
 * - Forderungen (``requires_decision``) zeigen Entscheidungs-Buttons,
 * - alle uebrigen Funksprueche bleiben als (mehrzeiliger) Fliesstext.
 */
@Component({
  selector: 'app-transmissions',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DatePipe, CombatReportComponent, BtnIconComponent, IconTileComponent, MessageComposeComponent, TabBarComponent, EmptyStateComponent],
  template: `
    <h1>Postfach · Funksprüche</h1>
    <p class="sub">Eingehende Transmissionen und Crew-Forderungen.</p>

    <div class="bar-row">
      <app-tab-bar [tabs]="filterTabs()" [active]="onlyUnread() ? 'unread' : 'all'"
        (select)="onlyUnread.set($event === 'unread')" />
      <button class="btn btn-sm btn-primary" [disabled]="advisorBusy()" (click)="askAdvisor()"
        title="Der KI-Berater analysiert dein Imperium und schickt Empfehlungen ins Postfach">
        <app-btn-icon [src]="uiIcon('advisor')" glyph="🧠" /> {{ advisorBusy() ? 'Berater denkt…' : 'Berater fragen' }}
      </button>
      <button class="btn btn-sm btn-ghost" [disabled]="!unreadCount()" (click)="markAllRead()"
        title="Markiert alle Funksprüche als gelesen (offene Forderungen bleiben)">
        ✓ Alle gelesen{{ unreadCount() ? ' (' + unreadCount() + ')' : '' }}
      </button>
      <button class="btn btn-sm btn-ghost del-read" [disabled]="!readCount()" (click)="deleteRead()">
        <app-btn-icon [src]="uiIcon('trash')" glyph="🗑" /> Gelesene löschen{{ readCount() ? ' (' + readCount() + ')' : '' }}
      </button>
      <button class="btn btn-sm btn-ghost del-read" [disabled]="!clearableCount()" (click)="deleteAll()"
        title="Leert das Postfach (offene Forderungen bleiben erhalten)">
        <app-btn-icon [src]="uiIcon('trash')" glyph="🗑" /> Alles löschen{{ clearableCount() ? ' (' + clearableCount() + ')' : '' }}
      </button>
    </div>

    @if (visible().length) {
      <div class="grid list">
        @for (t of visible(); track t.id) {
          <article class="card msg" [class.unread]="!t.read" [class.demand]="t.requires_decision">
            <div class="msg-head">
              <span class="type-glyph"><app-btn-icon [src]="typeIconSrc(t)" [glyph]="typeGlyph(t)" [size]="16" /></span>
              <div class="msg-meta">
                <div class="title-row">
                  <h3>{{ t.subject }}</h3>
                  <span class="type-chip" [class]="'tc-' + t.type">{{ typeLabel(t) }}</span>
                </div>
                <span class="faint small">
                  @if (t.from_name) { <app-btn-icon [src]="navIcon('mail')" glyph="✉" [size]="14" /> Von {{ t.from_name }} } @else { {{ commanderName(t.commander_id) }} }
                  · {{ t.created_at | date: 'short' }}
                </span>
              </div>
              @if (!t.read) {
                <span class="dot-new" title="ungelesen"></span>
              }
            </div>

            @if (spyIntel(t); as intel) {
              <!-- Strukturierter Spionagebericht ----------------------------- -->
              <div class="intel">
                <div class="intel-top">
                  <span class="intel-target"><app-btn-icon [src]="uiIcon(intel.kind === 'player' ? 'player' : 'npc')" [glyph]="kindGlyph(intel.kind)" [size]="14" /> {{ intel.name }}</span>
                  <span class="lvl-badge" [attr.data-lvl]="intel.level" title="Aufklaerungsstufe">
                    Stufe {{ intel.level }}/3
                  </span>
                </div>

                <div class="intel-strength">
                  <span class="stat"><span class="stat-num">{{ fmt(intel.shipsTotal) }}</span> Schiffe</span>
                  <span class="stat"><span class="stat-num">{{ fmt(intel.defensesTotal) }}</span> Verteidigung</span>
                </div>

                @if (intel.fleet) {
                  <div class="intel-section">
                    <div class="intel-label"><app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="16" /> Flotte</div>
                    <div class="intel-rows">
                      @for (u of intel.fleet; track u.label) {
                        <span class="unit"><app-icon-tile class="u-ico" [glyph]="u.glyph" [src]="u.icon" [size]="20" variant="muted" />{{ u.count }}× {{ u.label }}</span>
                      }
                    </div>
                  </div>
                }
                @if (intel.defenses) {
                  <div class="intel-section">
                    <div class="intel-label"><app-btn-icon [src]="statIcon('shield')" glyph="🛡" [size]="16" /> Verteidigung</div>
                    <div class="intel-rows">
                      @for (u of intel.defenses; track u.label) {
                        <span class="unit"><app-icon-tile class="u-ico" [glyph]="u.glyph" [src]="u.icon" [size]="20" variant="muted" />{{ u.count }}× {{ u.label }}</span>
                      } @empty {
                        <span class="faint small">keine</span>
                      }
                    </div>
                  </div>
                }
                @if (intel.resources) {
                  <div class="intel-section">
                    <div class="intel-label"><app-btn-icon [src]="uiIcon('loot')" glyph="💰" [size]="16" /> Ressourcen</div>
                    <div class="intel-rows">
                      @for (u of intel.resources; track u.label) {
                        <span class="unit res"><app-icon-tile class="u-ico" [glyph]="u.glyph" [src]="u.icon" [size]="20" variant="muted" />{{ fmt(u.count) }} {{ u.label }}</span>
                      }
                    </div>
                  </div>
                }
                @if (intel.economy; as eco) {
                  <div class="intel-section">
                    <div class="intel-label"><app-btn-icon [src]="'assets/img/buildings/robot_factory.png'" glyph="🏭" [size]="16" /> Wirtschaft</div>
                    <div class="intel-rows">
                      <span class="unit" title="Wirtschaftlicher Ausbaustand — waechst mit Region, Spielerstaerke und Alter"><app-btn-icon [src]="navIcon('buildings')" glyph="🏗️" [size]="14" /> Ausbaustufe {{ eco.development }}</span>
                      <span class="unit" title="Forschungsstand des Imperiums"><app-btn-icon [src]="navIcon('research')" glyph="🔬" [size]="14" /> Forschung {{ eco.research }}</span>
                    </div>
                  </div>
                }
                @if (intel.buildings) {
                  <div class="intel-section">
                    <div class="intel-label"><app-btn-icon [src]="navIcon('buildings')" glyph="🏗️" [size]="16" /> Gebäude</div>
                    <div class="intel-rows">
                      @for (u of intel.buildings; track u.label) {
                        <span class="unit"><app-icon-tile class="u-ico" [glyph]="u.glyph" [src]="u.icon" [size]="20" variant="muted" />{{ u.label }} <strong>Stufe {{ u.count }}</strong></span>
                      }
                    </div>
                  </div>
                }
                @if (intel.research) {
                  <div class="intel-section">
                    <div class="intel-label"><app-btn-icon [src]="navIcon('research')" glyph="🔬" [size]="16" /> Forschung</div>
                    <div class="intel-rows">
                      @for (u of intel.research; track u.label) {
                        <span class="unit"><app-icon-tile class="u-ico" [glyph]="u.glyph" [src]="u.icon" [size]="20" variant="muted" />{{ u.label }} <strong>Stufe {{ u.count }}</strong></span>
                      }
                    </div>
                  </div>
                }
                @if (intel.combatTech) {
                  <div class="intel-section">
                    <div class="intel-label"><app-btn-icon [src]="statusIcon('attack')" glyph="⚔" [size]="16" /> Kampftech</div>
                    <div class="intel-rows">
                      @for (u of intel.combatTech; track u.label) {
                        <span class="unit"><app-icon-tile class="u-ico" [glyph]="u.glyph" [src]="u.icon" [size]="20" variant="muted" />{{ u.label }} <strong>Stufe {{ u.count }}</strong></span>
                      }
                    </div>
                  </div>
                }

                <!-- Aktionen: direkt angreifen / in Simulator laden -->
                @if (intel.coords) {
                  <div class="intel-actions">
                    <button class="btn btn-primary btn-sm" type="button" (click)="attackTarget(intel)" title="Flotte auf dieses Ziel ansetzen">
                      ⚔️ Angreifen
                    </button>
                    @if (intel.fleet || intel.defenses) {
                      <button class="btn btn-ghost btn-sm" type="button" (click)="loadInSimulator(intel)" title="Gegnerwerte in den Kampf-Simulator übernehmen">
                        🎯 In Simulator laden
                      </button>
                    }
                  </div>
                }

                @if (intel.level < 3) {
                  <p class="intel-hint small">
                    <app-btn-icon [src]="uiIcon('lock')" glyph="🔒" [size]="14" /> {{ intel.level < 2 ? 'Nur Gesamtstaerke aufgeklaert.' : 'Ressourcen verborgen.' }}
                    Mehr Sonden oder hoehere Spionagetechnik liefern Details.
                  </p>
                }
                @if (intel.scannedAt) {
                  <p class="faint small intel-time">Aufgeklaert: {{ intel.scannedAt | date: 'short' }}</p>
                }
              </div>
            } @else {
              <p class="body">{{ t.body }}</p>
            }

            @if (t.requires_decision) {
              @if (isEventDecision(t)) {
                <div class="decision">
                  <span class="muted small">Ereignis — deine Entscheidung:</span>
                  <div class="dec-buttons">
                    @for (c of eventChoices(t); track c.key) {
                      <button
                        class="btn btn-sm"
                        [class.btn-primary]="c.tone === 'primary'"
                        [class.btn-danger]="c.tone === 'danger'"
                        [class.btn-ghost]="c.tone === 'ghost'"
                        [disabled]="deciding() === t.id"
                        (click)="decideEvent(t, c.key)"
                      >{{ c.label }}</button>
                    }
                  </div>
                </div>
              } @else {
                <div class="decision">
                  <span class="muted small">Forderung — deine Entscheidung:</span>
                  <div class="dec-buttons">
                    <button
                      class="btn btn-sm btn-primary"
                      [disabled]="deciding() === t.id"
                      (click)="decide(t, 'accept')"
                    >Erfuellen</button>
                    <button
                      class="btn btn-sm btn-ghost"
                      [disabled]="deciding() === t.id"
                      (click)="decide(t, 'negotiate')"
                    >Verhandeln</button>
                    <button
                      class="btn btn-sm btn-danger"
                      [disabled]="deciding() === t.id"
                      (click)="decide(t, 'reject')"
                    >Ablehnen</button>
                  </div>
                </div>
              }
            } @else {
              <div class="msg-actions">
                @if (reportId(t); as rid) {
                  <button class="btn btn-sm btn-primary" (click)="openReport(t, rid)"><app-btn-icon [src]="missionIcon('attack')" glyph="⚔️" /> Bericht öffnen</button>
                }
                @if (t.from_player_id) {
                  <button class="btn btn-sm btn-primary" (click)="reply(t)"><app-btn-icon [src]="navIcon('mail')" glyph="✉" /> Antworten</button>
                }
                @if (!t.read) {
                  <button class="btn btn-sm btn-ghost" (click)="markRead(t)">Als gelesen markieren</button>
                }
                <button class="btn btn-sm btn-ghost del" (click)="deleteOne(t)" title="Funkspruch loeschen"><app-btn-icon [src]="uiIcon('trash')" glyph="🗑" /> Löschen</button>
              </div>
            }
          </article>
        }
      </div>
    } @else {
      <app-empty-state art="empty_inbox">
        {{ onlyUnread() ? 'Keine ungelesenen Funksprueche.' : 'Funkstille. Keine Transmissionen.' }}
      </app-empty-state>
    }

    @if (openReportId(); as rid) {
      <app-combat-report [reportId]="rid" (close)="openReportId.set(null)" />
    }
    @if (composeReply(); as c) {
      <app-message-compose
        [toPlayerId]="c.id"
        [toName]="c.name"
        [initialSubject]="c.subject"
        (close)="composeReply.set(null)"
      />
    }
  `,
  styles: [transmissionStyles],
})
export class TransmissionsComponent {
  private readonly api = inject(ApiService);
  protected readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly router = inject(Router);
  private readonly simPreload = inject(CombatSimPreloadService);

  /** Combat-relevante Tech-Keys, die der Simulator als Gegner-Forschung versteht. */
  private static readonly SIM_TECH_KEYS = [
    'weapons_tech', 'shield_tech', 'armor_tech',
    'weapons_mastery', 'shield_mastery', 'armor_mastery',
  ];

  /** „⚔️ Angreifen": öffnet den Flottenversand auf die Zielkoordinate (Mission Angriff). */
  attackTarget(intel: SpyIntelView): void {
    if (!intel.coords) {
      this.notify.warning('Keine Koordinaten', 'Dieser Bericht enthält kein angreifbares Ziel.');
      return;
    }
    const [g, s, p] = intel.coords;
    this.router.navigate(['/fleet'], { queryParams: { g, s, p, mission: 'attack' } });
  }

  /** „🎯 In Simulator laden": Gegner-Flotte/Verteidigung (+ spionierte Tech) vorbefüllen. */
  loadInSimulator(intel: SpyIntelView): void {
    const tech: Record<string, number> = {};
    for (const k of TransmissionsComponent.SIM_TECH_KEYS) {
      if (intel.rawResearch[k]) {
        tech[k] = Number(intel.rawResearch[k]);
      }
    }
    // Spionierte Kampftech (Stufe >=2, auch fuer NPC ohne Forschungs-Detail) ergaenzen/ueberschreiben.
    for (const [k, v] of Object.entries(intel.rawCombatTech)) {
      if (v) {
        tech[k] = Number(v);
      }
    }
    const coordStr = intel.coords ? `${intel.coords[0]}:${intel.coords[1]}:${intel.coords[2]}` : '';
    this.simPreload.set({
      ships: { ...intel.rawFleet },
      defenses: { ...intel.rawDefenses },
      tech,
      label: `${intel.name}${coordStr ? ' (' + coordStr + ')' : ''}`,
    });
    this.router.navigate(['/combat-sim']);
  }

  /** Asset-Pfad-Helfer fuers Template (Buttons mit Glyph-Fallback via app-btn-icon). */
  protected readonly missionIcon = missionIcon;
  protected readonly navIcon = navIcon;
  protected readonly statIcon = statIcon;
  protected readonly statusIcon = statusIcon;
  protected readonly uiIcon = uiIcon;

  protected readonly onlyUnread = signal(false);
  protected readonly advisorBusy = signal(false);
  protected readonly filterTabs = computed(() => [
    { key: 'all', label: 'Alle', glyph: '📨', icon: navIcon('mail') },
    { key: 'unread', label: 'Ungelesen', glyph: '●', icon: statusIcon('transmission_unread'), count: this.state.unreadTransmissions() },
  ]);
  protected readonly deciding = signal<string | null>(null);
  protected readonly openReportId = signal<string | null>(null);
  protected readonly composeReply = signal<{ id: string; name: string; subject: string } | null>(null);

  reply(t: Transmission): void {
    if (!t.from_player_id) {
      return;
    }
    const subj = t.subject?.startsWith('Re:') ? t.subject : `Re: ${t.subject ?? ''}`;
    this.composeReply.set({ id: t.from_player_id, name: t.from_name ?? 'Spieler', subject: subj });
  }

  private readonly commanderMap = computed(
    () => new Map<string, Commander>(this.state.commanders().map((c) => [c.id, c])),
  );

  protected readonly visible = computed(() => {
    // NPC-Diplomatie-Funksprueche leben im Diplomatie-Reiter, Expeditionsberichte im
    // Expeditionen-Screen — beide hier im allgemeinen Postfach ausblenden.
    const all = [...this.state.transmissions()]
      .filter((t) => t.type !== 'npc_diplomacy' && t.type !== 'expedition')
      .sort((a, b) => new Date(b.created_at).getTime() - new Date(a.created_at).getTime());
    return this.onlyUnread() ? all.filter((t) => !t.read) : all;
  });

  /** Anzahl loeschbarer (gelesener, nicht entscheidungs-offener) Funksprueche. */
  protected readonly readCount = computed(
    () => this.state.transmissions().filter((t) => t.read && !t.requires_decision).length,
  );

  /** Postfach-Funkspruch (Diplomatie/Expedition leben in eigenen Screens). */
  private isPostfach(t: Transmission): boolean {
    return t.type !== 'npc_diplomacy' && t.type !== 'expedition';
  }
  /** Ungelesene Postfach-Funksprueche ohne offene Forderung (fuer "Alle gelesen"). */
  protected readonly unreadCount = computed(
    () =>
      this.state
        .transmissions()
        .filter((t) => this.isPostfach(t) && !t.read && !t.requires_decision).length,
  );
  /** Leerbare Postfach-Funksprueche (alles ausser offenen Forderungen; fuer "Alles löschen"). */
  protected readonly clearableCount = computed(
    () =>
      this.state.transmissions().filter((t) => this.isPostfach(t) && !t.requires_decision).length,
  );

  constructor() {
    void this.state.reloadTransmissions();
  }

  decide(t: Transmission, choice: DecisionChoice): void {
    this.deciding.set(t.id);
    this.api.decideTransmission(t.id, choice).subscribe({
      next: (res) => {
        this.deciding.set(null);
        const sign = res.morale_delta > 0 ? '+' : '';
        this.notify.success('Entscheidung getroffen', `${res.message} (Moral ${sign}${res.morale_delta})`);
        this.state.upsertTransmission({ ...t, read: true, requires_decision: false });
        void this.state.reloadCommanders();
      },
      error: (err) => {
        this.deciding.set(null);
        this.notify.warning('Fehler', err?.error?.detail ?? 'Entscheidung fehlgeschlagen.');
      },
    });
  }

  /** Ist dies eine Event-Entscheidung (vs. Kommandeur-Forderung)? */
  isEventDecision(t: Transmission): boolean {
    const p = t.decision_payload as Record<string, unknown> | null;
    return !!p && typeof p === 'object' && p['kind'] === 'event';
  }

  /** Auswahl-Buttons für eine Event-Entscheidung (Label + Farbton je nach Wahl). */
  eventChoices(t: Transmission): { key: string; label: string; tone: string }[] {
    const p = t.decision_payload as Record<string, unknown> | null;
    const choices = (p?.['choices'] as string[]) ?? [];
    const isRaid = p?.['event_type'] === 'pirate_raid';
    const meta: Record<string, { label: string; tone: string }> = {
      // Bei Piraten-Razzien ist "bribe" eine Bestechung, sonst das Auszahlen (z. B. Streik).
      bribe: { label: isRaid ? 'Bestechen (Deuterium)' : 'Deuterium zahlen', tone: 'primary' },
      force: { label: 'Gewaltsam beenden', tone: 'danger' },
      // Bei Razzien heisst "wait" konkret: die Razzia kommen lassen.
      wait: { label: isRaid ? 'Angriff abwarten' : 'Aussitzen', tone: 'ghost' },
      board: { label: 'Entern', tone: 'primary' },
      ignore: { label: 'Ignorieren', tone: 'ghost' },
      help: { label: 'Helfen', tone: 'primary' },
    };
    return choices.map((c) => ({ key: c, label: meta[c]?.label ?? c, tone: meta[c]?.tone ?? 'ghost' }));
  }

  decideEvent(t: Transmission, choice: string): void {
    this.deciding.set(t.id);
    this.api.decideEvent(t.id, choice).subscribe({
      next: (res) => {
        this.deciding.set(null);
        this.notify.success('Entscheidung getroffen', res.message ?? 'Erledigt.');
        this.state.upsertTransmission({ ...t, read: true, requires_decision: false });
        void this.state.reloadActivePlanet();
      },
      error: (err) => {
        this.deciding.set(null);
        this.notify.warning('Fehler', err?.error?.detail ?? 'Entscheidung fehlgeschlagen.');
      },
    });
  }

  /** Extrahiert die report_id aus einem Kampfbericht-Funkspruch (sonst null). */
  reportId(t: Transmission): string | null {
    if (t.type !== 'combat_report') {
      return null;
    }
    const p = t.decision_payload as Record<string, unknown> | null;
    const id = p && typeof p === 'object' ? p['report_id'] : null;
    return typeof id === 'string' ? id : null;
  }

  /** Öffnet den Kampfbericht-Viewer und markiert den Funkspruch als gelesen. */
  openReport(t: Transmission, reportId: string): void {
    this.openReportId.set(reportId);
    if (!t.read) {
      this.markRead(t);
    }
  }

  markRead(t: Transmission): void {
    this.api.markTransmissionRead(t.id).subscribe({
      next: () => this.state.upsertTransmission({ ...t, read: true }),
      error: () => this.state.upsertTransmission({ ...t, read: true }),
    });
  }

  deleteOne(t: Transmission): void {
    // Optimistisch entfernen; bei Fehler neu laden.
    this.state.removeTransmission(t.id);
    this.api.deleteTransmission(t.id).subscribe({
      error: () => void this.state.reloadTransmissions(),
    });
  }

  askAdvisor(): void {
    if (this.advisorBusy()) {
      return;
    }
    this.advisorBusy.set(true);
    this.api.requestAdvisor().subscribe({
      next: () => {
        this.notify.success('Berater angefordert',
          'Der Stratege analysiert dein Imperium — der Rat trifft gleich im Postfach ein.');
        setTimeout(() => this.advisorBusy.set(false), 8000);
      },
      error: (err) => {
        this.advisorBusy.set(false);
        this.notify.warning('Berater nicht erreichbar', err?.error?.detail ?? 'Bitte spaeter erneut.');
      },
    });
  }

  deleteRead(): void {
    const n = this.readCount();
    if (!n) {
      return;
    }
    this.state.removeReadTransmissions();
    this.api.deleteReadTransmissions().subscribe({
      next: () => this.notify.success('Postfach aufgeraeumt', `${n} gelesene Funksprueche geloescht.`),
      error: () => void this.state.reloadTransmissions(),
    });
  }

  markAllRead(): void {
    const n = this.unreadCount();
    if (!n) {
      return;
    }
    this.state.markAllTransmissionsRead();
    this.api.markAllTransmissionsRead().subscribe({
      next: () => this.notify.success('Alles gelesen', `${n} Funksprueche als gelesen markiert.`),
      error: () => void this.state.reloadTransmissions(),
    });
  }

  deleteAll(): void {
    const n = this.clearableCount();
    if (!n) {
      return;
    }
    this.state.removeAllTransmissions();
    this.api.deleteAllTransmissions().subscribe({
      next: () =>
        this.notify.success('Postfach geleert', `${n} Funksprueche geloescht (offene Forderungen bleiben).`),
      error: () => void this.state.reloadTransmissions(),
    });
  }

  commanderName(id: string | null): string {
    if (!id) {
      return 'Kommandostab';
    }
    return this.commanderMap().get(id)?.name ?? 'Unbekannter Commander';
  }

  /** Tausenderpunkt-Formatierung (de-DE). */
  fmt(n: number): string {
    return Math.round(n).toLocaleString('de-DE');
  }

  /** Baut die strukturierte Aufklaerungs-Sicht, sonst null (-> Fliesstext-Fallback). */
  spyIntel(t: Transmission): SpyIntelView | null {
    if (t.type !== 'spy_report') {
      return null;
    }
    const p = t.decision_payload as Record<string, unknown> | null;
    if (!p || typeof p !== 'object') {
      return null;
    }
    const units = (
      map: unknown,
      metaMap: Record<string, { label: string; glyph: string }>,
      iconFor: (key: string) => string,
    ): IntelUnit[] | null => {
      if (!map || typeof map !== 'object') {
        return null;
      }
      const rows: IntelUnit[] = [];
      for (const [key, value] of Object.entries(map as Record<string, number>)) {
        const meta = metaFor(metaMap, key);
        rows.push({ label: meta.label, glyph: meta.glyph, icon: iconFor(key), count: Number(value) || 0 });
      }
      return rows.length ? rows : null;
    };
    const res = p['resources'] as Record<string, number> | undefined;
    const resources = res
      ? (['metal', 'crystal', 'deuterium'] as const)
          .filter((k) => res[k])
          .map((k) => {
            const meta = metaFor(RESOURCE_META, k);
            return { label: meta.label, glyph: meta.glyph, icon: resourceIcon(k), count: Number(res[k]) || 0 };
          })
      : null;

    const coords: [number, number, number] | null =
      p['galaxy'] != null && p['system'] != null && p['position'] != null
        ? [Number(p['galaxy']), Number(p['system']), Number(p['position'])]
        : null;
    const asMap = (v: unknown): Record<string, number> =>
      v && typeof v === 'object' ? (v as Record<string, number>) : {};

    return {
      name: String(p['name'] ?? 'Unbekanntes Ziel'),
      kind: String(p['kind'] ?? 'npc'),
      level: Number(p['level'] ?? 1),
      coords,
      shipsTotal: Number(p['ships_total'] ?? 0),
      defensesTotal: Number(p['defenses_total'] ?? 0),
      fleet: units(p['fleet'], SHIP_META, shipIcon),
      defenses: units(p['defenses'], DEFENSE_META, defenseIcon),
      resources: resources && resources.length ? resources : null,
      buildings: units(p['buildings'], BUILDING_META, buildingIcon),
      research: units(p['research'], TECH_META, techIcon),
      combatTech: units(p['combat_tech'], TECH_META, techIcon),
      economy: (() => {
        const e = p['economy'] as Record<string, number> | undefined;
        return e && typeof e === 'object'
          ? { development: Number(e['development'] ?? 0), research: Number(e['research'] ?? 0) }
          : null;
      })(),
      scannedAt: typeof p['scanned_at'] === 'string' ? (p['scanned_at'] as string) : null,
      rawFleet: asMap(p['fleet']),
      rawDefenses: asMap(p['defenses']),
      rawResearch: asMap(p['research']),
      rawCombatTech: asMap(p['combat_tech']),
    };
  }

  kindGlyph(kind: string): string {
    return kind === 'player' ? '👤' : '🤖';
  }

  typeGlyph(t: Transmission): string {
    if (t.type === 'npc_diplomacy') {
      return '🕊️';
    }
    if (t.requires_decision) {
      return '⚠️';
    }
    switch (t.type) {
      case 'spy_report':
        return '🛰️';
      case 'combat_report':
        return '⚔️';
      case 'reaction':
        return '🎙️';
      case 'big_moment':
        return '🏆';
      case 'system':
        return '🛰️';
      default:
        return '📡';
    }
  }

  typeIconSrc(t: Transmission): string | null {
    if (t.type === 'npc_diplomacy') {
      return statusIcon('broadcast');
    }
    if (t.requires_decision) {
      return statusIcon('alert');
    }
    switch (t.type) {
      case 'spy_report':
        return missionIcon('spy');
      case 'combat_report':
        return missionIcon('attack');
      case 'reaction':
        return statusIcon('broadcast');
      case 'big_moment':
        return statusIcon('victory');
      case 'system':
        return statusIcon('transmission_unread');
      default:
        return statusIcon('transmission_unread');
    }
  }

  typeLabel(t: Transmission): string {
    if (t.type === 'npc_diplomacy') {
      return 'Diplomatie';
    }
    if (t.requires_decision) {
      return 'Forderung';
    }
    switch (t.type) {
      case 'spy_report':
        return 'Spionagebericht';
      case 'combat_report':
        return 'Kampfbericht';
      case 'reaction':
        return 'Funkspruch';
      case 'big_moment':
        return 'Großmoment';
      case 'demand':
        return 'Forderung';
      case 'system':
        return 'System';
      default:
        return 'Funkspruch';
    }
  }
}
