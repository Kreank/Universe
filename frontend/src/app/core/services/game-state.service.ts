import { Injectable, computed, inject, signal } from '@angular/core';
import { Observable, firstValueFrom } from 'rxjs';
import { ApiService } from './api.service';
import { WebSocketService } from './websocket.service';
import { NotificationService } from './notification.service';
import { BalanceService } from './balance.service';
import {
  Commander,
  Fleet,
  Planet,
  PlanetDetail,
  SpanInfo,
  Transmission,
  WsAttackWarning,
  WsBuildComplete,
  WsFleetArrived,
  WsFleetReturned,
  WsResearchComplete,
  WsResourceTick,
  WsTransmission,
} from '../models/api.models';
import { BUILDING_META, TECH_META, metaFor } from '../models/display';

export interface AttackAlert {
  location: string;
  arriveAt: string;
  shipsTotal?: number;
  attackerName?: string;
}

/**
 * Zentraler reaktiver Spielzustand. Buendelt API-Ladevorgaenge und verteilt
 * Live-WebSocket-Updates an Signale, auf die alle Screens reagieren.
 */
@Injectable({ providedIn: 'root' })
export class GameStateService {
  private readonly api = inject(ApiService);
  private readonly ws = inject(WebSocketService);
  private readonly notify = inject(NotificationService);
  private readonly balance = inject(BalanceService);

  readonly planets = signal<Planet[]>([]);
  readonly activePlanetId = signal<string | null>(null);
  readonly activePlanet = signal<PlanetDetail | null>(null);
  /** Zeitstempel (ms), wann die Ressourcen von activePlanet zuletzt vom Backend kamen.
   * Basis fuer die sekundengenaue 1:1-Hochrechnung in der Ressourcen-Leiste (gleiche Formel
   * wie das Backend -> die Anzeige stimmt mit dem echten Bestand ueberein). */
  readonly resourcesAt = signal(0);
  readonly fleets = signal<Fleet[]>([]);
  readonly commanders = signal<Commander[]>([]);
  readonly span = signal<SpanInfo | null>(null);
  readonly transmissions = signal<Transmission[]>([]);
  readonly attackAlerts = signal<AttackAlert[]>([]);

  // Versions-Zaehler: zaehlen bei Fertigstellungs-WS-Events hoch, damit Feature-Seiten
  // (Gebaeude/Forschung/Werft) ihre Listen automatisch neu laden (ueber ihren load-effect).
  readonly buildingsVersion = signal(0);
  readonly researchVersion = signal(0);
  readonly shipyardVersion = signal(0);

  readonly unreadTransmissions = computed(
    () => this.transmissions().filter((t) => !t.read).length,
  );
  readonly pendingDecisions = computed(
    () => this.transmissions().filter((t) => t.requires_decision && !t.read).length,
  );

  private wired = false;

  /** Nach dem Login aufrufen: Verbindung + Erst-Daten + WS-Verdrahtung. */
  async bootstrap(): Promise<void> {
    this.ws.connect();
    this.wireWebSocket();
    await this.loadPlanets();
    void this.reloadFleets();
    void this.reloadCommanders();
    void this.reloadTransmissions();
    void this.reloadIncomingAttacks();
  }

  /** Offene NPC-Angriffe laden, damit das Cockpit sie auch nach Reload zeigt. */
  async reloadIncomingAttacks(): Promise<void> {
    try {
      const incoming = await this.firstValue(this.api.getIncomingAttacks());
      const seeded: AttackAlert[] = incoming.map((a) => ({
        location: `${a.target.galaxy}:${a.target.system}:${a.target.position}`,
        arriveAt: a.arrive_at,
        shipsTotal: a.ships_total,
        attackerName: a.attacker,
      }));
      this.attackAlerts.update((list) => {
        const known = new Set(list.map((x) => x.location));
        const merged = [...list];
        for (const alert of seeded) {
          if (!known.has(alert.location)) {
            merged.push(alert);
            known.add(alert.location);
          }
        }
        return merged;
      });
    } catch {
      // incoming-attacks optional
    }
  }

  async loadPlanets(): Promise<void> {
    const planets = await this.firstValue(this.api.getPlanets());
    this.planets.set(planets);
    if (!this.activePlanetId() && planets.length > 0) {
      const home = planets.find((p) => p.is_homeworld) ?? planets[0];
      await this.selectPlanet(home.id);
    }
  }

  /** Aktualisiert den Anzeigenamen eines Planeten in der Liste + (falls aktiv) im Detail. */
  updatePlanetName(planetId: string, name: string): void {
    this.planets.update((list) => list.map((p) => (p.id === planetId ? { ...p, name } : p)));
    const ap = this.activePlanet();
    if (ap && ap.id === planetId) {
      this.activePlanet.set({ ...ap, name });
    }
  }

  async selectPlanet(planetId: string): Promise<void> {
    this.activePlanetId.set(planetId);
    this.ws.subscribePlanet(planetId);
    await this.reloadActivePlanet();
  }

  async reloadActivePlanet(): Promise<void> {
    const id = this.activePlanetId();
    if (!id) {
      return;
    }
    const detail = await this.firstValue(this.api.getPlanet(id));
    this.activePlanet.set(detail);
    this.resourcesAt.set(Date.now());
  }

  async reloadFleets(): Promise<void> {
    this.fleets.set(await this.firstValue(this.api.getFleets()));
  }

  async reloadCommanders(): Promise<void> {
    this.commanders.set(await this.firstValue(this.api.getCommanders()));
    try {
      this.span.set(await this.firstValue(this.api.getSpan()));
    } catch {
      // span optional
    }
  }

  async reloadTransmissions(): Promise<void> {
    this.transmissions.set(await this.firstValue(this.api.getTransmissions()));
  }

  upsertTransmission(t: Transmission): void {
    this.transmissions.update((list) => {
      const idx = list.findIndex((x) => x.id === t.id);
      if (idx >= 0) {
        const copy = [...list];
        copy[idx] = t;
        return copy;
      }
      return [t, ...list];
    });
  }

  removeTransmission(id: string): void {
    this.transmissions.update((list) => list.filter((x) => x.id !== id));
  }

  removeReadTransmissions(): void {
    this.transmissions.update((list) => list.filter((x) => !x.read || x.requires_decision));
  }

  reset(): void {
    this.ws.disconnect();
    this.planets.set([]);
    this.activePlanetId.set(null);
    this.activePlanet.set(null);
    this.fleets.set([]);
    this.commanders.set([]);
    this.span.set(null);
    this.transmissions.set([]);
    this.attackAlerts.set([]);
  }

  private wireWebSocket(): void {
    if (this.wired) {
      return;
    }
    this.wired = true;

    this.ws.on<WsResourceTick>('resource_tick').subscribe((msg) => {
      if (msg.planet_id === this.activePlanetId()) {
        this.activePlanet.update((p) => (p ? { ...p, resources: msg.resources } : p));
        this.resourcesAt.set(Date.now());
      }
    });

    this.ws.on<WsBuildComplete>('build_complete').subscribe((msg) => {
      const label = metaFor(BUILDING_META, msg.building).label;
      this.notify.success('Bau abgeschlossen', `${label} ist jetzt Stufe ${msg.level}. Tippen zum Öffnen.`, '/buildings');
      void this.reloadActivePlanet();
      this.buildingsVersion.update((v) => v + 1);
    });

    this.ws.on<WsResearchComplete>('research_complete').subscribe((msg) => {
      const label = metaFor(TECH_META, msg.tech).label;
      this.notify.success('Forschung abgeschlossen', `${label} Stufe ${msg.level} erreicht. Tippen zum Öffnen.`, '/research');
      void this.reloadActivePlanet();
      this.researchVersion.update((v) => v + 1);
    });

    this.ws.on<{ type: string }>('shipyard_complete').subscribe(() => {
      this.notify.success('Werft: Bau abgeschlossen', 'Neue Einheiten stehen bereit. Tippen zum Öffnen.', '/shipyard');
      void this.reloadActivePlanet();
      this.shipyardVersion.update((v) => v + 1);
    });

    this.ws.on<WsFleetArrived>('fleet_arrived').subscribe((msg) => {
      this.notify.info('Flotte angekommen', `Mission "${msg.mission}" hat ihr Ziel erreicht. Tippen für die Flotten.`, '/fleet');
      void this.reloadFleets();
    });

    this.ws.on<WsFleetReturned>('fleet_returned').subscribe(() => {
      this.notify.info('Flotte zurueck', 'Eine Flotte ist zur Basis zurueckgekehrt. Tippen für die Flotten.', '/fleet');
      void this.reloadFleets();
    });

    this.ws.on<WsTransmission>('transmission').subscribe((msg) => {
      this.upsertTransmission(msg.transmission);
      this.notify.push(
        'transmission',
        'Eingehende Transmission',
        msg.transmission.subject,
        msg.transmission.id,
      );
    });

    this.ws.on<WsAttackWarning>('attack_warning').subscribe((msg) => {
      this.attackAlerts.update((list) => {
        if (list.some((x) => x.location === msg.location)) {
          return list;
        }
        return [
          {
            location: msg.location,
            arriveAt: msg.arrive_at,
            shipsTotal: msg.ships_total,
            attackerName: msg.attacker_name,
          },
          ...list,
        ];
      });
      this.notify.warning('Eingehender Angriff', `Ziel: ${msg.location}. Fleetsave pruefen! Tippen für die Flotten.`, '/fleet');
    });
  }

  private firstValue<T>(obs: Observable<T>): Promise<T> {
    return firstValueFrom(obs);
  }
}
