import { useEffect, useMemo, useState } from "react";

type HealthState = "checking" | "healthy" | "unreachable";
type RequestState = "idle" | "loading";
type View = "capture" | "plans" | "context";

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
  trade_plan_id: string;
  approval_state: string;
};

type PlanSummary = {
  id: string;
  trade_idea_id: string;
  trade_thesis_id: string;
  instrument_id: string;
  instrument_symbol: string | null;
  playbook_id: string;
  playbook_slug: string | null;
  purpose: string;
  direction: string;
  horizon: string;
  approval_state: string;
  created_at: string;
  linked_context_count: number;
};

type MarketContextSummary = {
  id: string;
  instrument_id: string;
  target_type: string | null;
  target_id: string | null;
  context_type: string;
  source: string;
  source_ref: string | null;
  observed_at: string;
  captured_at: string;
};

type PlanDetail = {
  idea: {
    id: string;
    instrument_id: string;
    instrument_symbol: string | null;
    instrument_name: string | null;
    playbook_id: string;
    playbook_slug: string | null;
    playbook_name: string | null;
    purpose: string;
    direction: string;
    horizon: string;
    status: string;
    created_at: string;
  };
  thesis: {
    id: string;
    reasoning: string;
    supporting_evidence: string[];
    risks: string[];
    disconfirming_signals: string[];
  };
  plan: {
    id: string;
    entry_criteria: string;
    invalidation: string;
    targets: string[];
    risk_model: string | null;
    sizing_assumptions: string | null;
    approval_state: string;
    created_at: string;
  };
  rule_evaluations: Array<{ id: string; passed: boolean; details: string | null }>;
  order_intents: Array<{ id: string; symbol: string; side: string; order_type: string; quantity: string; status: string }>;
  positions: Array<{ id: string; lifecycle_state: string; current_quantity: string; average_entry_price: string | null }>;
  market_context: MarketContextSummary[];
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
  { path: "TradeIdea.instrument_symbol", entity: "TradeIdea", field: "instrument_symbol", label: "Symbol", value: (draft) => draft.idea.instrument_symbol },
  { path: "TradeIdea.playbook_slug", entity: "TradeIdea", field: "playbook_slug", label: "Playbook", value: (draft) => draft.idea.playbook_slug },
  { path: "TradeIdea.purpose", entity: "TradeIdea", field: "purpose", label: "Purpose", value: (draft) => draft.idea.purpose },
  { path: "TradeIdea.direction", entity: "TradeIdea", field: "direction", label: "Direction", value: (draft) => draft.idea.direction },
  { path: "TradeIdea.horizon", entity: "TradeIdea", field: "horizon", label: "Horizon", value: (draft) => draft.idea.horizon },
  { path: "TradeThesis.reasoning", entity: "TradeThesis", field: "reasoning", label: "Reasoning", value: (draft) => draft.thesis.reasoning },
  { path: "TradePlan.entry_criteria", entity: "TradePlan", field: "entry_criteria", label: "Entry criteria", value: (draft) => draft.plan.entry_criteria },
  { path: "TradePlan.invalidation", entity: "TradePlan", field: "invalidation", label: "Invalidation", value: (draft) => draft.plan.invalidation },
];

export function App() {
  const [activeView, setActiveView] = useState<View>("capture");
  const [healthState, setHealthState] = useState<HealthState>("checking");
  const [instruments, setInstruments] = useState<Instrument[]>([]);
  const [playbooks, setPlaybooks] = useState<Playbook[]>([]);
  const [referenceError, setReferenceError] = useState<string | null>(null);
  const [apiError, setApiError] = useState<string | null>(null);

  const [sourceText, setSourceText] = useState("");
  const [draft, setDraft] = useState<TradeCaptureDraft>(emptyDraft);
  const [hasParsed, setHasParsed] = useState(false);
  const [parseState, setParseState] = useState<RequestState>("idle");
  const [saveState, setSaveState] = useState<RequestState>("idle");
  const [savedResult, setSavedResult] = useState<SavedTradeCapture | null>(null);

  const [plans, setPlans] = useState<PlanSummary[]>([]);
  const [planFilter, setPlanFilter] = useState("draft");
  const [planSort, setPlanSort] = useState("newest");
  const [selectedPlanId, setSelectedPlanId] = useState<string | null>(null);
  const [planDetail, setPlanDetail] = useState<PlanDetail | null>(null);
  const [plansState, setPlansState] = useState<RequestState>("idle");
  const [approveState, setApproveState] = useState<RequestState>("idle");

  const [contextRows, setContextRows] = useState<MarketContextSummary[]>([]);
  const [contextCandidates, setContextCandidates] = useState<MarketContextSummary[]>([]);
  const [attachState, setAttachState] = useState<RequestState>("idle");

  useEffect(() => {
    const controller = new AbortController();
    async function loadRuntimeState() {
      try {
        const healthResponse = await fetch(`${apiBaseUrl}/health`, { signal: controller.signal });
        setHealthState(healthResponse.ok ? "healthy" : "unreachable");
      } catch {
        if (!controller.signal.aborted) setHealthState("unreachable");
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
          fetch(`${apiBaseUrl}/reference/instruments`, { signal: controller.signal }),
          fetch(`${apiBaseUrl}/reference/playbooks`, { signal: controller.signal }),
        ]);
        if (!instrumentResponse.ok || !playbookResponse.ok) {
          setReferenceError("Reference lookup is unavailable.");
          return;
        }
        setInstruments((await instrumentResponse.json()) as Instrument[]);
        setPlaybooks((await playbookResponse.json()) as Playbook[]);
        setReferenceError(null);
      } catch {
        if (!controller.signal.aborted) setReferenceError("Reference lookup is unavailable.");
      }
    }
    void loadReferences();
    return () => controller.abort();
  }, []);

  useEffect(() => {
    if (activeView === "plans") void loadPlans();
    if (activeView === "context") void loadContextRows();
  }, [activeView, planFilter, planSort]);

  useEffect(() => {
    if (!selectedPlanId) {
      setPlanDetail(null);
      setContextCandidates([]);
      return;
    }
    void loadPlanDetail(selectedPlanId);
  }, [selectedPlanId]);

  useEffect(() => {
    if (planDetail) void loadContextCandidates(planDetail.idea.instrument_id);
  }, [planDetail?.plan.id, planDetail?.market_context.length]);

  const validationIssues = useMemo(() => buildValidationIssues(draft, hasParsed), [draft, hasParsed]);
  const issuesByPath = useMemo(() => groupIssues(validationIssues), [validationIssues]);
  const readyToSave = hasParsed && validationIssues.length === 0;

  async function loadPlans() {
    setPlansState("loading");
    setApiError(null);
    try {
      const params = new URLSearchParams({ sort: planSort });
      if (planFilter !== "all") params.set("approval_state", planFilter);
      const response = await fetch(`${apiBaseUrl}/trade-plans?${params.toString()}`);
      const body = await response.json();
      if (!response.ok) throw new Error(readErrorMessage(body, "Plan list failed."));
      const loaded = body as PlanSummary[];
      setPlans(loaded);
      if (!selectedPlanId && loaded.length > 0) setSelectedPlanId(loaded[0].id);
      if (selectedPlanId && !loaded.some((plan) => plan.id === selectedPlanId)) {
        setSelectedPlanId(loaded[0]?.id ?? null);
      }
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Plan list failed.");
    } finally {
      setPlansState("idle");
    }
  }

  async function loadPlanDetail(planId: string) {
    setApiError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/trade-plans/${planId}`);
      const body = await response.json();
      if (!response.ok) throw new Error(readErrorMessage(body, "Plan detail failed."));
      setPlanDetail(body as PlanDetail);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Plan detail failed.");
    }
  }

  async function loadContextRows() {
    setApiError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/market-context`);
      const body = await response.json();
      if (!response.ok) throw new Error(readErrorMessage(body, "Context list failed."));
      setContextRows(body as MarketContextSummary[]);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Context list failed.");
    }
  }

  async function loadContextCandidates(instrumentId: string) {
    try {
      const response = await fetch(`${apiBaseUrl}/market-context?instrument_id=${instrumentId}`);
      const body = await response.json();
      if (!response.ok) throw new Error(readErrorMessage(body, "Context candidates failed."));
      setContextCandidates(body as MarketContextSummary[]);
    } catch {
      setContextCandidates([]);
    }
  }

  async function handleParse() {
    if (!sourceText.trim() || parseState === "loading") return;
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
      if (!response.ok) throw new Error(readErrorMessage(body, "Trade capture parse failed."));
      setDraft((body as DraftResponse).draft);
      setHasParsed(true);
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Trade capture parse failed.");
    } finally {
      setParseState("idle");
    }
  }

  async function handleSave() {
    if (!readyToSave || saveState === "loading") return;
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
        const issues = readErrorIssues(body);
        if (issues.length > 0) {
          setDraft((current) => ({
            ...current,
            ambiguous_field_issues: [...current.ambiguous_field_issues, ...issues.filter((issue) => issue.issue_type === "ambiguous")],
          }));
        }
        throw new Error(readErrorMessage(body, "Trade capture save failed."));
      }
      const saved = body as SavedTradeCapture;
      setSavedResult(saved);
      setSelectedPlanId(saved.trade_plan_id);
      setActiveView("plans");
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Trade capture save failed.");
    } finally {
      setSaveState("idle");
    }
  }

  async function handleApprove() {
    if (!planDetail || approveState === "loading") return;
    setApproveState("loading");
    setApiError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/trade-plans/${planDetail.plan.id}/approve`, { method: "POST" });
      const body = await response.json();
      if (!response.ok) throw new Error(readErrorMessage(body, "Plan approval failed."));
      setPlanDetail(body as PlanDetail);
      await loadPlans();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Plan approval failed.");
    } finally {
      setApproveState("idle");
    }
  }

  async function handleAttach(snapshotId: string) {
    if (!planDetail || attachState === "loading") return;
    setAttachState("loading");
    setApiError(null);
    try {
      const response = await fetch(`${apiBaseUrl}/market-context/${snapshotId}/copy-to-target`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_type: "TradePlan", target_id: planDetail.plan.id }),
      });
      const body = await response.json();
      if (!response.ok) throw new Error(readErrorMessage(body, "Context attachment failed."));
      await loadPlanDetail(planDetail.plan.id);
      await loadPlans();
    } catch (error) {
      setApiError(error instanceof Error ? error.message : "Context attachment failed.");
    } finally {
      setAttachState("idle");
    }
  }

  function updateIdeaField(field: keyof TradeCaptureDraft["idea"], value: string) {
    setSavedResult(null);
    setDraft((current) => ({
      ...current,
      ambiguous_field_issues: clearAmbiguity(current.ambiguous_field_issues, `TradeIdea.${field}`),
      idea: { ...current.idea, [field]: normalizeInput(value) },
    }));
  }

  function updateThesisField(field: keyof TradeCaptureDraft["thesis"], value: string) {
    setSavedResult(null);
    setDraft((current) => ({
      ...current,
      ambiguous_field_issues: clearAmbiguity(current.ambiguous_field_issues, `TradeThesis.${field}`),
      thesis: { ...current.thesis, [field]: isListField(field) ? parseLines(value) : normalizeInput(value) },
    }));
  }

  function updatePlanField(field: keyof TradeCaptureDraft["plan"], value: string) {
    setSavedResult(null);
    setDraft((current) => ({
      ...current,
      ambiguous_field_issues: clearAmbiguity(current.ambiguous_field_issues, `TradePlan.${field}`),
      plan: { ...current.plan, [field]: isListField(field) ? parseLines(value) : normalizeInput(value) },
    }));
  }

  return (
    <main className="workspace-shell">
      <header className="workspace-header">
        <div>
          <p className="eyebrow">Milestone 9</p>
          <h1>Trading Workbench</h1>
        </div>
        <dl className="runtime-strip">
          <StatusItem label="API" value={healthState} state={healthState} />
          <StatusItem label="Instruments" value={String(instruments.length || "-")} />
          <StatusItem label="Playbooks" value={String(playbooks.length || "-")} />
        </dl>
      </header>

      <nav className="top-nav" aria-label="Workbench views">
        <button className={activeView === "capture" ? "nav-button active" : "nav-button"} onClick={() => setActiveView("capture")}>Capture</button>
        <button className={activeView === "plans" ? "nav-button active" : "nav-button"} onClick={() => setActiveView("plans")}>Plans</button>
        <button className={activeView === "context" ? "nav-button active" : "nav-button"} onClick={() => setActiveView("context")}>Context</button>
      </nav>

      {referenceError ? <div className="alert subtle">{referenceError}</div> : null}
      {apiError ? <div className="alert">{apiError}</div> : null}

      {activeView === "capture" ? (
        <CaptureView
          sourceText={sourceText}
          draft={draft}
          hasParsed={hasParsed}
          parseState={parseState}
          saveState={saveState}
          readyToSave={readyToSave}
          validationIssues={validationIssues}
          issuesByPath={issuesByPath}
          instruments={instruments}
          playbooks={playbooks}
          savedResult={savedResult}
          setSourceText={setSourceText}
          handleParse={handleParse}
          handleSave={handleSave}
          updateIdeaField={updateIdeaField}
          updateThesisField={updateThesisField}
          updatePlanField={updatePlanField}
        />
      ) : null}

      {activeView === "plans" ? (
        <PlansView
          plans={plans}
          planFilter={planFilter}
          planSort={planSort}
          selectedPlanId={selectedPlanId}
          planDetail={planDetail}
          plansState={plansState}
          approveState={approveState}
          attachState={attachState}
          contextCandidates={contextCandidates}
          setPlanFilter={setPlanFilter}
          setPlanSort={setPlanSort}
          setSelectedPlanId={setSelectedPlanId}
          handleApprove={handleApprove}
          handleAttach={handleAttach}
        />
      ) : null}

      {activeView === "context" ? <ContextView contextRows={contextRows} /> : null}
    </main>
  );
}

function CaptureView(props: {
  sourceText: string;
  draft: TradeCaptureDraft;
  hasParsed: boolean;
  parseState: RequestState;
  saveState: RequestState;
  readyToSave: boolean;
  validationIssues: DraftFieldIssue[];
  issuesByPath: Record<string, DraftFieldIssue[]>;
  instruments: Instrument[];
  playbooks: Playbook[];
  savedResult: SavedTradeCapture | null;
  setSourceText: (value: string) => void;
  handleParse: () => Promise<void>;
  handleSave: () => Promise<void>;
  updateIdeaField: (field: keyof TradeCaptureDraft["idea"], value: string) => void;
  updateThesisField: (field: keyof TradeCaptureDraft["thesis"], value: string) => void;
  updatePlanField: (field: keyof TradeCaptureDraft["plan"], value: string) => void;
}) {
  return (
    <>
      <section className="capture-grid">
        <section className="capture-input-panel">
          <div className="section-heading">
            <h2>Capture</h2>
            <span className="section-meta">{props.sourceText.trim().length} chars</span>
          </div>
          <textarea
            className="source-input"
            value={props.sourceText}
            onChange={(event) => props.setSourceText(event.target.value)}
            placeholder="NVDA long swing pullback-to-trend setup. Entry on reclaim of prior high. Stop below pullback low."
          />
          <div className="action-row">
            <button className="primary-button" disabled={!props.sourceText.trim() || props.parseState === "loading"} onClick={() => void props.handleParse()}>
              {props.parseState === "loading" ? "Parsing" : "Parse"}
            </button>
            <button className="secondary-button" disabled={!props.readyToSave || props.saveState === "loading"} onClick={() => void props.handleSave()}>
              {props.saveState === "loading" ? "Saving" : "Save draft"}
            </button>
          </div>
          <ReadinessSummary hasParsed={props.hasParsed} readyToSave={props.readyToSave} issueCount={props.validationIssues.length} />
        </section>

        <section className="draft-panel">
          <DraftSection title="Idea">
            <FieldShell label="Symbol" issues={props.issuesByPath["TradeIdea.instrument_symbol"]}>
              <select value={props.draft.idea.instrument_symbol ?? ""} onChange={(event) => props.updateIdeaField("instrument_symbol", event.target.value)}>
                <option value="">Select symbol</option>
                {props.instruments.map((instrument) => (
                  <option key={instrument.id} value={instrument.symbol}>{instrument.symbol}{instrument.name ? ` - ${instrument.name}` : ""}</option>
                ))}
              </select>
            </FieldShell>
            <FieldShell label="Playbook" issues={props.issuesByPath["TradeIdea.playbook_slug"]}>
              <select value={props.draft.idea.playbook_slug ?? ""} onChange={(event) => props.updateIdeaField("playbook_slug", event.target.value)}>
                <option value="">Select playbook</option>
                {props.playbooks.map((playbook) => <option key={playbook.id} value={playbook.slug}>{playbook.name}</option>)}
              </select>
            </FieldShell>
            <TextField label="Purpose" value={props.draft.idea.purpose} issues={props.issuesByPath["TradeIdea.purpose"]} onChange={(value) => props.updateIdeaField("purpose", value)} />
            <FieldShell label="Direction" issues={props.issuesByPath["TradeIdea.direction"]}>
              <select value={props.draft.idea.direction ?? ""} onChange={(event) => props.updateIdeaField("direction", event.target.value)}>
                <option value="">Select direction</option>
                <option value="long">long</option>
                <option value="short">short</option>
              </select>
            </FieldShell>
            <TextField label="Horizon" value={props.draft.idea.horizon} issues={props.issuesByPath["TradeIdea.horizon"]} onChange={(value) => props.updateIdeaField("horizon", value)} />
          </DraftSection>

          <DraftSection title="Thesis">
            <TextAreaField label="Reasoning" value={props.draft.thesis.reasoning} issues={props.issuesByPath["TradeThesis.reasoning"]} onChange={(value) => props.updateThesisField("reasoning", value)} />
            <TextAreaField label="Supporting evidence" value={formatLines(props.draft.thesis.supporting_evidence)} issues={props.issuesByPath["TradeThesis.supporting_evidence"]} onChange={(value) => props.updateThesisField("supporting_evidence", value)} />
            <TextAreaField label="Risks" value={formatLines(props.draft.thesis.risks)} issues={props.issuesByPath["TradeThesis.risks"]} onChange={(value) => props.updateThesisField("risks", value)} />
            <TextAreaField label="Disconfirming signals" value={formatLines(props.draft.thesis.disconfirming_signals)} issues={props.issuesByPath["TradeThesis.disconfirming_signals"]} onChange={(value) => props.updateThesisField("disconfirming_signals", value)} />
          </DraftSection>

          <DraftSection title="Plan">
            <TextAreaField label="Entry criteria" value={props.draft.plan.entry_criteria} issues={props.issuesByPath["TradePlan.entry_criteria"]} onChange={(value) => props.updatePlanField("entry_criteria", value)} />
            <TextAreaField label="Invalidation" value={props.draft.plan.invalidation} issues={props.issuesByPath["TradePlan.invalidation"]} onChange={(value) => props.updatePlanField("invalidation", value)} />
            <TextAreaField label="Targets" value={formatLines(props.draft.plan.targets)} issues={props.issuesByPath["TradePlan.targets"]} onChange={(value) => props.updatePlanField("targets", value)} />
            <TextAreaField label="Risk model" value={props.draft.plan.risk_model} issues={props.issuesByPath["TradePlan.risk_model"]} onChange={(value) => props.updatePlanField("risk_model", value)} />
            <TextAreaField label="Sizing assumptions" value={props.draft.plan.sizing_assumptions} issues={props.issuesByPath["TradePlan.sizing_assumptions"]} onChange={(value) => props.updatePlanField("sizing_assumptions", value)} />
          </DraftSection>
        </section>
      </section>
      {props.savedResult ? <SavedSummary savedResult={props.savedResult} /> : null}
    </>
  );
}

function PlansView(props: {
  plans: PlanSummary[];
  planFilter: string;
  planSort: string;
  selectedPlanId: string | null;
  planDetail: PlanDetail | null;
  plansState: RequestState;
  approveState: RequestState;
  attachState: RequestState;
  contextCandidates: MarketContextSummary[];
  setPlanFilter: (value: string) => void;
  setPlanSort: (value: string) => void;
  setSelectedPlanId: (value: string) => void;
  handleApprove: () => Promise<void>;
  handleAttach: (snapshotId: string) => Promise<void>;
}) {
  return (
    <section className="plans-workbench">
      <aside className="plan-list-panel">
        <div className="section-heading">
          <h2>Plans</h2>
          <span className="section-meta">{props.plansState === "loading" ? "Loading" : `${props.plans.length} shown`}</span>
        </div>
        <div className="toolbar">
          <select value={props.planFilter} onChange={(event) => props.setPlanFilter(event.target.value)}>
            <option value="draft">Draft</option>
            <option value="approved">Approved</option>
            <option value="all">All</option>
          </select>
          <select value={props.planSort} onChange={(event) => props.setPlanSort(event.target.value)}>
            <option value="newest">Newest</option>
            <option value="oldest">Oldest</option>
          </select>
        </div>
        <div className="plan-list">
          {props.plans.map((plan) => (
            <button key={plan.id} className={props.selectedPlanId === plan.id ? "plan-row active" : "plan-row"} onClick={() => props.setSelectedPlanId(plan.id)}>
              <span>{plan.instrument_symbol ?? plan.instrument_id}</span>
              <small>{plan.direction} {plan.purpose} / {plan.approval_state}</small>
              <small>{plan.linked_context_count} context</small>
            </button>
          ))}
        </div>
      </aside>
      <section className="detail-panel">
        {props.planDetail ? (
          <PlanDetailView
            detail={props.planDetail}
            approveState={props.approveState}
            attachState={props.attachState}
            contextCandidates={props.contextCandidates}
            handleApprove={props.handleApprove}
            handleAttach={props.handleAttach}
          />
        ) : (
          <div className="empty-state">No plan selected.</div>
        )}
      </section>
    </section>
  );
}

function PlanDetailView(props: {
  detail: PlanDetail;
  approveState: RequestState;
  attachState: RequestState;
  contextCandidates: MarketContextSummary[];
  handleApprove: () => Promise<void>;
  handleAttach: (snapshotId: string) => Promise<void>;
}) {
  const linkedIds = new Set(props.detail.market_context.map((snapshot) => snapshot.id));
  const attachable = props.contextCandidates.filter((snapshot) => !linkedIds.has(snapshot.id) && snapshot.target_id !== props.detail.plan.id);
  return (
    <div className="detail-stack">
      <section className="detail-header">
        <div>
          <p className="eyebrow">{props.detail.idea.instrument_symbol ?? props.detail.idea.instrument_id}</p>
          <h2>{props.detail.idea.direction} {props.detail.idea.purpose} / {props.detail.idea.horizon}</h2>
        </div>
        <span className={`status-pill ${props.detail.plan.approval_state}`}>{props.detail.plan.approval_state}</span>
        {props.detail.plan.approval_state === "draft" ? (
          <button className="primary-button" disabled={props.approveState === "loading"} onClick={() => void props.handleApprove()}>
            {props.approveState === "loading" ? "Approving" : "Approve"}
          </button>
        ) : null}
      </section>

      <DetailSection title="Idea">
        <Fact label="Playbook" value={props.detail.idea.playbook_name ?? props.detail.idea.playbook_slug ?? props.detail.idea.playbook_id} />
        <Fact label="Status" value={props.detail.idea.status} />
      </DetailSection>
      <DetailSection title="Thesis">
        <p>{props.detail.thesis.reasoning}</p>
        <List label="Evidence" values={props.detail.thesis.supporting_evidence} />
        <List label="Risks" values={props.detail.thesis.risks} />
        <List label="Disconfirming" values={props.detail.thesis.disconfirming_signals} />
      </DetailSection>
      <DetailSection title="Plan">
        <Fact label="Entry" value={props.detail.plan.entry_criteria} />
        <Fact label="Invalidation" value={props.detail.plan.invalidation} />
        <List label="Targets" values={props.detail.plan.targets} />
        <Fact label="Risk" value={props.detail.plan.risk_model ?? "-"} />
        <Fact label="Sizing" value={props.detail.plan.sizing_assumptions ?? "-"} />
      </DetailSection>
      <DetailSection title="Linked Records">
        <div className="metric-row">
          <Fact label="Rule evaluations" value={String(props.detail.rule_evaluations.length)} />
          <Fact label="Order intents" value={String(props.detail.order_intents.length)} />
          <Fact label="Positions" value={String(props.detail.positions.length)} />
        </div>
      </DetailSection>
      <DetailSection title="Market Context">
        <ContextTable rows={props.detail.market_context} />
      </DetailSection>
      <DetailSection title="Attach Existing Context">
        <div className="context-candidates">
          {attachable.length === 0 ? <p className="muted">No matching snapshots available.</p> : null}
          {attachable.map((snapshot) => (
            <div className="candidate-row" key={snapshot.id}>
              <span>{snapshot.context_type} / {snapshot.source}</span>
              <small>{formatDate(snapshot.observed_at)}</small>
              <button className="secondary-button" disabled={props.attachState === "loading"} onClick={() => void props.handleAttach(snapshot.id)}>
                Attach
              </button>
            </div>
          ))}
        </div>
      </DetailSection>
    </div>
  );
}

function ContextView({ contextRows }: { contextRows: MarketContextSummary[] }) {
  return (
    <section className="context-panel">
      <div className="section-heading">
        <h2>Context</h2>
        <span className="section-meta">{contextRows.length} snapshots</span>
      </div>
      <ContextTable rows={contextRows} />
    </section>
  );
}

function ContextTable({ rows }: { rows: MarketContextSummary[] }) {
  if (rows.length === 0) return <p className="muted">No context snapshots found.</p>;
  return (
    <div className="table">
      <div className="table-head">
        <span>Type</span>
        <span>Source</span>
        <span>Target</span>
        <span>Observed</span>
      </div>
      {rows.map((row) => (
        <div className="table-row" key={row.id}>
          <span>{row.context_type}</span>
          <span>{row.source}</span>
          <span>{row.target_type ? `${row.target_type}` : "Unlinked"}</span>
          <span>{formatDate(row.observed_at)}</span>
        </div>
      ))}
    </div>
  );
}

function StatusItem({ label, value, state }: { label: string; value: string; state?: HealthState }) {
  return (
    <div>
      <dt>{label}</dt>
      <dd className={state}>{value}</dd>
    </div>
  );
}

function DraftSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="draft-section">
      <h2>{title}</h2>
      <div className="field-grid">{children}</div>
    </section>
  );
}

function DetailSection({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <section className="detail-section">
      <h2>{title}</h2>
      <div className="detail-body">{children}</div>
    </section>
  );
}

function FieldShell({ label, issues, children }: { label: string; issues?: DraftFieldIssue[]; children: React.ReactNode }) {
  return (
    <label className={issues && issues.length > 0 ? "field has-issue" : "field"}>
      <span>{label}</span>
      {children}
      {issues && issues.length > 0 ? <span className="field-issues">{issues.map((issue) => issue.message).join(" ")}</span> : null}
    </label>
  );
}

function TextField({ label, value, issues, onChange }: { label: string; value: string | null; issues?: DraftFieldIssue[]; onChange: (value: string) => void }) {
  return (
    <FieldShell label={label} issues={issues}>
      <input value={value ?? ""} onChange={(event) => onChange(event.target.value)} />
    </FieldShell>
  );
}

function TextAreaField({ label, value, issues, onChange }: { label: string; value: string | null; issues?: DraftFieldIssue[]; onChange: (value: string) => void }) {
  return (
    <FieldShell label={label} issues={issues}>
      <textarea value={value ?? ""} onChange={(event) => onChange(event.target.value)} />
    </FieldShell>
  );
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="fact">
      <dt>{label}</dt>
      <dd>{value}</dd>
    </div>
  );
}

function List({ label, values }: { label: string; values: string[] }) {
  return <Fact label={label} value={values.length ? values.join("; ") : "-"} />;
}

function ReadinessSummary({ hasParsed, readyToSave, issueCount }: { hasParsed: boolean; readyToSave: boolean; issueCount: number }) {
  if (!hasParsed) return <p className="readiness neutral">Paste a trade note and parse it.</p>;
  if (readyToSave) return <p className="readiness ready">Draft is ready to save.</p>;
  return <p className="readiness blocked">{issueCount} field{issueCount === 1 ? "" : "s"} need attention.</p>;
}

function SavedSummary({ savedResult }: { savedResult: SavedTradeCapture }) {
  return (
    <section className="saved-summary">
      <div className="section-heading">
        <h2>Saved</h2>
        <span className="section-meta">{savedResult.approval_state}</span>
      </div>
      <p className="muted">Plan {savedResult.trade_plan_id} is available in Plans.</p>
    </section>
  );
}

function buildValidationIssues(draft: TradeCaptureDraft, hasParsed: boolean): DraftFieldIssue[] {
  if (!hasParsed) return [];
  const missingIssues = requiredFields.flatMap((definition) => {
    const value = definition.value(draft);
    if (value && value.trim()) return [];
    return [{ entity: definition.entity, field: definition.field, path: definition.path, issue_type: "missing" as const, message: `${definition.label} is required before save.`, candidates: [] }];
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
  return value.split("\n").map((line) => line.trim()).filter(Boolean);
}

function formatLines(values: string[]): string {
  return values.join("\n");
}

function isListField(field: string): boolean {
  return ["supporting_evidence", "risks", "disconfirming_signals", "targets"].includes(field);
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }).format(new Date(value));
}

function readErrorMessage(body: unknown, fallback: string): string {
  if (typeof body === "object" && body !== null && "detail" in body) {
    const detail = (body as { detail: unknown }).detail;
    if (typeof detail === "string") return detail;
    if (typeof detail === "object" && detail !== null && "message" in detail) {
      const message = (detail as { message: unknown }).message;
      if (typeof message === "string") return message;
    }
  }
  return fallback;
}

function readErrorIssues(body: unknown): DraftFieldIssue[] {
  if (typeof body !== "object" || body === null || !("detail" in body)) return [];
  const detail = (body as { detail: unknown }).detail;
  if (typeof detail !== "object" || detail === null || !("issues" in detail)) return [];
  const issues = (detail as { issues: unknown }).issues;
  return Array.isArray(issues) ? (issues as DraftFieldIssue[]) : [];
}
