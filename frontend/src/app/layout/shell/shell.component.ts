import { ChangeDetectionStrategy, Component, OnInit, computed, inject, signal } from '@angular/core';
import { RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { GameStateService } from '../../core/services/game-state.service';
import { ShortNumberPipe } from '../../shared/pipes/short-number.pipe';
import { RESOURCE_META } from '../../core/models/display';
import { shellStyles } from './shell.styles';

interface NavItem {
  path: string;
  label: string;
  glyph: string;
}

@Component({
  selector: 'app-shell',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, RouterLink, RouterLinkActive, ShortNumberPipe],
  template: `
    <div class="shell">
      <!-- Topbar: Ressourcen + Planet + Spieler -->
      <header class="topbar">
        <div class="topbar-left">
          <button class="burger btn-ghost btn btn-sm" type="button" (click)="toggleNav()">☰</button>
          <a routerLink="/dashboard" class="logo">✦ UNIVERSE</a>
        </div>

        <div class="res-bar">
          @for (r of resourceRows(); track r.key) {
            <div
              class="res tip"
              [attr.data-tip]="r.tip"
              [class.full]="r.pct >= 100"
            >
              <img class="res-icon" src="assets/img/resources/{{ r.key }}.png" alt="" />
              <div class="res-meta">
                <span class="res-amount mono">{{ r.amount | shortNumber }}</span>
                <div class="bar" [class.full]="r.pct >= 100">
                  <span class="fill" [style.width.%]="r.pct"></span>
                </div>
              </div>
              <span class="res-rate mono" [class.neg]="r.rate < 0"
                >{{ r.rate >= 0 ? '+' : '' }}{{ r.rate | shortNumber }}/h</span
              >
            </div>
          }
          <div class="res energy tip" [attr.data-tip]="energyTip()">
            <img class="res-icon" src="assets/img/resources/energy.png" alt="" />
            <span class="res-amount mono" [class.neg]="energyBalance() < 0">{{
              energyBalance() | shortNumber
            }}</span>
          </div>
        </div>

        <div class="topbar-right">
          @if (planets().length) {
            <select
              class="planet-select"
              [value]="state.activePlanetId()"
              (change)="onPlanetChange($event)"
            >
              @for (p of planets(); track p.id) {
                <option [value]="p.id">
                  {{ p.name }} [{{ p.galaxy }}:{{ p.system }}:{{ p.position }}]
                </option>
              }
            </select>
          }
          <span class="player muted">{{ player()?.display_name }}</span>
          <button class="btn btn-ghost btn-sm" type="button" (click)="logout()">Logout</button>
        </div>
      </header>

      <!-- Angriffswarnung -->
      @if (state.attackAlerts().length) {
        <div class="attack-banner">
          ⚠ Eingehender Angriff auf {{ state.attackAlerts()[0].location }} — Fleetsave pruefen!
        </div>
      }

      <div class="body">
        <!-- Navigation -->
        <nav class="sidenav" [class.open]="navOpen()">
          @for (item of nav; track item.path) {
            <a
              class="nav-link"
              [routerLink]="item.path"
              routerLinkActive="active"
              (click)="closeNav()"
            >
              <span class="nav-glyph">{{ item.glyph }}</span>
              <span class="nav-label">{{ item.label }}</span>
              @if (item.path === '/transmissions' && state.unreadTransmissions() > 0) {
                <span class="badge">{{ state.unreadTransmissions() }}</span>
              }
            </a>
          }
        </nav>
        @if (navOpen()) {
          <div class="scrim" (click)="closeNav()"></div>
        }

        <main class="content">
          <router-outlet />
        </main>
      </div>
    </div>
  `,
  styles: [shellStyles],
})
export class ShellComponent implements OnInit {
  protected readonly state = inject(GameStateService);
  private readonly auth = inject(AuthService);

  protected readonly planets = this.state.planets;
  protected readonly player = this.auth.player;
  protected readonly navOpen = signal(false);

  protected readonly nav: NavItem[] = [
    { path: '/dashboard', label: 'Dashboard', glyph: '🛰️' },
    { path: '/buildings', label: 'Gebaeude', glyph: '🏗️' },
    { path: '/research', label: 'Forschung', glyph: '🔬' },
    { path: '/techtree', label: 'Techbaum', glyph: '🌳' },
    { path: '/shipyard', label: 'Werft', glyph: '🛠️' },
    { path: '/fleet', label: 'Flotte', glyph: '🚀' },
    { path: '/galaxy', label: 'Galaxie', glyph: '🌌' },
    { path: '/commanders', label: 'Kommandozentrale', glyph: '🎖️' },
    { path: '/transmissions', label: 'Postfach', glyph: '📡' },
  ];

  protected readonly resourceRows = computed(() => {
    const res = this.state.activePlanet()?.resources;
    const keys: ('metal' | 'crystal' | 'deuterium')[] = ['metal', 'crystal', 'deuterium'];
    return keys.map((key) => {
      const pool = res?.[key];
      const amount = pool?.amount ?? 0;
      const capacity = pool?.capacity ?? 0;
      const rate = pool?.rate ?? 0;
      const pct = capacity > 0 ? Math.min(100, (amount / capacity) * 100) : 0;
      return {
        key,
        glyph: RESOURCE_META[key].glyph,
        amount,
        rate,
        pct,
        tip: `${RESOURCE_META[key].label}\n${Math.floor(amount)} / ${Math.floor(capacity)}\nRate: ${rate.toFixed(0)}/h`,
      };
    });
  });

  protected readonly energyBalance = computed(
    () => this.state.activePlanet()?.resources?.energy?.balance ?? 0,
  );

  protected readonly energyTip = computed(() => {
    const e = this.state.activePlanet()?.resources?.energy;
    if (!e) {
      return 'Energie';
    }
    return `Energie\nProduktion: ${e.produced.toFixed(0)}\nVerbrauch: ${e.consumed.toFixed(0)}\nFaktor: ${(e.factor * 100).toFixed(0)}%`;
  });

  ngOnInit(): void {
    void this.state.bootstrap();
  }

  onPlanetChange(event: Event): void {
    const id = (event.target as HTMLSelectElement).value;
    void this.state.selectPlanet(id);
  }

  toggleNav(): void {
    this.navOpen.update((v) => !v);
  }

  closeNav(): void {
    this.navOpen.set(false);
  }

  logout(): void {
    this.state.reset();
    this.auth.logout();
    window.location.href = '/login';
  }
}
