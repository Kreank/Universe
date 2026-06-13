export const commanderDetailStyles = `
  .back { display: inline-block; margin-bottom: var(--sp-4); font-size: var(--fs-sm); }
  .small { font-size: var(--fs-xs); }
  .layout { grid-template-columns: minmax(280px, 360px) 1fr; align-items: start; }

  .profile { display: flex; flex-direction: column; gap: var(--sp-3); }
  /* Signatur-Schraegecke: nur EINMAL, als Detail-Header-Akzent. */
  .profile {
    clip-path: polygon(0 0, calc(100% - 18px) 0, 100% 18px, 100% 100%, 0 100%);
  }
  .profile h1 { font-family: var(--font-display); margin: 0; }
  .portrait {
    width: 120px; height: 120px; border-radius: var(--r-lg); overflow: hidden;
    border: 2px solid var(--band, var(--accent));
    box-shadow: 0 0 18px color-mix(in srgb, var(--band, var(--accent)) 45%, transparent);
  }
  .portrait img { width: 100%; height: 100%; display: block; }
  .badges { display: flex; flex-wrap: wrap; gap: var(--sp-1); }
  .chip-ico {
    width: 1.15em; height: 1.15em; object-fit: contain;
    vertical-align: -0.2em; margin-right: 0.3em;
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5));
  }
  .grade-chip { font-family: var(--font-display); font-weight: 800; color: var(--bg-deep); border: none; }
  .grade-chip.grade-low { background: var(--text-faint); }
  .grade-chip.grade-mid { background: var(--info); }
  .grade-chip.grade-high { background: var(--accent); }
  /* Elite/SSS = Prestige (Gold->Cyan), bewusst KEIN Magenta. */
  .grade-chip.grade-elite { background: linear-gradient(135deg, var(--energy), var(--accent-strong)); color: var(--bg-deep); }
  .morale-bar .fill { background: linear-gradient(90deg, color-mix(in srgb, var(--band) 50%, transparent), var(--band)); }

  .stats { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-2); margin: 0; }
  .stats div { display: flex; justify-content: space-between; padding: var(--sp-1) 0; border-bottom: 1px solid var(--border); }
  .stats dt { color: var(--text-dim); font-size: var(--fs-sm); margin: 0; }
  .stats dd { margin: 0; }
  .stats dd.warn { color: var(--warn); }

  .train-row { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2); }
  .traits { display: flex; flex-wrap: wrap; gap: var(--sp-1); }
  .persona p { margin: var(--sp-1) 0; }

  /* Timeline */
  .timeline { list-style: none; margin: 0; padding: 0; position: relative; }
  .timeline::before {
    content: ''; position: absolute; left: 6px; top: 6px; bottom: 6px;
    width: 2px; background: var(--border);
  }
  .timeline li { position: relative; padding: 0 0 var(--sp-4) var(--sp-5); }
  .timeline .dot {
    position: absolute; left: 0; top: 4px;
    width: 14px; height: 14px; border-radius: var(--r-pill);
    background: var(--accent); box-shadow: 0 0 10px var(--accent);
    border: 2px solid var(--bg);
  }
  .entry .body { color: var(--text-dim); margin: var(--sp-1) 0 0; }

  @media (max-width: 860px) {
    .layout { grid-template-columns: 1fr; }
  }

  /* --- Faehigkeiten-Panel --- */
  .abilities-panel { margin-top: var(--sp-4); }
  .ab-head { display: flex; align-items: center; gap: var(--sp-2); margin-bottom: var(--sp-3); }
  .ab-head .panel-title { margin: 0; padding-bottom: 0; border-bottom: none; }
  .sp-badge, .slot-badge {
    font-family: var(--mono);
    font-size: var(--fs-xs); padding: 2px var(--sp-2); border-radius: var(--r-pill);
    border: 1px solid var(--accent-dim); color: var(--accent);
    background: var(--accent-soft); white-space: nowrap;
  }
  .slot-badge { color: var(--text-dim); border-color: var(--border); background: rgba(255,255,255,0.03); }

  .ability-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--sp-2); }
  .ability-card {
    position: relative; padding: var(--sp-2) var(--sp-3);
    border: 1px solid var(--border); border-radius: var(--r-md);
    background: rgba(255,255,255,0.02);
    display: flex; flex-direction: column; gap: var(--sp-1);
  }
  .ability-card.learned { border-color: var(--accent-dim); background: var(--accent-soft); }
  .ability-card.locked { opacity: 0.55; }
  .ac-top { display: flex; align-items: center; gap: var(--sp-1); }
  .ac-glyph {
    width: 26px; height: 26px; flex: 0 0 26px; display: flex; align-items: center; justify-content: center;
    border-radius: var(--r-sm); background: var(--surface-3); border: 1px solid var(--border); font-size: var(--fs-md);
  }
  .ability-card.learned .ac-glyph { border-color: var(--accent-dim); color: var(--accent); }
  .ac-ico { width: 18px; height: 18px; object-fit: contain; }
  .ac-glyph-fb { display: none; }
  .ac-name { font-family: var(--font-display); font-weight: 600; font-size: var(--fs-sm); flex: 1; line-height: 1.1; }
  .ac-pips { display: inline-flex; gap: 3px; flex: 0 0 auto; }
  .ac-pips .pip {
    width: 8px; height: 8px; border-radius: var(--r-pill);
    border: 1px solid var(--border-strong); background: transparent;
  }
  .ac-pips .pip.on { background: var(--accent); border-color: var(--accent); box-shadow: 0 0 6px var(--accent); }
  .ac-effect { font-size: var(--fs-xs); color: var(--text-dim); line-height: 1.2; }
  .ac-foot { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-1); margin-top: auto; }
  .ac-req { font-size: var(--fs-xs); color: var(--warn); }
  .ac-max { font-size: var(--fs-xs); color: var(--accent); }

  /* --- Charakter-Zucht / Gouverneur / Boni (kompakte Panels) --- */
  .trait-train, .governor, .bonuses { margin-top: var(--sp-4); }
  .trait-train .panel-title, .governor .panel-title, .bonuses .panel-title { padding-bottom: var(--sp-2); margin-bottom: var(--sp-2); }
  .trait-train .replace-row, .gov-assign { display: flex; flex-wrap: wrap; gap: var(--sp-1); margin: var(--sp-1) 0; }
  .trait-train select, .gov-assign select { flex: 1 1 130px; }
  .bonus-chips { display: flex; flex-wrap: wrap; gap: var(--sp-1); }
  .chip.bonus {
    border-color: var(--accent-dim); color: var(--accent);
    background: color-mix(in srgb, var(--accent) 8%, transparent);
    font-size: var(--fs-xs);
  }
  .chip.bonus.neg { border-color: var(--warn); color: var(--warn); background: color-mix(in srgb, var(--warn) 8%, transparent); }
`;
