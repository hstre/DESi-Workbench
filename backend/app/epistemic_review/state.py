"""SQLite-backed append-only state for MCP review runs."""
from __future__ import annotations

import hashlib
import json
import os
import sqlite3
from pathlib import Path
from typing import Any


def canonical_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value: Any) -> str:
    return hashlib.sha256(canonical_json(value).encode("utf-8")).hexdigest()


class RunStore:
    """Small bounded store; stage rows are immutable after completion."""

    def __init__(self, path: str | Path | None = None) -> None:
        configured = path or os.getenv("DESI_MCP_DB", "data/epistemic_review.sqlite3")
        self.path = Path(configured)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _init(self) -> None:
        with self._connect() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    run_id TEXT PRIMARY KEY,
                    title TEXT NOT NULL,
                    document_hash TEXT NOT NULL,
                    text TEXT NOT NULL,
                    modes_json TEXT NOT NULL,
                    focus TEXT,
                    audit_json TEXT NOT NULL,
                    blindspots_json TEXT NOT NULL,
                    engines_json TEXT NOT NULL,
                    status TEXT NOT NULL,
                    head_hash TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS stages (
                    run_id TEXT NOT NULL,
                    ordinal INTEGER NOT NULL,
                    stage_id TEXT NOT NULL,
                    role TEXT NOT NULL,
                    status TEXT NOT NULL,
                    input_json TEXT NOT NULL,
                    output_json TEXT,
                    prev_hash TEXT NOT NULL,
                    entry_hash TEXT NOT NULL,
                    PRIMARY KEY (run_id, stage_id),
                    UNIQUE (run_id, ordinal),
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                CREATE TABLE IF NOT EXISTS reports (
                    run_id TEXT PRIMARY KEY,
                    report_json TEXT NOT NULL,
                    report_markdown TEXT NOT NULL,
                    report_hash TEXT NOT NULL,
                    FOREIGN KEY (run_id) REFERENCES runs(run_id)
                );
                """
            )

    def get_run(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM runs WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None

    def create_run(
        self,
        *,
        run: dict[str, Any],
        stages: list[dict[str, Any]],
    ) -> None:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                "SELECT run_id FROM runs WHERE run_id=?", (run["run_id"],)
            ).fetchone()
            if existing:
                return
            conn.execute(
                """INSERT INTO runs
                (run_id,title,document_hash,text,modes_json,focus,audit_json,
                 blindspots_json,engines_json,status,head_hash)
                VALUES (?,?,?,?,?,?,?,?,?,?,?)""",
                (
                    run["run_id"], run["title"], run["document_hash"], run["text"],
                    canonical_json(run["modes"]), run.get("focus"),
                    canonical_json(run["audit"]), canonical_json(run["blindspots"]),
                    canonical_json(run["engines"]), "active", run["head_hash"],
                ),
            )
            for stage in stages:
                conn.execute(
                    """INSERT INTO stages
                    (run_id,ordinal,stage_id,role,status,input_json,output_json,
                     prev_hash,entry_hash) VALUES (?,?,?,?,?,?,?,?,?)""",
                    (
                        run["run_id"], stage["ordinal"], stage["stage_id"],
                        stage["role"], stage["status"], canonical_json(stage["input"]),
                        None, stage["prev_hash"], stage["entry_hash"],
                    ),
                )

    def stages(self, run_id: str) -> list[dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT * FROM stages WHERE run_id=? ORDER BY ordinal", (run_id,)
            ).fetchall()
        return [dict(row) for row in rows]

    def next_stage(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute(
                """SELECT * FROM stages WHERE run_id=? AND status!='complete'
                   ORDER BY ordinal LIMIT 1""",
                (run_id,),
            ).fetchone()
            if not row:
                return None
            if row["status"] == "pending":
                conn.execute(
                    "UPDATE stages SET status='active' WHERE run_id=? AND stage_id=?",
                    (run_id, row["stage_id"]),
                )
                row = conn.execute(
                    "SELECT * FROM stages WHERE run_id=? AND stage_id=?",
                    (run_id, row["stage_id"]),
                ).fetchone()
        return dict(row) if row else None

    def activate_stage(
        self, run_id: str, stage_id: str, packet: dict[str, Any]
    ) -> dict[str, Any]:
        """Bind the exact role packet before the stage is exposed to the host model."""
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM stages WHERE run_id=? AND stage_id=?",
                (run_id, stage_id),
            ).fetchone()
            if not row:
                raise KeyError("unknown stage")
            if row["status"] == "complete":
                return dict(row)
            if row["status"] == "pending":
                entry_hash = digest(
                    {
                        "run_id": run_id,
                        "stage_id": stage_id,
                        "role": row["role"],
                        "input": packet,
                        "prev_hash": row["prev_hash"],
                    }
                )
                conn.execute(
                    """UPDATE stages SET status='active', input_json=?, entry_hash=?
                       WHERE run_id=? AND stage_id=?""",
                    (canonical_json(packet), entry_hash, run_id, stage_id),
                )
            updated = conn.execute(
                "SELECT * FROM stages WHERE run_id=? AND stage_id=?",
                (run_id, stage_id),
            ).fetchone()
        return dict(updated)

    def complete_stage(
        self, run_id: str, stage_id: str, result: dict[str, Any]
    ) -> dict[str, Any]:
        with self._connect() as conn:
            conn.execute("BEGIN IMMEDIATE")
            row = conn.execute(
                "SELECT * FROM stages WHERE run_id=? AND stage_id=?",
                (run_id, stage_id),
            ).fetchone()
            if not row:
                raise KeyError("unknown stage")
            if row["status"] == "complete":
                stored = json.loads(row["output_json"])
                if stored != result:
                    raise ValueError("completed stages are immutable")
                return dict(row)
            first_open = conn.execute(
                """SELECT stage_id FROM stages WHERE run_id=? AND status!='complete'
                   ORDER BY ordinal LIMIT 1""",
                (run_id,),
            ).fetchone()
            if not first_open or first_open["stage_id"] != stage_id:
                raise ValueError("stages must be submitted in order")
            prev_hash = row["prev_hash"]
            entry_hash = digest(
                {
                    "run_id": run_id,
                    "stage_id": stage_id,
                    "role": row["role"],
                    "input": json.loads(row["input_json"]),
                    "output": result,
                    "prev_hash": prev_hash,
                }
            )
            conn.execute(
                """UPDATE stages SET status='complete', output_json=?, entry_hash=?
                   WHERE run_id=? AND stage_id=?""",
                (canonical_json(result), entry_hash, run_id, stage_id),
            )
            conn.execute("UPDATE runs SET head_hash=? WHERE run_id=?", (entry_hash, run_id))
            next_row = conn.execute(
                """SELECT stage_id FROM stages WHERE run_id=? AND status='pending'
                   ORDER BY ordinal LIMIT 1""",
                (run_id,),
            ).fetchone()
            if next_row:
                conn.execute(
                    "UPDATE stages SET prev_hash=? WHERE run_id=? AND stage_id=?",
                    (entry_hash, run_id, next_row["stage_id"]),
                )
            else:
                conn.execute("UPDATE runs SET status='ready' WHERE run_id=?", (run_id,))
            updated = conn.execute(
                "SELECT * FROM stages WHERE run_id=? AND stage_id=?", (run_id, stage_id)
            ).fetchone()
        return dict(updated)

    def save_report(self, run_id: str, report: dict[str, Any], markdown: str) -> str:
        report_hash = digest(report)
        with self._connect() as conn:
            conn.execute(
                """INSERT INTO reports(run_id,report_json,report_markdown,report_hash)
                   VALUES(?,?,?,?) ON CONFLICT(run_id) DO NOTHING""",
                (run_id, canonical_json(report), markdown, report_hash),
            )
            conn.execute("UPDATE runs SET status='complete' WHERE run_id=?", (run_id,))
        return report_hash

    def report(self, run_id: str) -> dict[str, Any] | None:
        with self._connect() as conn:
            row = conn.execute("SELECT * FROM reports WHERE run_id=?", (run_id,)).fetchone()
        return dict(row) if row else None
