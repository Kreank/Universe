export const galaxyStyles = `
  .sub { color: var(--text-dim); margin: calc(-1 * var(--sp-1)) 0 var(--sp-4); font-size: var(--fs-sm); }
  .small { font-size: var(--fs-xs); }
  .layout {
    grid-template-columns: minmax(340px, 1.5fr) minmax(280px, 1fr);
    align-items: start;
  }

  /* --- Scanner-Navigation --- */
  .gx-nav { display: flex; align-items: flex-end; gap: var(--sp-2); flex-wrap: wrap; }
  .coordbox { display: flex; flex-direction: column; gap: var(--sp-1); }
  .coordbox label {
    font-family: var(--font-display);
    font-size: var(--fs-xs); color: var(--text-dim);
    text-transform: uppercase; letter-spacing: 0.1em;
  }
  .coordbox input {
    width: 72px; min-height: 32px; padding: var(--sp-1) var(--sp-2);
    font-family: var(--mono); font-variant-numeric: tabular-nums; text-align: center;
  }
  .coords-current {
    color: var(--text-faint); margin: var(--sp-3) 0 var(--sp-3); font-size: var(--fs-sm);
  }

  /* --- Scanner: cinematischer Tiefenraum (DER atmosphaerische Screen) --- */
  .scanner { position: relative; isolation: isolate; overflow: hidden; }
  .scanner::before {
    content: '';
    position: absolute; inset: 0; border-radius: inherit;
    background:
      linear-gradient(to bottom,
        color-mix(in srgb, var(--surface-1) 86%, transparent),
        color-mix(in srgb, var(--bg-deep) 92%, transparent)),
      url('/assets/img/backgrounds/system_view.png') center / cover no-repeat;
    opacity: 0.55; z-index: -1; pointer-events: none;
  }
  /* Dezenter Akzent-Lichtschein oben rechts — EIN gezieltes Tiefe-Motiv, kein Flaechenglow. */
  .scanner::after {
    content: '';
    position: absolute; inset: 0; border-radius: inherit;
    background: radial-gradient(420px 300px at 88% -10%, var(--accent-soft), transparent 70%);
    z-index: -1; pointer-events: none;
  }

  /* --- Kompakte Positions-Zeilen (OGame-Tabellen-Stil) --- */
  .positions { display: flex; flex-direction: column; gap: var(--sp-1); }
  .row {
    position: relative;
    display: grid;
    grid-template-columns: 26px 34px 1fr auto;
    align-items: center;
    gap: var(--sp-2);
    padding: var(--sp-1) var(--sp-2);
    border: 1px solid transparent;
    border-radius: var(--r-sm);
    min-height: 40px;
    transition: border-color var(--motion-fast) var(--ease-out),
      background var(--motion-fast) var(--ease-out);
  }
  .row.occupied {
    border-color: var(--border);
    background: color-mix(in srgb, var(--surface-2) 80%, transparent);
  }
  .row.occupied:hover { border-color: var(--border-strong); }
  .row.npc {
    border-color: var(--danger-dim);
    background: color-mix(in srgb, var(--danger) 7%, var(--surface-2));
  }
  .row.player { border-color: var(--border-strong); }
  .row.own {
    border-color: var(--accent);
    background: color-mix(in srgb, var(--accent) 9%, var(--surface-2));
  }
  .row.empty { opacity: 0.4; min-height: 26px; padding: 2px var(--sp-2); }
  .row.empty:hover { opacity: 0.7; }

  .pos { font-family: var(--mono); font-variant-numeric: tabular-nums; font-size: var(--fs-xs); color: var(--text-dim); text-align: center; }
  .vis { position: relative; display: flex; align-items: center; justify-content: center; width: 34px; height: 34px; }
  .vis-img {
    width: 32px; height: 32px; object-fit: contain;
    filter: drop-shadow(0 1px 3px rgba(0,0,0,0.5));
    transition: transform var(--motion-base) var(--ease-out), filter var(--motion-base) var(--ease-out);
  }
  /* Gestuftes Tiefe-/Glow-Motiv NUR fuer belegte Planeten-Slots (eigene/NPC), dezent + auf Hover verstaerkt. */
  .row.own .vis::before,
  .row.npc .vis::before {
    content: '';
    position: absolute; inset: -6px; border-radius: var(--r-pill);
    opacity: 0.35;
    z-index: -1;
    transition: opacity var(--motion-base) var(--ease-out), transform var(--motion-base) var(--ease-out);
  }
  .row.own .vis::before { background: radial-gradient(circle, var(--accent-soft), transparent 70%); }
  .row.npc .vis::before { background: radial-gradient(circle, color-mix(in srgb, var(--danger) 16%, transparent), transparent 70%); }
  .row.own:hover .vis::before,
  .row.npc:hover .vis::before { opacity: 0.8; transform: scale(1.15); }
  .row.own:hover .vis-img,
  .row.npc:hover .vis-img { transform: scale(1.06); }
  .vis-dot { width: 6px; height: 6px; border-radius: var(--r-pill); background: var(--text-faint); opacity: 0.4; }

  .info { display: flex; align-items: baseline; gap: var(--sp-2); min-width: 0; }
  .kind { font-size: var(--fs-sm); white-space: nowrap; }
  .name { font-size: var(--fs-sm); color: var(--text-faint); overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }

  .acts { display: flex; align-items: center; gap: var(--sp-1); justify-content: flex-end; flex-wrap: wrap; }
  .ic {
    display: inline-flex; align-items: center; justify-content: center;
    width: 30px; height: 30px; border-radius: var(--r-sm); cursor: pointer; font-size: var(--fs-md);
    background: rgba(255,255,255,0.05); border: 1px solid var(--border); color: var(--text);
    transition: background var(--motion-fast) var(--ease-out),
      border-color var(--motion-fast) var(--ease-out),
      color var(--motion-fast) var(--ease-out),
      transform var(--motion-fast) var(--ease-out);
  }
  .ic:hover { background: rgba(255,255,255,0.12); }
  .ic:active { transform: translateY(1px); }
  .ic.spy:hover { border-color: var(--accent); color: var(--accent); }
  .ic.msg:hover { border-color: var(--accent); color: var(--accent); }
  .ic.phx:hover { border-color: var(--accent); color: var(--accent); }
  .ic.atk:hover { border-color: var(--danger); color: var(--danger); }
  .ic.trp:hover { border-color: var(--ok); color: var(--ok); }
  .ic.mine:hover { border-color: var(--warn); color: var(--warn); }
  .ic.col:hover { border-color: var(--ok); color: var(--ok); }
  .ic.exp:hover { border-color: var(--accent); color: var(--accent); }

  .chip {
    color: var(--text-dim); font-size: var(--fs-xs);
    border: 1px solid var(--border); border-radius: var(--r-pill);
    padding: 2px var(--sp-2); white-space: nowrap;
  }
  .chip.disc { color: var(--accent); border-color: var(--accent-dim); cursor: help; }
  .chip.own { color: var(--accent); border-color: var(--accent-dim); }
  .chip.lvl { color: var(--accent); border-color: var(--accent-dim); margin-right: var(--sp-1); }
  .chip.trade { color: var(--accent); border-color: var(--accent-dim); background: var(--accent-soft); cursor: help; margin-right: var(--sp-1); }
  .chip.rock { color: var(--warn); border-color: color-mix(in srgb, var(--warn) 55%, transparent); background: color-mix(in srgb, var(--warn) 10%, transparent); cursor: help; margin-right: var(--sp-1); }
  .chip.moon { color: var(--text-dim); border-color: var(--border-strong); background: rgba(255,255,255,0.04); cursor: help; margin-right: var(--sp-1); }
  .chip.station { color: var(--warn); border-color: color-mix(in srgb, var(--warn) 55%, transparent); background: color-mix(in srgb, var(--warn) 10%, transparent); cursor: help; margin-right: var(--sp-1); }
  .chip.station.mine { color: var(--accent); border-color: var(--accent-dim); background: var(--accent-soft); }
  .chip.debris {
    color: #ff9d6e; border-color: color-mix(in srgb, #ff7a45 55%, transparent);
    background: color-mix(in srgb, #ff7a45 12%, transparent); cursor: help; margin-right: var(--sp-1);
  }
  .chip.event {
    color: #ffd27d; border-color: color-mix(in srgb, #ffae3b 60%, transparent);
    background: color-mix(in srgb, #ffae3b 14%, transparent); cursor: help; margin-right: var(--sp-1);
    font-weight: 600; animation: chipEventGlow 1.8s ease-in-out infinite;
  }
  @keyframes chipEventGlow { 0%, 100% { box-shadow: 0 0 0 transparent; } 50% { box-shadow: 0 0 10px color-mix(in srgb, #ffae3b 45%, transparent); } }
  @media (prefers-reduced-motion: reduce) { .chip.event { animation: none; } }

  /* --- Ziel-Verzeichnis (kompakt, OGame-artig) --- */
  .tgt-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; }
  .tgt {
    display: flex; flex-direction: column; gap: var(--sp-1);
    padding: var(--sp-2) 0;
    border-bottom: 1px solid var(--border);
  }
  .tgt:last-child { border-bottom: none; }
  .tgt-top { display: flex; align-items: center; gap: var(--sp-2); flex-wrap: wrap; }
  .tgt-name { font-family: var(--font-display); font-weight: 600; font-size: var(--fs-base); }
  .tgt-coords { margin-left: auto; color: var(--text-faint); font-size: var(--fs-xs); }
  .tgt-sub { display: flex; align-items: center; gap: var(--sp-3); color: var(--text-dim); }
  .tgt-stat { display: inline-flex; align-items: center; gap: 4px; font-variant-numeric: tabular-nums; }
  .tgt-stat.tip { cursor: help; }
  .tgt-acts { justify-content: flex-start; margin-top: 2px; }
  .ic.trd:hover { border-color: var(--accent); color: var(--accent); }

  @media (max-width: 720px) {
    .layout { grid-template-columns: 1fr; }
    /* Touch-Targets >= 44px auf Mobile. */
    .ic { width: 44px; height: 44px; }
    .coordbox input { min-height: 44px; }
    /* Mobile: Name + Chips bekommen die volle Breite (Chips duerfen umbrechen), die
       Aktions-Buttons rutschen auf eine eigene Zeile darunter -> kein Zeilen-Ueberlauf
       mehr durch den Truemmerfeld-Chip + Recycler-Button. */
    .row { grid-template-columns: 26px 34px 1fr; }
    .info { flex-wrap: wrap; row-gap: 2px; }
    .acts { grid-column: 1 / -1; justify-content: flex-start; margin-top: var(--sp-1); }
  }
  .zone-banner { display: flex; flex-wrap: wrap; gap: var(--sp-1); margin: var(--sp-1) 0 var(--sp-2); }
  .zone-chip { display: inline-flex; align-items: center; gap: 6px; padding: 2px 8px; border-radius: 999px;
    border: 1px solid rgba(255,170,80,.5); background: rgba(255,170,80,.08); }
  .zone-chip.mine { border-color: rgba(46,230,214,.6); background: rgba(46,230,214,.10); }
  .zone-mark { width: 18px; height: 18px; object-fit: contain;
    filter: sepia(1) saturate(3) hue-rotate(330deg); }
  .zone-chip.mine .zone-mark { filter: none; }
  .zone-tag { font-weight: 600; letter-spacing: .04em; }
  /* Welle 5: Konjunktions-Marker (wandernde Galaxie) */
  .conj-banner { display: flex; flex-wrap: wrap; gap: var(--sp-1); margin: var(--sp-1) 0 var(--sp-2); }
  .conj-chip { display: inline-flex; align-items: center; gap: 4px; padding: 2px 8px; border-radius: 999px;
    font-size: var(--fs-xs); font-variant-numeric: tabular-nums;
    color: #3ddc97; border: 1px solid rgba(61,220,151,.4); background: rgba(61,220,151,.08); }
  .conj-chip.bane { color: var(--text-dim); border-color: var(--border); background: rgba(255,255,255,.03); }
  /* W1: NPC-/Spieler-Ziel-Aktionen sind in den Ziele-Screen gewandert — dezenter Verweis. */
  .acts.steer { gap: var(--sp-2); }
  .steer-hint { font-size: var(--fs-xs); color: var(--text-dim); text-decoration: none; white-space: nowrap;
    border: 1px solid var(--border); border-radius: 999px; padding: 2px 10px; background: rgba(255,255,255,.03);
    transition: color var(--motion-fast) var(--ease-out), border-color var(--motion-fast) var(--ease-out); }
  .steer-hint:hover { color: var(--accent); border-color: var(--accent-dim); background: var(--accent-soft); }
  .steer-card { display: flex; flex-direction: column; gap: var(--sp-2); align-items: flex-start; }
  .steer-card .btn { align-self: flex-start; }
`;
