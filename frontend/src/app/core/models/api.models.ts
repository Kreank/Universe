/**
 * TypeScript-Typen, die exakt dem `shared/api-contract.md` (v0.1) entsprechen.
 * Single Source of Truth fuer alle Service-Calls.
 */

export type ResourceKey = 'metal' | 'crystal' | 'deuterium';

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
  temp_max: number;
  fields_used: number;
  fields_max: number;
  is_homeworld: boolean;
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

export type FleetMission = 'attack' | 'transport' | 'spy' | 'deploy';
export type FleetStatus = 'flying' | 'arrived' | 'returning' | 'returned';

export interface Coordinate {
  galaxy: number;
  system: number;
  position: number;
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
}

export interface GalaxyCell {
  position: number;
  occupant_type: string;
  name: string | null;
  player_id: string | null;
  npc_id: string | null;
}

export interface GalaxyResponse {
  cells: GalaxyCell[];
}

export interface GalaxyTarget {
  npc_id: string;
  name: string;
  galaxy: number;
  system: number;
  position: number;
  coords: string;
  ships_total: number;
  defenses_total: number;
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
  xp: number;
  morale: number;
  loyalty: number;
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
  attacker_fire: number;
  defender_fire: number;
  attacker_losses: Record<string, number>;
  defender_losses: Record<string, number>;
}

export interface CombatReport {
  id: string;
  location: string;
  attacker: unknown;
  defender: unknown;
  rounds: CombatRound[];
  winner: string;
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
