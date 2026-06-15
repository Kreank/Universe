import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Observable } from 'rxjs';
import { ApiService } from '../../core/services/api.service';
import { AuthService } from '../../core/services/auth.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  AllianceInvite,
  AllianceMember,
  AllianceOverview,
  AllianceResearchContext,
  AllianceResearchNode,
  AllianceStation,
  ResourceCost,
} from '../../core/models/api.models';
import {
  ConfirmDialogComponent,
  ConfirmRequest,
} from '../../shared/components/confirm-dialog.component';
import { CostLineComponent } from '../../shared/components/cost-line.component';
import { IconTileComponent } from '../../shared/components/icon-tile.component';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';
import { TabBarComponent, TabDef } from '../../shared/components/tab-bar.component';
import { navIcon, resourceIcon, statIcon } from '../../core/models/icon-assets';

/** Lesbare Label + Glyph der vier Forschungs-Zweige (Reihenfolge = Anzeige). */
const TREE_ORDER = ['piracy', 'economy', 'trade', 'protection'] as const;
const TREE_GLYPH: Record<string, string> = {
  piracy: '🏴‍☠️',
  economy: '🏦',
  trade: '💱',
  protection: '🛡️',
};

/** Kontext-Badge eines Forschungs-Knotens (Wirkungs-Reichweite). */
const CONTEXT_LABEL: Record<AllianceResearchContext, string> = {
  coop: 'Koop',
  zone: 'Zone',
  ally: 'Verbündete',
  passive_collective: 'Passiv',
};

/**
 * Allianz-Hub: gründen/beitreten, Mitglieder & Rollen verwalten, gemeinsamen
 * Ressourcen-Pool füllen, Allianz-Forschung betreiben und Allianz-Stationen
 * (Zonen-Infrastruktur) bauen/warten. Das Backend ist autoritativ; nach jeder
 * Mutation wird der Zustand neu geladen. Fehler (422/403/404) zeigen `detail`.
 */
@Component({
  selector: 'app-alliance',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, ConfirmDialogComponent, CostLineComponent, IconTileComponent, BtnIconComponent, TabBarComponent],
  template: `
    <section class="alliance">
      <header class="page-head">
        <div>
          <h1><app-btn-icon [src]="navIcon('alliance')" glyph="🤝" [size]="18" /> Allianz</h1>
          <p class="muted small">
            Schließt euch zusammen: gemeinsamer Pool, Allianz-Forschung und Zonen-Stationen.
          </p>
        </div>
      </header>

      @if (loading()) {
        <p class="muted">Lade Allianz…</p>
      } @else if (alliance(); as a) {
        <!-- ============ MITGLIED EINER ALLIANZ ============ -->
        <div class="ally-head card">
          <div class="ally-id">
            <span class="ally-tag mono">[{{ a.tag }}]</span>
            <span class="ally-name">{{ a.name }}</span>
          </div>
          <span class="pill mono">Mitglieder {{ a.member_count }}/{{ a.max_members }}</span>
        </div>

        <app-tab-bar [tabs]="mainTabs()" [active]="tab()" (select)="tab.set($event)" />

        <!-- ---------- Übersicht ---------- -->
        @if (tab() === 'overview') {
          <div class="card">
            <div class="panel-title">Mitglieder</div>
            @for (m of a.members; track m.player_id) {
              <div class="member">
                <div class="member-main">
                  <span class="mname">{{ m.name }}</span>
                  <span class="role-badge" [class]="'role-' + m.role">{{ roleLabel(m.role) }}</span>
                  @if (m.player_id === myId()) {
                    <span class="muted small">(du)</span>
                  }
                </div>
                @if (memberControls(m); as ctl) {
                  <div class="member-act">
                    @if (ctl.promote) {
                      <button class="btn btn-ghost btn-sm" type="button" [disabled]="busy()" (click)="setRole(m, 'officer')">
                        Befördern
                      </button>
                    }
                    @if (ctl.demote) {
                      <button class="btn btn-ghost btn-sm" type="button" [disabled]="busy()" (click)="setRole(m, 'member')">
                        Degradieren
                      </button>
                    }
                    @if (ctl.transfer) {
                      <button class="btn btn-ghost btn-sm" type="button" [disabled]="busy()" (click)="askTransfer(m)">
                        Führung übergeben
                      </button>
                    }
                    @if (ctl.kick) {
                      <button class="btn btn-danger btn-sm" type="button" [disabled]="busy()" (click)="askKick(m)">
                        Entfernen
                      </button>
                    }
                  </div>
                }
              </div>
            }
          </div>

          @if (isOfficerPlus()) {
            <div class="card">
              <div class="panel-title">Spieler einladen</div>
              <div class="invite-row">
                <input
                  type="text"
                  maxlength="40"
                  [ngModel]="inviteName()"
                  (ngModelChange)="inviteName.set($event)"
                  placeholder="Anzeigename des Spielers"
                />
                <button
                  class="btn btn-primary btn-sm"
                  type="button"
                  [disabled]="busy() || !inviteName().trim()"
                  (click)="invite()"
                >
                  Einladen
                </button>
              </div>
              <p class="muted small">Offiziere und der Gründer dürfen einladen.</p>
            </div>
          }

          <div class="card">
            <div class="panel-title">Allianz</div>
            @if (isFounder()) {
              <p class="muted small">
                Als Gründer trägst du die Allianz — du kannst sie auflösen, aber nicht verlassen.
                Übergib zuerst die Führung, wenn du gehen willst.
              </p>
              <button class="btn btn-danger btn-sm" type="button" [disabled]="busy()" (click)="askDisband()">
                Allianz auflösen
              </button>
            } @else {
              <button class="btn btn-danger btn-sm" type="button" [disabled]="busy()" (click)="askLeave()">
                Allianz verlassen
              </button>
            }
          </div>
        }

        <!-- ---------- Pool ---------- -->
        @if (tab() === 'pool') {
          <div class="card">
            <div class="panel-title">Gemeinsamer Pool</div>
            <app-cost-line [cost]="poolCost(a)" />
          </div>

          <div class="card">
            <div class="panel-title">Einzahlen</div>
            @if (planets().length === 0) {
              <p class="muted small">Keine Planeten verfügbar.</p>
            } @else {
              <div class="field">
                <label>Von Planet</label>
                <select [ngModel]="depPlanet()" (ngModelChange)="depPlanet.set($event)">
                  @for (p of planets(); track p.id) {
                    <option [value]="p.id">
                      {{ p.planet_type === 'moon' ? '🌑 ' : '' }}{{ p.name }} [{{ p.galaxy }}:{{ p.system }}:{{ p.position }}]
                    </option>
                  }
                </select>
              </div>
              <div class="dep-grid">
                <div class="field">
                  <label><app-btn-icon [src]="resourceIcon('metal')" glyph="⛏️" [size]="14" /> Metall</label>
                  <input type="number" min="0" [ngModel]="depMetal()" (ngModelChange)="depMetal.set(+$event || 0)" />
                </div>
                <div class="field">
                  <label><app-btn-icon [src]="resourceIcon('crystal')" glyph="💎" [size]="14" /> Kristall</label>
                  <input type="number" min="0" [ngModel]="depCrystal()" (ngModelChange)="depCrystal.set(+$event || 0)" />
                </div>
                <div class="field">
                  <label><app-btn-icon [src]="resourceIcon('deuterium')" glyph="🛢️" [size]="14" /> Deuterium</label>
                  <input type="number" min="0" [ngModel]="depDeut()" (ngModelChange)="depDeut.set(+$event || 0)" />
                </div>
              </div>
              <button
                class="btn btn-primary btn-sm"
                type="button"
                [disabled]="busy() || !depPlanet() || depTotal() <= 0"
                (click)="deposit()"
              >
                In den Pool einzahlen
              </button>
            }
          </div>
        }

        <!-- ---------- Forschung ---------- -->
        @if (tab() === 'research') {
          <app-tab-bar [tabs]="treeTabs(a)" [active]="treeTab()" (select)="treeTab.set($event)" />
          @if (activeTree(a); as tree) {
            <div class="card">
              <div class="panel-title tree-title">
                <img class="tree-emblem" [src]="treeEmblem()" alt="" loading="lazy" />
                <span>{{ tree.label }}</span>
              </div>
              @for (n of treeNodes(tree); track n.key) {
                <div class="node">
                  <div class="node-head">
                    <app-icon-tile [src]="nodeIcon(n.key)" [glyph]="treeGlyph()" [size]="40" />
                    <span class="node-name">{{ n.node.lever }}</span>
                    <span class="ctx-badge" [class]="'ctx-' + n.node.context">{{ ctxLabel(n.node.context) }}</span>
                  </div>
                  <p class="node-effect small muted">{{ n.node.effect }}</p>
                  <div class="node-foot">
                    <span class="lvl mono">
                      Stufe {{ n.node.level }}@if (!n.node.repeatable) {/{{ n.node.max_level }}}
                    </span>
                    @if (n.node.next_cost; as cost) {
                      <app-cost-line [cost]="cost" [available]="poolAvail(a)" />
                    } @else {
                      <span class="muted small">Max. erreicht</span>
                    }
                    @if (isOfficerPlus()) {
                      <button
                        class="btn btn-trade btn-sm"
                        type="button"
                        [disabled]="busy() || !n.node.next_cost || !canAfford(n.node.next_cost, a)"
                        (click)="research(n.key)"
                      >
                        Erforschen
                      </button>
                    }
                  </div>
                </div>
              }
            </div>
          }
          @if (isFounder()) {
            <div class="card">
              <div class="panel-title">Forschung zurücksetzen</div>
              <p class="muted small">
                Setzt alle Allianz-Forschungen auf Stufe 0 zurück. Achtung: voller Sink — es gibt
                <strong>keine Rückerstattung</strong> der investierten Ressourcen.
              </p>
              <button class="btn btn-danger btn-sm" type="button" [disabled]="busy()" (click)="askResetResearch()">
                Forschung zurücksetzen
              </button>
            </div>
          }
        }

        <!-- ---------- Station ---------- -->
        @if (tab() === 'station') {
          <div class="card">
            <div class="panel-title">Allianz-Stationen ({{ a.stations.length }}/{{ a.station_config.max_per_alliance }})</div>
            @if (a.stations.length === 0) {
              <p class="muted small">Noch keine Station errichtet.</p>
            }
            @for (s of a.stations; track s.id) {
              <div class="station">
                <img class="station-art" [src]="stationArt" alt="" loading="lazy" />
                <div class="station-body">
                <div class="station-main">
                  <span class="mono">[{{ s.coords }}]</span>
                  <span class="status-badge" [class]="'st-' + s.status">{{ stationStatus(s.status) }}</span>
                </div>
                <div class="station-meta small muted">
                  Zonen-Radius {{ zoneRadius(a, s) }} Sys (Stufe {{ s.radius_level }}) ·
                  <app-btn-icon [src]="statIcon('fuel')" glyph="⛽" [size]="14" /> {{ s.fuel }} Deut · <app-btn-icon [src]="statIcon('hull')" glyph="❤" [size]="14" /> {{ s.hp }} HP
                </div>
                @if (isOfficerPlus() && s.status !== 'destroyed') {
                  <div class="station-act">
                    <span class="refuel">
                      <input
                        class="mini"
                        type="number"
                        min="0"
                        [ngModel]="refuelAmt()[s.id] || 0"
                        (ngModelChange)="setRefuel(s.id, +$event || 0)"
                        placeholder="Deut"
                      />
                      <button class="btn btn-ghost btn-sm" type="button" [disabled]="busy() || (refuelAmt()[s.id] || 0) <= 0" (click)="refuel(s)">
                        Betanken
                      </button>
                    </span>
                    <button
                      class="btn btn-ghost btn-sm"
                      type="button"
                      [disabled]="busy() || s.radius_level >= a.station_config.max_radius"
                      (click)="upgrade(s)"
                    >
                      Radius ausbauen
                    </button>
                  </div>
                }
                </div>
              </div>
            }
            <p class="muted small">
              Unterhalt: {{ a.station_config.upkeep_deuterium_per_tick }} Deut/Tick aus dem Treibstoff-Vorrat.
              Basis-Radius {{ a.station_config.base_radius }}, max. {{ a.station_config.max_radius }} Ausbaustufen.
            </p>
          </div>

          @if (isOfficerPlus() && a.stations.length < a.station_config.max_per_alliance) {
            <div class="card">
              <div class="panel-title">Station errichten</div>
              <div class="build-preview">
                <img class="station-art" [src]="stationArt" alt="" loading="lazy" />
                <p class="muted small">
                  Eine Allianz-Station spannt eine Einflusszone über die umliegenden Systeme.
                </p>
              </div>
              <div class="coord-row">
                <input class="mini" type="number" min="1" [ngModel]="stG()" (ngModelChange)="stG.set(+$event || 1)" placeholder="Gal" />
                <span class="sep">:</span>
                <input class="mini" type="number" min="1" [ngModel]="stS()" (ngModelChange)="stS.set(+$event || 1)" placeholder="Sys" />
                <span class="sep">:</span>
                <input class="mini" type="number" min="1" [ngModel]="stP()" (ngModelChange)="stP.set(+$event || 1)" placeholder="Pos" />
                <button class="btn btn-primary btn-sm" type="button" [disabled]="busy()" (click)="buildStation()">
                  Errichten
                </button>
              </div>
              <p class="muted small">Baukosten aus dem Allianz-Pool:</p>
              <app-cost-line [cost]="a.station_config.build_cost" [available]="poolAvail(a)" />
            </div>
          }
        }
      } @else {
        <!-- ============ KEINE ALLIANZ ============ -->
        <div class="card">
          <div class="panel-title">Allianz gründen</div>
          <div class="field">
            <label>Name (3–40 Zeichen)</label>
            <input
              type="text"
              maxlength="40"
              [ngModel]="newName()"
              (ngModelChange)="newName.set($event)"
              placeholder="z. B. Galaktische Föderation"
            />
          </div>
          <div class="field">
            <label>Tag (2–6 Zeichen)</label>
            <input
              type="text"
              maxlength="6"
              [ngModel]="newTag()"
              (ngModelChange)="newTag.set($event)"
              placeholder="z. B. GFED"
            />
          </div>
          @if (createCost(); as cc) {
            <p class="muted small">
              Gründungskosten (vom Heimatplaneten):
            </p>
            <app-cost-line [cost]="cc" />
          }
          @if (maxMembers(); as mm) {
            <p class="muted small">Platz für bis zu {{ mm }} Mitglieder.</p>
          }
          <button
            class="btn btn-primary btn-sm"
            type="button"
            [disabled]="busy() || !canCreate()"
            (click)="create()"
          >
            Gründen
          </button>
        </div>

        <div class="card">
          <div class="panel-title">Einladungen ({{ invites().length }})</div>
          @if (invites().length === 0) {
            <p class="muted small">Aktuell liegen keine Einladungen vor.</p>
          }
          @for (inv of invites(); track inv.id) {
            <div class="member">
              <div class="member-main">
                <span class="ally-tag mono">[{{ inv.tag }}]</span>
                <span class="mname">{{ inv.name }}</span>
              </div>
              <div class="member-act">
                <button class="btn btn-primary btn-sm" type="button" [disabled]="busy()" (click)="accept(inv)">
                  Beitreten
                </button>
                <button class="btn btn-ghost btn-sm" type="button" [disabled]="busy()" (click)="decline(inv)">
                  Ablehnen
                </button>
              </div>
            </div>
          }
        </div>
      }
    </section>

    @if (confirmReq(); as c) {
      <app-confirm-dialog
        [title]="c.title"
        [message]="c.message"
        [confirmLabel]="c.confirmLabel"
        [pending]="busy()"
        (confirm)="runConfirm()"
        (dismiss)="confirmReq.set(null)"
      />
    }
  `,
  styles: [
    `
      .alliance {
        max-width: 880px;
        margin: 0 auto;
        padding-bottom: var(--sp-8);
        display: flex;
        flex-direction: column;
        gap: var(--sp-4);
      }
      .page-head h1 {
        margin: 0 0 var(--sp-1);
      }
      .small {
        font-size: var(--fs-sm);
      }
      .pill {
        font-size: var(--fs-xs);
        color: var(--text);
        background: rgba(47, 227, 210, 0.12);
        border: 1px solid var(--border);
        padding: 2px var(--sp-2);
        border-radius: var(--r-pill);
      }

      .ally-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: var(--sp-3);
      }
      .ally-id {
        display: flex;
        align-items: baseline;
        gap: var(--sp-2);
        flex-wrap: wrap;
      }
      .ally-tag {
        color: var(--accent);
        font-weight: 600;
      }
      .ally-name {
        font-family: var(--font-display);
        font-weight: 600;
        font-size: var(--fs-lg);
        color: var(--text);
      }

      /* Mitglieder- / Einladungs-Zeilen */
      .member {
        display: flex;
        align-items: center;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: var(--sp-2);
        border-top: 1px solid var(--border);
        padding: var(--sp-3) 0;
      }
      .member:first-of-type {
        border-top: none;
      }
      .member-main {
        display: flex;
        align-items: center;
        gap: var(--sp-2);
        flex-wrap: wrap;
      }
      .mname {
        font-family: var(--font-display);
        font-weight: 600;
        color: var(--text);
      }
      .member-act {
        display: flex;
        flex-wrap: wrap;
        gap: var(--sp-2);
      }
      .role-badge {
        font-size: var(--fs-xs);
        font-weight: 600;
        padding: 1px var(--sp-2);
        border-radius: var(--r-pill);
        color: var(--text-dim);
        background: rgba(255, 255, 255, 0.06);
      }
      .role-founder {
        color: var(--bg-deep);
        background: var(--accent);
      }
      .role-officer {
        color: var(--accent);
        background: rgba(47, 227, 210, 0.12);
      }

      .invite-row {
        display: flex;
        gap: var(--sp-2);
        flex-wrap: wrap;
        align-items: center;
      }
      .invite-row input {
        flex: 1 1 220px;
      }

      .dep-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(140px, 1fr));
        gap: var(--sp-3);
        margin-bottom: var(--sp-3);
      }

      /* Forschungs-Knoten */
      .node {
        border-top: 1px solid var(--border);
        padding: var(--sp-3) 0;
      }
      .node:first-of-type {
        border-top: none;
      }
      .node-head {
        display: flex;
        align-items: center;
        gap: var(--sp-2);
        flex-wrap: wrap;
      }
      .node-name {
        font-family: var(--font-display);
        font-weight: 600;
        color: var(--text);
      }
      .node-effect {
        margin: var(--sp-1) 0;
      }
      .node-foot {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: var(--sp-3);
      }
      .lvl {
        color: var(--text-dim);
      }
      .ctx-badge {
        font-size: var(--fs-xs);
        font-weight: 600;
        padding: 1px var(--sp-2);
        border-radius: var(--r-pill);
        color: var(--text-dim);
        background: rgba(255, 255, 255, 0.06);
        border: 1px solid var(--border);
      }
      .ctx-coop {
        color: var(--accent);
      }
      .ctx-zone {
        color: var(--warn);
      }

      /* Forschungs-Zweig-Emblem im Karten-Titel */
      .tree-title {
        display: flex;
        align-items: center;
        gap: var(--sp-2);
      }
      .tree-emblem {
        width: 40px;
        height: 40px;
        object-fit: contain;
        border-radius: 8px;
        filter: drop-shadow(0 1px 4px rgba(0, 0, 0, 0.5));
      }

      /* Stationen */
      .station {
        display: flex;
        align-items: flex-start;
        gap: var(--sp-3);
        border-top: 1px solid var(--border);
        padding: var(--sp-3) 0;
      }
      .station:first-of-type {
        border-top: none;
      }
      .station-body {
        flex: 1 1 auto;
        min-width: 0;
      }
      .station-art {
        width: 72px;
        height: 72px;
        object-fit: contain;
        flex: 0 0 auto;
        border-radius: 10px;
        background: linear-gradient(145deg, rgba(46, 230, 214, 0.12), rgba(13, 22, 41, 0.9));
        border: 1px solid rgba(46, 230, 214, 0.28);
        box-shadow: inset 0 0 14px rgba(46, 230, 214, 0.1);
      }
      .build-preview {
        display: flex;
        align-items: center;
        gap: var(--sp-3);
        margin-bottom: var(--sp-3);
      }
      .build-preview .station-art {
        width: 88px;
        height: 88px;
      }
      .build-preview p {
        margin: 0;
      }
      .station-main {
        display: flex;
        align-items: center;
        gap: var(--sp-2);
        flex-wrap: wrap;
      }
      .station-meta {
        margin: var(--sp-1) 0;
      }
      .station-act {
        display: flex;
        flex-wrap: wrap;
        align-items: center;
        gap: var(--sp-3);
        margin-top: var(--sp-1);
      }
      .refuel {
        display: inline-flex;
        align-items: center;
        gap: var(--sp-1);
      }
      .status-badge {
        font-size: var(--fs-xs);
        font-weight: 600;
        padding: 1px var(--sp-2);
        border-radius: var(--r-pill);
      }
      .st-active {
        color: var(--bg-deep);
        background: var(--accent);
      }
      .st-inactive {
        color: var(--warn);
        background: rgba(255, 180, 60, 0.12);
      }
      .st-destroyed {
        color: var(--danger);
        background: rgba(255, 77, 125, 0.12);
      }

      .coord-row {
        display: flex;
        align-items: center;
        gap: var(--sp-1);
        flex-wrap: wrap;
        margin-bottom: var(--sp-2);
      }
      .mini {
        width: 70px;
      }
      .sep {
        color: var(--text-dim);
      }
    `,
  ],
})
export class AllianceComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly auth = inject(AuthService);
  private readonly state = inject(GameStateService);
  private readonly notify = inject(NotificationService);

  protected readonly planets = this.state.planets;

  protected readonly navIcon = navIcon;
  protected readonly resourceIcon = resourceIcon;
  protected readonly statIcon = statIcon;

  protected readonly loading = signal(true);
  protected readonly busy = signal(false);
  protected readonly alliance = signal<AllianceOverview | null>(null);
  protected readonly invites = signal<AllianceInvite[]>([]);
  protected readonly createCost = signal<ResourceCost | null>(null);
  protected readonly maxMembers = signal<number | null>(null);
  protected readonly confirmReq = signal<ConfirmRequest | null>(null);

  // Reiter
  protected readonly tab = signal<string>('overview');
  protected readonly treeTab = signal<string>('piracy');

  // Gründungs-Formular
  protected readonly newName = signal('');
  protected readonly newTag = signal('');

  // Einladung
  protected readonly inviteName = signal('');

  // Einzahlen
  protected readonly depPlanet = signal('');
  protected readonly depMetal = signal(0);
  protected readonly depCrystal = signal(0);
  protected readonly depDeut = signal(0);

  // Station bauen / betanken
  protected readonly stG = signal(1);
  protected readonly stS = signal(1);
  protected readonly stP = signal(1);
  protected readonly refuelAmt = signal<Record<string, number>>({});

  protected readonly myId = computed(() => this.auth.player()?.id ?? null);
  protected readonly isFounder = computed(() => this.alliance()?.my_role === 'founder');
  protected readonly isOfficerPlus = computed(() => {
    const r = this.alliance()?.my_role;
    return r === 'founder' || r === 'officer';
  });

  protected readonly mainTabs = computed<TabDef[]>(() => [
    { key: 'overview', label: 'Übersicht', glyph: '👥' },
    { key: 'pool', label: 'Pool', glyph: '🏦' },
    { key: 'research', label: 'Forschung', glyph: '🔬' },
    { key: 'station', label: 'Station', glyph: '🛰' },
  ]);

  protected readonly depTotal = computed(() => this.depMetal() + this.depCrystal() + this.depDeut());

  protected readonly canCreate = computed(() => {
    const n = this.newName().trim();
    const t = this.newTag().trim();
    return n.length >= 3 && n.length <= 40 && t.length >= 2 && t.length <= 6;
  });

  ngOnInit(): void {
    this.reload();
  }

  private reload(): void {
    this.loading.set(true);
    this.api.getAlliance().subscribe({
      next: (res) => {
        this.alliance.set(res.alliance);
        this.invites.set(res.invites ?? []);
        this.createCost.set(res.create_cost ?? null);
        this.maxMembers.set(res.max_members ?? null);
        if (res.alliance && !this.depPlanet()) {
          const home = this.planets().find((p) => p.is_homeworld) ?? this.planets()[0];
          if (home) {
            this.depPlanet.set(home.id);
          }
        }
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.warning('Laden fehlgeschlagen', err?.error?.detail ?? 'Allianz nicht erreichbar.');
      },
    });
  }

  /** Generischer Mutations-Helfer: setzt busy, lädt bei Erfolg neu, zeigt detail bei Fehler. */
  private run(obs: Observable<unknown>, successTitle: string, successMsg: string): void {
    if (this.busy()) {
      return;
    }
    this.busy.set(true);
    obs.subscribe({
      next: () => {
        this.busy.set(false);
        this.notify.success(successTitle, successMsg);
        this.reload();
      },
      error: (err: { error?: { detail?: string } }) => {
        this.busy.set(false);
        this.notify.warning('Fehlgeschlagen', err?.error?.detail ?? 'Bitte Eingaben prüfen.');
      },
    });
  }

  // --- Anzeige-Helfer ---

  roleLabel(role: string): string {
    return role === 'founder' ? 'Gründer' : role === 'officer' ? 'Offizier' : 'Mitglied';
  }

  ctxLabel(ctx: AllianceResearchContext): string {
    return CONTEXT_LABEL[ctx] ?? ctx;
  }

  /** Stations-Artwork (Karten + Bau-Vorschau). */
  protected readonly stationArt = 'assets/img/alliance/alliance_station.png';

  /** Emblem des aktiven Forschungs-Zweigs (assets/img/tech/alliance_<tree>.png). */
  treeEmblem(): string {
    return `assets/img/tech/alliance_${this.treeTab()}.png`;
  }

  /** Emoji-Glyph des aktiven Zweigs (Fallback fuer fehlende Knoten-Icons). */
  treeGlyph(): string {
    return TREE_GLYPH[this.treeTab()] ?? '🔬';
  }

  /** Knoten-Icon eines Forschungs-Knotens (assets/img/tech/alliance_<key>.png). */
  nodeIcon(key: string): string {
    return `assets/img/tech/alliance_${key}.png`;
  }

  stationStatus(status: string): string {
    return status === 'active' ? 'Aktiv' : status === 'inactive' ? 'Inaktiv' : 'Zerstört';
  }

  poolCost(a: AllianceOverview): ResourceCost {
    return { metal: a.pool.metal, crystal: a.pool.crystal, deuterium: a.pool.deuterium };
  }

  poolAvail(a: AllianceOverview): Record<string, number> {
    return { metal: a.pool.metal, crystal: a.pool.crystal, deuterium: a.pool.deuterium };
  }

  canAfford(cost: ResourceCost, a: AllianceOverview): boolean {
    return (
      a.pool.metal >= (cost.metal ?? 0) &&
      a.pool.crystal >= (cost.crystal ?? 0) &&
      a.pool.deuterium >= (cost.deuterium ?? 0)
    );
  }

  zoneRadius(a: AllianceOverview, s: AllianceStation): number {
    return a.station_config.base_radius + s.radius_level;
  }

  treeTabs(a: AllianceOverview): TabDef[] {
    return TREE_ORDER.filter((k) => k in a.research_catalog).map((k) => ({
      key: k,
      label: a.research_catalog[k].label,
      glyph: TREE_GLYPH[k],
    }));
  }

  activeTree(a: AllianceOverview) {
    return a.research_catalog[this.treeTab()] ?? a.research_catalog[TREE_ORDER[0]] ?? null;
  }

  treeNodes(tree: { nodes: Record<string, AllianceResearchNode> }): { key: string; node: AllianceResearchNode }[] {
    return Object.entries(tree.nodes).map(([key, node]) => ({ key, node }));
  }

  /** Welche Mitglieder-Aktionen für `m` sichtbar sind (rollenabhängig). */
  memberControls(m: AllianceMember): { promote: boolean; demote: boolean; transfer: boolean; kick: boolean } | null {
    const isSelf = m.player_id === this.myId();
    const founder = this.isFounder();
    const officer = this.isOfficerPlus();
    if (isSelf || m.role === 'founder') {
      return null;
    }
    const ctl = {
      promote: founder && m.role === 'member',
      demote: founder && m.role === 'officer',
      transfer: founder,
      // Offiziere dürfen nur einfache Mitglieder entfernen; der Gründer alle Nicht-Gründer.
      kick: founder || (officer && m.role === 'member'),
    };
    return ctl.promote || ctl.demote || ctl.transfer || ctl.kick ? ctl : null;
  }

  // --- Bestätigungen ---

  runConfirm(): void {
    const c = this.confirmReq();
    this.confirmReq.set(null);
    c?.action();
  }

  // --- Keine Allianz ---

  create(): void {
    if (!this.canCreate()) {
      return;
    }
    this.run(
      this.api.createAlliance({ name: this.newName().trim(), tag: this.newTag().trim() }),
      'Gegründet',
      `Allianz „${this.newName().trim()}" erstellt.`,
    );
  }

  accept(inv: AllianceInvite): void {
    this.run(this.api.acceptInvite(inv.id), 'Beigetreten', `Du bist jetzt Mitglied von [${inv.tag}].`);
  }

  decline(inv: AllianceInvite): void {
    this.run(this.api.declineInvite(inv.id), 'Abgelehnt', `Einladung von [${inv.tag}] abgelehnt.`);
  }

  // --- Übersicht ---

  invite(): void {
    const name = this.inviteName().trim();
    if (!name) {
      return;
    }
    this.busy.set(true);
    this.api.inviteToAlliance({ name }).subscribe({
      next: () => {
        this.busy.set(false);
        this.inviteName.set('');
        this.notify.success('Eingeladen', `Einladung an „${name}" verschickt.`);
        this.reload();
      },
      error: (err) => {
        this.busy.set(false);
        this.notify.warning('Einladung fehlgeschlagen', err?.error?.detail ?? 'Spieler nicht gefunden?');
      },
    });
  }

  setRole(m: AllianceMember, role: 'member' | 'officer'): void {
    this.run(
      this.api.setMemberRole(m.player_id, role),
      'Rolle geändert',
      `${m.name} ist jetzt ${this.roleLabel(role)}.`,
    );
  }

  askTransfer(m: AllianceMember): void {
    this.confirmReq.set({
      title: 'Führung übergeben?',
      message: `Du übergibst die Gründer-Rolle dauerhaft an ${m.name}. Du wirst danach Offizier.`,
      confirmLabel: 'Übergeben',
      action: () =>
        this.run(this.api.transferLeadership(m.player_id), 'Führung übergeben', `${m.name} führt nun die Allianz.`),
    });
  }

  askKick(m: AllianceMember): void {
    this.confirmReq.set({
      title: 'Mitglied entfernen?',
      message: `${m.name} wird aus der Allianz entfernt.`,
      confirmLabel: 'Entfernen',
      action: () => this.run(this.api.kickMember(m.player_id), 'Entfernt', `${m.name} wurde entfernt.`),
    });
  }

  askDisband(): void {
    this.confirmReq.set({
      title: 'Allianz auflösen?',
      message: 'Die Allianz wird unwiderruflich aufgelöst. Pool, Forschung und Stationen gehen verloren.',
      confirmLabel: 'Auflösen',
      action: () => this.run(this.api.disbandAlliance(), 'Aufgelöst', 'Die Allianz wurde aufgelöst.'),
    });
  }

  askLeave(): void {
    this.confirmReq.set({
      title: 'Allianz verlassen?',
      message: 'Du verlässt die Allianz. Eingezahlte Ressourcen verbleiben im Pool.',
      confirmLabel: 'Verlassen',
      action: () => this.run(this.api.leaveAlliance(), 'Verlassen', 'Du hast die Allianz verlassen.'),
    });
  }

  // --- Pool ---

  deposit(): void {
    if (!this.depPlanet() || this.depTotal() <= 0) {
      return;
    }
    this.busy.set(true);
    this.api
      .depositToAlliance({
        planet_id: this.depPlanet(),
        metal: this.depMetal(),
        crystal: this.depCrystal(),
        deuterium: this.depDeut(),
      })
      .subscribe({
        next: () => {
          this.busy.set(false);
          this.depMetal.set(0);
          this.depCrystal.set(0);
          this.depDeut.set(0);
          this.notify.success('Eingezahlt', 'Ressourcen wurden in den Pool übertragen.');
          this.reload();
          void this.state.reloadActivePlanet();
        },
        error: (err) => {
          this.busy.set(false);
          this.notify.warning('Einzahlen fehlgeschlagen', err?.error?.detail ?? 'Bitte Eingaben prüfen.');
        },
      });
  }

  // --- Forschung ---

  research(node: string): void {
    this.run(this.api.researchAlliance(this.treeTab(), node), 'Erforscht', 'Allianz-Forschung verbessert.');
  }

  askResetResearch(): void {
    this.confirmReq.set({
      title: 'Forschung zurücksetzen?',
      message:
        'Alle Allianz-Forschungen fallen auf Stufe 0. Es gibt KEINE Rückerstattung — die investierten Ressourcen sind endgültig verloren.',
      confirmLabel: 'Zurücksetzen',
      action: () => this.run(this.api.resetAllianceResearch(), 'Zurückgesetzt', 'Allianz-Forschung wurde zurückgesetzt.'),
    });
  }

  // --- Station ---

  setRefuel(id: string, amount: number): void {
    this.refuelAmt.update((m) => ({ ...m, [id]: amount }));
  }

  refuel(s: AllianceStation): void {
    const amt = this.refuelAmt()[s.id] || 0;
    if (amt <= 0) {
      return;
    }
    this.busy.set(true);
    this.api.refuelStation(s.id, amt).subscribe({
      next: () => {
        this.busy.set(false);
        this.setRefuel(s.id, 0);
        this.notify.success('Betankt', `Station [${s.coords}] erhielt ${amt} Deuterium.`);
        this.reload();
      },
      error: (err) => {
        this.busy.set(false);
        this.notify.warning('Betanken fehlgeschlagen', err?.error?.detail ?? 'Nicht genug im Pool?');
      },
    });
  }

  upgrade(s: AllianceStation): void {
    this.run(this.api.upgradeStation(s.id), 'Ausgebaut', `Zonen-Radius von [${s.coords}] erweitert.`);
  }

  buildStation(): void {
    this.run(
      this.api.buildAllianceStation({ galaxy: this.stG(), system: this.stS(), position: this.stP() }),
      'Errichtet',
      `Station bei [${this.stG()}:${this.stS()}:${this.stP()}] gebaut.`,
    );
  }
}
