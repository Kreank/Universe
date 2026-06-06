export const commanderStyles = `
  .head {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;
  }
  .sub { margin-top: -0.3rem; font-size: 0.85rem; }
  .small { font-size: 0.76rem; }

  .span-card { margin-bottom: 1.2rem; }
  .span-head { display: flex; align-items: center; justify-content: space-between; margin-bottom: 0.5rem; }
  .span-big { font-size: 1.2rem; color: var(--accent); }
  .span-big.over { color: var(--magenta); }
  .span-detail { margin-top: 0.4rem; }

  .roster { grid-template-columns: repeat(auto-fill, minmax(300px, 1fr)); }
  .cmd-card {
    display: flex; gap: 0.9rem; text-decoration: none; color: var(--text);
    transition: transform 0.12s ease, box-shadow 0.15s ease, border-color 0.15s ease;
  }
  .cmd-card:hover {
    transform: translateY(-2px);
    border-color: var(--border-strong);
    box-shadow: var(--glow);
  }

  .portrait {
    position: relative;
    width: 84px; flex: 0 0 84px; height: 84px;
    border-radius: 10px; overflow: hidden;
    border: 2px solid var(--band, var(--accent));
    box-shadow: 0 0 14px color-mix(in srgb, var(--band, var(--accent)) 40%, transparent);
  }
  .portrait img { width: 100%; height: 100%; display: block; }
  .rank-badge {
    position: absolute; bottom: 0; left: 0; right: 0;
    background: rgba(6,10,20,0.85);
    font-size: 0.62rem; text-align: center; padding: 1px 0;
    color: var(--band, var(--accent));
  }
  .status-tag {
    position: absolute; top: 4px; right: 4px;
    background: rgba(255,64,160,0.85); color: #fff;
    font-size: 0.58rem; padding: 1px 5px; border-radius: 99px;
  }

  .cmd-body { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.5rem; }
  .cmd-body h3 { font-size: 1rem; margin: 0; }
  .morale-bar .fill { background: linear-gradient(90deg, color-mix(in srgb, var(--band) 50%, transparent), var(--band)); }
  .traits { display: flex; flex-wrap: wrap; gap: 0.3rem; }
  .trait { border-color: var(--border); }
  .cmd-foot { display: flex; flex-wrap: wrap; gap: 0.3rem; }

  @media (max-width: 520px) {
    .cmd-card { flex-direction: column; }
    .portrait { width: 100%; flex: 0 0 auto; height: 120px; }
  }
`;
