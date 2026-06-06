import { Injectable, signal } from '@angular/core';

export type ToastKind = 'info' | 'success' | 'warning' | 'transmission';

export interface Toast {
  id: number;
  kind: ToastKind;
  title: string;
  message: string;
  /** Zugehoeriger Funkspruch fuer die "Eingehende Transmission"-Animation. */
  transmissionId?: string;
}

/**
 * In-App-Benachrichtigungen (Toasts). Angriffswarnung und eingehende
 * Funksprueche sind die wichtigsten Kanaele (Doku 11 §6).
 */
@Injectable({ providedIn: 'root' })
export class NotificationService {
  private nextId = 1;
  readonly toasts = signal<Toast[]>([]);

  push(kind: ToastKind, title: string, message: string, transmissionId?: string): number {
    const id = this.nextId++;
    const toast: Toast = { id, kind, title, message, transmissionId };
    this.toasts.update((list) => [...list, toast]);
    const ttl = kind === 'warning' ? 12000 : 7000;
    setTimeout(() => this.dismiss(id), ttl);
    return id;
  }

  info(title: string, message: string): number {
    return this.push('info', title, message);
  }

  success(title: string, message: string): number {
    return this.push('success', title, message);
  }

  warning(title: string, message: string): number {
    return this.push('warning', title, message);
  }

  dismiss(id: number): void {
    this.toasts.update((list) => list.filter((t) => t.id !== id));
  }
}
