import { describe, it, expect, vi, beforeEach } from "vitest";
import { render, screen, fireEvent, waitFor } from "@testing-library/react";
import Page from "@/app/page";
import type { Health, Review } from "@/lib/api";

const health: Health = {
  status: "ok",
  verdict: "REVIEW_ASSISTANCE_ONLY",
  pipeline_version: "workbench-mvp-0.1.0a0",
  desi: {
    library: "desi-governance",
    version: "0.1.0a0",
    core_identity: 1.0,
    audit_framing: "framing",
  },
};

const review: Review = {
  review_id: "abc123def4567890",
  title: "Sample",
  claims: [
    {
      id: "claim_1",
      category: "novelty_claim",
      section: "Abstract",
      text: "We present the first novel method that solves it.",
      has_numbers: false,
      overclaim_terms: ["first", "novel", "solves"],
      supported: false,
    },
  ],
  unsupported_claims: [],
  overclaims: [
    {
      id: "overclaim_1",
      claim_id: "claim_1",
      section: "Abstract",
      text: "...",
      terms: ["first"],
      reason: "Claims novelty without comparison.",
    },
  ],
  evidence_gaps: [
    { id: "gap_1", claim_id: "claim_1", section: "Abstract", note: "no support", missing: "inline_support" },
  ],
  reproducibility_risks: [{ id: "repro_1", risk_type: "missing_code", detail: "no code" }],
  reviewer_questions: ["A question?"],
  graph: {
    nodes: [
      { id: "paper", type: "paper", label: "Sample" },
      { id: "claim_1", type: "claim", label: "c" },
    ],
    edges: [{ source: "paper", target: "claim_1", type: "contains" }],
  },
  replay: {
    input_hash: "abc123def4567890",
    output_hash: "out",
    pipeline_version: "workbench-mvp-0.1.0a0",
    offline_mode: true,
    core_identity: 1.0,
    audit_framing: "framing",
    desi_library: "desi-governance",
    desi_version: "0.1.0a0",
    forbidden_term_hits: [],
  },
  verdict: "REVIEW_ASSISTANCE_ONLY",
};

beforeEach(() => {
  vi.stubGlobal(
    "fetch",
    vi.fn((url: string) => {
      const u = String(url);
      if (u.endsWith("/health"))
        return Promise.resolve({ ok: true, json: () => Promise.resolve(health) });
      if (u.endsWith("/api/review"))
        return Promise.resolve({ ok: true, json: () => Promise.resolve(review) });
      return Promise.resolve({ ok: true, text: () => Promise.resolve("# report") });
    }) as unknown as typeof fetch
  );
});

describe("DESi Workbench app", () => {
  it("renders the app shell", async () => {
    render(<Page />);
    expect(screen.getByText(/DESi Workbench/)).toBeInTheDocument();
    await waitFor(() => expect(screen.getByText(/DESi online/)).toBeInTheDocument());
  });

  it("submits sample text, shows claims and a report link", async () => {
    render(<Page />);
    fireEvent.click(screen.getByText("Load sample"));
    fireEvent.click(screen.getByText("Review"));
    // The claim text appears in both the list and the detail panel.
    await waitFor(() =>
      expect(
        screen.getAllByText(/We present the first novel method that solves it\./)
          .length
      ).toBeGreaterThan(0)
    );
    expect(screen.getByText("Download report.md")).toBeInTheDocument();
  });
});
