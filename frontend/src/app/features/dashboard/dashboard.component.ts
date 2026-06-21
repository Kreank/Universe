import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  signal,
} from '@angular/core';
import { RouterLink } from '@angular/router';
import { firstValueFrom } from 'rxjs';
import { AttackAlert, GameStateService } from '../../core/services/game-state.service';
import { ApiService } from '../../core/services/api.service';
import { NotificationService } from '../../core/services/notification.service';
import { ShortNumberPipe } from '../../shared/pipes/short-number.pipe';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { JumpGateDialogComponent } from '../../shared/components/jump-gate-dialog.component';
import { BalanceService } from '../../core/services/balance.service';
import {
  BUILDING_META,
  RESOURCE_META,
  RANK_META,
  SPECIALIZATION_META,
  SHIP_META,
  DEFENSE_META,
  TECH_META,
  MISSION_META,
  PLANET_TYPE_META,
  metaFor,
} from '../../core/models/display';
import {
  navIcon,
  resourceIcon,
  statIcon,
  statusIcon,
  uiIcon,
  buildingIcon,
  techIcon,
  shipIcon,
  defenseIcon,
  missionIcon,
  rankIcon,
  planetIcon,
  fleetIcon,
} from '../../core/models/icon-assets';
import {
  BuildQueueItem,
  BuildingState,
  Fleet,
  RankBoardEntry,
  ResearchState,
  AwakeningStatus,
  AwakeningWarden,
  AwakeningLevelStatus,
  Conjunction,
  ConjunctionInfo,
} from '../../core/models/api.models';
import { dashboardStyles } from './dashboard.styles';
import { OnboardingPanelComponent } from '../../shared/components/onboarding-panel.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';

@Component({
  selector: 'app-dashboard',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterLink, ShortNumberPipe, CountdownComponent, JumpGateDialogComponent, OnboardingPanelComponent, IconTileComponent, BtnIconComponent],
  template: `
    <h1>Dashboard</h1>

    <app-onboarding-panel />

    <!-- Welle 4: „Der Erwachte" — dramatisches Banner, wenn der Waechter aktiv die Galaxie bedroht. -->
    @if (warden(); as w) {
      <a class="warden-banner" [routerLink]="['/galaxy']" [queryParams]="wardenParams()"
        title="Den Erwachten auf der Galaxie-Karte stellen">
        <div class="wb-glow" aria-hidden="true"></div>
        <div class="wb-body">
          <div class="wb-title">🕯️ DER ERWACHTE ist erwacht</div>
          <div class="wb-sub">Die Galaxie hat ihren Wächter gerufen. Stellt ihn — ehe er euch stellt.</div>
          <div class="wb-stats">
            @if (w.coords) {
              <span class="wb-chip">📍 [{{ w.coords }}]</span>
            }
            <span class="wb-chip danger">🔥 Bedrohung endet in <app-countdown [target]="w.expires_at" /></span>
            <span class="wb-chip">⚔️ {{ w.participants }} Mitstreiter</span>
          </div>
          @if (wardenFleet(); as fl) {
            <div class="wb-fleet">
              @for (e of fl; track e.label) {
                <span class="wb-ship">{{ e.count | shortNumber }}× {{ e.label }}</span>
              }
            </div>
          }
        </div>
        <span class="wb-cta">Zur Galaxie →</span>
      </a>
    }

    <!-- Imperiums-Punkte (OGame-Score) — prominent, gleich nach dem Wächter-Banner, verlinkt zur Rangliste -->
    <a class="score-hero" routerLink="/ranking">
      <img class="score-ico" src="assets/img/nav/ranking.png" alt="" (error)="onIcoError($event)" />
      <div class="score-main">
        <span class="score-label">Imperiums-Punkte</span>
        <span class="score-value mono">{{ (me()?.total ?? 0) | shortNumber }}</span>
      </div>
      <div class="score-rank">
        <span class="rank-big mono">#{{ me()?.rank ?? '–' }}</span>
        <span class="faint small">von {{ totalPlayers() }}</span>
      </div>
      <div class="score-breakdown">
        <span class="bd tip" data-tip="Gebäude"><app-btn-icon [src]="navIcon('buildings')" glyph="🏗️" [size]="14" /> {{ (me()?.buildings ?? 0) | shortNumber }}</span>
        <span class="bd tip" data-tip="Forschung"><app-btn-icon [src]="navIcon('research')" glyph="🔬" [size]="14" /> {{ (me()?.research ?? 0) | shortNumber }}</span>
        <span class="bd tip" data-tip="Flotte"><app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="14" /> {{ (me()?.fleet ?? 0) | shortNumber }}</span>
        <span class="bd tip" data-tip="Verteidigung"><app-btn-icon [src]="statIcon('shield')" glyph="🛡️" [size]="14" /> {{ (me()?.defense ?? 0) | shortNumber }}</span>
      </div>
      <span class="score-cta faint small">Rangliste →</span>
    </a>

    @if (planet(); as p) {
      <p class="muted sub">
        @if (editingName()) {
          <input class="rename-inp" #ni [value]="p.name" maxlength="40"
            (keyup.enter)="saveRename(p.id, ni.value)" (keyup.escape)="editingName.set(false)" />
          <button class="name-btn ok" type="button" (click)="saveRename(p.id, ni.value)" title="Speichern">✓</button>
          <button class="name-btn" type="button" (click)="editingName.set(false)" title="Abbrechen">✕</button>
        } @else {
          <span class="planet-name">{{ p.name }}</span>
          <button class="name-btn" type="button" (click)="startRename()" title="Planet umbenennen">✏️</button>
        }
        · <app-btn-icon [src]="planetIcon(p.planet_type ?? 'normal')" [glyph]="planetType(p.planet_type).glyph" [size]="14" /> {{ planetType(p.planet_type).label }} ·
        Koordinaten [{{ p.galaxy }}:{{ p.system }}:{{ p.position }}] ·
        {{ p.temp_max }}°C · Felder {{ p.fields_used }}/{{ p.fields_max }}
        @if (moon(); as m) {
          · <button class="moon-chip" type="button" (click)="selectMoon(m.id)"
              title="Zum Mond wechseln"><app-btn-icon [src]="'assets/img/backgrounds/moon.png'" glyph="🌑" [size]="14" /> Mond</button>
        }
        @if (parentPlanet(); as pp) {
          · <button class="moon-chip" type="button" (click)="selectMoon(pp.id)"
              title="Zum Planeten wechseln"><app-btn-icon [src]="'assets/img/planets/normal.png'" glyph="🪐" [size]="14" /> Planet</button>
        }
        @if (isMoon() && hasJumpGate()) {
          · <button class="moon-chip jump" type="button" (click)="showJump.set(true)"
              title="Sprungtor: Schiffe sofort zu einem anderen Mond versetzen"><app-btn-icon [src]="'assets/img/buildings/jump_gate.png'" glyph="🌀" [size]="14" /> Sprungtor</button>
        }
      </p>

      <!-- Alerts / Ereignisse — dringend, daher direkt nach dem Planeten-Header (volle Breite). -->
      <section class="card alerts-top">
        <div class="panel-title"><app-btn-icon [src]="statusIcon('alert')" glyph="⚠" [size]="16" /> Alerts & Ereignisse</div>
        @if (state.attackAlerts().length) {
          @for (a of state.attackAlerts(); track a.location) {
            <div class="alert danger attack-alert">
              <div class="aa-head">
                <span>
                  <app-btn-icon [src]="statusIcon('attack')" glyph="⚔️" [size]="14" />
                  {{ a.attackerName || 'Feindflotte' }} → <a class="coord-link" [routerLink]="['/galaxy']" [queryParams]="alertCoords(a.location)" title="Auf der Galaxie-Karte ansehen">{{ a.location }}</a>
                </span>
                <app-countdown [target]="a.arriveAt" />
              </div>
              @if (alertShips(a); as entries) {
                <div class="aa-ships">
                  @for (e of entries; track e.label) {
                    <span class="aa-ship">{{ e.count }}× {{ e.label }}</span>
                  }
                </div>
              } @else if (a.shipsTotal) {
                <div class="aa-ships muted small">
                  {{ a.shipsTotal }} Schiffe — Zusammensetzung unbekannt (Spionagetechnik Stufe 2+ nötig)
                </div>
              }
            </div>
          }
        }
        @if (energyDeficit()) {
          <div class="alert danger">
            <span><app-btn-icon [src]="statusIcon('energy_deficit')" glyph="⚡" [size]="14" /> Energie-Defizit ({{ energy().balance | shortNumber }}) drosselt die Minen</span>
            <a class="btn btn-sm" routerLink="/buildings">Beheben</a>
          </div>
        }
        @if (fullStorages().length) {
          <div class="alert">
            <span><app-btn-icon [src]="statusIcon('storage_full')" glyph="📦" [size]="14" /> Lager fast voll: {{ fullStoragesLabel() }}</span>
            <a class="btn btn-sm" routerLink="/buildings">Ausbauen</a>
          </div>
        }
        @if (state.unreadTransmissions() > 0) {
          <div class="alert decision">
            <span><app-btn-icon [src]="statusIcon('transmission_unread')" glyph="📡" [size]="14" /> {{ state.unreadTransmissions() }} ungelesene Transmission(en)</span>
            <a class="btn btn-sm" routerLink="/transmissions">Oeffnen</a>
          </div>
        }
        @if (!hasAlerts()) {
          <p class="muted small">Keine offenen Ereignisse. Alles ruhig im Sektor.</p>
        }
      </section>

      <div class="cols">
       <div class="col">
        <!-- Ressourcen -->
        <section class="card">
          <div class="panel-title">⛏️ Ressourcen</div>
          <div class="res-grid">
            @for (r of resources(); track r.key) {
              <div class="res-card">
                <div class="row-between">
                  <span class="res-name"><app-icon-tile [glyph]="r.glyph" [src]="r.img" [size]="18" variant="muted" /> {{ r.label }}</span>
                  <span class="mono">{{ r.amount | shortNumber }}</span>
                </div>
                <div class="bar" [class.full]="r.pct >= 100">
                  <span class="fill" [style.width.%]="r.pct"></span>
                </div>
                <div class="row-between small">
                  <span class="faint mono">{{ r.amount | shortNumber }} / {{ r.capacity | shortNumber }}</span>
                  <span class="mono" [class.ok]="r.rate >= 0">+{{ r.rate | shortNumber }}/h</span>
                </div>
              </div>
            }
            <div class="res-card energy">
              <div class="row-between">
                <span><app-btn-icon [src]="resourceIcon('energy')" glyph="⚡" [size]="16" /> Energie</span>
                <span class="mono" [class.neg]="energy().balance < 0">{{ energy().balance | shortNumber }}</span>
              </div>
              <div class="row-between small">
                <span class="faint">Produktion {{ energy().produced | shortNumber }}</span>
                <span class="faint">Verbrauch {{ energy().consumed | shortNumber }}</span>
              </div>
              <div class="row-between small">
                <span class="faint tip" data-tip="Bei Defizit drosselt der Faktor die Minen-Rate.">Faktor</span>
                <span class="mono" [class.neg]="energy().factor < 1">{{ (energy().factor * 100).toFixed(0) }}%</span>
              </div>
            </div>
          </div>
        </section>

        <!-- Aktive Vorgaenge -->
        <section class="card">
          <div class="panel-title"><app-btn-icon [src]="uiIcon('time')" glyph="⏳" [size]="16" /> Aktive Vorgaenge</div>

          <div class="ops-block">
            <div class="ops-label"><app-btn-icon [src]="navIcon('buildings')" glyph="🏗️" [size]="16" /> Bau</div>
            @if (activeBuild(); as b) {
              <a class="queue-row link" routerLink="/buildings" [queryParams]="{ focus: b.type }"
                title="Zum laufenden Ausbau springen">
                <span><app-btn-icon [src]="buildingIcon(b.type)" [glyph]="metaB(b.type).glyph" [size]="14" /> {{ metaB(b.type).label }} → Stufe {{ b.level + 1 }}</span>
                <app-countdown [target]="b.upgrade_finishes_at" />
              </a>
            } @else {
              <p class="muted small">Kein Bau aktiv. <a routerLink="/buildings">Bauen →</a></p>
            }
          </div>

          <hr />

          <div class="ops-block">
            <div class="ops-label"><app-btn-icon [src]="navIcon('research')" glyph="🔬" [size]="16" /> Forschung</div>
            @if (activeResearch(); as t) {
              <a class="queue-row link" routerLink="/research" [queryParams]="{ focus: t.type }"
                title="Zur laufenden Forschung springen">
                <span><app-btn-icon [src]="techIcon(t.type)" [glyph]="metaT(t.type).glyph" [size]="14" /> {{ metaT(t.type).label }} → Stufe {{ t.level + 1 }}</span>
                <app-countdown [target]="t.finishes_at" />
              </a>
            } @else {
              <p class="muted small">Keine Forschung aktiv. <a routerLink="/research">Techbaum →</a></p>
            }
          </div>

          <hr />

          <div class="ops-block">
            <div class="ops-label"><app-btn-icon [src]="navIcon('shipyard')" glyph="🛠️" [size]="16" /> Werft</div>
            @if (shipQueue().length) {
              @for (q of shipQueue(); track $index; let first = $first) {
                <a class="queue-row link" [class.q-waiting]="!first" routerLink="/shipyard" [queryParams]="{ focus: q.type }"
                  [title]="first ? 'Wird gerade gebaut — zur Werft springen' : 'Wartet, bis die vorherigen Aufträge fertig sind (serielle Werft)'">
                  <span>
                    <app-btn-icon [src]="shipIcon(q.type)" [glyph]="metaShip(q).glyph" [size]="14" /> {{ q.count }}× {{ metaShip(q).label }}
                    @if (first) { <span class="q-tag build">⏳ Im Bau</span> } @else { <span class="q-tag wait">⏸ wartet</span> }
                  </span>
                  @if (first) {
                    <app-countdown [target]="q.finishes_at" />
                  }
                </a>
              }
            } @else {
              <p class="muted small">Werft frei. <a routerLink="/shipyard">Schiffe bauen →</a></p>
            }
          </div>

          <hr />

          <div class="ops-block">
            <div class="ops-label"><app-btn-icon [src]="navIcon('defense')" glyph="🛡️" [size]="16" /> Verteidigung</div>
            @if (defenseQueue().length) {
              @for (q of defenseQueue(); track $index; let first = $first) {
                <a class="queue-row link" [class.q-waiting]="!first" routerLink="/defense" [queryParams]="{ focus: q.type }"
                  [title]="first ? 'Wird gerade gebaut — zur Verteidigung springen' : 'Wartet, bis die vorherigen Aufträge fertig sind (serielle Verteidigungsfabrik)'">
                  <span>
                    <app-btn-icon [src]="defenseIcon(q.type)" [glyph]="metaShip(q).glyph" [size]="14" /> {{ q.count }}× {{ metaShip(q).label }}
                    @if (first) { <span class="q-tag build">⏳ Im Bau</span> } @else { <span class="q-tag wait">⏸ wartet</span> }
                  </span>
                  @if (first) {
                    <app-countdown [target]="q.finishes_at" />
                  }
                </a>
              }
            } @else {
              <p class="muted small">Verteidigungsfabrik frei. <a routerLink="/defense">Verteidigung bauen →</a></p>
            }
          </div>
        </section>

        <!-- Flottenbewegungen -->
        <section class="card">
          <div class="panel-title"><app-btn-icon [src]="navIcon('fleet')" glyph="🚀" [size]="16" /> Flottenbewegungen</div>
          @if (activeFleets().length) {
            @for (f of activeFleets(); track f.id) {
              <div class="queue-row has-tip">
                <span>
                  <app-btn-icon [src]="fleetIcon()" glyph="🚀" [size]="16" /> {{ metaM(f.mission).label }}
                  <span class="faint">→ </span><a class="coord-link" [routerLink]="['/galaxy']" [queryParams]="{ g: f.target.galaxy, s: f.target.system }" title="Auf der Galaxie-Karte ansehen">[{{ f.target.galaxy }}:{{ f.target.system }}:{{ f.target.position }}]</a>
                  <span class="chip">{{ statusLabel(f.status) }}</span>
                </span>
                <app-countdown [target]="f.status === 'returning' ? f.return_at : f.arrive_at" />
                @if (f.mining; as m) {
                  <div class="mine-bar" title="Schürf-Fortschritt — der Frachtraum füllt sich über die Verweilzeit. Bei einem Abfang erbeutet der Gegner nur das bisher Geförderte.">
                    <div class="mb-track"><span class="mb-fill" [style.width.%]="m.progress * 100"></span></div>
                    <span class="mb-amt mono">⛏ {{ m.metal | shortNumber }} · 💎 {{ m.crystal | shortNumber }}</span>
                  </div>
                }
                <div class="fleet-tip" role="tooltip">
                  <div class="tip-head"><app-btn-icon [src]="fleetIcon()" glyph="🚀" [size]="14" /> {{ metaM(f.mission).label }} → [{{ f.target.galaxy }}:{{ f.target.system }}:{{ f.target.position }}]</div>
                  <div class="tip-sec">
                    <div class="tip-sec-title">Schiffe</div>
                    @for (e of shipEntries(f.ships); track e.label) {
                      <div class="tip-row"><span>{{ e.label }}</span><span class="mono">{{ e.count | shortNumber }}</span></div>
                    }
                  </div>
                  @if (cargoEntries(f.cargo).length) {
                    <div class="tip-sec">
                      <div class="tip-sec-title">Fracht</div>
                      @for (e of cargoEntries(f.cargo); track e.label) {
                        <div class="tip-row"><span>{{ e.label }}</span><span class="mono">{{ e.amount | shortNumber }}</span></div>
                      }
                    </div>
                  } @else {
                    <div class="tip-sec"><div class="tip-row muted">Keine Fracht</div></div>
                  }
                </div>
              </div>
            }
          } @else {
            <p class="muted small">Keine Flotten unterwegs. <a routerLink="/fleet">Flotte entsenden →</a></p>
          }
        </section>

       </div>

       <div class="col">
        <!-- Commander-Moral -->
        <section class="card">
          <div class="panel-title"><app-btn-icon [src]="uiIcon('morale')" glyph="🎖️" [size]="16" /> Crew-Moral</div>
          @if (state.commanders().length) {
            @for (c of state.commanders(); track c.id) {
              <a class="cmd-row" [routerLink]="['/commanders', c.id]">
                <span class="cmd-name">
                  <app-btn-icon [src]="rankIcon(c.rank)" [glyph]="rank(c.rank).glyph" [size]="14" /> {{ c.name }}
                  <span class="faint">· {{ spec(c.specialization).label }}</span>
                </span>
                <span class="cmd-morale" [class]="bandClass(c.morale)">
                  <span class="dot"></span>{{ c.morale }} · {{ c.morale_band.label }}
                </span>
              </a>
            }
            @if (state.span(); as s) {
              <p class="muted small span-line">
                Span of Control: {{ s.in_use }}/{{ s.total }} belegt
              </p>
            }
          } @else {
            <p class="muted small">Noch keine Commander. <a routerLink="/commanders">Kommandozentrale →</a></p>
          }
        </section>

        <!-- Verteidigung auf diesem Planeten (genaue Anzahl je Typ) -->
        <section class="card">
          <div class="panel-title"><app-btn-icon [src]="statIcon('shield')" glyph="🛡️" [size]="16" /> Verteidigung</div>
          @if (defenses().length) {
            @for (d of defenses(); track d.type) {
              <div class="def-row">
                <span class="def-name"><app-btn-icon [src]="defenseIcon(d.type)" [glyph]="d.glyph" [size]="14" /> {{ d.label }}</span>
                <span class="def-count mono">{{ d.count }}</span>
              </div>
            }
            <div class="def-row def-total">
              <span class="def-name faint">Gesamt</span>
              <span class="def-count mono">{{ defenseTotal() }}</span>
            </div>
          } @else {
            <p class="muted small">Keine Verteidigungsanlagen. <a routerLink="/defense">Bauen →</a></p>
          }
        </section>
       </div>
      </div>
    } @else {
      <p class="empty-state">Lade Planetendaten…</p>
    }

    <!-- === Ambiente (situativ) — aufgeräumt + eingeklappt ganz unten === -->

    <!-- Welle 4: Aggressions-Barometer — der „Puls" des Universums (einklappbar, Default zu). -->
    @if (awakeningEnabled()) {
      <section class="card awakening-baro collapsible" [class.collapsed]="!awakeningOpen()" [style.--band]="statusColor()">
        <button class="collapse-head" type="button" (click)="awakeningOpen.set(!awakeningOpen())"
          [attr.aria-expanded]="awakeningOpen()" title="Auf-/zuklappen">
          <span class="ch-title">📊 Universums-Aggression: <span class="baro-status" [style.color]="statusColor()">{{ statusGlyph() }} {{ statusLabelAw() }}</span></span>
          <span class="ch-arrow">{{ awakeningOpen() ? '▾' : '▸' }}</span>
        </button>
        @if (awakeningOpen()) {
          <div class="collapse-body">
            <div class="baro-bar"
              title="Aggressionsniveau der Galaxie. Erreicht es die Schwelle, erwacht Der Erwachte.">
              <span class="baro-fill" [style.width.%]="baroPct()"></span>
              @for (t of bandTicks(); track t.status) {
                <span class="baro-tick" [class.peak]="t.status === 'apocalypse'" [style.left.%]="t.pct"></span>
              }
            </div>
            <div class="baro-meta">
              <span class="mono">{{ level() | shortNumber }} / {{ threshold() | shortNumber }}</span>
              <span class="faint">{{ combatCount() }} Kämpfe · {{ attackers() }} Angreifer (6 h)</span>
              @if (sparkPoints(); as pts) {
                <svg class="baro-spark" viewBox="0 0 100 24" preserveAspectRatio="none" aria-hidden="true">
                  <polyline [attr.points]="pts" />
                </svg>
              }
            </div>
          </div>
        }
      </section>
    }

    <!-- Welle 5: Wandernde Galaxie — Konjunktions-Fenster (einklappbar, Default zu). -->
    @if (conjEnabled() && (activeConj().length || upcomingConj().length)) {
      <section class="card conj-card collapsible" [class.collapsed]="!conjOpen()">
        <button class="collapse-head" type="button" (click)="conjOpen.set(!conjOpen())"
          [attr.aria-expanded]="conjOpen()" title="Auf-/zuklappen">
          <span class="ch-title">🌌 Konjunktionen <span class="faint small">({{ activeConj().length }} aktiv)</span></span>
          <span class="ch-arrow">{{ conjOpen() ? '▾' : '▸' }}</span>
        </button>
        @if (conjOpen()) {
          <div class="collapse-body">
            @if (activeConj().length) {
              <div class="conj-block">
                <div class="conj-head faint small">Aktive Fenster</div>
                @for (c of activeConj(); track c.from + '>' + c.to) {
                  <div class="conj-row">
                    <span class="conj-route">
                      <a class="coord-link" [routerLink]="['/galaxy']" [queryParams]="{ g: c.from_coords.galaxy, s: c.from_coords.system }">[{{ c.from }}]</a>
                      <span class="conj-arrow">↔</span>
                      <a class="coord-link" [routerLink]="['/galaxy']" [queryParams]="{ g: c.to_coords.galaxy, s: c.to_coords.system }">[{{ c.to }}]</a>
                    </span>
                    <span class="conj-disc" [class.boon]="c.discount_pct >= 0" [class.bane]="c.discount_pct < 0">{{ discountLabel(c) }}</span>
                    <span class="conj-cd small">endet in <app-countdown [target]="c.ends_at ?? null" /></span>
                  </div>
                }
              </div>
            }
            @if (upcomingConj().length) {
              <div class="conj-block">
                <div class="conj-head faint small">Nächste Fenster</div>
                @for (c of upcomingConj(); track c.from + '>' + c.to) {
                  <div class="conj-row upcoming">
                    <span class="conj-route">
                      <a class="coord-link" [routerLink]="['/galaxy']" [queryParams]="{ g: c.from_coords.galaxy, s: c.from_coords.system }">[{{ c.from }}]</a>
                      <span class="conj-arrow">↔</span>
                      <a class="coord-link" [routerLink]="['/galaxy']" [queryParams]="{ g: c.to_coords.galaxy, s: c.to_coords.system }">[{{ c.to }}]</a>
                    </span>
                    <span class="conj-disc" [class.boon]="c.discount_pct >= 0" [class.bane]="c.discount_pct < 0">{{ discountLabel(c) }}</span>
                    <span class="conj-cd small">beginnt in <app-countdown [target]="c.starts_at ?? c.next_at ?? null" /></span>
                  </div>
                }
              </div>
            }
          </div>
        }
      </section>
    }

    @if (showJump()) {
      <app-jump-gate-dialog (close)="showJump.set(false)" />
    }
  `,
  styles: [dashboardStyles],
})
export class DashboardComponent {
  protected readonly state = inject(GameStateService);
  private readonly api = inject(ApiService);
  private readonly balance = inject(BalanceService);
  private readonly notify = inject(NotificationService);

  /** Inline-Umbenennung des aktiven Planeten/Mondes. */
  protected readonly editingName = signal(false);

  protected startRename(): void {
    this.editingName.set(true);
    setTimeout(() => {
      const inp = document.querySelector('.rename-inp') as HTMLInputElement | null;
      inp?.focus();
      inp?.select();
    }, 0);
  }

  protected saveRename(planetId: string, value: string): void {
    const name = value.trim();
    if (!name) {
      this.editingName.set(false);
      return;
    }
    this.api.renamePlanet(planetId, name).subscribe({
      next: (p) => {
        this.state.updatePlanetName(planetId, p.name);
        this.editingName.set(false);
        this.notify.success('Umbenannt', `Heißt jetzt „${p.name}".`);
      },
      error: () => this.notify.warning('Fehlgeschlagen', 'Planet konnte nicht umbenannt werden.'),
    });
  }

  /** Asset-Pfad-Helfer fuers Template (Glyph-Fallback via app-btn-icon). */
  protected readonly navIcon = navIcon;
  protected readonly resourceIcon = resourceIcon;
  protected readonly statIcon = statIcon;
  protected readonly statusIcon = statusIcon;
  protected readonly uiIcon = uiIcon;
  protected readonly buildingIcon = buildingIcon;
  protected readonly techIcon = techIcon;
  protected readonly shipIcon = shipIcon;
  protected readonly defenseIcon = defenseIcon;
  protected readonly missionIcon = missionIcon;
  protected readonly rankIcon = rankIcon;
  protected readonly planetIcon = planetIcon;

  protected readonly planet = this.state.activePlanet;

  /** Mond des aktiven Planeten (teilt die Koordinate; planet_type 'moon'). */
  protected readonly moon = computed(() => {
    const p = this.planet();
    if (!p || p.planet_type === 'moon') return null;
    return (
      this.state
        .planets()
        .find(
          (x) =>
            x.planet_type === 'moon' &&
            x.galaxy === p.galaxy &&
            x.system === p.system &&
            x.position === p.position,
        ) ?? null
    );
  });

  selectMoon(id: string): void {
    void this.state.selectPlanet(id);
  }

  /** Ist der aktive Kontext ein Mond? */
  protected readonly isMoon = computed(() => this.planet()?.planet_type === 'moon');

  /** Verteidigungsanlagen des aktiven Planeten, je Typ mit Label/Icon, größte Anzahl zuerst. */
  protected readonly defenses = computed(() =>
    (this.planet()?.defenses ?? [])
      .filter((d) => d.count > 0)
      .map((d) => ({ type: d.type, count: d.count, ...metaFor(DEFENSE_META, d.type) }))
      .sort((a, b) => b.count - a.count),
  );
  protected readonly defenseTotal = computed(() =>
    this.defenses().reduce((sum, d) => sum + d.count, 0),
  );

  /** Mutterplanet, wenn der aktive Kontext ein Mond ist (Koordinaten-Match). */
  protected readonly parentPlanet = computed(() => {
    const p = this.planet();
    if (!p || p.planet_type !== 'moon') return null;
    return (
      this.state
        .planets()
        .find(
          (x) =>
            x.planet_type !== 'moon' &&
            x.galaxy === p.galaxy &&
            x.system === p.system &&
            x.position === p.position,
        ) ?? null
    );
  });

  /** Hat der aktive Mond ein gebautes Sprungtor (Voraussetzung fuer den Sprung-Dialog)? */
  protected readonly hasJumpGate = computed(
    () => this.planet()?.buildings?.some((b) => b.type === 'jump_gate' && b.level >= 1) ?? false,
  );

  /** Sprungtor-Dialog offen? */
  protected readonly showJump = signal(false);

  // --- Aktive Vorgaenge (per Effekt beim Planetenwechsel geladen) ---
  protected readonly activeBuild = signal<BuildingState | null>(null);
  protected readonly activeResearch = signal<ResearchState | null>(null);
  protected readonly shipyardQueue = signal<BuildQueueItem[]>([]);
  /** Werft- und Verteidigungs-Schlange laufen getrennt/parallel — im Dashboard separat zeigen. */
  protected readonly shipQueue = computed(() => this.shipyardQueue().filter((q) => q.category === 'ship'));
  protected readonly defenseQueue = computed(() => this.shipyardQueue().filter((q) => q.category === 'defense'));

  // --- Imperiums-Punkte (Rangliste) ---
  protected readonly me = signal<RankBoardEntry | null>(null);
  protected readonly totalPlayers = signal(0);

  // --- Welle 4: Die erwachende Galaxie ---
  protected readonly awakening = signal<AwakeningStatus | null>(null);

  // --- Welle 5: Wandernde Galaxie / Konjunktions-Fenster ---
  protected readonly conjunctions = signal<ConjunctionInfo | null>(null);
  protected readonly conjEnabled = computed(() => this.conjunctions()?.enabled ?? false);
  protected readonly activeConj = computed(() => this.conjunctions()?.active ?? []);
  protected readonly upcomingConj = computed(() => this.conjunctions()?.upcoming ?? []);

  // --- Einklappbare Ambient-Karten (Konjunktionen + Aggressions-Barometer) ---
  // Zustand pro Karte in localStorage; Default = eingeklappt (Tester: „zu viel Info").
  protected readonly conjOpen = this.persistBool('dash.conj.open', false);
  protected readonly awakeningOpen = this.persistBool('dash.awakening.open', false);

  /**
   * Persistenter boolean-Signal-Helfer: liest den Startwert aus localStorage
   * (Fallback = Default) und schreibt jede Änderung via Effekt zurück.
   * Reines Angular-Signal-Pattern, kein externes Lib.
   */
  private persistBool(key: string, def: boolean) {
    let init = def;
    try {
      const raw = localStorage.getItem(key);
      if (raw === '1' || raw === '0') init = raw === '1';
    } catch {
      /* localStorage evtl. nicht verfügbar — Default verwenden */
    }
    const sig = signal(init);
    effect(() => {
      try {
        localStorage.setItem(key, sig() ? '1' : '0');
      } catch {
        /* Schreiben fehlgeschlagen — still ignorieren */
      }
    });
    return sig;
  }

  /** Rabatt-Label: positiv = Distanz reduziert (Segen), negativ = Aufschlag (dezent). */
  discountLabel(c: Conjunction): string {
    const p = c.discount_pct;
    return p >= 0 ? `−${p.toFixed(0)}% Distanz` : `+${Math.abs(p).toFixed(0)}%`;
  }

  /** Status -> Label/Farbe/Glyph fuers Barometer (deutsche Begriffe). */
  private readonly awStatusMeta: Record<
    AwakeningLevelStatus,
    { label: string; color: string; glyph: string }
  > = {
    peaceful: { label: 'Ruhig', color: '#3ddc97', glyph: '🕊️' },
    tense: { label: 'Angespannt', color: '#e8c547', glyph: '⚡' },
    war: { label: 'Krieg', color: '#f59340', glyph: '⚔️' },
    apocalypse: { label: 'Apokalypse', color: '#ff4d4d', glyph: '💀' },
  };

  protected readonly awakeningEnabled = computed(() => this.awakening()?.enabled ?? false);
  protected readonly level = computed(() => this.awakening()?.level ?? 0);
  protected readonly threshold = computed(() => this.awakening()?.threshold ?? 0);
  protected readonly combatCount = computed(() => this.awakening()?.combat_count ?? 0);
  protected readonly attackers = computed(() => this.awakening()?.unique_attackers ?? 0);

  private readonly awMeta = computed(
    () => this.awStatusMeta[this.awakening()?.status ?? 'peaceful'] ?? this.awStatusMeta.peaceful,
  );
  protected readonly statusLabelAw = computed(() => this.awMeta().label);
  protected readonly statusColor = computed(() => this.awMeta().color);
  protected readonly statusGlyph = computed(() => this.awMeta().glyph);

  /** Balken-Fuellung: Aggression relativ zur Erwachen-Schwelle (gedeckelt). */
  protected readonly baroPct = computed(() => {
    const t = this.threshold();
    if (t <= 0) return 0;
    return Math.min(100, (this.level() / t) * 100);
  });

  /** Status-Band-Marken auf der Achse (peaceful/tense/war/apocalypse). */
  protected readonly bandTicks = computed(() => {
    const t = this.threshold();
    if (t <= 0) return [] as { status: AwakeningLevelStatus; pct: number }[];
    return (this.awakening()?.status_bands ?? [])
      .filter((b) => b.min > 0)
      .map((b) => ({ status: b.status, pct: Math.min(100, (b.min / t) * 100) }));
  });

  /** 24h-Verlauf als SVG-Polyline (100x24-Viewbox). Leer bei < 2 Punkten. */
  protected readonly sparkPoints = computed(() => {
    const hist = this.awakening()?.history ?? [];
    if (hist.length < 2) return '';
    const max = Math.max(this.threshold(), ...hist.map((p) => p.level), 1);
    const n = hist.length;
    return hist
      .map((p, i) => {
        const x = (i / (n - 1)) * 100;
        const y = 23 - (Math.min(p.level, max) / max) * 22;
        return `${x.toFixed(1)},${y.toFixed(1)}`;
      })
      .join(' ');
  });

  /** Der Waechter — nur, wenn er gerade aktiv die Galaxie bedroht. */
  protected readonly warden = computed<AwakeningWarden | null>(() => {
    const w = this.awakening()?.warden ?? null;
    return w && w.status === 'active' ? w : null;
  });

  /** Galaxie-Karten-QueryParams aus den "g:s:p"-Koordinaten des Waechters. */
  protected wardenParams(): Record<string, number> {
    const c = this.warden()?.coords;
    if (!c) return {};
    const [g, s, p] = c.split(':').map((n) => Number(n));
    return { g: g || 1, s: s || 1, p: p || 1 };
  }

  /** Flotten-Andeutung des Waechters (groesste Verbaende zuerst). */
  protected readonly wardenFleet = computed(() => {
    const entries = this.shipEntries(this.warden()?.fleet);
    return entries.length ? entries : null;
  });

  constructor() {
    // Eigenen Score + Rang frisch laden (Server rechnet bei jedem Abruf neu).
    this.api.getRanking().subscribe({
      next: (r) => {
        this.me.set(r.me);
        this.totalPlayers.set(r.total);
      },
      error: () => {},
    });

    // Welle 4: Puls der Galaxie + Waechter-Status (read-only, Fehler stumm).
    this.api.getAwakeningStatus().subscribe({
      next: (a) => this.awakening.set(a),
      error: () => {},
    });

    // Welle 5: Konjunktions-Fenster — aktive + kommende Routen-Rabatte (read-only, Fehler stumm).
    this.api.getConjunctions().subscribe({
      next: (c) => this.conjunctions.set(c),
      error: () => {},
    });

    // Reload der Timer, sobald ein anderer Planet aktiv wird.
    effect(() => {
      const id = this.state.activePlanetId();
      if (id) {
        void this.loadActiveOps(id);
      } else {
        this.activeBuild.set(null);
        this.activeResearch.set(null);
        this.shipyardQueue.set([]);
      }
    });
  }

  private async loadActiveOps(planetId: string): Promise<void> {
    // Bau
    try {
      const res = await firstValueFrom(this.api.getBuildings(planetId));
      this.activeBuild.set(res.buildings.find((b) => b.upgrade_finishes_at) ?? null);
    } catch {
      this.activeBuild.set(null);
    }
    // Forschung (global)
    try {
      const res = await firstValueFrom(this.api.getResearch());
      this.activeResearch.set(res.research.find((t) => t.finishes_at) ?? null);
    } catch {
      this.activeResearch.set(null);
    }
    // Werft-Queue
    try {
      const res = await firstValueFrom(this.api.getShipyard(planetId));
      this.shipyardQueue.set(res.queue ?? []);
    } catch {
      this.shipyardQueue.set([]);
    }
  }

  protected readonly resources = computed(() => {
    const res = this.planet()?.resources;
    const keys: ('metal' | 'crystal' | 'deuterium')[] = ['metal', 'crystal', 'deuterium'];
    return keys.map((key) => {
      const pool = res?.[key];
      const amount = pool?.amount ?? 0;
      const capacity = pool?.capacity ?? 0;
      return {
        key,
        label: RESOURCE_META[key].label,
        glyph: RESOURCE_META[key].glyph,
        img: `assets/img/resources/${key}.png`,
        amount,
        capacity,
        rate: pool?.rate ?? 0,
        pct: capacity > 0 ? Math.min(100, (amount / capacity) * 100) : 0,
      };
    });
  });

  protected readonly energy = computed(
    () =>
      this.planet()?.resources?.energy ?? { produced: 0, consumed: 0, balance: 0, factor: 1 },
  );

  protected readonly energyDeficit = computed(() => this.energy().balance < 0);

  /** Lager mit >= 95% Fuellstand. */
  protected readonly fullStorages = computed(() => this.resources().filter((r) => r.pct >= 95));
  protected readonly fullStoragesLabel = computed(() =>
    this.fullStorages().map((r) => r.label).join(', '),
  );

  /** Aktive Flotten: unterwegs zum Ziel oder auf dem Rueckflug. */
  protected readonly activeFleets = computed(() =>
    this.state.fleets().filter((f) => f.status === 'flying' || f.status === 'returning'),
  );

  protected readonly hasAlerts = computed(
    () =>
      this.state.attackAlerts().length > 0 ||
      this.energyDeficit() ||
      this.fullStorages().length > 0 ||
      this.state.unreadTransmissions() > 0,
  );

  statusLabel = (s: string) => (s === 'returning' ? 'Rueckflug' : 'unterwegs');

  metaB = (t: string) => metaFor(BUILDING_META, t);
  metaT = (t: string) => metaFor(TECH_META, t);
  metaM = (m: string) => metaFor(MISSION_META, m);
  metaShip = (q: BuildQueueItem) =>
    metaFor(q.category === 'defense' ? DEFENSE_META : SHIP_META, q.type);
  rank = (r: string) => metaFor(RANK_META, r);
  spec = (s: string) => metaFor(SPECIALIZATION_META, s);
  planetType = (t: string | undefined) => metaFor(PLANET_TYPE_META, t ?? 'normal');
  bandClass = (m: number) => this.balance.moraleBandClass(m);

  protected readonly fleetIcon = fleetIcon;

  /** Schiffs-Zusammensetzung einer Flotte als sortierte Label/Anzahl-Liste (groesste zuerst). */
  shipEntries(ships: Record<string, number> | null | undefined): { label: string; count: number }[] {
    if (!ships) return [];
    return Object.entries(ships)
      .filter(([, c]) => (c ?? 0) > 0)
      .map(([t, c]) => ({ label: metaFor(SHIP_META, t).label, count: c as number }))
      .sort((a, b) => b.count - a.count);
  }

  /** Zerlegt eine "g:s:p"-Location in Galaxie-Karten-QueryParams. */
  alertCoords(location: string): { g: number; s: number } {
    const [g, s] = location.split(':').map((n) => Number(n));
    return { g: g || 1, s: s || 1 };
  }

  /** Angreifer-Flotte als Label/Menge-Liste — nur wenn die Aufklaerung sie kennt (>= Stufe 2). */
  alertShips(a: AttackAlert): { label: string; count: number }[] | null {
    const entries = this.shipEntries(a.ships);
    return entries.length ? entries : null;
  }

  /** Fracht einer Flotte als Label/Menge-Liste (nur Ressourcen mit Menge > 0). */
  cargoEntries(cargo: Record<string, number> | null | undefined): { label: string; amount: number }[] {
    if (!cargo) return [];
    return Object.entries(cargo)
      .filter(([, v]) => (v ?? 0) > 0)
      .map(([k, v]) => ({ label: metaFor(RESOURCE_META, k).label, amount: v as number }));
  }

  protected onIcoError(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
}
