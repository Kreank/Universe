import { Injectable, inject } from '@angular/core';
import { Observable, Subject, filter } from 'rxjs';
import { AuthService } from './auth.service';
import { WsClientSubscribe, WsMessage } from '../models/api.models';

/**
 * Verbindet `/ws?token=<jwt>` und stellt eingehende Nachrichten als RxJS-Subject
 * bereit. Komponenten subscriben gezielt per `on('transmission')` etc.
 * Reconnect mit Backoff; haelt Verbindung per Ping am Leben.
 */
@Injectable({ providedIn: 'root' })
export class WebSocketService {
  private readonly auth = inject(AuthService);
  private socket: WebSocket | null = null;
  private readonly messages$ = new Subject<WsMessage>();
  private reconnectAttempts = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private pingTimer: ReturnType<typeof setInterval> | null = null;
  private manualClose = false;

  /** Stream aller eingehenden Nachrichten. */
  get stream$(): Observable<WsMessage> {
    return this.messages$.asObservable();
  }

  /** Typsicherer Stream gefiltert auf einen Nachrichtentyp. */
  on<T extends WsMessage = WsMessage>(type: string): Observable<T> {
    return this.messages$.pipe(filter((m): m is T => m.type === type));
  }

  connect(): void {
    const token = this.auth.getToken();
    if (!token || this.socket) {
      return;
    }
    this.manualClose = false;
    const proto = window.location.protocol === 'https:' ? 'wss' : 'ws';
    const url = `${proto}://${window.location.host}/ws?token=${encodeURIComponent(token)}`;
    const socket = new WebSocket(url);
    this.socket = socket;

    socket.onopen = () => {
      this.reconnectAttempts = 0;
      this.startPing();
    };
    socket.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data as string) as WsMessage;
        if (data && typeof data.type === 'string') {
          this.messages$.next(data);
        }
      } catch {
        // unparsable frame ignorieren
      }
    };
    socket.onclose = () => {
      this.cleanupSocket();
      if (!this.manualClose) {
        this.scheduleReconnect();
      }
    };
    socket.onerror = () => {
      socket.close();
    };
  }

  /** Abonniert Updates fuer einen Planeten (Client→Server). */
  subscribePlanet(planetId: string): void {
    const msg: WsClientSubscribe = { type: 'subscribe', planet_id: planetId };
    this.send(msg);
  }

  send(payload: unknown): void {
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }

  disconnect(): void {
    this.manualClose = true;
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.cleanupSocket();
  }

  private startPing(): void {
    this.stopPing();
    this.pingTimer = setInterval(() => this.send({ type: 'ping' }), 30000);
  }

  private stopPing(): void {
    if (this.pingTimer) {
      clearInterval(this.pingTimer);
      this.pingTimer = null;
    }
  }

  private cleanupSocket(): void {
    this.stopPing();
    this.socket = null;
  }

  private scheduleReconnect(): void {
    if (!this.auth.getToken()) {
      return;
    }
    this.reconnectAttempts += 1;
    const delay = Math.min(30000, 1000 * 2 ** this.reconnectAttempts);
    this.reconnectTimer = setTimeout(() => this.connect(), delay);
  }
}
