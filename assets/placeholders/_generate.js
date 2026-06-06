#!/usr/bin/env node
/*
 * Generator fuer Universe-Platzhalter-SVGs.
 * Erzeugt einheitliche, palettentreue Stub-Assets gemaess docs/STYLE_BIBLE.md.
 * KEINE externen Abhaengigkeiten/URLs. Reproduzierbar:  node _generate.js
 * Ausgabe spiegelt die echte Asset-Ordnerstruktur (drop-in ersetzbar).
 */
'use strict';
const fs = require('fs');
const path = require('path');
const BASE = __dirname;

// --- Palette (Single Source: docs/STYLE_BIBLE.md) ---
const VOID = '#05070F', BG800 = '#0B1424', BG700 = '#12203A', GRID = '#1C3354';
const STROKE = '#2A467A', ACCENT = '#2BE0E6', ACCENT_DIM = '#157E86';
const HULL = '#8DA2BF', HULL_LIGHT = '#C3D2E6', HULL_DARK = '#4A5B78';
const HUMAN = '#FFB23F', MAGENTA = '#FF41F8', DANGER = '#F0070C', SUCCESS = '#36E07A';
const TEXT = '#E6F2FF', TEXT_MUTED = '#8DA2BF';
const RES = { metal: '#B8C2CF', crystal: '#46D5FF', deuterium: '#57F2C4', energy: '#FFD23F' };
const RANK = { cadet: '#8DA2BF', officer: '#C98A3A', veteran: '#C7D2DD', elite: '#FFD23F', legend: '#FF41F8' };
const MORALE = { high: '#36E07A', neutral: '#2BE0E6', low: '#FFB23F', critical: '#F0070C' };

function write(rel, svg) {
  const p = path.join(BASE, rel);
  fs.mkdirSync(path.dirname(p), { recursive: true });
  fs.writeFileSync(p, svg, 'utf8');
  console.log('wrote', rel);
}
const header = (w, h) =>
  `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 ${w} ${h}" role="img">`;

// Dunkles Panel mit Cyan-Rahmen + abgeschnittener Ecke oben-rechts (Marken-Signatur)
function panel(w, h, accent = ACCENT, chamfer = null) {
  const c = chamfer != null ? chamfer : Math.max(8, Math.floor(w / 8));
  const pts = `0,0 ${w - c},0 ${w},${c} ${w},${h} 0,${h}`;
  return `<polygon points="${pts}" fill="${BG800}"/>`
    + `<polygon points="${pts}" fill="none" stroke="${accent}" stroke-width="${Math.max(2, Math.floor(w / 128))}"/>`
    + `<rect x="0" y="0" width="${Math.max(6, Math.floor(w / 12))}" height="${Math.max(3, Math.floor(w / 40))}" fill="${accent}"/>`;
}
function label(w, h, name, sub = 'PLATZHALTER') {
  const fs1 = Math.max(9, Math.floor(w / 22));
  const sfs = Math.max(7, Math.floor(w / 34));
  return `<text x="${w / 2}" y="${h - h * 0.10}" fill="${TEXT}" font-family="monospace" font-size="${fs1}" text-anchor="middle" font-weight="bold">${name}</text>`
    + `<text x="${w / 2}" y="${h - h * 0.045}" fill="${TEXT_MUTED}" font-family="monospace" font-size="${sfs}" text-anchor="middle" letter-spacing="2">${sub}</text>`;
}

// ---- Ressourcen-Icons (64x64) ----
function resource(name, color) {
  const w = 64, h = 64, cx = w / 2, cy = h / 2 - 4;
  let g = '';
  if (name === 'metal') {
    [[-12, 6], [-4, -2], [4, 6]].forEach(([dx, dy]) => {
      g += `<rect x="${cx + dx - 9}" y="${cy + dy - 5}" width="18" height="10" rx="2" fill="${color}" stroke="${HULL_DARK}"/>`;
    });
  } else if (name === 'crystal') {
    g = `<polygon points="${cx},${cy - 16} ${cx + 11},${cy} ${cx},${cy + 16} ${cx - 11},${cy}" fill="${color}" stroke="${HULL_LIGHT}"/>`
      + `<polygon points="${cx},${cy - 16} ${cx + 11},${cy} ${cx},${cy}" fill="${HULL_LIGHT}" opacity="0.4"/>`;
  } else if (name === 'deuterium') {
    g = `<path d="M ${cx} ${cy - 16} C ${cx + 13} ${cy} ${cx + 10} ${cy + 16} ${cx} ${cy + 16} C ${cx - 10} ${cy + 16} ${cx - 13} ${cy} ${cx} ${cy - 16} Z" fill="${color}" stroke="${HULL_LIGHT}"/>`;
  } else if (name === 'energy') {
    g = `<polygon points="${cx + 2},${cy - 16} ${cx - 10},${cy + 2} ${cx - 1},${cy + 2} ${cx - 3},${cy + 16} ${cx + 11},${cy - 3} ${cx + 1},${cy - 3}" fill="${color}" stroke="${HULL_DARK}"/>`;
  }
  return header(w, h) + panel(w, h, color, 8) + g
    + `<text x="${w / 2}" y="${h - 7}" fill="${TEXT}" font-family="monospace" font-size="8" text-anchor="middle">${name}</text></svg>`;
}

// ---- Schiffe (512, Keil, Bug oben-rechts, je Klasse skaliert) ----
function ship(name, s, color = HULL) {
  const w = 512, h = 512, cx = w / 2, cy = h / 2;
  const pts = `${cx + 70 * s},${cy - 90 * s} ${cx + 95 * s},${cy + 40 * s} ${cx - 60 * s},${cy + 95 * s} ${cx - 95 * s},${cy + 20 * s} ${cx - 30 * s},${cy - 30 * s}`;
  const eng = `<circle cx="${cx - 78 * s}" cy="${cy + 55 * s}" r="${14 * s}" fill="${ACCENT}" opacity="0.85"/>`
    + `<circle cx="${cx - 50 * s}" cy="${cy + 75 * s}" r="${12 * s}" fill="${ACCENT}" opacity="0.7"/>`;
  const body = `<polygon points="${pts}" fill="${color}" stroke="${ACCENT}" stroke-width="3"/>`
    + `<polygon points="${cx + 70 * s},${cy - 90 * s} ${cx + 95 * s},${cy + 40 * s} ${cx + 20 * s},${cy + 10 * s}" fill="${HULL_LIGHT}" opacity="0.25"/>`;
  return header(w, h) + panel(w, h) + eng + body + label(w, h, name) + '</svg>';
}

// ---- Gebäude (512, Iso-Wuerfel auf Sockel) ----
function building(name, accent = ACCENT) {
  const w = 512, h = 512, cx = w / 2, cy = h / 2 - 10;
  const base = `<polygon points="${cx},${cy + 120} ${cx + 150},${cy + 50} ${cx},${cy - 20} ${cx - 150},${cy + 50}" fill="${BG700}" stroke="${ACCENT_DIM}" stroke-width="2"/>`;
  const top = `<polygon points="${cx},${cy - 110} ${cx + 110},${cy - 50} ${cx},${cy + 10} ${cx - 110},${cy - 50}" fill="${HULL_LIGHT}"/>`;
  const left = `<polygon points="${cx - 110},${cy - 50} ${cx},${cy + 10} ${cx},${cy + 90} ${cx - 110},${cy + 30}" fill="${HULL_DARK}"/>`;
  const right = `<polygon points="${cx + 110},${cy - 50} ${cx},${cy + 10} ${cx},${cy + 90} ${cx + 110},${cy + 30}" fill="${HULL}"/>`;
  const glow = `<circle cx="${cx}" cy="${cy - 50}" r="22" fill="${accent}" opacity="0.9"/>`;
  return header(w, h) + panel(w, h) + base + left + right + top + glow + label(w, h, name) + '</svg>';
}

// ---- Verteidigung (512, Geschuetz auf Iso-Pad) ----
function defense(name, accent = ACCENT) {
  const w = 512, h = 512, cx = w / 2, cy = h / 2 - 10;
  const pad = `<polygon points="${cx},${cy + 90} ${cx + 120},${cy + 30} ${cx},${cy - 30} ${cx - 120},${cy + 30}" fill="${BG700}" stroke="${ACCENT_DIM}" stroke-width="2"/>`;
  const mount = `<rect x="${cx - 30}" y="${cy - 30}" width="60" height="50" rx="6" fill="${HULL_DARK}"/>`;
  const barrel = `<rect x="${cx - 8}" y="${cy - 130}" width="16" height="110" rx="6" fill="${HULL}" stroke="${ACCENT}" stroke-width="2"/>`
    + `<circle cx="${cx}" cy="${cy - 130}" r="12" fill="${accent}"/>`;
  return header(w, h) + panel(w, h) + pad + mount + barrel + label(w, h, name) + '</svg>';
}

// ---- Commander-Portrait je Rang (1024) ----
function portrait(rank) {
  const w = 1024, h = 1024, cx = w / 2, col = RANK[rank];
  const grad = `<defs><radialGradient id="bg${rank}" cx="50%" cy="38%" r="75%">`
    + `<stop offset="0%" stop-color="#0E2A33"/><stop offset="100%" stop-color="${VOID}"/></radialGradient></defs>`
    + `<rect width="${w}" height="${h}" fill="url(#bg${rank})"/>`;
  const bust = `<circle cx="${cx}" cy="${h * 0.40}" r="150" fill="${HULL_DARK}" stroke="${HUMAN}" stroke-width="4"/>`
    + `<path d="M ${cx - 220} ${h * 0.92} C ${cx - 220} ${h * 0.62} ${cx - 120} ${h * 0.56} ${cx} ${h * 0.56} C ${cx + 120} ${h * 0.56} ${cx + 220} ${h * 0.62} ${cx + 220} ${h * 0.92} Z" fill="${HULL}" stroke="${HUMAN}" stroke-width="4"/>`;
  const glow = rank === 'cadet' ? '' : `<rect x="20" y="20" width="${w - 40}" height="${h - 40}" fill="none" stroke="${col}" stroke-width="10" opacity="0.35"/>`;
  const frame = `<rect x="44" y="44" width="${w - 88}" height="${h - 88}" fill="none" stroke="${col}" stroke-width="8"/>`;
  const badge = `<rect x="${cx - 150}" y="${h - 150}" width="300" height="70" rx="6" fill="${BG800}" stroke="${col}" stroke-width="3"/>`
    + `<text x="${cx}" y="${h - 104}" fill="${col}" font-family="monospace" font-size="34" text-anchor="middle" font-weight="bold" letter-spacing="3">${rank.toUpperCase()}</text>`;
  const sub = `<text x="${cx}" y="80" fill="${TEXT_MUTED}" font-family="monospace" font-size="26" text-anchor="middle" letter-spacing="4">COMMANDER · PLATZHALTER</text>`;
  return header(w, h) + grad + glow + frame + bust + badge + sub + '</svg>';
}

// ---- Moral-Balken (4 Bänder) ----
function morale(color, fillPct, labelDe) {
  const w = 256, h = 48, pad = 6, innerW = w - 2 * pad - 60;
  const fillW = Math.round(innerW * fillPct);
  const track = `<rect x="${pad}" y="${pad}" width="${innerW}" height="${h - 2 * pad}" rx="4" fill="${BG700}" stroke="${STROKE}"/>`;
  const fill = `<rect x="${pad}" y="${pad}" width="${fillW}" height="${h - 2 * pad}" rx="4" fill="${color}"/>`;
  const txt = `<text x="${w - 30}" y="${h / 2 + 5}" fill="${color}" font-family="monospace" font-size="14" text-anchor="middle" font-weight="bold">${labelDe}</text>`;
  return header(w, h) + `<rect width="${w}" height="${h}" fill="${BG800}"/>` + track + fill + txt + '</svg>';
}

// ---- Alarm-Icon (64) ----
function alert() {
  const w = 64, h = 64, cx = w / 2;
  const tri = `<polygon points="${cx},10 ${w - 8},${h - 12} 8,${h - 12}" fill="${DANGER}" stroke="#FFFFFF" stroke-width="2"/>`;
  const bang = `<rect x="${cx - 3}" y="24" width="6" height="18" rx="2" fill="#FFFFFF"/><circle cx="${cx}" cy="48" r="3.5" fill="#FFFFFF"/>`;
  return header(w, h) + tri + bang + '</svg>';
}

function main() {
  for (const [n, c] of Object.entries(RES)) write(`icons/resources/${n}.svg`, resource(n, c));

  const ships = [['light_fighter', 0.55, HULL], ['heavy_fighter', 0.7, HULL],
    ['cruiser', 0.9, HULL], ['small_cargo', 0.85, '#9aa7b5'], ['spy_probe', 0.35, HULL]];
  for (const [n, s, col] of ships) write(`ships/${n}.svg`, ship(n, s, col));

  const bld = { metal_mine: HUMAN, crystal_mine: RES.crystal, deuterium_synth: RES.deuterium,
    solar_plant: ACCENT, robot_factory: '#FFD23F', shipyard: ACCENT,
    research_lab: ACCENT, command_academy: HUMAN, command_center: HUMAN };
  for (const [n, acc] of Object.entries(bld)) write(`buildings/${n}.svg`, building(n, acc));

  write('defenses/rocket_launcher.svg', defense('rocket_launcher', DANGER));
  write('defenses/light_laser.svg', defense('light_laser', ACCENT));

  for (const r of Object.keys(RANK)) write(`commanders/portrait_${r}.svg`, portrait(r));

  write('icons/ui/morale_high.svg', morale(MORALE.high, 0.92, 'HOCH'));
  write('icons/ui/morale_neutral.svg', morale(MORALE.neutral, 0.65, 'NEUTRAL'));
  write('icons/ui/morale_low.svg', morale(MORALE.low, 0.38, 'NIEDRIG'));
  write('icons/ui/morale_critical.svg', morale(MORALE.critical, 0.15, 'KRITISCH'));
  write('icons/ui/alert.svg', alert());
  console.log('done.');
}
main();
