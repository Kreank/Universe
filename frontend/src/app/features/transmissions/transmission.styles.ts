export const transmissionStyles = `
  .head {
    display: flex; align-items: flex-start; justify-content: space-between;
    gap: 1rem; flex-wrap: wrap; margin-bottom: 1rem;
  }
  .sub { margin-top: -0.3rem; font-size: 0.85rem; }
  .small { font-size: 0.76rem; }
  .filters { display: flex; gap: 0.4rem; }

  .list { grid-template-columns: 1fr; gap: 0.8rem; max-width: 760px; }
  .msg { position: relative; border-left: 3px solid var(--border); }
  .msg.unread { border-left-color: var(--accent); box-shadow: var(--glow); }
  .msg.demand { border-left-color: var(--magenta); }

  .msg-head { display: flex; gap: 0.7rem; align-items: flex-start; }
  .type-glyph { font-size: 1.4rem; line-height: 1; }
  .msg-meta { flex: 1; min-width: 0; }
  .msg-meta h3 { margin: 0; font-size: 1rem; }
  .dot-new {
    width: 10px; height: 10px; border-radius: 99px;
    background: var(--accent); box-shadow: 0 0 8px var(--accent);
    flex: 0 0 auto; margin-top: 4px;
  }

  .body { color: var(--text-dim); font-size: 0.9rem; margin: 0.7rem 0 0; white-space: pre-line; }

  .decision {
    margin-top: 0.9rem; padding-top: 0.8rem;
    border-top: 1px solid var(--border);
    display: flex; flex-direction: column; gap: 0.5rem;
  }
  .dec-buttons { display: flex; gap: 0.5rem; flex-wrap: wrap; }
  .mark { margin-top: 0.8rem; }
`;
