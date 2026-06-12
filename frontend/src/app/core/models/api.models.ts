/**
 * TypeScript-Typen, die exakt dem `shared/api-contract.md` (v0.1) entsprechen.
 * Single Source of Truth fuer alle Service-Calls.
 */

export type ResourceKey = 'metal' | 'crystal' | 'deuterium';

/** Ein Eintrag der Rangliste (Punktesystem, OGame-Stil). */
export interface RankingEntry {
  rank: number;
  player_id: string;
  display_name: string;
  is_self: boolean;
  points: number;
  buildings: number;
  research: number;
  fleet: number;
  defense: number;
}

export interface RankingResponse {
  entries: RankingEntry[];
  me: RankingEntry | null;
  total_players: number;
}

export interface ResourceCost {
  metal: number;
  crystal: number;
  deuterium: number;
}

// --- Auth ---------------------------------------------------------------

export interface Player {
  id: string;
  email: string;
  display_name: string;
  score: number;
  is_protected: boolean;
  created_at: string;
  last_active: string;
}

export interface AuthResponse {
  token: string;
  player: Player;
}

export interface RegisterRequest {
  email: string;
  password: string;
  display_name: string;
}

export interface LoginRequest {
  email: string;
  password: string;
}

// --- Planet & Wirtschaft ------------------------------------------------

export interface Planet {
  id: string;
  name: string;
  galaxy: number;
  system: number;
  position: number;
  /** Aus der Position abgeleitet: fire | barren | normal | cold | ice. */
  planet_type?: string;
  temp_max: number;
  fields_used: number;
  fields_max: number;
  is_homeworld: boolean;
  /** Kommandeur, der diesen Planeten als Gouverneur verwaltet (Produktions-Bonus). */
  governor_commander_id?: string | null;
}

export interface ResourcePool {
  amount: number;
  rate: number;
  capacity: number;
}

export interface EnergyBalance {
  produced: number;
  consumed: number;
  balance: number;
  factor: number;
}

export interface PlanetResources {
  metal: ResourcePool;
  crystal: ResourcePool;
  deuterium: ResourcePool;
  energy: EnergyBalance;
}

export interface PlanetBuilding {
  type: string;
  level: number;
  upgrade_finishes_at: string | null;
}

export interface PlanetUnit {
  type: string;
  count: number;
}

export interface PlanetDetail extends Planet {
  resources: PlanetResources;
  buildings: PlanetBuilding[];
  ships: PlanetUnit[];
  defenses: PlanetUnit[];
  /** Monde: Verknuepfung zum Mutterplaneten + letzter Sprung (Sprungtor-Cooldown). */
  parent_planet_id?: string | null;
  last_jump_at?: string | null;
}

// --- Voraussetzungen ----------------------------------------------------

/** Eine einzelne Voraussetzung (Forschung ODER Gebaeude) mit Erfuellungs-Status. */
export interface Requirement {
  type: string;
  level: number;
  met: boolean;
}

// --- Gebaeude -----------------------------------------------------------

export interface BuildingState {
  type: string;
  level: number;
  upgrade_finishes_at: string | null;
}

export interface BuildingOption {
  type: string;
  next_level: number;
  cost: ResourceCost;
  build_seconds: number;
  can_afford: boolean;
  requirements_met: boolean;
  requirements?: Requirement[];
  /** Energiebilanz: + erzeugt, - verbraucht, 0 neutral. */
  energy_now: number;
  energy_next: number;
  energy_delta: number;
}

export interface BuildingsResponse {
  buildings: BuildingState[];
  available: BuildingOption[];
}

export interface UpgradeResponse {
  type: string;
  level: number;
  upgrade_finishes_at: string;
}

export interface DemolishResponse {
  type: string;
  level: number;
}

// --- Forschung ----------------------------------------------------------

export interface ResearchState {
  type: string;
  level: number;
  finishes_at: string | null;
}

export interface ResearchOption {
  type: string;
  next_level: number;
  cost: ResourceCost;
  research_seconds: number;
  can_afford: boolean;
  requirements_met: boolean;
  requirements?: Requirement[];
}

export interface ResearchResponse {
  research: ResearchState[];
  available: ResearchOption[];
}

export interface ResearchStartResponse {
  type: string;
  level: number;
  finishes_at: string;
}

// --- Werft --------------------------------------------------------------

export type ShipyardCategory = 'ship' | 'defense';

export interface ShipOption {
  type: string;
  cost: ResourceCost;
  build_seconds_each: number;
  can_build: boolean;
  requirements_met: boolean;
  requirements?: Requirement[];
  weapon_type?: string | null;
  drive?: number | null;
  range?: string | null;
}

export interface BuildQueueItem {
  type: string;
  count: number;
  category: ShipyardCategory;
  finishes_at: string | null;
}

export interface ShipyardResponse {
  ships: ShipOption[];
  defenses: ShipOption[];
  queue: BuildQueueItem[];
}

export interface ShipyardBuildRequest {
  type: string;
  count: number;
  category: ShipyardCategory;
}

export interface ShipyardBuildResponse {
  queue: BuildQueueItem[];
}

// --- Flotte -------------------------------------------------------------

export type FleetMission =
  | 'attack' | 'transport' | 'spy' | 'deploy' | 'recycle' | 'colonize' | 'mine' | 'expedition' | 'trade' | 'intercept';
export type FleetStatus = 'flying' | 'arrived' | 'returning' | 'returned';

export interface Coordinate {
  galaxy: number;
  system: number;
  position: number;
}

export interface IncomingAttack {
  id: string;
  attacker: string;
  origin: string | null;
  target: Coordinate;
  ships_total: number;
  arrive_at: string;
}

export interface Fleet {
  id: string;
  mission: FleetMission;
  status: string;
  origin: string;
  target: Coordinate;
  commander_id: string | null;
  ships: Record<string, number>;
  cargo: Partial<ResourceCost>;
  depart_at: string;
  arrive_at: string;
  return_at: string;
}

export interface FleetSendRequest {
  origin_planet_id: string;
  target: Coordinate;
  mission: FleetMission;
  ships: Record<string, number>;
  cargo: ResourceCost;
  commander_id: string | null;
  speed_pct: number;
  /** Handel: Angebots-Ressource faehrt als Fracht mit, getauscht gegen want_res. */
  offer_res?: 'metal' | 'crystal' | 'deuterium';
  offer_amount?: number;
  want_res?: 'metal' | 'crystal' | 'deuterium';
  /** Gewaehlte Eskort-Patrouillen (StationedFleet-IDs), die die Route decken. */
  escort_ids?: string[];
  /** Scharfzuschaltende erlernte Kommandeur-Faehigkeiten (Keys, bis arm_slots). */
  ability_keys?: string[];
  /** Expedition (mission == 'expedition'): gewuenschte Verweildauer in Stunden (1..max). */
  expedition_hours?: number;
  /** Ziel-Typ: 'moon' greift/spioniert den Mond statt des Planeten an der Koordinate. */
  target_type?: 'moon';
  /** Abfangen (mission == 'intercept'): Patrouillen-Radius in Systemen (Default 0 = nur Zielsystem). */
  radius?: number;
}

/** Ein Eintrag im Faehigkeiten-Katalog (RPG-Entwicklung). */
export interface AbilityDef {
  label: string;
  category: string;
  kind: string;
  per_level: number;
  max_level: number;
  sp_cost: number;
  requires?: { min_rank?: string };
  cooldown_seconds: number;
}

export interface AbilityCatalog {
  catalog: Record<string, AbilityDef>;
  progression: { arm_slots?: Record<string, number>; unlearn_refund?: number };
}

export interface GalaxyCell {
  position: number;
  occupant_type: string;
  name: string | null;
  player_id: string | null;
  player_name?: string | null;
  npc_id: string | null;
  /** Hat dieser Spieler dieses Ziel schon per Sonde aufgeklaert? */
  discovered?: boolean;
  /** P2P-Handelsanzeige des Spielers (falls aktiviert). */
  trade?: { offer: string | null; want: string | null; rate: number | null; note: string | null } | null;
  /** Asteroidenfeld am Ort (Restvorrat) — Bergbauschiffe koennen hier minen. */
  asteroid?: {
    richness: string;
    mult: number;
    metal: number;
    crystal: number;
    metal_max: number;
    crystal_max: number;
  } | null;
  /** Mond am Ort (teilt die Position) — eigenes Angriffs-/Spionageziel. */
  moon?: {
    name: string;
    player_id: string;
    player_name: string | null;
    own: boolean;
  } | null;
}

export interface GalaxyResponse {
  cells: GalaxyCell[];
}

/** Aufklaerungs-Schnappschuss eines Ziels (Detailtiefe je nach Stufe). */
export interface GalaxyIntel {
  name?: string;
  kind?: string;
  ships_total?: number;
  defenses_total?: number;
  level?: number;
  fleet?: Record<string, number>;
  defenses?: Record<string, number>;
  resources?: { metal?: number; crystal?: number; deuterium?: number };
  scanned_at?: string;
  /** Haendler-Markt (aus merchant_intel): Spezialisierung + Kurs-Schnappschuss. */
  merchant?: boolean;
  /** Unangreifbares Handelszentrum mit globalem Kurs (vs. lokaler Legacy-Haendler). */
  trade_center?: boolean;
  spec?: string;
  prices?: { metal?: number; crystal?: number; deuterium?: number };
  prices_at?: string;
}

/** Oeffentlicher globaler Handelskurs der Handelszentren (Wert je Einheit). */
export interface TradeIndex {
  prices: { metal: number; crystal: number; deuterium: number };
  base_value: { metal: number; crystal: number; deuterium: number };
  players: number;
  updated_at: string | null;
}

export interface GalaxyTarget {
  npc_id: string | null;
  name: string;
  galaxy: number;
  system: number;
  position: number;
  coords: string;
  ships_total: number;
  defenses_total: number;
  /** Aufklaerungs-Detailstufe (1..3). */
  level?: number;
  discovered_at?: string | null;
  intel?: GalaxyIntel | null;
}

// --- Commander ----------------------------------------------------------

export interface CommanderPersona {
  background: string;
  voice: string;
  focus?: string;
}

export interface MoraleBand {
  label: string;
  combat_mod: number;
}

export interface CommanderBonus {
  stat: 'attack' | 'shield' | 'speed' | string;
  target: string; // 'all' | Schiffsklasse (fighter/cruiser/capital/civil)
  pct: number; // Basiswert (im Kampf zusaetzlich moral-skaliert)
}

export interface Commander {
  id: string;
  name: string;
  persona: CommanderPersona;
  traits: string[];
  specialization: string;
  rank: string;
  /** Gueteklasse F..SSS (angeborenes Potenzial, Doku 05a). Default C. */
  grade?: string;
  xp: number;
  morale: number;
  loyalty: number;
  /** Unmut 0..100 — waechst je staerker der Kommandeur; Schwelle 100 -> Forderung. */
  unrest?: number;
  /** RPG-Entwicklung: Skillpunkte, erlernte Faehigkeiten, Arm-Slots. */
  skill_points?: number;
  abilities?: { key: string; level: number }[];
  arm_slots?: number;
  span_capacity: number;
  status: string;
  morale_band: MoraleBand;
  focus: string | null;
  bonuses: CommanderBonus[];
  assigned_fleet_id: string | null;
  training_finishes_at: string | null;
}

export interface CommanderDetail extends Commander {
  history: Transmission[];
}

export interface CommanderTrainResponse {
  commander: Commander;
}

export interface SpanInfo {
  base: number;
  from_command_center: number;
  from_doctrine: number;
  total: number;
  in_use: number;
}

// --- Postfach / Funksprueche --------------------------------------------

export interface Transmission {
  id: string;
  type: string;
  subject: string;
  body: string;
  commander_id: string | null;
  requires_decision: boolean;
  decision_payload: unknown;
  read: boolean;
  created_at: string;
  from_player_id?: string | null;
  from_name?: string | null;
}

/** Eigenes P2P-Handelsprofil (unverbindlicher Werbe-Kurs). */
export interface TradeProfile {
  enabled: boolean;
  offer: 'metal' | 'crystal' | 'deuterium' | null;
  want: 'metal' | 'crystal' | 'deuterium' | null;
  rate: number | null;
  note: string | null;
}

/** Ein aktiver P2P-Handelspartner im Verzeichnis. */
export interface TradePartner {
  player_id: string;
  name: string;
  offer: string | null;
  want: string | null;
  rate: number | null;
  note: string | null;
  coords: string | null;
}

export interface SendMessageRequest {
  to_player_id: string;
  subject: string;
  body: string;
  reply_to?: string | null;
}

/** Eine vom Sensorphalanx erfasste Flottenbewegung zu/von einem Ziel. */
export interface PhalanxMovement {
  id: string;
  owner: string;
  mission: string;
  status: string;
  direction: 'incoming' | 'outgoing';
  origin: string | null;
  target: string;
  ships_total: number;
  arrive_at: string | null;
  return_at: string | null;
}

export interface PhalanxScanResult {
  coords: string;
  movements: PhalanxMovement[];
}

/** Eine eigene stationierte Patrouille (deploy) inkl. Eskort-Angebot. */
export interface StationedFleet {
  id: string;
  coords: string;
  galaxy: number;
  system: number;
  position: number;
  ships: Record<string, number>;
  ships_total: number;
  escort_enabled: boolean;
  escort_radius: number;
  escort_fee_pct: number;
  intercept_enabled: boolean;
  intercept_radius: number;
  has_interdictor: boolean;
  interceptors: number;
  /** Treibstoff-Vorrat: null = eigenes Gebiet (gratis), Zahl = vorgeschobener Deuterium-Vorrat. */
  fuel: number | null;
}

/** Ein aktives Eskort-Angebot im Verzeichnis. */
export interface EscortOffer {
  id: string;
  owner: string;
  coords: string;
  galaxy: number;
  system: number;
  radius: number;
  fee_pct: number;
  power: number;
  ships_total: number;
}

export type DecisionChoice = 'accept' | 'reject' | 'negotiate';

export interface DecisionRequest {
  choice: DecisionChoice;
}

export interface DecisionResponse {
  ok: boolean;
  morale_delta: number;
  message: string;
}

// --- Combat-Report ------------------------------------------------------

export interface CombatRound {
  round: number;
  /** Distanz-Band dieser Runde: 'near' | 'medium' | 'far'. */
  distance?: string;
  attacker_fire: number;
  defender_fire: number;
  attacker_losses: Record<string, number>;
  defender_losses: Record<string, number>;
  attacker_fled?: number;
  defender_fled?: number;
  /** Ueberraschungs-/Hinterhaltsrunde (Tarnkappe, round=0). */
  ambush?: boolean;
}

export interface CombatReport {
  id: string;
  location: string;
  /** Perspektive des abrufenden Spielers. */
  role: 'attacker' | 'defender';
  npc_name?: string | null;
  attacker: Record<string, number>;
  defender: Record<string, number>;
  rounds: CombatRound[];
  winner: 'attacker' | 'defender' | 'draw';
  attacker_survivors: Record<string, number>;
  defender_survivors: Record<string, number>;
  attacker_losses: Record<string, number>;
  defender_losses: Record<string, number>;
  attacker_fled: Record<string, number>;
  defender_fled: Record<string, number>;
  attacker_captured: Record<string, number>;
  defender_captured: Record<string, number>;
  attacker_drive_disabled: Record<string, number>;
  defender_drive_disabled: Record<string, number>;
  loot: Partial<ResourceCost>;
  debris: Partial<ResourceCost>;
  created_at: string;
}

// --- WebSocket-Nachrichten ---------------------------------------------

export interface WsResourceTick {
  type: 'resource_tick';
  planet_id: string;
  resources: PlanetResources;
}

export interface WsBuildComplete {
  type: 'build_complete';
  planet_id: string;
  building: string;
  level: number;
}

export interface WsResearchComplete {
  type: 'research_complete';
  tech: string;
  level: number;
}

export interface WsFleetArrived {
  type: 'fleet_arrived';
  fleet_id: string;
  mission: string;
}

export interface WsFleetReturned {
  type: 'fleet_returned';
  fleet_id: string;
}

export interface WsTransmission {
  type: 'transmission';
  transmission: Transmission;
}

export interface WsAttackWarning {
  type: 'attack_warning';
  location: string;
  arrive_at: string;
  ships_total?: number;
  attacker_name?: string;
}

export interface WsCombatReport {
  type: 'combat_report';
  report_id: string;
  summary: Record<string, unknown>;
}

export type WsMessage =
  | WsResourceTick
  | WsBuildComplete
  | WsResearchComplete
  | WsFleetArrived
  | WsFleetReturned
  | WsTransmission
  | WsAttackWarning
  | WsCombatReport
  | { type: string; [key: string]: unknown };

export interface WsClientSubscribe {
  type: 'subscribe';
  planet_id: string;
}

export interface WsClientPing {
  type: 'ping';
}
