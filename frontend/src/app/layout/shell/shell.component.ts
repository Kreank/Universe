import { ChangeDetectionStrategy, Component, OnDestroy, OnInit, computed, inject, signal } from '@angular/core';
import { DOCUMENT } from '@angular/common';
import { NavigationEnd, Router, RouterLink, RouterLinkActive, RouterOutlet } from '@angular/router';
import { AuthService } from '../../core/services/auth.service';
import { GameStateService } from '../../core/services/game-state.service';
import { ShortNumberPipe } from '../../shared/pipes/short-number.pipe';
import { RESOURCE_META } from '../../core/models/display';
import { shellStyles } from './shell.styles';

interface NavItem {
  path: string;
  label: string;
  glyph: string;
  /** Serviertes Nav-Icon; faellt bei Ladefehler auf den Glyph zurueck. */
  icon: string;
}

interface NavGroup {
  label: string;
  items: NavItem[];
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
                <span class="res-amount mono">{{ r.display }}</span>
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
                  {{ p.planet_type === 'moon' ? '🌑 ' : '' }}{{ p.name }} [{{ p.galaxy }}:{{ p.system }}:{{ p.position }}]
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
        <!-- Navigation: nach Domaenen gruppiert (Desktop-Sidebar / Mobile-Drawer via "Mehr") -->
        <nav class="sidenav" [class.open]="navOpen()">
          <div class="drawer-head">
            <span class="drawer-title">Navigation</span>
            <button class="btn btn-ghost btn-sm drawer-close" type="button" (click)="closeNav()">✕</button>
          </div>
          @for (group of navGroups; track group.label) {
            <div class="nav-group">
              <div class="nav-group-label">{{ group.label }}</div>
              @for (item of group.items; track item.path) {
                <a
                  class="nav-link"
                  [routerLink]="item.path"
                  routerLinkActive="active"
                  (click)="closeNav()"
                >
                  <span class="nav-glyph">
                    <img class="nav-ico" [src]="item.icon" alt="" (error)="onNavIconError($event)" />
                    <span class="nav-glyph-fallback">{{ item.glyph }}</span>
                  </span>
                  <span class="nav-label">{{ item.label }}</span>
                  @if (item.path === '/transmissions' && state.unreadTransmissions() > 0) {
                    <span class="badge">{{ state.unreadTransmissions() }}</span>
                  }
                </a>
              }
            </div>
          }
        </nav>
        @if (navOpen()) {
          <div class="scrim" (click)="closeNav()"></div>
        }

        <main class="content">
          <router-outlet />
        </main>

        <!-- Kolonien-Leiste (Desktop) -->
        @if (planets().length) {
          <aside class="colony-rail">
            <div class="rail-title">Kolonien</div>
            @for (p of planets(); track p.id) {
              <button
                type="button"
                class="colony"
                [class.active]="p.id === state.activePlanetId()"
                (click)="selectColony(p.id)"
              >
                <span class="colony-name">{{ p.planet_type === 'moon' ? '🌑 ' : '' }}{{ p.name }}</span>
                <span class="colony-coords mono">[{{ p.galaxy }}:{{ p.system }}:{{ p.position }}]</span>
              </button>
            }
          </aside>
        }
      </div>

      <!-- Mobile: persistente Bottom-Tab-Bar (4 Kern-Screens + "Mehr"-Drawer) -->
      <nav class="bottomnav">
        @for (item of bottomNav; track item.path) {
          <a class="bn-item" [routerLink]="item.path" routerLinkActive="active" (click)="closeNav()">
            <span class="bn-glyph">
              <img class="bn-ico" [src]="item.icon" alt="" (error)="onNavIconError($event)" />
              <span class="nav-glyph-fallback">{{ item.glyph }}</span>
            </span>
            <span class="bn-label">{{ item.label }}</span>
          </a>
        }
        <button class="bn-item" type="button" [class.active]="navOpen()" (click)="toggleNav()">
          <span class="bn-glyph">
            ☰
            @if (state.unreadTransmissions() > 0) {
              <span class="bn-dot"></span>
            }
          </span>
          <span class="bn-label">Mehr</span>
        </button>
      </nav>
    </div>
  `,
  styles: [shellStyles],
})
export class ShellComponent implements OnInit, OnDestroy {
  protected readonly state = inject(GameStateService);
  private readonly auth = inject(AuthService);
  private readonly router = inject(Router);
  private readonly doc = inject(DOCUMENT);

  /** 1-Sekunden-Takt fuer die sekundengenaue Ressourcen-Hochrechnung. */
  protected readonly nowMs = signal(Date.now());
  private resTicker?: ReturnType<typeof setInterval>;

  constructor() {
    // Screen-spezifischen (statischen) Hintergrund setzen: body[data-screen] = erstes Routen-Segment
    // (styles.scss waehlt darueber den Desktop-Backdrop). Shell lebt app-weit -> kein Cleanup noetig.
    this.router.events.subscribe((e) => {
      if (e instanceof NavigationEnd) {
        this.doc.body.dataset['screen'] =
          this.router.url.split(/[?#]/)[0].split('/').filter(Boolean)[0] ?? 'dashboard';
      }
    });
  }

  protected readonly planets = this.state.planets;
  protected readonly player = this.auth.player;
  protected readonly navOpen = signal(false);

  private static readonly ITEMS: Record<string, NavItem> = {
    dashboard: { path: '/dashboard', label: 'Dashboard', glyph: '🛰️', icon: 'assets/img/nav/dashboard.png' },
    buildings: { path: '/buildings', label: 'Gebaeude', glyph: '🏗️', icon: 'assets/img/nav/buildings.png' },
    research: { path: '/research', label: 'Forschung', glyph: '🔬', icon: 'assets/img/nav/research.png' },
    techtree: { path: '/techtree', label: 'Techbaum', glyph: '🌳', icon: 'assets/img/tech/techtree.png' },
    shipyard: { path: '/shipyard', label: 'Werft', glyph: '🛠️', icon: 'assets/img/nav/shipyard.png' },
    megastructures: { path: '/megastructures', label: 'Megastrukturen', glyph: '🌌', icon: 'assets/img/nav/megastructures.png' },
    fleet: { path: '/fleet', label: 'Flotte', glyph: '🚀', icon: 'assets/img/nav/fleet.png' },
    combat: { path: '/combat-sim', label: 'Simulator', glyph: '⚔️', icon: 'assets/img/nav/simulator.png' },
    galaxy: { path: '/galaxy', label: 'Galaxie', glyph: '🌌', icon: 'assets/img/nav/map.png' },
    routines: { path: '/routines', label: 'Routinen', glyph: '🛰', icon: 'assets/img/nav/routines.png' },
    trade: { path: '/trade', label: 'Handel', glyph: '💱', icon: 'assets/img/nav/market.png' },
    commanders: { path: '/commanders', label: 'Kommandozentrale', glyph: '🎖️', icon: 'assets/img/nav/command.png' },
    transmissions: { path: '/transmissions', label: 'Postfach', glyph: '📡', icon: 'assets/img/nav/mail.png' },
    ranking: { path: '/ranking', label: 'Rangliste', glyph: '🏆', icon: 'assets/img/nav/ranking.png' },
  };

  protected readonly navGroups: NavGroup[] = [
    { label: 'Imperium', items: [ShellComponent.ITEMS['dashboard'], ShellComponent.ITEMS['buildings'], ShellComponent.ITEMS['research'], ShellComponent.ITEMS['techtree'], ShellComponent.ITEMS['shipyard'], ShellComponent.ITEMS['megastructures']] },
    { label: 'Militaer', items: [ShellComponent.ITEMS['fleet'], ShellComponent.ITEMS['combat'], ShellComponent.ITEMS['galaxy'], ShellComponent.ITEMS['routines']] },
    { label: 'Reich & Sozial', items: [ShellComponent.ITEMS['trade'], ShellComponent.ITEMS['commanders'], ShellComponent.ITEMS['transmissions'], ShellComponent.ITEMS['ranking']] },
  ];

  /** Mobile-Bottom-Nav: 4 Kern-Screens; "Mehr" oeffnet den vollen Drawer. */
  protected readonly bottomNav: NavItem[] = [
    ShellComponent.ITEMS['dashboard'],
    ShellComponent.ITEMS['buildings'],
    ShellComponent.ITEMS['fleet'],
    ShellComponent.ITEMS['galaxy'],
  ];

  protected readonly resourceRows = computed(() => {
    const res = this.state.activePlanet()?.resources;
    // Sekundengenaue 1:1-Hochrechnung: gleiche Lazy-Formel wie das Backend
    // (amount + rate/h * verstrichene Stunden, gedeckelt auf Kapazitaet). Die Anzeige stimmt
    // damit mit dem ECHTEN Backend-Bestand ueberein -> kein "zeigt genug, baut aber nicht" mehr.
    const elapsedH = Math.max(0, (this.nowMs() - this.state.resourcesAt()) / 3_600_000);
    const keys: ('metal' | 'crystal' | 'deuterium')[] = ['metal', 'crystal', 'deuterium'];
    return keys.map((key) => {
      const pool = res?.[key];
      const base = pool?.amount ?? 0;
      const capacity = pool?.capacity ?? 0;
      const rate = pool?.rate ?? 0;
      let amount = base + rate * elapsedH;
      if (capacity > 0) {
        amount = Math.min(capacity, amount);
      }
      amount = Math.max(0, amount);
      const pct = capacity > 0 ? Math.min(100, (amount / capacity) * 100) : 0;
      return {
        key,
        glyph: RESOURCE_META[key].glyph,
        // ABRUNDEN (nie aufrunden) + exakte Zahl mit Tausenderpunkten -> 1:1, nie ueber dem Bestand.
        display: Math.floor(amount).toLocaleString('de-DE'),
        rate,
        pct,
        tip: `${RESOURCE_META[key].label}\n${Math.floor(amount).toLocaleString('de-DE')} / ${Math.floor(capacity).toLocaleString('de-DE')}\nRate: ${rate.toFixed(0)}/h`,
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
    // Sekundentakt fuer die Live-Hochrechnung der Ressourcen-Leiste.
    this.resTicker = setInterval(() => this.nowMs.set(Date.now()), 1000);
  }

  ngOnDestroy(): void {
    if (this.resTicker) {
      clearInterval(this.resTicker);
    }
  }

  onPlanetChange(event: Event): void {
    const id = (event.target as HTMLSelectElement).value;
    void this.state.selectPlanet(id);
  }

  selectColony(id: string): void {
    void this.state.selectPlanet(id);
  }

  toggleNav(): void {
    this.navOpen.update((v) => !v);
  }

  closeNav(): void {
    this.navOpen.set(false);
  }

  /** Bild kaputt/fehlt -> Glyph-Fallback einblenden. */
  onNavIconError(event: Event): void {
    const img = event.target as HTMLImageElement;
    img.style.display = 'none';
    const fallback = img.nextElementSibling as HTMLElement | null;
    if (fallback) {
      fallback.style.display = 'inline';
    }
  }

  logout(): void {
    this.state.reset();
    this.auth.logout();
    window.location.href = '/login';
  }
}
