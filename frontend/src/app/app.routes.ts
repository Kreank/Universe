import { Routes } from '@angular/router';
import { authGuard, guestGuard } from './core/guards/auth.guard';

export const routes: Routes = [
  {
    path: 'login',
    canActivate: [guestGuard],
    loadComponent: () => import('./features/auth/login.component').then((m) => m.LoginComponent),
  },
  {
    path: 'register',
    canActivate: [guestGuard],
    loadComponent: () =>
      import('./features/auth/register.component').then((m) => m.RegisterComponent),
  },
  {
    path: '',
    canActivate: [authGuard],
    loadComponent: () => import('./layout/shell/shell.component').then((m) => m.ShellComponent),
    children: [
      { path: '', pathMatch: 'full', redirectTo: 'dashboard' },
      {
        path: 'dashboard',
        loadComponent: () =>
          import('./features/dashboard/dashboard.component').then((m) => m.DashboardComponent),
      },
      {
        path: 'buildings',
        loadComponent: () =>
          import('./features/buildings/buildings.component').then((m) => m.BuildingsComponent),
      },
      {
        path: 'research',
        loadComponent: () =>
          import('./features/research/research.component').then((m) => m.ResearchComponent),
      },
      {
        path: 'techtree',
        loadComponent: () =>
          import('./features/techtree/techtree.component').then((m) => m.TechtreeComponent),
      },
      {
        path: 'shipyard',
        loadComponent: () =>
          import('./features/shipyard/shipyard.component').then((m) => m.ShipyardComponent),
      },
      {
        path: 'megastructures',
        loadComponent: () =>
          import('./features/megastructures/megastructures.component').then(
            (m) => m.MegastructuresComponent,
          ),
      },
      {
        path: 'fleet',
        loadComponent: () =>
          import('./features/fleet/fleet.component').then((m) => m.FleetComponent),
      },
      {
        path: 'combat-sim',
        loadComponent: () =>
          import('./features/combat-sim/combat-sim.component').then((m) => m.CombatSimComponent),
      },
      {
        path: 'galaxy',
        loadComponent: () =>
          import('./features/galaxy/galaxy.component').then((m) => m.GalaxyComponent),
      },
      {
        path: 'trade',
        loadComponent: () =>
          import('./features/trade/trade.component').then((m) => m.TradeComponent),
      },
      {
        path: 'commanders',
        loadComponent: () =>
          import('./features/commanders/commanders.component').then((m) => m.CommandersComponent),
      },
      {
        path: 'commanders/:id',
        loadComponent: () =>
          import('./features/commanders/commander-detail.component').then(
            (m) => m.CommanderDetailComponent,
          ),
      },
      {
        path: 'transmissions',
        loadComponent: () =>
          import('./features/transmissions/transmissions.component').then(
            (m) => m.TransmissionsComponent,
          ),
      },
      {
        path: 'ranking',
        loadComponent: () =>
          import('./features/ranking/ranking.component').then((m) => m.RankingComponent),
      },
      {
        path: 'routines',
        loadComponent: () =>
          import('./features/routines/routines.component').then((m) => m.RoutinesComponent),
      },
    ],
  },
  { path: '**', redirectTo: '' },
];
