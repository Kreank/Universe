import { Injectable, computed, inject, signal } from '@angular/core';
import { HttpClient } from '@angular/common/http';
import { Observable, tap } from 'rxjs';
import { AuthResponse, LoginRequest, Player, RegisterRequest } from '../models/api.models';

const TOKEN_KEY = 'universe.token';
const PLAYER_KEY = 'universe.player';

/**
 * Verwaltet Authentifizierung und Token-Persistenz in localStorage.
 * Stellt reaktive Signale fuer den eingeloggten Spieler bereit.
 */
@Injectable({ providedIn: 'root' })
export class AuthService {
  private readonly http = inject(HttpClient);

  private readonly _token = signal<string | null>(this.readToken());
  private readonly _player = signal<Player | null>(this.readPlayer());

  readonly token = this._token.asReadonly();
  readonly player = this._player.asReadonly();
  readonly isAuthenticated = computed(() => this._token() !== null);

  register(body: RegisterRequest): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>('/api/auth/register', body)
      .pipe(tap((res) => this.persist(res)));
  }

  login(body: LoginRequest): Observable<AuthResponse> {
    return this.http
      .post<AuthResponse>('/api/auth/login', body)
      .pipe(tap((res) => this.persist(res)));
  }

  /** Laedt das aktuelle Spielerprofil (GET /api/auth/me). */
  refreshMe(): Observable<Player> {
    return this.http.get<Player>('/api/auth/me').pipe(tap((p) => this.setPlayer(p)));
  }

  logout(): void {
    this._token.set(null);
    this._player.set(null);
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(PLAYER_KEY);
  }

  getToken(): string | null {
    return this._token();
  }

  private persist(res: AuthResponse): void {
    this._token.set(res.token);
    localStorage.setItem(TOKEN_KEY, res.token);
    this.setPlayer(res.player);
  }

  private setPlayer(player: Player): void {
    this._player.set(player);
    localStorage.setItem(PLAYER_KEY, JSON.stringify(player));
  }

  private readToken(): string | null {
    return localStorage.getItem(TOKEN_KEY);
  }

  private readPlayer(): Player | null {
    const raw = localStorage.getItem(PLAYER_KEY);
    if (!raw) {
      return null;
    }
    try {
      return JSON.parse(raw) as Player;
    } catch {
      return null;
    }
  }
}
