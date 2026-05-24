"use client";

import { useEffect, useState } from "react";
import {
  getHealth,
  postReview,
  type Health,
  type Review,
} from "@/lib/api";
import UploadBox from "@/components/UploadBox";
import ClaimList from "@/components/ClaimList";
import ClaimDetail from "@/components/ClaimDetail";
import GraphView from "@/components/GraphView";
import EvidenceGapPanel from "@/components/EvidenceGapPanel";
import ReplayPanel from "@/components/ReplayPanel";
import ReportPanel from "@/components/ReportPanel";

export default function Page() {
  const [health, setHealth] = useState<Health | null>(null);
  const [review, setReview] = useState<Review | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    getHealth()
      .then(setHealth)
      .catch(() => setHealth(null));
  }, []);

  async function handleSubmit(title: string, text: string) {
    setLoading(true);
    setError(null);
    try {
      const result = await postReview({ title: title || undefined, text });
      setReview(result);
      setSelectedId(result.claims[0]?.id ?? null);
    } catch (e) {
      setError(String(e));
      setReview(null);
    } finally {
      setLoading(false);
    }
  }

  const selectedClaim =
    review?.claims.find((c) => c.id === selectedId) ?? null;

  return (
    <>
      <header className="app">
        <h1>
          DESi Workbench <span className="muted">— epistemic audit assistant</span>
        </h1>
        <span className="verdict">REVIEW_ASSISTANCE_ONLY</span>
        <span className="health">
          {health ? (
            <>
              <span className="dot ok" />
              DESi online — {health.desi.library} {health.desi.version},
              core_identity={health.desi.core_identity}
            </>
          ) : (
            <>
              <span className="dot bad" />
              backend unavailable (start it on {process.env.NEXT_PUBLIC_API_BASE ?? "http://localhost:8000"})
            </>
          )}
        </span>
      </header>

      <div className="layout">
        <UploadBox onSubmit={handleSubmit} loading={loading} />

        <div className="area-center">
          {error && (
            <div className="panel">
              <p className="error">Error: {error}</p>
            </div>
          )}
          <ClaimList
            claims={review?.claims ?? []}
            selectedId={selectedId}
            onSelect={setSelectedId}
          />
          <ClaimDetail claim={selectedClaim} />
        </div>

        <div className="area-right">
          {review ? (
            <>
              <GraphView graph={review.graph} />
              <EvidenceGapPanel review={review} />
              <ReplayPanel replay={review.replay} verdict={review.verdict} />
            </>
          ) : (
            <div className="panel">
              <h2>Audit panels</h2>
              <p className="muted">
                Submit a paper to see the graph, risks, and replay trace.
              </p>
            </div>
          )}
        </div>

        {review && <ReportPanel reviewId={review.review_id} />}
      </div>
    </>
  );
}
