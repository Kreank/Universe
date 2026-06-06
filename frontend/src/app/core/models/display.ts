/**
 * Anzeige-Labels, Kurzbeschreibungen und Platzhalter-Icon-Glyphen.
 * Die `type`-Keys stammen aus `shared/balance.json`. Labels werden hier
 * fuer das deutsche UI gepflegt; der Server bleibt autoritativ fuer Zahlen.
 *
 * Asset-Pfade sind so strukturiert, dass die Glyph-Platzhalter spaeter durch
 * echte Bilder ersetzt werden koennen (z. B. assets/img/ships/light_fighter.svg).
 */

export interface DisplayMeta {
  label: string;
  glyph: string;
  blurb?: string;
}

export const RESOURCE_META: Record<string, DisplayMeta> = {
  metal: { label: 'Metall', glyph: '⛏️', blurb: 'Grundbaustoff fuer alles.' },
  crystal: { label: 'Kristall', glyph: '💎', blurb: 'Elektronik und Forschung.' },
  deuterium: { label: 'Deuterium', glyph: '🛢️', blurb: 'Treibstoff und Fusion.' },
  energy: { label: 'Energie', glyph: '⚡', blurb: 'Treibt die Minen an.' },
};

export const BUILDING_META: Record<string, DisplayMeta> = {
  metal_mine: { label: 'Metallmine', glyph: '⛏️', blurb: 'Foerdert Metall.' },
  crystal_mine: { label: 'Kristallmine', glyph: '💠', blurb: 'Foerdert Kristall.' },
  deuterium_synth: { label: 'Deuterium-Synthesizer', glyph: '🛢️', blurb: 'Gewinnt Deuterium.' },
  solar_plant: { label: 'Solarkraftwerk', glyph: '☀️', blurb: 'Erzeugt Energie.' },
  fusion_reactor: { label: 'Fusionsreaktor', glyph: '🔆', blurb: 'Energie aus Deuterium.' },
  robot_factory: { label: 'Roboterfabrik', glyph: '🤖', blurb: 'Beschleunigt Bauten.' },
  shipyard: { label: 'Werft', glyph: '🛠️', blurb: 'Baut Schiffe & Verteidigung.' },
  research_lab: { label: 'Forschungslabor', glyph: '🔬', blurb: 'Schaltet Technologien frei.' },
  metal_storage: { label: 'Metallspeicher', glyph: '🏗️', blurb: 'Erhoeht Metall-Kapazitaet.' },
  crystal_storage: { label: 'Kristallspeicher', glyph: '🏬', blurb: 'Erhoeht Kristall-Kapazitaet.' },
  deuterium_tank: { label: 'Deuteriumtank', glyph: '🛢️', blurb: 'Erhoeht Deuterium-Kapazitaet.' },
  command_academy: { label: 'Kommando-Akademie', glyph: '🎖️', blurb: 'Bildet Commander aus.' },
  command_center: { label: 'Kommandozentrale', glyph: '📡', blurb: 'Erhoeht Span of Control.' },
};

export const TECH_META: Record<string, DisplayMeta> = {
  energy_tech: { label: 'Energietechnik', glyph: '⚡', blurb: 'Grundlage vieler Technologien.' },
  combustion_drive: { label: 'Verbrennungstriebwerk', glyph: '🚀', blurb: 'Antrieb leichter Schiffe.' },
  impulse_drive: { label: 'Impulstriebwerk', glyph: '🛸', blurb: 'Schnellerer Antrieb.' },
  spy_tech: { label: 'Spionagetechnik', glyph: '🛰️', blurb: 'Ermoeglicht Sonden.' },
  computer_tech: { label: 'Computertechnik', glyph: '💻', blurb: '+1 Flottenslot pro Stufe.' },
  weapons_tech: { label: 'Waffentechnik', glyph: '🔫', blurb: '+10% Angriff pro Stufe.' },
  shield_tech: { label: 'Schildtechnik', glyph: '🛡️', blurb: '+10% Schild pro Stufe.' },
  armor_tech: { label: 'Panzerung', glyph: '🪖', blurb: '+10% Huelle pro Stufe.' },
  command_doctrine: { label: 'Kommando-Doktrin', glyph: '📖', blurb: '+Span of Control.' },
  logistics_tech: { label: 'Logistik', glyph: '📦', blurb: 'Schnellere Moral-Erholung.' },
  crew_psychology: { label: 'Crew-Psychologie', glyph: '🧠', blurb: 'Hoehere Moral-Decke.' },
};

export const SHIP_META: Record<string, DisplayMeta> = {
  light_fighter: { label: 'Leichter Jaeger', glyph: '🛩️', blurb: 'Schnell und billig.' },
  heavy_fighter: { label: 'Schwerer Jaeger', glyph: '✈️', blurb: 'Robuster Angreifer.' },
  cruiser: { label: 'Kreuzer', glyph: '🚀', blurb: 'Schlagkraeftiges Kriegsschiff.' },
  small_cargo: { label: 'Kleiner Transporter', glyph: '📦', blurb: 'Transportiert Ressourcen.' },
  spy_probe: { label: 'Spionagesonde', glyph: '🛰️', blurb: 'Spaeht Ziele aus.' },
};

export const DEFENSE_META: Record<string, DisplayMeta> = {
  rocket_launcher: { label: 'Raketenwerfer', glyph: '🚀', blurb: 'Guenstige Verteidigung.' },
  light_laser: { label: 'Leichtes Lasergeschuetz', glyph: '🔦', blurb: 'Solide Verteidigung.' },
};

export const MISSION_META: Record<string, DisplayMeta> = {
  attack: { label: 'Angriff', glyph: '⚔️' },
  transport: { label: 'Transport', glyph: '📦' },
  spy: { label: 'Spionage', glyph: '🛰️' },
  deploy: { label: 'Stationierung', glyph: '🚚' },
};

export const SPECIALIZATION_META: Record<string, DisplayMeta> = {
  combat: { label: 'Kampf', glyph: '⚔️' },
  logistics: { label: 'Logistik', glyph: '📦' },
  spy: { label: 'Spionage', glyph: '🛰️' },
  research: { label: 'Forschung', glyph: '🔬' },
  trade: { label: 'Handel', glyph: '💱' },
};

export const RANK_META: Record<string, DisplayMeta> = {
  cadet: { label: 'Kadett', glyph: '▪' },
  officer: { label: 'Offizier', glyph: '▴' },
  veteran: { label: 'Veteran', glyph: '★' },
  elite: { label: 'Elite', glyph: '✦' },
  legend: { label: 'Legende', glyph: '✸' },
};

export const TRAIT_META: Record<string, DisplayMeta> = {
  aggressive: { label: 'aggressiv', glyph: '🔥' },
  cautious: { label: 'vorsichtig', glyph: '🧊' },
  loyal: { label: 'loyal', glyph: '🤝' },
  ambitious: { label: 'ehrgeizig', glyph: '📈' },
  greedy: { label: 'gierig', glyph: '🪙' },
  honorable: { label: 'ehrenhaft', glyph: '🎗️' },
  charismatic: { label: 'charismatisch', glyph: '✨' },
  hot_tempered: { label: 'aufbrausend', glyph: '💢' },
};

/** Faellt auf einen lesbaren Titel zurueck, wenn kein Label gepflegt ist. */
export function humanize(key: string): string {
  return key
    .split('_')
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(' ');
}

export function metaFor(map: Record<string, DisplayMeta>, key: string): DisplayMeta {
  return map[key] ?? { label: humanize(key), glyph: '◆' };
}
