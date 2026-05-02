import { useEffect, useMemo, useState } from "react";

type HealthState = "checking" | "healthy" | "unreachable";
type RequestState = "idle" | "loading";

type Instrument = {
  id: string;
  symbol: string;
  name: string | null;
};

type Playbook = {
  id: string;
  slug: string;
  name: string;
  description: string | null;
};

type DraftFieldIssue = {
  entity: "TradeIdea" | "TradeThesis" | "TradePlan";
  field: string;
  path: string;
  issue_type: "missing" | "ambiguous";
  message: string;
  candidates: string[];
};

type TradeCaptureDraft = {
  idea: {
    instrument_symbol: string | null;
    playbook_slug: string | null;
    purpose: string | null;
    direction: string | null;
    horizon: string | null;
  };
  thesis: {
    reasoning: string | null;
    supporting_evidence: string[];
    risks: string[];
    disconfirming_signals: string[];
  };
  plan: {
    entry_criteria: string | null;
    invalidation: string | null;
    targets: string[];
    risk_model: string | null;
    sizing_assumptions: string | null;
  };
  source_text: string | null;
  ambiguous_field_issues: DraftFieldIssue[];
};

type DraftResponse = {
  draft: TradeCaptureDraft;
  validation_issues: DraftFieldIssue[];
  ready_to_save: boolean;
};

type SavedTradeCapture = {
  trade_idea_id: string;
  trade_thesis_id: string;
  trade_plan_id: string;
  instrument_id: string;
  playbook_id: string;
  purpose: string;
  direction: string;
  horizon: string;
  reasoning: string;
  entry_criteria: string;
  invalidation: string;
  approval_state: string;
  targets: string[];
  risk_model: string | null;
  sizing_assumptions: string | null;
};

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000";

const emptyDraft: TradeCaptureDraft = {
  idea: {
    instrument_symbol: null,
    playbook_slug: null,
    purpose: null,
    direction: null,
    horizon: null,
  },
  thesis: {
    reasoning: null,
    supporting_evidence: [],
    risks: [],
    disconfirming_signals: [],
  },
  plan: {
    entry_criteria: null,
    invalidation: null,
    targets: [],
    risk_model: null,
    sizing_assumptions: null,
  },
  source_text: null,
  ambiguous_field_issues: [],
};

const requiredFields: Array<{
  path: string;
  entity: DraftFieldIssue["entity"];
  field: string;
  label: string;
  value: (draft: TradeCaptureDraft) => string | null;
}> = [
  {
    path: "TradeIdea.instrument_symbol",
    entity: "TradeIdea",
    field: "instrument_symbol",
    label: "Symbol",
    value: (draft) => draft.idea.instrument_symbol,
  },
  {
    path: "TradeIdea.playbook_slug",
    entity: "TradeIdea",
    field: "playbook_slug",
    label: "Playbook",
    value: (draft) => draft.idea.playbook_slug,
  },
  {
    path: "TradeIdea.purpose",
    entity: "TradeIdea",
    field: "purpose",
    label: "Purpose",
    value: (draft) => draft.idea.purpose,
  },
  {
    path: "TradeIdea.direction",
    entity: "TradeIdea",
    field: "direction",
    label: "Direction",
    value: (draft) => draft.idea.direction,
  },
  {
    path: "TradeIdea.horizon",
    entity: "TradeIdea",
    field: "horizon",
    label: "Horizon",
    value: (draft) => draft.idea.horizon,
  },
  {
    path: "TradeThesis.reasoning",
    entity: "TradeThesis",
    field: "reasoning",
    label: "Reasoning",
    value: (draft) => draft.thesis.reasoning,
  },
  {
    path: "TradePlan.entry_criteria",
    entity: "TradePlan",
    field: "entry_criteria",
    label: "Entry criteria",
    value: (draft) => draft.plan.entry_criteria,
  },
  {
    path: "TradePlan.invalidation",
    entity: "TradePlan",
    field: "invalidation",
    label: "Invalidation",
    value: (draft) => draft.plan.invalidation,
  },
];

export function App() {
  const [healthState, setHealthState] = useState<HealthState>("checking");
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [referenceError, setReferenceError] = useState<string | null>(null);
  const [sourceText, setSourceText] = useState("");
  const [draft, setDraft] = useState<TradeCaptureDraft>(emptyDraft);
  const [hasParsed, setHasParsed] = useState(false);
  const [parseState, setParseState] = useState<RequestState>("idle");
  const [saveState, setSaveState] = useState<RequestState>("idle");
  const [apiError, setApiError] = useState<string | null>(null);
  const [savedResult, setSavedResult] = useState<SavedTradeCapture | null>(null);

  useEffect(() => {
    const controller = new AbortController();

    async function loadRuntimeState() {
      try {
        const healthResponse = await fetch(`${apiBaseUrl}/health`, {
          signal: controller.signal,
        });
        setHealthState(healthResponse.ok ? "healthy" : "unreachable");
      } catch {
        if (!controller.signal.aborted) {
          setHealthState("unreachable");
        }
      }
    }

    void loadRuntimeState();

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
          setReferenceError("Reference lookup is unavailable.");
          return;
        }
        setInstruments((await instrumentResponse.json()) as Instrument[]);
        setPlaybooks((await playbookResponse.json()) as Playbook[]);
        setReferenceError(null);
      } catch {
        if (!controller.signal.aborted) {
          setReferenceError("Reference lookup is unavailable.");
        }
      }
    }

    void loadReferences();

    return () => controller.abort();
  }, []);

  const validationIssues = useMemo(
    () => buildValidationIssues(draft, hasParsed),
    [draft, hasParsed],
  );
  const issuesByPath = useMemo(() => groupIssues(validationIssues), [validationIssues]);
  const readyToSave = hasParsed && validationIssues.length === 0;

  async function handleParse() {
    if (!sourceText.trim() || parseState === "loading") {
      return;
    }
    setParseState("loading");
    setApiError(null);
    setSavedResult(null);
    try {
      const response = await fetch(`${apiBaseUrl}/trade-capture/parse`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ source_text: sourceText }),
      });
      const body = await response.json();
      if (!response.ok) {
        throw new Error(readErrorMessage(body, "Trade capture parse failed."));
      }
      const parsed = body as DraftResponse;
      setDraft(parsed.draft);
      setHasParsed(true);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Trade capture parse failed.");
    } finally {
      setParseState("idle");
    }
  }

  async function handleSave() {
    if (!readyToSave || saveState === "loading") {
      return;
    }
    setSaveState("loading");
    setApiError(null);
    setSavedResult(null);
    try {
      const response = await fetch(`${apiBaseUrl}/trade-capture/save`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(draft),
      });
      const body = await response.json();
      if (!response.ok) {
        const message = readErrorMessage(body, "Trade capture save failed.");
        const issues = readErrorIssues(body);
        if (issues.length > 0) {
          setDraft((current) => ({
            ...current,
            ambiguous_field_issues: [
              ...current.ambiguous_field_issues,
              ...issues.filter((issue) => issue.issue_type === "ambiguous"),
            ],
          }));
        }
        throw new Error(message);
      }
      setSavedResult(body as SavedTradeCapture);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Trade capture save failed.");
    } finally {
      setSaveState("idle");
    }
  }

  function updateIdeaField(
    field: keyof TradeCaptureDraft["idea"],
    value: string,
  ) {
    setSavedResult(null);
    setDraft((current) => ({
      ...current,
      ambiguous_field_issues: clearAmbiguity(
        current.ambiguous_field_issues,
        `TradeIdea.${field}`,
      ),
      idea: { ...current.idea, [field]: normalizeInput(value) },
    }));
  }

  function updateThesisField(
    field: keyof TradeCaptureDraft["thesis"],
    value: string,
  ) {
    setSavedResult(null);
    setDraft((current) => ({
      ...current,
      ambiguous_field_issues: clearAmbiguity(
        current.ambiguous_field_issues,
        `TradeThesis.${field}`,
      ),
      thesis: {
        ...current.thesis,
        [field]: isListField(field) ? parseLines(value) : normalizeInput(value),
      },
    }));
  }

  function updatePlanField(
    field: keyof TradeCaptureDraft["plan"],
    value: string,
  ) {
    setSavedResult(null);
    setDraft((current) => ({
      ...current,
      ambiguous_field_issues: clearAmbiguity(
        current.ambiguous_field_issues,
        `TradePlan.${field}`,
      ),
      plan: {
        ...current.plan,
        [field]: isListField(field) ? parseLines(value) : normalizeInput(value),
      },
    }));
  }

  return (
    <main className="workspace-shell">
      <header className="workspace-header">
        <div>
          <p className="eyebrow">Milestone 7F</p>
          <h1>Trade Capture Workspace</h1>
        </div>
        <dl className="runtime-strip">
          <StatusItem label="API" value={healthState} state={healthState} />
          <StatusItem label="Instruments" value={String(instruments.length || "-")} />
          <StatusItem label="Playbooks" value={String(playbooks.length || "-")} />
        </dl>
      </header>

      {referenceError ? <div className="alert subtle">{referenceError}</div> : null}
      {apiError ? <div className="alert">{apiError}</div> : null}

      <section className="capture-grid">
        <section className="capture-input-panel">
          <div className="section-heading">
            <h2>Capture</h2>
            <span className="section-meta">{sourceText.trim().length} chars</span>
          </div>
          <textarea
            className="source-input"
            value={sourceText}
            onChange={(event) => setSourceText(event.target.value)}
            placeholder="NVDA long swing pullback-to-trend setup. Entry on reclaim of prior high. Stop below pullback low. Target prior high. Thesis: trend remains intact after controlled pullback."
          />
          <div className="action-row">
            <button
              className="primary-button"
              disabled={!sourceText.trim() || parseState === "loading"}
              onClick={() => void handleParse()}
            >
              {parseState === "loading" ? "Parsing" : "Parse"}
            </button>
            <button
              className="secondary-button"
              disabled={!readyToSave || saveState === "loading"}
              onClick={() => void handleSave()}
            >
              {saveState === "loading" ? "Saving" : "Save draft"}
            </button>
          </div>
          <ReadinessSummary
            hasParsed={hasParsed}
            readyToSave={readyToSave}
            issueCount={validationIssues.length}
          />
        </section>

        <section className="draft-panel">
          <DraftSection title="Idea">
            <FieldShell
              label="Symbol"
              issues={issuesByPath["TradeIdea.instrument_symbol"]}
            >
              <select
                value={draft.idea.instrument_symbol ?? ""}
                onChange={(event) =>
                  updateIdeaField("instrument_symbol", event.target.value)
                }
              >
                <option value="">Select symbol</option>
                {instruments.map((instrument) => (
                  <option key={instrument.id} value={instrument.symbol}>
                    {instrument.symbol}
                    {instrument.name ? ` - ${instrument.name}` : ""}
                  </option>
                ))}
              </select>
            </FieldShell>
            <FieldShell
              label="Playbook"
              issues={issuesByPath["TradeIdea.playbook_slug"]}
            >
              <select
                value={draft.idea.playbook_slug ?? ""}
                onChange={(event) =>
                  updateIdeaField("playbook_slug", event.target.value)
                }
              >
                <option value="">Select playbook</option>
                {playbooks.map((playbook) => (
                  <option key={playbook.id} value={playbook.slug}>
                    {playbook.name}
                  </option>
                ))}
              </select>
            </FieldShell>
            <FieldShell label="Purpose" issues={issuesByPath["TradeIdea.purpose"]}>
              <input
                value={draft.idea.purpose ?? ""}
                onChange={(event) => updateIdeaField("purpose", event.target.value)}
                placeholder="swing"
              />
            </FieldShell>
            <FieldShell label="Direction" issues={issuesByPath["TradeIdea.direction"]}>
              <select
                value={draft.idea.direction ?? ""}
                onChange={(event) => updateIdeaField("direction", event.target.value)}
              >
                <option value="">Select direction</option>
                <option value="long">long</option>
                <option value="short">short</option>
              </select>
            </FieldShell>
            <FieldShell label="Horizon" issues={issuesByPath["TradeIdea.horizon"]}>
              <input
                value={draft.idea.horizon ?? ""}
                onChange={(event) => updateIdeaField("horizon", event.target.value)}
                placeholder="days_to_weeks"
              />
            </FieldShell>
          </DraftSection>

          <DraftSection title="Thesis">
            <FieldShell
              label="Reasoning"
              issues={issuesByPath["TradeThesis.reasoning"]}
            >
              <textarea
                value={draft.thesis.reasoning ?? ""}
                onChange={(event) => updateThesisField("reasoning", event.target.value)}
              />
            </FieldShell>
            <FieldShell
              label="Supporting evidence"
              issues={issuesByPath["TradeThesis.supporting_evidence"]}
            >
              <textarea
                value={formatLines(draft.thesis.supporting_evidence)}
                onChange={(event) =>
                  updateThesisField("supporting_evidence", event.target.value)
                }
              />
            </FieldShell>
            <FieldShell label="Risks" issues={issuesByPath["TradeThesis.risks"]}>
              <textarea
                value={formatLines(draft.thesis.risks)}
                onChange={(event) => updateThesisField("risks", event.target.value)}
              />
            </FieldShell>
            <FieldShell
              label="Disconfirming signals"
              issues={issuesByPath["TradeThesis.disconfirming_signals"]}
            >
              <textarea
                value={formatLines(draft.thesis.disconfirming_signals)}
                onChange={(event) =>
                  updateThesisField("disconfirming_signals", event.target.value)
                }
              />
            </FieldShell>
          </DraftSection>

          <DraftSection title="Plan">
            <FieldShell
              label="Entry criteria"
              issues={issuesByPath["TradePlan.entry_criteria"]}
            >
              <textarea
                value={draft.plan.entry_criteria ?? ""}
                onChange={(event) =>
                  updatePlanField("entry_criteria", event.target.value)
                }
              />
            </FieldShell>
            <FieldShell
              label="Invalidation"
              issues={issuesByPath["TradePlan.invalidation"]}
            >
              <textarea
                value={draft.plan.invalidation ?? ""}
                onChange={(event) => updatePlanField("invalidation", event.target.value)}
              />
            </FieldShell>
            <FieldShell label="Targets" issues={issuesByPath["TradePlan.targets"]}>
              <textarea
                value={formatLines(draft.plan.targets)}
                onChange={(event) => updatePlanField("targets", event.target.value)}
              />
            </FieldShell>
            <FieldShell label="Risk model" issues={issuesByPath["TradePlan.risk_model"]}>
              <textarea
                value={draft.plan.risk_model ?? ""}
                onChange={(event) => updatePlanField("risk_model", event.target.value)}
              />
            </FieldShell>
            <FieldShell
              label="Sizing assumptions"
              issues={issuesByPath["TradePlan.sizing_assumptions"]}
            >
              <textarea
                value={draft.plan.sizing_assumptions ?? ""}
                onChange={(event) =>
                  updatePlanField("sizing_assumptions", event.target.value)
                }
              />
            </FieldShell>
          </DraftSection>
        </section>
      </section>

      {savedResult ? <SavedSummary savedResult={savedResult} /> : null}
    </main>
  );
}

function StatusItem({
  label,
  value,
  state,
}: {
  label: string;
  value: string;
  state?: HealthState;
}) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className={state}>{value}</dd>
    </div>
  );
}

function DraftSection({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="draft-section">
      <h2>{title}</h2>
      <div className="field-grid">{children}</div>
    </section>
  );
}

function FieldShell({
  label,
  issues,
  children,
}: {
  label: string;
  issues?: DraftFieldIssue[];
  children: React.ReactNode;
}) {
  return (
    <label className={issues && issues.length > 0 ? "field has-issue" : "field"}>
      <span>{label}</span>
      {children}
      {issues && issues.length > 0 ? (
        <span className="field-issues">
          {issues.map((issue) => issue.message).join(" ")}
        </span>
      ) : null}
    </label>
  );
}

function ReadinessSummary({
  hasParsed,
  readyToSave,
  issueCount,
}: {
  hasParsed: boolean;
  readyToSave: boolean;
  issueCount: number;
}) {
  if (!hasParsed) {
    return <p className="readiness neutral">Paste a trade note and parse it.</p>;
  }
  if (readyToSave) {
    return <p className="readiness ready">Draft is ready to save.</p>;
  }
  return (
    <p className="readiness blocked">
      {issueCount} field{issueCount === 1 ? "" : "s"} need attention.
    </p>
  );
}

function SavedSummary({ savedResult }: { savedResult: SavedTradeCapture }) {
  return (
    <section className="saved-summary">
      <div className="section-heading">
        <h2>Saved</h2>
        <span className="section-meta">{savedResult.approval_state}</span>
      </div>
      <dl className="saved-grid">
        <div>
          <dt>Idea</dt>
          <dd>{savedResult.trade_idea_id}</dd>
        </div>
        <div>
          <dt>Thesis</dt>
          <dd>{savedResult.trade_thesis_id}</dd>
        </div>
        <div>
          <dt>Plan</dt>
          <dd>{savedResult.trade_plan_id}</dd>
        </div>
        <div>
          <dt>Trade</dt>
          <dd>
            {savedResult.direction} {savedResult.purpose} / {savedResult.horizon}
          </dd>
        </div>
      </dl>
    </section>
  );
}

function buildValidationIssues(
  draft: TradeCaptureDraft,
  hasParsed: boolean,
): DraftFieldIssue[] {
  if (!hasParsed) {
    return [];
  }
  const missingIssues = requiredFields.flatMap((definition) => {
    const value = definition.value(draft);
    if (value && value.trim()) {
      return [];
    }
    return [
      {
        entity: definition.entity,
        field: definition.field,
        path: definition.path,
        issue_type: "missing" as const,
        message: `${definition.label} is required before save.`,
        candidates: [],
      },
    ];
  });
  return [...missingIssues, ...draft.ambiguous_field_issues];
}

function groupIssues(issues: DraftFieldIssue[]): Record<string, DraftFieldIssue[]> {
  return issues.reduce<Record<string, DraftFieldIssue[]>>((groups, issue) => {
    groups[issue.path] = [...(groups[issue.path] ?? []), issue];
    return groups;
  }, {});
}

function clearAmbiguity(issues: DraftFieldIssue[], path: string): DraftFieldIssue[] {
  return issues.filter((issue) => issue.path !== path);
}

function normalizeInput(value: string): string | null {
  return value.trim() ? value : null;
}

function parseLines(value: string): string[] {
  return value
    .split("\n")
    .map((line) => line.trim())
    .filter(Boolean);
}

function formatLines(values: string[]): string {
  return values.join("\n");
}

function isListField(field: string): boolean {
  return [
    "supporting_evidence",
    "risks",
    "disconfirming_signals",
    "targets",
  ].includes(field);
}

function readErrorMessage(body: unknown, fallback: string): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") {
      return detail;
    }
    if (typeof detail === "object" && detail !== null && "message" in detail) {
      const message = (detail as { message: unknown }).message;
      if (typeof message === "string") {
        return message;
      }
    }
  }
  return fallback;
}

function readErrorIssues(body: unknown): DraftFieldIssue[] {
  if (typeof body !== "object" || body === null || !("detail" in body)) {
    return [];
  }
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail !== "object" || detail === null || !("issues" in detail)) {
    return [];
  }
  const issues = (detail as { issues: unknown }).issues;
  return Array.isArray(issues) ? (issues as DraftFieldIssue[]) : [];
}
