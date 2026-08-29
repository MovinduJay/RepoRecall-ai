"use client";

import { FormEvent, useEffect, useState } from "react";

type Repository = {
  id: string;
  owner: string;
  name: string;
  github_url: string;
  default_branch: string;
  indexing_status: string;
  existing?: boolean;
};

type IndexingJob = {
  id: string;
  status: "pending" | "running" | "completed" | "failed";
  issues_processed: number;
  pull_requests_processed: number;
  commits_processed: number;
  documents_upserted: number;
  error_message: string | null;
};

type Evidence = {
  title: string;
  text: string;
  html_url: string;
  source_type: string;
  rrf_score: number;
};

type Investigation = {
  decision: "sufficient" | "rewrite" | "abstain";
  confidence: number;
  retry_count: number;
  evidence: Evidence[];
  answer: string | null;
  citations: string[];
  generation_error: string | null;
};

const INDEXING_LIMIT = 500;

async function readJson<T>(response: Response): Promise<T> {
  const payload = (await response.json()) as T & { detail?: string };
  if (!response.ok) throw new Error(payload.detail ?? "The request could not be completed.");
  return payload;
}

export function RepositoryConnector() {
  const [repositories, setRepositories] = useState<Repository[]>([]);
  const [selected, setSelected] = useState<Repository | null>(null);
  const [job, setJob] = useState<IndexingJob | null>(null);
  const [githubUrl, setGithubUrl] = useState("");
  const [branch, setBranch] = useState("main");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [query, setQuery] = useState("");
  const [investigating, setInvestigating] = useState(false);
  const [searchError, setSearchError] = useState<string | null>(null);
  const [investigation, setInvestigation] = useState<Investigation | null>(null);

  useEffect(() => {
    fetch("/api/repositories")
      .then((response) => readJson<Repository[]>(response))
      .then(setRepositories)
      .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not load repositories."));
  }, []);

  useEffect(() => {
    if (!job || !["pending", "running"].includes(job.status)) return;
    const timer = window.setInterval(() => {
      fetch(`/api/indexing-jobs/${job.id}`)
        .then((response) => readJson<IndexingJob>(response))
        .then((nextJob) => {
          setJob(nextJob);
          if (nextJob.status === "completed" && selected) {
            setSelected({ ...selected, indexing_status: "completed" });
          }
        })
        .catch((reason: unknown) => setError(reason instanceof Error ? reason.message : "Could not check indexing progress."));
    }, 2500);
    return () => window.clearInterval(timer);
  }, [job, selected]);

  async function startIndexing(repository: Repository) {
    const response = await fetch(`/api/repositories/${repository.id}/sync`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ max_items_per_source: INDEXING_LIMIT }),
    });
    setJob(await readJson<IndexingJob>(response));
  }

  async function connectRepository(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setBusy(true);
    setError(null);
    setJob(null);
    try {
      const response = await fetch("/api/repositories", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ github_url: githubUrl, default_branch: branch }),
      });
      const repository = await readJson<Repository>(response);
      setSelected(repository);
      setRepositories((current) => [repository, ...current.filter((item) => item.id !== repository.id)]);
      if (!repository.existing || repository.indexing_status !== "completed") {
        await startIndexing(repository);
      }
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not connect this repository.");
    } finally {
      setBusy(false);
    }
  }

  async function reindexSelected() {
    if (!selected) return;
    setBusy(true);
    setError(null);
    setJob(null);
    try {
      await startIndexing(selected);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "Could not start deep indexing.");
    } finally {
      setBusy(false);
    }
  }

  function chooseRepository(repository: Repository) {
    setSelected(repository);
    setJob(null);
    setError(null);
    setInvestigation(null);
    setSearchError(null);
  }

  async function searchHistory(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!selected) {
      setSearchError("Connect or select a repository before searching.");
      return;
    }
    if (selected.indexing_status !== "completed" || active) {
      setSearchError("Wait for repository indexing to complete before searching.");
      return;
    }

    setInvestigating(true);
    setSearchError(null);
    setInvestigation(null);
    try {
      const response = await fetch("/api/search/investigate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ repository_id: selected.id, query, limit: 5 }),
      });
      setInvestigation(await readJson<Investigation>(response));
    } catch (reason) {
      setSearchError(reason instanceof Error ? reason.message : "Repository search failed.");
    } finally {
      setInvestigating(false);
    }
  }

  const active = busy || job?.status === "pending" || job?.status === "running";

  return <>
    <div className="connector-card">
      <div className="connector-heading">
        <div><span className="step-number">01</span><h2>Connect a repository</h2></div>
        <span className="public-label">Deep history · up to 500/source</span>
      </div>

      <form className="connector-form" onSubmit={connectRepository}>
        <label className="repo-url-field">
          <span>GitHub repository URL</span>
          <div><svg viewBox="0 0 24 24" aria-hidden="true"><path d="M12 .7a11.6 11.6 0 0 0-3.7 22.6c.6.1.8-.3.8-.6v-2.2c-3.4.7-4.1-1.4-4.1-1.4-.5-1.4-1.3-1.8-1.3-1.8-1.1-.7.1-.7.1-.7 1.2.1 1.8 1.2 1.8 1.2 1 1.8 2.8 1.3 3.5 1 .1-.8.4-1.3.7-1.6-2.7-.3-5.5-1.3-5.5-5.8 0-1.3.5-2.4 1.2-3.2-.1-.3-.5-1.5.1-3.2 0 0 1-.3 3.3 1.2a11.5 11.5 0 0 1 6 0c2.3-1.5 3.3-1.2 3.3-1.2.7 1.7.3 2.9.1 3.2.8.8 1.2 1.9 1.2 3.2 0 4.5-2.8 5.5-5.5 5.8.4.4.8 1.1.8 2.2v3.3c0 .4.2.7.8.6A11.6 11.6 0 0 0 12 .7Z" /></svg><input required type="url" value={githubUrl} onChange={(event) => setGithubUrl(event.target.value)} placeholder="https://github.com/owner/repository" /></div>
        </label>
        <label className="branch-field"><span>Branch</span><input required value={branch} onChange={(event) => setBranch(event.target.value)} /></label>
        <button className="connect-button" type="submit" disabled={active}>{busy ? "Connecting…" : "Connect & index"}<span>→</span></button>
      </form>

      {repositories.length > 0 && <div className="known-repositories"><span>Or continue with</span><div>{repositories.slice(0, 4).map((repository) => <button type="button" key={repository.id} onClick={() => chooseRepository(repository)} className={selected?.id === repository.id ? "is-selected" : ""}><i className={repository.indexing_status === "completed" ? "ready" : ""} />{repository.owner}/{repository.name}</button>)}</div></div>}

      {error && <div className="connector-message is-error" role="alert"><strong>Connection failed</strong><span>{error}</span></div>}
      {selected && !error && <div className={`connector-message ${job?.status === "failed" ? "is-error" : "is-success"}`}>
        <div className="connected-repo"><span className="repo-avatar">{selected.owner.slice(0, 1).toUpperCase()}</span><div><strong>{selected.owner}/{selected.name}</strong><span>{selected.default_branch} · {job ? job.status : selected.indexing_status}</span></div></div>
        {job && <div className="job-progress"><div><span style={{ width: job.status === "completed" ? "100%" : job.status === "running" ? "62%" : "18%" }} /></div><p>{job.status === "completed" ? `${job.documents_upserted} documents indexed. Ready to search.` : job.status === "failed" ? job.error_message : "Collecting GitHub history and building the search index…"}</p></div>}
        {!job && selected.indexing_status === "completed" && <div className="ready-actions"><span className="ready-copy">✓ Ready to search</span><button type="button" onClick={reindexSelected} disabled={busy}>{busy ? "Starting…" : "Deep re-index (500)"}</button></div>}
      </div>}
    </div>

    <div className="search-console">
      <div className="console-bar"><div className="window-dots" aria-hidden="true"><i /><i /><i /></div><span className="console-path">{selected ? `${selected.owner}/${selected.name}` : "select a repository"} / investigate</span><span className="console-branch"><svg viewBox="0 0 16 16" aria-hidden="true"><circle cx="4" cy="3" r="2" /><circle cx="12" cy="4" r="2" /><circle cx="4" cy="13" r="2" /><path d="M4 5v6M10 4H8a4 4 0 0 0-4 4" /></svg>{selected?.default_branch ?? "main"}</span></div>
      <form onSubmit={searchHistory}>
        <div className="query-row"><span className="prompt-sign" aria-hidden="true">›</span><label className="sr-only" htmlFor="history-query">Search repository history</label><textarea id="history-query" required value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Paste an error or ask whether this was solved before…" aria-describedby="query-hint" rows={2} /><button type="submit" className="search-button" disabled={investigating || active}><svg viewBox="0 0 20 20" aria-hidden="true"><circle cx="8.5" cy="8.5" r="5.5" /><path d="m13 13 4 4" /></svg>{investigating ? "Investigating…" : "Search history"}</button></div>
        <div className="query-hints" id="query-hint"><span>{selected ? `Searching ${selected.owner}/${selected.name}` : "Choose a repository above first"}</span><span>issues</span><span>pull requests</span><span>commits</span></div>
      </form>
    </div>

    {searchError && <div className="search-feedback is-error" role="alert"><strong>Could not search repository history</strong><p>{searchError}</p></div>}
    {investigating && <div className="search-feedback is-loading" aria-live="polite"><span className="search-spinner" /><div><strong>Investigating repository history</strong><p>Retrieving similar issues, commits, pull requests, and code changes…</p></div></div>}
    {investigation && <section className="investigation-result" aria-live="polite">
      <div className="result-header"><div><span className={`decision-dot decision-${investigation.decision}`} /><span>{investigation.decision === "sufficient" ? "Evidence found" : "Insufficient evidence"}</span></div><span>Top relevance score {investigation.confidence.toFixed(2)} · not a probability</span></div>
      <div className="result-answer"><span className="result-label">ANSWER.md</span><p>{investigation.answer ?? "RepoRecall found evidence but could not generate an answer."}</p>{investigation.generation_error && <div className="generation-note">{investigation.generation_error}</div>}</div>
      {investigation.citations.length > 0 && <div className="result-citations"><span className="result-label">Citations</span><div>{investigation.citations.map((citation, index) => <a key={citation} href={citation} target="_blank" rel="noreferrer"><span>[{index + 1}]</span>{citation.replace("https://github.com/", "")}</a>)}</div></div>}
      {investigation.evidence.length > 0 && <details className="result-evidence"><summary>Inspect {investigation.evidence.length} retrieved evidence items</summary><div>{investigation.evidence.map((item, index) => <a key={`${item.html_url}-${index}`} href={item.html_url} target="_blank" rel="noreferrer"><span className="evidence-type">{item.source_type.replaceAll("_", " ")}</span><strong>{item.title}</strong><p>{item.text.slice(0, 220)}{item.text.length > 220 ? "…" : ""}</p></a>)}</div></details>}
    </section>}
  </>;
}
