import {
  ChangeDetectionStrategy,
  Component,
  computed,
  effect,
  inject,
  input,
  linkedSignal,
  output,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import { BalanceService } from '../../core/services/balance.service';
import { FleetCalculationService } from '../../core/services/fleet-calculation.service';
import { Conjunction, ConjunctionInfo, Coordinate, EscortOffer, FleetMission, FleetSendRequest, GalaxyIntel, PlanetUnit, TradeIndex } from '../../core/models/api.models';
import { MISSION_META, RANK_META, SHIP_META, isMk2, metaFor } from '../../core/models/display';
import { missionIcon, navIcon, resourceIcon, shipIcon, statIcon, uiIcon } from '../../core/models/icon-assets';
import { BtnIconComponent } from './btn-icon.component';
import { IconTileComponent } from './icon-tile.component';
import { CountdownComponent } from './countdown.component';

/**
 * Kompaktes Versand-Overlay (OGame-Schnellaktion): direkt aus der Galaxie
 * eine Flotte zu einem Ziel schicken — Schiffs-Picker, optional Cargo
 * (Transport/Stationierung), Commander, Tempo — ohne Tab-Wechsel.
 *
 * Liest verfuegbare Schiffe/Commander/Ressourcen aus dem GameState des aktiven
 * Planeten und sendet via ApiService. Schliesst nach erfolgreichem Start.
 */
/** Transportierbare Fracht-Ressourcen inkl. Exoten (pro Planet, 2026-06-15). */
const CARGO_LOAD_KEYS = ['metal', 'crystal', 'deuterium', 'antimatter', 'dark_matter'] as const;
type DispatchCargoKey = (typeof CARGO_LOAD_KEYS)[number];

@Component({
  selector: 'app-fleet-dispatch',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, IconTileComponent, BtnIconComponent, CountdownComponent],
  host: { '(document:keydown.escape)': 'close.emit()' },
  template: `
    <div class="backdrop" (click)="close.emit()">
      <div class="popup glass" (click)="$event.stopPropagation()" role="dialog" aria-modal="true">
        <button class="x" type="button" (click)="close.emit()" aria-label="Schliessen">✕</button>

        <header class="head">
          @if (patrolMode()) {
            <h2><app-btn-icon [src]="missionIcon('attack')" glyph="⚔" [size]="18" /> Eigenes System patrouillieren</h2>
            <span class="coord mono">@ [{{ effTarget().galaxy }}:{{ effTarget().system }}:{{ effTarget().position }}]</span>
          } @else {
            <h2>{{ missionMeta(mission()).glyph }} Flotte entsenden</h2>
            @if (!editableTarget()) {
              <span class="coord mono">→ [{{ effTarget().galaxy }}:{{ effTarget().system }}:{{ effTarget().position }}]</span>
            }
            @if (targetName()) { <span class="tname">{{ targetName() }}</span> }
          }
        </header>

        <!-- W0: editierbares Ziel (allgemeiner Versand aus dem Flotten-Screen) -->
        @if (editableTarget() && !patrolMode()) {
          <div class="target-edit">
            <label class="cargo-title"><app-btn-icon [src]="uiIcon('target')" glyph="🎯" [size]="14" /> Ziel (Galaxie : System : Position)</label>
            <div class="coord-inputs">
              <input type="number" min="1" [ngModel]="tgtG()" (ngModelChange)="tgtG.set(+$event || 1)" aria-label="Galaxie" />
              <span class="sep">:</span>
              <input type="number" min="1" [ngModel]="tgtS()" (ngModelChange)="tgtS.set(+$event || 1)" aria-label="System" />
              <span class="sep">:</span>
              <input type="number" min="1" [ngModel]="tgtP()" (ngModelChange)="tgtP.set(+$event || 1)" aria-label="Position" />
            </div>
          </div>
        }

        @if (!patrolMode()) {
        <!-- Welle 5: Konjunktions-Hinweis fuer die gewaehlte Route (reine Anzeige; Server rechnet beim Start). -->
        @if (routeConjunction(); as rc) {
          <div class="conj-badge active">
            🌌 Konjunktion aktiv – Distanz/Sprit reduziert (−{{ rc.discount_pct.toFixed(0) }}%)
            @if (rc.ends_at) { <span class="conj-cd">· endet in <app-countdown [target]="rc.ends_at" /></span> }
          </div>
        } @else if (nextRouteConjunction(); as nc) {
          <div class="conj-badge upcoming">
            🌌 Nächstes günstiges Fenster (−{{ nc.discount_pct.toFixed(0) }}%) in <app-countdown [target]="nc.starts_at ?? nc.next_at ?? null" />
          </div>
        }

        <!-- Missionswahl -->
        <div class="mission-tabs">
          @for (m of missions(); track m) {
            <button
              type="button"
              class="mtab"
              [class.active]="mission() === m"
              (click)="mission.set(m)"
            >@if (missionIcon(m); as mi) {<img class="mtab-ico" [src]="mi" alt="" (error)="hideImg($event)" />} @else {{{ missionMeta(m).glyph }} }{{ missionMeta(m).label }}</button>
          }
        </div>
        }

        <!-- Schiffs-Picker -->
        <div class="ships">
          @for (s of availableShips(); track s.type) {
            <div class="ship" [class.picked]="shipCount(s.type) > 0">
              <div class="ship-art">
                <app-icon-tile [glyph]="shipMeta(s.type).glyph" [src]="shipIcon(s.type)" [mk2]="isMk2(s.type)" [size]="40" />
                <span class="avail" title="vorhanden">{{ s.count }}</span>
              </div>
              <div class="ship-name">{{ shipMeta(s.type).label }}</div>
              <div class="ship-pick">
                <input type="number" min="0" [max]="s.count"
                  [ngModel]="shipCount(s.type)" (ngModelChange)="setShip(s.type, $event, s.count)" aria-label="Menge" />
                <button class="btn btn-ghost btn-sm" type="button" (click)="setShip(s.type, s.count, s.count)">alle</button>
              </div>
              @if (shipCount(s.type) > 0 && shipCargo(s.type) > 0) {
                <div class="ship-cargo faint mono"><app-btn-icon [src]="statIcon('cargo')" glyph="📦" [size]="14" /> {{ (shipCargo(s.type) * shipCount(s.type)).toLocaleString('de-DE') }}</div>
              }
            </div>
          } @empty {
            <p class="muted small">Keine Schiffe auf diesem Planeten. <a href="/shipyard">Werft →</a></p>
          }
        </div>

        @if (missionHint(); as h) {
          <p class="hint small">{{ h }}</p>
        }

        <!-- W0: Patrouillen-Radius (eigenes System abfangen) -->
        @if (patrolMode()) {
          <div class="opts">
            <div class="field">
              <label class="tip" data-tip="0 = nur das eigene System. Höhere Reichweite via Hyperraum-Interdiktion-Forschung (max 6).">📡 Abfang-Radius {{ patrolRadius() }} Sys</label>
              <input type="number" min="0" max="6" [ngModel]="patrolRadius()" (ngModelChange)="patrolRadius.set(+$event || 0)" />
            </div>
          </div>
          <p class="muted small">Die Schiffe bleiben im eigenen System und fangen durchreisende Feindflotten ab (kein Flug).</p>
        }

        <!-- W0: Abfangen (intercept) — Patrouillen-Radius am Zielsystem -->
        @if (mission() === 'intercept' && !patrolMode()) {
          <div class="opts">
            <div class="field">
              <label class="tip" data-tip="0 = nur das Zielsystem. Reichweite steigt mit Hyperraum-Interdiktion-Forschung (max 6).">📡 Abfang-Radius {{ interceptRadius() }} Sys</label>
              <input type="number" min="0" max="6" [ngModel]="interceptRadius()" (ngModelChange)="interceptRadius.set(+$event || 0)" />
            </div>
          </div>
        }

        <!-- W0: Eskorte (escort) — Deckungs-Radius + Gebühr -->
        @if (mission() === 'escort' && !patrolMode()) {
          <div class="opts">
            <div class="field">
              <label class="tip" data-tip="Wie viele Systeme um das Stationssystem dein Geleitschutz-Angebot Handelsrouten deckt.">🛡 Eskort-Radius {{ escortRadius() }} Sys</label>
              <input type="number" min="0" max="50" [ngModel]="escortRadius()" (ngModelChange)="escortRadius.set(+$event || 0)" />
            </div>
            <div class="field">
              <label class="tip" data-tip="Dein Anteil am Frachtwert, den der Trader als Deuterium zahlt (max. 10 %).">Gebühr {{ escortFeePct() }} %</label>
              <input type="number" min="0" max="10" step="0.5" [ngModel]="escortFeePct()" (ngModelChange)="escortFeePct.set(+$event || 0)" />
            </div>
          </div>
        }

        <!-- Cargo (Transport/Stationierung/Kolonisierung) -->
        @if (showCargo()) {
          <div class="cargo">
            <div class="cargo-head">
              <div class="cargo-title"><app-btn-icon [src]="statIcon('cargo')" glyph="📦" [size]="16" /> Fracht laden</div>
              <button class="btn btn-trade btn-sm" type="button"
                [disabled]="cargoInfo().capacity <= 0" (click)="fillAllCargo()">Alles laden</button>
            </div>
            @if (cargoInfo().capacity <= 0) {
              <p class="hint small">Zuerst Schiffe mit Frachtraum auswählen.</p>
            }
            <div class="cargo-row">
              @for (r of cargoLoadFields; track r.key) {
                @if (showCargoField(r.key)) {
                <div class="cargo-field">
                  <label><img class="cargo-ico" [src]="resourceIcon(r.key)" alt="" (error)="hideImg($event)" />{{ r.label }}</label>
                  <div class="cargo-input">
                    <input type="number" min="0" [max]="cargoCapFor(r.key)"
                      [ngModel]="cargo()[r.key]" (ngModelChange)="setCargo(r.key, $event)" />
                    <button class="btn btn-ghost btn-sm" type="button"
                      [disabled]="cargoCapFor(r.key) <= 0"
                      (click)="setCargo(r.key, cargoCapFor(r.key))">max</button>
                  </div>
                  <span class="cargo-avail faint mono">{{ availOnPlanet(r.key).toLocaleString('de-DE') }} verfügbar</span>
                </div>
                }
              }
            </div>
          </div>
        }

        <!-- Handelsauftrag -->
        @if (showTrade()) {
          <div class="cargo">
            <div class="cargo-title"><app-btn-icon [src]="navIcon('market')" glyph="💱" [size]="16" /> Handelsauftrag</div>
            <div class="trade-grid">
              <div class="field">
                <label>Biete</label>
                <select [ngModel]="offerRes()" (ngModelChange)="offerRes.set($event)">
                  @for (r of cargoFields; track r.key) { <option [ngValue]="r.key">{{ r.glyph }} {{ r.label }}</option> }
                </select>
                <input type="number" min="0" [max]="planetRes()?.[offerRes()]?.amount ?? 0"
                  [ngModel]="offerAmount()" (ngModelChange)="offerAmount.set(+$event || 0)" aria-label="Angebotsmenge" />
              </div>
              <div class="field">
                <label>Erhalte</label>
                <select [ngModel]="wantRes()" (ngModelChange)="wantRes.set($event)">
                  @for (r of cargoFields; track r.key) { <option [ngValue]="r.key">{{ r.glyph }} {{ r.label }}</option> }
                </select>
                @if (merchantIntel(); as mi) {
                  @if (mi.trade_center) {
                    <span class="muted small"><app-btn-icon [src]="navIcon('market')" glyph="💱" [size]="14" /> Handelszentrum · globaler Handelskurs</span>
                  } @else {
                    <span class="muted small">Spez.: {{ mi.spec }} · Kurse vom letzten Besuch</span>
                  }
                } @else {
                  <span class="muted small">Richtwert: globaler Handelskurs</span>
                }
              </div>
            </div>
            @if (tradeEstimate(); as est) {
              <p class="trade-preview small">≈ <strong>{{ est }}</strong> {{ wantRes() }} (ungefähr, vor Slippage/Reputation)</p>
            }
            @if (offerRes() === wantRes()) {
              <p class="hint small">Biete- und Wunsch-Ressource müssen verschieden sein.</p>
            }
            @if (coveringEscorts().length) {
              <div class="escorts">
                <div class="cargo-title"><app-btn-icon [src]="statIcon('shield')" glyph="🛡" [size]="16" /> Eskorte auf der Route</div>
                @for (e of coveringEscorts(); track e.id) {
                  <label class="escort-row small">
                    <input type="checkbox" [checked]="chosenEscorts().has(e.id)" (change)="toggleEscort(e.id)" />
                    {{ e.owner }} [{{ e.coords }}] · Kraft ~{{ e.power }} · {{ (e.fee_pct * 100).toFixed(1) }}% Gebühr
                  </label>
                }
              </div>
            }
            <p class="muted small">🛡 Frachter ohne bewaffnete Eskorte werden auf der Route überfallen.</p>
          </div>
        }

        @if (!patrolMode()) {
        <!-- Commander + Tempo -->
        <div class="opts">
          <div class="field">
            <label>Commander</label>
            <select [ngModel]="commanderId()" (ngModelChange)="commanderId.set($event)">
              <option [ngValue]="null">— ohne —</option>
              @for (c of assignableCommanders(); track c.id) {
                <option [ngValue]="c.id">{{ rankMeta(c.rank).glyph }} {{ c.name }}</option>
              }
            </select>
          </div>
          <div class="field">
            <label class="tip" data-tip="Langsamer = weniger Sprit">Tempo {{ speed() }}%</label>
            <input type="range" min="10" max="100" step="10" [ngModel]="speed()" (ngModelChange)="speed.set($event)" />
          </div>
        </div>
        @if (commanderId() && commanderAbilities().abilities.length) {
          <div class="escorts">
            <div class="cargo-title"><app-btn-icon [src]="uiIcon('ability')" glyph="⚡" [size]="16" /> Fähigkeiten scharf ({{ armed().size }}/{{ commanderAbilities().slots }})</div>
            @for (a of commanderAbilities().abilities; track a.key) {
              <label class="escort-row small">
                <input type="checkbox" [checked]="armed().has(a.key)" (change)="toggleArmed(a.key)" />
                {{ abilityLabel(a.key) }} · Stufe {{ a.level }}
              </label>
            }
          </div>
        }

        @if (mission() === 'expedition') {
          <div class="field">
            <label class="tip" data-tip="Offline-sicher: legt vorab fest, wie deine Expedition auf Ereignisse (z.B. ein Geisterschiff) reagiert. Vorsichtig = weniger Risiko & Ertrag; Risikofreudig = mehr Risiko, mehr Ertrag, hackt den Geisterschiff-Kern.">
              <app-btn-icon [src]="missionIcon('expedition')" glyph="🌌" [size]="16" /> Expeditions-Doktrin
            </label>
            <div class="doctrine-row">
              <button type="button" class="btn btn-sm" [class.btn-primary]="expeditionDoctrine() === 'cautious'" [class.btn-ghost]="expeditionDoctrine() !== 'cautious'" (click)="expeditionDoctrine.set('cautious')">🛡️ Vorsichtig</button>
              <button type="button" class="btn btn-sm" [class.btn-primary]="expeditionDoctrine() === 'neutral'" [class.btn-ghost]="expeditionDoctrine() !== 'neutral'" (click)="expeditionDoctrine.set('neutral')">⚖️ Neutral</button>
              <button type="button" class="btn btn-sm" [class.btn-primary]="expeditionDoctrine() === 'bold'" [class.btn-ghost]="expeditionDoctrine() !== 'bold'" (click)="expeditionDoctrine.set('bold')">🔥 Risikofreudig</button>
            </div>
          </div>
          <div class="field">
            @if (maxExpHours() > 0) {
              <label class="tip" data-tip="Länger = mehr Ertrag, aber mehr Risiko (Piraten/Aliens/Schwarzes Loch). Forschung Astrophysik hebt das Maximum (bis 24h).">
                <app-btn-icon [src]="missionIcon('expedition')" glyph="🌌" [size]="16" /> Verweildauer {{ expHours() }} / {{ maxExpHours() }} h
              </label>
              <input type="range" min="1" [max]="maxExpHours()" step="1" [ngModel]="expHours()" (ngModelChange)="setExpHours($event)" />
            } @else {
              <p class="hint small">Astrophysik Stufe 1 nötig, um Expeditionen in die galaktischen Weiten zu entsenden.</p>
            }
          </div>
        }

        @if (mission() === 'attack') {
          <div class="field">
            <label class="tip" data-tip="Welche GESTRANDETEN Gegnerschiffe (Antrieb durch Ionen lahmgelegt) deine Enterschiffe bevorzugt kapern. Standard: die wertvollsten zuerst.">
              <app-btn-icon [src]="missionIcon('attack')" glyph="🪝" [size]="16" /> Kaper-Priorität
            </label>
            <select [ngModel]="capturePriority()" (ngModelChange)="capturePriority.set($event)">
              <option value="value">Wertvollste zuerst</option>
              @for (t of captureTargets; track t) {
                <option [value]="t">{{ shipMeta(t).label }} zuerst</option>
              }
            </select>
          </div>
        }

        @if (hasSelection()) {
          <div class="fleet-summary" [class.out]="rangeInfo()?.inRange === false">
            <div class="cap-head">
              <span class="cap-label"><app-btn-icon [src]="statIcon('cargo')" glyph="📦" [size]="14" /> Frachtraum</span>
              <span class="cap-val mono" [class.over]="cargoInfo().over">{{ cargoInfo().used.toLocaleString('de-DE') }} / {{ cargoInfo().capacity.toLocaleString('de-DE') }}</span>
            </div>
            <div class="bar" [class.full]="cargoInfo().over">
              <div class="fill" [style.width.%]="capPct()"></div>
            </div>
            <div class="sum-grid">
              <div class="sum-cell tip" data-tip="Noch freie Frachtkapazität der gewählten Flotte">
                <span class="faint">Frei</span><span class="mono" [class.over]="cargoInfo().over">{{ cargoInfo().free.toLocaleString('de-DE') }}</span>
              </div>
              @if (rangeInfo(); as r) {
                <div class="sum-cell tip" data-tip="Distanz zwischen Startplanet und Ziel (OGame-Distanzmodell)">
                  <span class="faint"><app-btn-icon [src]="uiIcon('distance')" glyph="📏" [size]="14" /> Distanz</span><span class="mono">{{ r.distance.toLocaleString('de-DE') }}</span>
                </div>
                <div class="sum-cell tip" [attr.data-tip]="'Reichweite der Flotte (Tank). Limitierendes Schiff: ' + shipLabel(r.limiting)">
                  <span class="faint">🛰 Reichweite</span><span class="mono" [class.over]="!r.inRange">{{ r.maxRangeText }}</span>
                </div>
                <div class="sum-cell tip" data-tip="Treibstoff (Deuterium) vom Startplaneten">
                  <span class="faint"><img class="cargo-ico" [src]="resourceIcon('deuterium')" alt="" (error)="hideImg($event)" />Sprit</span><span class="mono">{{ r.fuel.toLocaleString('de-DE') }} {{ r.roundTrip ? '(H+R)' : '' }}</span>
                </div>
                <div class="sum-cell tip" data-tip="Geschätzte Flugzeit je Strecke (ohne Antriebsforschung — mit Forschung schneller). Tempo-Regler wirkt.">
                  <span class="faint"><app-btn-icon [src]="uiIcon('time')" glyph="⏱" [size]="14" /> Flugzeit</span><span class="mono">{{ flightText(flightSecs()) }}{{ r.roundTrip ? ' /Strecke' : '' }}</span>
                </div>
              }
            </div>
          </div>
        }
        }

        <div class="actions">
          <button class="btn btn-primary" type="button" [disabled]="!canSend() || sending()" (click)="send()">
            @if (patrolMode()) {
              {{ sending() ? 'Sende…' : '⚔ Patrouille aufstellen' }}
            } @else {
              {{ sending() ? 'Sende…' : (missionMeta(mission()).glyph + ' ' + missionMeta(mission()).label + ' starten') }}
            }
          </button>
        </div>
        @if (!hasSelection()) {
          <p class="hint small">Mindestens ein Schiff auswählen.</p>
        } @else if (showCargo() && cargoInfo().over) {
          <p class="hint small">Frachtraum überladen: {{ cargoInfo().used.toLocaleString('de-DE') }} / {{ cargoInfo().capacity.toLocaleString('de-DE') }}. Fracht reduzieren oder mehr Schiffe wählen.</p>
        } @else if (rangeInfo(); as r) {
          @if (!r.inRange) {
            <p class="hint small">Außer Reichweite: {{ shipLabel(r.limiting) }} schafft nur {{ r.maxRangeText }} (Hin+Rück). Kürzeres Ziel wählen, das schwächste Schiff weglassen oder per Stationierung vorschieben.</p>
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
      /* .glass (global) liefert Background/Blur/Border/Elevation; hier nur Layout + Signatur-Ecke. */
      .popup {
        position: relative; width: 100%; max-width: 560px; max-height: 88vh; overflow-y: auto;
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
      .coord { color: var(--accent); font-size: var(--fs-base); }
      .tname { color: var(--text-dim); font-size: var(--fs-sm); }

      /* W0: editierbares Ziel (Koordinaten-Eingabe) */
      .target-edit { margin-top: var(--sp-3); display: flex; flex-direction: column; gap: var(--sp-1); }
      .coord-inputs { display: flex; align-items: center; gap: var(--sp-1); }
      .coord-inputs input { width: 64px; text-align: center; min-height: 32px; padding: var(--sp-1); }
      .coord-inputs .sep { color: var(--text-faint); font-weight: 700; }

      /* Welle 5: Konjunktions-Hinweis fuer die Route */
      .conj-badge {
        margin-top: var(--sp-3); padding: var(--sp-2) var(--sp-3); border-radius: var(--r-md);
        font-size: var(--fs-sm); display: flex; align-items: center; flex-wrap: wrap; gap: 4px var(--sp-2);
        border: 1px solid var(--border);
      }
      .conj-badge.active {
        color: #3ddc97; background: rgba(61,220,151,0.08); border-color: rgba(61,220,151,0.35);
      }
      .conj-badge.upcoming { color: var(--text-dim); background: rgba(255,255,255,0.03); }
      .conj-badge .conj-cd { color: inherit; }

      .mission-tabs { display: flex; flex-wrap: wrap; gap: var(--sp-1); margin: var(--sp-3) 0; }
      .mtab {
        font-size: var(--fs-sm); padding: var(--sp-1) var(--sp-3); border-radius: var(--r-pill);
        background: rgba(255,255,255,0.04); border: 1px solid var(--border); color: var(--text-dim); cursor: pointer;
        transition: color var(--motion-fast) var(--ease-out), border-color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .mtab:hover { color: var(--text); border-color: var(--border-strong); }
      .mtab.active { background: var(--accent-soft); color: var(--accent); border-color: var(--accent-dim); }
      .mtab-ico { width: 16px; height: 16px; object-fit: contain; vertical-align: -3px; margin-right: 4px; }
      .cargo-ico { width: 15px; height: 15px; object-fit: contain; vertical-align: -2px; margin-right: 4px; }

      .ships {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
        gap: var(--sp-2); margin-top: var(--sp-1);
      }
      .ship {
        display: flex; flex-direction: column; align-items: center; gap: var(--sp-1);
        padding: var(--sp-2); border: 1px solid var(--border); border-radius: var(--r-md);
        background: rgba(255,255,255,0.02);
        transition: border-color var(--motion-fast) var(--ease-out), background var(--motion-fast) var(--ease-out);
      }
      .ship.picked { border-color: var(--accent-dim); background: var(--accent-soft); }
      .ship-art { position: relative; }
      .ship-art .avail {
        position: absolute; bottom: -4px; right: -6px; min-width: 18px; padding: 0 4px; height: 18px;
        border-radius: var(--r-pill); background: var(--surface-3); border: 1px solid var(--border);
        font-size: var(--fs-xs); display: flex; align-items: center; justify-content: center; color: var(--text);
        font-family: var(--mono); font-variant-numeric: tabular-nums;
      }
      .ship-name { font-size: var(--fs-sm); text-align: center; line-height: 1.1; color: var(--text-dim); }
      .ship-pick { display: flex; gap: var(--sp-1); align-items: center; }
      .ship-pick input { width: 52px; text-align: center; min-height: 28px; padding: var(--sp-1); }
      .ship-cargo { font-size: var(--fs-xs); color: var(--accent); }

      .cargo { margin-top: var(--sp-3); }
      .cargo-head { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); margin-bottom: var(--sp-2); }
      .cargo-title { font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); }
      .cargo-row { display: flex; flex-wrap: wrap; gap: var(--sp-3); }
      .cargo-field { display: flex; flex-direction: column; gap: var(--sp-1); flex: 1 1 150px; }
      .cargo-field label { font-size: var(--fs-xs); color: var(--text-dim); }
      .cargo-input { display: flex; gap: var(--sp-1); align-items: center; }
      .cargo-input input { min-height: 32px; }
      .cargo-input .btn { flex: 0 0 auto; }
      .cargo-avail { font-size: var(--fs-xs); }

      .opts { display: flex; flex-wrap: wrap; gap: var(--sp-3); margin-top: var(--sp-3); }
      .opts .field { flex: 1 1 200px; display: flex; flex-direction: column; gap: var(--sp-1); }
      .opts label { font-size: var(--fs-xs); color: var(--text-dim); }

      .trade-grid { display: flex; flex-wrap: wrap; gap: var(--sp-3); }
      .trade-grid .field { flex: 1 1 200px; display: flex; flex-direction: column; gap: var(--sp-1); }
      .trade-grid select, .trade-grid input { min-height: 30px; }
      .doctrine-row { display: flex; flex-wrap: wrap; gap: var(--sp-1); }
      .trade-preview { color: var(--accent); margin: var(--sp-2) 0 0; }
      .escorts { margin-top: var(--sp-2); }
      .escort-row { display: flex; align-items: center; gap: var(--sp-1); padding: 2px 0; cursor: pointer; }

      .actions { margin-top: var(--sp-4); }
      .actions .btn { width: 100%; }
      .hint { color: var(--warn); margin: var(--sp-1) 0 0; }
      .small { font-size: var(--fs-sm); }

      .fleet-summary {
        margin-top: var(--sp-3); padding: var(--sp-3);
        border: 1px solid var(--border); border-radius: var(--r-md);
        background: rgba(255,255,255,0.02);
        transition: border-color var(--motion-fast) var(--ease-out);
      }
      .fleet-summary.out { border-color: var(--warn); }
      .cap-head { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-2); margin-bottom: var(--sp-2); }
      .cap-label { font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); }
      .cap-val { font-size: var(--fs-base); color: var(--text); font-variant-numeric: tabular-nums; }
      .cap-val.over { color: var(--danger); font-weight: 600; }
      .sum-grid {
        display: grid; grid-template-columns: repeat(auto-fill, minmax(120px, 1fr));
        gap: var(--sp-1) var(--sp-3); margin-top: var(--sp-3);
      }
      .sum-cell { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-2); font-size: var(--fs-sm); }
      .sum-cell .faint { font-size: var(--fs-xs); }
      .sum-cell .mono { font-variant-numeric: tabular-nums; color: var(--text); }
      .sum-cell .mono.over { color: var(--danger); font-weight: 600; }

      @media (max-width: 560px) {
        .backdrop { padding: var(--sp-2); }
        .popup { max-width: 100%; max-height: 94vh; padding: var(--sp-4); }
      }
    `,
  ],
})
export class FleetDispatchComponent {
  private readonly api = inject(ApiService);
  private readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);
  private readonly balanceSvc = inject(BalanceService);
  private readonly calc = inject(FleetCalculationService);

  /** Festes Ziel (Galaxie/Bergbau/Handel/Expedition). Bei editierbarem Ziel optional als Vorbelegung. */
  readonly target = input<Coordinate | null>(null);
  readonly targetName = input<string | null>(null);
  readonly initialMission = input<FleetMission>('attack');
  /** 'moon' -> Angriff/Spionage zielt auf den Mond; 'station' -> Belagerung der Allianz-Station;
   *  'mining_fleet' -> Angriff auf die am Feld schuerfende Flotte. */
  readonly targetType = input<'moon' | 'station' | 'mining_fleet' | null>(null);
  /** W0: editierbares Ziel (allgemeiner Versand aus dem Flotten-Screen) — zeigt Koordinaten-Eingaben
   *  oben und bietet den vollen Missions-Satz. Bestehende Aufrufer (festes Ziel) lassen dies weg. */
  readonly editableTarget = input<boolean>(false);
  /** W0: Patrouillen-Modus — nur Schiffs-Picker + Radius, ruft api.patrolHome statt sendFleet
   *  (eigenes System abfangen, ohne Flug). */
  readonly patrolMode = input<boolean>(false);

  readonly close = output<void>();
  readonly sent = output<void>();

  // -- Editierbares Ziel (nur bei editableTarget): Koordinaten-Eingaben -----------
  protected readonly tgtG = signal(1);
  protected readonly tgtS = signal(1);
  protected readonly tgtP = signal(1);

  /** Tatsächlich verwendetes Ziel: festes target() (readonly) ODER die getippten Koordinaten. */
  protected readonly effTarget = computed<Coordinate>(() => {
    if (this.patrolMode()) {
      const p = this.state.activePlanet();
      return p ? { galaxy: p.galaxy, system: p.system, position: p.position } : { galaxy: 1, system: 1, position: 1 };
    }
    if (!this.editableTarget()) {
      const t = this.target();
      if (t) {
        return t;
      }
      const p = this.state.activePlanet();
      return p ? { galaxy: p.galaxy, system: p.system, position: p.position } : { galaxy: 1, system: 1, position: 1 };
    }
    return { galaxy: this.tgtG(), system: this.tgtS(), position: this.tgtP() };
  });

  /** Missionswahl:
   *  - editierbares Ziel (allgemeiner Flotten-Versand): voller Missions-Satz inkl. intercept/escort/recycle.
   *  - festes Ziel am Deep-Space-Slot: NUR Expedition.
   *  - festes Ziel sonst: die normalen Schnellaktionen (Galaxie/Bergbau/Handel). */
  protected readonly missions = computed<FleetMission[]>(() => {
    if (this.editableTarget()) {
      return ['attack', 'transport', 'spy', 'deploy', 'intercept', 'escort', 'recycle', 'colonize'];
    }
    const deep = this.bnum((this.balanceSvc.value as any)?.expedition?.deep_space_position);
    if (deep && this.effTarget().position === deep) {
      return ['expedition'];
    }
    return ['attack', 'transport', 'spy', 'deploy', 'colonize', 'mine', 'trade'];
  });
  protected readonly mission = linkedSignal<FleetMission>(() => this.initialMission());

  // -- W0: Missions-spezifische Felder (aus der alten fleet.component übernommen) --
  /** Abfangen (intercept): Patrouillen-Radius in Systemen (0 = nur Zielsystem). */
  protected readonly interceptRadius = signal(0);
  /** Eskorte (escort): Deckungs-Radius in Systemen + Gebühr (Prozent 0..10, Backend deckelt). */
  protected readonly escortRadius = signal(5);
  protected readonly escortFeePct = signal(2);
  /** Patrouille (patrolMode): Abfang-Radius um das eigene System (0..6). */
  protected readonly patrolRadius = signal(0);

  // NUR metal/crystal/deuterium — auch für die Handels-Dropdowns (kein NPC-Handel mit Exoten!).
  protected readonly cargoFields = [
    { key: 'metal' as const, glyph: '⛏️', label: 'Metall' },
    { key: 'crystal' as const, glyph: '💎', label: 'Kristall' },
    { key: 'deuterium' as const, glyph: '🛢️', label: 'Deuterium' },
  ];
  // Fracht-Beladung (Transport): inkl. Exoten (pro Planet, transportierbar).
  protected readonly cargoLoadFields = [
    { key: 'metal' as const, label: 'Metall' },
    { key: 'crystal' as const, label: 'Kristall' },
    { key: 'deuterium' as const, label: 'Deuterium' },
    { key: 'antimatter' as const, label: 'Antimaterie' },
    { key: 'dark_matter' as const, label: 'Dunkle Materie' },
  ];

  protected readonly selection = signal<Record<string, number>>({});
  protected readonly cargo = signal<Record<DispatchCargoKey, number>>({
    metal: 0, crystal: 0, deuterium: 0, antimatter: 0, dark_matter: 0,
  });
  protected readonly commanderId = signal<string | null>(null);
  protected readonly speed = signal(100);
  protected readonly armed = signal<Set<string>>(new Set());
  protected readonly abilityCatalog = signal<Record<string, { label: string }>>({});
  protected readonly sending = signal(false);

  /** Erlernte Faehigkeiten des gewaehlten Kommandeurs (fuer die Scharfschalt-Auswahl). */
  protected readonly commanderAbilities = computed(() => {
    const id = this.commanderId();
    const c = this.assignableCommanders().find((x) => x.id === id);
    return c ? { abilities: c.abilities ?? [], slots: c.arm_slots ?? 1 } : { abilities: [], slots: 1 };
  });

  toggleArmed(key: string): void {
    this.armed.update((s) => {
      const next = new Set(s);
      if (next.has(key)) {
        next.delete(key);
      } else if (next.size < this.commanderAbilities().slots) {
        next.add(key);
      }
      return next;
    });
  }

  abilityLabel(key: string): string {
    return this.abilityCatalog()[key]?.label ?? key;
  }

  // --- Handel ---
  protected readonly offerRes = signal<'metal' | 'crystal' | 'deuterium'>('metal');
  protected readonly offerAmount = signal(0);
  protected readonly wantRes = signal<'metal' | 'crystal' | 'deuterium'>('deuterium');
  protected readonly merchantIntel = signal<GalaxyIntel | null>(null);
  /** Oeffentlicher globaler Handelskurs (Handelszentren) — immer verfuegbar. */
  protected readonly globalIndex = signal<TradeIndex | null>(null);
  /** Eskort-Angebote, die die Route decken (nur Handel relevant). */
  protected readonly escortOffers = signal<EscortOffer[]>([]);
  protected readonly chosenEscorts = signal<Set<string>>(new Set());

  // --- Welle 5: Konjunktions-Fenster (reine Anzeige fuer die gewaehlte Route) ---
  protected readonly conjunctions = signal<ConjunctionInfo | null>(null);

  /** Trifft ein Konjunktions-Eintrag die aktuelle Route (Origin↔Ziel, Richtung egal)? */
  private routeMatch(c: Conjunction): boolean {
    const p = this.state.activePlanet();
    const t = this.effTarget();
    if (!p) {
      return false;
    }
    const a = { g: p.galaxy, s: p.system };
    const b = { g: t.galaxy, s: t.system };
    const f = c.from_coords;
    const to = c.to_coords;
    return (
      (f.galaxy === a.g && f.system === a.s && to.galaxy === b.g && to.system === b.s) ||
      (f.galaxy === b.g && f.system === b.s && to.galaxy === a.g && to.system === a.s)
    );
  }

  /** Gerade aktive Konjunktion auf der Route (oder null). */
  protected readonly routeConjunction = computed<Conjunction | null>(() =>
    (this.conjunctions()?.active ?? []).find((c) => this.routeMatch(c)) ?? null,
  );

  /** Naechstes guenstiges Fenster (discount_pct > 0) auf der Route, wenn keins aktiv ist. */
  protected readonly nextRouteConjunction = computed<Conjunction | null>(() =>
    (this.conjunctions()?.upcoming ?? []).find((c) => c.discount_pct > 0 && this.routeMatch(c)) ?? null,
  );

  /** Eskort-Angebote, deren Station die Route (Origin↔Ziel) im Radius schneidet. */
  protected readonly coveringEscorts = computed<EscortOffer[]>(() => {
    const t = this.effTarget();
    const p = this.state.activePlanet();
    if (!p) {
      return [];
    }
    const lo = Math.min(p.system, t.system);
    const hi = Math.max(p.system, t.system);
    return this.escortOffers().filter(
      (o) => o.galaxy === t.galaxy && p.galaxy === t.galaxy && o.system >= lo - o.radius && o.system <= hi + o.radius,
    );
  });

  protected readonly showTrade = computed(() => this.mission() === 'trade');

  /** Kaper-Priorität (mission == 'attack'): 'value' (teuerste zuerst) oder ein Schiffstyp-Key. */
  protected readonly capturePriority = signal<string>('value');
  /** Lohnende Kaperziele für das Dropdown (wertvolle Kampf-/Capital-/Frachtschiffe). */
  protected readonly captureTargets = [
    'battleship', 'battlecruiser', 'destroyer', 'cruiser', 'bomber',
    'corsair', 'carrier', 'deathstar', 'harvest_titan', 'trade_leviathan', 'large_cargo',
  ];

  /** Ist das Ziel ein (oeffentliches) Handelszentrum mit globalem Kurs? */
  protected readonly isCenter = computed(() => !!this.merchantIntel()?.trade_center);

  /**
   * Massgebliche Kurse fuer die Vorschau: lokaler Legacy-Haendler-Snapshot, falls
   * vorhanden; sonst der immer verfuegbare globale Index (Handelszentren).
   */
  protected readonly effPrices = computed<{ metal?: number; crystal?: number; deuterium?: number } | null>(() => {
    const local = this.merchantIntel();
    if (local && !local.trade_center && local.prices) {
      return local.prices;
    }
    return this.globalIndex()?.prices ?? local?.prices ?? null;
  });

  /**
   * Grobe Vorschau aus den massgeblichen Kursen (OHNE Slippage/Reputation — der echte
   * Tausch wird serverseitig bei Ankunft berechnet).
   */
  protected readonly tradeEstimate = computed<number | null>(() => {
    const p = this.effPrices();
    if (!p) {
      return null;
    }
    const pIn = p[this.offerRes()] ?? 0;
    const pOut = p[this.wantRes()] ?? 0;
    if (pIn <= 0 || pOut <= 0 || this.offerAmount() <= 0) {
      return null;
    }
    return Math.round(this.offerAmount() * (pIn / pOut) * 0.96); // 0.96 ≈ Standard-Marge
  });

  private readonly missionRequires: Partial<Record<FleetMission, { type: string; label: string }>> = {
    spy: { type: 'spy_probe', label: 'Spionagesonde' },
    colonize: { type: 'colony_ship', label: 'Kolonieschiff' },
    mine: { type: 'miner', label: 'Bergbauschiff' },
    recycle: { type: 'recycler', label: 'Recycler' },
    expedition: { type: 'expedition_ship', label: 'Expeditionsschiff' },
  };

  toggleEscort(id: string): void {
    this.chosenEscorts.update((s) => {
      const next = new Set(s);
      next.has(id) ? next.delete(id) : next.add(id);
      return next;
    });
  }

  constructor() {
    // W0: editierbares Ziel mit dem festen target() bzw. dem aktiven Planeten vorbelegen.
    const seed = this.target() ?? this.state.activePlanet();
    if (seed) {
      this.tgtG.set(seed.galaxy);
      this.tgtS.set(seed.system);
      this.tgtP.set((seed as Coordinate).position ?? 1);
    }
    // Globalen Handelskurs laden (immer verfuegbar — keine Aufklaerung noetig).
    this.api.getTradeIndex().subscribe((idx) => this.globalIndex.set(idx));
    // Eskort-Angebote (fuer die Routen-Auswahl im Handel) laden.
    this.api.getEscortOffers().subscribe((list) => this.escortOffers.set(list));
    // Welle 5: Konjunktions-Fenster laden (fuer den Routen-Hinweis; Fehler stumm).
    this.api.getConjunctions().subscribe({
      next: (c) => this.conjunctions.set(c),
      error: () => {},
    });
    // Faehigkeiten-Katalog (fuer Labels der Scharfschalt-Auswahl).
    this.api.getAbilityCatalog().subscribe((c) => this.abilityCatalog.set(c.catalog as Record<string, { label: string }>));
    // Astrophysik-Stufe (begrenzt die Expeditions-Verweildauer).
    this.api.getResearch().subscribe((r) => {
      const astro = (r.research ?? []).find((x) => x.type === 'astrophysics');
      this.astroLevel.set(astro?.level ?? 0);
    });
    // Schrumpft die Auswahl, sodass die geladene Fracht die Kapazitaet uebersteigt,
    // automatisch von hinten (Deut -> Kristall -> Metall) kuerzen -> nie ueberladen.
    effect(() => {
      const cap = this.cargoInfo().capacity;
      const c = this.cargo();
      let used = CARGO_LOAD_KEYS.reduce((s, k) => s + (c[k] || 0), 0);
      if (used <= cap) {
        return;
      }
      const next = { ...c };
      // Erst Standard-Ressourcen kuerzen, Exoten zuletzt (wertvoll -> moeglichst behalten).
      for (const k of ['deuterium', 'crystal', 'metal', 'antimatter', 'dark_matter'] as const) {
        if (used <= cap) {
          break;
        }
        const cut = Math.min(next[k], used - cap);
        next[k] -= cut;
        used -= cut;
      }
      this.cargo.set(next);
    });
    // Kurs-Schnappschuss/Typ des Zielhaendlers laden (Handelszentrum vs. Legacy).
    effect(() => {
      const t = this.effTarget();
      this.api.getGalaxyTargets().subscribe((list) => {
        const hit = list.find(
          (x) => x.galaxy === t.galaxy && x.system === t.system && x.position === t.position,
        );
        this.merchantIntel.set(hit?.intel?.merchant ? (hit.intel as GalaxyIntel) : null);
      });
    });
  }

  // Nur entsendbare Schiffe: count > 0 UND mit Antrieb (stationaere Einheiten wie der
  // Solarsatellit haben speed 0 und bleiben in der Umlaufbahn -> nicht waehlbar).
  protected readonly availableShips = computed<PlanetUnit[]>(() => {
    const ships = this.balanceSvc.value?.ships as Record<string, { speed?: number }> | undefined;
    return (
      this.state.activePlanet()?.ships?.filter(
        (s) => s.count > 0 && (ships?.[s.type]?.speed ?? 1) > 0,
      ) ?? []
    );
  });
  protected readonly planetRes = computed(() => this.state.activePlanet()?.resources ?? null);
  protected readonly assignableCommanders = computed(() =>
    this.state.commanders().filter((c) => c.status !== 'training' && !c.assigned_fleet_id),
  );

  protected readonly showCargo = computed(
    () =>
      this.mission() === 'transport' ||
      this.mission() === 'deploy' ||
      this.mission() === 'colonize', // W0: Fracht startet die neue Kolonie (Backend bucht sie ein)
  );
  protected readonly hasSelection = computed(() =>
    Object.values(this.selection()).some((n) => n > 0),
  );
  protected readonly missionHint = computed<string | null>(() => {
    const req = this.missionRequires[this.mission()];
    if (!req) {
      return null;
    }
    return this.shipCount(req.type) > 0 ? null : `Diese Mission benötigt mindestens ein ${req.label}.`;
  });
  protected readonly canSend = computed(() => {
    if (!this.hasSelection() || !this.state.activePlanetId()) {
      return false;
    }
    // Patrouille: kein Ziel/keine Reichweite/keine Pflicht-Schiffe — nur Auswahl nötig.
    if (this.patrolMode()) {
      return true;
    }
    if (this.missionHint()) {
      return false;
    }
    if (this.rangeInfo()?.inRange === false) {
      return false;
    }
    if (this.showCargo() && this.cargoInfo().over) {
      return false;
    }
    if (this.mission() === 'expedition') {
      return this.maxExpHours() > 0;
    }
    if (this.mission() === 'trade') {
      return this.offerAmount() > 0 && this.offerRes() !== this.wantRes();
    }
    return true;
  });

  // -- Treibstoff-Tank: Reichweite (Hin+Rück) + Spritkosten — Rechnung via FleetCalculationService.
  private bnum(v: unknown, d = 0): number {
    return typeof v === 'number' ? v : d;
  }

  /** Origin-Koordinaten des aktiven Planeten (für die Distanz/Reichweiten-Rechnung). */
  private originCoord(): Coordinate | null {
    const p = this.state.activePlanet();
    return p ? { galaxy: p.galaxy, system: p.system, position: p.position } : null;
  }

  protected readonly rangeInfo = computed<{
    distance: number; maxRange: number; maxRangeText: string;
    limiting: string | null; fuel: number; roundTrip: boolean; inRange: boolean;
  } | null>(() => {
    const sel = this.selection();
    const entries = Object.entries(sel).filter(([, n]) => n > 0);
    const bal = this.balanceSvc.value as any;
    const dist = this.calc.distanceTo(this.originCoord(), this.effTarget(), bal);
    if (!entries.length || dist === null) return null;
    const roundTrip = this.mission() !== 'deploy';
    const { maxRange, limiting } = this.calc.fleetMaxRange(sel, roundTrip, bal);
    const fuel = this.calc.fuelCost(sel, dist, roundTrip, bal);
    return {
      distance: dist,
      maxRange,
      maxRangeText: maxRange === Infinity ? '∞' : Math.floor(maxRange).toLocaleString('de-DE'),
      limiting,
      fuel,
      roundTrip,
      inRange: dist <= maxRange,
    };
  });

  shipLabel(type: string | null): string {
    return type ? metaFor(SHIP_META, type).label : '';
  }

  /** Gesamt-Frachtkapazitaet der gewaehlten Flotte + aktuell beladene Menge (OGame-artig). */
  protected readonly cargoInfo = computed(() => {
    const capacity = this.calc.cargoCapacity(this.selection(), this.balanceSvc.value as any);
    let used = 0;
    if (this.mission() === 'trade') {
      used = this.bnum(this.offerAmount());
    } else {
      const c = this.cargo();
      used = CARGO_LOAD_KEYS.reduce((s, k) => s + this.bnum(c[k]), 0);
    }
    return { capacity, used, free: Math.max(0, capacity - used), over: used > capacity };
  });

  /** Geschaetzte Flugzeit (eine Strecke) — gespiegelt aus flight_seconds, OHNE Antriebsforschung
   * (daher konservativ/Obergrenze). null wenn keine Distanz/Auswahl. */
  protected readonly flightSecs = computed<number | null>(() => {
    const bal = this.balanceSvc.value as any;
    const dist = this.calc.distanceTo(this.originCoord(), this.effTarget(), bal);
    return this.calc.flightSeconds(dist, this.selection(), this.speed(), bal);
  });

  protected flightText(secs: number | null): string {
    if (secs === null) return '–';
    const s = Math.max(0, Math.round(secs));
    const h = Math.floor(s / 3600);
    const m = Math.floor((s % 3600) / 60);
    const sec = s % 60;
    return (h ? `${h}h ` : '') + (h || m ? `${m}m ` : '') + `${sec}s`;
  }

  // -- Expedition: Verweildauer (1..max, max aus Astrophysik) -------------------
  protected readonly astroLevel = signal(0);
  protected readonly expHours = signal(1);
  /** Expeditions-Doktrin (offline-sichere Vorab-Wahl): biegt Risiko + Ertrag. */
  protected readonly expeditionDoctrine = signal<'cautious' | 'neutral' | 'bold'>('neutral');

  /** Maximale Verweildauer = min(astrophysics * per_level, hour_cap); 0 = nicht freigeschaltet. */
  protected readonly maxExpHours = computed(() => {
    const dur = (this.balanceSvc.value as any)?.expedition?.duration ?? {};
    const per = this.bnum(dur.max_hours_per_astro_level, 1);
    const cap = this.bnum(dur.hour_cap, 24);
    return Math.max(0, Math.min(cap, Math.floor(this.astroLevel() * per)));
  });

  setExpHours(v: number): void {
    const mx = this.maxExpHours();
    this.expHours.set(Math.max(1, Math.min(mx || 1, Math.floor(v || 1))));
  }

  shipCount(type: string): number {
    return this.selection()[type] ?? 0;
  }

  setShip(type: string, value: number, max: number): void {
    const n = Math.max(0, Math.min(max, Math.floor(value || 0)));
    this.selection.update((s) => ({ ...s, [type]: n }));
  }

  /** Auf dem aktiven Planeten verfuegbare Menge einer Ressource — Exoten liegen unter .exotic. */
  availOnPlanet(key: DispatchCargoKey): number {
    return this.calc.availOnPlanet(this.state.activePlanet(), key);
  }

  /** Exoten-Ladefelder nur zeigen, wenn der Planet welche hat (oder schon geladen). */
  showCargoField(key: DispatchCargoKey): boolean {
    if (key !== 'antimatter' && key !== 'dark_matter') return true;
    return this.availOnPlanet(key) > 0 || this.bnum(this.cargo()[key]) > 0;
  }

  /** Frachtkapazitaet eines Schiffstyps (pro Einheit) — fuer die Live-Anzeige im Picker. */
  shipCargo(type: string): number {
    return this.bnum((this.balanceSvc.value as any)?.ships?.[type]?.cargo);
  }

  /**
   * Maximal ladbare Menge EINER Ressource = min(auf dem Planeten verfuegbar,
   * freie Restkapazitaet der Flotte ohne diese Ressource).
   *
   * Behebt den Lade-Bug: zuvor wurde nur auf den Planetenbestand begrenzt (und bei
   * kurzzeitig null'er planetRes auf 0 -> Eingabe blockiert) und die Frachtkapazitaet
   * der Flotte gar nicht beruecksichtigt.
   */
  cargoCapFor(key: DispatchCargoKey): number {
    return this.calc.cargoCapFor(
      key, this.cargo(), CARGO_LOAD_KEYS, this.cargoInfo().capacity, this.state.activePlanet(),
    );
  }

  /** OGame „alles laden": Metall -> Kristall -> Deuterium -> Exoten bis die Kapazitaet voll ist. */
  fillAllCargo(): void {
    let remaining = this.cargoInfo().capacity;
    const next: Record<DispatchCargoKey, number> = {
      metal: 0, crystal: 0, deuterium: 0, antimatter: 0, dark_matter: 0,
    };
    for (const k of CARGO_LOAD_KEYS) {
      const load = Math.max(0, Math.min(this.availOnPlanet(k), remaining));
      next[k] = load;
      remaining -= load;
    }
    this.cargo.set(next);
  }

  setCargo(key: DispatchCargoKey, value: number): void {
    const max = this.cargoCapFor(key);
    const n = Math.max(0, Math.min(max, Math.floor(value || 0)));
    this.cargo.update((c) => ({ ...c, [key]: n }));
  }

  /** Frachtraum-Auslastung in % (0..100, gedeckelt) fuer den Kapazitaetsbalken. */
  protected readonly capPct = computed(() => {
    const ci = this.cargoInfo();
    return ci.capacity > 0 ? Math.min(100, (ci.used / ci.capacity) * 100) : 0;
  });

  send(): void {
    const origin = this.state.activePlanetId();
    if (!origin || !this.canSend()) {
      return;
    }
    const ships: Record<string, number> = {};
    for (const [type, n] of Object.entries(this.selection())) {
      if (n > 0) {
        ships[type] = n;
      }
    }
    // W0: Patrouillen-Modus -> eigenes System abfangen (kein Flug, kein Ziel).
    if (this.patrolMode()) {
      this.sending.set(true);
      this.api.patrolHome(origin, { ships, radius: this.patrolRadius() }).subscribe({
        next: () => {
          this.sending.set(false);
          this.notify.success('Patrouille aktiv', 'Deine Schiffe patrouillieren jetzt das eigene System.');
          void this.state.reloadActivePlanet();
          this.sent.emit();
          this.close.emit();
        },
        error: (err) => {
          this.sending.set(false);
          this.notify.warning('Patrouille fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
        },
      });
      return;
    }
    const cargo = this.showCargo()
      ? this.cargo()
      : { metal: 0, crystal: 0, deuterium: 0, antimatter: 0, dark_matter: 0 };
    const body: FleetSendRequest = {
      origin_planet_id: origin,
      target: this.effTarget(),
      mission: this.mission(),
      ships,
      cargo,
      commander_id: this.commanderId(),
      speed_pct: this.speed(),
      ability_keys: [...this.armed()],
    };
    // W0: Missions-spezifische Felder (gespiegelt aus der alten fleet.component-Logik).
    if (this.mission() === 'intercept') {
      body.radius = this.interceptRadius();
    }
    if (this.mission() === 'escort') {
      body.escort_radius = this.escortRadius();
      body.escort_fee_pct = this.escortFeePct() / 100; // Prozent -> Anteil (Backend deckelt)
    }
    if (this.mission() === 'expedition') {
      body.expedition_hours = this.expHours();
      if (this.expeditionDoctrine() !== 'neutral') {
        body.expedition_doctrine = this.expeditionDoctrine() as 'cautious' | 'bold';
      }
    }
    if (this.mission() === 'attack' && this.capturePriority() !== 'value') {
      body.capture_priority = this.capturePriority();
    }
    if (this.targetType() === 'moon') {
      body.target_type = 'moon';
    } else if (this.targetType() === 'station') {
      body.target_type = 'station';
    } else if (this.targetType() === 'mining_fleet') {
      body.target_type = 'mining_fleet';
    }
    if (this.mission() === 'trade') {
      // Angebots-Ressource faehrt als Fracht mit; der Server baut Cargo + mission_data.
      body.offer_res = this.offerRes();
      body.offer_amount = this.offerAmount();
      body.want_res = this.wantRes();
      const escorts = [...this.chosenEscorts()].filter((id) =>
        this.coveringEscorts().some((e) => e.id === id),
      );
      if (escorts.length) {
        body.escort_ids = escorts;
      }
    }
    this.sending.set(true);
    this.api
      .sendFleet(body)
      .subscribe({
        next: () => {
          this.sending.set(false);
          this.notify.success('Flotte gestartet', `Mission ${this.missionMeta(this.mission()).label} unterwegs.`);
          void this.state.reloadFleets();
          void this.state.reloadActivePlanet();
          void this.state.reloadCommanders();
          this.sent.emit();
          this.close.emit();
        },
        error: (err) => {
          this.sending.set(false);
          this.notify.warning('Start fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
        },
      });
  }

  shipMeta = (t: string) => metaFor(SHIP_META, t);
  missionMeta = (m: string) => metaFor(MISSION_META, m);
  rankMeta = (r: string) => metaFor(RANK_META, r);

  /** Asset-Pfad-Helfer fuer das Template (Glyph-Fallback via (error)="hideImg"). */
  protected readonly shipIcon = shipIcon;
  protected readonly isMk2 = isMk2;
  protected readonly missionIcon = missionIcon;
  protected readonly resourceIcon = resourceIcon;
  protected readonly navIcon = navIcon;
  protected readonly statIcon = statIcon;
  protected readonly uiIcon = uiIcon;

  /** Verbirgt ein kaputtes/fehlendes Icon-Bild, sodass der Text-/Glyph-Fallback greift. */
  hideImg(event: Event): void {
    (event.target as HTMLImageElement).style.display = 'none';
  }
}
