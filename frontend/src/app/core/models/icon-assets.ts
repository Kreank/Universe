/**
 * Aufloesung balance.json-Key -> serviertes Icon-Asset (``assets/img/<kind>/<key>.png``).
 *
 * Bewusst getrennt von ``display.ts`` (Labels/Glyphen), damit die Asset-Verdrahtung
 * unabhaengig von der Text-Pflege bleibt. Jede Funktion liefert einen Pfad; die
 * Komponenten reichen ihn als ``[src]`` an ``app-icon-tile`` weiter, das bei
 * fehlendem/kaputtem Bild automatisch auf den Emoji-Glyph zurueckfaellt.
 *
 * Die Dateinamen unter ``assets/img/<kind>/`` entsprechen den Map-Keys aus
 * ``display.ts`` 1:1 — Ausnahmen werden hier per Alias abgebildet.
 */

/** Missions-Typ -> Dateiname (Sonderfall: ``spy`` heisst als Datei ``espionage``). */
const MISSION_FILE: Record<string, string> = {
  spy: 'espionage',
};

export function techIcon(key: string): string {
  return `assets/img/tech/${key}.png`;
}

export function resourceIcon(key: string): string {
  return `assets/img/resources/${key}.png`;
}

export function shipIcon(key: string): string {
  // Mk2/Elite-Schiffe (`<parent>_mk2`) nutzen dasselbe Schiff-Bild wie ihr Parent —
  // unterschieden werden sie allein durch den Mk2-Rahmen (siehe icon-tile `[mk2]`).
  const base = key.endsWith('_mk2') ? key.slice(0, -4) : key;
  return `assets/img/ships/${base}.png`;
}

export function defenseIcon(key: string): string {
  return `assets/img/defenses/${key}.png`;
}

export function buildingIcon(key: string): string {
  return `assets/img/buildings/${key}.png`;
}

export function traitIcon(key: string): string {
  return `assets/img/traits/${key}.png`;
}

export function specIcon(key: string): string {
  return `assets/img/spec/${key}.png`;
}

export function rankIcon(key: string): string {
  return `assets/img/ranks/${key}.png`;
}

export function planetIcon(key: string): string {
  return `assets/img/planets/${key}.png`;
}

export function weaponIcon(key: string): string {
  return `assets/img/weapons/${key}.png`;
}

export function rangeIcon(key: string): string {
  return `assets/img/range/${key}.png`;
}

export function statusIcon(name: string): string {
  return `assets/img/status/${name}.png`;
}

export function navIcon(key: string): string {
  return `assets/img/nav/${key}.png`;
}

/**
 * Generisches Flotten-Icon (ein Schiff im Flug) — ersetzt in den Flottenbewegungs-Zeilen
 * das Missions-Label durch ein einheitliches Schiff-Symbol. Ein einziges Asset fuer alle
 * Missionen; Glyph-Fallback (🚀) im Aufrufer, solange das Bild fehlt.
 */
export function fleetIcon(): string {
  return 'assets/img/ui/fleet_underway.png';
}

/** Generisches UI-Icon (Aktions-Buttons): ``assets/img/ui/<name>.png``. */
export function uiIcon(name: string): string {
  return `assets/img/ui/${name}.png`;
}

/**
 * Missions-Icon. ``trade`` besitzt (noch) keine eigene Datei und faellt
 * im Aufrufer auf den Glyph zurueck (``null`` => kein Bild).
 */
export function missionIcon(type: string): string | null {
  if (type === 'trade') return null;
  const file = MISSION_FILE[type] ?? type;
  return `assets/img/missions/${file}.png`;
}

/**
 * Equipment-Slot-Platzhalter (Kopf/Haende/Brust/Schuhe).
 * Dateien unter assets/img/equipment/slot_<slot>.png; Glyph-Fallback im Aufrufer.
 */
export function equipmentSlotIcon(slot: string): string {
  return `assets/img/equipment/slot_${slot}.png`;
}

/**
 * Equipment-Item-Icon (z.B. fighter_helm.png).
 * Dateien unter assets/img/equipment/<itemKey>.png; Glyph-Fallback im Aufrufer.
 */
export function equipmentItemIcon(itemKey: string): string {
  return `assets/img/equipment/${itemKey}.png`;
}

/**
 * Set-Emblem (set_fighter/set_cruiser/set_capital/set_civil).
 * Dateien unter assets/img/equipment/set_<setKey>.png; Glyph-Fallback im Aufrufer.
 */
export function equipmentSetIcon(setKey: string): string {
  return `assets/img/equipment/set_${setKey}.png`;
}

/**
 * Stat-Icon fuers Detail-Popup (Angriff/Schild/Fracht/Speed/Treibstoff/Energie).
 * Dateien unter assets/img/icons/spec/stat_<key>.png; Glyph-Fallback im Aufrufer.
 */
export function statIcon(key: string): string {
  return `assets/img/icons/spec/stat_${key}.png`;
}

/**
 * Faehigkeits-Kategorie-Icon (Commander-Abilities). Dateien unter
 * assets/img/icons/traits/trait_category_<category>.png; Glyph-Fallback im Aufrufer.
 */
export function abilityCategoryIcon(category: string): string {
  return `assets/img/icons/traits/trait_category_${category}.png`;
}
