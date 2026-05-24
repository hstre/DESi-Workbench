"use client";

import type { Review } from "@/lib/api";

interface Props {
  review: Review;
}

export default function EvidenceGapPanel({ review }: Props) {
  return (
    <div className="panel">
      <h2>Risks &amp; gaps</h2>

      <h3 style={{ fontSize: 13, margin: "8px 0 4px" }}>
        Overclaim risks ({review.overclaims.length})
      </h3>
      {review.overclaims.length === 0 ? (
        <p className="muted">None detected.</p>
      ) : (
        <ul className="items">
          {review.overclaims.map((o) => (
            <li key={o.id}>
              <span className="tag warn">{o.terms.join(", ")}</span>
              <span className="muted">[{o.claim_id}]</span> {o.reason}
            </li>
          ))}
        </ul>
      )}

      <h3 style={{ fontSize: 13, margin: "12px 0 4px" }}>
        Evidence gaps ({review.evidence_gaps.length})
      </h3>
      {review.evidence_gaps.length === 0 ? (
        <p className="muted">None flagged.</p>
      ) : (
        <ul className="items">
          {review.evidence_gaps.map((g) => (
            <li key={g.id}>
              <span className="muted">[{g.claim_id}]</span> {g.note}
            </li>
          ))}
        </ul>
      )}

      <h3 style={{ fontSize: 13, margin: "12px 0 4px" }}>
        Reproducibility risks ({review.reproducibility_risks.length})
      </h3>
      {review.reproducibility_risks.length === 0 ? (
        <p className="muted">None flagged.</p>
      ) : (
        <ul className="items">
          {review.reproducibility_risks.map((r) => (
            <li key={r.id}>
              <span className="tag bad">{r.risk_type}</span> {r.detail}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
