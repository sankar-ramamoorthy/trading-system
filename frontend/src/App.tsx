import { useEffect, useState } from "react";

type HealthState = "checking" | "healthy" | "unreachable";

type ReferenceSummary = {
  instruments: number | null;
  playbooks: number | null;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function App() {
  const [healthState, setHealthState] = useState<HealthState>("checking");
  const [referenceSummary, setReferenceSummary] = useState<ReferenceSummary>({
    instruments: null,
    playbooks: null,
  });

  useEffect(() => {
    const controller = new AbortController();

    async function checkHealth() {
      try {
        const response = await fetch(`${apiBaseUrl}/health`, {
          signal: controller.signal,
        });
        setHealthState(response.ok ? "healthy" : "unreachable");
      } catch {
        if (!controller.signal.aborted) {
          setHealthState("unreachable");
        }
      }
    }

    void checkHealth();

    return () => controller.abort();
  }, []);

  useEffect(() => {
    const controller = new AbortController();

    async function loadReferences() {
      try {
        const [instrumentResponse, playbookResponse] = await Promise.all([
          fetch(`${apiBaseUrl}/reference/instruments`, {
            signal: controller.signal,
          }),
          fetch(`${apiBaseUrl}/reference/playbooks`, {
            signal: controller.signal,
          }),
        ]);
        if (!instrumentResponse.ok || !playbookResponse.ok) {
          return;
        }
        const instruments = (await instrumentResponse.json()) as unknown[];
        const playbooks = (await playbookResponse.json()) as unknown[];
        setReferenceSummary({
          instruments: instruments.length,
          playbooks: playbooks.length,
        });
      } catch {
        if (!controller.signal.aborted) {
          setReferenceSummary({ instruments: null, playbooks: null });
        }
      }
    }

    void loadReferences();

    return () => controller.abort();
  }, []);

  return (
    <main className="app-shell">
      <section className="status-panel">
        <p className="eyebrow">Milestone 7A</p>
        <h1>Trading System</h1>
        <p className="summary">
          Local web runtime shell for the API-first trade capture workspace.
        </p>
        <dl className="health-grid">
          <div>
            <dt>API</dt>
            <dd className={healthState}>{healthState}</dd>
          </div>
          <div>
            <dt>Mode</dt>
            <dd>runtime skeleton</dd>
          </div>
          <div>
            <dt>Instruments</dt>
            <dd>{referenceSummary.instruments ?? "unavailable"}</dd>
          </div>
          <div>
            <dt>Playbooks</dt>
            <dd>{referenceSummary.playbooks ?? "unavailable"}</dd>
          </div>
        </dl>
      </section>
    </main>
  );
}
