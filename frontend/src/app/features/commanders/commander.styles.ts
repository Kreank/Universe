export const commanderStyles = `
  .head {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: var(--sp-4); flex-wrap: wrap; margin-bottom: var(--sp-4);
  }
  .sub { margin-top: calc(-1 * var(--sp-1)); font-size: var(--fs-sm); }
  .small { font-size: var(--fs-xs); }

  .span-card { margin-bottom: var(--sp-5); }
  .span-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: var(--sp-2); }
  .span-big { font-family: var(--font-display); font-size: var(--fs-lg); color: var(--accent); }
  .span-big.over { color: var(--danger); }
  .span-detail { margin-top: var(--sp-2); }

  .roster { grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
  .cmd-card {
    display: flex; gap: var(--sp-3); text-decoration: none; color: var(--text);
    transition: transform var(--motion-fast) var(--ease-out),
      box-shadow var(--motion-base) var(--ease-out),
      border-color var(--motion-base) var(--ease-out);
  }
  .cmd-card:hover {
    transform: translateY(-2px);
    border-color: var(--border-strong);
    box-shadow: var(--glow);
  }

  .portrait {
    position: relative;
    width: 84px; flex: 0 0 84px; height: 84px;
    border-radius: var(--r-md); overflow: hidden;
    border: 2px solid var(--band, var(--accent));
    box-shadow: 0 0 14px color-mix(in srgb, var(--band, var(--accent)) 40%, transparent);
  }
  .portrait > img { width: 100%; height: 100%; display: block; }
  .rank-badge {
    position: absolute; bottom: 0; left: 0; right: 0;
    background: rgba(6,10,20,0.85);
    font-family: var(--font-display);
    font-size: var(--fs-xs); text-align: center; padding: 1px 0;
    color: var(--band, var(--accent));
  }
  /* Status-Tag: rein informativ (Einsatz/Ausbildung) -> Akzent, nicht Magenta. */
  .status-tag {
    position: absolute; top: var(--sp-1); right: var(--sp-1);
    background: rgba(6,10,20,0.85); color: var(--accent);
    border: 1px solid var(--accent-dim);
    font-size: var(--fs-xs); padding: 1px var(--sp-2); border-radius: var(--r-pill);
  }

  /* Gueteklassen-Badge (F..SSS), prominent oben links. */
  .grade-badge {
    position: absolute; top: var(--sp-1); left: var(--sp-1);
    min-width: 20px; text-align: center;
    font-family: var(--font-display);
    font-weight: 800; font-size: var(--fs-xs); letter-spacing: 0.02em;
    padding: 1px var(--sp-2); border-radius: var(--r-sm);
    color: var(--bg-deep); border: 1px solid rgba(255,255,255,0.25);
    box-shadow: 0 0 8px var(--grade-glow, transparent);
  }
  .grade-badge.grade-low { background: var(--text-faint); --grade-glow: color-mix(in srgb, var(--text-faint) 50%, transparent); }
  .grade-badge.grade-mid { background: var(--info); --grade-glow: color-mix(in srgb, var(--info) 60%, transparent); }
  .grade-badge.grade-high { background: var(--accent); --grade-glow: color-mix(in srgb, var(--accent) 70%, transparent); }
  /* Elite/SSS = Prestige (Gold->Cyan), bewusst KEIN Magenta. */
  .grade-badge.grade-elite {
    background: linear-gradient(135deg, var(--energy), var(--accent-strong)); color: var(--bg-deep);
    --grade-glow: color-mix(in srgb, var(--energy) 70%, transparent);
  }

  /* Investitions-Stufen-Auswahl. */
  .tier-block { display: flex; flex-direction: column; gap: var(--sp-2); }
  .tier-row { display: grid; grid-template-columns: repeat(auto-fit, minmax(140px, 1fr)); gap: var(--sp-2); }
  .tier-card {
    display: flex; flex-direction: column; gap: var(--sp-1); text-align: left;
    padding: var(--sp-2) var(--sp-3); border-radius: var(--r-md);
    border: 1px solid var(--border); background: rgba(255,255,255,0.02);
    color: var(--text); cursor: pointer; min-height: 44px;
    transition: border-color var(--motion-fast) var(--ease-out),
      box-shadow var(--motion-fast) var(--ease-out),
      background var(--motion-fast) var(--ease-out);
  }
  .tier-card:hover { border-color: var(--border-strong); }
  .tier-card.active {
    border-color: var(--accent); background: color-mix(in srgb, var(--accent) 10%, transparent);
    box-shadow: var(--glow);
  }
  .tier-name { font-family: var(--font-display); font-weight: 700; font-size: var(--fs-sm); }
  .tier-cost { font-size: var(--fs-xs); color: var(--text-dim); }
  .tier-hint { font-size: var(--fs-xs); }

  .cmd-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: var(--sp-2); }
  .cmd-body h3 { font-family: var(--font-display); font-size: var(--fs-md); margin: 0; }
  .morale-bar .fill { background: linear-gradient(90deg, color-mix(in srgb, var(--band) 50%, transparent), var(--band)); }
  .traits { display: flex; flex-wrap: wrap; gap: var(--sp-1); }
  .trait { border-color: var(--border); }
  .risk { display: flex; flex-wrap: wrap; gap: var(--sp-1); }
  .chip.warn { border-color: var(--warn); color: var(--warn); background: color-mix(in srgb, var(--warn) 8%, transparent); }

  /* Inline-Icon in Chips/Badges (Rang, Spezialisierung, Traits). */
  .chip-ico {
    width: 1.15em; height: 1.15em; object-fit: contain;
    vertical-align: -0.2em; margin-right: 0.3em;
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5));
  }
  .rank-badge .chip-ico { margin-right: 0.2em; }

  .train-panel { margin-bottom: var(--sp-5); display: flex; flex-direction: column; gap: var(--sp-3); }
  .train-grid { display: grid; grid-template-columns: 1fr 1fr; gap: var(--sp-3); }
  .train-panel .field { display: flex; flex-direction: column; gap: var(--sp-1); margin-bottom: 0; }
  .train-panel .field > span {
    font-family: var(--font-display);
    font-size: var(--fs-xs); letter-spacing: 0.1em; text-transform: uppercase; color: var(--text-dim);
  }
  .train-panel .preview { display: flex; flex-direction: column; gap: var(--sp-1); }
  .train-panel .btn-primary { align-self: flex-start; }
  @media (max-width: 520px) { .train-grid { grid-template-columns: 1fr; } }

  .bonuses { display: flex; flex-direction: column; gap: var(--sp-1); }
  .bonus-head {
    font-family: var(--font-display);
    text-transform: uppercase; letter-spacing: 0.12em;
  }
  .bonus-chips { display: flex; flex-wrap: wrap; gap: var(--sp-1); }
  .chip.bonus {
    border-color: var(--accent-dim);
    color: var(--accent);
    background: color-mix(in srgb, var(--accent) 8%, transparent);
    font-size: var(--fs-xs);
  }
  .chip.bonus.neg {
    border-color: var(--warn); color: var(--warn);
    background: color-mix(in srgb, var(--warn) 8%, transparent);
  }

  .cmd-foot { display: flex; flex-wrap: wrap; gap: var(--sp-1); }

  @media (max-width: 520px) {
    .cmd-card { flex-direction: column; }
    .portrait { width: 100%; flex: 0 0 auto; height: 120px; }
  }
`;
