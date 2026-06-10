export const galaxyStyles = `
  .sub { color: var(--text-dim); margin: -0.3rem 0 0.8rem; font-size: 0.85rem; }
  .small { font-size: 0.76rem; }
  .layout {
    grid-template-columns: minmax(340px, 1.5fr) minmax(280px, 1fr);
    align-items: start;
  }

  /* --- Scanner-Navigation --- */
  .gx-nav { display: flex; align-items: flex-end; gap: 0.4rem; flex-wrap: wrap; }
  .coordbox { display: flex; flex-direction: column; gap: 0.15rem; }
  .coordbox label { font-size: 0.68rem; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.05em; }
  .coordbox input { width: 70px; min-height: 32px; padding: 0.25rem 0.45rem; }
  .coords-current { color: var(--text-faint); margin: 0.5rem 0 0.6rem; font-size: 0.8rem; }

  /* --- Scanner mit dezentem Sonnensystem-Hintergrund --- */
  .scanner { position: relative; isolation: isolate; }
  .scanner::before {
    content: '';
    position: absolute; inset: 0; border-radius: inherit;
    background:
      linear-gradient(to bottom, color-mix(in srgb, var(--surface) 88%, transparent), color-mix(in srgb, var(--surface) 95%, transparent)),
      url('/assets/img/backgrounds/system_view.png') center / cover no-repeat;
    opacity: 0.5; z-index: -1; pointer-events: none;
  }

  /* --- Kompakte Positions-Zeilen (OGame-Tabellen-Stil) --- */
  .positions { display: flex; flex-direction: column; gap: 0.2rem; }
  .row {
    display: grid;
    grid-template-columns: 26px 34px 1fr auto;
    align-items: center;
    gap: 0.55rem;
    padding: 0.28rem 0.5rem;
    border: 1px solid transparent;
    border-radius: var(--radius-sm);
    min-height: 40px;
  }
  .row.occupied { border-color: var(--border); background: color-mix(in srgb, var(--surface-2) 80%, transparent); }
  .row.npc { border-color: var(--magenta-dim); background: color-mix(in srgb, var(--magenta) 7%, var(--surface-2)); }
  .row.player { border-color: var(--border-strong); }
  .row.own { border-color: var(--accent); background: color-mix(in srgb, var(--accent) 9%, var(--surface-2)); }
  .row.empty { opacity: 0.4; min-height: 26px; padding: 0.1rem 0.5rem; }

  .pos { font-size: 0.74rem; color: var(--text-dim); text-align: center; }
  .vis { display: flex; align-items: center; justify-content: center; width: 34px; height: 34px; }
  .vis-img { width: 32px; height: 32px; object-fit: contain; filter: drop-shadow(0 1px 3px rgba(0,0,0,0.5)); }
  .vis-dot { width: 6px; height: 6px; border-radius: 50%; background: var(--text-faint); opacity: 0.4; }

  .info { display: flex; align-items: baseline; gap: 0.5rem; min-width: 0; }
  .kind { font-size: 0.82rem; white-space: nowrap; }
  .name { font-size: 0.78rem; color: var(--text-faint); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .acts { display: flex; align-items: center; gap: 0.3rem; justify-content: flex-end; flex-wrap: wrap; }
  .ic {
    display: inline-flex; align-items: center; justify-content: center;
    width: 30px; height: 30px; border-radius: 7px; cursor: pointer; font-size: 0.92rem;
    background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text);
    transition: background 0.12s, border-color 0.12s, transform 0.05s;
  }
  .ic:hover { background: rgba(255,255,255,0.12); }
  .ic:active { transform: translateY(1px); }
  .ic.spy:hover { border-color: var(--accent); color: var(--accent); }
  .ic.atk:hover { border-color: var(--magenta); color: var(--magenta); }
  .ic.trp:hover { border-color: var(--ok); color: var(--ok); }

  .chip { color: var(--text-dim); font-size: 0.7rem; border: 1px solid var(--border); border-radius: 999px; padding: 0.1rem 0.5rem; white-space: nowrap; }
  .chip.disc { color: var(--accent); border-color: var(--accent-dim); cursor: help; }
  .chip.own { color: var(--accent); border-color: var(--accent-dim); }
  .chip.lvl { color: var(--accent); border-color: var(--accent-dim); margin-right: 0.3rem; }
  .chip.trade { color: var(--accent); border-color: var(--accent-dim); background: rgba(46, 230, 214, 0.1); cursor: help; margin-right: 0.3rem; }

  /* --- Ziel-Verzeichnis --- */
  .target-row {
    display: flex; flex-direction: column; gap: 0.25rem;
    padding: 0.5rem 0;
    border-bottom: 1px solid var(--border);
  }
  .target-main { display: flex; align-items: baseline; justify-content: space-between; gap: 0.5rem; }
  .target-name { font-weight: 600; font-size: 0.9rem; }
  .target-intel { color: var(--text-faint); }
  .target-act { display: flex; gap: 0.4rem; margin-top: 0.2rem; flex-wrap: wrap; }

  @media (max-width: 720px) {
    .layout { grid-template-columns: 1fr; }
  }
`;
