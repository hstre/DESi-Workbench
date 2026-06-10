"use client";

import type { Claim } from "@/lib/api";

interface Props {
  claim: Claim | null;
}

export default function ClaimDetail({ claim }: Props) {
  if (!claim) {
    return (
      <div className="panel">
        <h2>Claim detail</h2>
        <p className="muted">Select a claim to see its details.</p>
      </div>
    );
  }
  return (
    <div className="panel">
      <h2>Claim detail — {claim.id}</h2>
      <div className="kv">
        Category: <code>{claim.category}</code>
      </div>
      <div className="kv">
        Section: <code>{claim.section}</code>
      </div>
      <div className="kv">
        Supported: <code>{String(claim.supported)}</code> · Contains numbers:{" "}
        <code>{String(claim.has_numbers)}</code>
      </div>
      <div className="kv">
        Overclaim terms:{" "}
        <code>
          {claim.overclaim_terms.length > 0
            ? claim.overclaim_terms.join(", ")
            : "none"}
        </code>
      </div>
      <div className="kv">
        Method: <code>{claim.method ?? "—"}</code> · Identity:{" "}
        <code>{claim.content_hash ? claim.content_hash.slice(0, 12) : "—"}</code>
      </div>
      <p style={{ fontSize: 13 }}>{claim.text}</p>
    </div>
  );
}
