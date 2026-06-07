export const fleetStyles = `
  .layout {
    grid-template-columns: minmax(300px, 1fr) minmax(340px, 1.3fr);
    align-items: start;
  }
  .send { grid-column: 1 / -1; }
  .small { font-size: 0.76rem; }
  .full { width: 100%; }
  .hint { color: var(--text-faint); margin: 0.4rem 0 0; }

  /* --- Schiffsauswahl: dichtes, bild-zentriertes Kachel-Raster (OGame-Stil) --- */
  .ships-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: 0.7rem;
    margin-bottom: 1rem;
  }
  .empty-ships { grid-column: 1 / -1; }
  .ship {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 0.45rem;
    padding: 0.7rem 0.6rem;
    text-align: center;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: rgba(255, 255, 255, 0.015);
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }
  .ship.picked { border-color: var(--accent); box-shadow: var(--glow); }
  .ship-art { position: relative; }
  .ship-art .avail {
    position: absolute; bottom: -5px; right: -5px;
    min-width: 22px; height: 22px; padding: 0 6px; border-radius: 99px;
    background: var(--surface-3); color: var(--text); border: 1px solid var(--border);
    font-size: 0.74rem; font-weight: 700; font-variant-numeric: tabular-nums;
    display: flex; align-items: center; justify-content: center;
  }
  .ship-name { font-weight: 600; font-size: 0.88rem; }
  .ship-pick { display: flex; align-items: center; gap: 0.35rem; width: 100%; margin-top: auto; }
  .ship-pick input { min-height: 38px; padding: 0.3rem 0.4rem; text-align: center; }
  .ship-pick .btn-sm { min-height: 38px; padding: 0.3rem 0.5rem; flex: 0 0 auto; }

  /* --- Auftrags-Leiste --- */
  .order-bar {
    display: grid;
    grid-template-columns: minmax(220px, 1.4fr) repeat(3, minmax(140px, 1fr)) minmax(150px, auto);
    gap: 0.7rem 0.9rem;
    align-items: end;
    padding-top: 0.9rem;
    border-top: 1px solid var(--border);
  }
  .order-bar .field { margin-bottom: 0; }
  .coord { display: flex; align-items: center; gap: 0.35rem; }
  .coord input { text-align: center; padding: 0.6rem 0.3rem; }
  .coord .sep { color: var(--text-faint); font-weight: 700; }
  .send-field { justify-content: flex-end; }
  input[type="range"] { padding: 0; min-height: auto; }

  /* --- Laufende Flotten --- */
  .fleet-row {
    display: flex; align-items: center; justify-content: space-between;
    gap: 0.6rem; padding: 0.6rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    flex-wrap: wrap;
  }
  .fleet-info { display: flex; flex-direction: column; gap: 0.25rem; }
  .fleet-act { display: flex; align-items: center; gap: 0.6rem; }
  .badge-mission { font-weight: 600; }

  /* --- Galaxie-Ansicht --- */
  .gx-controls { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.8rem; }
  .gx-controls input { width: 90px; }
  .gx-table { width: 100%; border-collapse: collapse; font-size: 0.86rem; }
  .gx-table th {
    text-align: left; color: var(--text-dim); font-weight: 500;
    font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.06em;
    padding: 0.4rem 0.5rem; border-bottom: 1px solid var(--border);
  }
  .gx-table td { padding: 0.45rem 0.5rem; border-bottom: 1px solid rgba(255,255,255,0.04); }
  .gx-table tr.occupied { background: rgba(46,230,214,0.04); }

  @media (max-width: 960px) {
    .order-bar { grid-template-columns: 1fr 1fr; }
    .order-bar .coords { grid-column: 1 / -1; }
    .send-field { grid-column: 1 / -1; }
  }
  @media (max-width: 860px) {
    .layout { grid-template-columns: 1fr; }
  }
`;
