import {
  ChangeDetectionStrategy,
  Component,
  computed,
  inject,
  OnInit,
  signal,
} from '@angular/core';
import { DecimalPipe, DatePipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  Coordinate,
  EscortOffer,
  EscortJob,
  EscortJobMine,
  CoveringStation,
  CreateEscortJobRequest,
  FleetMission,
  PlayerHub,
  StationedFleet,
  TradeCenter,
  TradeCentersResponse,
  TradeHistoryEntry,
  TradeIndex,
  TradePartner,
  TradeProfile,
} from '../../core/models/api.models';
import { missionIcon, navIcon, statIcon, uiIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { MessageComposeComponent } from '../../shared/components/message-compose.component';
import { FleetDispatchComponent } from '../../shared/components/fleet-dispatch.component';
import { CostLineComponent } from '../../shared/components/cost-line.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { CountdownComponent } from '../../shared/components/countdown.component';

type Res = 'metal' | 'crystal' | 'deuterium';

/**
 * Handels-Hub (wie der Bergbau-Reiter): zeigt oben die aktiven NPC-Handelszentren in
 * Forschungs-Reichweite (Handelsnetz) — pro Zentrum Koordinaten, Spezialisierung, aktuelle
 * Kurse und Distanz, direkt anhandelbar — plus die Handelshistorie (mit wem zuletzt
 * gehandelt wurde). Darunter weiterhin der klassische P2P-Handel: eigenes Handelsprofil,
 * Partner-Verzeichnis, stationierte Flotten/Eskorten. P2P-Lieferung laeuft klassisch per
 * Transport-Flotte; der Tausch am Handelszentrum laeuft ueber die 'trade'-Mission.
 */
@Component({
  selector: 'app-trade',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [
    FormsModule,
    DecimalPipe,
    DatePipe,
    RouterLink,
    BtnIconComponent,
    MessageComposeComponent,
    FleetDispatchComponent,
    CostLineComponent,
    EmptyStateComponent,
    CountdownComponent,
  ],
  template: `
    <section class="trade">
      <header class="page-head">
        <h1><app-btn-icon [src]="navIcon('market')" glyph="💱" [size]="18" /> Handel</h1>
        <p class="muted">
          Globaler Handelskurs (Handelszentren):
          @if (index(); as ix) {
            <app-cost-line [cost]="ix.prices" />
          } @else { <span class="muted">…</span> }
        </p>
      </header>

      <!-- Handelszentren — NPC-Handel direkt in Forschungs-Reichweite (Muster: Bergbau-Übersicht) -->
      <div class="card">
        <div class="panel-title"><app-btn-icon [src]="navIcon('market')" glyph="💱" [size]="16" /> Handelszentren</div>
        @if (centers(); as c) {
          <div class="bar-row">
            <span class="chip">Handelsnetz Stufe {{ c.trade_network }}</span>
            <span class="chip ghost">Reichweite: {{ rangeLabel(c) }}</span>
            @if (c.building_bonus > 0) {
              <span class="chip ghost" title="Reichweiten-Bonus durch dein Handelszentrum">+{{ c.building_bonus }} via Handelszentrum</span>
            }
            <span class="chip ghost">{{ c.centers.length }} in Reichweite</span>
            <button class="btn btn-sm btn-ghost" type="button" (click)="reloadCenters()">↻ Aktualisieren</button>
          </div>

          @if (c.centers.length) {
            <div class="centers">
              @for (z of c.centers; track z.npc_id) {
                <article class="center">
                  <div class="c-top">
                    <a class="coord mono" [routerLink]="['/galaxy']" [queryParams]="{ g: z.galaxy, s: z.system }" title="Auf der Galaxie-Karte ansehen">[{{ z.coords }}]</a>
                    <span class="c-dist small muted">{{ distanceLabel(z) }}</span>
                  </div>
                  <div class="c-name">{{ z.name }}</div>
                  <div class="c-spec small muted">{{ specLabel(z.spec) }}</div>
                  <div class="c-prices small">
                    <span class="faint">Kurse je Einheit:</span>
                    <app-cost-line [cost]="z.prices" />
                  </div>
                  <div class="c-foot">
                    <button class="btn btn-trade btn-sm" type="button" (click)="openCenter(z)"><app-btn-icon [src]="navIcon('market')" glyph="💱" [size]="14" /> Handeln</button>
                  </div>
                </article>
              }
            </div>
          } @else {
            <app-empty-state art="empty_search">
              Keine Handelszentren in Reichweite. Erforsche <strong>Handelsnetz</strong> oder baue ein
              <strong>Handelszentrum</strong>, um weiter entfernte Galaxien anzubinden.
            </app-empty-state>
          }

          <!-- Spieler-Handelszentren — fremde Hubs in Handelsnetz-Reichweite (Tausch zahlt dem Besitzer Marge) -->
          @if (c.player_hubs.length) {
            <h3 class="sub"><app-btn-icon [src]="uiIcon('player')" glyph="🧑‍🚀" [size]="14" /> Spieler-Handelszentren ({{ c.player_hubs.length }})</h3>
            <div class="centers">
              @for (h of c.player_hubs; track h.planet_id) {
                <article class="center hub">
                  <div class="c-top">
                    <a class="coord mono" [routerLink]="['/galaxy']" [queryParams]="{ g: h.galaxy, s: h.system }" title="Auf der Galaxie-Karte ansehen">[{{ h.coords }}]</a>
                    <span class="c-dist small muted">{{ hubDistanceLabel(h) }}</span>
                  </div>
                  <div class="c-name">{{ h.name }} <span class="hub-badge">Spieler-Hub</span></div>
                  <div class="c-spec small muted"><app-btn-icon [src]="uiIcon('player')" glyph="🧑‍🚀" [size]="13" /> {{ h.owner_name }} · Besitzer-Marge {{ marginLabel(h.hub_margin) }}</div>
                  <div class="c-prices small">
                    <span class="faint">Kurse je Einheit:</span>
                    <app-cost-line [cost]="h.prices" />
                  </div>
                  <div class="c-foot">
                    <button class="btn btn-trade btn-sm" type="button" (click)="openHub(h)"><app-btn-icon [src]="navIcon('market')" glyph="💱" [size]="14" /> Handeln</button>
                  </div>
                </article>
              }
            </div>
          }

          <p class="muted small">
            Frachter ohne bewaffnete Eskorte werden auf der Route überfallen — der Tausch wird bei Ankunft am
            Handelszentrum zum dortigen Kurs abgerechnet. Mehr Reichweite über
            <a class="link-inline" routerLink="/research" [queryParams]="{ focus: 'trade_network' }">Forschung Handelsnetz</a>
            oder ein eigenes <a class="link-inline" routerLink="/buildings">Handelszentrum</a>. Dein eigenes
            Handelszentrum erscheint nicht in dieser Liste — es verdient automatisch mit, wenn fremde Spieler dort
            handeln (Einnahmen erscheinen unten in der <strong>Handelshistorie</strong>).
          </p>
        } @else {
          <p class="muted small">Lade Handelszentren…</p>
        }
      </div>

      <!-- Handelshistorie — mit wem zuletzt gehandelt wurde -->
      <div class="card">
        <div class="panel-title"><app-btn-icon [src]="uiIcon('time')" glyph="🕘" [size]="16" /> Handelshistorie</div>
        @if (history().length === 0) {
          <p class="muted small">Noch keine Handelsgeschäfte. Sobald du an einem Handelszentrum tauschst, erscheint es hier.</p>
        }
        @for (h of history(); track h.id) {
          <div class="hist">
            <div class="hist-main">
              <span class="pname">
                @if (h.partner_kind === 'npc') {
                  <app-btn-icon [src]="navIcon('market')" glyph="🏛" [size]="14" />
                } @else {
                  <app-btn-icon [src]="uiIcon('player')" glyph="🧑‍🚀" [size]="14" />
                }
                {{ h.partner_name }}
              </span>
              <span class="hist-kind small muted">{{ h.partner_kind === 'npc' ? 'Handelszentrum' : 'Spieler' }}</span>
            </div>
            <div class="hist-deal small">
              <span class="give">{{ glyph(h.offered_res) }} {{ h.offered_amount | number: '1.0-0' }}</span>
              <span class="arrow">→</span>
              <span class="get">{{ glyph(h.received_res) }} {{ h.received_amount | number: '1.0-0' }}</span>
            </div>
            <div class="hist-time faint small">{{ h.created_at | date: 'short' }}</div>
          </div>
        }
      </div>

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
              <span class="pname"><app-btn-icon [src]="uiIcon('player')" glyph="🧑‍🚀" [size]="14" /> {{ p.name }}</span>
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

      <!-- 🛡️ Eskort-Marktplatz: eigene Geleitschutz-Angebote verwalten + fremde durchsuchen -->
      <div class="card">
        <div class="panel-title"><app-btn-icon [src]="statIcon('shield')" glyph="🛡" [size]="16" /> Eskort-Marktplatz</div>
        <p class="muted small">
          Geleitschutz für Handelsrouten: <strong>biete</strong> deine stationierten Flotten als Eskorte an oder
          <strong>nutze</strong> fremde. Das <em>Annehmen</em> passiert beim Handel — beim Versand zu einem
          Handelszentrum wählst du die deckenden Eskorten auf deiner Route aus.
        </p>

        <!-- (a) Meine Eskort-Angebote — eigene stationierte Flotten als Geleitschutz -->
        <div class="market-head">
          <h3 class="sub"><app-btn-icon [src]="statIcon('shield')" glyph="🛡" [size]="14" /> Meine Eskort-Angebote ({{ stationed().length }})</h3>
          <button class="btn btn-primary btn-sm" type="button" (click)="offerEscort()">➕ Eskorte anbieten</button>
        </div>
        @if (stationed().length === 0) {
          <p class="muted small">Du bietest aktuell keinen Geleitschutz an. Mit „<app-btn-icon [src]="statIcon('shield')" glyph="🛡" [size]="14" /> Eskorte anbieten" stationierst du eine Flotte als Geleitschutz in eine Region (Radius + Gebühr), deren Handelsrouten du decken willst. Eine schon geparkte Flotte (Mission „Stationierung") kannst du hier per „Eskorte anbieten"-Schalter umstellen.</p>
        }
        @for (s of stationed(); track s.id) {
          <div class="partner">
            <div class="partner-main">
              <span class="mono">[{{ s.coords }}]</span>
              <span class="small muted">{{ s.ships_total }} <app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="14" /></span>
              @if (powerOf(s.id); as pw) {
                <span class="small muted" title="Geschätzte Kampfkraft dieser Eskorte"><app-btn-icon [src]="statIcon('attack')" glyph="⚔" [size]="14" /> ~{{ pw }}</span>
              }
              @if (s.fuel === null) {
                <span class="small tag-ok" title="Eigenes Gebiet — kein Treibstoff-Unterhalt"><app-btn-icon [src]="uiIcon('home')" glyph="🏠" [size]="14" /> gratis</span>
              } @else {
                <span class="small" [class.tag-warn]="s.fuel < 1000" title="Vorgeschoben: Deuterium-Vorrat. Leer → automatische Rückkehr."><app-btn-icon [src]="statIcon('fuel')" glyph="⛽" [size]="14" /> {{ s.fuel }} Deut</span>
              }
            </div>
            <div class="escort-edit">
              @if (s.mode === 'intercept') {
                <span class="small tag-ok" title="Aktive Abfang-Patrouille — auf der Flotten-Seite verwaltet.">
                  <app-btn-icon [src]="'assets/img/buildings/sensorphalanx.png'" glyph="📡" [size]="14" /> Abfangen · Radius {{ s.intercept_radius }} Sys
                  @if (s.has_interdictor) { · Interdiktor (Pin) }
                  @else if (s.interceptors > 0) { · {{ s.interceptors }}× Abfangjäger }
                </span>
                <span class="small muted">Eskorte deaktiviert — exklusiv zum Abfangen.</span>
              } @else {
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
                } @else {
                  <span class="small muted"><app-btn-icon [src]="missionIcon('deploy')" glyph="🚚" [size]="14" /> Geparkt — rein passiv.</span>
                }
              }
              <button class="btn btn-ghost btn-sm" type="button" (click)="recall(s)"><app-btn-icon [src]="missionIcon('return')" glyph="↩" /> Zurückrufen</button>
            </div>
          </div>
        }

        <!-- (b) Verfügbare Eskorten — fremde Angebote auf dem Markt durchsuchen -->
        <h3 class="sub mt"><app-btn-icon [src]="statIcon('shield')" glyph="🛰" [size]="14" /> Verfügbare Eskorten ({{ marketOffers().length }})</h3>
        @if (marketOffers().length === 0) {
          <p class="muted small">Aktuell bietet kein anderer Spieler Geleitschutz an.</p>
        }
        @for (o of marketOffers(); track o.id) {
          <div class="partner">
            <div class="partner-main">
              <span class="pname"><app-btn-icon [src]="statIcon('shield')" glyph="🛡" [size]="14" /> {{ o.owner }}</span>
              <span class="mono small muted">[{{ o.coords }}] · Radius {{ o.radius }} Sys</span>
            </div>
            <div class="small muted"><app-btn-icon [src]="statIcon('attack')" glyph="⚔" [size]="14" /> Kampfkraft ~{{ o.power }} · Gebühr {{ (o.fee_pct * 100).toFixed(1) }}% des Frachtwerts</div>
          </div>
        }
        @if (marketOffers().length) {
          <p class="muted small">💡 Diese Eskorten kannst du beim Handel auf passender Route auswählen: starte oben einen <strong>Handel an einem Handelszentrum</strong> in Reichweite — im Versand-Dialog hakst du dann die deckende Eskorte ab. Sie senkt das Routenrisiko gegen Gebühr.</p>
        }

        <!-- (c) Eskorte gesucht — offene Aufträge ANDERER, die du mit eigenen Stationen decken kannst -->
        <h3 class="sub mt"><app-btn-icon [src]="statIcon('shield')" glyph="🤝" [size]="14" /> Eskorte gesucht ({{ jobs().length }})</h3>
        @if (jobs().length === 0) {
          <app-empty-state art="empty_search">
            Aktuell sucht kein Spieler auf einer Route, die deine Eskort-Stationen decken können, nach
            Geleitschutz. Stationiere oben eine Flotte als <strong>Eskort-Angebot</strong>, um passende
            Gesuche hier zu sehen.
          </app-empty-state>
        }
        @for (j of jobs(); track j.id) {
          <div class="partner">
            <div class="partner-main">
              <span class="pname"><app-btn-icon [src]="uiIcon('player')" glyph="🧑‍🚀" [size]="14" /> {{ j.requester }}</span>
              <app-countdown class="small" [target]="j.expires_at" idleLabel="abgelaufen" />
            </div>
            <div class="route small">
              <a class="coord mono" [routerLink]="['/galaxy']" [queryParams]="{ g: j.origin_coords.galaxy, s: j.origin_coords.system }">[{{ j.origin }}]</a>
              <span class="arrow">→</span>
              <a class="coord mono" [routerLink]="['/galaxy']" [queryParams]="{ g: j.target_coords.galaxy, s: j.target_coords.system }">[{{ j.target }}]</a>
            </div>
            <div class="small muted job-meta">
              <span title="Frachtwert"><app-btn-icon [src]="navIcon('market')" glyph="📦" [size]="13" /> {{ j.cargo_value | number: '1.0-0' }}</span>
              <span title="Maximale Gebühr">max. {{ (j.max_fee_pct * 100).toFixed(1) }}%</span>
              @if (j.min_power > 0) {
                <span title="Mindest-Kampfkraft"><app-btn-icon [src]="statIcon('attack')" glyph="⚔" [size]="13" /> min. ~{{ j.min_power | number: '1.0-0' }}</span>
              }
            </div>
            <div class="job-accept">
              @if (j.covering_stations.length > 1) {
                <select class="small" [ngModel]="chosenStationId(j)" (ngModelChange)="setChosenStation(j.id, $event)">
                  @for (cs of j.covering_stations; track cs.station_id) {
                    <option [ngValue]="cs.station_id">[{{ cs.coords }}] · ~{{ cs.power | number: '1.0-0' }} ⚔ · {{ (cs.fee_pct * 100).toFixed(1) }}% ({{ cs.fee | number: '1.0-0' }})</option>
                  }
                </select>
              } @else if (chosenStation(j); as cs) {
                <span class="small muted">Station [{{ cs.coords }}] · {{ (cs.fee_pct * 100).toFixed(1) }}% Gebühr ({{ cs.fee | number: '1.0-0' }})</span>
              }
              <button class="btn btn-primary btn-sm" type="button" [disabled]="acceptingId() === j.id || j.covering_stations.length === 0" (click)="acceptJob(j)">
                {{ acceptingId() === j.id ? 'Nehme an…' : '✓ Annehmen' }}
              </button>
            </div>
          </div>
        }

        <!-- (d) Meine Eskort-Aufträge — eigene Gesuche verwalten + neues erstellen -->
        <div class="market-head mt">
          <h3 class="sub"><app-btn-icon [src]="statIcon('shield')" glyph="📋" [size]="14" /> Meine Eskort-Aufträge ({{ myJobs().length }})</h3>
          <button class="btn btn-primary btn-sm" type="button" (click)="toggleJobForm()">➕ Eskorte suchen / Auftrag erstellen</button>
        </div>

        @if (jobFormOpen()) {
          <div class="job-form">
            <div class="grid">
              <div class="field">
                <label>Ziel-Koordinaten</label>
                <div class="coord-in">
                  <input type="number" min="1" [ngModel]="jobTargetG()" (ngModelChange)="jobTargetG.set(+$event || null)" placeholder="G" />
                  <input type="number" min="1" [ngModel]="jobTargetS()" (ngModelChange)="jobTargetS.set(+$event || null)" placeholder="S" />
                  <input type="number" min="1" [ngModel]="jobTargetP()" (ngModelChange)="jobTargetP.set(+$event || null)" placeholder="P" />
                </div>
              </div>
              <div class="field">
                <label>Frachtwert</label>
                <input type="number" min="0" [ngModel]="jobCargo()" (ngModelChange)="jobCargo.set(+$event || null)" placeholder="z. B. 500000" />
              </div>
              <div class="field">
                <label>Max. Gebühr (%)</label>
                <input type="number" min="0" max="100" step="0.5" [ngModel]="jobMaxFee()" (ngModelChange)="jobMaxFee.set(+$event || null)" placeholder="z. B. 5" />
              </div>
              <div class="field">
                <label>Min. Kampfkraft (optional)</label>
                <input type="number" min="0" [ngModel]="jobMinPower()" (ngModelChange)="jobMinPower.set(+$event || null)" placeholder="0 = egal" />
              </div>
            </div>
            <label class="toggle small">
              <input type="checkbox" [ngModel]="jobOriginOn()" (ngModelChange)="jobOriginOn.set($event)" />
              <span>Start abweichend vom Heimatplanet</span>
            </label>
            @if (jobOriginOn()) {
              <div class="field">
                <label>Start-Koordinaten</label>
                <div class="coord-in">
                  <input type="number" min="1" [ngModel]="jobOriginG()" (ngModelChange)="jobOriginG.set(+$event || null)" placeholder="G" />
                  <input type="number" min="1" [ngModel]="jobOriginS()" (ngModelChange)="jobOriginS.set(+$event || null)" placeholder="S" />
                  <input type="number" min="1" [ngModel]="jobOriginP()" (ngModelChange)="jobOriginP.set(+$event || null)" placeholder="P" />
                </div>
              </div>
            }
            <div class="actions job-form-act">
              <button class="btn btn-primary btn-sm" type="button" [disabled]="!canSubmitJob() || submittingJob()" (click)="submitJob()">
                {{ submittingJob() ? 'Erstelle…' : 'Auftrag erstellen' }}
              </button>
              <button class="btn btn-ghost btn-sm" type="button" (click)="toggleJobForm()">Abbrechen</button>
            </div>
          </div>
        }

        @if (myJobs().length === 0) {
          <p class="muted small">Du hast keine offenen Eskort-Aufträge. Mit „➕ Eskorte suchen" stellst du einen Geleitschutz-Auftrag ein — passende Anbieter nehmen ihn an.</p>
        }
        @for (m of myJobs(); track m.id) {
          <div class="partner">
            <div class="partner-main">
              <span class="status-badge" [attr.data-st]="m.status">{{ statusLabel(m.status) }}</span>
              <app-countdown class="small" [target]="m.expires_at" idleLabel="abgelaufen" />
            </div>
            <div class="route small">
              <a class="coord mono" [routerLink]="['/galaxy']" [queryParams]="{ g: m.origin_coords.galaxy, s: m.origin_coords.system }">[{{ m.origin }}]</a>
              <span class="arrow">→</span>
              <a class="coord mono" [routerLink]="['/galaxy']" [queryParams]="{ g: m.target_coords.galaxy, s: m.target_coords.system }">[{{ m.target }}]</a>
            </div>
            <div class="small muted job-meta">
              <span title="Frachtwert"><app-btn-icon [src]="navIcon('market')" glyph="📦" [size]="13" /> {{ m.cargo_value | number: '1.0-0' }}</span>
              <span title="Maximale Gebühr">max. {{ (m.max_fee_pct * 100).toFixed(1) }}%</span>
              @if (m.min_power > 0) {
                <span title="Mindest-Kampfkraft"><app-btn-icon [src]="statIcon('attack')" glyph="⚔" [size]="13" /> min. ~{{ m.min_power | number: '1.0-0' }}</span>
              }
            </div>
            @if (m.status === 'accepted' && m.accepted_by) {
              <div class="small accepted-info">
                <app-btn-icon [src]="statIcon('shield')" glyph="🛡" [size]="13" /> Übernommen von <strong>{{ m.accepted_by }}</strong>
                @if (m.accepted_station_coords) { · Station [{{ m.accepted_station_coords.galaxy }}:{{ m.accepted_station_coords.system }}:{{ m.accepted_station_coords.position }}] }
                @if (m.accepted_fee_pct !== null) { · Gebühr {{ (m.accepted_fee_pct * 100).toFixed(1) }}% }
              </div>
            }
            @if (m.status === 'open' || m.status === 'accepted') {
              <div class="partner-act">
                <button class="btn btn-ghost btn-sm" type="button" [disabled]="cancellingId() === m.id" (click)="cancelJob(m)">
                  <app-btn-icon [src]="uiIcon('close')" glyph="✕" [size]="13" /> {{ cancellingId() === m.id ? 'Storniere…' : 'Stornieren' }}
                </button>
              </div>
            }
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
        [initialMission]="d.mission"
        [editableTarget]="d.editable ?? false"
        (sent)="onDispatched()"
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

      /* Handels-Hub: Status-Kopfzeile (Forschungsstufe/Reichweite) wie im Bergbau-Reiter. */
      .bar-row { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; margin: var(--sp-2) 0 var(--sp-3); }
      .chip { font-size: var(--fs-sm); background: var(--surface-2); border: 1px solid var(--border-strong); border-radius: var(--r-sm); padding: 2px var(--sp-2); }
      .chip.ghost { background: transparent; color: var(--text-dim); }

      /* Handelszentren-Raster (Karten je Zentrum, atmosphärisch). */
      .centers { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--sp-3); margin-bottom: var(--sp-3); }
      .center {
        display: flex; flex-direction: column; gap: var(--sp-1);
        padding: var(--sp-3); border: 1px solid var(--border); border-radius: var(--r-md);
        background: rgba(255,255,255,0.02);
        transition: border-color var(--motion-fast) var(--ease-out);
      }
      .center:hover { border-color: var(--border-strong); }
      /* Spieler-Hubs: dezent vom NPC-Zentrum abgesetzt (Akzentkante + Badge). */
      .center.hub { border-color: var(--accent-dim); background: var(--accent-soft); }
      .hub-badge {
        font-size: var(--fs-xs); font-weight: 600; color: var(--accent);
        border: 1px solid var(--accent-dim); border-radius: var(--r-pill);
        padding: 0 var(--sp-2); margin-left: var(--sp-1); vertical-align: 1px;
      }
      .c-top { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-2); }
      .coord { color: var(--text); text-decoration: none; border-bottom: 1px dotted var(--border-strong); }
      .coord:hover { color: var(--accent); }
      .c-name { font-family: var(--font-display); font-weight: 600; color: var(--text); }
      .c-prices { display: flex; align-items: center; flex-wrap: wrap; gap: var(--sp-2); margin: var(--sp-1) 0; }
      .c-foot { display: flex; justify-content: flex-end; margin-top: auto; }
      .faint { color: var(--text-faint); }
      .link-inline { color: var(--accent); }
      .link-inline:hover { color: var(--accent-strong); }

      /* Handelshistorie: kompakte Zeilen Geber → Nehmer mit Zeitstempel. */
      .hist { border-top: 1px solid var(--border); padding: var(--sp-2) 0; }
      .hist:first-of-type { border-top: none; }
      .hist-main { display: flex; align-items: baseline; flex-wrap: wrap; gap: var(--sp-2); }
      .hist-deal { display: flex; align-items: center; gap: var(--sp-2); margin: var(--sp-1) 0; font-variant-numeric: tabular-nums; }
      .hist-deal .arrow { color: var(--text-faint); }
      .hist-deal .get { color: var(--accent); }
      .hist-time { font-variant-numeric: tabular-nums; }

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

      /* Eskort-Marktplatz: Unter-Überschriften + Kopfzeile mit Aktion. */
      .sub {
        font-family: var(--font-display); font-size: var(--fs-sm); font-weight: 600;
        color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.06em;
        margin: var(--sp-3) 0 var(--sp-1);
      }
      .sub.mt { margin-top: var(--sp-4); border-top: 1px solid var(--border); padding-top: var(--sp-3); }
      .market-head { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); flex-wrap: wrap; margin: var(--sp-3) 0 var(--sp-1); }
      .market-head .sub { margin: 0; }

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

      /* Eskort-Gesuche-Board: Routenzeile, Meta-Chips, Annehmen-Reihe, Formular. */
      .route { display: flex; align-items: center; gap: var(--sp-2); margin: var(--sp-1) 0; }
      .route .arrow { color: var(--text-faint); }
      .job-meta { display: flex; align-items: center; flex-wrap: wrap; gap: var(--sp-3); font-variant-numeric: tabular-nums; }
      .job-accept { display: flex; align-items: center; flex-wrap: wrap; gap: var(--sp-2); margin-top: var(--sp-2); }
      .accepted-info { margin-top: var(--sp-1); color: var(--accent); }
      .job-form {
        border: 1px solid var(--border-strong); border-radius: var(--r-md);
        background: rgba(255, 255, 255, 0.02); padding: var(--sp-3); margin: var(--sp-2) 0 var(--sp-3);
      }
      .job-form .grid { margin: 0 0 var(--sp-2); }
      .coord-in { display: flex; gap: var(--sp-1); }
      .coord-in input { width: 100%; min-width: 0; }
      .job-form-act { display: flex; gap: var(--sp-2); margin-top: var(--sp-3); }

      /* Status-Badge eigener Aufträge — farbcodiert nach Zustand. */
      .status-badge {
        font-size: var(--fs-xs); font-weight: 600; text-transform: uppercase; letter-spacing: 0.05em;
        border-radius: var(--r-pill); padding: 1px var(--sp-2);
        border: 1px solid var(--border-strong); color: var(--text-dim);
      }
      .status-badge[data-st='open'] { color: var(--accent); border-color: var(--accent-dim); }
      .status-badge[data-st='accepted'] { color: var(--bg-deep); background: var(--accent); border-color: var(--accent); }
      .status-badge[data-st='cancelled'],
      .status-badge[data-st='expired'] { color: var(--warn); border-color: var(--warn); }
    `,
  ],
})
export class TradeComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly notify = inject(NotificationService);

  /** Asset-Pfad-Helfer fuers Template (Buttons mit Glyph-Fallback via app-btn-icon). */
  protected readonly missionIcon = missionIcon;
  protected readonly navIcon = navIcon;
  protected readonly statIcon = statIcon;
  protected readonly uiIcon = uiIcon;

  protected readonly resList = [
    { key: 'metal' as const, glyph: '⛏️', label: 'Metall' },
    { key: 'crystal' as const, glyph: '💎', label: 'Kristall' },
    { key: 'deuterium' as const, glyph: '🛢️', label: 'Deuterium' },
  ];

  protected readonly index = signal<TradeIndex | null>(null);
  protected readonly partners = signal<TradePartner[]>([]);
  protected readonly stationed = signal<StationedFleet[]>([]);
  protected readonly offers = signal<EscortOffer[]>([]);

  // --- Eskort-Gesuche-Board ---
  /** Offene Aufträge anderer, die meine Stationen decken können. */
  protected readonly jobs = signal<EscortJob[]>([]);
  /** Meine eigenen Eskort-Aufträge. */
  protected readonly myJobs = signal<EscortJobMine[]>([]);
  /** Pro Auftrag gewählte deckende Station (jobId → stationId). */
  protected readonly jobStation = signal<Record<string, string>>({});
  protected readonly acceptingId = signal<string | null>(null);
  protected readonly cancellingId = signal<string | null>(null);

  // Formular „Eskorte suchen / Auftrag erstellen".
  protected readonly jobFormOpen = signal(false);
  protected readonly submittingJob = signal(false);
  protected readonly jobTargetG = signal<number | null>(null);
  protected readonly jobTargetS = signal<number | null>(null);
  protected readonly jobTargetP = signal<number | null>(null);
  protected readonly jobCargo = signal<number | null>(null);
  protected readonly jobMaxFee = signal<number | null>(null);
  protected readonly jobMinPower = signal<number | null>(null);
  protected readonly jobOriginOn = signal(false);
  protected readonly jobOriginG = signal<number | null>(null);
  protected readonly jobOriginS = signal<number | null>(null);
  protected readonly jobOriginP = signal<number | null>(null);
  /** Handels-Hub: NPC-Handelszentren in Reichweite + Forschungs-/Reichweiten-Kopf. */
  protected readonly centers = signal<TradeCentersResponse | null>(null);
  /** Handelshistorie (mit wem zuletzt gehandelt wurde). */
  protected readonly history = signal<TradeHistoryEntry[]>([]);

  protected readonly enabled = signal(false);
  protected readonly offer = signal<Res>('crystal');
  protected readonly want = signal<Res>('deuterium');
  protected readonly rate = signal<number | null>(null);
  protected readonly note = signal('');
  protected readonly saving = signal(false);

  protected readonly composeTo = signal<{ id: string; name: string; subject: string } | null>(null);
  protected readonly dispatch = signal<{
    target: Coordinate | null;
    name: string;
    mission: FleetMission;
    /** W2: editierbares Ziel (Eskorte irgendwo stationieren) statt festem Handelsziel. */
    editable?: boolean;
  } | null>(null);

  /** W2: nur fremde Eskort-Angebote (eigene über die Stationierungs-IDs herausfiltern). */
  protected readonly marketOffers = computed<EscortOffer[]>(() => {
    const mine = new Set(this.stationed().map((s) => s.id));
    return this.offers().filter((o) => !mine.has(o.id));
  });
  /** W2: Kampfkraft je Eskort-Angebot (id → power) — auch für die eigenen Angebote. */
  private readonly offerPower = computed<Map<string, number>>(() => {
    const m = new Map<string, number>();
    for (const o of this.offers()) {
      m.set(o.id, o.power);
    }
    return m;
  });

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
    this.reloadCenters();
    this.reloadHistory();
    this.reloadOffers();
    this.reloadJobs();
    this.reloadMyJobs();
  }

  private reloadPartners(): void {
    this.api.getTradePartners().subscribe((list) => this.partners.set(list));
  }

  /** NPC-Handelszentren in Reichweite (Forschung Handelsnetz) neu laden. */
  reloadCenters(): void {
    this.api.getTradeCenters().subscribe({
      next: (c) => this.centers.set(c),
      error: () => {},
    });
  }

  private reloadHistory(): void {
    this.api.getTradeHistory(30).subscribe({
      next: (h) => this.history.set(h.entries),
      error: () => {},
    });
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
    // P2P: klassischer Transport (Kurs per Nachricht ausgehandelt).
    this.dispatch.set({ target: { galaxy: g, system: s, position: pos }, name: p.name, mission: 'transport' });
  }

  /** Öffnet den Handels-Versand (Biete/Wunsch) zu einem NPC-Handelszentrum. */
  openCenter(z: TradeCenter): void {
    this.dispatch.set({
      target: { galaxy: z.galaxy, system: z.system, position: z.position },
      name: z.name,
      mission: 'trade',
    });
  }

  /** Öffnet den Handels-Versand zu einem fremden Spieler-Handelszentrum (gleicher 'trade'-Flow). */
  openHub(h: PlayerHub): void {
    this.dispatch.set({
      target: { galaxy: h.galaxy, system: h.system, position: h.position },
      name: `${h.name} · ${h.owner_name}`,
      mission: 'trade',
    });
  }

  /** Marge eines Spieler-Hubs als Prozent (z. B. 0.02 → „2 %"). */
  marginLabel(margin: number): string {
    return `${(margin * 100).toFixed(margin * 100 < 1 ? 1 : 0)} %`;
  }

  /** Distanz-Label eines Spieler-Hubs (0 = eigene Galaxie). */
  hubDistanceLabel(h: PlayerHub): string {
    return h.distance_galaxies <= 0
      ? 'eigene Galaxie'
      : `${h.distance_galaxies} Galaxie${h.distance_galaxies === 1 ? '' : 'n'} entfernt`;
  }

  /** Nach erfolgreichem Versand (Handel oder Eskorte-Stationierung): alles Relevante auffrischen. */
  onDispatched(): void {
    this.reloadHistory();
    this.reloadCenters();
    this.reloadStationed();
    this.reloadOffers();
  }

  /** Aktive Eskort-Angebote (Verzeichnis) neu laden. */
  private reloadOffers(): void {
    this.api.getEscortOffers().subscribe((list) => this.offers.set(list));
  }

  // --- Eskort-Gesuche-Board ---

  /** Offene Aufträge anderer (von meinen Stationen deckbar) neu laden. */
  private reloadJobs(): void {
    this.api.getEscortJobs().subscribe({
      next: (list) => this.jobs.set(list),
      error: () => {},
    });
  }

  /** Eigene Eskort-Aufträge neu laden. */
  private reloadMyJobs(): void {
    this.api.getMyEscortJobs().subscribe({
      next: (list) => this.myJobs.set(list),
      error: () => {},
    });
  }

  /** Gewählte (oder erste) deckende Station eines offenen Auftrags. */
  chosenStation(j: EscortJob): CoveringStation | null {
    if (j.covering_stations.length === 0) {
      return null;
    }
    const sel = this.jobStation()[j.id];
    return j.covering_stations.find((s) => s.station_id === sel) ?? j.covering_stations[0];
  }

  chosenStationId(j: EscortJob): string {
    return this.chosenStation(j)?.station_id ?? '';
  }

  setChosenStation(jobId: string, stationId: string): void {
    this.jobStation.update((m) => ({ ...m, [jobId]: stationId }));
  }

  /** Auftrag annehmen — erste gewinnt; bei 409 Liste neu laden. */
  acceptJob(j: EscortJob): void {
    const station = this.chosenStation(j);
    if (!station || this.acceptingId()) {
      return;
    }
    this.acceptingId.set(j.id);
    this.api.acceptEscortJob(j.id, station.station_id).subscribe({
      next: () => {
        this.acceptingId.set(null);
        this.notify.success('Eskorte übernommen', `Auftrag von ${j.requester} angenommen.`);
        this.reloadJobs();
        this.reloadMyJobs();
      },
      error: (err) => {
        this.acceptingId.set(null);
        if (err?.status === 409) {
          this.notify.warning('Schon vergeben', 'Dieser Auftrag ist nicht mehr offen — Liste wird aktualisiert.');
        } else {
          this.notify.warning('Annehmen fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
        }
        this.reloadJobs();
      },
    });
  }

  /** Eigenen Auftrag stornieren (open/accepted). */
  cancelJob(m: EscortJobMine): void {
    if (this.cancellingId()) {
      return;
    }
    this.cancellingId.set(m.id);
    this.api.deleteEscortJob(m.id).subscribe({
      next: () => {
        this.cancellingId.set(null);
        this.notify.success('Storniert', `Auftrag [${m.origin}] → [${m.target}] storniert.`);
        this.reloadMyJobs();
        this.reloadJobs();
      },
      error: (err) => {
        this.cancellingId.set(null);
        this.notify.warning('Stornieren fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
        this.reloadMyJobs();
      },
    });
  }

  toggleJobForm(): void {
    this.jobFormOpen.update((v) => !v);
  }

  protected canSubmitJob(): boolean {
    const t = this.jobTargetG() && this.jobTargetS() && this.jobTargetP();
    const ok =
      !!t &&
      (this.jobCargo() ?? 0) > 0 &&
      (this.jobMaxFee() ?? -1) >= 0;
    if (!ok) {
      return false;
    }
    if (this.jobOriginOn()) {
      return !!(this.jobOriginG() && this.jobOriginS() && this.jobOriginP());
    }
    return true;
  }

  /** Neuen Eskort-Auftrag erstellen (Origin default Heimatplanet). */
  submitJob(): void {
    if (!this.canSubmitJob() || this.submittingJob()) {
      return;
    }
    this.submittingJob.set(true);
    const body: CreateEscortJobRequest = {
      target: { galaxy: this.jobTargetG()!, system: this.jobTargetS()!, position: this.jobTargetP()! },
      cargo_value: this.jobCargo()!,
      max_fee_pct: (this.jobMaxFee() ?? 0) / 100,
    };
    if ((this.jobMinPower() ?? 0) > 0) {
      body.min_power = this.jobMinPower()!;
    }
    if (this.jobOriginOn()) {
      body.origin = { galaxy: this.jobOriginG()!, system: this.jobOriginS()!, position: this.jobOriginP()! };
    }
    this.api.createEscortJob(body).subscribe({
      next: () => {
        this.submittingJob.set(false);
        this.notify.success('Auftrag erstellt', 'Dein Eskort-Gesuch ist offen — Anbieter können es annehmen.');
        this.resetJobForm();
        this.reloadMyJobs();
        this.reloadJobs();
      },
      error: (err) => {
        this.submittingJob.set(false);
        this.notify.warning('Erstellen fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
      },
    });
  }

  private resetJobForm(): void {
    this.jobFormOpen.set(false);
    this.jobTargetG.set(null);
    this.jobTargetS.set(null);
    this.jobTargetP.set(null);
    this.jobCargo.set(null);
    this.jobMaxFee.set(null);
    this.jobMinPower.set(null);
    this.jobOriginOn.set(false);
    this.jobOriginG.set(null);
    this.jobOriginS.set(null);
    this.jobOriginP.set(null);
  }

  /** Status-Label eines eigenen Auftrags. */
  statusLabel(status: EscortJobMine['status']): string {
    switch (status) {
      case 'open':
        return 'Offen';
      case 'accepted':
        return 'Übernommen';
      case 'cancelled':
        return 'Storniert';
      case 'expired':
        return 'Abgelaufen';
      case 'done':
        return 'Erledigt';
      default:
        return status;
    }
  }

  /** W2: „➕ Eskorte anbieten" — Versand-Overlay mit editierbarem Ziel + Eskort-Mission öffnen. */
  offerEscort(): void {
    this.dispatch.set({ target: null, name: 'Geleitschutz stationieren', mission: 'escort', editable: true });
  }

  /** Geschätzte Kampfkraft einer eigenen Eskorte (aus dem Angebots-Verzeichnis), falls aktiv. */
  powerOf(id: string): number | null {
    return this.offerPower().get(id) ?? null;
  }

  /** Spezialisierungs-Label (data-driven; aktuell nur 'trade_center'). */
  specLabel(spec: string): string {
    return spec === 'trade_center' ? 'Handelszentrum' : spec;
  }

  /** Reichweiten-Kopf: „nur eigene Galaxie" bzw. „eigene Galaxie + N". */
  rangeLabel(c: TradeCentersResponse): string {
    return c.range <= 0 ? 'nur eigene Galaxie' : `eigene Galaxie + ${c.range}`;
  }

  /** Distanz-Label eines Zentrums (0 = eigene Galaxie). */
  distanceLabel(z: TradeCenter): string {
    return z.distance_galaxies <= 0
      ? 'eigene Galaxie'
      : `${z.distance_galaxies} Galaxie${z.distance_galaxies === 1 ? '' : 'n'} entfernt`;
  }
}
