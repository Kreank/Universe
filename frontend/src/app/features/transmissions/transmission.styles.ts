export const transmissionStyles = `
  .head {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: var(--sp-4); flex-wrap: wrap; margin-bottom: var(--sp-4);
  }
  h1 { font-family: var(--font-display); }
  .sub { margin-top: calc(-1 * var(--sp-1)); margin-bottom: var(--sp-3); font-size: var(--fs-sm); color: var(--text-dim); }
  .small { font-size: var(--fs-xs); }
  .filters { display: flex; gap: var(--sp-2); }
  .bar-row { display: flex; align-items: center; gap: var(--sp-3); flex-wrap: wrap; margin-bottom: var(--sp-4); }
  .bar-row app-tab-bar { flex: 1 1 auto; }
  .bar-row .tab-bar { margin: 0; border-bottom: 0; padding-bottom: 0; }
  .del-read { margin-left: auto; }

  .list { grid-template-columns: 1fr; gap: var(--sp-3); max-width: 760px; }

  /* Nachrichtenkarte: linker Statusbalken kodiert Zustand/Typ. */
  .msg { position: relative; border-left: 3px solid var(--border); transition: border-color var(--motion-fast) var(--ease-out); }
  .msg.unread { border-left-color: var(--accent); box-shadow: var(--glow-soft); }
  .msg.demand { border-left-color: var(--danger); }

  .msg-head { display: flex; gap: var(--sp-3); align-items: flex-start; }
  .type-glyph { font-size: var(--fs-xl); line-height: 1; flex: 0 0 auto; }
  .msg-meta { flex: 1; min-width: 0; }
  .title-row { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
  .msg-meta h3 { margin: 0; font-family: var(--font-display); font-size: var(--fs-md); }
  .dot-new {
    width: 10px; height: 10px; border-radius: var(--r-pill);
    background: var(--accent); box-shadow: 0 0 8px var(--accent);
    flex: 0 0 auto; margin-top: var(--sp-1);
  }

  /* Typ-Badge je Funkspruch-Art (uebernimmt globale .chip-Optik). */
  .type-chip {
    font-family: var(--font-display);
    font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.08em;
    padding: 2px var(--sp-2); border-radius: var(--r-pill);
    border: 1px solid var(--border); color: var(--text-dim);
    background: rgba(255, 255, 255, 0.04); white-space: nowrap;
  }
  .type-chip.tc-spy_report { border-color: var(--accent); color: var(--accent); }
  .type-chip.tc-combat_report { border-color: var(--danger-dim); color: var(--danger); }
  .type-chip.tc-big_moment { border-color: var(--warn); color: var(--warn); }

  .body { color: var(--text-dim); font-size: var(--fs-base); margin: var(--sp-3) 0 0; white-space: pre-line; }

  /* -- Strukturierter Spionagebericht ----------------------------------- */
  .intel {
    margin-top: var(--sp-3); padding: var(--sp-3) var(--sp-4);
    border: 1px solid var(--border); border-radius: var(--r-md);
    background: rgba(255, 255, 255, 0.02);
    display: flex; flex-direction: column; gap: var(--sp-3);
  }
  .intel-top { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-3); }
  .intel-target { font-family: var(--font-display); font-weight: 600; }
  .lvl-badge {
    font-family: var(--mono);
    font-size: var(--fs-xs); padding: 2px var(--sp-2); border-radius: var(--r-pill);
    border: 1px solid var(--border); white-space: nowrap;
  }
  .lvl-badge[data-lvl="1"] { color: var(--text-dim); }
  .lvl-badge[data-lvl="2"] { color: var(--accent); border-color: var(--accent); }
  .lvl-badge[data-lvl="3"] { color: var(--danger); border-color: var(--danger-dim); }

  .intel-strength {
    display: flex; gap: var(--sp-5); padding-bottom: var(--sp-2);
    border-bottom: 1px solid var(--border);
  }
  .intel-strength .stat { font-size: var(--fs-sm); color: var(--text-dim); }
  .intel-strength .stat-num {
    font-family: var(--mono); font-variant-numeric: tabular-nums;
    font-size: var(--fs-lg); font-weight: 700; color: var(--text); margin-right: var(--sp-1);
  }

  .intel-section { display: flex; flex-direction: column; gap: var(--sp-2); }
  .intel-label {
    font-family: var(--font-display);
    font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim);
  }
  .intel-rows { display: flex; flex-wrap: wrap; gap: var(--sp-2); }
  .unit {
    display: inline-flex; align-items: center; gap: var(--sp-1);
    font-size: var(--fs-sm); padding: var(--sp-1) var(--sp-2); border-radius: var(--r-sm);
    background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border);
    font-variant-numeric: tabular-nums;
  }
  .unit.res { font-family: var(--mono); }
  .u-ico { flex: 0 0 auto; }

  .intel-hint { color: var(--text-dim); margin: var(--sp-1) 0 0; }
  .intel-actions { display: flex; flex-wrap: wrap; gap: var(--sp-2); margin-top: var(--sp-2); }
  .intel-time { margin: 0; }

  .decision {
    margin-top: var(--sp-3); padding-top: var(--sp-3);
    border-top: 1px solid var(--border);
    display: flex; flex-direction: column; gap: var(--sp-2);
  }
  .dec-buttons { display: flex; gap: var(--sp-2); flex-wrap: wrap; }
  .msg-actions { display: flex; gap: var(--sp-2); flex-wrap: wrap; margin-top: var(--sp-3); }
  .del:hover { color: var(--danger); border-color: var(--danger-dim); }
`;
