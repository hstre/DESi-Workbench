"use client";

import type { Replay } from "@/lib/api";

interface Props {
  replay: Replay;
  verdict: string;
}

export default function ReplayPanel({ replay, verdict }: Props) {
  return (
    <div className="panel">
      <h2>Replay / audit trace</h2>
      <blockquote className="muted" style={{ margin: "0 0 8px", fontSize: 12 }}>
        {replay.audit_framing}
      </blockquote>
      <div className="kv">
        Verdict: <code>{verdict}</code>
      </div>
      <div className="kv">
        Input hash: <code>{replay.input_hash}</code>
      </div>
      <div className="kv">
        Output hash: <code>{replay.output_hash}</code>
      </div>
      <div className="kv">
        Pipeline: <code>{replay.pipeline_version}</code>
      </div>
      <div className="kv">
        Offline mode: <code>{String(replay.offline_mode)}</code>
      </div>
      <div className="kv">
        DESi: <code>{replay.desi_library}</code> {replay.desi_version} ·
        core_identity <code>{replay.core_identity}</code>
      </div>
      <div className="kv">
        DESi hype/forbidden-term hits:{" "}
        <code>
          {replay.forbidden_term_hits.length > 0
            ? replay.forbidden_term_hits.join(", ")
            : "none"}
        </code>
      </div>
    </div>
  );
}
