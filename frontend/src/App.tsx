import { useEffect, useState } from "react";

type HealthState = "checking" | "healthy" | "unreachable";

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

export function App() {
  const [healthState, setHealthState] = useState<HealthState>("checking");

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
        </dl>
      </section>
    </main>
  );
}
