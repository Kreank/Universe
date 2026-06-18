export const dashboardStyles = `
  .sub { margin-top: calc(-1 * var(--sp-1)); font-size: var(--fs-sm); }
  .planet-name { color: var(--text); font-weight: 600; }
  /* Inline-Umbenennung des Planeten */
  .rename-inp {
    font: inherit; color: var(--text); width: min(220px, 50vw);
    background: var(--surface-1); border: 1px solid var(--accent); border-radius: var(--r-sm);
    padding: 1px var(--sp-2);
  }
  .rename-inp:focus { outline: none; box-shadow: var(--glow-soft); }
  .name-btn {
    font: inherit; cursor: pointer; color: var(--text-faint);
    background: none; border: none; padding: 0 4px; line-height: 1;
    transition: color var(--motion-fast) var(--ease-out);
  }
  .name-btn:hover { color: var(--accent); }
  .name-btn.ok:hover { color: var(--ok); }
  .moon-chip {
    font: inherit; cursor: pointer;
    color: var(--accent); background: var(--accent-soft);
    border: 1px solid var(--accent-dim); border-radius: var(--r-pill);
    padding: 1px var(--sp-2); margin-left: var(--sp-1);
  }
  .moon-chip:hover { background: color-mix(in srgb, var(--accent) 22%, transparent); }
  .moon-chip.jump {
    color: var(--warn); border-color: color-mix(in srgb, var(--warn) 55%, transparent);
    background: color-mix(in srgb, var(--warn) 12%, transparent);
  }
  .moon-chip.jump:hover { background: color-mix(in srgb, var(--warn) 22%, transparent); }

  /* Imperiums-Punkte-Hero — prominent, gut erkennbar, klickbar. */
  .score-hero {
    display: flex; align-items: center; gap: var(--sp-4); flex-wrap: wrap;
    margin: var(--sp-1) 0 var(--sp-4);
    padding: var(--sp-4) var(--sp-5); border-radius: var(--r-lg);
    background: linear-gradient(135deg, var(--accent-soft), var(--surface-1));
    border: 1px solid color-mix(in srgb, var(--accent) 36%, transparent);
    box-shadow: var(--e1), inset 0 0 22px rgba(47,227,210,0.07);
    color: var(--text); text-decoration: none;
    transition: border-color var(--motion-base) var(--ease-out), box-shadow var(--motion-base) var(--ease-out);
  }
  .score-hero:hover {
    border-color: var(--accent);
    box-shadow: var(--glow-soft), inset 0 0 22px rgba(47,227,210,0.12);
  }
  .score-ico {
    width: 52px; height: 52px; object-fit: contain; flex: 0 0 auto;
    filter: drop-shadow(0 2px 5px rgba(0,0,0,0.6));
  }
  .score-main { display: flex; flex-direction: column; line-height: 1.1; }
  .score-label {
    font-family: var(--font-display);
    font-size: var(--fs-xs); letter-spacing: 0.12em; text-transform: uppercase;
    color: var(--text-dim);
  }
  .score-value {
    font-family: var(--font-display);
    font-size: var(--fs-2xl); font-weight: 700; color: var(--accent-strong);
    font-variant-numeric: tabular-nums;
    text-shadow: 0 0 14px rgba(47,227,210,0.4);
  }
  .score-rank {
    display: flex; flex-direction: column; align-items: center; line-height: 1.1;
    padding: 0 var(--sp-3); border-left: 1px solid var(--border);
  }
  .rank-big { font-family: var(--font-display); font-size: var(--fs-xl); font-weight: 700; }
  .score-breakdown { display: flex; flex-wrap: wrap; gap: var(--sp-2); flex: 1; }
  .score-breakdown .bd {
    font-size: var(--fs-sm); padding: 2px var(--sp-2); border-radius: var(--r-sm);
    background: rgba(255,255,255,0.05); border: 1px solid var(--border);
    white-space: nowrap; font-variant-numeric: tabular-nums;
  }
  .score-cta { margin-left: auto; align-self: flex-end; }
  @media (max-width: 640px) {
    .score-value { font-size: var(--fs-xl); }
    .score-cta { display: none; }
  }
  /* Zwei feste, oben ausgerichtete Spalten — balanciert, keine toten Flaechen */
  .cols {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: var(--sp-3);
    align-items: start;
  }
  .col { display: flex; flex-direction: column; gap: var(--sp-3); min-width: 0; }
  @media (max-width: 900px) {
    .cols { grid-template-columns: 1fr; gap: var(--sp-4); }
    .col { gap: var(--sp-4); }
  }
  .res-grid { display: flex; flex-direction: column; gap: var(--sp-3); }
  .res-card { display: flex; flex-direction: column; gap: var(--sp-2); }
  .res-card.energy { border-top: 1px solid var(--border); padding-top: var(--sp-3); }
  .small { font-size: var(--fs-sm); }
  .ops-block { display: flex; flex-direction: column; gap: var(--sp-1); }
  .ops-label {
    font-family: var(--font-display);
    font-size: var(--fs-xs); letter-spacing: 0.1em; color: var(--text-dim);
    margin-bottom: 2px;
  }
  .queue-row .chip { margin-left: var(--sp-2); }
  .ok { color: var(--ok); }
  .neg { color: var(--danger); }

  /* --- Hover-Aufschluesselung der Flotte (Schiffe + Fracht) --- */
  .has-tip { position: relative; }
  .fleet-tip {
    position: absolute;
    top: calc(100% + var(--sp-1)); left: 0;
    z-index: 30;
    min-width: 210px; max-width: 320px;
    padding: var(--sp-2) var(--sp-3);
    background: var(--surface-2, var(--surface-1));
    border: 1px solid var(--border);
    border-radius: var(--radius-2, 8px);
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.45);
    opacity: 0; visibility: hidden; transform: translateY(-4px);
    transition: opacity .12s ease, transform .12s ease, visibility .12s;
    pointer-events: none;
  }
  .has-tip:hover .fleet-tip,
  .has-tip:focus-within .fleet-tip {
    opacity: 1; visibility: visible; transform: translateY(0);
  }
  .tip-head {
    font-family: var(--font-display); font-weight: 600;
    font-size: var(--fs-sm); margin-bottom: var(--sp-2);
    padding-bottom: var(--sp-1); border-bottom: 1px solid var(--border);
    white-space: nowrap;
  }
  .tip-sec { margin-top: var(--sp-2); }
  .tip-sec:first-of-type { margin-top: 0; }
  .tip-sec-title {
    font-size: var(--fs-xs, .72rem); text-transform: uppercase;
    letter-spacing: .04em; color: var(--text-dim); margin-bottom: var(--sp-1);
  }
  .tip-row {
    display: flex; justify-content: space-between; gap: var(--sp-3);
    font-size: var(--fs-sm); padding: 1px 0;
  }
  .tip-row.muted { color: var(--text-dim); justify-content: flex-start; }

  .queue-row, .alert, .cmd-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: var(--sp-3);
    flex-wrap: wrap;
    padding: var(--sp-2) 0;
    font-size: var(--fs-sm);
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }
  /* Live-Frachtbalken einer schürfenden Flotte (eigene Zeile unter der Bewegung). */
  .mine-bar { flex-basis: 100%; display: flex; align-items: center; gap: var(--sp-2); margin-top: 2px; }
  .mb-track { flex: 1; height: 5px; background: rgba(255,255,255,0.08); border-radius: 999px; overflow: hidden; }
  .mb-fill { display: block; height: 100%; border-radius: 999px;
    background: linear-gradient(90deg, var(--accent-dim), var(--accent)); transition: width var(--motion-base) var(--ease-out); }
  .mb-amt { font-size: var(--fs-xs); color: var(--text-dim); white-space: nowrap; }
  .alert { border-bottom: none; }
  .alert.danger { color: #ffb3d0; }
  .alert.decision { color: var(--accent); }
  hr { border: none; border-top: 1px solid var(--border); margin: var(--sp-2) 0; }

  .cmd-row { text-decoration: none; color: var(--text); }

  /* Verteidigungs-Übersicht (Anzahl je Typ) */
  .def-row {
    display: flex; align-items: center; justify-content: space-between; gap: var(--sp-3);
    padding: var(--sp-1) 0; font-size: var(--fs-sm);
    border-bottom: 1px solid rgba(255,255,255,0.05);
  }
  .def-name { display: inline-flex; align-items: center; gap: var(--sp-2); min-width: 0; }
  .def-count { color: var(--text); font-weight: 600; }
  .def-row.def-total { border-bottom: none; border-top: 1px solid var(--border-strong); margin-top: 2px; }
  .def-row.def-total .def-count { color: var(--accent); }

  /* Laufender Prozess als Deeplink (Dashboard -> Forschung/Gebaeude/Werft mit Highlight). */
  .queue-row.link {
    text-decoration: none; color: var(--text); cursor: pointer;
    border-radius: var(--r-sm); padding-left: var(--sp-2); padding-right: var(--sp-2);
    margin: 0 calc(-1 * var(--sp-2));
    transition: background var(--motion-fast) var(--ease-out), color var(--motion-fast) var(--ease-out);
  }
  .queue-row.link:hover { background: rgba(255,255,255,0.05); color: var(--accent); }
  /* Serielle Werft-Schlange: aktiver vs. wartender Auftrag klar markieren. */
  .queue-row.q-waiting { opacity: 0.65; }
  .q-tag {
    font-size: var(--fs-xs); font-weight: 600; padding: 0 var(--sp-2); border-radius: var(--r-pill);
    margin-left: var(--sp-1); white-space: nowrap;
  }
  .q-tag.build { color: #04201d; background: var(--accent); }
  .q-tag.wait { color: var(--text-dim); background: rgba(255,255,255,0.06); border: 1px solid var(--border-strong); }
  .cmd-row:hover { background: rgba(255,255,255,0.04); border-radius: var(--r-sm); }
  .cmd-name { font-size: var(--fs-base); }
  .cmd-morale {
    display: inline-flex; align-items: center; gap: var(--sp-2);
    font-size: var(--fs-sm); color: var(--band);
  }
  .cmd-morale .dot {
    width: 8px; height: 8px; border-radius: var(--r-pill); background: var(--band);
    box-shadow: 0 0 8px var(--band);
  }
  .span-line { margin-top: var(--sp-3); }
`;
