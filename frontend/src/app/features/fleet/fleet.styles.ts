export const fleetStyles = `
  .small { font-size: var(--fs-xs); }
  .hint { color: var(--text-faint); margin: var(--sp-1) 0 0; }
  .card { margin-bottom: var(--sp-4); }

  /* --- Flottenkommando: Aktions-Leiste (öffnet das gemeinsame Versand-Overlay) --- */
  .actions-card .action-row {
    display: flex; flex-wrap: wrap; gap: var(--sp-3); margin-bottom: var(--sp-2);
  }
  .actions-card .action-row .btn { flex: 0 1 auto; }

  /* --- Laufende Flotten & Patrouillen: dichte Listenzeilen --- */
  .fleet-row {
    display: flex; align-items: center; justify-content: space-between;
    gap: var(--sp-3); padding: var(--sp-2) 0;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }
  .fleet-row:last-child { border-bottom: none; }
  .fleet-info { display: flex; flex-direction: column; gap: var(--sp-1); min-width: 0; }
  .fleet-act { display: flex; align-items: center; gap: var(--sp-3); }
  .badge-mission { font-family: var(--font-display); font-weight: 600; }

  /* --- Eingehende Angriffe (Gefahr -> --danger) --- */
  .card.incoming {
    border: 1px solid color-mix(in srgb, var(--danger) 45%, transparent);
    background: color-mix(in srgb, var(--danger) 10%, var(--surface-1));
    margin-bottom: var(--sp-4);
  }
  .incoming-row {
    display: flex; align-items: center; justify-content: space-between;
    gap: var(--sp-3); padding: var(--sp-2) 0;
    border-bottom: 1px solid color-mix(in srgb, var(--danger) 18%, transparent);
    flex-wrap: wrap;
  }
  .incoming-row:last-of-type { border-bottom: none; }
  .incoming-info { display: flex; flex-direction: column; gap: var(--sp-1); min-width: 0; }
  .badge-threat { font-family: var(--font-display); font-weight: 700; color: var(--danger); }

  /* --- Hover-Aufschluesselung: Schiffe + Fracht beim Drueberfahren --- */
  .has-tip { position: relative; }
  .fleet-tip {
    position: absolute;
    top: calc(100% + var(--sp-1)); left: 0;
    z-index: 30;
    min-width: 220px; max-width: 320px;
    padding: var(--sp-2) var(--sp-3);
    background: var(--surface-2, var(--surface-1));
    border: 1px solid var(--border);
    border-radius: var(--radius-2, 8px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
    opacity: 0; visibility: hidden; transform: translateY(-4px);
    transition: opacity .12s ease, transform .12s ease, visibility .12s;
    pointer-events: none;
  }
  .has-tip:hover .fleet-tip,
  .has-tip:focus-within .fleet-tip {
    opacity: 1; visibility: visible; transform: translateY(0);
  }
  .tip-head {
    font-family: var(--font-display); font-weight: 600;
    font-size: var(--fs-sm); margin-bottom: var(--sp-2);
    padding-bottom: var(--sp-1); border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  .tip-sec { margin-top: var(--sp-2); }
  .tip-sec:first-of-type { margin-top: 0; }
  .tip-sec-title {
    font-size: var(--fs-xs, .72rem); text-transform: uppercase;
    letter-spacing: .04em; color: var(--text-dim); margin-bottom: var(--sp-1);
  }
  .tip-row {
    display: flex; justify-content: space-between; gap: var(--sp-3);
    font-size: var(--fs-sm); padding: 1px 0;
  }
  .tip-row.muted { color: var(--text-dim); justify-content: flex-start; }

  /* --- Galaxie-Hinweis (Verweis auf die eigene Galaxie-Seite) --- */
  .galaxy-hint {
    margin-top: var(--sp-4); text-align: center;
    padding: var(--sp-3); border: 1px dashed var(--border); border-radius: var(--r-md);
  }

  /* Mobile: gestapelte Karten + Touch-Targets >= 44px. */
  @media (max-width: 860px) {
    .fleet-row { padding: var(--sp-3) 0; }
    .fleet-act .btn { min-height: 44px; }
  }

  .hangar-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(96px, 1fr));
    gap: var(--sp-2);
  }
  .hship {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 2px;
    padding: var(--sp-2);
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    background: rgba(255, 255, 255, 0.02);
    text-align: center;
  }
  .hship-name { font-size: var(--fs-xs); color: var(--text-dim); line-height: 1.1; }
  .hship-count { font-size: var(--fs-base); color: var(--text); font-variant-numeric: tabular-nums; }
`;
