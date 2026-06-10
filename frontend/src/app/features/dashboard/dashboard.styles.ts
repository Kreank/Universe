export const dashboardStyles = `
  .sub { margin-top: -0.3rem; font-size: 0.85rem; }

  /* Imperiums-Punkte-Hero — prominent, gut erkennbar, klickbar. */
  .score-hero {
    display: flex; align-items: center; gap: 1rem; flex-wrap: wrap;
    margin: 0.2rem 0 0.9rem;
    padding: 0.7rem 1rem; border-radius: 12px;
    background: linear-gradient(135deg, rgba(46,230,214,0.16), rgba(13,22,41,0.92));
    border: 1px solid rgba(46,230,214,0.4);
    box-shadow: 0 0 22px rgba(46,230,214,0.14), inset 0 0 18px rgba(46,230,214,0.08);
    color: var(--text); text-decoration: none;
    transition: border-color 0.15s ease, box-shadow 0.15s ease;
  }
  .score-hero:hover {
    border-color: var(--accent);
    box-shadow: 0 0 30px rgba(46,230,214,0.28), inset 0 0 18px rgba(46,230,214,0.12);
  }
  .score-ico {
    width: 52px; height: 52px; object-fit: contain; flex: 0 0 auto;
    filter: drop-shadow(0 2px 5px rgba(0,0,0,0.6));
  }
  .score-main { display: flex; flex-direction: column; line-height: 1.1; }
  .score-label {
    font-size: 0.7rem; letter-spacing: 0.08em; text-transform: uppercase;
    color: var(--text-dim);
  }
  .score-value {
    font-size: 2rem; font-weight: 800; color: var(--accent);
    text-shadow: 0 0 12px rgba(46,230,214,0.4);
  }
  .score-rank {
    display: flex; flex-direction: column; align-items: center; line-height: 1.1;
    padding: 0 0.6rem; border-left: 1px solid var(--border);
  }
  .rank-big { font-size: 1.5rem; font-weight: 800; }
  .score-breakdown { display: flex; flex-wrap: wrap; gap: 0.4rem; flex: 1; }
  .score-breakdown .bd {
    font-size: 0.8rem; padding: 0.18rem 0.5rem; border-radius: 6px;
    background: rgba(255,255,255,0.05); border: 1px solid var(--border);
    white-space: nowrap;
  }
  .score-cta { margin-left: auto; align-self: flex-end; }
  @media (max-width: 640px) {
    .score-value { font-size: 1.6rem; }
    .score-cta { display: none; }
  }
  /* Zwei feste, oben ausgerichtete Spalten — balanciert, keine toten Flaechen */
  .cols {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 0.7rem;
    align-items: start;
  }
  .col {
    display: flex;
    flex-direction: column;
    gap: 0.7rem;
    min-width: 0;
  }
  @media (max-width: 900px) {
    .cols { grid-template-columns: 1fr; gap: 1rem; }
    .col { gap: 1rem; }
  }
  .res-grid { display: flex; flex-direction: column; gap: 0.55rem; }
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
  .ops-block { display: flex; flex-direction: column; gap: 0.2rem; }
  .ops-label {
    font-size: 0.74rem;
    letter-spacing: 0.08em;
    color: var(--text-dim);
    margin-bottom: 0.1rem;
  }
  .queue-row .chip { margin-left: 0.35rem; }
  .ok { color: var(--ok); }
  .neg { color: var(--magenta); }

  .queue-row, .alert, .cmd-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 0.6rem;
    padding: 0.32rem 0;
    font-size: 0.86rem;
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }
  .alert { border-bottom: none; }
  .alert.danger { color: #ffb3d8; }
  .alert.decision { color: var(--accent); }
  hr { border: none; border-top: 1px solid var(--border); margin: 0.5rem 0; }

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
