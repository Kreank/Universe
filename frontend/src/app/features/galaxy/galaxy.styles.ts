export const galaxyStyles = `
  .sub { color: var(--text-dim); margin: -0.3rem 0 1.2rem; }
  .small { font-size: 0.76rem; }
  .layout {
    grid-template-columns: minmax(320px, 1.4fr) minmax(300px, 1fr);
    align-items: start;
  }

  /* --- Scanner-Navigation --- */
  .gx-nav { display: flex; align-items: flex-end; gap: 0.5rem; flex-wrap: wrap; }
  .coordbox { display: flex; flex-direction: column; gap: 0.2rem; }
  .coordbox label { font-size: 0.7rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; }
  .coordbox input { width: 80px; min-height: 36px; padding: 0.3rem 0.5rem; }
  .coords-current { color: var(--text-faint); margin: 0.7rem 0 0.9rem; font-size: 0.82rem; }

  /* --- Positions-Raster --- */
  .positions { display: flex; flex-direction: column; gap: 0.4rem; }
  .cell {
    display: grid;
    grid-template-columns: 40px 1fr auto;
    align-items: center;
    gap: 0.7rem;
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: var(--surface-2);
  }
  .cell.empty { opacity: 0.5; }
  .cell.npc { border-color: var(--magenta-dim); background: color-mix(in srgb, var(--magenta) 7%, var(--surface-2)); }
  .cell.player { border-color: var(--border-strong); }
  .cell.own { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 9%, var(--surface-2)); }
  .cell-pos { font-size: 1.1rem; color: var(--text-dim); text-align: center; }
  .cell-body { display: flex; flex-direction: column; gap: 0.1rem; }
  .cell-kind { font-size: 0.82rem; }
  .cell-name { font-size: 0.76rem; color: var(--text-faint); }
  .chip.own { color: var(--accent); font-size: 0.74rem; border: 1px solid var(--accent-dim); border-radius: 999px; padding: 0.15rem 0.55rem; }

  /* --- Ziel-Verzeichnis --- */
  .target-row {
    display: flex; flex-direction: column; gap: 0.3rem;
    padding: 0.65rem 0;
    border-bottom: 1px solid var(--border);
  }
  .target-main { display: flex; align-items: baseline; justify-content: space-between; gap: 0.5rem; }
  .target-name { font-weight: 600; }
  .target-act { display: flex; gap: 0.5rem; margin-top: 0.25rem; }

  @media (max-width: 720px) {
    .layout { grid-template-columns: 1fr; }
    .cell { grid-template-columns: 32px 1fr; }
    .cell > button, .cell > .chip { grid-column: 1 / -1; justify-self: start; }
  }
`;
