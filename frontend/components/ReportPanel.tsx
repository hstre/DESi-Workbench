"use client";

import { useState } from "react";
import { reportUrl } from "@/lib/api";

interface Props {
  reviewId: string;
}

export default function ReportPanel({ reviewId }: Props) {
  const [report, setReport] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const url = reportUrl(reviewId);

  async function fetchReport() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(url);
      if (!res.ok) throw new Error(`${res.status}`);
      setReport(await res.text());
    } catch (e) {
      setError(String(e));
    } finally {
      setLoading(false);
    }
  }

  return (
    <div className="panel area-bottom">
      <h2>Report export</h2>
      <div className="row" style={{ marginTop: 0 }}>
        <button onClick={fetchReport} disabled={loading}>
          {loading ? "Loading..." : "Preview report"}
        </button>
        <a
          className="report-link"
          href={url}
          target="_blank"
          rel="noreferrer"
          download={`review_${reviewId.slice(0, 12)}.md`}
        >
          Download report.md
        </a>
      </div>
      {error && <p className="error">Could not load report: {error}</p>}
      {report && <pre className="report">{report}</pre>}
    </div>
  );
}
