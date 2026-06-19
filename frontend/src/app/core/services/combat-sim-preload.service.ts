import { Injectable, signal } from '@angular/core';

/** Gegner-Voreinstellung für den Kampf-Simulator (z. B. aus einem Spionagebericht). */
export interface CombatSimPreset {
  ships: Record<string, number>;
  defenses: Record<string, number>;
  /** Gegner-Techstufen (Engine-Keys: weapons_tech/shield_tech/armor_tech …). Optional. */
  tech: Record<string, number>;
  /** Quelle für eine kurze Notiz im Simulator (z. B. Zielname/Koords). */
  label?: string;
}

/**
 * Übergibt eine Gegner-Voreinstellung an den Simulator, ohne sie durch URL-Params zu schleusen
 * (Flotten-/Verteidigungs-Dicts können groß sein). Der Simulator ruft beim Init ``consume()`` —
 * die Voreinstellung wird genau einmal angewandt und danach gelöscht.
 */
@Injectable({ providedIn: 'root' })
export class CombatSimPreloadService {
  private readonly _preset = signal<CombatSimPreset | null>(null);

  set(preset: CombatSimPreset): void {
    this._preset.set(preset);
  }

  /** Liest die Voreinstellung und löscht sie (einmalige Anwendung). */
  consume(): CombatSimPreset | null {
    const p = this._preset();
    this._preset.set(null);
    return p;
  }
}
