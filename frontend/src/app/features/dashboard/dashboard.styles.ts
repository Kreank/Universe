export const dashboardStyles = `
  .sub { margin-top: -0.3rem; font-size: 0.85rem; }
  .cols {
    grid-template-columns: repeat(auto-fit, minmax(290px, 1fr));
    align-items: start;
  }
  .res-grid { display: flex; flex-direction: column; gap: 0.8rem; }
  .res-card {
    display: flex;
    flex-direction: column;
    gap: 0.35rem;
  }
  .res-card.energy {
    border-top: 1px solid var(--border);
    padding-top: 0.7rem;
  }
  .small { font-size: 0.76rem; }
  .ok { color: var(--ok); }
  .neg { color: var(--magenta); }

  .queue-row, .alert, .cmd-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    padding: 0.5rem 0;
    font-size: 0.88rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }
  .alert { border-bottom: none; }
  .alert.danger { color: #ffb3d8; }
  .alert.decision { color: var(--accent); }
  hr { border: none; border-top: 1px solid var(--border); margin: 0.7rem 0; }

  .cmd-row { text-decoration: none; color: var(--text); }
  .cmd-row:hover { background: rgba(46,230,214,0.05); border-radius: 6px; }
  .cmd-name { font-size: 0.88rem; }
  .cmd-morale {
    display: inline-flex; align-items: center; gap: 0.4rem;
    font-size: 0.8rem; color: var(--band);
  }
  .cmd-morale .dot {
    width: 8px; height: 8px; border-radius: 99px; background: var(--band);
    box-shadow: 0 0 8px var(--band);
  }
  .span-line { margin-top: 0.6rem; }
`;
