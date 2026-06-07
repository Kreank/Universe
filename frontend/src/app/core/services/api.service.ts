import { Injectable, inject } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable } from 'rxjs';
import {
  BuildingsResponse,
  CombatReport,
  Commander,
  CommanderBonus,
  CommanderDetail,
  CommanderTrainResponse,
  DecisionChoice,
  DecisionResponse,
  Fleet,
  FleetSendRequest,
  GalaxyResponse,
  GalaxyTarget,
  Planet,
  PlanetDetail,
  ResearchResponse,
  ResearchStartResponse,
  ShipyardBuildRequest,
  ShipyardBuildResponse,
  ShipyardResponse,
  SpanInfo,
  Transmission,
  UpgradeResponse,
  DemolishResponse,
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

  // --- Forschung ---
  getResearch(): Observable<ResearchResponse> {
    return this.http.get<ResearchResponse>('/api/research');
  }

  startResearch(type: string, planetId: string): Observable<ResearchStartResponse> {
    return this.http.post<ResearchStartResponse>(`/api/research/${type}/start`, {
      planet_id: planetId,
    });
  }

  // --- Werft ---
  getShipyard(planetId: string): Observable<ShipyardResponse> {
    return this.http.get<ShipyardResponse>(`/api/planets/${planetId}/shipyard`);
  }

  buildShips(planetId: string, body: ShipyardBuildRequest): Observable<ShipyardBuildResponse> {
    return this.http.post<ShipyardBuildResponse>(`/api/planets/${planetId}/shipyard/build`, body);
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

  getGalaxyTargets(): Observable<GalaxyTarget[]> {
    return this.http.get<GalaxyTarget[]>('/api/galaxy/targets');
  }

  getGalaxy(galaxy: number, system: number): Observable<GalaxyResponse> {
    return this.http.get<GalaxyResponse>(`/api/galaxy/${galaxy}/${system}`);
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
  ): Observable<CommanderTrainResponse> {
    return this.http.post<CommanderTrainResponse>('/api/commanders/train', {
      planet_id: planetId,
      specialization: specialization ?? null,
      focus: focus ?? null,
    });
  }

  getBonusPreview(specialization: string, focus: string | null): Observable<CommanderBonus[]> {
    let q = `?specialization=${encodeURIComponent(specialization)}`;
    if (focus) {
      q += `&focus=${encodeURIComponent(focus)}`;
    }
    return this.http.get<CommanderBonus[]>(`/api/commanders/bonus-preview${q}`);
  }

  getSpan(): Observable<SpanInfo> {
    return this.http.get<SpanInfo>('/api/player/span');
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

  // --- Combat-Report ---
  getCombatReport(id: string): Observable<CombatReport> {
    return this.http.get<CombatReport>(`/api/combat-reports/${id}`);
  }
}
