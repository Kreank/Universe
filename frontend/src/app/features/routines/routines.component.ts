import {
  ChangeDetectionStrategy,
  Component,
  OnInit,
  computed,
  inject,
  signal,
} from '@angular/core';
import { FormsModule } from '@angular/forms';
import { ApiService } from '../../core/services/api.service';
import { BalanceService } from '../../core/services/balance.service';
import { GameStateService } from '../../core/services/game-state.service';
import { NotificationService } from '../../core/services/notification.service';
import {
  Routine,
  RoutineLimits,
  RoutinePauseReason,
  RoutineStatus,
  RoutineWaypoint,
  RoutineWriteRequest,
} from '../../core/models/api.models';
import { SHIP_META, metaFor } from '../../core/models/display';
import { shipIcon } from '../../core/models/icon-assets';
import {
  ConfirmDialogComponent,
  ConfirmRequest,
} from '../../shared/components/confirm-dialog.component';
import { BtnIconComponent } from '../../shared/components/btn-icon.component';

/** Schiffstypen, die fuer Farm-Routen sinnvoll sind (Reihenfolge = Anzeige). */
const ROUTINE_SHIP_TYPES = ['miner', 'recycler', 'large_cargo', 'small_cargo'];

/** Lesbare deutsche Texte fuer Pausen-Gruende. */
const PAUSE_REASON_LABEL: Record<RoutinePauseReason, string> = {
  no_fuel: 'Kein Treibstoff',
  no_ships: 'Keine Schiffe verfügbar',
  no_slot: 'Kein freier Flottenslot',
  no_target: 'Kein gültiges Ziel',
  fleet_lost: 'Flotte verloren',
};

/** Editor-Zustand fuer das Routen-Design (Neu oder Bearbeiten). */
interface RoutineDraft {
  id: string | null;
  name: string;
  homePlanetId: string;
  waypoints: RoutineWaypoint[];
  ships: Record<string, number>;
}

/**
 * Routinen-Hub: automatisierte Farm-Routen anlegen, bearbeiten, an/abschalten und loeschen.
 * Der Server fliegt die Routen autoritativ; diese Seite ist reines Management
 * (Status/Cursor kommen vom Backend). Validierung (422) wird inline gezeigt.
 */
@Component({
  selector: 'app-routines',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, ConfirmDialogComponent, BtnIconComponent],
  template: `
    <section class="routines">
      <header class="page-head">
        <div>
          <h1>🛰 Routinen</h1>
          <p class="muted small">
            Automatisierte Farm-Routen: deine Flotte klappert die Wegpunkte selbstständig ab.
          </p>
        </div>
        @if (limits(); as l) {
          <div class="limits">
            <span class="pill mono">Routinen {{ l.used_routines }}/{{ l.max_routines }}</span>
            <span class="pill mono">max. Felder pro Route: {{ l.max_fields_per_route }}</span>
          </div>
        }
      </header>

      <div class="toolbar">
        <button
          class="btn btn-primary btn-sm"
          type="button"
          [disabled]="!canCreate()"
          (click)="openCreate()"
        >
          + Routine anlegen
        </button>
        @if (!canCreate() && limits()) {
          <span class="hint">
            Routen-Limit erreicht — erforsche „Logistik-Netz", um mehr Routinen zu betreiben.
          </span>
        }
      </div>

      @if (loading()) {
        <p class="muted">Lade Routinen…</p>
      } @else if (routines().length === 0) {
        <div class="card empty">
          <p class="muted">Noch keine Routinen. Lege deine erste automatisierte Farm-Route an.</p>
        </div>
      }

      @for (r of routines(); track r.id) {
        <div class="card routine">
          <div class="routine-head">
            <div class="routine-title">
              <span class="rname">{{ r.name }}</span>
              <span class="status" [class]="'status-' + r.status">{{ statusLabel(r) }}</span>
            </div>
            <label class="toggle small" title="Routine an- oder abschalten">
              <input
                type="checkbox"
                [ngModel]="r.enabled"
                [disabled]="busyId() === r.id"
                (ngModelChange)="toggleEnabled(r, $event)"
              />
              <span>{{ r.enabled ? 'Aktiv' : 'Pausiert' }}</span>
            </label>
          </div>

          <div class="routine-meta small muted">
            Heimatbasis: {{ planetName(r.home_planet_id) }}
          </div>

          <div class="waypoints">
            @for (w of r.waypoints; track $index) {
              <span class="wp" [class.current]="$index === r.cursor && r.status !== 'idle'">
                {{ w.galaxy }}:{{ w.system }}:{{ w.position }}
              </span>
              @if (!$last) {
                <span class="arrow">→</span>
              }
            }
          </div>

          <div class="ships small">
            @for (s of shipEntries(r.ships); track s.type) {
              <span class="ship-chip">
                <app-btn-icon [src]="shipIcon(s.type)" [glyph]="shipGlyph(s.type)" />
                {{ shipLabel(s.type) }} ×{{ s.count }}
              </span>
            } @empty {
              <span class="muted">Keine Schiffe zugewiesen</span>
            }
          </div>

          <div class="routine-act">
            <button class="btn btn-ghost btn-sm" type="button" (click)="openEdit(r)">
              Bearbeiten
            </button>
            <button class="btn btn-danger btn-sm" type="button" (click)="askDelete(r)">
              Löschen
            </button>
          </div>
        </div>
      }
    </section>

    @if (draft(); as d) {
      <div class="backdrop" (click)="closeEditor()">
        <div class="popup glass designer" (click)="$event.stopPropagation()">
          <h2 class="title">{{ d.id ? 'Routine bearbeiten' : 'Neue Routine' }}</h2>

          <div class="field">
            <label>Name</label>
            <input
              type="text"
              maxlength="60"
              [ngModel]="d.name"
              (ngModelChange)="patchDraft({ name: $event })"
              placeholder="z. B. Asteroiden-Runde Nord"
            />
          </div>

          <div class="field">
            <label>Heimatbasis</label>
            <select [ngModel]="d.homePlanetId" (ngModelChange)="patchDraft({ homePlanetId: $event })">
              @for (p of planets(); track p.id) {
                <option [value]="p.id">
                  {{ p.planet_type === 'moon' ? '🌑 ' : '' }}{{ p.name }} [{{ p.galaxy }}:{{ p.system }}:{{ p.position }}]
                </option>
              }
            </select>
          </div>

          <!-- Wegpunkte -->
          <div class="block">
            <div class="block-title">
              Wegpunkte
              <span class="muted small">({{ d.waypoints.length }}/{{ maxFields() }})</span>
            </div>

            @for (w of d.waypoints; track $index) {
              <div class="wp-row">
                <span class="wp-no mono">{{ $index + 1 }}.</span>
                <span class="mono">{{ w.galaxy }}:{{ w.system }}:{{ w.position }}</span>
                <span class="spacer"></span>
                <button
                  class="btn btn-ghost btn-sm"
                  type="button"
                  [disabled]="$index === 0"
                  (click)="moveWaypoint($index, -1)"
                  title="Nach oben"
                >
                  ↑
                </button>
                <button
                  class="btn btn-ghost btn-sm"
                  type="button"
                  [disabled]="$index === d.waypoints.length - 1"
                  (click)="moveWaypoint($index, 1)"
                  title="Nach unten"
                >
                  ↓
                </button>
                <button class="btn btn-ghost btn-sm" type="button" (click)="removeWaypoint($index)" title="Entfernen">
                  ✕
                </button>
              </div>
            }

            @if (d.waypoints.length < maxFields()) {
              <div class="wp-add">
                <input class="mini" type="number" min="1" [ngModel]="newG()" (ngModelChange)="newG.set(+$event || 1)" placeholder="Gal" />
                <span class="sep">:</span>
                <input class="mini" type="number" min="1" [ngModel]="newS()" (ngModelChange)="newS.set(+$event || 1)" placeholder="Sys" />
                <span class="sep">:</span>
                <input class="mini" type="number" min="1" [ngModel]="newP()" (ngModelChange)="newP.set(+$event || 1)" placeholder="Pos" />
                <button class="btn btn-ghost btn-sm" type="button" (click)="addWaypoint()">
                  Feld hinzufügen
                </button>
              </div>
            } @else {
              <p class="hint">
                Maximale Felderzahl erreicht — erforsche „Routen-Planung", um längere Routen zu fliegen.
              </p>
            }
          </div>

          <!-- Schiffe -->
          <div class="block">
            <div class="block-title">Schiffe</div>
            <p class="muted small">
              Asteroidenfelder brauchen Bergbauschiffe, Trümmerfelder brauchen Recycler; Transporter
              erhöhen den Laderaum.
            </p>
            <div class="ship-grid">
              @for (t of shipTypes(); track t) {
                <div class="ship-field">
                  <label>
                    <app-btn-icon [src]="shipIcon(t)" [glyph]="shipGlyph(t)" />
                    {{ shipLabel(t) }}
                  </label>
                  <input
                    type="number"
                    min="0"
                    [ngModel]="shipCount(d, t)"
                    (ngModelChange)="setShip(t, +$event || 0)"
                  />
                </div>
              }
            </div>
          </div>

          @if (formError(); as err) {
            <p class="form-error">{{ err }}</p>
          }

          <div class="actions">
            <button class="btn btn-ghost" type="button" (click)="closeEditor()">Abbrechen</button>
            <button class="btn btn-primary" type="button" [disabled]="saving()" (click)="save()">
              {{ saving() ? 'Speichere…' : 'Speichern' }}
            </button>
          </div>
        </div>
      </div>
    }

    @if (confirmReq(); as c) {
      <app-confirm-dialog
        [title]="c.title"
        [message]="c.message"
        [confirmLabel]="c.confirmLabel"
        [pending]="busyId() !== null"
        (confirm)="runConfirm()"
        (dismiss)="confirmReq.set(null)"
      />
    }
  `,
  styles: [
    `
      .routines {
        max-width: 880px;
        margin: 0 auto;
        padding-bottom: var(--sp-8);
        display: flex;
        flex-direction: column;
        gap: var(--sp-4);
      }
      .page-head {
        display: flex;
        align-items: flex-start;
        justify-content: space-between;
        flex-wrap: wrap;
        gap: var(--sp-3);
      }
      .page-head h1 {
        margin: 0 0 var(--sp-1);
      }
      .limits {
        display: flex;
        flex-wrap: wrap;
        gap: var(--sp-2);
      }
      .pill {
        font-size: var(--fs-xs);
        color: var(--text);
        background: rgba(47, 227, 210, 0.12);
        border: 1px solid var(--border);
        padding: 2px var(--sp-2);
        border-radius: var(--r-pill);
      }
      .toolbar {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: var(--sp-3);
      }
      .hint {
        color: var(--warn);
        font-size: var(--fs-sm);
        margin: 0;
      }
      .small {
        font-size: var(--fs-sm);
      }
      .empty {
        text-align: center;
      }

      /* Routinen-Karten */
      .routine {
        display: flex;
        flex-direction: column;
        gap: var(--sp-2);
      }
      .routine-head {
        display: flex;
        align-items: center;
        justify-content: space-between;
        gap: var(--sp-3);
        flex-wrap: wrap;
      }
      .routine-title {
        display: flex;
        align-items: center;
        gap: var(--sp-2);
        flex-wrap: wrap;
      }
      .rname {
        font-family: var(--font-display);
        font-weight: 600;
        color: var(--text);
      }
      .status {
        font-size: var(--fs-xs);
        font-weight: 600;
        padding: 1px var(--sp-2);
        border-radius: var(--r-pill);
      }
      .status-idle {
        color: var(--text-dim);
        background: rgba(255, 255, 255, 0.06);
      }
      .status-flying {
        color: var(--bg-deep);
        background: var(--accent);
      }
      .status-paused {
        color: var(--warn);
        background: rgba(255, 180, 60, 0.12);
      }

      .waypoints {
        display: flex;
        align-items: center;
        flex-wrap: wrap;
        gap: var(--sp-1);
      }
      .wp {
        font-family: var(--font-mono, monospace);
        font-size: var(--fs-sm);
        padding: 1px var(--sp-2);
        border-radius: var(--r-sm);
        border: 1px solid var(--border);
        color: var(--text-dim);
      }
      .wp.current {
        color: var(--bg-deep);
        background: var(--accent);
        border-color: var(--accent);
      }
      .arrow {
        color: var(--text-dim);
      }

      .ships {
        display: flex;
        flex-wrap: wrap;
        gap: var(--sp-2);
      }
      .ship-chip {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        color: var(--text);
      }
      .routine-act {
        display: flex;
        gap: var(--sp-2);
        margin-top: var(--sp-1);
      }

      .toggle {
        display: inline-flex;
        align-items: center;
        gap: var(--sp-2);
        cursor: pointer;
        color: var(--text);
      }
      .toggle input {
        width: 18px;
        height: 18px;
        accent-color: var(--accent);
        cursor: pointer;
      }

      /* Designer-Modal */
      .backdrop {
        position: fixed;
        inset: 0;
        z-index: 110;
        display: flex;
        align-items: center;
        justify-content: center;
        padding: var(--sp-4);
        background: rgba(4, 7, 14, 0.72);
        backdrop-filter: blur(4px);
        -webkit-backdrop-filter: blur(4px);
      }
      .popup.designer {
        position: relative;
        width: 100%;
        max-width: 560px;
        max-height: 88vh;
        overflow-y: auto;
        border-radius: var(--r-lg);
        padding: var(--sp-5);
        clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
      }
      .title {
        margin: 0 0 var(--sp-4);
        font-size: var(--fs-lg);
      }
      .field {
        display: flex;
        flex-direction: column;
        gap: var(--sp-1);
        margin-bottom: var(--sp-3);
      }
      .field label {
        font-size: var(--fs-sm);
        color: var(--text-dim);
      }
      .block {
        margin: var(--sp-4) 0;
        padding-top: var(--sp-3);
        border-top: 1px solid var(--border);
      }
      .block-title {
        font-family: var(--font-display);
        font-weight: 600;
        margin-bottom: var(--sp-2);
      }
      .wp-row {
        display: flex;
        align-items: center;
        gap: var(--sp-2);
        padding: var(--sp-1) 0;
      }
      .wp-no {
        color: var(--text-dim);
        width: 28px;
      }
      .spacer {
        flex: 1;
      }
      .wp-add {
        display: flex;
        align-items: center;
        gap: var(--sp-1);
        margin-top: var(--sp-2);
        flex-wrap: wrap;
      }
      .mini {
        width: 64px;
      }
      .sep {
        color: var(--text-dim);
      }
      .ship-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
        gap: var(--sp-3);
        margin-top: var(--sp-2);
      }
      .ship-field {
        display: flex;
        flex-direction: column;
        gap: var(--sp-1);
      }
      .ship-field label {
        display: inline-flex;
        align-items: center;
        gap: 4px;
        font-size: var(--fs-sm);
        color: var(--text-dim);
      }
      .form-error {
        color: var(--warn);
        font-size: var(--fs-sm);
        margin: var(--sp-2) 0 0;
      }
      .actions {
        display: flex;
        gap: var(--sp-2);
        justify-content: flex-end;
        margin-top: var(--sp-4);
      }
      @media (max-width: 480px) {
        .actions {
          flex-direction: column-reverse;
        }
        .actions .btn {
          width: 100%;
        }
      }
    `,
  ],
})
export class RoutinesComponent implements OnInit {
  private readonly api = inject(ApiService);
  private readonly notify = inject(NotificationService);
  private readonly state = inject(GameStateService);
  private readonly balance = inject(BalanceService);

  /** Asset-Helfer fuers Template. */
  protected readonly shipIcon = shipIcon;

  protected readonly routines = signal<Routine[]>([]);
  protected readonly limits = signal<RoutineLimits | null>(null);
  protected readonly loading = signal(true);

  protected readonly draft = signal<RoutineDraft | null>(null);
  protected readonly saving = signal(false);
  protected readonly formError = signal<string | null>(null);

  protected readonly busyId = signal<string | null>(null);
  protected readonly confirmReq = signal<ConfirmRequest | null>(null);

  /** Eingabefelder fuer den naechsten Wegpunkt. */
  protected readonly newG = signal(1);
  protected readonly newS = signal(1);
  protected readonly newP = signal(1);

  protected readonly planets = this.state.planets;

  /** Relevante Schiffstypen, die es auch in balance.json gibt. */
  protected readonly shipTypes = computed(() => {
    const ships = this.balance.value?.ships ?? {};
    return ROUTINE_SHIP_TYPES.filter((t) => t in ships);
  });

  protected readonly maxFields = computed(() => this.limits()?.max_fields_per_route ?? 0);

  protected readonly canCreate = computed(() => {
    const l = this.limits();
    return !!l && l.used_routines < l.max_routines;
  });

  ngOnInit(): void {
    this.reload();
  }

  private reload(): void {
    this.loading.set(true);
    this.api.getRoutines().subscribe({
      next: (res) => {
        this.routines.set(res.routines);
        this.limits.set(res.limits);
        this.loading.set(false);
      },
      error: (err) => {
        this.loading.set(false);
        this.notify.warning('Laden fehlgeschlagen', err?.error?.detail ?? 'Routinen nicht erreichbar.');
      },
    });
  }

  // --- Anzeige-Helfer ---

  statusLabel(r: Routine): string {
    const base: Record<RoutineStatus, string> = {
      idle: 'Bereit',
      flying: 'Unterwegs',
      paused: 'Pausiert',
    };
    if (r.status === 'paused' && r.pause_reason) {
      return `Pausiert — ${PAUSE_REASON_LABEL[r.pause_reason]}`;
    }
    return base[r.status];
  }

  planetName(id: string): string {
    const p = this.planets().find((x) => x.id === id);
    if (!p) {
      return '—';
    }
    return `${p.name} [${p.galaxy}:${p.system}:${p.position}]`;
  }

  shipEntries(ships: Record<string, number>): { type: string; count: number }[] {
    return Object.entries(ships)
      .filter(([, c]) => c > 0)
      .map(([type, count]) => ({ type, count }));
  }

  shipCount(d: RoutineDraft, type: string): number {
    return d.ships[type] || 0;
  }

  shipLabel(type: string): string {
    return metaFor(SHIP_META, type).label;
  }

  shipGlyph(type: string): string {
    return metaFor(SHIP_META, type).glyph;
  }

  // --- An/Aus + Loeschen ---

  toggleEnabled(r: Routine, enabled: boolean): void {
    this.busyId.set(r.id);
    this.api.updateRoutine(r.id, { enabled }).subscribe({
      next: (updated) => {
        this.busyId.set(null);
        this.routines.update((list) => list.map((x) => (x.id === updated.id ? updated : x)));
      },
      error: (err) => {
        this.busyId.set(null);
        this.notify.warning('Umschalten fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
      },
    });
  }

  askDelete(r: Routine): void {
    this.confirmReq.set({
      title: 'Routine löschen?',
      message: `„${r.name}" wird dauerhaft entfernt. Eine eventuell aktive Flotte fliegt regulär zurück.`,
      confirmLabel: 'Löschen',
      action: () => this.deleteRoutine(r),
    });
  }

  runConfirm(): void {
    const c = this.confirmReq();
    this.confirmReq.set(null);
    c?.action();
  }

  private deleteRoutine(r: Routine): void {
    this.busyId.set(r.id);
    this.api.deleteRoutine(r.id).subscribe({
      next: () => {
        this.busyId.set(null);
        this.routines.update((list) => list.filter((x) => x.id !== r.id));
        this.limits.update((l) => (l ? { ...l, used_routines: Math.max(0, l.used_routines - 1) } : l));
        this.notify.success('Gelöscht', `Routine „${r.name}" entfernt.`);
      },
      error: (err) => {
        this.busyId.set(null);
        this.notify.warning('Löschen fehlgeschlagen', err?.error?.detail ?? 'Fehler.');
      },
    });
  }

  // --- Designer ---

  openCreate(): void {
    if (!this.canCreate()) {
      return;
    }
    const home = this.planets().find((p) => p.is_homeworld) ?? this.planets()[0];
    this.formError.set(null);
    this.draft.set({
      id: null,
      name: '',
      homePlanetId: home?.id ?? '',
      waypoints: [],
      ships: {},
    });
  }

  openEdit(r: Routine): void {
    this.formError.set(null);
    this.draft.set({
      id: r.id,
      name: r.name,
      homePlanetId: r.home_planet_id,
      waypoints: r.waypoints.map((w) => ({ ...w })),
      ships: { ...r.ships },
    });
  }

  closeEditor(): void {
    this.draft.set(null);
  }

  patchDraft(patch: Partial<RoutineDraft>): void {
    this.draft.update((d) => (d ? { ...d, ...patch } : d));
  }

  setShip(type: string, count: number): void {
    this.draft.update((d) => {
      if (!d) {
        return d;
      }
      const ships = { ...d.ships };
      if (count > 0) {
        ships[type] = count;
      } else {
        delete ships[type];
      }
      return { ...d, ships };
    });
  }

  addWaypoint(): void {
    const d = this.draft();
    if (!d || d.waypoints.length >= this.maxFields()) {
      return;
    }
    const wp: RoutineWaypoint = {
      galaxy: Math.max(1, this.newG()),
      system: Math.max(1, this.newS()),
      position: Math.max(1, this.newP()),
    };
    this.draft.set({ ...d, waypoints: [...d.waypoints, wp] });
  }

  removeWaypoint(index: number): void {
    this.draft.update((d) =>
      d ? { ...d, waypoints: d.waypoints.filter((_, i) => i !== index) } : d,
    );
  }

  moveWaypoint(index: number, dir: -1 | 1): void {
    this.draft.update((d) => {
      if (!d) {
        return d;
      }
      const target = index + dir;
      if (target < 0 || target >= d.waypoints.length) {
        return d;
      }
      const waypoints = [...d.waypoints];
      [waypoints[index], waypoints[target]] = [waypoints[target], waypoints[index]];
      return { ...d, waypoints };
    });
  }

  save(): void {
    const d = this.draft();
    if (!d || this.saving()) {
      return;
    }
    this.saving.set(true);
    this.formError.set(null);

    if (d.id) {
      const body: RoutineWriteRequest = {
        name: d.name,
        ships: d.ships,
        waypoints: d.waypoints,
      };
      this.api.updateRoutine(d.id, body).subscribe({
        next: (updated) => {
          this.saving.set(false);
          this.routines.update((list) => list.map((x) => (x.id === updated.id ? updated : x)));
          this.closeEditor();
          this.notify.success('Gespeichert', `Routine „${updated.name}" aktualisiert.`);
        },
        error: (err) => this.onSaveError(err),
      });
    } else {
      const body: RoutineWriteRequest = {
        name: d.name,
        home_planet_id: d.homePlanetId,
        ships: d.ships,
        waypoints: d.waypoints,
      };
      this.api.createRoutine(body).subscribe({
        next: (created) => {
          this.saving.set(false);
          this.routines.update((list) => [...list, created]);
          this.limits.update((l) => (l ? { ...l, used_routines: l.used_routines + 1 } : l));
          this.closeEditor();
          this.notify.success('Angelegt', `Routine „${created.name}" erstellt.`);
        },
        error: (err) => this.onSaveError(err),
      });
    }
  }

  private onSaveError(err: { error?: { detail?: string } }): void {
    this.saving.set(false);
    this.formError.set(err?.error?.detail ?? 'Speichern fehlgeschlagen. Bitte Eingaben prüfen.');
  }
}
