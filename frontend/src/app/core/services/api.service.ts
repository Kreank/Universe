import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  AbilityCatalog,
  BuildingsResponse,
  CombatReport,
  Commander,
  CommanderBonus,
  CommanderDetail,
  CommanderTrainResponse,
  DecisionChoice,
  DecisionResponse,
  FeedbackRequest,
  Fleet,
  IncomingAttack,
  FleetSendRequest,
  GalaxyResponse,
  GalaxyTarget,
  Planet,
  PlanetDetail,
  RankingResponse,
  ResearchResponse,
  ResearchStartResponse,
  ShipyardBuildRequest,
  ShipyardBuildResponse,
  ShipyardResponse,
  EscortOffer,
  PhalanxScanResult,
  SendMessageRequest,
  StationedFleet,
  SpanInfo,
  TradeIndex,
  TradePartner,
  TradeProfile,
  Transmission,
  UpgradeResponse,
  DemolishResponse,
  MegastructureListResponse,
  Routine,
  RoutineListResponse,
  RoutineWriteRequest,
  AllianceResponse,
  AllianceOverview,
  AllianceStation,
} from '../models/api.models';

/**
 * Duenne, typsichere Huelle ueber alle REST-Endpunkte aus
 * `shared/api-contract.md`. Der Auth-Interceptor haengt das Bearer-Token an.
 */
@Injectable({ providedIn: 'root' })
export class ApiService {
  private readonly http = inject(HttpClient);

  // --- Planet & Wirtschaft ---
  getPlanets(): Observable<Planet[]> {
    return this.http.get<Planet[]>('/api/planets');
  }

  getPlanet(planetId: string): Observable<PlanetDetail> {
    return this.http.get<PlanetDetail>(`/api/planets/${planetId}`);
  }

  // --- Gebaeude ---
  getBuildings(planetId: string): Observable<BuildingsResponse> {
    return this.http.get<BuildingsResponse>(`/api/planets/${planetId}/buildings`);
  }

  upgradeBuilding(planetId: string, type: string): Observable<UpgradeResponse> {
    return this.http.post<UpgradeResponse>(
      `/api/planets/${planetId}/buildings/${type}/upgrade`,
      {},
    );
  }

  demolishBuilding(planetId: string, type: string): Observable<DemolishResponse> {
    return this.http.post<DemolishResponse>(
      `/api/planets/${planetId}/buildings/${type}/demolish`,
      {},
    );
  }

  /** Bricht den laufenden Ausbau dieses Gebaeudes ab (voller Ressourcen-Refund). */
  cancelBuilding(planetId: string, type: string): Observable<UpgradeResponse> {
    return this.http.post<UpgradeResponse>(
      `/api/planets/${planetId}/buildings/${type}/cancel`,
      {},
    );
  }

  // --- Forschung ---
  getResearch(): Observable<ResearchResponse> {
    return this.http.get<ResearchResponse>('/api/research');
  }

  startResearch(type: string, planetId: string): Observable<ResearchStartResponse> {
    return this.http.post<ResearchStartResponse>(`/api/research/${type}/start`, {
      planet_id: planetId,
    });
  }

  /** Bricht die laufende Forschung ab (voller Ressourcen-Refund auf die Heimatwelt). */
  cancelResearch(): Observable<ResearchStartResponse> {
    return this.http.post<ResearchStartResponse>('/api/research/cancel', {});
  }

  // --- Megastrukturen ---
  getMegastructures(): Observable<MegastructureListResponse> {
    return this.http.get<MegastructureListResponse>('/api/megastructures');
  }

  buildMegastructure(type: string): Observable<unknown> {
    return this.http.post(`/api/megastructures/${type}/build`, {});
  }

  // --- Werft ---
  getShipyard(planetId: string): Observable<ShipyardResponse> {
    return this.http.get<ShipyardResponse>(`/api/planets/${planetId}/shipyard`);
  }

  buildShips(planetId: string, body: ShipyardBuildRequest): Observable<ShipyardBuildResponse> {
    return this.http.post<ShipyardBuildResponse>(`/api/planets/${planetId}/shipyard/build`, body);
  }

  /** Bricht einen Werft-Auftrag ab (Refund + Nachruecken der Schlange). */
  cancelShipyardItem(planetId: string, itemId: string): Observable<ShipyardBuildResponse> {
    return this.http.post<ShipyardBuildResponse>(
      `/api/planets/${planetId}/shipyard/${itemId}/cancel`,
      {},
    );
  }

  // --- Flotte ---
  getFleets(): Observable<Fleet[]> {
    return this.http.get<Fleet[]>('/api/fleets');
  }

  sendFleet(body: FleetSendRequest): Observable<Fleet> {
    return this.http.post<Fleet>('/api/fleets/send', body);
  }

  recallFleet(fleetId: string): Observable<Fleet> {
    return this.http.post<Fleet>(`/api/fleets/${fleetId}/recall`, {});
  }

  /** Sprungtor: Schiffe sofort zwischen zwei eigenen Monden versetzen (kein Flug). */
  jumpFleet(body: {
    from_moon_id: string;
    to_moon_id: string;
    ships: Record<string, number>;
  }): Observable<{ ok: boolean; next_jump_at: string }> {
    return this.http.post<{ ok: boolean; next_jump_at: string }>('/api/fleets/jump', body);
  }

  getIncomingAttacks(): Observable<IncomingAttack[]> {
    return this.http.get<IncomingAttack[]>('/api/incoming-attacks');
  }

  getGalaxyTargets(): Observable<GalaxyTarget[]> {
    return this.http.get<GalaxyTarget[]>('/api/galaxy/targets');
  }

  getGalaxy(galaxy: number, system: number): Observable<GalaxyResponse> {
    return this.http.get<GalaxyResponse>(`/api/galaxy/${galaxy}/${system}`);
  }

  /** Oeffentlicher, immer sichtbarer globaler Handelskurs (Handelszentren). */
  getTradeIndex(): Observable<TradeIndex> {
    return this.http.get<TradeIndex>('/api/trade/index');
  }

  getTradeProfile(): Observable<TradeProfile> {
    return this.http.get<TradeProfile>('/api/trade/profile');
  }

  putTradeProfile(body: TradeProfile): Observable<TradeProfile> {
    return this.http.put<TradeProfile>('/api/trade/profile', body);
  }

  getTradePartners(): Observable<TradePartner[]> {
    return this.http.get<TradePartner[]>('/api/trade/partners');
  }

  sendMessage(body: SendMessageRequest): Observable<Transmission> {
    return this.http.post<Transmission>('/api/messages', body);
  }

  /** Sensorphalanx-Scan: Flottenbewegungen zu/von einer Koordinate (ETA fuers Timing). */
  phalanxScan(galaxy: number, system: number, position: number): Observable<PhalanxScanResult> {
    return this.http.post<PhalanxScanResult>('/api/phalanx/scan', { galaxy, system, position });
  }

  getStationed(): Observable<StationedFleet[]> {
    return this.http.get<StationedFleet[]>('/api/stationed');
  }

  patrolHome(planetId: string, body: { ships: Record<string, number>; radius: number }): Observable<StationedFleet> {
    return this.http.post<StationedFleet>(`/api/planets/${planetId}/patrol`, body);
  }

  recallStation(id: string): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`/api/stationed/${id}/recall`, {});
  }

  setInterceptMode(id: string, body: { enabled: boolean; radius: number }): Observable<StationedFleet> {
    return this.http.put<StationedFleet>(`/api/stationed/${id}/intercept`, body);
  }

  setEscortOffer(id: string, body: { enabled: boolean; radius: number; fee_pct: number }): Observable<StationedFleet> {
    return this.http.put<StationedFleet>(`/api/stationed/${id}/escort`, body);
  }

  getEscortOffers(): Observable<EscortOffer[]> {
    return this.http.get<EscortOffer[]>('/api/escort/offers');
  }

  // --- Commander ---
  getCommanders(): Observable<Commander[]> {
    return this.http.get<Commander[]>('/api/commanders');
  }

  getCommander(id: string): Observable<CommanderDetail> {
    return this.http.get<CommanderDetail>(`/api/commanders/${id}`);
  }

  trainCommander(
    planetId: string,
    specialization?: string | null,
    focus?: string | null,
    tier?: string | null,
  ): Observable<CommanderTrainResponse> {
    return this.http.post<CommanderTrainResponse>('/api/commanders/train', {
      planet_id: planetId,
      specialization: specialization ?? null,
      focus: focus ?? null,
      tier: tier ?? null,
    });
  }

  getBonusPreview(
    specialization: string,
    focus: string | null,
    grade?: string | null,
  ): Observable<CommanderBonus[]> {
    let q = `?specialization=${encodeURIComponent(specialization)}`;
    if (focus) {
      q += `&focus=${encodeURIComponent(focus)}`;
    }
    if (grade) {
      q += `&grade=${encodeURIComponent(grade)}`;
    }
    return this.http.get<CommanderBonus[]>(`/api/commanders/bonus-preview${q}`);
  }

  getSpan(): Observable<SpanInfo> {
    return this.http.get<SpanInfo>('/api/player/span');
  }

  getAbilityCatalog(): Observable<AbilityCatalog> {
    return this.http.get<AbilityCatalog>('/api/commanders/ability-catalog');
  }

  trainAbility(commanderId: string, key: string): Observable<CommanderDetail> {
    return this.http.post<CommanderDetail>(`/api/commanders/${commanderId}/abilities/train`, { key });
  }

  forgetAbility(commanderId: string, key: string): Observable<CommanderDetail> {
    return this.http.post<CommanderDetail>(`/api/commanders/${commanderId}/abilities/forget`, { key });
  }

  /** Charakter-Zucht: Traits neu wuerfeln ('reroll') oder einen gezielt ersetzen ('replace'). */
  retrainTraits(
    commanderId: string,
    mode: 'reroll' | 'replace',
    trait?: string,
    drop?: string,
  ): Observable<CommanderDetail> {
    return this.http.post<CommanderDetail>(`/api/commanders/${commanderId}/retrain-traits`, {
      mode,
      trait,
      drop,
    });
  }

  /** Gouverneur eines Planeten setzen (commanderId) oder entfernen (null). */
  setGovernor(planetId: string, commanderId: string | null): Observable<{ ok: boolean }> {
    return this.http.put<{ ok: boolean }>(`/api/planets/${planetId}/governor`, {
      commander_id: commanderId,
    });
  }

  // --- Postfach / Funksprueche ---
  getTransmissions(unread = false): Observable<Transmission[]> {
    const query = unread ? '?unread=true' : '';
    return this.http.get<Transmission[]>(`/api/transmissions${query}`);
  }

  markTransmissionRead(id: string): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`/api/transmissions/${id}/read`, {});
  }

  decideTransmission(id: string, choice: DecisionChoice): Observable<DecisionResponse> {
    return this.http.post<DecisionResponse>(`/api/transmissions/${id}/decide`, { choice });
  }

  deleteTransmission(id: string): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(`/api/transmissions/${id}`);
  }

  deleteReadTransmissions(): Observable<{ ok: boolean }> {
    return this.http.delete<{ ok: boolean }>(`/api/transmissions/read`);
  }

  /** KI-Berater anfordern (Phase 5): der Rat trifft kurz darauf als Funkspruch im Postfach ein. */
  requestAdvisor(): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`/api/advisor`, {});
  }

  // --- Combat-Report ---
  getCombatReport(id: string): Observable<CombatReport> {
    return this.http.get<CombatReport>(`/api/combat-reports/${id}`);
  }

  /** Was-waere-wenn-Schlacht: simuliert ohne Spielstand-Effekt (nutzt eigene Forschung). */
  simulateCombat(body: {
    attacker_ships: Record<string, number>;
    defender_ships: Record<string, number>;
    defender_defenses: Record<string, number>;
    seed?: number | null;
  }): Observable<CombatReport> {
    return this.http.post<CombatReport>('/api/combat/simulate', body);
  }

  // --- Rangliste ---
  getRanking(limit = 100): Observable<RankingResponse> {
    return this.http.get<RankingResponse>(`/api/ranking?limit=${limit}`);
  }

  // --- Feedback (Testphase) ---
  submitFeedback(body: FeedbackRequest): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>('/api/feedback', body);
  }

  // --- Routinen (automatisierte Farm-Routen) ---
  getRoutines(): Observable<RoutineListResponse> {
    return this.http.get<RoutineListResponse>('/api/routines');
  }

  createRoutine(body: RoutineWriteRequest): Observable<Routine> {
    return this.http.post<Routine>('/api/routines', body);
  }

  updateRoutine(id: string, body: RoutineWriteRequest): Observable<Routine> {
    return this.http.patch<Routine>(`/api/routines/${id}`, body);
  }

  deleteRoutine(id: string): Observable<void> {
    return this.http.delete<void>(`/api/routines/${id}`);
  }

  resumeRoutine(id: string): Observable<Routine> {
    return this.http.post<Routine>(`/api/routines/${id}/resume`, {});
  }

  // --- Allianz ---
  getAlliance(): Observable<AllianceResponse> {
    return this.http.get<AllianceResponse>('/api/alliance');
  }

  createAlliance(body: { name: string; tag: string }): Observable<AllianceOverview> {
    return this.http.post<AllianceOverview>('/api/alliance', body);
  }

  disbandAlliance(): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>('/api/alliance/disband', {});
  }

  /** Einladung per Anzeigename ODER Spieler-ID (Offizier+). */
  inviteToAlliance(body: { name?: string; player_id?: string }): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>('/api/alliance/invite', body);
  }

  acceptInvite(allianceId: string): Observable<AllianceOverview> {
    return this.http.post<AllianceOverview>(`/api/alliance/invites/${allianceId}/accept`, {});
  }

  declineInvite(allianceId: string): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>(`/api/alliance/invites/${allianceId}/decline`, {});
  }

  leaveAlliance(): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>('/api/alliance/leave', {});
  }

  kickMember(playerId: string): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>('/api/alliance/kick', { player_id: playerId });
  }

  setMemberRole(playerId: string, role: 'member' | 'officer'): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>('/api/alliance/role', { player_id: playerId, role });
  }

  transferLeadership(playerId: string): Observable<{ ok: boolean }> {
    return this.http.post<{ ok: boolean }>('/api/alliance/transfer', { player_id: playerId });
  }

  depositToAlliance(body: {
    planet_id: string;
    metal: number;
    crystal: number;
    deuterium: number;
  }): Observable<unknown> {
    return this.http.post('/api/alliance/deposit', body);
  }

  researchAlliance(tree: string, node: string): Observable<unknown> {
    return this.http.post('/api/alliance/research', { tree, node });
  }

  resetAllianceResearch(): Observable<unknown> {
    return this.http.post('/api/alliance/research/reset', {});
  }

  buildAllianceStation(body: {
    galaxy: number;
    system: number;
    position: number;
  }): Observable<AllianceStation> {
    return this.http.post<AllianceStation>('/api/alliance/station', body);
  }

  refuelStation(id: string, deuterium: number): Observable<unknown> {
    return this.http.post(`/api/alliance/station/${id}/refuel`, { deuterium });
  }

  upgradeStation(id: string): Observable<unknown> {
    return this.http.post(`/api/alliance/station/${id}/upgrade`, {});
  }
}
