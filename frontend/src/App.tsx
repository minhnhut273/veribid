import { useEffect, useMemo, useState } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { api, DemoDto, DocumentDto, EvaluationDto, MatrixDto, RequirementDto, ResultDto, RunDto } from './api';

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
    api.health().then(setHealth).catch(() => setError('API health is not reachable yet.'));
    const onPopState = () => setPage(pageFromLocation());
    window.addEventListener('popstate', onPopState);
    return () => window.removeEventListener('popstate', onPopState);
  }, []);

  useEffect(() => {
    if (page === 'demo') api.demo().then(setDemo).catch(() => setError('Demo data is not reachable yet.'));
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
    {page === 'app' && <Workspace onBack={() => navigate('home')} />}
    {error && <div className="toast" role="status">{error}</div>}
    <footer><span>Evidence first. Decisions remain human.</span><span>API {health?.data.status ?? 'checking'}</span></footer>
  </div>;
}

function Landing({ health, onDemo, onApp }: { health: { data: { status: string } } | null; onDemo: () => void; onApp: () => void }) {
  return <main>
    <section className="hero">
      <div className="eyebrow">EVIDENCE-DRIVEN BID EVALUATION</div>
      <h1>Turn vendor claims into <em>defensible</em> decisions.</h1>
      <p className="lede">VeriBid connects every assessment to source evidence, separates deterministic scoring from semantic reasoning, and keeps final judgment with your review team.</p>
      <div className="hero-actions"><button className="button-primary" onClick={onDemo}>Explore the public demo <span>↗</span></button><button className="button-quiet" onClick={onApp}>Start an evaluation</button></div>
      <div className="health-pill"><span className={health?.data.status === 'ok' ? 'dot live' : 'dot'} /> {health?.data.status === 'ok' ? 'API connected' : 'Connecting to API'} </div>
    </section>
    <section className="feature-grid">
      <Feature number="01" title="Grounded by evidence" text="Every visible claim points back to a document, page, section, or cell. No unsupported confidence theater." />
      <Feature number="02" title="Deterministic where it matters" text="Thresholds, totals, SLAs, TCO, and weighted scores run in code—not in a language model." />
      <Feature number="03" title="Human-owned outcome" text="Reviewers accept or override a suggestion with rationale. The original suggestion and audit trail remain intact." />
    </section>
  </main>;
}

function Feature({ number, title, text }: { number: string; title: string; text: string }) {
  return <article className="feature"><span className="feature-number">{number}</span><h2>{title}</h2><p>{text}</p></article>;
}

function Demo({ demo, onBack }: { demo: DemoDto | null; onBack: () => void }) {
  return <main className="content"><button className="back" onClick={onBack}>← Back to overview</button><div className="eyebrow">READ-ONLY PUBLIC DEMO</div><h1>{demo?.data.title ?? 'A transparent evaluation, end to end.'}</h1><p className="lede">Synthetic fixture data, intentionally read-only. Inspect the evidence-grounded matrix before signing in.</p>{demo ? <>
    <div className="stats"><div><strong>{demo.data.requirements.length}</strong><span>requirements</span></div><div><strong>{demo.data.vendors.length}</strong><span>vendors</span></div><div><strong>{demo.data.status}</strong><span>evaluation state</span></div></div>
    <div className="matrix-card"><div className="card-heading"><span>Evidence matrix</span><small>System suggestion · read-only</small></div><table><thead><tr><th>Requirement</th>{demo.data.vendors.map((vendor) => <th key={vendor.vendor_id}>{vendor.name}</th>)}</tr></thead><tbody>{demo.data.requirements.map((req) => <tr key={req.id}><th><span>{req.category}</span>{req.text}</th>{demo.data.vendors.map((vendor) => { const cell = demo.data.matrix.find((item) => item.requirement_id === req.id && item.vendor_id === vendor.vendor_id); return <td key={vendor.vendor_id}><StateBadge state={cell?.state ?? 'INSUFFICIENT_EVIDENCE'} confidence={cell?.confidence ?? 0} /></td>; })}</tr>)}</tbody></table></div>
  </> : <div className="loading-card">Loading the public fixture…</div>}</main>;
}

function StateBadge({ state, confidence }: { state: string; confidence?: number }) {
  const className = state === 'SATISFIED' ? 'satisfied' : state === 'CONFLICTING_EVIDENCE' ? 'conflict' : state === 'NOT_SATISFIED' ? 'not' : state === 'PARTIALLY_SATISFIED' ? 'partial' : 'insufficient';
  return <div className={`state ${className}`}><strong>{state.replaceAll('_', ' ')}</strong>{confidence !== undefined && <small>{Math.round(confidence * 100)}% confidence</small>}</div>;
}

function Workspace({ onBack }: { onBack: () => void }) {
  return <Authenticator loginMechanisms={['email']}>
    {({ user, signOut }) => <AuthenticatedWorkspace userEmail={user?.signInDetails?.loginId ?? 'authenticated user'} onBack={onBack} onSignOut={signOut} />}
  </Authenticator>;
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
  const [vendorId, setVendorId] = useState('VENDOR_A');
  const [proposalId, setProposalId] = useState('PROPOSAL_A');
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [busy, setBusy] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);

  const refresh = async (evaluationId: string) => {
    const [evaluationResponse, documentResponse, requirementResponse] = await Promise.all([
      api.getEvaluation(evaluationId), api.listDocuments(evaluationId), api.listRequirements(evaluationId),
    ]);
    setEvaluation(evaluationResponse.data);
    setDocuments(documentResponse.data);
    setRequirements(requirementResponse.data);
    if (requirementResponse.data.length) {
      try { setMatrix((await api.matrix(evaluationId)).data); } catch { /* results may not exist yet */ }
    }
  };

  const create = async () => {
    setError(null); setBusy('create');
    try { const result = await api.createEvaluation(name); setEvaluation(result.data); await refresh(result.data.evaluation_id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not create evaluation'); }
    finally { setBusy(null); }
  };

  const upload = async (file: File) => {
    if (!evaluation) return;
    const mediaType = file.type || (file.name.endsWith('.pdf') ? 'application/pdf' : file.name.endsWith('.docx') ? 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' : 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet');
    setError(null); setUploadStatus('Preparing a verified upload…'); setBusy('upload');
    try {
      const initialized = await api.initializeDocument(evaluation.evaluation_id, new File([file], file.name, { type: mediaType }), role, role.startsWith('VENDOR_') ? vendorId : undefined, role.startsWith('VENDOR_') ? proposalId : undefined);
      const uploadResponse = await fetch(initialized.data.upload.url, { method: 'PUT', headers: initialized.data.upload.required_headers, body: file });
      if (!uploadResponse.ok) throw new Error(`S3 upload failed (${uploadResponse.status})`);
      const completed = await api.completeDocument(evaluation.evaluation_id, initialized.data.document_id);
      setUploadStatus(`Verified and queued: ${completed.data.job_id}`);
      await refresh(evaluation.evaluation_id);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Upload failed'); setUploadStatus(null); }
    finally { setBusy(null); }
  };

  const extract = async () => {
    if (!evaluation) return;
    setBusy('extract'); setError(null);
    try { await api.extractRequirements(evaluation.evaluation_id); setUploadStatus('Requirement extraction queued. Refreshing shortly…'); window.setTimeout(() => void refresh(evaluation.evaluation_id), 2500); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not extract requirements'); }
    finally { setBusy(null); }
  };

  const startRun = async () => {
    if (!evaluation) return;
    setBusy('run'); setError(null);
    try {
      const started = await api.startRun(evaluation.evaluation_id, Array.from(new Set(documents.map((item) => item.vendor_id).filter((value): value is string => Boolean(value)))));
      setRun({ run_id: started.data.run_id, status: started.data.status });
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not start evaluation'); }
    finally { setBusy(null); }
  };

  useEffect(() => {
    if (!evaluation || !run?.run_id || ['COMPLETED', 'FAILED', 'PARTIALLY_COMPLETED'].includes(run.status)) return;
    const timer = window.setInterval(async () => {
      try {
        const next = (await api.getRun(evaluation.evaluation_id, run.run_id!)).data;
        setRun(next);
        if (['COMPLETED', 'FAILED', 'PARTIALLY_COMPLETED'].includes(next.status)) {
          const matrixResponse = await api.matrix(evaluation.evaluation_id);
          setMatrix(matrixResponse.data);
        }
      } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not read evaluation progress'); }
    }, 2000);
    return () => window.clearInterval(timer);
  }, [evaluation, run?.run_id, run?.status]);

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
      const report = (await api.getExport(evaluation.evaluation_id, started.data.export_id)).data;
      const blob = format === 'PDF' && report.content_base64 ? new Blob([Uint8Array.from(atob(report.content_base64), (character) => character.charCodeAt(0))], { type: 'application/pdf' }) : new Blob([report.content ?? ''], { type: 'text/markdown' });
      const url = URL.createObjectURL(blob); const link = document.createElement('a'); link.href = url; link.download = `veribid-${evaluation.evaluation_id.toLowerCase()}.${format === 'PDF' ? 'pdf' : 'md'}`; link.click(); URL.revokeObjectURL(url);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not generate export'); }
  };

  const vendorCount = useMemo(() => new Set(documents.map((item) => item.vendor_id).filter(Boolean)).size, [documents]);
  return <main className="content workspace">
    <div className="workspace-nav"><button className="back" onClick={onBack}>← Back to overview</button><button className="button-quiet" onClick={() => onSignOut?.()}>Sign out</button></div>
    <div className="eyebrow">EVALUATION WORKSPACE · {userEmail}</div><h1>Bring the evidence together.</h1><p className="lede">Create a private evaluation workspace, upload buyer and vendor evidence, then review every result before exporting.</p>
    {!evaluation ? <div className="workspace-card"><div className="upload-icon">+</div><h2>Start an evaluation workspace</h2><label htmlFor="evaluation-name">Evaluation name</label><input id="evaluation-name" value={name} onChange={(event) => setName(event.target.value)} /><button className="button-primary" onClick={() => void create()} disabled={busy !== null}>Create evaluation</button>{error && <div className="form-error" role="alert">{error}</div>}</div> : <>
      <div className="workspace-toolbar"><div><span className="eyebrow">WORKSPACE</span><strong>{evaluation.name}</strong><small>{evaluation.evaluation_id} · {evaluation.status}</small></div><div className="toolbar-actions"><button className="button-quiet" onClick={() => void extract()} disabled={busy !== null || documents.length === 0}>Extract requirements</button><button className="button-primary" onClick={() => void startRun()} disabled={busy !== null || requirements.length === 0}>Run evaluation</button></div></div>
      <div className="stats compact"><div><strong>{documents.length}</strong><span>documents</span></div><div><strong>{requirements.length}</strong><span>requirements</span></div><div><strong>{vendorCount}</strong><span>vendor scopes</span></div><div><strong>{run?.status ?? 'READY'}</strong><span>run status</span></div></div>
      <section className="workflow-grid"><div className="workspace-card left-card"><div className="eyebrow">01 · DIRECT UPLOAD</div><h2>Add scoped evidence</h2><p>Each vendor proposal is isolated by vendor and proposal ID before ingestion.</p><label htmlFor="document-role">Document role</label><select id="document-role" value={role} onChange={(event) => setRole(event.target.value)}><option>BUYER_RFP</option><option>BUYER_RUBRIC</option><option>BUYER_POLICY</option><option>VENDOR_PROPOSAL</option><option>VENDOR_PRICING</option><option>VENDOR_APPENDIX</option></select>{role.startsWith('VENDOR_') && <><label htmlFor="vendor-id">Vendor ID</label><input id="vendor-id" value={vendorId} onChange={(event) => setVendorId(event.target.value)} /><label htmlFor="proposal-id">Proposal ID</label><input id="proposal-id" value={proposalId} onChange={(event) => setProposalId(event.target.value)} /></>}<label className="file-label" htmlFor="evidence-file">Choose PDF, DOCX, or XLSX</label><input id="evidence-file" type="file" accept=".pdf,.docx,.xlsx" disabled={busy !== null} onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); }} />{uploadStatus && <div className="upload-status" role="status">{uploadStatus}</div>}</div><div className="workspace-card left-card"><div className="eyebrow">02 · PROCESSING</div><h2>Pipeline checkpoints</h2><div className="checkpoint"><span className={documents.length ? 'checkpoint-dot done' : 'checkpoint-dot'} />Documents verified <small>{documents.length} uploaded</small></div><div className="checkpoint"><span className={requirements.length ? 'checkpoint-dot done' : 'checkpoint-dot'} />Requirements extracted <small>{requirements.length ? `${requirements.length} typed requirements` : 'Awaiting buyer evidence'}</small></div><div className="checkpoint"><span className={matrix ? 'checkpoint-dot done' : 'checkpoint-dot'} />Evidence matrix <small>{matrix ? 'Ready for human review' : 'Run evaluation to populate'}</small></div>{error && <div className="form-error" role="alert">{error}</div>}</div></section>
      {documents.length > 0 && <section className="matrix-card document-card"><div className="card-heading"><span>Document ledger</span><small>private · owner scoped</small></div><table><thead><tr><th>File</th><th>Role</th><th>Scope</th><th>Status</th></tr></thead><tbody>{documents.map((document) => <tr key={document.document_id}><td>{document.file_name}</td><td>{document.document_role}</td><td>{document.vendor_id ? `${document.vendor_id} / ${document.proposal_id}` : 'Buyer scope'}</td><td><span className="status-chip">{document.ingestion_status}</span></td></tr>)}</tbody></table></section>}
      {requirements.length > 0 && <section className="matrix-card document-card"><div className="card-heading"><span>Typed requirements</span><small>SourcePointer attached</small></div><table><thead><tr><th>Code</th><th>Requirement</th><th>Category</th><th>Source</th></tr></thead><tbody>{requirements.map((requirement) => <tr key={requirement.requirement_id}><td>{requirement.requirement_code}</td><td>{requirement.title}<small className="cell-note">{requirement.description}</small></td><td>{requirement.category}</td><td>{requirement.source_pointer.document_name}{requirement.source_pointer.page_number ? ` · p.${requirement.source_pointer.page_number}` : requirement.source_pointer.sheet_name ? ` · ${requirement.source_pointer.sheet_name}` : ''}</td></tr>)}</tbody></table></section>}
      {matrix && <EvidenceMatrix matrix={matrix} onOpenResult={(resultId) => void openResult(resultId)} onExport={(format) => void exportReport(format)} />}
      {selectedResult && <ResultPanel result={selectedResult} onClose={() => setSelectedResult(null)} onReview={(body) => void saveReview(body)} />}
    </>}
  </main>;
}

function EvidenceMatrix({ matrix, onOpenResult, onExport }: { matrix: MatrixDto; onOpenResult: (resultId: string) => void; onExport: (format: 'MARKDOWN' | 'PDF') => void }) {
  return <section className="matrix-card document-card"><div className="card-heading"><span>Evidence matrix</span><div><button className="button-quiet small-button" onClick={() => onExport('MARKDOWN')}>Markdown</button><button className="button-quiet small-button" onClick={() => onExport('PDF')}>PDF</button></div></div><div className="matrix-scroll"><table><thead><tr><th>Requirement</th>{matrix.vendors.map((vendor) => <th key={vendor.vendor_id}>{vendor.display_name}</th>)}</tr></thead><tbody>{matrix.rows.map((row) => <tr key={row.requirement.requirement_id}><th><span>{row.requirement.category}</span>{row.requirement.title}<small className="cell-note">{row.requirement.requirement_code}</small></th>{matrix.vendors.map((vendor) => { const cell = row.results.find((item) => item.vendor_id === vendor.vendor_id); return <td key={vendor.vendor_id}>{cell ? <button className="matrix-cell" onClick={() => onOpenResult(cell.evaluation_result_id)}><StateBadge state={cell.final_state ?? cell.state} /><small>{cell.review_status} · {cell.specialist ?? 'specialist pending'}</small>{cell.has_conflict && <em>conflict preserved</em>}</button> : <StateBadge state="INSUFFICIENT_EVIDENCE" />}</td>; })}</tr>)}</tbody></table></div></section>;
}

function ResultPanel({ result, onClose, onReview }: { result: ResultDto; onClose: () => void; onReview: (body: { action: string; final_state?: string; final_score?: number; rationale?: string }) => void }) {
  const [action, setAction] = useState('ACCEPT');
  const [finalState, setFinalState] = useState(result.state);
  const [score, setScore] = useState(String(result.suggested_score ?? 0));
  const [rationale, setRationale] = useState('');
  const requiresDecision = action === 'OVERRIDE';
  return <div className="result-overlay" role="dialog" aria-modal="true"><aside className="result-panel"><div className="panel-header"><div><div className="eyebrow">RESULT DETAIL · {result.specialist ?? 'SPECIALIST'}</div><h2>{result.vendor_id} / {result.proposal_id}</h2></div><button className="button-quiet" onClick={onClose} aria-label="Close result detail">×</button></div><StateBadge state={result.state} /><p className="result-rationale">{result.rationale}</p>{result.deterministic_result && <div className="evidence-block"><strong>Deterministic authority</strong><p>{result.deterministic_result.tool} · {result.deterministic_result.authoritative_state ?? 'calculated'}</p></div>}<div className="evidence-block"><strong>Source evidence</strong>{result.evidence_claims.length ? result.evidence_claims.map((claim, index) => <div className="claim" key={`${claim.source_pointer.source_pointer_id}-${index}`}><span>{claim.relation}</span><p>{claim.claim_text}</p><small>{claim.source_pointer.document_name}{claim.source_pointer.page_number ? ` · page ${claim.source_pointer.page_number}` : claim.source_pointer.sheet_name ? ` · ${claim.source_pointer.sheet_name}` : ''}</small></div>) : <p>INSUFFICIENT_EVIDENCE — no resolvable source claim.</p>}</div>{result.conflict_pairs.length > 0 && <div className="conflict-box"><strong>Conflict preserved</strong><p>{result.conflict_pairs.length} conflict pair(s) require reviewer attention.</p></div>}<div className="review-box"><div className="eyebrow">HUMAN REVIEW</div><select value={action} onChange={(event) => setAction(event.target.value)}><option value="ACCEPT">ACCEPT system suggestion</option><option value="OVERRIDE">OVERRIDE with rationale</option><option value="REQUEST_FOLLOWUP">REQUEST FOLLOW-UP</option></select>{requiresDecision && <><select value={finalState} onChange={(event) => setFinalState(event.target.value)}>{['SATISFIED', 'PARTIALLY_SATISFIED', 'NOT_SATISFIED', 'CONFLICTING_EVIDENCE', 'INSUFFICIENT_EVIDENCE'].map((state) => <option key={state}>{state}</option>)}</select><input type="number" min="0" value={score} onChange={(event) => setScore(event.target.value)} placeholder="Final score" /><textarea value={rationale} onChange={(event) => setRationale(event.target.value)} placeholder="Override rationale is required" /> </>}<button className="button-primary" disabled={requiresDecision && !rationale.trim()} onClick={() => onReview({ action, ...(requiresDecision ? { final_state: finalState, final_score: Number(score), rationale } : {}) })}>Record review</button>{result.human_review && <small className="review-record">Latest review: {result.human_review.action} · {result.human_review.reviewed_at}</small>}</div></aside></div>;
}
