/** Geteilte Styles fuer Login- und Register-Screen. */
export const authPanelStyles = `
  .auth-wrap {
    min-height: 100vh;
    display: grid;
    place-items: center;
    padding: 1.5rem;
  }
  .auth-card {
    width: min(420px, 100%);
    padding: 2rem 1.8rem;
  }
  .brand {
    display: flex;
    align-items: center;
    gap: 0.9rem;
    margin-bottom: 1.6rem;
  }
  .logo {
    font-size: 2.2rem;
    color: var(--accent);
    filter: drop-shadow(0 0 12px rgba(46, 230, 214, 0.6));
  }
  .brand h1 {
    margin: 0;
    letter-spacing: 0.3em;
    font-size: 1.4rem;
  }
  .tagline {
    margin: 0;
    font-size: 0.78rem;
    letter-spacing: 0.1em;
  }
  .full {
    width: 100%;
    margin-top: 0.4rem;
  }
  .error {
    color: var(--magenta);
    font-size: 0.85rem;
    margin: 0 0 0.8rem;
  }
  .switch {
    text-align: center;
    margin-top: 1.2rem;
    font-size: 0.86rem;
  }
`;
