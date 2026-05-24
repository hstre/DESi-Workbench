"use client";

import type { Claim } from "@/lib/api";

interface Props {
  claims: Claim[];
  selectedId: string | null;
  onSelect: (id: string) => void;
}

export default function ClaimList({ claims, selectedId, onSelect }: Props) {
  return (
    <div className="panel">
      <h2>Claims ({claims.length})</h2>
      {claims.length === 0 ? (
        <p className="muted">No claims yet. Submit a paper to begin.</p>
      ) : (
        <div>
          {claims.map((c) => (
            <div
              key={c.id}
              className={"claim" + (c.id === selectedId ? " selected" : "")}
              onClick={() => onSelect(c.id)}
            >
              <div className="meta">
                <span className="tag">{c.category}</span>
                {c.overclaim_terms.length > 0 && (
                  <span className="tag warn">overclaim</span>
                )}
                {!c.supported && <span className="tag bad">unsupported</span>}
                <span>
                  {c.id} · {c.section}
                </span>
              </div>
              <div className="snippet">{c.text}</div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}
