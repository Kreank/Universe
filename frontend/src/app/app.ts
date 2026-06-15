import { ChangeDetectionStrategy, Component, inject } from '@angular/core';
import { RouterOutlet } from '@angular/router';
import { SwUpdate, VersionReadyEvent } from '@angular/service-worker';
import { filter } from 'rxjs';
import { ToastContainerComponent } from './shared/components/toast-container.component';

@Component({
  selector: 'app-root',
  changeDetection: ChangeDetectionStrategy.OnPush,
  imports: [RouterOutlet, ToastContainerComponent],
  template: `<router-outlet />
    <app-toast-container />`,
})
export class App {
  private readonly sw = inject(SwUpdate);

  constructor() {
    // PWA-Auto-Update: Sobald nach einem Deploy eine neue Version bereitsteht, sofort aktivieren
    // und neu laden — sonst bleiben offene Clients auf der veralteten, gecachten App-Shell haengen
    // (Symptom: "Layout verrutscht / Elemente fehlen", obwohl die ausgelieferte Version korrekt ist).
    if (this.sw.isEnabled) {
      this.sw.versionUpdates
        .pipe(filter((e): e is VersionReadyEvent => e.type === 'VERSION_READY'))
        .subscribe(() => this.sw.activateUpdate().then(() => document.location.reload()));
      // Lang offene Sessions / installierte PWA: regelmaessig auf neue Version pruefen.
      setInterval(() => void this.sw.checkForUpdate().catch(() => {}), 60_000);
    }
  }
}
