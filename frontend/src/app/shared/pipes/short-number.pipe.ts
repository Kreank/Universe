import { Pipe, PipeTransform } from '@angular/core';

/** Formatiert grosse Zahlen kompakt (1.2k, 3.4M, 5.1B). */
@Pipe({ name: 'shortNumber' })
export class ShortNumberPipe implements PipeTransform {
  transform(value: number | null | undefined): string {
    if (value === null || value === undefined || Number.isNaN(value)) {
      return '–';
    }
    const abs = Math.abs(value);
    if (abs < 1000) {
      return Math.round(value).toString();
    }
    const units = ['k', 'M', 'B', 'T'];
    let unitIndex = -1;
    let scaled = value;
    while (Math.abs(scaled) >= 1000 && unitIndex < units.length - 1) {
      scaled /= 1000;
      unitIndex += 1;
    }
    return `${scaled.toFixed(scaled < 10 ? 1 : 0)}${units[unitIndex]}`;
  }
}
