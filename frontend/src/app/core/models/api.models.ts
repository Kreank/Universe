/**
 * TypeScript-Typen, die exakt dem `shared/api-contract.md` (v0.1) entsprechen.
 * Single Source of Truth fuer alle Service-Calls.
 */

export type ResourceKey = 'metal' | 'crystal' | 'deuterium';

/** Rangliste (OGame-Stil): Reiter Spieler/Allianzen + Kategorie-Wertungen. */
export type RankBoard = 'players' | 'alliances';
export type RankCategory = 'total' | 'buildings' | 'research' | 'fleet' | 'defense';

/** Ein Eintrag (Spieler ODER Allianz, je nach Board). `id` = player_id bzw. alliance_id. */
export interface RankBoardEntry {
  rank: number; // Rang in der aktuell gewählten Kategorie
  id: string;
  name: string;
  tag?: string | null; // Allianz-Tag (nur Allianz-Board)
  member_count?: number | null; // nur Allianz-Board
  is_self: boolean;
  value: number; // Punkte in der gewählten Kategorie
  total: number;
  buildings: number;
  research: number;
  fleet: number;
  defense: number;
}

export interface RankBoardResponse {
  board: RankBoard;
  category: RankCategory;
  entries: RankBoardEntry[];
  me: RankBoardEntry | null;
  my_ranks: Record<RankCategory, number> | null; // eigener Rang je Kategorie ("Dein Platz")
  total: number;
}

export interface ResourceCost {
  metal: number;
  crystal: number;
  deuterium: number;
  /** Exotische Endgame-Kosten (Capstone-Schiffe), kontoweit. 0/undefiniert = nicht relevant. */
  antimatter?: number;
  dark_matter?: number;
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
  /** Exotische Endgame-Ressourcen (kontoweit, erspielt). Von /auth/me geliefert. */
  dark_matter?: number;
  antimatter?: number;
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
  /** Exotische Materie pro Planet (antimatter/dark_matter); nur vorhanden, wenn je produziert/erhalten. */
  exotic?: Record<string, { amount: number; rate: number }>;
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
  /** Positions-Gate (Exo-Minen): auf diesem Planeten-Slot baubar? */
  position_ok?: boolean;
  /** Erlaubte System-Positionen (leer = ueberall baubar). */
  allowed_positions?: number[];
  /** Nur eines pro Imperium baubar (z. B. Handelszentrum). */
  one_per_account?: boolean;
  /** Schon woanders im Imperium vorhanden -> hier gesperrt. */
  account_blocked?: boolean;
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
  /** Endgame-Capstone-Schiff: Besitz-Status (owned/cap). null = kein Capstone. */
  capstone?: { owned: number; cap: number } | null;
  /** Pro-Planet-Limit (z. B. Schildkuppeln 1). null = unbegrenzt. */
  max_per_planet?: number | null;
  /** Bestand dieser pro-Planet-einmaligen Einheit auf dem Planeten (gebaut + Queue). */
  planet_owned?: number | null;
}

export interface BuildQueueItem {
  id: string;
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
  | 'attack' | 'transport' | 'spy' | 'deploy' | 'recycle' | 'colonize' | 'mine' | 'expedition' | 'trade' | 'intercept' | 'escort';
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
  mission?: FleetMission;
  /** Aufklaerungsstufe des Betrachters (1..3): L1 nur Gesamtstaerke, L2 + Zusammensetzung, L3 + Fracht. */
  intel_level?: number;
  /** Flotten-Zusammensetzung — nur ab Aufklaerungsstufe 2 gesetzt, sonst null. */
  ships?: Record<string, number> | null;
  /** Mitgefuehrte Fracht — nur ab Aufklaerungsstufe 3 gesetzt, sonst null. */
  cargo?: Partial<ResourceCost> | null;
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
  /** Nur bei laufender Mining-Session: Live-Frachtbalken (anteilig gefüllt). */
  mining?: {
    metal: number;
    crystal: number;
    filled: number;
    capacity: number;
    progress: number;
  } | null;
}

/** Aufschlüsselung der belegten Flotten-Slots nach Aktivität (Summe == used). */
export interface FleetSlotBreakdown {
  flights: number;
  expeditions: number;
  mining: number;
  recycling: number;
  patrols: number;
}

/** Kapazitäts-Anzeige der Flotten-Slots: belegt/frei + Aufschlüsselung. */
export interface FleetSlots {
  max: number;
  used: number;
  free: number;
  breakdown: FleetSlotBreakdown;
}

/** Ein aktives Asteroidenfeld in der Bergbau-Übersicht (Reichweite via Ortungs-Forschung). */
export interface MiningField {
  galaxy: number;
  system: number;
  position: number;
  coords: string;
  richness: string;
  mult: number;
  metal: number;
  crystal: number;
  metal_max: number;
  crystal_max: number;
  expires_at: string | null;
}

/** Antwort der Asteroiden-Übersicht: Ortungsstufe + Reichweite + sichtbare Felder. */
export interface MiningFieldsResponse {
  prospecting: number;
  range: number;
  home_galaxy: number | null;
  fields: MiningField[];
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
  /** Expeditions-Doktrin (offline-sichere Vorab-Wahl): 'cautious' | 'bold'. */
  expedition_doctrine?: 'cautious' | 'bold';
  /** Ziel-Typ: 'moon' greift/spioniert den Mond, 'station' belagert die Allianz-Station,
   *  'mining_fleet' greift die am Feld schuerfende Flotte an. */
  target_type?: 'moon' | 'station' | 'mining_fleet';
  /** Abfangen (mission == 'intercept'): Patrouillen-Radius in Systemen (Default 0 = nur Zielsystem). */
  radius?: number;
  /** Eskorte (mission == 'escort'): Deckungs-Radius in Systemen + Gebuehr (Anteil 0..max_fee_pct). */
  escort_radius?: number;
  escort_fee_pct?: number;
  /** Kapern (mission == 'attack'): bevorzugtes Kaperziel — Schiffstyp-Key oder 'value' (teuerste zuerst). */
  capture_priority?: string;
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
  /** Allianz-Station am Ort (teilt die Position) — fremde Station ist ein Belagerungsziel. */
  station?: {
    alliance_id: string;
    tag: string;
    mine: boolean;
    status: string;
    hp: number;
    max_hp: number;
    hp_pct: number;
  } | null;
  /** Geparkte Schuerf-Flotte am Ort — fremde sind angreifbar (Fracht-Beute), eigene nur Info. */
  mining_fleet?: {
    owner: string | null;
    mine: boolean;
    ships_total: number;
  } | null;
  /** Dynamisches Game-Event am Ort (Komet/Anomalie/Schwarzmarkt/Wrack/...). */
  event?: { event_type: string; data: Record<string, unknown>; expires_at: string } | null;
  /** Trümmerfeld am Ort (nach Kämpfen) — mit Recyclern abbaubar. */
  debris?: { metal: number; crystal: number } | null;
}

/** Ein laufendes Welt-/Karten-Event (GET /api/events). */
export interface GameEvent {
  id: string;
  event_type: string;
  scope: string;
  galaxy: number | null;
  system: number | null;
  position: number | null;
  coords: string | null;
  data: Record<string, unknown>;
  expires_at: string;
}

export interface AllianceZone {
  alliance_id: string;
  tag: string;
  center_system: number;
  radius: number;
  /** Gehoert die Zone der eigenen Allianz? */
  mine: boolean;
}

export interface GalaxyResponse {
  cells: GalaxyCell[];
  /** Allianz-Einflusszonen, die dieses System abdecken. */
  zones?: AllianceZone[];
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
  /** Aufgeklaerte Kampfforschung des Ziels (ab Stufe 2, Spieler UND NPC). */
  combat_tech?: { weapons_tech?: number; shield_tech?: number; armor_tech?: number };
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

// --- W1: Ziele & Bedrohungen (gebündelter Ziel-Screen) ------------------

/** Ein entdecktes NPC-Imperium in der Ziele-Liste (GET /api/targets/npcs). */
export interface NpcTarget {
  npc_id: string;
  name: string;
  behavior_profile: string;
  galaxy: number;
  system: number;
  position: number;
  coords: string;
  intel_level: number;
  ships_total: number;
  defenses_total: number;
  /** Aktueller Beziehungsstatus (NpcRelationStatus) oder null, wenn nie kontaktiert. */
  relation_status: string | null;
  /** Galaxien-Distanz zum Heimatplaneten (null, wenn unbekannt). */
  distance_galaxies: number | null;
  last_intel_at: string | null;
}

/** Ein entdeckter Spieler in der Ziele-Liste (GET /api/targets/players). */
export interface PlayerTarget {
  player_id: string | null;
  name: string;
  galaxy: number;
  system: number;
  position: number;
  coords: string;
  intel_level: number;
  ships_total: number;
  has_trade_offer: boolean;
  distance_galaxies: number | null;
  last_intel_at: string | null;
}

/** Eine Bedrohung in der Ziele-Liste (GET /api/targets/threats). */
export interface ThreatItem {
  kind: 'incoming' | 'hostile_npc';
  name: string;
  attacker_kind: 'npc' | 'player' | null;
  /** Nur bei kind === 'hostile_npc' gesetzt. */
  npc_id?: string | null;
  origin: string | null;
  target: Coordinate | null;
  arrive_at: string | null;
  ships_total: number;
  intel_level: number;
  distance_galaxies: number | null;
  mission: FleetMission | string | null;
  /** Dringlichkeit: 0 = akut (hervorgehoben), höher = weniger dringend. */
  priority: number;
}

// --- NPC-Diplomatie (Welle 1: verhandelbare KI-Imperien) ----------------

/** Beziehungsstatus zwischen Spieler und NPC-Imperium. */
export type NpcRelationStatus =
  | 'neutral'
  | 'allied'
  | 'ceasefire'
  | 'hostile'
  | 'broken_pact';

/** Angebotsart einer Verhandlung. */
export type NpcOfferType = 'alliance' | 'ceasefire' | 'tribute';

/** Aktuelle Beziehung zu einem NPC-Imperium (GET /api/npc/{id}/relation). */
export interface NpcRelation {
  npc_id: string;
  status: NpcRelationStatus;
  alliance_since: string | null;
  ceasefire_until: string | null;
  tribute_metal_per_cycle: number;
  betrayed_by_player: boolean;
  betrayed_by_npc: boolean;
  message_count: number;
  positive_actions: number;
  negative_actions: number;
  last_decision_at: string | null;
}

/** Ein Eintrag der Diplomatie-Uebersicht (GET /api/npc/relations): Beziehung + Name/Koordinaten. */
export interface NpcRelationListItem extends NpcRelation {
  npc_name: string;
  galaxy: number;
  system: number;
  position: number;
  coords: string;
  /** Zeitpunkt eines gebrochenen Pakts (sonst null). */
  broken_at: string | null;
}

/** Body fuer POST /api/npc/{id}/negotiate. */
export interface NegotiateRequest {
  offer_type: NpcOfferType;
  /** Bei 'tribute': angebotenes Metall je Zyklus (Server klemmt auf Cap + Bestand). */
  tribute_metal?: number;
  /** Bei 'ceasefire': gewuenschte Dauer in Stunden (Server klemmt auf Cap). */
  ceasefire_hours?: number;
  /** Optionaler Freitext — vom Backend als DATEN behandelt, nie als Instruktion. */
  message?: string;
}

/** Antwort auf eine Kontaktaufnahme (202): die KI-Antwort folgt asynchron als Funkspruch. */
export interface NegotiateResponse {
  ok: boolean;
  status: string;
  message: string;
}

/** decision_payload eines NPC-Gegenangebots (Transmission type 'npc_diplomacy'). */
export interface DiplomacyCounterPayload {
  kind: 'diplomacy_counter';
  npc_id: string;
  offer_type: NpcOfferType;
  proposed_terms: { tribute_metal?: number; ceasefire_hours?: number };
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
  /** Anteil der Boni, der aus getragener Ausruestung stammt (separat ausgewiesen). */
  equipment_bonuses?: CommanderBonus[];
  /** Getragene Set-Teile je Set (z.B. {key:'fighter',count:2}). */
  equipment_sets?: { key: string; count: number }[];
  assigned_fleet_id: string | null;
  training_finishes_at: string | null;
}

export interface CommanderDetail extends Commander {
  history: Transmission[];
}

// --- Commander-Gedaechtnis & Eigenleben (Welle 2) -----------------------

/** Stimmung einer Erinnerung — faerbt die Gedaechtnis-Timeline. */
export type MemorySentiment = 'positive' | 'negative' | 'neutral';

/** Eine einzelne Erinnerung des Kommandeurs (chronologisch, sentiment-gefaerbt). */
export interface CommanderMemoryEntry {
  event_type: string;
  context: {
    enemy_name?: string;
    planet?: string;
    outcome?: string;
    loot?: Partial<Record<ResourceKey, number>> | Record<string, number>;
    kind?: string;
    rank?: string;
    about_player_id?: string;
    about_npc_id?: string;
    [key: string]: unknown;
  };
  sentiment: MemorySentiment;
  created_at: string | null;
}

/** Meinung des Kommandeurs ueber einen Gegner (Spieler/NPC). */
export interface CommanderOpinion {
  opinion_type: 'respects' | 'despises' | 'fears' | 'envies' | string;
  strength: number; // 0..1
  hated: boolean; // Erzfeind-Hervorhebung
  target_name: string | null;
  target_kind: 'player' | 'npc';
}

/** Beziehung zu einem anderen Kommandeur des Spielers. */
export interface CommanderRelationship {
  other_commander_id: string;
  other_name: string | null;
  rel_type: 'rivalry' | 'respect' | 'grudge' | 'bond' | string;
  strength: number; // 0..1
}

/** Eine offene Kraenkung (treibt Unmut/Meuterei). */
export interface CommanderGrievance {
  grievance_type: string;
  severity: number;
  accumulated_count: number;
  created_at: string | null;
}

/** Volles Gedaechtnis-Dossier (GET /api/commanders/{id}/memory). */
export interface CommanderMemoryDossier {
  commander_id: string;
  status: string;
  /** true bei status == 'mutinous' — Frontend zeigt deutliche Meuterei-Warnung. */
  mutiny_warning: boolean;
  /** KI-Erinnerungs-Narrativ (atmosphaerischer Text), falls vorhanden. */
  memory_summary: string | null;
  memories: CommanderMemoryEntry[];
  opinions: CommanderOpinion[];
  relationships: CommanderRelationship[];
  grievances: CommanderGrievance[];
}

// --- Commander-Ausruestung (Equipment-System) ---------------------------

/** Eine konkrete Item-Instanz im Spieler-Inventar bzw. in einem Slot. */
export interface EquipmentItem {
  id: string;
  item_key: string;
  slot: string; // head | hands | chest | shoes
  rarity: string; // common | rare | epic
  rarity_label: string;
  label: string;
  set: string; // fighter | cruiser | capital | civil
  equipped_commander_id: string | null;
  bonuses: CommanderBonus[];
}

/** Ein Ausruestungs-Slot mit (optional) belegtem Item. */
export interface EquipmentSlotView {
  slot: string;
  label: string;
  item: EquipmentItem | null;
}

/** Set-Fortschritt eines Kommandeurs (getragene Teile + aktive Schwellen). */
export interface EquipmentSet {
  key: string;
  label: string;
  count: number;
  active_thresholds: number[];
}

/** Vollstaendiger Ausruestungs-Zustand eines Kommandeurs. */
export interface EquipmentState {
  slots: EquipmentSlotView[];
  sets: EquipmentSet[];
  bonuses: CommanderBonus[];
}

/** Statischer Katalog (Slots, Raritaeten, Sets, Items, Fertigung). */
export interface EquipmentCatalog {
  slots: string[];
  slot_labels: Record<string, string>;
  rarities: Record<string, { label: string; mult: number }>;
  sets: Record<
    string,
    { label: string; ship_class: string; bonus: Record<string, CommanderBonus[]> }
  >;
  items: Record<
    string,
    { slot: string; set: string; label: string; bonuses: CommanderBonus[] }
  >;
  craft: { academy_min: number; cost: { metal: number; crystal: number; deuterium: number } };
  drops: Record<string, unknown>;
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

/** Ein NPC-Handelszentrum in Forschungs-Reichweite (Handel-Reiter). */
export interface TradeCenter {
  npc_id: string;
  name: string;
  galaxy: number;
  system: number;
  position: number;
  coords: string;
  spec: string;
  prices: { metal: number; crystal: number; deuterium: number };
  /** Distanz in Galaxien zur Heimat (0 = eigene Galaxie). */
  distance_galaxies: number;
}

/** Ein fremdes Spieler-Handelszentrum (eigenes Handelszentrum-Gebaeude) in Handelsnetz-Reichweite.
 *  Handeln laeuft wie beim NPC-Zentrum ueber eine 'trade'-Mission zu den Hub-Koordinaten; der
 *  Besitzer verdient an der Marge (sichtbar in seiner Handelshistorie als partner_kind 'player'). */
export interface PlayerHub {
  kind: 'player_hub';
  planet_id: string;
  owner_name: string;
  /** Planetenname (zeigt das Hub an). */
  name: string;
  galaxy: number;
  system: number;
  position: number;
  coords: string;
  /** Globaler Indexkurs (Wert je Einheit) — wie bei den NPC-Zentren. */
  prices: { metal: number; crystal: number; deuterium: number };
  /** Effektive Marge des Besitzers (z. B. 0.02 = 2 %). */
  hub_margin: number;
  /** Distanz in Galaxien zur Heimat (0 = eigene Galaxie). */
  distance_galaxies: number;
}

/** Antwort des Handels-Hubs: Forschungsstufe + Reichweite + aktive Handelszentren + Spieler-Hubs. */
export interface TradeCentersResponse {
  trade_network: number;
  range: number;
  building_bonus: number;
  home_galaxy: number | null;
  centers: TradeCenter[];
  /** Fremde Spieler-Handelszentren in Reichweite (eigenes erscheint nie). */
  player_hubs: PlayerHub[];
}

/** Ein Eintrag der Handelshistorie (mit wem zuletzt gehandelt wurde). */
export interface TradeHistoryEntry {
  id: string;
  partner_kind: 'npc' | 'player';
  partner_id: string;
  partner_name: string;
  offered_res: string;
  offered_amount: number;
  received_res: string;
  received_amount: number;
  created_at: string;
}

export interface TradeHistoryResponse {
  entries: TradeHistoryEntry[];
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

/** Modus einer stationierten Flotte (genau einer, exklusiv). */
export type StationMode = 'park' | 'intercept' | 'escort';

/** Eine eigene stationierte Flotte (Stationieren/Abfangen/Eskorte). */
export interface StationedFleet {
  id: string;
  coords: string;
  galaxy: number;
  system: number;
  position: number;
  ships: Record<string, number>;
  ships_total: number;
  /** Exklusiver Modus: 'park' (geparkt), 'intercept' (Abfangen) oder 'escort' (Eskorte). */
  mode: StationMode;
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

// --- Eskort-Gesuche-Board (Nachfrage-Seite) -----------------------------

export type EscortJobStatus = 'open' | 'accepted' | 'cancelled' | 'expired' | 'done';

/**
 * Eine eigene Eskort-Station, die ein offenes Gesuch decken koennte
 * (kommt aus GET /escort/jobs pro fremdem Auftrag).
 */
export interface CoveringStation {
  station_id: string;
  /** "g:s:p" der Station. */
  coords: string;
  /** Gebuehr-Anteil dieser Station (0..1). */
  fee_pct: number;
  /** Absolute Gebuehr fuer diesen Auftrag (cargo_value * fee_pct). */
  fee: number;
  power: number;
  ships_total: number;
}

/**
 * Offener Eskort-Auftrag EINES ANDEREN Spielers, den du mit eigenen
 * Eskort-Stationen decken kannst (GET /escort/jobs).
 */
export interface EscortJob {
  id: string;
  /** "g:s:p" — Start (default Heimatplanet des Erstellers). */
  origin: string;
  /** "g:s:p" — Ziel. */
  target: string;
  origin_coords: Coordinate;
  target_coords: Coordinate;
  cargo_value: number;
  max_fee_pct: number;
  min_power: number;
  status: EscortJobStatus;
  created_at: string;
  expires_at: string;
  /** Name des Auftraggebers. */
  requester: string;
  /** Eigene Stationen, die diesen Auftrag decken koennen (>=1). */
  covering_stations: CoveringStation[];
}

/** Eigener Eskort-Auftrag (GET /escort/jobs/mine). */
export interface EscortJobMine {
  id: string;
  origin: string;
  target: string;
  origin_coords: Coordinate;
  target_coords: Coordinate;
  cargo_value: number;
  max_fee_pct: number;
  min_power: number;
  status: EscortJobStatus;
  created_at: string;
  expires_at: string;
  /** Bei status === 'accepted': Name des annehmenden Anbieters. */
  accepted_by: string | null;
  accepted_station_id: string | null;
  accepted_station_coords: Coordinate | null;
  accepted_fee_pct: number | null;
}

/** Body fuer POST /escort/jobs. */
export interface CreateEscortJobRequest {
  target: Coordinate;
  cargo_value: number;
  max_fee_pct: number;
  /** Default = Heimatplanet, wenn weggelassen. */
  origin?: Coordinate;
  min_power?: number;
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

/** Kampf-Tech einer Seite (für die Simulator-Transparenz). */
export interface CombatSimTech {
  weapons_tech: number;
  shield_tech: number;
  armor_tech: number;
  weapons_mastery: number;
  shield_mastery: number;
  armor_mastery: number;
}

/** Transparente Annahmen, mit denen der Simulator gerechnet hat (Tech, Doktrin, Commander). */
export interface CombatSimMeta {
  /** DEINE Seite (volle Forschung + Doktrin + optionaler Commander) — unabhängig von der Rolle. */
  you: {
    tech: CombatSimTech;
    antimatter_forge: number;
    doctrine: string | null;
    doctrine_mult: number;
    aura_mult: number;
    commander: {
      name: string;
      morale: number;
      specialization: string;
      grade?: string;
      attack_mult: number;
    } | null;
  };
  /** Die eingestellte Gegner-Forschung. */
  enemy: { tech: CombatSimTech };
  /** Deine Rolle im simulierten Kampf. */
  role: 'attacker' | 'defender';
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
  /** Durch Ionen lahmgelegte (überlebende) Verteidigung — feuert für den Rest der Schlacht nicht. */
  defender_defense_disabled?: Record<string, number>;
  /** Nach dem Kampf automatisch reparierte Verteidigung (70 % der zerstörten). */
  defender_defense_rebuilt?: Record<string, number>;
  /** Nur im Kampf-Simulator: transparente Tech/Commander-Annahmen beider Seiten. */
  sim_meta?: CombatSimMeta | null;
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

// --- Megastrukturen ---
export interface MegastructureCost {
  metal: number;
  crystal: number;
  deuterium: number;
  dark_matter: number;
  antimatter: number;
}

export interface MegastructureOption {
  type: string;
  name: string;
  level: number;
  max_level: number;
  next_level: number;
  cost: MegastructureCost;
  build_seconds: number;
  effect: string | null;
  effect_per_level: number;
  blurb: string;
  building_until: string | null;
  busy: boolean;
  maxed: boolean;
  can_afford: boolean;
}

export interface MegastructureListResponse {
  dark_matter: number;
  antimatter: number;
  structures: MegastructureOption[];
}

// --- Routinen (automatisierte Farm-Routen) ---

/** Ein Wegpunkt einer Farm-Route (galaktische Koordinate). */
export interface RoutineWaypoint {
  galaxy: number;
  system: number;
  position: number;
}

export type RoutineStatus = 'idle' | 'flying' | 'paused';
export type RoutinePauseReason =
  | 'no_fuel'
  | 'no_ships'
  | 'no_slot'
  | 'no_target'
  | 'fleet_lost';

/** Eine gespeicherte Farm-Routine (Backend-autoritativer Status). */
export interface Routine {
  id: string;
  name: string;
  home_planet_id: string;
  ships: Record<string, number>;
  waypoints: RoutineWaypoint[];
  enabled: boolean;
  status: RoutineStatus;
  pause_reason: RoutinePauseReason | null;
  /** Index des aktuellen Wegpunkts. */
  cursor: number;
  active_fleet_id: string | null;
}

export interface RoutineLimits {
  max_routines: number;
  max_fields_per_route: number;
  used_routines: number;
}

export interface RoutineListResponse {
  routines: Routine[];
  limits: RoutineLimits;
}

/** Anlage-/Bearbeitungs-Body (POST/PATCH). */
export interface RoutineWriteRequest {
  name?: string;
  home_planet_id?: string;
  enabled?: boolean;
  ships?: Record<string, number>;
  waypoints?: RoutineWaypoint[];
}

// --- Allianz ------------------------------------------------------------

export type AllianceRole = 'founder' | 'officer' | 'member';

/** Offene Einladung in eine Allianz (Spieler ist (noch) in keiner). */
export interface AllianceInvite {
  id: string;
  name: string;
  tag: string;
}

/** Gemeinsamer Ressourcen-Pool der Allianz. */
export interface AlliancePool {
  metal: number;
  crystal: number;
  deuterium: number;
}

export interface AllianceMember {
  player_id: string;
  name: string;
  role: AllianceRole;
  joined_at: string;
}

export interface AllianceStationStats {
  defenses: Record<string, number>;
  attack_total: number;
  shield_total: number;
  max_hp: number;
  zone_radius: number;
  defense_tech: Record<string, number>;
  /** Stations-Forschung: aktuelle Verteidigungs-Tech-Stufe, Cap + Kosten der nächsten Stufe. */
  tech_level?: number;
  max_tech?: number;
  next_tech_cost?: ResourceCost | null;
  modules?: Record<string, number>;
  slots?: number;
  slots_used?: number;
  module_tech_bonus?: Record<string, number>;
  relocate_speed_mult?: number;
}

export interface AllianceStationTransit {
  target: [number, number, number] | null;
  arrive_at: string | null;
  returning: boolean;
}

export interface AllianceStation {
  id: string;
  coords: string;
  galaxy: number;
  system: number;
  position: number;
  radius_level: number;
  fuel: number;
  hp: number;
  status: 'active' | 'inactive' | 'transit' | 'destroyed';
  stats?: AllianceStationStats;
  transit?: AllianceStationTransit | null;
}

/** Kontext eines Forschungs-Knotens: bestimmt die Wirkungs-Reichweite. */
export type AllianceResearchContext = 'coop' | 'zone' | 'ally' | 'passive_collective';

export interface AllianceResearchNode {
  context: AllianceResearchContext;
  lever: string;
  effect: string;
  repeatable: boolean;
  max_level: number;
  level: number;
  per_level: number;
  next_cost: ResourceCost | null;
}

export interface AllianceResearchTree {
  label: string;
  nodes: Record<string, AllianceResearchNode>;
}

export interface AllianceStationConfig {
  build_cost: ResourceCost;
  base_radius: number;
  max_radius: number;
  radius_upgrade_cost: ResourceCost;
  upkeep_deuterium_per_tick: number;
  max_per_alliance: number;
  [key: string]: unknown;
}

/** Vollstaendige Allianz-Uebersicht (Spieler ist Mitglied). */
export interface AllianceOverview {
  id: string;
  name: string;
  tag: string;
  founder_id: string;
  pool: AlliancePool;
  research_levels: Record<string, number>;
  members: AllianceMember[];
  member_count: number;
  max_members: number;
  stations: AllianceStation[];
  my_role: AllianceRole;
  research_catalog: Record<string, AllianceResearchTree>;
  station_config: AllianceStationConfig;
}

/** Antwort von GET /api/alliance: entweder Mitglied (alliance gesetzt) oder offene Einladungen. */
export interface AllianceResponse {
  alliance: AllianceOverview | null;
  invites: AllianceInvite[];
  /** Nur ohne eigene Allianz: Gruendungskosten (vom Heimatplaneten) + Mitglieder-Cap. */
  create_cost?: ResourceCost;
  max_members?: number;
}

// --- Lebende Galaxie-Chronik (Welle 3) ---
/** Schluessel-Ereignis-Typ eines Chronik-Kapitels (steuert Label + Glyph). */
export type ChronicleEventType =
  | 'battle'
  | 'power'
  | 'rise'
  | 'fall'
  | 'betrayal'
  | 'diplomacy'
  | 'cosmic_event'
  | 'quiet';

/** Ein zugrundeliegendes Server-Ereignis ("Quelle" eines Kapitels). Neben `type` freie Fakten-Felder. */
export interface ChronicleKeyEvent {
  type: ChronicleEventType;
  [key: string]: unknown;
}

/** Ein erzaehltes Kapitel der Galaxie-Saga (KI-Historiker). */
export interface ChronicleEntry {
  id: string;
  title: string;
  /** Erzaehlter Fliesstext (mehrere Saetze) — der Hauptinhalt. */
  body: string;
  narrator: string;
  /** Berichtszeitraum (ISO) — Anfang/Ende. */
  span_start: string | null;
  span_end: string | null;
  key_events: ChronicleKeyEvent[];
  published_at: string | null;
}

// --- Spieler-Feedback (Testphase) ---
export type FeedbackCategory = 'bug' | 'idea' | 'other';

/** Body fuer POST /api/feedback. `page` wird vom Frontend automatisch gesetzt. */
export interface FeedbackRequest {
  category: FeedbackCategory;
  message: string;
  page?: string | null;
}

// --- Die erwachende Galaxie (Welle 4) ---
/** Aggressions-Stufe der Galaxie. Steuert Farbe/Label des Barometers. */
export type AwakeningLevelStatus = 'peaceful' | 'tense' | 'war' | 'apocalypse';

/** Ein Status-Band (Achse/Schwelle) des Aggressions-Barometers. */
export interface AwakeningBand {
  status: AwakeningLevelStatus;
  min: number;
}

/** Ein Stundenpunkt des 24h-Aggressionsverlaufs (fuer die Sparkline). */
export interface AggressionPoint {
  hour: string | null;
  level: number;
  status: AwakeningLevelStatus;
  combat_count: number;
  total_debris: number;
  unique_attackers: number;
}

/** „Der Erwachte" — der serverweite Waechter, wenn er aktiv ist. */
export interface AwakeningWarden {
  status: string; // 'active', wenn er gerade die Galaxie bedroht
  /** Standort als "g:s:p"-String (null, falls unbekannt). */
  coords: string | null;
  aggression_level: number;
  spawned_at: string | null;
  expires_at: string | null;
  /** Flotten-Andeutung: Schiffstyp -> Anzahl. */
  fleet: Record<string, number>;
  participants: number;
}

/** Antwort von GET /api/awakening/status (read-only, fuers Dashboard). */
export interface AwakeningStatus {
  enabled: boolean;
  level: number;
  status: AwakeningLevelStatus;
  threshold: number;
  combat_count: number;
  total_debris: number;
  unique_attackers: number;
  status_bands: AwakeningBand[];
  warden: AwakeningWarden | null;
  history: AggressionPoint[];
}

// --- Welle 5: Wandernde Galaxie / Konjunktions-Fenster ---

/**
 * Ein Konjunktions-Eintrag: eine Route (Quell-/Zielsystem g:s), deren Distanz
 * gerade durch eine Konjunktion verkuerzt (oder selten verlaengert) ist.
 * `discount_pct` positiv = guenstiger/schneller, negativ = Aufschlag.
 */
export interface Conjunction {
  /** Quellsystem als "g:s". */
  from: string;
  /** Zielsystem als "g:s". */
  to: string;
  from_coords: { galaxy: number; system: number };
  to_coords: { galaxy: number; system: number };
  /** Distanz-Faktor (< 1 = kuerzer). */
  factor: number;
  /** Rabatt in % (positiv = guenstiger/schneller, negativ = Aufschlag). */
  discount_pct: number;
  active: boolean;
  /** Bei aktivem Fenster: wann es endet (ISO). */
  ends_at?: string | null;
  /** Bei kommendem Fenster: wann das naechste Fenster startet (ISO). */
  next_at?: string;
  /** Bei kommendem Fenster: Beginn des Fensters (ISO, = next_at minus halbe Fensterbreite). */
  starts_at?: string;
}

/** Antwort von GET /api/conjunctions (aktive + kommende Fenster fuers Timing). */
export interface ConjunctionInfo {
  enabled: boolean;
  /** Server-Jetzt (ISO) — nur wenn aktiviert. */
  now?: string;
  /** Betrachteter Nachbar-Radius (Systeme) — nur wenn aktiviert. */
  radius?: number;
  active: Conjunction[];
  upcoming: Conjunction[];
}
