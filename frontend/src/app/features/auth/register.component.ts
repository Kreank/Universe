import { ChangeDetectionStrategy, Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { Router, RouterLink } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { authPanelStyles } from './auth.styles';

@Component({
  selector: 'app-register',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [FormsModule, RouterLink],
  template: `
    <div class="auth-wrap">
      <div class="auth-card card">
        <div class="brand">
          <span class="logo">✦</span>
          <div>
            <h1>UNIVERSE</h1>
            <p class="muted tagline">Neues Imperium gruenden</p>
          </div>
        </div>

        <form (ngSubmit)="submit()">
          <div class="field">
            <label for="name">Anzeigename</label>
            <input id="name" name="name" type="text" [(ngModel)]="displayName" autocomplete="nickname" required />
          </div>
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
              autocomplete="new-password"
              required
            />
          </div>

          @if (error()) {
            <p class="error">{{ error() }}</p>
          }

          <button class="btn btn-primary full" type="submit" [disabled]="loading()">
            {{ loading() ? 'Erstelle…' : 'Imperium gruenden' }}
          </button>
        </form>

        <p class="switch muted">Schon dabei? <a routerLink="/login">Einloggen</a></p>
      </div>
    </div>
  `,
  styles: [authPanelStyles],
})
export class RegisterComponent {
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);

  displayName = '';
  email = '';
  password = '';
  readonly loading = signal(false);
  readonly error = signal<string | null>(null);

  submit(): void {
    if (!this.displayName || !this.email || !this.password) {
      return;
    }
    this.loading.set(true);
    this.error.set(null);
    this.auth
      .register({ display_name: this.displayName, email: this.email, password: this.password })
      .subscribe({
        next: () => {
          this.loading.set(false);
          void this.router.navigate(['/dashboard']);
        },
        error: (err) => {
          this.loading.set(false);
          this.error.set(err?.error?.detail ?? 'Registrierung fehlgeschlagen.');
        },
      });
  }
}
