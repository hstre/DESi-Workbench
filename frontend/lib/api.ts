// Typed client for the DESi Workbench backend.

export const API_BASE =
  process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000";

export interface Claim {
  id: string;
  category: string;
  section: string;
  text: string;
  has_numbers: boolean;
  overclaim_terms: string[];
  supported: boolean;
  // Provenance + stable identity (SPL content/method discipline).
  method?: string;
  content_hash?: string;
}

export interface SplClaim {
  id: string;
  content: string;
  method: string;
}

export interface Overclaim {
  id: string;
  claim_id: string;
  section: string;
  text: string;
  terms: string[];
  reason: string;
}

export interface EvidenceGap {
  id: string;
  claim_id: string;
  section: string;
  note: string;
  missing: string;
}

export interface ReproRisk {
  id: string;
  risk_type: string;
  detail: string;
}

export interface GraphNode {
  id: string;
  type: string;
  label: string;
}

export interface GraphEdge {
  source: string;
  target: string;
  type: string;
}

export interface Graph {
  nodes: GraphNode[];
  edges: GraphEdge[];
}

export interface Replay {
  input_hash: string;
  output_hash: string;
  pipeline_version: string;
  offline_mode: boolean;
  core_identity: number;
  audit_framing: string;
  desi_library: string;
  desi_version: string;
  forbidden_term_hits: string[];
}

export interface Review {
  review_id: string;
  title: string;
  claims: Claim[];
  unsupported_claims: Claim[];
  overclaims: Overclaim[];
  evidence_gaps: EvidenceGap[];
  reproducibility_risks: ReproRisk[];
  reviewer_questions: string[];
  graph: Graph;
  replay: Replay;
  verdict: string;
  // Real DESi SPL projection — present only in live mode (opt-in).
  spl_claims?: SplClaim[];
}

export interface Health {
  status: string;
  verdict: string;
  pipeline_version: string;
  desi: {
    library: string;
    version: string;
    core_identity: number;
    audit_framing: string;
  };
}

async function asJson<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let detail = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? detail;
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status}: ${detail}`);
  }
  return (await res.json()) as T;
}

export async function getHealth(): Promise<Health> {
  return asJson<Health>(await fetch(`${API_BASE}/health`));
}

export async function postReview(input: {
  title?: string;
  text: string;
}): Promise<Review> {
  const res = await fetch(`${API_BASE}/api/review`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...input, mode: "offline" }),
  });
  return asJson<Review>(res);
}

export function reportUrl(reviewId: string): string {
  return `${API_BASE}/api/review/${reviewId}/report.md`;
}
