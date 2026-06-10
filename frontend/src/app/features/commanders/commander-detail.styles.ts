export const commanderDetailStyles = `
  .back { display: inline-block; margin-bottom: 1rem; font-size: 0.86rem; }
  .small { font-size: 0.78rem; }
  .layout { grid-template-columns: minmax(280px, 360px) 1fr; align-items: start; }

  .profile { display: flex; flex-direction: column; gap: 0.8rem; }
  .profile h1 { margin: 0; }
  .portrait {
    width: 120px; height: 120px; border-radius: 14px; overflow: hidden;
    border: 2px solid var(--band, var(--accent));
    box-shadow: 0 0 18px color-mix(in srgb, var(--band, var(--accent)) 45%, transparent);
  }
  .portrait img { width: 100%; height: 100%; display: block; }
  .badges { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .chip-ico {
    width: 1.15em; height: 1.15em; object-fit: contain;
    vertical-align: -0.2em; margin-right: 0.3em;
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5));
  }
  .grade-chip { font-weight: 800; color: #06101e; border: none; }
  .grade-chip.grade-low { background: #9aa3b2; }
  .grade-chip.grade-mid { background: #4aa3ff; }
  .grade-chip.grade-high { background: #22e0c8; }
  .grade-chip.grade-elite { background: linear-gradient(135deg, #ff49c0, #ffd24a); color: #1a0a14; }
  .morale-bar .fill { background: linear-gradient(90deg, color-mix(in srgb, var(--band) 50%, transparent), var(--band)); }

  .stats { display: grid; grid-template-columns: 1fr 1fr; gap: 0.5rem; margin: 0; }
  .stats div { display: flex; justify-content: space-between; padding: 0.3rem 0; border-bottom: 1px solid rgba(255,255,255,0.05); }
  .stats dt { color: var(--text-dim); font-size: 0.8rem; margin: 0; }
  .stats dd { margin: 0; }

  .train-row { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; }
  .traits { display: flex; flex-wrap: wrap; gap: 0.35rem; }
  .persona p { margin: 0.3rem 0; }

  /* Timeline */
  .timeline { list-style: none; margin: 0; padding: 0; position: relative; }
  .timeline::before {
    content: ''; position: absolute; left: 6px; top: 6px; bottom: 6px;
    width: 2px; background: var(--border);
  }
  .timeline li { position: relative; padding: 0 0 1.1rem 1.6rem; }
  .timeline .dot {
    position: absolute; left: 0; top: 4px;
    width: 14px; height: 14px; border-radius: 99px;
    background: var(--accent); box-shadow: 0 0 10px var(--accent);
    border: 2px solid var(--bg);
  }
  .entry .body { color: var(--text-dim); margin: 0.25rem 0 0; }

  @media (max-width: 860px) {
    .layout { grid-template-columns: 1fr; }
  }
`;
