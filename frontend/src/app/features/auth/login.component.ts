import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { authPanelStyles } from './auth.styles';

@Component({
  selector: 'app-login',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="auth-wrap">
      <div class="auth-card glass">
        <div class="brand">
          <span class="logo">✦</span>
          <div>
            <h1>UNIVERSE</h1>
            <p class="muted tagline">Kommandozentrale · Anmeldung</p>
          </div>
        </div>

        <form (ngSubmit)="submit()">
          <div class="field">
            <label for="email">E-Mail</label>
            <input id="email" name="email" type="email" [(ngModel)]="email" autocomplete="email" required />
          </div>
          <div class="field">
            <label for="pw">Passwort</label>
            <input
              id="pw"
              name="pw"
              type="password"
              [(ngModel)]="password"
              autocomplete="current-password"
              required
            />
          </div>

          @if (error()) {
            <p class="error">{{ error() }}</p>
          }

          <button class="btn btn-primary full" type="submit" [disabled]="loading()">
            {{ loading() ? 'Verbinde…' : 'Einloggen' }}
          </button>
        </form>

        <p class="switch muted">
          Noch kein Imperium? <a routerLink="/register">Konto erstellen</a>
        </p>
      </div>
    </div>
  `,
  styles: [authPanelStyles],
})
export class LoginComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  email = '';
  password = '';
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  submit(): void {
    if (!this.email || !this.password) {
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.auth.login({ email: this.email, password: this.password }).subscribe({
      next: () => {
        this.loading.set(false);
        void this.router.navigate(['/dashboard']);
      },
      error: (err) => {
        this.loading.set(false);
        this.error.set(err?.error?.detail ?? 'Anmeldung fehlgeschlagen.');
      },
    });
  }
}
