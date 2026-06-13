/** Geteilte Styles fuer Login- und Register-Screen (cinematic, token-getrieben). */
export const authPanelStyles = `
  /* Bildschirmfuellende, cinematic Buehne: Foto + Tiefen-Overlay + Akzent-Schimmer. */
  .auth-wrap {
    position: relative;
    overflow: hidden;
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: var(--sp-6);
    background-image:
      radial-gradient(900px 640px at 80% -12%, var(--accent-soft), transparent 62%),
      radial-gradient(820px 620px at 6% 112%, color-mix(in srgb, var(--info) 16%, transparent), transparent 60%),
      linear-gradient(165deg, color-mix(in srgb, var(--bg-deep) 70%, transparent), color-mix(in srgb, var(--bg-deep) 90%, transparent)),
      url('/assets/img/backgrounds/login.jpg');
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    background-attachment: fixed;
  }

  /* Sanft driftender Akzent-Schein (nur transform/opacity -> performant). */
  .auth-wrap::before {
    content: '';
    position: absolute;
    inset: 0;
    z-index: 0;
    pointer-events: none;
    background: radial-gradient(640px 640px at 50% 118%, var(--accent-soft), transparent 70%);
    animation: authGlow 14s var(--ease-out) infinite alternate;
  }
  @keyframes authGlow {
    from { transform: translateY(var(--sp-4)) scale(1); opacity: 0.45; }
    to   { transform: translateY(calc(-1 * var(--sp-5))) scale(1.08); opacity: 0.85; }
  }

  /* Zentriertes, edles Glas-Panel; hebt sich mit sanftem Auftakt vom Foto ab. */
  .auth-card {
    position: relative;
    z-index: 1;
    width: min(420px, 100%);
    border-radius: var(--r-lg);
    padding: var(--sp-8) var(--sp-6);
    animation: authRise var(--motion-slow) var(--ease-out) both;
  }
  @keyframes authRise {
    from { opacity: 0; transform: translateY(var(--sp-4)); }
    to   { opacity: 1; transform: translateY(0); }
  }

  /* Marke als zentrierte Display-Typo mit Akzent-Emblem. */
  .brand {
    display: flex;
    flex-direction: column;
    align-items: center;
    text-align: center;
    gap: var(--sp-3);
    margin-bottom: var(--sp-6);
    padding-bottom: var(--sp-5);
    border-bottom: 1px solid var(--border);
  }
  .logo {
    display: inline-grid;
    place-items: center;
    width: 64px;
    height: 64px;
    border-radius: var(--r-pill);
    background: var(--accent-soft);
    border: 1px solid color-mix(in srgb, var(--accent) 42%, transparent);
    box-shadow: var(--glow-soft);
    font-size: var(--fs-2xl);
    line-height: 1;
    color: var(--accent-strong);
  }
  .brand h1 {
    margin: 0;
    font-family: var(--font-display);
    font-size: var(--fs-2xl);
    font-weight: 700;
    letter-spacing: 0.34em;
    text-indent: 0.34em;
    color: var(--text);
  }
  .tagline {
    margin: 0;
    font-family: var(--font-display);
    font-size: var(--fs-xs);
    letter-spacing: 0.18em;
    text-transform: uppercase;
  }

  .full {
    width: 100%;
    margin-top: var(--sp-2);
  }

  /* Fehlerhinweis als dezente Gefahr-Notiz. */
  .error {
    margin: 0 0 var(--sp-4);
    padding: var(--sp-2) var(--sp-3);
    border-radius: var(--r-md);
    background: color-mix(in srgb, var(--danger) 12%, transparent);
    border: 1px solid var(--danger-dim);
    color: var(--danger);
    font-size: var(--fs-sm);
  }

  .switch {
    text-align: center;
    margin-top: var(--sp-5);
    font-size: var(--fs-sm);
  }

  /* Mobile: hochformatiges Artwork, Panel auf voller Breite mit Rand. */
  @media (max-width: 640px) {
    .auth-wrap {
      padding: var(--sp-5);
      background-image:
        radial-gradient(700px 520px at 80% -12%, var(--accent-soft), transparent 62%),
        linear-gradient(165deg, color-mix(in srgb, var(--bg-deep) 72%, transparent), color-mix(in srgb, var(--bg-deep) 92%, transparent)),
        url('/assets/img/backgrounds/login_portrait.jpg');
    }
    .auth-card { padding: var(--sp-6) var(--sp-5); }
  }
`;
