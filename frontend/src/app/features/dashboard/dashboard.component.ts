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

    <!-- Imperiums-Punkte (OGame-Score) — prominent, verlinkt zur Rangliste -->
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

       <div class="col">
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

        <!-- Alerts / Ereignisse -->
        <section class="card">
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

       </div>
      </div>
    } @else {
      <p class="empty-state">Lade Planetendaten…</p>
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

  constructor() {
    // Eigenen Score + Rang frisch laden (Server rechnet bei jedem Abruf neu).
    this.api.getRanking().subscribe({
      next: (r) => {
        this.me.set(r.me);
        this.totalPlayers.set(r.total);
      },
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
