"use client";

import { useMemo } from "react";
import type { Graph } from "@/lib/api";

interface Props {
  graph: Graph;
}

const COLORS: Record<string, string> = {
  paper: "#5b9dff",
  claim: "#c7d2e6",
  overclaim_risk: "#f0b429",
  evidence_gap: "#ff6b6b",
  reproducibility_risk: "#e2a3ff",
};

const COLUMN_X: Record<string, number> = {
  paper: 60,
  claim: 240,
  overclaim_risk: 440,
  evidence_gap: 440,
  reproducibility_risk: 440,
};

const ROW_H = 26;
const TOP = 24;
const WIDTH = 520;

function truncate(s: string, n: number): string {
  return s.length <= n ? s : s.slice(0, n - 1) + "…";
}

export default function GraphView({ graph }: Props) {
  const { positions, height } = useMemo(() => {
    const columns: Record<string, string[]> = {
      paper: [],
      claim: [],
      risk: [],
    };
    for (const node of graph.nodes) {
      if (node.type === "paper") columns.paper.push(node.id);
      else if (node.type === "claim") columns.claim.push(node.id);
      else columns.risk.push(node.id);
    }
    const pos: Record<string, { x: number; y: number }> = {};
    for (const node of graph.nodes) {
      const col =
        node.type === "paper"
          ? "paper"
          : node.type === "claim"
          ? "claim"
          : "risk";
      const idx = columns[col].indexOf(node.id);
      pos[node.id] = {
        x: COLUMN_X[node.type] ?? 440,
        y: TOP + idx * ROW_H,
      };
    }
    const maxCount = Math.max(
      1,
      columns.paper.length,
      columns.claim.length,
      columns.risk.length
    );
    return { positions: pos, height: TOP * 2 + maxCount * ROW_H };
  }, [graph]);

  if (graph.nodes.length === 0) {
    return (
      <div className="panel">
        <h2>Claim graph</h2>
        <p className="muted">No graph yet.</p>
      </div>
    );
  }

  return (
    <div className="panel">
      <h2>Claim graph</h2>
      <svg className="graph" viewBox={`0 0 ${WIDTH} ${height}`} role="img" aria-label="claim graph">
        {graph.edges.map((e, i) => {
          const s = positions[e.source];
          const t = positions[e.target];
          if (!s || !t) return null;
          return (
            <line
              key={i}
              x1={s.x}
              y1={s.y}
              x2={t.x}
              y2={t.y}
              stroke="#39414f"
              strokeWidth={1}
            />
          );
        })}
        {graph.nodes.map((n) => {
          const p = positions[n.id];
          if (!p) return null;
          const color = COLORS[n.type] ?? "#c7d2e6";
          const label =
            n.type === "claim" ? n.id : truncate(n.label, 22);
          return (
            <g key={n.id}>
              <title>{`${n.type}: ${n.label}`}</title>
              <circle cx={p.x} cy={p.y} r={6} fill={color} />
              <text
                x={p.x + 10}
                y={p.y + 3}
                fontSize={10}
                fill="#9aa3b2"
              >
                {label}
              </text>
            </g>
          );
        })}
      </svg>
      <p className="muted" style={{ fontSize: 11 }}>
        {graph.nodes.length} nodes · {graph.edges.length} edges · hover a node
        for its label
      </p>
    </div>
  );
}
