import { lazy, memo, Suspense, useEffect, useMemo, useRef, useState, type RefObject } from 'react';
import { api, DemoDto, DocumentDto, EvaluationDto, MatrixDto, RequirementDto, ResultDto, RunDto } from './api';

const Authenticator = lazy(async () => {
  const [module] = await Promise.all([
    import('@aws-amplify/ui-react'),
    import('@aws-amplify/ui-react/styles.css'),
  ]);
  return { default: module.Authenticator };
});

type Page = 'home' | 'demo' | 'app';

function pageFromLocation(): Page {
  if (window.location.pathname === '/demo') return 'demo';
  if (window.location.pathname === '/app') return 'app';
  return 'home';
}

export function App() {
  const [page, setPage] = useState<Page>(pageFromLocation);
  const [health, setHealth] = useState<{ data: { status: string } } | null>(null);
  const [demo, setDemo] = useState<DemoDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then((response) => {
      if (typeof response?.data?.status !== 'string') {
        setError('API health returned an unexpected response.');
        return;
      }
      setHealth(response);
    }).catch(() => setError('API health is not reachable yet.'));
    const onPopState = () => setPage(pageFromLocation());
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    if (page !== 'demo') return;
    let cancelled = false;
    api.demo()
      .then((response) => { if (!cancelled) setDemo(response); })
      .catch(() => { if (!cancelled) setError('Demo data is not reachable yet.'); });
    return () => { cancelled = true; };
  }, [page]);

  const navigate = (next: Page) => {
    const path = next === 'home' ? '/' : `/${next}`;
    window.history.pushState({}, '', path);
    setPage(next);
    setError(null);
  };

  return <div className="shell">
    <header className="topbar">
      <button className="wordmark" onClick={() => navigate('home')} aria-label="Go home">VERIBID</button>
      <nav aria-label="Main navigation">
        <button onClick={() => navigate('demo')}>Public demo</button>
        <button className="nav-primary" onClick={() => navigate('app')}>Open workspace</button>
      </nav>
    </header>
    {page === 'home' && <Landing health={health} onDemo={() => navigate('demo')} onApp={() => navigate('app')} />}
    {page === 'demo' && <Demo demo={demo} onBack={() => navigate('home')} />}
    {page === 'app' && <Workspace onBack={() => navigate('home')} onDemo={() => navigate('demo')} />}
    {error && <div className={`toast${page === 'app' ? ' toast-workspace' : ''}`} role="status">{error}</div>}
    <footer><span>Evidence first. Decisions remain human.</span><span>API {health?.data?.status ?? 'checking'}</span></footer>
  </div>;
}

function Landing({ health, onDemo, onApp }: { health: { data: { status: string } } | null; onDemo: () => void; onApp: () => void }) {
  return <main>
    <section className="hero">
      <div className="eyebrow">EVIDENCE-DRIVEN BID EVALUATION</div>
      <h1>Turn vendor claims into <em>defensible</em> decisions.</h1>
      <p className="lede">VeriBid connects every assessment to source evidence, separates deterministic scoring from semantic reasoning, and keeps final judgment with your review team.</p>
      <div className="hero-actions"><button className="button-primary" onClick={onDemo}>Explore the public demo <span>↗</span></button><button className="button-quiet" onClick={onApp}>Start an evaluation</button></div>
      <div className="health-pill"><span className={health?.data?.status === 'ok' ? 'dot live' : 'dot'} /> {health?.data?.status === 'ok' ? 'API connected' : 'Connecting to API'} </div>
    </section>
    <section className="feature-grid">
      <Feature number="01" title="Grounded by evidence" text="Every visible claim points back to a document, page, section, or cell. No unsupported confidence theater." />
      <Feature number="02" title="Deterministic where it matters" text="Thresholds, totals, SLAs, TCO, and weighted scores run in code—not in a language model." />
      <Feature number="03" title="Human-owned outcome" text="Reviewers accept or override a suggestion with rationale. The original suggestion and audit trail remain intact." />
    </section>
  </main>;
}

const Feature = memo(function Feature({ number, title, text }: { number: string; title: string; text: string }) {
  return <article className="feature"><span className="feature-number">{number}</span><h2>{title}</h2><p>{text}</p></article>;
});

function Demo({ demo, onBack }: { demo: DemoDto | null; onBack: () => void }) {
  const [selectedResult, setSelectedResult] = useState<ResultDto | null>(null);
  const matrixByCell = useMemo(() => new Map((demo?.data.matrix ?? []).map((item) => [`${item.requirement_id}:${item.vendor_id}`, item])), [demo]);

  const openDemoResult = (req: { id: string; text: string; category: string }, vendor: { vendor_id: string; name: string }, cell: DemoDto['data']['matrix'][number]) => {
    const claimIds = cell.source_pointers.map((_, index) => `DEMO_CLAIM_${vendor.vendor_id}_${req.id}_${index + 1}`);
    setSelectedResult({
      evaluation_result_id: `DEMO_${req.id}_${vendor.vendor_id}`,
      requirement_id: req.id,
      vendor_id: vendor.vendor_id,
      proposal_id: `${vendor.vendor_id}_PROPOSAL`,
      state: cell.state,
      suggested_score: cell.state === 'SATISFIED' ? 10 : cell.state === 'PARTIALLY_SATISFIED' ? 6 : 0,
      max_score: 10,
      rationale: `Synthetic demo scenario for "${req.text}". This is not an AI-generated evaluation or an assessment of a real vendor document.`,
      specialist: req.category === 'TECHNICAL' ? 'TECHNICAL_SPECIALIST' : req.category === 'COMPLIANCE' ? 'COMPLIANCE_SPECIALIST' : 'COMMERCIAL_SPECIALIST',
      evidence_claims: cell.source_pointers.map((pointer, index) => {
        const conflict = cell.conflict_pairs?.[0];
        return {
          evidence_claim_id: claimIds[index],
          claim_text: conflict
            ? `Synthetic scenario statement: ${index === 0 ? conflict.left : conflict.right}`
            : `Synthetic fixture locator: ${pointer.locator}. No real proposal text or vendor file is included.`,
          relation: cell.state === 'NOT_SATISFIED' || (conflict && index > 0) ? 'contradicts' : 'supports',
          confidence: cell.confidence,
          source_pointer: {
            source_pointer_id: `DEMO_PTR_${pointer.document_id}_${pointer.page ?? 'NA'}`,
            document_id: pointer.document_id,
            document_name: `${pointer.document_id}.pdf (synthetic fixture)`,
            document_type: 'PDF',
            page_number: pointer.page,
            resolvable: false,
          },
        };
      }),
      conflict_pairs: (cell.conflict_pairs ?? []).map((_, index) => ({
        supporting_claim_id: claimIds[index * 2] ?? claimIds[0] ?? `DEMO_MISSING_SUPPORT_${index}`,
        contradicting_claim_id: claimIds[index * 2 + 1] ?? `DEMO_MISSING_CONTRADICTION_${index}`,
        conflict_type: 'SYNTHETIC_DEMO_SCENARIO',
        resolution_status: 'UNRESOLVED',
      })),
      human_review: null,
    });
  };

  return <main className="content">
    <button className="back" onClick={onBack}>← Back to overview</button>
    <div className="eyebrow">INTERACTIVE PUBLIC DEMO · SYNTHETIC DATA</div>
    <h1>{demo?.data.title ?? 'A transparent evaluation, end to end.'}</h1>
    <p className="lede">Explore the basic review flow without an account. All vendors, requirements, and evidence are synthetic; review changes stay in this browser session. No uploads or real AI analysis.</p>
    {demo ? <>
      <div className="stats">
        <div><strong>{demo.data.requirements.length}</strong><span>requirements</span></div>
        <div><strong>{demo.data.vendors.length}</strong><span>vendors</span></div>
        <div><strong>{demo.data.status}</strong><span>evaluation state</span></div>
      </div>
      <div className="matrix-card">
        <div className="card-heading">
          <span>Evidence matrix</span>
          <small>Click any cell to inspect evidence claims</small>
        </div>
        <table>
          <thead>
            <tr>
              <th>Requirement</th>
              {demo.data.vendors.map((vendor) => <th key={vendor.vendor_id}>{vendor.name}</th>)}
            </tr>
          </thead>
          <tbody>
            {demo.data.requirements.map((req) => <tr key={req.id}>
              <th><span>{req.category}</span>{req.text}</th>
              {demo.data.vendors.map((vendor) => {
                const cell = matrixByCell.get(`${req.id}:${vendor.vendor_id}`);
                const demoCell = cell ?? { requirement_id: req.id, vendor_id: vendor.vendor_id, state: 'INSUFFICIENT_EVIDENCE', confidence: 0, source_pointers: [] };
                return <td key={vendor.vendor_id}>
                  <button className="matrix-cell" onClick={() => openDemoResult(req, vendor, demoCell)}>
                    <StateBadge state={demoCell.state} confidence={demoCell.confidence} />
                    <small>click to inspect evidence</small>
                  </button>
                </td>;
              })}
            </tr>)}
          </tbody>
        </table>
      </div>
      {selectedResult && <ResultPanel result={selectedResult} simulation onClose={() => setSelectedResult(null)} onReview={(body) => {
        setSelectedResult((prev) => prev ? { ...prev, human_review: { human_review_id: 'DEMO_REV_01', evaluation_result_id: prev.evaluation_result_id, action: body.action, system_state: prev.state, system_score: prev.suggested_score, final_state: body.final_state, final_score: body.final_score, rationale: body.rationale, reviewer_sub: 'demo-session', reviewed_at: new Date().toISOString() } } : null);
      }} />}
    </> : <div className="loading-card">Loading the public fixture…</div>}
  </main>;
}

const StateBadge = memo(function StateBadge({ state, confidence }: { state: string; confidence?: number }) {
  const className = state === 'SATISFIED' ? 'satisfied' : state === 'CONFLICTING_EVIDENCE' ? 'conflict' : state === 'NOT_SATISFIED' ? 'not' : state === 'PARTIALLY_SATISFIED' ? 'partial' : 'insufficient';
  const icon = state === 'SATISFIED' ? '✓' : state === 'CONFLICTING_EVIDENCE' ? '⚠' : state === 'NOT_SATISFIED' ? '✕' : state === 'PARTIALLY_SATISFIED' ? '~' : '?';
  return <div className={`state ${className}`}><strong><span className="badge-icon">{icon}</span> {state.replaceAll('_', ' ')}</strong>{confidence !== undefined && <small>{Math.round(confidence * 100)}% confidence</small>}</div>;
});

function Workspace({ onBack, onDemo }: { onBack: () => void; onDemo: () => void }) {
  return <main className="content workspace-entry">
    <div className="workspace-card workspace-auth-card">
      <div className="workspace-auth-intro">
        <div className="eyebrow">SECURE WORKSPACE</div>
        <h2>Sign in to VeriBid</h2>
        <p>Create an account or sign in to review evidence-backed bids.</p>
      </div>
      <div className="authenticator-shell">
        <Suspense fallback={<div className="loading-card">Loading auth provider…</div>}>
          <Authenticator loginMechanisms={['email']}>
            {({ user, signOut }) => <AuthenticatedWorkspace userEmail={user?.signInDetails?.loginId ?? 'authenticated user'} onBack={onBack} onSignOut={signOut} />}
          </Authenticator>
        </Suspense>
      </div>
      <button className="workspace-demo-link" onClick={onDemo}>Try the interactive demo (no sign-up)</button>
    </div>
  </main>;
}

function AuthenticatedWorkspace({ userEmail, onBack, onSignOut }: { userEmail: string; onBack: () => void; onSignOut?: () => void }) {
  const [name, setName] = useState('Cloud platform procurement');
  const [evaluation, setEvaluation] = useState<EvaluationDto | null>(null);
  const [documents, setDocuments] = useState<DocumentDto[]>([]);
  const [requirements, setRequirements] = useState<RequirementDto[]>([]);
  const [matrix, setMatrix] = useState<MatrixDto | null>(null);
  const [run, setRun] = useState<RunDto | null>(null);
  const [selectedResult, setSelectedResult] = useState<ResultDto | null>(null);
  const [role, setRole] = useState('BUYER_RFP');
  const [vendorId, setVendorId] = useState('');
  const [proposalId, setProposalId] = useState('');
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const extractionRefreshTimer = useRef<number | null>(null);
  const resultsSectionRef = useRef<HTMLElement | null>(null);
  const lastAutoScrolledRunId = useRef<string | null>(null);

  const resultCells = matrix?.rows.flatMap((row) => row.results) ?? [];
  const hasResults = resultCells.length > 0;
  const pendingReviewCount = resultCells.filter((cell) => cell.review_status !== 'CONFIRMED').length;
  const conflictCount = resultCells.filter((cell) => cell.has_conflict).length;
  const runIsActive = Boolean(run && !['COMPLETED', 'FAILED', 'PARTIALLY_COMPLETED'].includes(run.status));
  const hasBuyerBrief = documents.some((document) => document.document_role === 'BUYER_RFP')
    && documents.some((document) => document.document_role === 'BUYER_RUBRIC');
  const hasVendorEvidence = documents.some((document) => document.document_role.startsWith('VENDOR_'));
  const currentStep = !hasBuyerBrief ? 1 : !requirements.length ? 2 : !hasVendorEvidence ? 3 : !hasResults ? 4 : 5;

  const scrollToResults = () => {
    if (!resultsSectionRef.current) return;
    const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
    resultsSectionRef.current.scrollIntoView({ behavior: reduceMotion ? 'auto' : 'smooth', block: 'start' });
    resultsSectionRef.current.querySelector('h2')?.focus({ preventScroll: true });
  };

  const refresh = async (evaluationId: string) => {
    const [evaluationResponse, documentResponse, requirementResponse] = await Promise.all([
      api.getEvaluation(evaluationId), api.listDocuments(evaluationId), api.listRequirements(evaluationId),
    ]);
    setEvaluation(evaluationResponse.data);
    setDocuments(documentResponse.data);
    setRequirements(requirementResponse.data);
    if (requirementResponse.data.length) {
      try { setMatrix((await api.matrix(evaluationId)).data); } catch { /* results may not exist yet */ }
    } else setMatrix(null);
  };

  useEffect(() => () => {
    if (extractionRefreshTimer.current !== null) window.clearTimeout(extractionRefreshTimer.current);
  }, []);

  const create = async () => {
    setError(null); setBusy('create');
    try { const result = await api.createEvaluation(name); setEvaluation(result.data); await refresh(result.data.evaluation_id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not create evaluation'); }
    finally { setBusy(null); }
  };

  const upload = async (file: File) => {
    if (!evaluation) return;
    const scopedVendorId = vendorId.trim();
    const scopedProposalId = proposalId.trim();
    if (role.startsWith('VENDOR_') && (!scopedVendorId || !scopedProposalId)) {
      setError('Enter both the vendor ID and proposal ID before uploading this file.');
      setUploadStatus(null);
      return;
    }
    const mediaType = file.type || (file.name.endsWith('.pdf') ? 'application/pdf' : file.name.endsWith('.docx') ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    setError(null); setUploadStatus('Preparing a verified upload…'); setBusy('upload');
    try {
      const uploadFile = file.type === mediaType ? file : new File([file], file.name, { type: mediaType });
      const initialized = await api.initializeDocument(evaluation.evaluation_id, uploadFile, role, role.startsWith('VENDOR_') ? scopedVendorId : undefined, role.startsWith('VENDOR_') ? scopedProposalId : undefined);
      const uploadResponse = await fetch(initialized.data.upload.url, { method: 'PUT', headers: initialized.data.upload.required_headers, body: file });
      if (!uploadResponse.ok) throw new Error(`S3 upload failed (${uploadResponse.status})`);
      await api.completeDocument(evaluation.evaluation_id, initialized.data.document_id);
      setUploadStatus(`${file.name} uploaded and queued for verification.`);
      await refresh(evaluation.evaluation_id);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Upload failed'); setUploadStatus(null); }
    finally { setBusy(null); }
  };

  const extract = async () => {
    if (!evaluation) return;
    setBusy('extract'); setError(null);
    try {
      await api.extractRequirements(evaluation.evaluation_id);
      setUploadStatus('Requirement extraction queued. Refreshing shortly…');
      if (extractionRefreshTimer.current !== null) window.clearTimeout(extractionRefreshTimer.current);
      extractionRefreshTimer.current = window.setTimeout(() => {
        extractionRefreshTimer.current = null;
        void refresh(evaluation.evaluation_id);
      }, 2500);
    }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not extract requirements'); }
    finally { setBusy(null); }
  };

  const startRun = async () => {
    if (!evaluation) return;
    setBusy('run'); setError(null); setRun(null); setMatrix(null); setSelectedResult(null);
    try {
      const started = await api.startRun(evaluation.evaluation_id, Array.from(new Set(documents.map((item) => item.vendor_id).filter((value): value is string => Boolean(value)))));
      setRun({ run_id: started.data.run_id, status: started.data.status });
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not start evaluation'); }
    finally { setBusy(null); }
  };

  useEffect(() => {
    const evaluationId = evaluation?.evaluation_id;
    const runId = run?.run_id;
    if (!evaluationId || !runId || ['COMPLETED', 'FAILED', 'PARTIALLY_COMPLETED'].includes(run.status)) return;
    let cancelled = false;
    let inFlight = false;
    const poll = async () => {
      if (cancelled || inFlight) return;
      inFlight = true;
      try {
        const next = (await api.getRun(evaluationId, runId)).data;
        if (cancelled) return;
        setRun(next);
        if (['COMPLETED', 'FAILED', 'PARTIALLY_COMPLETED'].includes(next.status)) {
          const matrixResponse = await api.matrix(evaluationId);
          if (!cancelled) setMatrix(matrixResponse.data);
        }
      } catch (reason) {
        if (!cancelled) setError(reason instanceof Error ? reason.message : 'Could not read evaluation progress');
      } finally {
        inFlight = false;
      }
    };
    void poll();
    const timer = window.setInterval(() => void poll(), 2000);
    return () => { cancelled = true; window.clearInterval(timer); };
  }, [evaluation?.evaluation_id, run?.run_id, run?.status]);

  useEffect(() => {
    const runId = run?.run_id;
    if (run?.status !== 'COMPLETED' || !runId || !hasResults || lastAutoScrolledRunId.current === runId) return;
    lastAutoScrolledRunId.current = runId;
    const timer = window.setTimeout(scrollToResults, 150);
    return () => window.clearTimeout(timer);
  }, [run?.status, run?.run_id, hasResults]);

  const openResult = async (resultId: string) => {
    if (!evaluation) return;
    try { setSelectedResult((await api.result(evaluation.evaluation_id, resultId)).data); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not load result detail'); }
  };

  const saveReview = async (body: { action: string; final_state?: string; final_score?: number; rationale?: string }) => {
    if (!evaluation || !selectedResult) return;
    try {
      await api.review(evaluation.evaluation_id, selectedResult.evaluation_result_id, body);
      setSelectedResult((await api.result(evaluation.evaluation_id, selectedResult.evaluation_result_id)).data);
      setMatrix((await api.matrix(evaluation.evaluation_id)).data);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not save review'); }
  };

  const exportReport = async (format: 'MARKDOWN' | 'PDF') => {
    if (!evaluation) return;
    try {
      const started = await api.startExport(evaluation.evaluation_id, format);
      let report = (await api.getExport(evaluation.evaluation_id, started.data.export_id)).data;
      for (let attempt = 0; attempt < 15 && !report.content && !report.content_base64; attempt += 1) {
        await new Promise((resolve) => window.setTimeout(resolve, 1000));
        report = (await api.getExport(evaluation.evaluation_id, started.data.export_id)).data;
      }
      if (!report.content && !report.content_base64) throw new Error('Export is still processing; please try again shortly.');
      const blob = format === 'PDF' && report.content_base64 ? new Blob([Uint8Array.from(atob(report.content_base64), (character) => character.charCodeAt(0))], { type: 'application/pdf' }) : new Blob([report.content ?? ''], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `veribid-${evaluation.evaluation_id.toLowerCase()}.${format === 'PDF' ? 'pdf' : 'md'}`; link.click(); window.setTimeout(() => URL.revokeObjectURL(url), 0);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not generate export'); }
  };

  const vendorCount = useMemo(() => new Set(documents.map((item) => item.vendor_id).filter(Boolean)).size, [documents]);
  const runStatus = run?.status ?? (hasResults ? 'RESULTS_READY' : 'READY');
  const canUploadVendorFile = !role.startsWith('VENDOR_') || Boolean(vendorId.trim() && proposalId.trim());
  return (
    <div className="content workspace">
      <div className="workspace-nav">
        <button className="back" onClick={onBack}>← Back to overview</button>
        <button className="button-quiet" onClick={() => onSignOut?.()}>Sign out</button>
      </div>
      <div className="eyebrow">EVALUATION WORKSPACE · {userEmail}</div>
      <h1>Bring the evidence together.</h1>
      <p className="lede">Upload the buyer requirements and each vendor’s evidence. VeriBid links results to their sources; a person makes the final decision.</p>
      {!evaluation ? (
        <div className="workspace-card">
          <div className="upload-icon" aria-hidden="true">+</div>
          <h2>Start an evaluation workspace</h2>
          <label htmlFor="evaluation-name">Evaluation name</label>
          <input id="evaluation-name" name="evaluation-name" value={name} onChange={(event) => setName(event.target.value)} />
          <button className="button-primary" onClick={() => void create()} disabled={busy !== null}>{busy === 'create' ? 'Creating…' : 'Create evaluation'}</button>
          {error && <div className="form-error" role="alert">{error}</div>}
        </div>
      ) : (
        <>
          <div className="workspace-toolbar">
            <div>
              <span className="eyebrow">WORKSPACE</span>
              <strong>{evaluation.name}</strong>
              <small>{evaluation.evaluation_id} · {evaluation.status}</small>
            </div>
            <div className="toolbar-actions">
              <button className="button-quiet" onClick={() => void extract()} disabled={busy !== null || runIsActive || documents.length === 0}>{busy === 'extract' ? 'Extracting…' : 'Extract requirements'}</button>
              <button className="button-primary" onClick={() => void startRun()} disabled={busy !== null || runIsActive || requirements.length === 0}>{busy === 'run' ? 'Starting…' : runIsActive ? 'Evaluation running…' : 'Run evaluation'}</button>
            </div>
          </div>
          <div className="stats compact">
            <div><strong>{documents.length}</strong><span>documents</span></div>
            <div><strong>{requirements.length}</strong><span>requirements</span></div>
            <div><strong>{vendorCount}</strong><span>vendor scopes</span></div>
            <div><strong>{runStatus}</strong><span>run status</span></div>
          </div>
          <ol className="workflow-steps" aria-label="Evaluation steps">
            <li className={hasBuyerBrief ? 'step-done' : currentStep === 1 ? 'step-current' : ''} aria-current={currentStep === 1 ? 'step' : undefined}>
              <span>01</span><div><strong>Buyer brief</strong><small>Upload the RFP and rubric</small></div>
            </li>
            <li className={requirements.length ? 'step-done' : currentStep === 2 ? 'step-current' : ''} aria-current={currentStep === 2 ? 'step' : undefined}>
              <span>02</span><div><strong>Requirements</strong><small>Extract and check the criteria</small></div>
            </li>
            <li className={hasVendorEvidence ? 'step-done' : currentStep === 3 ? 'step-current' : ''} aria-current={currentStep === 3 ? 'step' : undefined}>
              <span>03</span><div><strong>Vendor evidence</strong><small>Scope each proposal and price file</small></div>
            </li>
            <li className={hasResults ? 'step-done' : currentStep === 4 ? 'step-current' : ''} aria-current={currentStep === 4 ? 'step' : undefined}>
              <span>04</span><div><strong>Results & review</strong><small>Inspect evidence before export</small></div>
            </li>
          </ol>
          {runIsActive && <div className="run-status-banner" role="status" aria-live="polite">
            <strong>Evaluation is running…</strong>
            <span>{run?.progress ? `${run.progress.completed_items} of ${run.progress.total_items} assessments completed${run.progress.failed_items ? ` · ${run.progress.failed_items} failed` : ''}.` : 'The evidence matrix will appear here when processing finishes.'}</span>
          </div>}
          {run?.status === 'COMPLETED' && <div className="run-result-banner" role="status" aria-live="polite">
            <div>
              <strong>Evaluation complete — your results are below.</strong>
              <span>{hasResults ? `${resultCells.length} assessment results · ${pendingReviewCount} need human review${conflictCount ? ` · ${conflictCount} with conflicting evidence` : ''}.` : 'Loading the evidence matrix…'}</span>
            </div>
            <button className="button-primary" onClick={scrollToResults} disabled={!hasResults}>View results ↓</button>
          </div>}
          {run?.status === 'PARTIALLY_COMPLETED' && <div className="run-status-banner run-warning" role="status" aria-live="polite">
            <strong>Run finished with some incomplete assessments.</strong>
            <span>Review the available results below and check the error details before continuing.</span>
            {hasResults && <button className="button-quiet" onClick={scrollToResults}>View available results ↓</button>}
          </div>}
          {run?.status === 'FAILED' && <div className="run-status-banner run-warning" role="alert">
            <strong>Evaluation could not finish.</strong>
            <span>Check the error shown in Pipeline checkpoints, fix the issue, and run it again.</span>
          </div>}
          <section className="workflow-grid">
            <div className="workspace-card left-card">
              <div className="eyebrow">01 · DIRECT UPLOAD</div>
              <h2>Add the evaluation files</h2>
              <p>Start with the buyer RFP and rubric. Then upload each vendor proposal and its matching pricing file.</p>
              <label htmlFor="document-role">This file is a</label>
              <select id="document-role" name="document-role" value={role} onChange={(event) => { setRole(event.target.value); setError(null); setUploadStatus(null); }}>
                <option>BUYER_RFP</option><option>BUYER_RUBRIC</option><option>BUYER_POLICY</option><option>VENDOR_PROPOSAL</option><option>VENDOR_PRICING</option><option>VENDOR_APPENDIX</option>
              </select>
              <p className="field-help" id="role-help">Choose the role that matches the file. Vendor ID and proposal ID keep every supplier’s evidence separate.</p>
              {role.startsWith('VENDOR_') && <>
                <label htmlFor="vendor-id">Vendor ID</label>
                <input id="vendor-id" name="vendor-id" autoComplete="off" spellCheck={false} placeholder="Example: VEN_CLOUD_A" value={vendorId} onChange={(event) => { setVendorId(event.target.value); setError(null); setUploadStatus(null); }} />
                <label htmlFor="proposal-id">Proposal ID</label>
                <input id="proposal-id" name="proposal-id" autoComplete="off" spellCheck={false} placeholder="Example: PROP_CLOUD_A" value={proposalId} onChange={(event) => { setProposalId(event.target.value); setError(null); setUploadStatus(null); }} />
                <p className={`field-help${canUploadVendorFile ? '' : ' field-warning'}`} id="scope-help">{canUploadVendorFile ? 'Use this same ID pair for the vendor’s proposal and pricing file.' : 'Enter both IDs to enable the file picker.'}</p>
              </>}
              <label className="file-label" htmlFor="evidence-file">Choose a file · upload starts when selected</label>
              <input id="evidence-file" name="evidence-file" type="file" accept=".pdf,.docx,.xlsx" aria-describedby={role.startsWith('VENDOR_') ? 'role-help scope-help' : 'role-help'} disabled={busy !== null || !canUploadVendorFile} onChange={(event) => { const file = event.currentTarget.files?.[0]; event.currentTarget.value = ''; if (file) void upload(file); }} />
              {uploadStatus && <div className="upload-status" role="status" aria-live="polite">{uploadStatus}</div>}
            </div>
            <div className="workspace-card left-card">
              <div className="eyebrow">02 · PROCESSING</div>
              <h2>What happens next</h2>
              <div className="checkpoint"><span className={documents.length ? 'checkpoint-dot done' : 'checkpoint-dot'} />Documents <small>{documents.length} uploaded</small></div>
              <div className="checkpoint"><span className={requirements.length ? 'checkpoint-dot done' : 'checkpoint-dot'} />Requirements <small>{requirements.length ? `${requirements.length} extracted` : 'Upload the RFP and rubric, then extract'}</small></div>
              <div className="checkpoint"><span className={hasResults ? 'checkpoint-dot done' : 'checkpoint-dot'} />Results <small>{hasResults ? 'Ready below for human review' : 'Run evaluation to create the evidence matrix'}</small></div>
              {error && <div className="form-error" role="alert">{error}</div>}
            </div>
          </section>
          {run?.status && run.status !== 'COMPLETED' && run.status !== 'PARTIALLY_COMPLETED' && run.status !== 'FAILED' && runIsActive && run.progress && <div className="progress-track" role="progressbar" aria-label="Evaluation progress" aria-valuemin={0} aria-valuemax={Math.max(1, run.progress.total_items)} aria-valuenow={run.progress.completed_items}>
            <span style={{ width: `${run.progress.total_items ? Math.min(100, Math.round((run.progress.completed_items / run.progress.total_items) * 100)) : 0}%` }} />
          </div>}
          {hasResults && matrix && <EvidenceMatrix sectionRef={resultsSectionRef} matrix={matrix} resultCount={resultCells.length} pendingReviewCount={pendingReviewCount} conflictCount={conflictCount} onOpenResult={(resultId) => void openResult(resultId)} onExport={(format) => void exportReport(format)} />}
          {requirements.length > 0 && !hasResults && <section className="results-placeholder matrix-card document-card" aria-labelledby="results-placeholder-title">
            <span className="eyebrow">RESULTS</span>
            <h2 id="results-placeholder-title">Your results will appear here</h2>
            <p>After the run completes, select <strong>View results</strong> to jump to the evidence matrix. Open any cell to check its source and record a human review.</p>
          </section>}
          {documents.length > 0 && <section className="matrix-card document-card">
            <div className="card-heading"><span>Document ledger</span><small>Private to this evaluation</small></div>
            <div className="matrix-scroll"><table>
              <thead><tr><th>File</th><th>Role</th><th>Scope</th><th>Status</th></tr></thead>
              <tbody>{documents.map((document) => <tr key={document.document_id}>
                <td>{document.file_name}</td><td>{document.document_role}</td><td>{document.vendor_id ? `${document.vendor_id} / ${document.proposal_id}` : 'Buyer scope'}</td><td><span className="status-chip">{document.ingestion_status}</span></td>
              </tr>)}</tbody>
            </table></div>
          </section>}
          {requirements.length > 0 && <section className="matrix-card document-card">
            <div className="card-heading"><span>Buyer requirements</span><small>Source locations included</small></div>
            <div className="matrix-scroll"><table>
              <thead><tr><th>Code</th><th>Requirement</th><th>Category</th><th>Source</th></tr></thead>
              <tbody>{requirements.map((requirement) => <tr key={requirement.requirement_id}>
                <td>{requirement.requirement_code}</td>
                <td>{requirement.title}<small className="cell-note">{requirement.description}</small></td>
                <td>{requirement.category}</td>
                <td>{requirement.source_pointer.document_name}{requirement.source_pointer.page_number ? ` · p.${requirement.source_pointer.page_number}` : requirement.source_pointer.sheet_name ? ` · ${requirement.source_pointer.sheet_name}` : ''}</td>
              </tr>)}</tbody>
            </table></div>
          </section>}
          {selectedResult && <ResultPanel result={selectedResult} onClose={() => setSelectedResult(null)} onReview={(body) => void saveReview(body)} />}
        </>
      )}
    </div>
  );
}

function EvidenceMatrix({ sectionRef, matrix, resultCount, pendingReviewCount, conflictCount, onOpenResult, onExport }: { sectionRef: RefObject<HTMLElement | null>; matrix: MatrixDto; resultCount: number; pendingReviewCount: number; conflictCount: number; onOpenResult: (resultId: string) => void; onExport: (format: 'MARKDOWN' | 'PDF') => void }) {
  const exportBlocked = pendingReviewCount > 0;
  return <section className="matrix-card document-card results-section" id="evaluation-results" ref={sectionRef} aria-labelledby="evaluation-results-title">
    <div className="results-heading">
      <div>
        <span className="eyebrow">RESULTS · HUMAN REVIEW REQUIRED</span>
        <h2 id="evaluation-results-title" tabIndex={-1}>Evidence matrix</h2>
        <p>{resultCount} assessment results across {matrix.rows.length} requirements and {matrix.vendors.length} vendor scopes. Select a cell to inspect its evidence and source location.</p>
      </div>
      <div className="matrix-actions">
        <button className="button-quiet small-button" onClick={() => onExport('MARKDOWN')} disabled={exportBlocked} title={exportBlocked ? 'Review every result before exporting.' : undefined}>Export Markdown</button>
        <button className="button-quiet small-button" onClick={() => onExport('PDF')} disabled={exportBlocked} title={exportBlocked ? 'Review every result before exporting.' : undefined}>Export PDF</button>
      </div>
    </div>
    <div className="result-summary" aria-label="Result summary">
      <div><strong>{resultCount}</strong><span>assessment results</span></div>
      <div><strong>{pendingReviewCount}</strong><span>need human review</span></div>
      <div><strong>{conflictCount}</strong><span>conflicts preserved</span></div>
    </div>
    {exportBlocked && <p className="export-help">Review each result first. Export unlocks after every result has an accepted or overridden decision.</p>}
    <div className="matrix-scroll">
      <table>
        <thead><tr><th>Requirement</th>{matrix.vendors.map((vendor) => <th key={vendor.vendor_id}>{vendor.display_name}</th>)}</tr></thead>
        <tbody>{matrix.rows.map((row) => <tr key={row.requirement.requirement_id}>
          <th><span>{row.requirement.category}</span>{row.requirement.title}<small className="cell-note">{row.requirement.requirement_code}</small></th>
          {matrix.vendors.map((vendor) => {
            const cell = row.results.find((item) => item.vendor_id === vendor.vendor_id);
            return <td key={vendor.vendor_id}>{cell
              ? <button className="matrix-cell" aria-label={`View ${row.requirement.requirement_code} result for ${vendor.display_name}: ${cell.final_state ?? cell.state}`} onClick={() => onOpenResult(cell.evaluation_result_id)}>
                  <StateBadge state={cell.final_state ?? cell.state} />
                  <small>{cell.review_status === 'PENDING' ? 'Needs human review' : cell.review_status === 'CONFIRMED' ? 'Reviewed' : 'Follow-up requested'} · {cell.specialist ?? 'specialist pending'}</small>
                  {cell.has_conflict && <em>Conflict preserved</em>}
                </button>
              : <StateBadge state="INSUFFICIENT_EVIDENCE" />}</td>;
          })}
        </tr>)}</tbody>
      </table>
    </div>
  </section>;
}

function pointerLabel(pointer: ResultDto['evidence_claims'][number]['source_pointer']) {
  const locations = [
    pointer.page_number ? `page ${pointer.page_number}` : null,
    pointer.section ? `section ${pointer.section}` : null,
    pointer.line_start ? `lines ${pointer.line_start}-${pointer.line_end ?? pointer.line_start}` : null,
    pointer.sheet_name ? `sheet ${pointer.sheet_name}` : null,
    pointer.row_start ? `rows ${pointer.row_start}-${pointer.row_end ?? pointer.row_start}` : null,
    pointer.chunk_id ? `chunk ${pointer.chunk_id}` : null,
  ].filter(Boolean).join(' · ') || 'source locator unavailable';
  return `${pointer.source_pointer_id} · ${pointer.document_name} (${pointer.document_type}) · ${locations}`;
}

function ResultPanel({ result, onClose, onReview, simulation = false }: { result: ResultDto; onClose: () => void; onReview: (body: { action: string; final_state?: string; final_score?: number; rationale?: string }) => void; simulation?: boolean }) {
  const [action, setAction] = useState('ACCEPT');
  const [finalState, setFinalState] = useState(result.state);
  const [score, setScore] = useState(String(result.suggested_score ?? 0));
  const [rationale, setRationale] = useState('');

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === 'Escape') onClose();
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [onClose]);

  const requiresDecision = action === 'OVERRIDE';
  const claims = new Map(result.evidence_claims.map((claim, index) => [claim.evidence_claim_id ?? `claim-${index}`, claim]));
  const finalReview = result.human_review?.action === 'OVERRIDE' ? `${result.human_review.final_state ?? 'state not supplied'} · score ${result.human_review.final_score ?? 'not supplied'}` : result.human_review?.action === 'ACCEPT' ? 'ACCEPT system suggestion' : result.human_review?.action ?? 'No human decision recorded';
  return <div className="result-overlay" role="dialog" aria-modal="true">
    <aside className="result-panel">
      <div className="panel-header">
        <div><div className="eyebrow">{simulation ? 'DEMO SIMULATION · LOCAL ONLY' : `RESULT DETAIL · ${result.specialist ?? 'SPECIALIST'}`}</div><h2>{result.vendor_id} / {result.proposal_id}</h2></div>
        <button className="button-quiet" onClick={onClose} aria-label="Close result detail">×</button>
      </div>
      <div className="decision-trace">
        <div><span>{simulation ? 'SAMPLE SCENARIO' : 'SYSTEM SUGGESTION'}</span><strong><StateBadge state={result.state} /> {result.suggested_score ?? '—'} / {result.max_score}</strong></div>
        <div><span>{simulation ? 'LOCAL DEMO REVIEW' : 'HUMAN DECISION'}</span><strong>{finalReview}</strong></div>
        {result.human_review?.rationale && <div><span>RATIONALE</span><strong>{result.human_review.rationale}</strong></div>}
      </div>
      <p className="result-rationale">{result.rationale}</p>
      {result.deterministic_result && <div className="evidence-block"><strong>Deterministic authority</strong><p>{result.deterministic_result.tool} · {result.deterministic_result.authoritative_state ?? 'calculated'}</p></div>}
      <div className="evidence-block">
        <strong>{simulation ? 'Synthetic fixture references (not real source documents)' : 'Source evidence'}</strong>
        {result.evidence_claims.length ? result.evidence_claims.map((claim, index) => <div className="claim" key={`${claim.source_pointer.source_pointer_id}-${index}`}><span>{claim.relation}</span><p>Evidence excerpt / claim: {claim.claim_text}</p><small>{pointerLabel(claim.source_pointer)}</small></div>) : <p>INSUFFICIENT_EVIDENCE — no resolvable source claim.</p>}
      </div>
      {result.conflict_pairs.length > 0 && <div className="conflict-box">
        <strong>{simulation ? 'Sample scenario conflict' : 'Conflict preserved'}</strong>
        <p>{result.conflict_pairs.length} conflict pair(s) {simulation ? 'are included for demonstration only.' : 'require reviewer attention.'}</p>
        {result.conflict_pairs.map((pair, index) => {
          const supporting = claims.get(pair.supporting_claim_id);
          const contradicting = claims.get(pair.contradicting_claim_id);
          return <div className="conflict-pair" key={`${pair.supporting_claim_id}-${pair.contradicting_claim_id}-${index}`}>
            <div><span>Supporting evidence</span><p>Evidence excerpt / claim: {supporting?.claim_text ?? `Claim ${pair.supporting_claim_id} is not present in this response.`}</p>{supporting && <small>{pointerLabel(supporting.source_pointer)}</small>}</div>
            <div><span>Contradicting evidence</span><p>Evidence excerpt / claim: {contradicting?.claim_text ?? `Claim ${pair.contradicting_claim_id} is not present in this response.`}</p>{contradicting && <small>{pointerLabel(contradicting.source_pointer)}</small>}</div>
            <small className="conflict-meta">{pair.conflict_type} · {pair.resolution_status}</small>
          </div>;
        })}
      </div>}
      <div className="review-box">
        <div className="eyebrow">{simulation ? 'SIMULATED HUMAN REVIEW · NOT SAVED' : 'HUMAN REVIEW'}</div>
        <select value={action} onChange={(event) => setAction(event.target.value)}><option value="ACCEPT">ACCEPT system suggestion</option><option value="OVERRIDE">OVERRIDE with rationale</option><option value="REQUEST_FOLLOWUP">REQUEST FOLLOW-UP</option></select>
        {requiresDecision && <><select value={finalState} onChange={(event) => setFinalState(event.target.value)}>{['SATISFIED', 'PARTIALLY_SATISFIED', 'NOT_SATISFIED', 'CONFLICTING_EVIDENCE', 'INSUFFICIENT_EVIDENCE'].map((state) => <option key={state}>{state}</option>)}</select><input type="number" min="0" value={score} onChange={(event) => setScore(event.target.value)} placeholder="Final score" /><textarea value={rationale} onChange={(event) => setRationale(event.target.value)} placeholder="Override rationale is required" /></>}
        <button className="button-primary" disabled={requiresDecision && !rationale.trim()} onClick={() => onReview({ action, ...(requiresDecision ? { final_state: finalState, final_score: Number(score), rationale } : {}) })}>{simulation ? 'Apply locally' : 'Record review'}</button>
        {simulation && <small>Demo changes are temporary and reset when you leave or refresh this page.</small>}
        {result.human_review && <small className="review-record">{simulation ? 'Demo review' : 'Latest review'}: {result.human_review.action} · {result.human_review.reviewed_at}</small>}
      </div>
    </aside>
  </div>;
}
