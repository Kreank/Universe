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

  /* --- Fähigkeiten-Panel --- */
  .abilities-panel { margin-top: 1rem; }
  .ab-head { display: flex; align-items: center; gap: 0.5rem; margin-bottom: 0.6rem; }
  .ab-head .panel-title { margin: 0; }
  .sp-badge, .slot-badge {
    font-size: 0.72rem; padding: 0.12rem 0.5rem; border-radius: 99px;
    border: 1px solid var(--accent-dim); color: var(--accent);
    background: rgba(46, 230, 214, 0.1); white-space: nowrap;
  }
  .slot-badge { color: var(--text-dim); border-color: var(--border); background: rgba(255,255,255,0.03); }

  .ability-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: 0.55rem; }
  .ability-card {
    position: relative; padding: 0.55rem 0.65rem;
    border: 1px solid var(--border); border-radius: var(--radius-sm);
    background: rgba(255,255,255,0.02);
    clip-path: polygon(0 0, calc(100% - 10px) 0, 100% 10px, 100% 100%, 0 100%);
    display: flex; flex-direction: column; gap: 0.35rem;
  }
  .ability-card.learned { border-color: var(--accent-dim); background: rgba(46, 230, 214, 0.06); }
  .ability-card.locked { opacity: 0.55; }
  .ac-top { display: flex; align-items: center; gap: 0.4rem; }
  .ac-glyph {
    width: 26px; height: 26px; flex: 0 0 26px; display: flex; align-items: center; justify-content: center;
    border-radius: 7px; background: var(--surface-3); border: 1px solid var(--border); font-size: 0.95rem;
  }
  .ability-card.learned .ac-glyph { border-color: var(--accent-dim); color: var(--accent); }
  .ac-name { font-weight: 600; font-size: 0.86rem; flex: 1; line-height: 1.1; }
  .ac-pips { display: inline-flex; gap: 3px; flex: 0 0 auto; }
  .ac-pips .pip {
    width: 8px; height: 8px; border-radius: 99px;
    border: 1px solid var(--border-strong); background: transparent;
  }
  .ac-pips .pip.on { background: var(--accent); border-color: var(--accent); box-shadow: 0 0 6px var(--accent); }
  .ac-effect { font-size: 0.76rem; color: var(--text-dim); line-height: 1.2; }
  .ac-foot { display: flex; flex-wrap: wrap; align-items: center; gap: 0.35rem; margin-top: auto; }
  .ac-foot .btn { padding: 0.25rem 0.55rem; font-size: 0.76rem; min-height: 28px; }
  .ac-req { font-size: 0.72rem; color: var(--warn); }
  .ac-max { font-size: 0.74rem; color: var(--accent); }

  /* --- Charakter-Zucht / Gouverneur / Boni (kompakte Panels) --- */
  .trait-train, .governor, .bonuses { margin-top: 1rem; }
  .trait-train .replace-row, .gov-assign { display: flex; flex-wrap: wrap; gap: 0.4rem; margin: 0.4rem 0; }
  .trait-train select, .gov-assign select { min-height: 30px; flex: 1 1 130px; }
  .bonus-chips { display: flex; flex-wrap: wrap; gap: 0.35rem; }
`;
