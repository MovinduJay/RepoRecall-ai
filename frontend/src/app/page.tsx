import { ThemeToggle } from "@/components/theme-toggle";
import { ApiRequestError, getApiHealth } from "@/lib/api";

async function loadHealth() {
  try { return { health: await getApiHealth(), error: null }; }
  catch (error) {
    const message = error instanceof ApiRequestError ? error.message : "An unexpected error occurred.";
    return { health: null, error: message };
  }
}

function RepoMark() {
  return <svg className="repo-mark" viewBox="0 0 36 36" aria-hidden="true"><path d="M10 8.5v13a6 6 0 0 0 6 6h3" /><path d="M10 14h9a6 6 0 0 1 6 6v7.5" /><circle cx="10" cy="7" r="3" /><circle cx="25" cy="29" r="3" /><circle cx="21" cy="14" r="3" /></svg>;
}

export default async function Home() {
  const { health, error } = await loadHealth();
  const online = health?.status === "ok";

  return (
    <main className="site-shell">
      <div className="ambient-grid" aria-hidden="true" />
      <header className="topbar">
        <a className="brand" href="#top" aria-label="RepoRecall home"><span className="brand-mark"><RepoMark /></span><span>RepoRecall</span><span className="brand-tag">AI</span></a>
        <div className="topbar-actions">
          <div className={`status-pill ${online ? "is-online" : "is-offline"}`}><span className="status-dot" /><span className="status-copy">{online ? "Systems ready" : "API offline"}</span></div>
          <ThemeToggle />
          <a className="github-link" href="https://github.com" aria-label="Open GitHub"><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .7a11.6 11.6 0 0 0-3.7 22.6c.6.1.8-.3.8-.6v-2.2c-3.4.7-4.1-1.4-4.1-1.4-.5-1.4-1.3-1.8-1.3-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.7-.3-5.5-1.3-5.5-5.8 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.7 1.7.3 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.5-2.8 5.5-5.5 5.8.4.4.8 1.1.8 2.2v3.3c0 .4.2.7.8.6A11.6 11.6 0 0 0 12 .7Z" /></svg></a>
        </div>
      </header>

      <section className="hero" id="top">
        <div className="eyebrow"><span>●</span> Your repository remembers</div>
        <h1>Ask the codebase.<br /><span>Find the why.</span></h1>
        <p className="hero-copy">Trace bugs back through commits, pull requests, and issues. RepoRecall turns repository history into answers grounded in the evidence your team already created.</p>
        <div className="search-console">
          <div className="console-bar"><div className="window-dots" aria-hidden="true"><i /><i /><i /></div><span className="console-path">reporecall / semantic-search</span><span className="console-branch"><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="4" cy="3" r="2" /><circle cx="12" cy="4" r="2" /><circle cx="4" cy="13" r="2" /><path d="M4 5v6M10 4H8a4 4 0 0 0-4 4" /></svg>main</span></div>
          <div className="query-row"><span className="prompt-sign" aria-hidden="true">›</span><label className="sr-only" htmlFor="history-query">Search repository history</label><input id="history-query" type="text" placeholder="Why did we stop retrying failed webhooks?" aria-describedby="query-hint" /><button type="button" className="search-button" title="Search UI coming next"><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" /><path d="m13 13 4 4" /></svg>Search history</button></div>
          <div className="query-hints" id="query-hint"><span><kbd>⌘</kbd><kbd>K</kbd> to focus</span><span>issues</span><span>pull requests</span><span>commits</span></div>
        </div>
      </section>

      <section className="proof-section" aria-labelledby="proof-title">
        <div className="section-heading"><div><p className="section-kicker">Evidence, not guesses</p><h2 id="proof-title">Follow the trail from symptom to fix.</h2></div><p>Every answer stays connected to the repository events that explain it.</p></div>
        <div className="evidence-board">
          <div className="timeline-card"><div className="card-label"><span><span className="code-brackets">{`{ }`}</span> RECALL TRACE</span></div><div className="timeline">
            <article className="timeline-item issue-item"><div className="timeline-node"><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="6" /><circle cx="8" cy="8" r="1" /></svg></div><div><div className="item-meta"><span className="badge badge-green">issue</span><code>#184</code><span>opened</span></div><h3>Webhook delivery stalls after provider timeout</h3><p>Reports establish the original symptom and affected workflow.</p></div></article>
            <article className="timeline-item commit-item"><div className="timeline-node"><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="8" cy="8" r="3" /><path d="M8 1v4M8 11v4" /></svg></div><div><div className="item-meta"><span className="badge badge-blue">commit</span><code>7d2a9f1</code><span>linked</span></div><h3>Bound retries and preserve delivery evidence</h3><p>The diff reveals the implementation decision behind the fix.</p></div></article>
            <article className="timeline-item pr-item"><div className="timeline-node"><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="4" cy="3" r="2" /><circle cx="12" cy="4" r="2" /><circle cx="4" cy="13" r="2" /><path d="M4 5v6M10 4H8a4 4 0 0 0-4 4" /></svg></div><div><div className="item-meta"><span className="badge badge-purple">pull request</span><code>#191</code><span>merged</span></div><h3>Retry policy now fails safely</h3><p>Review discussion captures the trade-off and final rationale.</p></div></article>
          </div></div>
          <aside className="answer-card"><div className="answer-topline"><span>ANSWER.md</span><span className="answer-state">● grounded</span></div><div className="answer-content"><div className="answer-mark"><RepoMark /></div><p className="answer-lead">Retries were bounded to prevent duplicate deliveries after ambiguous provider timeouts.</p><p className="answer-detail">The team chose evidence preservation over silent retries, making failed attempts inspectable before another delivery is queued.</p><div className="citations"><span>[1] issue #184</span><span>[2] 7d2a9f1</span><span>[3] PR #191</span></div></div><div className="answer-footer"><span>3 sources connected</span><span>hybrid retrieval</span></div></aside>
        </div>
      </section>

      <section className="feature-grid" aria-label="Product capabilities">
        <article><span className="feature-index">01</span><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="10" cy="10" r="6" /><path d="m15 15 5 5M10 7v6M7 10h6" /></svg><h3>Search beyond keywords</h3><p>Combine semantic meaning with precise repository terms to retrieve relevant history.</p></article>
        <article><span className="feature-index">02</span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="m12 3 8 4v5c0 5-3.4 8-8 9-4.6-1-8-4-8-9V7l8-4Z" /><path d="m8.5 12 2.2 2.2 4.8-5" /></svg><h3>Stay tied to evidence</h3><p>Inspect the issues, commits, and pull requests supporting each generated answer.</p></article>
        <article><span className="feature-index">03</span><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M4 7h16M4 12h10M4 17h7" /><circle cx="18" cy="17" r="3" /></svg><h3>Recover team context</h3><p>Bring implementation choices and review rationale back into the current conversation.</p></article>
      </section>

      <footer className="footer"><div><RepoMark /><span>RepoRecall</span><span className="footer-note">Engineering memory, retrieved.</span></div><div className={`footer-health ${online ? "is-online" : "is-offline"}`}><span className="status-dot" />{online ? "FastAPI connected" : error || "Backend unavailable"}</div></footer>
    </main>
  );
}
