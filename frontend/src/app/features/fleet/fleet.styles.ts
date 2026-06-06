export const fleetStyles = `
  .layout {
    grid-template-columns: minmax(300px, 1fr) minmax(320px, 1.2fr);
    align-items: start;
  }
  .galaxy { grid-column: 1 / -1; }
  .small { font-size: 0.76rem; }
  .full { width: 100%; margin-top: 0.5rem; }
  .hint { color: var(--text-faint); margin: 0.4rem 0 0; }

  .ships { display: flex; flex-direction: column; gap: 0.4rem; margin-bottom: 1rem; }
  .ship-pick {
    display: grid;
    grid-template-columns: 1fr auto 80px;
    gap: 0.6rem;
    align-items: center;
    font-size: 0.86rem;
  }
  .ship-pick input { min-height: 36px; padding: 0.3rem 0.5rem; }

  .coord { display: grid; grid-template-columns: 1fr 1fr 1fr; gap: 0.6rem; }
  .row2 { display: grid; grid-template-columns: 1fr 1fr; gap: 0.6rem; }
  .coord .field, .row2 .field { margin-bottom: 0.6rem; }
  input[type="range"] { padding: 0; min-height: auto; }

  .fleet-row {
    display: flex; align-items: center; justify-content: space-between;
    gap: 0.6rem; padding: 0.6rem 0;
    border-bottom: 1px solid rgba(255,255,255,0.06);
    flex-wrap: wrap;
  }
  .fleet-info { display: flex; flex-direction: column; gap: 0.25rem; }
  .fleet-act { display: flex; align-items: center; gap: 0.6rem; }
  .badge-mission { font-weight: 600; }

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

  @media (max-width: 860px) {
    .layout { grid-template-columns: 1fr; }
  }
`;
