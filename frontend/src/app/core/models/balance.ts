/**
 * Lockerer Typ fuer `shared/balance.json`. Wird NUR fuer Anzeige
 * (Labels, Tooltip-Werte, Moral-Baender) genutzt — niemals fuer Berechnungen,
 * da der Server autoritativ ist (ADR-006).
 */

export interface BalanceMoraleBand {
  min: number;
  max: number;
  combat_mod: number;
  label: string;
  effects: string[];
}

export interface BalanceRank {
  key: string;
  label: string;
  xp_threshold: number;
  span_contrib: number;
  stat_cap: number;
  permadeath_protection: number;
}

export interface Balance {
  universe: {
    speed: number;
    base_income: Record<string, number>;
    galaxies: number;
    systems_per_galaxy: number;
    positions_per_system: number;
  };
  buildings: Record<string, Record<string, unknown>>;
  research: {
    techs: Record<string, Record<string, unknown>>;
    [key: string]: unknown;
  };
  ships: Record<string, Record<string, unknown>>;
  defenses: Record<string, Record<string, unknown>>;
  commander: {
    morale: {
      min: number;
      max: number;
      bands: BalanceMoraleBand[];
      [key: string]: unknown;
    };
    ranks: BalanceRank[];
    specializations: string[];
    personality_traits: Record<string, Record<string, unknown>>;
    [key: string]: unknown;
  };
  [key: string]: unknown;
}
