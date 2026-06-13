import { Injectable, computed, effect, inject, signal } from '@angular/core';
import { GameStateService } from './game-state.service';

/** Ein gefuehrter Erste-Schritte-Eintrag (FTUE). */
export interface OnboardingStep {
  id: string;
  title: string;
  hint: string;
  route: string;
  cta: string;
  /** Optionale Zustands-Erkennung; zusaetzlich zaehlt ein Klick auf die Aktion als erledigt. */
  detect?: () => boolean;
}

interface OnboardingState {
  done: string[];
  dismissed: boolean;
}

const STORAGE_KEY = 'universe.onboarding.v1';

/**
 * Gefuehrte First-Time-User-Experience (Doku: docs/design/FRONTEND_REDESIGN.md §7).
 *
 * Reine Frontend-Schicht (kein Backend): leitet den Fortschritt aus dem vorhandenen
 * Spielzustand ab UND latcht erledigte Schritte in localStorage, sodass ein Schritt nie
 * wieder "offen" wird. Schritte koennen zudem per Klick auf die Aktion abgehakt werden
 * (Engagement zaehlt), was OGame-artige Komplexitaet schrittweise oeffnet statt zu erschlagen.
 */
@Injectable({ providedIn: 'root' })
export class OnboardingService {
  private readonly state = inject(GameStateService);

  private readonly persisted = signal<OnboardingState>(this.load());

  readonly steps: OnboardingStep[] = [
    {
      id: 'economy',
      title: 'Wirtschaft ausbauen',
      hint: 'Baue Minen (Metall/Kristall) und das Solarkraftwerk aus — sie finanzieren alles Weitere.',
      route: '/buildings',
      cta: 'Zu den Gebaeuden',
    },
    {
      id: 'research',
      title: 'Erste Technologie erforschen',
      hint: 'Im Forschungslabor schaltest du neue Schiffe, Gebaeude und Boni frei.',
      route: '/research',
      cta: 'Zur Forschung',
    },
    {
      id: 'ships',
      title: 'Erste Schiffe bauen',
      hint: 'In der Werft entstehen Spaehsonden, Transporter und Kampfschiffe.',
      route: '/shipyard',
      cta: 'Zur Werft',
      detect: () => (this.state.activePlanet()?.ships ?? []).some((s) => (s.count ?? 0) > 0),
    },
    {
      id: 'fleet',
      title: 'Erste Flotte senden',
      hint: 'Spaehe einen Nachbarn aus oder transportiere Rohstoffe — starte deine erste Mission.',
      route: '/galaxy',
      cta: 'Galaxie oeffnen',
      detect: () => this.state.fleets().length > 0,
    },
    {
      id: 'commander',
      title: 'Kommandeur einsetzen',
      hint: 'Kommandeure verstaerken Flotten und Planeten mit Boni, Moral und Faehigkeiten.',
      route: '/commanders',
      cta: 'Zur Kommandozentrale',
      detect: () => this.state.commanders().length > 0,
    },
  ];

  /** Schritte inkl. erledigt-Flag (gelatchter Speicher ODER aktuelle Zustands-Erkennung). */
  readonly resolved = computed(() => {
    const doneSet = new Set(this.persisted().done);
    return this.steps.map((s) => ({
      step: s,
      done: doneSet.has(s.id) || (s.detect ? s.detect() : false),
    }));
  });

  readonly completedCount = computed(() => this.resolved().filter((r) => r.done).length);
  readonly total = computed(() => this.steps.length);
  readonly allDone = computed(() => this.completedCount() === this.total());
  readonly nextStep = computed(() => this.resolved().find((r) => !r.done)?.step ?? null);
  readonly dismissed = computed(() => this.persisted().dismissed);
  readonly visible = computed(() => !this.dismissed() && !this.allDone());

  constructor() {
    // Zustands-erkannte Schritte dauerhaft latchen, sobald sie einmal erfuellt sind.
    effect(() => {
      const detected = this.steps.filter((s) => s.detect?.()).map((s) => s.id);
      if (detected.length) {
        this.markDone(detected);
      }
    });
  }

  /** Markiert einen Schritt als erledigt (z. B. nach Klick auf die Aktion). */
  complete(id: string): void {
    this.markDone([id]);
  }

  dismiss(): void {
    this.persisted.update((s) => ({ ...s, dismissed: true }));
    this.save();
  }

  /** Onboarding erneut anzeigen (z. B. ueber einen Hilfe-Eintrag). */
  reset(): void {
    this.persisted.set({ done: [], dismissed: false });
    this.save();
  }

  private markDone(ids: string[]): void {
    const cur = this.persisted();
    const merged = new Set(cur.done);
    let changed = false;
    for (const id of ids) {
      if (!merged.has(id)) {
        merged.add(id);
        changed = true;
      }
    }
    if (changed) {
      this.persisted.set({ ...cur, done: [...merged] });
      this.save();
    }
  }

  private load(): OnboardingState {
    try {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (raw) {
        const parsed = JSON.parse(raw) as Partial<OnboardingState>;
        return { done: parsed.done ?? [], dismissed: parsed.dismissed ?? false };
      }
    } catch {
      /* localStorage nicht verfuegbar / korrupt -> Default */
    }
    return { done: [], dismissed: false };
  }

  private save(): void {
    try {
      localStorage.setItem(STORAGE_KEY, JSON.stringify(this.persisted()));
    } catch {
      /* ignorieren */
    }
  }
}
