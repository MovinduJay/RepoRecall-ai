import { ApiRequestError, getApiHealth } from "@/lib/api";

async function loadHealth() {
  try {
    return { health: await getApiHealth(), error: null };
  } catch (error) {
    const message =
      error instanceof ApiRequestError ? error.message : "An unexpected error occurred.";
    return { health: null, error: message };
  }
}

export default async function Home() {
  const { health, error } = await loadHealth();
  const online = health?.status === "ok";

  return (
    <main className="mx-auto flex min-h-screen w-full max-w-5xl flex-col px-6 py-12 sm:px-10">
      <header className="flex items-center justify-between border-b border-slate-800 pb-6">
        <div>
          <p className="font-mono text-xs uppercase tracking-[0.24em] text-cyan-400">
            Engineering memory
          </p>
          <h1 className="mt-2 text-2xl font-semibold tracking-tight text-white">
            RepoRecall AI
          </h1>
        </div>
        <div className="flex items-center gap-2 text-sm text-slate-300">
          <span
            className={`h-2.5 w-2.5 rounded-full ${online ? "bg-emerald-400" : "bg-rose-400"}`}
          />
          API {online ? "online" : "offline"}
        </div>
      </header>

      <section className="flex flex-1 items-center py-20">
        <div className="max-w-3xl">
          <p className="text-sm font-medium text-cyan-300">Historical bug-fix search</p>
          <h2 className="mt-4 text-4xl font-semibold leading-tight tracking-tight text-white sm:text-6xl">
            Find how your team solved this before.
          </h2>
          <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-400">
            RepoRecall searches issues, pull requests, commits, and code changes to surface
            evidence-backed fixes from repository history.
          </p>

          <div className="mt-10 rounded-2xl border border-slate-800 bg-slate-900/70 p-6">
            <div className="flex items-start justify-between gap-6">
              <div>
                <h3 className="font-medium text-white">Backend connection</h3>
                <p className="mt-2 text-sm leading-6 text-slate-400">
                  {online
                    ? "FastAPI responded successfully. The frontend is ready for repository workflows."
                    : error}
                </p>
              </div>
              <span
                className={`rounded-full px-3 py-1 text-xs font-semibold ${
                  online
                    ? "bg-emerald-400/10 text-emerald-300"
                    : "bg-rose-400/10 text-rose-300"
                }`}
              >
                {online ? "Healthy" : "Unavailable"}
              </span>
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
