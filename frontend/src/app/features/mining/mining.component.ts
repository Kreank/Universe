import { ChangeDetectionStrategy, Component, computed, inject, signal } from '@angular/core';
import { DecimalPipe } from '@angular/common';
import { RouterLink } from '@angular/router';
import { ApiService } from '../../core/services/api.service';
import { Coordinate, FleetSlots, MiningComposition, MiningField, MiningFieldsResponse } from '../../core/models/api.models';
import { CountdownComponent } from '../../shared/components/countdown.component';
import { EmptyStateComponent } from '../../shared/components/empty-state.component';
import { FleetDispatchComponent } from '../../shared/components/fleet-dispatch.component';
import { FleetSlotsComponent } from '../../shared/components/fleet-slots.component';

type SortKey = 'richness' | 'metal' | 'crystal' | 'expires' | 'composition';
type CompFilter = 'all' | MiningComposition;

/** Reichtums-Tier -> Sortier-Rang (ergiebig zuerst). */
const RICHNESS_RANK: Record<string, number> = { ergiebig: 3, reich: 2, normal: 1, karg: 0 };

/** Komposition -> Sortier-Rang (spezialisierte Felder zuerst, ausgewogen zuletzt). */
const COMPOSITION_RANK: Record<string, number> = { metal_rich: 2, crystal_rich: 1, balanced: 0 };

/** Anzeige-Meta je Komposition (Badge-Glyph + Klarname). */
const COMPOSITION_META: Record<MiningComposition, { glyph: string; label: string }> = {
  metal_rich: { glyph: '⚙️', label: 'Metalllastig' },
  balanced: { glyph: '⚖️', label: 'Ausgewogen' },
  crystal_rich: { glyph: '💎', label: 'Kristalllastig' },
};

/** Ein wählbarer System-Filter-Eintrag (Wert "g:s" + Anzeige-Label). */
interface SystemOption {
  key: string;
  label: string;
}

/**
 * Bergbau · Asteroiden-Übersicht. Zeigt alle AKTIVEN Felder in Reichweite der
 * Ortungs-Forschung (Stufe 1 = Heimat-Galaxie, je Stufe +1 Galaxie). Felder wandern
 * alle 24–48h, daher ist diese Liste der Weg, sie zu finden — ohne System für System
 * durch die Galaxie-Ansicht zu klicken. Jede Zeile ist direkt anfliegbar (Minen).
 */
@Component({
  selector: 'app-mining',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [DecimalPipe, RouterLink, CountdownComponent, EmptyStateComponent, FleetDispatchComponent, FleetSlotsComponent],
  template: `
    <h1>Bergbau · Asteroidenfelder</h1>
    <p class="sub">
      Aktive Felder in Reichweite deiner Ortung. Felder wandern alle 24–48 h — hier siehst du,
      wo gerade was liegt.
    </p>

    @if (loading()) {
      <p class="muted">Lade Felder…</p>
    } @else if (data(); as d) {
      @if (d.prospecting < 1) {
        <div class="card lock">
          <div class="lock-ico">🛰</div>
          <div>
            <strong>Ortung nicht erforscht</strong>
            <p class="muted small">
              Erforsche <strong>Ortung</strong>, um aktive Asteroidenfelder aufzuspüren.
              Stufe 1 zeigt deine Heimat-Galaxie, jede weitere Stufe erweitert die Reichweite.
            </p>
            <a class="btn btn-sm btn-primary" routerLink="/research" [queryParams]="{ focus: 'prospecting' }">Zur Forschung →</a>
          </div>
        </div>
      } @else {
        <div class="bar-row">
          <span class="chip">Ortung Stufe {{ d.prospecting }}</span>
          <span class="chip ghost">Reichweite: {{ rangeLabel(d) }}</span>
          <span class="chip ghost">{{ d.fields.length }} Felder</span>
          <span class="chip deut" title="Beim Schürfen wird mit dieser Chance zusätzlich Deuterium gefunden — ein Zufallsfund, kein Feld-Vorrat.">🛢️ Deuterium-Fund-Chance: {{ deutChancePct(d) }}%</span>
          <button class="btn btn-sm btn-ghost" (click)="reload()">↻ Aktualisieren</button>
        </div>

        @if (deutChancePct(d) < 5) {
          <p class="deut-hint muted small">
            🛢️ Deuterium-Funde sind aktuell selten. Die Forschung
            <a routerLink="/research" [queryParams]="{ focus: 'deuterium_prospecting' }">Deuterium-Prospektion</a>
            erhöht Chance und Menge beim Asteroiden-Bergbau.
          </p>
        }

        <p class="slot-line muted small">
          {{ slots()?.breakdown?.mining ?? 0 }} Bergbau-Flüge aktiv ·
          <app-fleet-slots [slots]="slots()" [compact]="true" />
        </p>

        @if (d.fields.length) {
          <div class="filter-row">
            <label class="f-grp">
              <span class="muted small">System:</span>
              <select class="sel" [value]="filterSystem()" (change)="filterSystem.set($any($event.target).value)">
                <option value="all">Alle Systeme</option>
                @for (s of availableSystems(); track s.key) {
                  <option [value]="s.key">{{ s.label }}</option>
                }
              </select>
            </label>
            <div class="f-grp">
              <span class="muted small">Komposition:</span>
              <button class="lnk" [class.on]="filterComp() === 'all'" (click)="filterComp.set('all')">Alle</button>
              <button class="lnk" [class.on]="filterComp() === 'metal_rich'" (click)="filterComp.set('metal_rich')">⚙️ Metalllastig</button>
              <button class="lnk" [class.on]="filterComp() === 'balanced'" (click)="filterComp.set('balanced')">⚖️ Ausgewogen</button>
              <button class="lnk" [class.on]="filterComp() === 'crystal_rich'" (click)="filterComp.set('crystal_rich')">💎 Kristalllastig</button>
            </div>
          </div>

          <div class="sort-row">
            <span class="muted small">Sortieren:</span>
            <button class="lnk" [class.on]="sortKey() === 'richness'" (click)="sortKey.set('richness')">Reichtum</button>
            <button class="lnk" [class.on]="sortKey() === 'metal'" (click)="sortKey.set('metal')">Metall</button>
            <button class="lnk" [class.on]="sortKey() === 'crystal'" (click)="sortKey.set('crystal')">Kristall</button>
            <button class="lnk" [class.on]="sortKey() === 'composition'" (click)="sortKey.set('composition')">Komposition</button>
            <button class="lnk" [class.on]="sortKey() === 'expires'" (click)="sortKey.set('expires')">Verfällt</button>
          </div>
        }

        @if (sortedFields().length) {
          <div class="grid fields">
            @for (f of sortedFields(); track f.coords) {
              <article class="card field">
                <div class="f-top">
                  <a class="coord" [routerLink]="['/galaxy']" [queryParams]="{ g: f.galaxy, s: f.system }" title="Auf der Galaxie-Karte ansehen">[{{ f.coords }}]</a>
                  <span class="rich" [attr.data-r]="f.richness">{{ richnessLabel(f.richness) }} · ×{{ f.mult }}</span>
                </div>
                <div class="f-comp">
                  <span class="comp-badge" [attr.data-c]="f.composition ?? 'balanced'">{{ compGlyph(f) }} {{ compLabel(f) }}</span>
                </div>
                <div class="f-res">
                  <span class="r metal" [class.dom]="f.composition === 'metal_rich'" title="Metall-Restvorrat">⛏ {{ f.metal | number: '1.0-0' }}<span class="faint"> / {{ f.metal_max | number: '1.0-0' }}</span></span>
                  <span class="r crystal" [class.dom]="f.composition === 'crystal_rich'" title="Kristall-Restvorrat">💎 {{ f.crystal | number: '1.0-0' }}<span class="faint"> / {{ f.crystal_max | number: '1.0-0' }}</span></span>
                </div>
                <div class="f-foot">
                  @if (f.expires_at) {
                    <span class="exp muted small">wandert in <app-countdown [target]="f.expires_at" /></span>
                  }
                  <button class="btn btn-sm btn-primary" (click)="openMine(f)">⛏ Minen</button>
                </div>
              </article>
            }
          </div>
        } @else if (d.fields.length) {
          <app-empty-state art="empty_search">
            Keine Felder passen zu den gewählten Filtern. <button class="lnk on" (click)="resetFilters()">Filter zurücksetzen</button>
          </app-empty-state>
        } @else {
          <app-empty-state art="empty_search">
            Keine aktiven Felder in Reichweite. Höhere Ortungsstufe erweitert die Reichweite.
          </app-empty-state>
        }
      }
    }

    @if (dispatch(); as d) {
      <app-fleet-dispatch
        [target]="d.target"
        [targetName]="d.name"
        [initialMission]="'mine'"
        (sent)="onMined()"
        (close)="dispatch.set(null)"
      />
    }
  `,
  styles: [
    `
      .sub { color: var(--text-dim); margin-top: calc(-1 * var(--sp-2)); }
      .bar-row { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; margin: var(--sp-3) 0; }
      .slot-line { display: flex; align-items: baseline; gap: 0.35em; flex-wrap: wrap; margin: calc(-1 * var(--sp-2)) 0 var(--sp-3); }
      .slot-line app-fleet-slots { display: inline; }
      .chip { font-size: var(--fs-sm); background: var(--surface-2); border: 1px solid var(--border-strong); border-radius: var(--r-sm); padding: 2px var(--sp-2); }
      .chip.ghost { background: transparent; color: var(--text-dim); }
      .chip.deut { color: #ffd479; border-color: color-mix(in srgb, #ffd479 35%, var(--border-strong)); }
      .deut-hint { margin: calc(-1 * var(--sp-2)) 0 var(--sp-3); }
      .deut-hint a { color: var(--accent); }
      .lock { display: flex; gap: var(--sp-3); align-items: center; padding: var(--sp-4); }
      .lock-ico { font-size: 2rem; }
      .filter-row { display: flex; align-items: center; gap: var(--sp-4); flex-wrap: wrap; margin-bottom: var(--sp-2); }
      .f-grp { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
      .sel { background: var(--surface-2); border: 1px solid var(--border-strong); border-radius: var(--r-sm); color: var(--text); font-size: var(--fs-sm); padding: 2px var(--sp-2); }
      .sort-row { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; margin-bottom: var(--sp-2); }
      .lnk { background: none; border: none; color: var(--text-dim); cursor: pointer; font-size: var(--fs-sm); padding: 0; }
      .lnk.on { color: var(--accent); text-decoration: underline; }
      .fields { display: grid; grid-template-columns: repeat(auto-fill, minmax(240px, 1fr)); gap: var(--sp-3); }
      .field { display: flex; flex-direction: column; gap: var(--sp-2); padding: var(--sp-3); }
      .f-top { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); }
      .coord { font-family: var(--font-mono); color: var(--text); text-decoration: none; border-bottom: 1px dotted var(--border-strong); }
      .coord:hover { color: var(--accent); }
      .rich { font-size: var(--fs-xs); padding: 1px var(--sp-1); border-radius: var(--r-sm); background: rgba(255,255,255,0.06); color: var(--text-dim); }
      .rich[data-r='reich'] { color: #7fd3ff; }
      .rich[data-r='ergiebig'] { color: #ffd479; }
      .f-comp { display: flex; }
      .comp-badge { font-size: var(--fs-xs); padding: 1px var(--sp-2); border-radius: var(--r-sm); background: rgba(255,255,255,0.05); color: var(--text-dim); border: 1px solid transparent; }
      .comp-badge[data-c='metal_rich'] { color: #d7c4a8; border-color: color-mix(in srgb, #d7c4a8 35%, transparent); }
      .comp-badge[data-c='crystal_rich'] { color: #9fd0ff; border-color: color-mix(in srgb, #9fd0ff 35%, transparent); }
      .f-res { display: flex; gap: var(--sp-3); font-size: var(--fs-sm); }
      .r.dom { font-weight: 700; color: var(--text); }
      .f-foot { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); margin-top: auto; }
      .faint { color: var(--text-faint); }
    `,
  ],
})
export class MiningComponent {
  private readonly api = inject(ApiService);

  protected readonly loading = signal(true);
  protected readonly data = signal<MiningFieldsResponse | null>(null);
  protected readonly sortKey = signal<SortKey>('richness');
  /** Filter: nach System ("g:s") oder 'all'. */
  protected readonly filterSystem = signal<string>('all');
  /** Filter: nach Komposition oder 'all'. */
  protected readonly filterComp = signal<CompFilter>('all');
  /** Offener Versand-Dialog (Bergbau-Flotte zum Feld schicken). */
  protected readonly dispatch = signal<{ target: Coordinate; name: string } | null>(null);
  /** Flotten-Slot-Kapazität (gemeinsamer Pool — Bergbau-Flüge zählen mit). */
  protected readonly slots = signal<FleetSlots | null>(null);

  /** Alle in der Feldliste vorkommenden Systeme (für das System-Dropdown). */
  protected readonly availableSystems = computed<SystemOption[]>(() => {
    const fields = this.data()?.fields ?? [];
    const galaxies = new Set(fields.map((f) => f.galaxy));
    const multiGalaxy = galaxies.size > 1;
    const seen = new Map<string, SystemOption>();
    for (const f of fields) {
      const key = `${f.galaxy}:${f.system}`;
      if (!seen.has(key)) {
        seen.set(key, { key, label: multiGalaxy ? `Galaxie ${f.galaxy} · System ${f.system}` : `System ${f.system}` });
      }
    }
    return [...seen.values()].sort((a, b) => {
      const [ga, sa] = a.key.split(':').map(Number);
      const [gb, sb] = b.key.split(':').map(Number);
      return ga - gb || sa - sb;
    });
  });

  /** Felder nach den aktiven Filtern (System + Komposition) — VOR der Sortierung. */
  protected readonly filteredFields = computed<MiningField[]>(() => {
    const fields = this.data()?.fields ?? [];
    const sys = this.filterSystem();
    const comp = this.filterComp();
    return fields.filter((f) => {
      if (sys !== 'all' && `${f.galaxy}:${f.system}` !== sys) {
        return false;
      }
      if (comp !== 'all' && (f.composition ?? 'balanced') !== comp) {
        return false;
      }
      return true;
    });
  });

  protected readonly sortedFields = computed(() => {
    const fields = [...this.filteredFields()];
    const key = this.sortKey();
    return fields.sort((a, b) => {
      switch (key) {
        case 'metal': return b.metal - a.metal;
        case 'crystal': return b.crystal - a.crystal;
        case 'expires': return (a.expires_at ?? '').localeCompare(b.expires_at ?? '');
        case 'composition': return (COMPOSITION_RANK[b.composition ?? 'balanced'] ?? 0) - (COMPOSITION_RANK[a.composition ?? 'balanced'] ?? 0)
          || (b.metal + b.crystal) - (a.metal + a.crystal);
        default: return (RICHNESS_RANK[b.richness] ?? 0) - (RICHNESS_RANK[a.richness] ?? 0)
          || (b.metal + b.crystal) - (a.metal + a.crystal);
      }
    });
  });

  constructor() {
    this.reload();
  }

  reload(): void {
    this.loading.set(true);
    this.api.getMiningFields().subscribe({
      next: (d) => { this.data.set(d); this.loading.set(false); },
      error: () => { this.loading.set(false); },
    });
    this.loadSlots();
  }

  loadSlots(): void {
    this.api.getFleetSlots().subscribe({
      next: (s) => this.slots.set(s),
      error: () => this.slots.set(null),
    });
  }

  /** Setzt System- und Kompositions-Filter zurück. */
  resetFilters(): void {
    this.filterSystem.set('all');
    this.filterComp.set('all');
  }

  /** Öffnet den Versand-Dialog (Bergbau-Flotte) für ein Feld. */
  openMine(f: MiningField): void {
    this.dispatch.set({ target: { galaxy: f.galaxy, system: f.system, position: f.position }, name: `Asteroidenfeld [${f.coords}]` });
  }

  /** Nach erfolgreichem Versand: Dialog schließen + Felder neu laden. */
  onMined(): void {
    this.dispatch.set(null);
    this.reload();
  }

  richnessLabel(r: string): string {
    return ({ karg: 'Karg', normal: 'Normal', reich: 'Reich', ergiebig: 'Ergiebig' } as Record<string, string>)[r] ?? r;
  }

  /** Komposition eines Feldes (Default 'balanced' für Alt-Felder). */
  private comp(f: MiningField): MiningComposition {
    return f.composition ?? 'balanced';
  }

  compGlyph(f: MiningField): string {
    return COMPOSITION_META[this.comp(f)].glyph;
  }

  compLabel(f: MiningField): string {
    return COMPOSITION_META[this.comp(f)].label;
  }

  /** Deuterium-Fund-Chance in Prozent (gerundet). */
  deutChancePct(d: MiningFieldsResponse): number {
    return Math.round((d.deuterium_chance ?? 0) * 100);
  }

  rangeLabel(d: MiningFieldsResponse): string {
    if (d.range <= 0) return 'Heimat-Galaxie';
    return `Galaxien ±${d.range}`;
  }
}
