export type HealthDto = {
  data: { service: string; version: string; status: string; timestamp: string };
};

export type DemoDto = {
  data: {
    evaluation_id: string;
    title: string;
    status: string;
    requirements: Array<{ id: string; text: string; category: string }>;
    vendors: Array<{ vendor_id: string; name: string }>;
    matrix: Array<{ requirement_id: string; vendor_id: string; state: string; confidence: number; source_pointers: Array<{ document_id: string; page?: number; locator: string }>; conflict_pairs?: Array<{ left: string; right: string }> }>;
  };
};

export type EvaluationDto = { evaluation_id: string; name: string; status: string; created_at: string };
export type UploadInitDto = { document_id: string; ingestion_status: string; upload: { method: 'PUT'; url: string; expires_at: string; required_headers: { 'Content-Type': string } } };
export type DocumentDto = { document_id: string; file_name: string; media_type: string; document_role: string; vendor_id?: string; proposal_id?: string; ingestion_status: string; created_at: string };
export type SourcePointerDto = { source_pointer_id: string; document_id: string; document_name: string; document_type: string; page_number?: number; section?: string; line_start?: number; line_end?: number; sheet_name?: string; row_start?: number; row_end?: number; chunk_id?: string; content_hash?: string; resolvable: boolean };
export type RequirementDto = { requirement_id: string; requirement_code: string; title: string; description: string; category: string; mandatory: boolean; is_disqualifying: boolean; weight: number; evaluation_type: string; threshold?: number; source_pointer: SourcePointerDto };
export type RunDto = { run_id?: string; job_id?: string; status: string; progress?: { total_items: number; completed_items: number; failed_items: number }; telemetry?: Record<string, number | null> };
export type MatrixCellDto = { vendor_id: string; evaluation_result_id: string; state: string; suggested_score?: number; final_state?: string | null; final_score?: number | null; review_status: string; specialist?: string; has_conflict: boolean };
export type MatrixDto = { vendors: Array<{ vendor_id: string; display_name: string }>; rows: Array<{ requirement: Pick<RequirementDto, 'requirement_id' | 'requirement_code' | 'title' | 'category' | 'mandatory' | 'is_disqualifying' | 'weight'>; results: MatrixCellDto[] }> };
export type ResultDto = { evaluation_result_id: string; requirement_id: string; vendor_id: string; proposal_id: string; state: string; suggested_score?: number; max_score: number; rationale: string; specialist?: string; evidence_claims: Array<{ claim_text: string; relation: string; confidence: number; source_pointer: SourcePointerDto }>; conflict_pairs: Array<{ supporting_claim_id: string; contradicting_claim_id: string; conflict_type: string; resolution_status: string }>; deterministic_result?: { tool: string; passed?: boolean; authoritative_state?: string; result?: Record<string, unknown> }; human_review?: ReviewDto | null; audit_events?: Array<Record<string, unknown>> };
export type ReviewDto = { human_review_id: string; evaluation_result_id: string; action: string; system_state: string; system_score?: number; final_state?: string; final_score?: number; rationale?: string; reviewer_sub: string; reviewed_at: string };
export type ExportDto = { export_id: string; status: string; report_version: number; generated_at: string; format: string; content?: string; content_base64?: string };

const baseUrl = (import.meta.env.VITE_API_BASE_URL as string | undefined)?.replace(/\/$/, '') ?? '';

async function request<T>(path: string, init?: RequestInit, authenticated = false): Promise<T> {
  let authorization: Record<string, string> = {};
  if (authenticated) {
    const { fetchAuthSession } = await import('aws-amplify/auth');
    const session = await fetchAuthSession();
    const token = session.tokens?.accessToken?.toString();
    if (token) authorization = { authorization: `Bearer ${token}` };
  }
  const response = await fetch(`${baseUrl}${path}`, {
    ...init,
    headers: { accept: 'application/json', ...authorization, ...(init?.headers ?? {}) },
  });
  const payload = await response.json().catch(() => ({}));
  if (!response.ok) throw new Error(payload?.error?.message ?? `API request failed (${response.status})`);
  return payload as T;
}

const authRequest = <T>(path: string, init?: RequestInit) => request<T>(path, init, true);

export const api = {
  health: () => request<HealthDto>('/api/v1/health'),
  demo: () => request<DemoDto>('/api/v1/demo'),
  createEvaluation: (name: string) => authRequest<{ data: EvaluationDto }>('/api/v1/evaluations', { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': crypto.randomUUID() }, body: JSON.stringify({ name }) }),
  getEvaluation: (evaluationId: string) => authRequest<{ data: EvaluationDto }>(`/api/v1/evaluations/${evaluationId}`),
  listDocuments: (evaluationId: string) => authRequest<{ data: DocumentDto[] }>(`/api/v1/evaluations/${evaluationId}/documents`),
  initializeDocument: (evaluationId: string, file: File, documentRole: string, vendorId?: string, proposalId?: string) => authRequest<{ data: UploadInitDto }>(`/api/v1/evaluations/${evaluationId}/documents`, { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': crypto.randomUUID() }, body: JSON.stringify({ file_name: file.name, media_type: file.type, document_role: documentRole, vendor_id: vendorId || undefined, proposal_id: proposalId || undefined }) }),
  completeDocument: (evaluationId: string, documentId: string) => authRequest<{ data: { document_id: string; ingestion_status: string; job_id: string } }>(`/api/v1/evaluations/${evaluationId}/documents/${documentId}/complete-upload`, { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': crypto.randomUUID() }, body: '{}' }),
  extractRequirements: (evaluationId: string) => authRequest<{ data: { job_id: string; status: string } }>(`/api/v1/evaluations/${evaluationId}/requirements/extract`, { method: 'POST', headers: { 'idempotency-key': crypto.randomUUID() }, body: '{}' }),
  listRequirements: (evaluationId: string) => authRequest<{ data: RequirementDto[] }>(`/api/v1/evaluations/${evaluationId}/requirements`),
  startRun: (evaluationId: string, vendorIds: string[] = []) => authRequest<{ data: { run_id: string; status: string } }>(`/api/v1/evaluations/${evaluationId}/runs`, { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': crypto.randomUUID() }, body: JSON.stringify({ vendor_ids: vendorIds }) }),
  getRun: (evaluationId: string, runId: string) => authRequest<{ data: RunDto }>(`/api/v1/evaluations/${evaluationId}/runs/${runId}`),
  matrix: (evaluationId: string) => authRequest<{ data: MatrixDto }>(`/api/v1/evaluations/${evaluationId}/matrix`),
  result: (evaluationId: string, resultId: string) => authRequest<{ data: ResultDto }>(`/api/v1/evaluations/${evaluationId}/results/${resultId}`),
  review: (evaluationId: string, resultId: string, body: { action: string; final_state?: string; final_score?: number; rationale?: string }) => authRequest<{ data: ReviewDto }>(`/api/v1/evaluations/${evaluationId}/results/${resultId}/reviews`, { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': crypto.randomUUID() }, body: JSON.stringify(body) }),
  startExport: (evaluationId: string, format: 'MARKDOWN' | 'PDF') => authRequest<{ data: { export_id: string; status: string } }>(`/api/v1/evaluations/${evaluationId}/exports`, { method: 'POST', headers: { 'content-type': 'application/json', 'idempotency-key': crypto.randomUUID() }, body: JSON.stringify({ format }) }),
  getExport: (evaluationId: string, exportId: string) => authRequest<{ data: ExportDto }>(`/api/v1/evaluations/${evaluationId}/exports/${exportId}`),
};
