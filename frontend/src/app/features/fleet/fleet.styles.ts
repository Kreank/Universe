export const fleetStyles = `
  /* Zwei Spalten ab Desktop: links Sende-Formular (volle Breite), darunter die Listen. */
  .layout {
    grid-template-columns: minmax(300px, 1fr) minmax(340px, 1.3fr);
    align-items: start;
  }
  .send { grid-column: 1 / -1; }

  .small { font-size: var(--fs-xs); }
  .hint { color: var(--text-faint); margin: var(--sp-1) 0 0; }

  /* --- Schiffsauswahl: dichtes, bild-zentriertes Kachel-Raster (OGame-Stil) --- */
  .ships-grid {
    grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
    gap: var(--sp-3);
    margin-bottom: var(--sp-4);
  }
  .empty-ships { grid-column: 1 / -1; }
  .ship {
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: var(--sp-2);
    padding: var(--sp-3) var(--sp-2);
    text-align: center;
    border: 1px solid var(--border);
    border-radius: var(--r-md);
    background: rgba(255, 255, 255, 0.015);
    transition: border-color var(--motion-fast) var(--ease-out),
      box-shadow var(--motion-fast) var(--ease-out);
  }
  .ship.picked { border-color: var(--accent); box-shadow: var(--glow); }
  .ship-art { position: relative; }
  .ship-art .avail {
    position: absolute; bottom: -5px; right: -5px;
    min-width: 22px; height: 22px; padding: 0 var(--sp-1); border-radius: var(--r-pill);
    background: var(--surface-3); color: var(--text); border: 1px solid var(--border);
    font-family: var(--mono); font-size: var(--fs-xs); font-weight: 700;
    font-variant-numeric: tabular-nums;
    display: flex; align-items: center; justify-content: center;
  }
  .ship-name { font-family: var(--font-display); font-weight: 600; font-size: var(--fs-sm); }
  .ship-pick { display: flex; align-items: center; gap: var(--sp-1); width: 100%; margin-top: auto; }
  .ship-pick input { min-height: 44px; padding: var(--sp-1) var(--sp-2); text-align: center; }
  .ship-pick .btn-sm { min-height: 44px; padding: var(--sp-1) var(--sp-2); flex: 0 0 auto; }

  /* --- Auftrags-Leiste: Ziel, Mission, Tempo, Commander, Start --- */
  .order-bar {
    display: grid;
    grid-template-columns: minmax(220px, 1.4fr) repeat(3, minmax(140px, 1fr)) minmax(150px, auto);
    gap: var(--sp-3) var(--sp-4);
    align-items: end;
    padding-top: var(--sp-4);
    border-top: 1px solid var(--border);
  }
  .order-bar .field { margin-bottom: 0; }
  .coord { display: flex; align-items: center; gap: var(--sp-1); }
  .coord input { text-align: center; padding: var(--sp-2) var(--sp-1); }
  .coord .sep { color: var(--text-faint); font-weight: 700; }
  .send-field { justify-content: flex-end; }
  input[type="range"] { padding: 0; min-height: auto; }

  /* --- Laufende Flotten & Patrouillen: dichte Listenzeilen --- */
  .fleet-row {
    display: flex; align-items: center; justify-content: space-between;
    gap: var(--sp-3); padding: var(--sp-2) 0;
    border-bottom: 1px solid var(--border);
    flex-wrap: wrap;
  }
  .fleet-row:last-child { border-bottom: none; }
  .fleet-info { display: flex; flex-direction: column; gap: var(--sp-1); min-width: 0; }
  .fleet-act { display: flex; align-items: center; gap: var(--sp-3); }
  .badge-mission { font-family: var(--font-display); font-weight: 600; }
  .mission-ico {
    width: 1.2em; height: 1.2em; object-fit: contain;
    vertical-align: -0.25em; margin-right: var(--sp-1);
    filter: drop-shadow(0 1px 2px rgba(0,0,0,0.5));
  }

  /* --- Eingehende Angriffe (Gefahr -> --danger) --- */
  .card.incoming {
    border: 1px solid color-mix(in srgb, var(--danger) 45%, transparent);
    background: color-mix(in srgb, var(--danger) 10%, var(--surface-1));
    margin-bottom: var(--sp-4);
  }
  .incoming-row {
    display: flex; align-items: center; justify-content: space-between;
    gap: var(--sp-3); padding: var(--sp-2) 0;
    border-bottom: 1px solid color-mix(in srgb, var(--danger) 18%, transparent);
    flex-wrap: wrap;
  }
  .incoming-row:last-of-type { border-bottom: none; }
  .incoming-info { display: flex; flex-direction: column; gap: var(--sp-1); min-width: 0; }
  .badge-threat { font-family: var(--font-display); font-weight: 700; color: var(--danger); }

  /* --- Galaxie-Hinweis (Verweis auf die eigene Galaxie-Seite) --- */
  .galaxy-hint {
    margin-top: var(--sp-4); text-align: center;
    padding: var(--sp-3); border: 1px dashed var(--border); border-radius: var(--r-md);
  }

  /* Mobile: gestapelte Karten + Touch-Targets >= 44px. */
  @media (max-width: 960px) {
    .order-bar { grid-template-columns: 1fr 1fr; }
    .order-bar .coords { grid-column: 1 / -1; }
    .send-field { grid-column: 1 / -1; }
  }
  @media (max-width: 860px) {
    .layout { grid-template-columns: 1fr; }
    .fleet-row { padding: var(--sp-3) 0; }
    .fleet-act .btn { min-height: 44px; }
  }

  /* Desktop: kompaktere Picker-Felder (Maus-Targets duerfen unter 44px). */
  @media (min-width: 900px) {
    .ship-pick input,
    .ship-pick .btn-sm { min-height: 34px; }
  }

  /* --- Fracht-Beladung + Flotten-Übersicht --- */
  .cargo-box { margin-top: var(--sp-3); padding: var(--sp-2) var(--sp-3); border: 1px solid var(--border); border-radius: var(--r-sm); }
  .cargo-head { display: flex; align-items: center; justify-content: space-between; font-family: var(--font-display); font-size: var(--fs-xs); text-transform: uppercase; letter-spacing: 0.1em; color: var(--text-dim); margin-bottom: var(--sp-2); }
  .cargo-grid { display: flex; flex-wrap: wrap; gap: var(--sp-3); }
  .cargo-field { display: flex; flex-direction: column; gap: 4px; flex: 1 1 150px; }
  .cargo-field label { font-size: var(--fs-xs); color: var(--text-dim); display: inline-flex; align-items: center; gap: 5px; }
  .cargo-ico { width: 15px; height: 15px; object-fit: contain; }
  .cargo-input { display: flex; gap: var(--sp-1); }
  .cargo-input input { min-height: 30px; flex: 1; }
  .avail-hint { font-size: var(--fs-xs); }

  .fleet-summary { margin-top: var(--sp-3); display: flex; flex-direction: column; gap: var(--sp-2); }
  .cap-line { display: flex; align-items: baseline; justify-content: space-between; font-size: var(--fs-sm); }
  .cap-bar { height: 6px; border-radius: var(--r-pill); background: rgba(255,255,255,0.08); overflow: hidden; margin-top: 4px; }
  .cap-bar span { display: block; height: 100%; background: var(--accent); transition: width var(--motion-base) var(--ease-out); }
  .cap-bar.over span { background: var(--danger); }
  .cap.over .cap-line { color: var(--danger); }
  .route-chips { display: flex; flex-wrap: wrap; gap: var(--sp-1) var(--sp-3); color: var(--text-dim); }
  .route-chips img { vertical-align: -2px; margin-right: 3px; }
`;
