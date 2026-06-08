export const shellStyles = `
  :host { display: block; }
  .shell {
    min-height: 100vh;
    display: flex;
    flex-direction: column;
  }

  /* Topbar */
  .topbar {
    position: sticky;
    top: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    gap: 1rem;
    padding: 0.5rem 1rem;
    background: rgba(10, 16, 32, 0.92);
    backdrop-filter: blur(10px);
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }
  .topbar-left, .topbar-right {
    display: flex;
    align-items: center;
    gap: 0.7rem;
  }
  .topbar-right { margin-left: auto; flex-wrap: wrap; }
  .logo {
    font-weight: 700;
    letter-spacing: 0.18em;
    color: var(--accent);
    font-size: 0.95rem;
  }
  .burger { display: none; }

  .res-bar {
    display: flex;
    gap: 1rem;
    flex: 1 1 auto;
    justify-content: center;
    flex-wrap: wrap;
  }
  .res {
    display: flex;
    align-items: center;
    gap: 0.45rem;
  }
  .res-glyph { font-size: 1.1rem; }
  .res-icon { width: 22px; height: 22px; object-fit: contain; vertical-align: middle; flex: 0 0 auto; }
  .res-meta { display: flex; flex-direction: column; gap: 3px; min-width: 64px; }
  .res-amount { font-size: 0.92rem; }
  .res-amount.neg { color: var(--magenta); }
  .res-rate { font-size: 0.7rem; color: var(--ok); }
  .res-rate.neg { color: var(--magenta); }
  .res .bar { width: 64px; }
  .res.full .res-amount { color: var(--warn); }

  .planet-select {
    width: auto;
    min-height: 34px;
    padding: 0.3rem 0.5rem;
    font-size: 0.82rem;
  }
  .player { font-size: 0.85rem; }

  .attack-banner {
    background: linear-gradient(90deg, rgba(255,64,160,0.25), rgba(255,64,160,0.08));
    border-bottom: 1px solid var(--magenta);
    color: #ffd6ec;
    text-align: center;
    padding: 0.5rem 1rem;
    font-size: 0.85rem;
    font-weight: 600;
    letter-spacing: 0.03em;
    animation: warn-pulse 1.6s ease infinite;
  }
  @keyframes warn-pulse {
    0%,100% { background: rgba(255,64,160,0.10); }
    50% { background: rgba(255,64,160,0.22); }
  }

  .body { display: flex; flex: 1; }

  /* Sidenav */
  .sidenav {
    width: 220px;
    flex: 0 0 220px;
    padding: 1rem 0.7rem;
    border-right: 1px solid var(--border);
    background: rgba(13, 22, 41, 0.5);
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  .nav-link {
    display: flex;
    align-items: center;
    gap: 0.7rem;
    padding: 0.65rem 0.8rem;
    border-radius: var(--radius-sm);
    color: var(--text-dim);
    font-size: 0.92rem;
    border: 1px solid transparent;
    transition: background 0.15s ease, color 0.15s ease;
  }
  .nav-link:hover { background: rgba(46,230,214,0.06); color: var(--text); }
  .nav-link.active {
    background: rgba(46,230,214,0.12);
    color: var(--accent);
    border-color: var(--border);
    box-shadow: inset 2px 0 0 var(--accent);
  }
  .nav-glyph { font-size: 1.1rem; width: 1.4rem; text-align: center; }
  .nav-label { flex: 1; }
  .badge {
    background: var(--magenta);
    color: #fff;
    font-size: 0.7rem;
    font-weight: 700;
    border-radius: 99px;
    padding: 0.05rem 0.4rem;
    min-width: 18px;
    text-align: center;
  }

  .content {
    flex: 1;
    min-width: 0;
    padding: 1.3rem;
    width: 100%;
  }

  /* Kolonien-Leiste (rechts) */
  .colony-rail {
    width: 160px;
    flex: 0 0 160px;
    padding: 1rem 0.6rem;
    border-left: 1px solid var(--border);
    background: rgba(13, 22, 41, 0.5);
    display: flex;
    flex-direction: column;
    gap: 0.3rem;
  }
  .rail-title {
    font-size: 0.72rem;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: var(--text-dim);
    padding: 0 0.4rem 0.4rem;
  }
  .colony {
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 2px;
    width: 100%;
    text-align: left;
    padding: 0.5rem 0.55rem;
    border-radius: var(--radius-sm);
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-dim);
    cursor: pointer;
    transition: background 0.15s ease, color 0.15s ease;
  }
  .colony:hover { background: rgba(46,230,214,0.06); color: var(--text); }
  .colony.active {
    background: rgba(46,230,214,0.12);
    color: var(--accent);
    border-color: var(--border);
    box-shadow: inset 2px 0 0 var(--accent);
  }
  .colony-name {
    font-size: 0.85rem;
    white-space: nowrap;
    overflow: hidden;
    text-overflow: ellipsis;
    max-width: 100%;
  }
  .colony-coords { font-size: 0.68rem; opacity: 0.75; }

  /* Auf Desktop ersetzt die Kolonien-Leiste das Topbar-Dropdown */
  .planet-select { display: none; }

  .scrim { display: none; }

  /* Mobile */
  @media (max-width: 860px) {
    .burger { display: inline-flex; }
    .res-bar { order: 3; width: 100%; justify-content: space-around; gap: 0.5rem; }
    .res-meta { min-width: 48px; }
    .res .bar { width: 48px; }
    .player { display: none; }
    .sidenav {
      position: fixed;
      top: 0; bottom: 0; left: 0;
      z-index: 50;
      transform: translateX(-100%);
      transition: transform 0.25s ease;
      background: var(--bg);
    }
    .sidenav.open { transform: translateX(0); }
    .colony-rail { display: none; }
    .planet-select {
      display: inline-block;
      width: auto;
      min-height: 34px;
      padding: 0.3rem 0.5rem;
      font-size: 0.82rem;
    }
    .scrim {
      display: block;
      position: fixed;
      inset: 0;
      background: rgba(0,0,0,0.6);
      z-index: 45;
    }
    .content { padding: 1rem; }
  }
`;
