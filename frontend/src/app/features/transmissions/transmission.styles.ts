export const transmissionStyles = `
  .head {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;
  }
  .sub { margin-top: -0.3rem; margin-bottom: 0.8rem; font-size: 0.85rem; color: var(--text-dim); }
  .small { font-size: 0.76rem; }
  .filters { display: flex; gap: 0.4rem; }
  .bar-row { display: flex; align-items: center; gap: 0.6rem; flex-wrap: wrap; margin-bottom: 1rem; }
  .bar-row app-tab-bar { flex: 1 1 auto; }
  .bar-row .tab-bar { margin: 0; border-bottom: 0; padding-bottom: 0; }
  .del-read { margin-left: auto; }

  .list { grid-template-columns: 1fr; gap: 0.8rem; max-width: 760px; }
  .msg { position: relative; border-left: 3px solid var(--border); }
  .msg.unread { border-left-color: var(--accent); box-shadow: var(--glow); }
  .msg.demand { border-left-color: var(--magenta); }

  .msg-head { display: flex; gap: 0.7rem; align-items: flex-start; }
  .type-glyph { font-size: 1.4rem; line-height: 1; }
  .msg-meta { flex: 1; min-width: 0; }
  .title-row { display: flex; align-items: center; gap: 0.5rem; flex-wrap: wrap; }
  .msg-meta h3 { margin: 0; font-size: 1rem; }
  .dot-new {
    width: 10px; height: 10px; border-radius: 99px;
    background: var(--accent); box-shadow: 0 0 8px var(--accent);
    flex: 0 0 auto; margin-top: 4px;
  }

  /* Typ-Badge je Funkspruch-Art */
  .type-chip {
    font-size: 0.66rem; text-transform: uppercase; letter-spacing: 0.05em;
    padding: 0.1rem 0.45rem; border-radius: 99px;
    border: 1px solid var(--border); color: var(--text-dim);
    background: rgba(255, 255, 255, 0.03); white-space: nowrap;
  }
  .type-chip.tc-spy_report { border-color: var(--accent); color: var(--accent); }
  .type-chip.tc-combat_report { border-color: var(--magenta); color: var(--magenta); }

  .body { color: var(--text-dim); font-size: 0.9rem; margin: 0.7rem 0 0; white-space: pre-line; }

  /* -- Strukturierter Spionagebericht ----------------------------------- */
  .intel {
    margin-top: 0.8rem; padding: 0.7rem 0.8rem;
    border: 1px solid var(--border); border-radius: 8px;
    background: rgba(255, 255, 255, 0.02);
    display: flex; flex-direction: column; gap: 0.6rem;
  }
  .intel-top { display: flex; align-items: center; justify-content: space-between; gap: 0.6rem; }
  .intel-target { font-weight: 600; }
  .lvl-badge {
    font-size: 0.72rem; padding: 0.12rem 0.5rem; border-radius: 99px;
    border: 1px solid var(--border); white-space: nowrap;
  }
  .lvl-badge[data-lvl="1"] { color: var(--text-dim); }
  .lvl-badge[data-lvl="2"] { color: var(--accent); border-color: var(--accent); }
  .lvl-badge[data-lvl="3"] { color: var(--magenta); border-color: var(--magenta); }

  .intel-strength {
    display: flex; gap: 1.2rem; padding-bottom: 0.4rem;
    border-bottom: 1px solid var(--border);
  }
  .intel-strength .stat { font-size: 0.82rem; color: var(--text-dim); }
  .intel-strength .stat-num { font-size: 1.05rem; font-weight: 700; color: var(--text); margin-right: 0.25rem; }

  .intel-section { display: flex; flex-direction: column; gap: 0.35rem; }
  .intel-label { font-size: 0.74rem; text-transform: uppercase; letter-spacing: 0.04em; color: var(--text-dim); }
  .intel-rows { display: flex; flex-wrap: wrap; gap: 0.4rem; }
  .unit {
    display: inline-flex; align-items: center; gap: 0.3rem;
    font-size: 0.82rem; padding: 0.2rem 0.5rem; border-radius: 6px;
    background: rgba(255, 255, 255, 0.04); border: 1px solid var(--border);
  }
  .unit.res { font-variant-numeric: tabular-nums; }
  .u-glyph { font-size: 0.9rem; }

  .intel-hint { color: var(--text-dim); margin: 0.1rem 0 0; }
  .intel-time { margin: 0; }

  .decision {
    margin-top: 0.9rem; padding-top: 0.8rem;
    border-top: 1px solid var(--border);
    display: flex; flex-direction: column; gap: 0.5rem;
  }
  .dec-buttons { display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .msg-actions { display: flex; gap: 0.5rem; flex-wrap: wrap; margin-top: 0.8rem; }
  .del:hover { color: var(--magenta); border-color: var(--magenta); }
`;
