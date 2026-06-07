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

  /* --- Scanner mit dezentem Sonnensystem-Hintergrund --- */
  .scanner { position: relative; isolation: isolate; }
  .scanner::before {
    content: '';
    position: absolute;
    inset: 0;
    border-radius: inherit;
    background:
      linear-gradient(to bottom, color-mix(in srgb, var(--surface) 86%, transparent), color-mix(in srgb, var(--surface) 94%, transparent)),
      url('/assets/img/backgrounds/system_view.png') center / cover no-repeat;
    opacity: 0.5;
    z-index: -1;
    pointer-events: none;
  }

  /* --- Positions-Raster --- */
  .positions { display: flex; flex-direction: column; gap: 0.4rem; }
  .cell {
    display: grid;
    grid-template-columns: 80px 1fr auto;
    align-items: center;
    gap: 0.7rem;
    padding: 0.55rem 0.7rem;
    border: 1px solid var(--border);
    border-radius: var(--radius-sm);
    background: color-mix(in srgb, var(--surface-2) 88%, transparent);
  }
  .cell.empty { opacity: 0.5; }
  .cell.npc { border-color: var(--magenta-dim); background: color-mix(in srgb, var(--magenta) 7%, var(--surface-2)); }
  .cell.player { border-color: var(--border-strong); }
  .cell.own { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 9%, var(--surface-2)); }

  /* --- Visuelle Zelle: Planeten-/Truemmerbild + Positionsnummer --- */
  .cell-visual {
    position: relative;
    display: flex;
    align-items: center;
    justify-content: center;
    width: 80px;
    height: 80px;
  }
  .cell-img {
    width: 72px;
    height: 72px;
    object-fit: contain;
    filter: drop-shadow(0 2px 6px rgba(0, 0, 0, 0.45));
  }
  .cell-dot {
    width: 8px;
    height: 8px;
    border-radius: 50%;
    background: var(--text-faint);
    opacity: 0.4;
  }
  .cell-pos {
    position: absolute;
    bottom: -2px;
    left: 0;
    font-size: 0.72rem;
    color: var(--text-dim);
    background: color-mix(in srgb, var(--surface) 70%, transparent);
    border-radius: 999px;
    padding: 0 0.35rem;
  }
  .cell-body { display: flex; flex-direction: column; gap: 0.1rem; }
  .cell-kind { font-size: 0.82rem; }
  .cell-name { font-size: 0.76rem; color: var(--text-faint); }
  .cell-act { display: flex; align-items: center; gap: 0.4rem; flex-wrap: wrap; justify-content: flex-end; }
  .chip { color: var(--text-dim); font-size: 0.72rem; border: 1px solid var(--border); border-radius: 999px; padding: 0.15rem 0.55rem; white-space: nowrap; }
  .chip.own { color: var(--accent); font-size: 0.74rem; border-color: var(--accent-dim); }
  .chip.lvl { color: var(--accent); border-color: var(--accent-dim); margin-right: 0.4rem; }

  /* --- Ziel-Verzeichnis --- */
  .target-row {
    display: flex; flex-direction: column; gap: 0.3rem;
    padding: 0.65rem 0;
    border-bottom: 1px solid var(--border);
  }
  .target-main { display: flex; align-items: baseline; justify-content: space-between; gap: 0.5rem; }
  .target-name { font-weight: 600; }
  .target-intel { color: var(--text-faint); }
  .target-act { display: flex; gap: 0.5rem; margin-top: 0.25rem; flex-wrap: wrap; }

  @media (max-width: 720px) {
    .layout { grid-template-columns: 1fr; }
    .cell { grid-template-columns: 64px 1fr; }
    .cell-visual { width: 64px; height: 64px; }
    .cell-img { width: 56px; height: 56px; }
    .cell > button, .cell > .chip, .cell > .cell-act { grid-column: 1 / -1; justify-self: start; }
    .cell-act { justify-content: flex-start; }
  }
`;
