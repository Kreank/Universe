import { Injectable, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { firstValueFrom } from 'rxjs';
import { Balance, BalanceMoraleBand } from '../models/balance';

/**
 * Laedt `assets/balance.json` einmalig beim App-Start. Liefert NUR
 * Anzeige-Hilfen (Moral-Baender, Rohkosten fuer Tooltips). Keine Spiel-Mathematik.
 */
@Injectable({ providedIn: 'root' })
export class BalanceService {
  private readonly http = inject(HttpClient);
  private readonly _balance = signal<Balance | null>(null);

  readonly balance = this._balance.asReadonly();

  async load(): Promise<void> {
    if (this._balance()) {
      return;
    }
    const data = await firstValueFrom(this.http.get<Balance>('assets/balance.json'));
    this._balance.set(data);
  }

  get value(): Balance | null {
    return this._balance();
  }

  /** Findet das Moral-Band fuer einen Wert (Fallback aus balance.json). */
  moraleBand(morale: number): BalanceMoraleBand | null {
    const bands = this._balance()?.commander?.morale?.bands ?? [];
    return bands.find((b) => morale >= b.min && morale <= b.max) ?? null;
  }

  /** CSS-Klassenname fuer das Moral-Band (Farbcodierung). */
  moraleBandClass(morale: number): string {
    const band = this.moraleBand(morale);
    switch (band?.label) {
      case 'hoch':
        return 'band-high';
      case 'neutral':
        return 'band-neutral';
      case 'niedrig':
        return 'band-low';
      case 'kritisch':
        return 'band-critical';
      default:
        return 'band-neutral';
    }
  }
}

/** APP_INITIALIZER-Factory: laedt balance.json bevor die App startet. */
export function initBalance(): () => Promise<void> {
  const service = inject(BalanceService);
  return () => service.load();
}
