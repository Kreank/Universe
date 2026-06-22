import { Injectable } from '@angular/core';
import { Coordinate } from '../models/api.models';

/**
 * Reine Flotten-Rechenlogik (Distanz/Reichweite/Sprit/Flugzeit/Fracht) — gespiegelt aus
 * dem Backend (fleet/service.py) und früher doppelt im Inline-Sendeformular (fleet.component)
 * UND im Versand-Overlay (fleet-dispatch) gepflegt. Welle W0: einmalig hier zentralisiert.
 *
 * Alle Methoden sind PURE: sie bekommen die balance.json (als `bal`) und die nötigen Eingaben
 * übergeben und halten KEINEN State. Die exakten Formeln stammen aus dem (vollständigeren)
 * fleet-dispatch-Overlay — bewusst KEINE Verhaltensänderung der Berechnung.
 */
@Injectable({ providedIn: 'root' })
export class FleetCalculationService {
  /** Sichere Zahl (NaN/undefined -> Default). */
  private bnum(v: unknown, d = 0): number {
    return typeof v === 'number' ? v : d;
  }

  /** OGame-Distanzmodell (balance.fleet.distance), gespiegelt aus compute_distance. */
  distanceTo(origin: Coordinate | null, target: Coordinate, bal: any): number | null {
    const d = bal?.fleet?.distance;
    if (!origin || !d) {
      return null;
    }
    if (origin.galaxy !== target.galaxy) {
      return this.bnum(d.inter_galaxy_per_galaxy) * Math.abs(origin.galaxy - target.galaxy);
    }
    if (origin.system !== target.system) {
      return this.bnum(d.same_galaxy_base) + this.bnum(d.same_galaxy_per_system) * Math.abs(origin.system - target.system);
    }
    if (origin.position !== target.position) {
      return this.bnum(d.same_system_base) + this.bnum(d.same_system_per_position) * Math.abs(origin.position - target.position);
    }
    return this.bnum(d.same_position);
  }

  /** Max. einfache Distanz eines Schiffstyps mit vollem Tank (round_trip = Hin+Rück). */
  shipRange(type: string, roundTrip: boolean, bal: any): number {
    const cfg = bal?.ships?.[type];
    if (!cfg) {
      return Infinity;
    }
    const fuel = this.bnum(cfg.fuel);
    if (fuel <= 0) {
      return Infinity; // ortsfest -> keine Begrenzung
    }
    const f = bal.fleet;
    const legs = roundTrip ? 2 : 1;
    return (this.bnum(cfg.fuel_tank) * this.bnum(f.speed_factor)) / (fuel * this.bnum(f.fuel_per_distance_unit) * legs);
  }

  /** Reichweite der Flotte.
   * Ohne Tankschiff: das schwächste (limitierende) Schiff der Auswahl.
   * Mit Tankschiff (combat_roster[*].tanker): Sprit gebündelt -> Gesamttank/Gesamtverbrauch
   * (das Tankschiff hebt die Reichweite aller mit; nie kleiner als das Min-Modell). */
  fleetMaxRange(
    selection: Record<string, number>,
    roundTrip: boolean,
    bal: any,
  ): { maxRange: number; limiting: string | null } {
    const hasTanker = Object.entries(selection).some(
      ([type, n]) => n > 0 && bal?.combat_roster?.[type]?.tanker,
    );
    if (hasTanker) {
      const f = bal.fleet;
      const legs = roundTrip ? 2 : 1;
      let totalTank = 0;
      let totalFuel = 0;
      for (const [type, n] of Object.entries(selection)) {
        if (n <= 0) {
          continue;
        }
        const cfg = bal?.ships?.[type];
        const fuel = this.bnum(cfg?.fuel);
        if (!cfg || fuel <= 0) {
          continue;
        }
        totalTank += this.bnum(cfg.fuel_tank) * n;
        totalFuel += fuel * n;
      }
      if (totalFuel <= 0) {
        return { maxRange: Infinity, limiting: null };
      }
      const pooled = (totalTank * this.bnum(f.speed_factor)) / (totalFuel * this.bnum(f.fuel_per_distance_unit) * legs);
      return { maxRange: pooled, limiting: null };
    }
    let maxRange = Infinity;
    let limiting: string | null = null;
    for (const [type, n] of Object.entries(selection)) {
      if (n <= 0) {
        continue;
      }
      const r = this.shipRange(type, roundTrip, bal);
      if (r < maxRange) {
        maxRange = r;
        limiting = type;
      }
    }
    return { maxRange, limiting };
  }

  /** Treibstoff-Bedarf (Deuterium) der Auswahl für eine Distanz (legs = 1 einfach / 2 Hin+Rück). */
  fuelCost(selection: Record<string, number>, distance: number, roundTrip: boolean, bal: any): number {
    const f = bal?.fleet;
    const legs = roundTrip ? 2 : 1;
    let total = 0;
    for (const [type, n] of Object.entries(selection)) {
      if (n > 0) {
        total += this.bnum(bal?.ships?.[type]?.fuel) * n;
      }
    }
    return Math.max(
      1,
      Math.ceil((total * distance) / this.bnum(f?.speed_factor, 1) * this.bnum(f?.fuel_per_distance_unit, 1) * legs),
    );
  }

  /** Geschätzte Flugzeit (eine Strecke, Sekunden) — gespiegelt aus flight_seconds, OHNE
   * Antriebsforschung (daher konservativ/Obergrenze). null wenn keine Distanz/Auswahl. */
  flightSeconds(distance: number | null, selection: Record<string, number>, speedPct: number, bal: any): number | null {
    if (distance === null) {
      return null;
    }
    let slowest = Infinity;
    for (const [type, n] of Object.entries(selection)) {
      if (n <= 0) {
        continue;
      }
      const sp = this.bnum(bal?.ships?.[type]?.speed);
      if (sp > 0 && sp < slowest) {
        slowest = sp;
      }
    }
    if (!isFinite(slowest) || slowest <= 0) {
      return null;
    }
    const fleetSpeed = Math.max(0.01, this.bnum(bal?.universe?.fleet_speed, 1));
    const pct = Math.max(1, speedPct);
    const raw = 10 + (35000 / pct) * Math.sqrt((distance * 10) / slowest);
    return raw / fleetSpeed;
  }

  /** Gesamt-Frachtkapazität der gewählten Flotte (Summe ship.cargo × Anzahl). */
  cargoCapacity(selection: Record<string, number>, bal: any): number {
    let capacity = 0;
    for (const [type, n] of Object.entries(selection)) {
      if (n > 0) {
        capacity += this.bnum(bal?.ships?.[type]?.cargo) * n;
      }
    }
    return capacity;
  }

  /** Auf dem aktiven Planeten verfügbare Menge einer Ressource — Exoten liegen unter .exotic. */
  availOnPlanet(planet: { resources?: any } | null, key: string): number {
    const res = planet?.resources;
    if (!res) {
      return 0;
    }
    if (key === 'antimatter' || key === 'dark_matter') {
      return Math.floor(this.bnum(res.exotic?.[key]?.amount));
    }
    return Math.floor(this.bnum(res[key]?.amount));
  }

  /**
   * Maximal ladbare Menge EINER Ressource = min(auf dem Planeten verfügbar,
   * freie Restkapazität der Flotte ohne diese Ressource).
   */
  cargoCapFor(
    key: string,
    cargo: Record<string, number>,
    cargoKeys: readonly string[],
    capacity: number,
    planet: { resources?: any } | null,
    reserve = 0,
  ): number {
    const others = cargoKeys.reduce((s, k) => s + this.bnum(cargo[k]), 0) - this.bnum(cargo[key]);
    const room = Math.max(0, capacity - others);
    // ``reserve`` (z.B. Spritbedarf bei Deuterium) bleibt am Planeten -> nicht ladbar.
    const avail = Math.max(0, this.availOnPlanet(planet, key) - Math.max(0, reserve));
    return Math.max(0, Math.min(avail, room));
  }
}
