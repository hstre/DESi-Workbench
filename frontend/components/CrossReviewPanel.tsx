"use client";

import type { Review } from "@/lib/api";

export default function CrossReviewPanel({ review }: { review: Review }) {
  const matches = review.cross_review ?? [];
  return (
    <div className="panel">
      <h2>
        Cross-review similarity <span className="muted">(Layer 9)</span>
      </h2>
      {matches.length === 0 ? (
        <p className="muted">
          No claim here matches a prior review in the shared ledger.
        </p>
      ) : (
        <ul>
          {matches.map((m, i) => (
            <li key={i} style={{ fontSize: 13 }}>
              <code>{m.claim_id}</code> — {m.match_type}
              {m.match_type === "lexical" ? ` (${m.score})` : ""} of prior{" "}
              <code>
                {m.prior_review_id.slice(0, 8)}/{m.prior_claim_id}
              </code>
              : <span className="muted">{m.prior_text}</span>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
