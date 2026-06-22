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
    /* Aeusserer Rahmen = Moral-Band; innerer Ring = Gueteklasse (--grade-ring). */
    border: 2px solid var(--band, var(--accent));
    box-shadow: 0 0 18px color-mix(in srgb, var(--band, var(--accent)) 45%, transparent),
      inset 0 0 0 4px color-mix(in srgb, var(--grade-ring, transparent) 90%, transparent),
      inset 0 0 14px color-mix(in srgb, var(--grade-ring, transparent) 45%, transparent);
  }
  .portrait.grade-e { --grade-ring: var(--text-faint); }
  .portrait.grade-d { --grade-ring: var(--ok); }
  .portrait.grade-c { --grade-ring: var(--info); }
  .portrait.grade-b { --grade-ring: var(--deuterium); }
  .portrait.grade-a { --grade-ring: var(--warn); }
  .portrait.grade-s { --grade-ring: var(--energy); }
  .portrait img { width: 100%; height: 100%; display: block; }
  .badges { display: flex; flex-wrap: wrap; gap: var(--sp-1); }
  .chip-ico {
    width: 1.15em; height: 1.15em; object-fit: contain;
    vertical-align: -0.2em; margin-right: 0.3em;
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5));
  }
  /* Grad-Chip: eine eigene Farbe je Guete (E..S). */
  .grade-chip { font-family: var(--font-display); font-weight: 800; color: var(--bg-deep); border: none; }
  .grade-chip.grade-e { background: var(--text-faint); }
  .grade-chip.grade-d { background: var(--ok); }
  .grade-chip.grade-c { background: var(--info); }
  .grade-chip.grade-b { background: var(--deuterium); }
  .grade-chip.grade-a { background: var(--warn); }
  /* S = Prestige-Gold, bewusst KEIN Magenta. */
  .grade-chip.grade-s { background: linear-gradient(135deg, var(--energy), var(--accent-strong)); color: var(--bg-deep); }
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

  /* --- Ausruestungs-Panel --- */
  .equip-panel { margin-top: var(--sp-4); }
  .equip-panel .panel-title { padding-bottom: var(--sp-2); margin-bottom: var(--sp-2); }
  .warn-text { color: var(--warn); }
  .slot-grid { display: grid; grid-template-columns: repeat(auto-fill, minmax(200px, 1fr)); gap: var(--sp-2); }
  .equip-slot {
    border: 1px solid var(--border); border-radius: var(--r-md);
    background: rgba(255,255,255,0.02); padding: var(--sp-2);
    display: flex; flex-direction: column; gap: var(--sp-1);
  }
  .equip-slot.filled { border-color: var(--accent-dim); background: var(--accent-soft); }
  .equip-slot.open { border-color: var(--accent); box-shadow: var(--glow); }
  .slot-btn {
    display: flex; align-items: center; gap: var(--sp-2); text-align: left;
    background: none; border: none; color: var(--text); cursor: pointer; padding: 0; width: 100%;
  }
  .slot-ico {
    position: relative; width: 38px; height: 38px; flex: 0 0 38px;
    display: flex; align-items: center; justify-content: center;
    border-radius: var(--r-sm); background: var(--surface-3); border: 1px solid var(--border); font-size: var(--fs-lg);
  }
  .slot-ico.sm { width: 28px; height: 28px; flex: 0 0 28px; font-size: var(--fs-md); }
  .slot-ico img { width: 26px; height: 26px; object-fit: contain; }
  .slot-ico.sm img { width: 20px; height: 20px; }
  .slot-glyph-fb { display: none; position: absolute; }
  .slot-meta { display: flex; flex-direction: column; gap: 1px; min-width: 0; }
  .slot-label {
    font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--text-dim);
  }
  .item-label { font-size: var(--fs-sm); font-weight: 600; line-height: 1.1; }
  .rar-tag { font-size: var(--fs-xs); }
  /* Raritaets-Farbcodierung (common grau, rare blau, epic violett/gold). */
  .rar.rar-common, .item-label.rar-common, .rar-tag.rar-common { color: var(--text-dim); }
  .rar.rar-rare, .item-label.rar-rare, .rar-tag.rar-rare { color: var(--info); }
  .rar.rar-epic, .item-label.rar-epic, .rar-tag.rar-epic { color: var(--energy); }
  .inv-opt.rar-rare { border-color: color-mix(in srgb, var(--info) 60%, var(--border)); }
  .inv-opt.rar-epic { border-color: color-mix(in srgb, var(--energy) 60%, var(--border)); }
  .item-bonus { display: flex; flex-wrap: wrap; gap: var(--sp-1); }
  .equip-slot .btn-sm { align-self: flex-start; }

  .inv-picker {
    display: flex; flex-direction: column; gap: var(--sp-1);
    border-top: 1px dashed var(--border); margin-top: var(--sp-1); padding-top: var(--sp-1);
  }
  .inv-opt {
    display: flex; align-items: center; gap: var(--sp-2); text-align: left; width: 100%;
    padding: var(--sp-1) var(--sp-2); border-radius: var(--r-sm);
    border: 1px solid var(--border); background: rgba(255,255,255,0.02); color: var(--text); cursor: pointer;
  }
  .inv-opt:hover { border-color: var(--accent); }
  .inv-opt-meta { display: flex; flex-direction: column; min-width: 0; }

  .set-progress { display: flex; flex-direction: column; gap: var(--sp-2); margin: var(--sp-3) 0; }
  .set-row { display: flex; gap: var(--sp-2); align-items: flex-start; }
  .set-ico {
    position: relative; width: 32px; height: 32px; flex: 0 0 32px;
    display: flex; align-items: center; justify-content: center;
    border-radius: var(--r-sm); background: var(--surface-3); border: 1px solid var(--border); font-size: var(--fs-md);
  }
  .set-ico img { width: 22px; height: 22px; object-fit: contain; }
  .set-body { flex: 1; min-width: 0; }
  .set-head { display: flex; gap: var(--sp-2); align-items: baseline; }
  .set-thresholds { display: flex; flex-direction: column; gap: var(--sp-1); margin-top: var(--sp-1); }
  .set-th { display: flex; flex-wrap: wrap; align-items: center; gap: var(--sp-1); opacity: 0.5; }
  .set-th.active { opacity: 1; }
  .set-th .th-n {
    font-family: var(--mono); font-size: var(--fs-xs);
    padding: 1px var(--sp-1); border-radius: var(--r-sm); border: 1px solid var(--border); color: var(--text-dim);
  }
  .set-th.active .th-n { border-color: var(--accent); color: var(--accent); }
  .chip.bonus.off { border-color: var(--border); color: var(--text-dim); background: transparent; }

  /* --- Meuterei-Warnbanner (Welle 2) --- */
  .mutiny-banner {
    margin-bottom: var(--sp-4); padding: var(--sp-3) var(--sp-4);
    border-radius: var(--r-md); border: 1px solid var(--warn);
    background: color-mix(in srgb, var(--warn) 12%, transparent);
    box-shadow: 0 0 14px color-mix(in srgb, var(--warn) 25%, transparent);
  }
  .mutiny-banner.acute {
    border-color: var(--danger);
    background: color-mix(in srgb, var(--danger) 16%, transparent);
    box-shadow: 0 0 20px color-mix(in srgb, var(--danger) 38%, transparent);
    animation: mutinyPulse 1.8s ease-in-out infinite;
  }
  @keyframes mutinyPulse {
    0%, 100% { box-shadow: 0 0 16px color-mix(in srgb, var(--danger) 30%, transparent); }
    50% { box-shadow: 0 0 28px color-mix(in srgb, var(--danger) 55%, transparent); }
  }
  .mutiny-banner .mb-title {
    font-family: var(--font-display); font-weight: 800; font-size: var(--fs-lg);
    color: var(--warn); letter-spacing: 0.02em;
  }
  .mutiny-banner.acute .mb-title { color: var(--danger); }
  .mutiny-banner .mb-body { margin: var(--sp-1) 0 0; font-size: var(--fs-sm); color: var(--text-dim); }

  /* --- Rechte Spalte: Innenleben + Historie --- */
  .col-right { display: flex; flex-direction: column; gap: var(--sp-4); min-width: 0; }
  .innenleben { display: flex; flex-direction: column; gap: var(--sp-3); }
  .il-block { display: flex; flex-direction: column; gap: var(--sp-2); }
  .il-head {
    font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase;
    letter-spacing: 0.08em; color: var(--text-dim);
    border-bottom: 1px solid var(--border); padding-bottom: var(--sp-1);
  }

  /* Erinnerungs-Narrativ */
  .memory-summary {
    margin: 0; padding: var(--sp-3); border-left: 3px solid var(--accent);
    background: var(--accent-soft); border-radius: var(--r-sm);
    font-style: italic; color: var(--text); line-height: 1.5;
  }

  /* Groll */
  .grievance-list { list-style: none; margin: 0; padding: 0; display: flex; flex-direction: column; gap: var(--sp-1); }
  .grievance {
    display: flex; align-items: center; gap: var(--sp-2);
    padding: var(--sp-1) var(--sp-2); border-radius: var(--r-sm);
    border: 1px solid color-mix(in srgb, var(--warn) 40%, var(--border));
    background: color-mix(in srgb, var(--warn) 6%, transparent);
  }
  .grievance.sev-high { border-color: var(--danger); background: color-mix(in srgb, var(--danger) 8%, transparent); }
  .grievance .g-dot { width: 8px; height: 8px; flex: 0 0 8px; border-radius: var(--r-pill); background: var(--warn); }
  .grievance.sev-high .g-dot { background: var(--danger); }
  .grievance .g-label { flex: 1; font-size: var(--fs-sm); }
  .grievance .g-count { font-family: var(--mono); font-size: var(--fs-xs); color: var(--warn); }
  .grievance .g-sev { font-family: var(--mono); font-size: var(--fs-xs); color: var(--text-dim); }

  /* Meinungen & Beziehungen (gemeinsame Optik) */
  .opinion, .relation {
    display: flex; flex-direction: column; gap: 4px;
    padding: var(--sp-2); border-radius: var(--r-sm);
    border: 1px solid var(--border); background: rgba(255,255,255,0.02);
    margin-bottom: var(--sp-1); text-decoration: none; color: var(--text);
  }
  .relation { cursor: pointer; }
  .relation:hover { border-color: var(--accent); }
  .opinion.hated { border-color: var(--danger); background: color-mix(in srgb, var(--danger) 8%, transparent); }
  .op-row { display: flex; align-items: center; gap: var(--sp-1); flex-wrap: wrap; }
  .op-verb {
    font-family: var(--font-display); font-weight: 700; font-size: var(--fs-sm);
  }
  .op-target { font-weight: 600; font-size: var(--fs-sm); }
  .op-kind { margin-left: auto; }
  .rel-arrow { margin-left: auto; color: var(--text-faint); }
  .archenemy {
    font-family: var(--font-display); font-weight: 800; font-size: var(--fs-xs);
    color: var(--danger); letter-spacing: 0.04em;
  }
  /* Stimmungs-/Beziehungs-Farben fuer Verb + Balken */
  .op-respects, .rel-respect, .rel-bond { color: var(--ok); }
  .op-fears, .op-despises, .rel-grudge { color: var(--danger); }
  .op-envies, .rel-rivalry { color: var(--warn); }
  .op-bar { height: 6px; }
  .op-bar .fill { display: block; height: 100%; border-radius: var(--r-pill); background: var(--accent); }
  .op-bar.op-respects .fill, .op-bar.rel-respect .fill, .op-bar.rel-bond .fill { background: var(--ok); }
  .op-bar.op-fears .fill, .op-bar.op-despises .fill, .op-bar.rel-grudge .fill { background: var(--danger); }
  .op-bar.op-envies .fill, .op-bar.rel-rivalry .fill { background: var(--warn); }

  /* Gedaechtnis-Timeline (sentiment-gefaerbt) */
  .mem-timeline { list-style: none; margin: 0; padding: 0; position: relative; }
  .mem-timeline::before {
    content: ''; position: absolute; left: 5px; top: 6px; bottom: 6px; width: 2px; background: var(--border);
  }
  .mem { position: relative; padding: 0 0 var(--sp-3) var(--sp-4); }
  .mem .mem-dot {
    position: absolute; left: 0; top: 4px; width: 12px; height: 12px;
    border-radius: var(--r-pill); border: 2px solid var(--bg); background: var(--text-faint);
  }
  .mem.sent-positive .mem-dot { background: var(--ok); box-shadow: 0 0 8px var(--ok); }
  .mem.sent-negative .mem-dot { background: var(--danger); box-shadow: 0 0 8px var(--danger); }
  .mem.sent-neutral .mem-dot { background: var(--text-dim); }
  .mem-entry { border-left: 2px solid transparent; padding-left: var(--sp-2); }
  .mem.sent-positive .mem-entry { border-left-color: color-mix(in srgb, var(--ok) 50%, transparent); }
  .mem.sent-negative .mem-entry { border-left-color: color-mix(in srgb, var(--danger) 50%, transparent); }
  .mem-ctx { color: var(--text-dim); margin: 2px 0 0; }

  /* Gefahrenzone: Kommandeur entlassen */
  .danger-zone {
    margin-top: var(--sp-5); padding: var(--sp-4);
    border: 1px solid color-mix(in srgb, var(--danger) 45%, var(--border));
    border-radius: var(--r-2); background: color-mix(in srgb, var(--danger) 6%, transparent);
  }
  .danger-zone h3 { margin: 0 0 var(--sp-2); color: var(--danger); letter-spacing: 0.04em; }
  .danger-warn { margin: 0 0 var(--sp-3); color: var(--text-dim); }
  .danger-actions { display: flex; gap: var(--sp-2); flex-wrap: wrap; }
  .danger-btn {
    padding: var(--sp-2) var(--sp-3); border-radius: var(--r-1); cursor: pointer;
    border: 1px solid var(--danger); color: var(--danger); font-weight: 600;
    background: color-mix(in srgb, var(--danger) 12%, transparent);
  }
  .danger-btn:hover:not([disabled]) { background: color-mix(in srgb, var(--danger) 24%, transparent); }
  .danger-btn[disabled] { opacity: 0.5; cursor: not-allowed; }
  .ghost-btn {
    padding: var(--sp-2) var(--sp-3); border-radius: var(--r-1); cursor: pointer;
    border: 1px solid var(--border); color: var(--text-dim); background: transparent;
  }
  .ghost-btn:hover:not([disabled]) { color: var(--text); border-color: var(--text-dim); }
`;
