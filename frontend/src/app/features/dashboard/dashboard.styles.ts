export const dashboardStyles = `
  /* Flotten-Slot-Kopfzeile in den Flottenbewegungen */
  .slots-title-row { display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-2); flex-wrap: wrap; }
  .slots-title-row app-fleet-slots { display: inline; font-weight: 400; }

  /* Welle 5: Konjunktions-Karte (wandernde Galaxie) */
  .conj-card { margin-bottom: var(--sp-4); }
  .conj-card .panel-title { display: flex; align-items: baseline; gap: var(--sp-2); }
  .conj-block + .conj-block { margin-top: var(--sp-3); }
  .conj-head {
    text-transform: uppercase; letter-spacing: 0.1em; margin-bottom: var(--sp-1);
  }
  .conj-row {
    display: flex; align-items: center; flex-wrap: wrap; gap: var(--sp-2) var(--sp-3);
    padding: var(--sp-1) 0; border-top: 1px solid var(--border);
  }
  .conj-row:first-of-type { border-top: none; }
  .conj-row.upcoming { opacity: 0.85; }
  .conj-route { display: inline-flex; align-items: center; gap: var(--sp-1); font-variant-numeric: tabular-nums; }
  .conj-arrow { color: var(--text-faint); }
  .conj-disc {
    font-variant-numeric: tabular-nums; font-weight: 600;
    padding: 1px var(--sp-2); border-radius: var(--r-pill);
    background: rgba(255,255,255,0.04); border: 1px solid var(--border);
  }
  .conj-disc.boon { color: #3ddc97; border-color: rgba(61,220,151,0.35); }
  .conj-disc.bane { color: var(--text-dim); }
  .conj-cd { margin-left: auto; color: var(--text-dim); white-space: nowrap; }
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
  /* Klickbare Zielkoordinaten -> Galaxie-Karte. */
  .coord-link { color: var(--text-dim); text-decoration: none; border-bottom: 1px dotted var(--border-strong); }
  .coord-link:hover { color: var(--accent); border-bottom-color: var(--accent); }
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
  .mb-deut { color: var(--text-faint); font-style: italic; }
  .alert { border-bottom: none; }
  .alert.danger { color: #ffb3d0; }
  .alert.decision { color: var(--accent); }
  /* Eingehender Angriff: Kopfzeile + Flotten-Zusammensetzung (aus der Aufklaerung). */
  .attack-alert { flex-direction: column; align-items: stretch; gap: var(--sp-1); }
  .attack-alert .aa-head { display: flex; align-items: center; justify-content: space-between; gap: var(--sp-3); flex-wrap: wrap; }
  .attack-alert .aa-ships { display: flex; flex-wrap: wrap; gap: var(--sp-1) var(--sp-2); }
  .attack-alert .aa-ship {
    font-size: var(--fs-xs); color: var(--text-dim);
    background: rgba(255,255,255,0.05); border-radius: var(--r-sm);
    padding: 1px var(--sp-1); white-space: nowrap;
  }
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

  /* === Welle 4: Die erwachende Galaxie === */
  /* Aggressions-Barometer — der „Puls" des Universums. --band = aktuelle Status-Farbe. */
  .awakening-baro { border-left: 3px solid var(--band); }
  .baro-head {
    display: flex; align-items: baseline; justify-content: space-between; gap: var(--sp-2);
    margin-bottom: var(--sp-2);
  }
  .baro-title { font-weight: 600; letter-spacing: 0.02em; }
  .baro-status {
    font-size: var(--fs-sm); font-weight: 700; color: var(--band); text-transform: uppercase;
    letter-spacing: 0.08em;
  }
  .baro-bar {
    position: relative; height: 12px; border-radius: var(--r-pill);
    background: rgba(255,255,255,0.06); overflow: hidden; border: 1px solid var(--border-strong);
  }
  .baro-fill {
    position: absolute; inset: 0 auto 0 0; height: 100%; border-radius: var(--r-pill);
    background: linear-gradient(90deg, color-mix(in srgb, var(--band) 55%, transparent), var(--band));
    box-shadow: 0 0 12px var(--band);
    transition: width var(--motion-slow) var(--ease-out);
  }
  .baro-tick {
    position: absolute; top: -1px; bottom: -1px; width: 1px;
    background: rgba(255,255,255,0.25); transform: translateX(-50%);
  }
  .baro-tick.peak { width: 2px; background: rgba(255,77,77,0.7); }
  .baro-meta {
    display: flex; align-items: center; gap: var(--sp-3); margin-top: var(--sp-2);
    font-size: var(--fs-sm);
  }
  .baro-spark {
    margin-left: auto; width: 96px; height: 20px; overflow: visible;
  }
  .baro-spark polyline {
    fill: none; stroke: var(--band); stroke-width: 1.5;
    stroke-linejoin: round; stroke-linecap: round;
    filter: drop-shadow(0 0 3px var(--band));
  }

  /* „Der Erwachte"-Banner — dramatisch, ehrfurchtgebietend, oben im Dashboard. */
  .warden-banner {
    position: relative; display: flex; align-items: center; gap: var(--sp-4);
    margin-bottom: var(--sp-4); padding: var(--sp-4) var(--sp-5);
    border-radius: var(--r-md); text-decoration: none; color: var(--text);
    overflow: hidden; cursor: pointer;
    border: 1px solid rgba(255,77,77,0.55);
    background:
      radial-gradient(120% 140% at 0% 0%, rgba(255,77,77,0.20), transparent 60%),
      linear-gradient(135deg, rgba(40,8,12,0.92), rgba(18,6,10,0.92));
    box-shadow: 0 0 28px rgba(255,77,77,0.28), inset 0 0 40px rgba(255,77,77,0.06);
    animation: warden-pulse 3.2s var(--ease-in-out) infinite;
  }
  @keyframes warden-pulse {
    0%, 100% { box-shadow: 0 0 22px rgba(255,77,77,0.22), inset 0 0 40px rgba(255,77,77,0.05); }
    50% { box-shadow: 0 0 40px rgba(255,77,77,0.42), inset 0 0 56px rgba(255,77,77,0.10); }
  }
  .warden-banner .wb-glow {
    position: absolute; right: -40px; top: 50%; transform: translateY(-50%);
    width: 220px; height: 220px; pointer-events: none;
    background: radial-gradient(circle, rgba(255,140,60,0.28), transparent 70%);
  }
  .warden-banner .wb-body { position: relative; z-index: 1; flex: 1; min-width: 0; }
  .wb-title {
    font-size: var(--fs-xl); font-weight: 800; letter-spacing: 0.04em;
    color: #ffd9a0; text-shadow: 0 0 14px rgba(255,120,40,0.55);
  }
  .wb-sub { font-size: var(--fs-sm); color: var(--text-dim); margin-top: 2px; }
  .wb-stats {
    display: flex; flex-wrap: wrap; gap: var(--sp-2); margin-top: var(--sp-3);
  }
  .wb-chip {
    display: inline-flex; align-items: center; gap: 4px;
    font-size: var(--fs-sm); font-variant-numeric: tabular-nums;
    padding: 2px var(--sp-2); border-radius: var(--r-pill);
    background: rgba(0,0,0,0.30); border: 1px solid rgba(255,255,255,0.10);
  }
  .wb-chip.danger { color: #ffb38a; border-color: rgba(255,77,77,0.45); }
  .wb-fleet {
    display: flex; flex-wrap: wrap; gap: var(--sp-2); margin-top: var(--sp-2);
    font-size: var(--fs-xs); color: var(--text-faint);
  }
  .wb-ship {
    padding: 1px var(--sp-2); border-radius: var(--r-sm);
    background: rgba(255,255,255,0.04);
  }
  .warden-banner .wb-cta {
    position: relative; z-index: 1; white-space: nowrap; align-self: center;
    font-weight: 700; color: #ffd9a0;
    transition: transform var(--motion-fast) var(--ease-out);
  }
  .warden-banner:hover .wb-cta { transform: translateX(3px); }

  /* Alerts direkt nach dem Planeten-Header — volle Breite, etwas Abstand zur Spalten-Sektion. */
  .alerts-top { margin-bottom: var(--sp-3); }

  /* === Einklappbare Ambient-Karten (Konjunktionen / Aggressions-Barometer) === */
  .collapsible { margin-bottom: var(--sp-3); }
  /* Eingeklappt = nur eine schlanke Kopfzeile. */
  .collapsible.collapsed { padding-top: var(--sp-2); padding-bottom: var(--sp-2); }
  .collapse-head {
    display: flex; align-items: center; justify-content: space-between; gap: var(--sp-2);
    width: 100%; font: inherit; text-align: left; cursor: pointer;
    background: none; border: none; padding: 0; color: var(--text);
    transition: color var(--motion-fast) var(--ease-out);
  }
  .collapse-head:hover { color: var(--accent); }
  .collapse-head .ch-title {
    display: inline-flex; align-items: baseline; gap: var(--sp-2);
    font-weight: 600; letter-spacing: 0.02em;
  }
  .collapse-head .ch-arrow {
    color: var(--text-dim); font-size: var(--fs-sm); flex: 0 0 auto;
  }
  .collapse-head:hover .ch-arrow { color: var(--accent); }
  .collapse-body { margin-top: var(--sp-3); }
`;
