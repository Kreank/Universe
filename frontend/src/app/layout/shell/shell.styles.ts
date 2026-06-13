export const shellStyles = `
  :host { display: block; }
  .shell {
    min-height: 100vh;
    min-height: 100dvh;
    display: flex;
    flex-direction: column;
  }

  /* Cinematic Loop-Backdrop hinter der gesamten App (fix). Liegt ueber dem statischen
     body-Backdrop, aber unter dem Inhalt; teiltransparente Leisten zeigen es durch. */
  .app-backdrop {
    position: fixed; inset: 0; width: 100%; height: 100%;
    object-fit: cover; z-index: -2; pointer-events: none;
  }
  .app-backdrop-veil {
    position: fixed; inset: 0; z-index: -1; pointer-events: none;
    background: linear-gradient(rgba(5, 7, 14, 0.62), rgba(5, 7, 14, 0.84));
  }
  /* Mobil + Reduced-Motion: kein Video -> statisches body-Backdrop bleibt. */
  @media (prefers-reduced-motion: reduce) { .app-backdrop, .app-backdrop-veil { display: none; } }
  @media (max-width: 899px) { .app-backdrop, .app-backdrop-veil { display: none; } }

  /* ---------- Topbar ---------- */
  .topbar {
    position: sticky;
    top: 0;
    z-index: 30;
    display: flex;
    align-items: center;
    gap: var(--sp-4);
    padding: var(--sp-2) var(--sp-4);
    background: rgba(8, 13, 24, 0.82);
    backdrop-filter: blur(14px) saturate(1.2);
    -webkit-backdrop-filter: blur(14px) saturate(1.2);
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }
  .topbar-left, .topbar-right { display: flex; align-items: center; gap: var(--sp-3); }
  .topbar-right { margin-left: auto; flex-wrap: wrap; }
  .logo {
    font-family: var(--font-display);
    font-weight: 700;
    letter-spacing: 0.2em;
    color: var(--accent);
    font-size: var(--fs-md);
    text-shadow: 0 0 18px rgba(47, 227, 210, 0.4);
  }

  /* ---------- Ressourcen-Leiste ---------- */
  .res-bar {
    display: flex;
    gap: var(--sp-5);
    flex: 1 1 auto;
    justify-content: center;
    flex-wrap: wrap;
  }
  .res { display: flex; align-items: center; gap: var(--sp-2); }
  .res-icon { width: 22px; height: 22px; object-fit: contain; flex: 0 0 auto; }
  .res-meta { display: flex; flex-direction: column; gap: 3px; min-width: 70px; }
  .res-amount { font-size: var(--fs-base); font-weight: 600; }
  .res-amount.neg { color: var(--danger); }
  .res-rate { font-size: var(--fs-xs); color: var(--ok); }
  .res-rate.neg { color: var(--danger); }
  .res .bar { width: 70px; height: 4px; }
  .res.full .res-amount { color: var(--warn); }
  .res.energy { gap: var(--sp-1); }

  .planet-select { width: auto; min-height: 34px; padding: var(--sp-1) var(--sp-2); font-size: var(--fs-sm); }
  .player { font-size: var(--fs-sm); }

  /* ---------- Angriffswarnung ---------- */
  .attack-banner {
    position: sticky; top: 0; z-index: 29;
    background: linear-gradient(90deg, rgba(255,77,125,0.28), rgba(255,77,125,0.08));
    border-bottom: 1px solid var(--danger);
    color: #ffd6e4;
    text-align: center;
    padding: var(--sp-2) var(--sp-4);
    font-size: var(--fs-sm);
    font-weight: 600;
    letter-spacing: 0.03em;
    animation: warn-pulse 1.8s ease infinite;
  }
  @keyframes warn-pulse {
    0%,100% { opacity: 0.85; }
    50% { opacity: 1; }
  }

  .body { display: flex; flex: 1; }

  /* ---------- Sidenav (Desktop) ---------- */
  .sidenav {
    width: 196px;
    flex: 0 0 196px;
    padding: var(--sp-3) var(--sp-2);
    border-right: 1px solid var(--border);
    background: rgba(12, 19, 32, 0.55);
    display: flex;
    flex-direction: column;
    gap: var(--sp-1);
  }
  .drawer-head { display: none; }
  .nav-group { display: flex; flex-direction: column; gap: 2px; margin-bottom: var(--sp-3); }
  .nav-group-label {
    font-family: var(--font-display);
    font-size: 0.62rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-faint);
    padding: var(--sp-2) var(--sp-3) var(--sp-1);
  }
  .nav-link {
    display: flex;
    align-items: center;
    gap: var(--sp-3);
    padding: var(--sp-2) var(--sp-3);
    border-radius: var(--r-md);
    color: var(--text-dim);
    font-size: var(--fs-sm);
    font-weight: 500;
    border: 1px solid transparent;
    position: relative;
    transition: background var(--motion-fast) var(--ease-out), color var(--motion-fast) var(--ease-out);
  }
  .nav-link:hover { background: rgba(255,255,255,0.04); color: var(--text); }
  .nav-link.active {
    background: var(--accent-soft);
    color: var(--accent-strong);
  }
  .nav-link.active::before {
    content: '';
    position: absolute; left: 0; top: 18%; bottom: 18%;
    width: 3px; border-radius: var(--r-pill);
    background: var(--accent);
    box-shadow: var(--glow-soft);
  }
  .nav-glyph {
    width: 1.5rem; height: 1.5rem; flex: 0 0 auto;
    display: inline-flex; align-items: center; justify-content: center;
  }
  .nav-ico { width: 21px; height: 21px; object-fit: contain; filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5)); }
  .nav-glyph-fallback { display: none; font-size: 1.05rem; }
  .nav-label { flex: 1; }
  .badge {
    background: var(--danger);
    color: #fff;
    font-size: var(--fs-xs);
    font-weight: 700;
    border-radius: var(--r-pill);
    padding: 1px 6px;
    min-width: 18px;
    text-align: center;
  }

  .content { flex: 1; min-width: 0; padding: var(--sp-4); width: 100%; }

  /* ---------- Kolonien-Leiste (Desktop) ---------- */
  .colony-rail {
    width: 158px;
    flex: 0 0 158px;
    padding: var(--sp-3) var(--sp-2);
    border-left: 1px solid var(--border);
    background: rgba(12, 19, 32, 0.55);
    display: flex;
    flex-direction: column;
    gap: 2px;
  }
  .rail-title {
    font-family: var(--font-display);
    font-size: 0.62rem;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    color: var(--text-faint);
    padding: 0 var(--sp-3) var(--sp-2);
  }
  .colony {
    display: flex; flex-direction: column; align-items: flex-start; gap: 2px;
    width: 100%; text-align: left;
    padding: var(--sp-2) var(--sp-3);
    border-radius: var(--r-md);
    border: 1px solid transparent;
    background: transparent;
    color: var(--text-dim);
    cursor: pointer;
    position: relative;
    transition: background var(--motion-fast) var(--ease-out), color var(--motion-fast) var(--ease-out);
  }
  .colony:hover { background: rgba(255,255,255,0.04); color: var(--text); }
  .colony.active { background: var(--accent-soft); color: var(--accent-strong); }
  .colony.active::before {
    content: ''; position: absolute; left: 0; top: 18%; bottom: 18%;
    width: 3px; border-radius: var(--r-pill); background: var(--accent); box-shadow: var(--glow-soft);
  }
  .colony-name { font-size: var(--fs-sm); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; max-width: 100%; }
  .colony-coords { font-size: 0.66rem; opacity: 0.75; }

  /* Auf Desktop: kein Topbar-Dropdown (Kolonien-Leiste uebernimmt), keine Bottom-Nav. */
  .planet-select { display: none; }
  .bottomnav { display: none; }
  .scrim { display: none; }

  /* ============================================================
     Mobile (<900px): Drawer-Sidenav + persistente Bottom-Tab-Bar
     ============================================================ */
  @media (max-width: 899px) {
    .res-bar { order: 3; width: 100%; justify-content: space-around; gap: var(--sp-3); }
    .res-meta { min-width: 52px; }
    .res .bar { width: 52px; }
    .player { display: none; }

    /* Sidenav wird zum Off-Canvas-Drawer ("Mehr"). */
    .sidenav {
      position: fixed; top: 0; bottom: 0; left: 0;
      width: 82vw; max-width: 320px;
      z-index: 60;
      transform: translateX(-100%);
      transition: transform var(--motion-base) var(--ease-out);
      background: rgba(8, 13, 24, 0.96);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-right: 1px solid var(--border-strong);
      overflow-y: auto;
      padding: var(--sp-3);
    }
    .sidenav.open { transform: translateX(0); }
    .drawer-head {
      display: flex; align-items: center; justify-content: space-between;
      margin-bottom: var(--sp-3); padding-bottom: var(--sp-3);
      border-bottom: 1px solid var(--border);
    }
    .drawer-title {
      font-family: var(--font-display); font-size: var(--fs-xs);
      letter-spacing: 0.16em; text-transform: uppercase; color: var(--text-dim);
    }
    .drawer-close { min-height: 36px; }
    .nav-link { min-height: 44px; font-size: var(--fs-base); }

    .colony-rail { display: none; }
    .planet-select { display: inline-block; }

    .scrim {
      display: block; position: fixed; inset: 0;
      background: rgba(0,0,0,0.55); z-index: 55;
    }

    .content { padding: var(--sp-3); padding-bottom: calc(64px + env(safe-area-inset-bottom)); }

    /* Persistente Bottom-Tab-Bar */
    .bottomnav {
      display: flex;
      position: fixed; left: 0; right: 0; bottom: 0; z-index: 40;
      background: rgba(8, 13, 24, 0.92);
      backdrop-filter: blur(16px) saturate(1.2);
      -webkit-backdrop-filter: blur(16px) saturate(1.2);
      border-top: 1px solid var(--border-strong);
      padding-bottom: env(safe-area-inset-bottom);
    }
    .bn-item {
      flex: 1 1 0;
      display: flex; flex-direction: column; align-items: center; justify-content: center;
      gap: 2px;
      min-height: 56px;
      background: transparent; border: none; cursor: pointer;
      color: var(--text-faint);
      font-family: var(--font); font-size: 0.62rem; letter-spacing: 0.02em;
      text-decoration: none;
      transition: color var(--motion-fast) var(--ease-out);
    }
    .bn-item.active { color: var(--accent-strong); }
    .bn-glyph { position: relative; display: inline-flex; align-items: center; justify-content: center; height: 22px; font-size: 1.1rem; }
    .bn-ico { width: 22px; height: 22px; object-fit: contain; }
    .bn-item.active .bn-ico { filter: drop-shadow(0 0 6px rgba(47,227,210,0.6)); }
    .bn-label { line-height: 1; }
    .bn-dot {
      position: absolute; top: -2px; right: -4px;
      width: 8px; height: 8px; border-radius: var(--r-pill);
      background: var(--danger); border: 1px solid var(--bg-deep);
    }
  }
`;
