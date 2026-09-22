import { useEffect, useState } from 'react';
import { Authenticator } from '@aws-amplify/ui-react';
import { api, DemoDto, HealthDto } from './api';

type Page = 'home' | 'demo' | 'app';

function pageFromLocation(): Page {
  if (window.location.pathname === '/demo') return 'demo';
  if (window.location.pathname === '/app') return 'app';
  return 'home';
}

export function App() {
  const [page, setPage] = useState<Page>(pageFromLocation);
  const [health, setHealth] = useState<HealthDto | null>(null);
  const [demo, setDemo] = useState<DemoDto | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    api.health().then(setHealth).catch(() => setError('API health is not reachable yet.'));
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

  return (
    <div className="shell">
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
    </div>
  );
}

function Landing({ health, onDemo, onApp }: { health: HealthDto | null; onDemo: () => void; onApp: () => void }) {
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

function StateBadge({ state, confidence }: { state: string; confidence: number }) {
  const className = state === 'SATISFIED' ? 'satisfied' : state === 'CONFLICTING_EVIDENCE' ? 'conflict' : state === 'NOT_SATISFIED' ? 'not' : 'insufficient';
  return <div className={`state ${className}`}><strong>{state.replaceAll('_', ' ')}</strong><small>{Math.round(confidence * 100)}% confidence</small></div>;
}

function Workspace({ onBack }: { onBack: () => void }) {
  return <Authenticator loginMechanisms={['email']}>
    {({ user, signOut }) => <AuthenticatedWorkspace userEmail={user?.signInDetails?.loginId ?? 'authenticated user'} onBack={onBack} onSignOut={signOut} />}
  </Authenticator>;
}

function AuthenticatedWorkspace({ userEmail, onBack, onSignOut }: { userEmail: string; onBack: () => void; onSignOut?: () => void }) {
  const [name, setName] = useState('Cloud platform procurement');
  const [evaluationId, setEvaluationId] = useState<string | null>(null);
  const [uploadStatus, setUploadStatus] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  const create = async () => {
    setError(null);
    try { const result = await api.createEvaluation(name); setEvaluationId(result.data.evaluation_id); }
    catch (reason) { setError(reason instanceof Error ? reason.message : 'Could not create evaluation'); }
  };
  const upload = async (file: File) => {
    if (!evaluationId) return;
    setError(null); setUploadStatus('Preparing a verified upload…');
    try {
      const initialized = await api.initializeDocument(evaluationId, file);
      const uploadResponse = await fetch(initialized.data.upload.url, { method: 'PUT', headers: initialized.data.upload.required_headers, body: file });
      if (!uploadResponse.ok) throw new Error(`S3 upload failed (${uploadResponse.status})`);
      const completed = await api.completeDocument(evaluationId, initialized.data.document_id);
      setUploadStatus(`Verified and queued: ${completed.data.job_id}`);
    } catch (reason) { setError(reason instanceof Error ? reason.message : 'Upload failed'); setUploadStatus(null); }
  };
  return <main className="content workspace"><div className="workspace-nav"><button className="back" onClick={onBack}>← Back to overview</button><button className="button-quiet" onClick={() => onSignOut?.()}>Sign out</button></div><div className="eyebrow">EVALUATION WORKSPACE · {userEmail}</div><h1>Bring the evidence together.</h1><p className="lede">Create a private evaluation workspace. Documents stay isolated by evaluation, vendor, proposal, and authenticated owner.</p><div className="workspace-card"><div className="upload-icon">↑</div><h2>Start with a buyer RFP</h2><p>PDF, DOCX, or XLSX. The object is verified before ingestion begins.</p>{!evaluationId ? <><label htmlFor="evaluation-name">Evaluation name</label><input id="evaluation-name" value={name} onChange={(event) => setName(event.target.value)} /><button className="button-primary" onClick={create}>Create evaluation</button></> : <><div className="created" role="status">Workspace <strong>{evaluationId}</strong></div><label className="file-label" htmlFor="buyer-file">Choose RFP</label><input id="buyer-file" type="file" accept=".pdf,.docx,.xlsx" onChange={(event) => { const file = event.target.files?.[0]; if (file) void upload(file); }} />{uploadStatus && <div className="upload-status" role="status">{uploadStatus}</div>}</>}{error && <div className="form-error" role="alert">{error}</div>}</div></main>;
}
