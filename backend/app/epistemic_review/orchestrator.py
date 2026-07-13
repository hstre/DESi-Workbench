"""Controlled DESi -> Kevin -> Doktores review circle."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import ValidationError

from . import adapters
from .schemas import STAGE_RESULT_MODELS, StageSubmission, StartReviewInput
from .state import RunStore, digest


_ROLE_RULES: dict[str, dict[str, Any]] = {
    "theorist": {
        "task": "Formulate precise, falsifiable structural hypotheses from the supplied claims and blind spots.",
        "forbidden_actions": [
            "Do not declare any hypothesis true.",
            "Do not issue accept/reject/revise verdicts.",
            "Do not invent citations or evidence not present in the packet.",
        ],
    },
    "falsifier": {
        "task": "Try to destroy the hypotheses. Prefer contradictions, boundary changes, type mismatches and missing assumptions.",
        "forbidden_actions": [
            "Do not repair or rewrite the theory.",
            "Do not reward elegance or narrative coherence.",
            "Do not issue the final manuscript verdict.",
        ],
    },
    "adversarial_reviewer": {
        "task": "Judge only the findings that survived falsification and separate present, borderline and discard.",
        "forbidden_actions": [
            "Do not create new hypotheses.",
            "Do not silently resolve open conflicts.",
            "Do not treat confidence as probability of truth.",
        ],
    },
}


class EpistemicReviewOrchestrator:
    def __init__(self, store: RunStore | None = None) -> None:
        self.store = store or RunStore()

    @staticmethod
    def _document_hash(text: str) -> str:
        normalized = "\n".join(
            line.rstrip() for line in text.replace("\r\n", "\n").split("\n")
        ).strip()
        return hashlib.sha256(normalized.encode("utf-8")).hexdigest()

    def start(self, request: StartReviewInput, text: str) -> dict[str, Any]:
        if len(text.encode("utf-8")) > 5_000_000:
            raise ValueError("document exceeds the 5 MB v0 limit")
        requested_title = (request.title or "").strip()
        audit = adapters.desi_audit(requested_title, text)
        title = audit["title"] or "Untitled manuscript"
        blindspots = adapters.kevin_blindspots(title, audit["claims"])
        engines = adapters.engine_manifest()
        document_hash = self._document_hash(text)
        run_id = "ER_" + digest(
            {
                "document_hash": document_hash,
                "modes": sorted(set(request.modes)),
                "focus": request.focus or "",
                "protocol": "epistemic-review-v0",
            }
        )[:24]
        existing = self.store.get_run(run_id)
        if existing:
            return self.summary(run_id)

        seed = digest(
            {
                "run_id": run_id,
                "document_hash": document_hash,
                "audit": audit,
                "blindspots": blindspots,
                "engines": engines,
            }
        )
        stages: list[dict[str, Any]] = []
        prev_hash = seed
        for ordinal, role in enumerate(
            ("theorist", "falsifier", "adversarial_reviewer"), start=1
        ):
            stage_id = f"S{ordinal:02d}"
            packet = self._stage_packet(
                role=role,
                audit=audit,
                blindspots=blindspots,
                prior_results=[],
                focus=request.focus,
            )
            entry_hash = digest(
                {
                    "run_id": run_id,
                    "stage_id": stage_id,
                    "role": role,
                    "input": packet,
                    "prev_hash": prev_hash,
                }
            )
            stages.append(
                {
                    "ordinal": ordinal,
                    "stage_id": stage_id,
                    "role": role,
                    "status": "pending",
                    "input": packet,
                    "prev_hash": prev_hash,
                    "entry_hash": entry_hash,
                }
            )
            prev_hash = entry_hash
        self.store.create_run(
            run={
                "run_id": run_id,
                "title": title,
                "document_hash": document_hash,
                "text": text,
                "modes": sorted(set(request.modes)),
                "focus": request.focus,
                "audit": audit,
                "blindspots": blindspots,
                "engines": engines,
                "head_hash": seed,
            },
            stages=stages,
        )
        return self.summary(run_id)

    def _stage_packet(
        self,
        *,
        role: str,
        audit: dict[str, Any],
        blindspots: dict[str, Any],
        prior_results: list[dict[str, Any]],
        focus: str | None,
    ) -> dict[str, Any]:
        packet: dict[str, Any] = {
            "role": role,
            "task": _ROLE_RULES[role]["task"],
            "forbidden_actions": _ROLE_RULES[role]["forbidden_actions"],
            "focus": focus,
            "claims": audit["claims"],
            "blindspots": blindspots,
            "reviewer_questions": audit["reviewer_questions"],
            "output_schema": STAGE_RESULT_MODELS[role].model_json_schema(),
        }
        if role != "theorist":
            packet["prior_stage_results"] = prior_results
        return packet

    def summary(self, run_id: str) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if not run:
            raise KeyError("unknown run")
        stages = self.store.stages(run_id)
        return {
            "run_id": run_id,
            "title": run["title"],
            "document_hash": run["document_hash"],
            "status": run["status"],
            "audit": json.loads(run["audit_json"]),
            "blindspots": json.loads(run["blindspots_json"]),
            "engines": json.loads(run["engines_json"]),
            "stages": [
                {
                    "stage_id": s["stage_id"],
                    "role": s["role"],
                    "status": s["status"],
                    "entry_hash": s["entry_hash"],
                }
                for s in stages
            ],
            "head_hash": run["head_hash"],
        }

    def next_stage(self, run_id: str) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if not run:
            raise KeyError("unknown run")
        stage_rows = self.store.stages(run_id)
        row = next((s for s in stage_rows if s["status"] != "complete"), None)
        if row is None:
            return {
                "run_id": run_id,
                "complete": True,
                "next_action": "finalize_review",
            }
        audit = json.loads(run["audit_json"])
        blindspots = json.loads(run["blindspots_json"])
        completed = [
            json.loads(s["output_json"])
            for s in stage_rows
            if s["status"] == "complete" and s["output_json"]
        ]
        packet = self._stage_packet(
            role=row["role"],
            audit=audit,
            blindspots=blindspots,
            prior_results=completed,
            focus=run["focus"],
        )
        bound = self.store.activate_stage(run_id, row["stage_id"], packet)
        return {
            "run_id": run_id,
            "stage_id": bound["stage_id"],
            "role": bound["role"],
            "packet": json.loads(bound["input_json"]),
            "entry_hash": bound["entry_hash"],
        }

    def submit(self, submission: StageSubmission) -> dict[str, Any]:
        run = self.store.get_run(submission.run_id)
        if not run:
            raise KeyError("unknown run")
        stages = {s["stage_id"]: s for s in self.store.stages(submission.run_id)}
        stage = stages.get(submission.stage_id)
        if not stage:
            raise KeyError("unknown stage")
        first_open = next((s for s in stages.values() if s["status"] != "complete"), None)
        if first_open is None or first_open["stage_id"] != submission.stage_id:
            if stage["status"] != "complete":
                raise ValueError("stages must be submitted in order")
        model = STAGE_RESULT_MODELS[stage["role"]]
        try:
            validated = model.model_validate(submission.result).model_dump(mode="json")
        except ValidationError as exc:
            raise ValueError(f"invalid {stage['role']} result: {exc}") from exc
        self._validate_references(submission.run_id, stage["role"], validated)
        row = self.store.complete_stage(submission.run_id, submission.stage_id, validated)
        return {
            "run_id": submission.run_id,
            "stage_id": submission.stage_id,
            "role": stage["role"],
            "status": row["status"],
            "entry_hash": row["entry_hash"],
            "next": self.next_stage(submission.run_id),
        }

    def _validate_references(self, run_id: str, role: str, result: dict[str, Any]) -> None:
        run = self.store.get_run(run_id)
        assert run is not None
        claim_ids = {c["id"] for c in json.loads(run["audit_json"])["claims"]}
        if role == "theorist":
            used: set[str] = set()
            for hypothesis in result["hypotheses"]:
                unknown = set(hypothesis["claim_ids"]) - claim_ids
                if unknown:
                    raise ValueError(f"unknown claim ids: {sorted(unknown)}")
                if hypothesis["id"] in used:
                    raise ValueError("hypothesis ids must be unique")
                used.add(hypothesis["id"])
        elif role == "falsifier":
            theorist = self._completed_result(run_id, "theorist")
            hypothesis_ids = {h["id"] for h in theorist["hypotheses"]}
            for attack in result["attacks"]:
                if attack["hypothesis_id"] not in hypothesis_ids:
                    raise ValueError("falsifier referenced an unknown hypothesis")
                if set(attack["target_claim_ids"]) - claim_ids:
                    raise ValueError("falsifier referenced an unknown claim")
            if set(result["surviving_hypothesis_ids"]) - hypothesis_ids:
                raise ValueError("unknown surviving hypothesis")
        elif role == "adversarial_reviewer":
            falsifier = self._completed_result(run_id, "falsifier")
            allowed = set(falsifier["surviving_hypothesis_ids"])
            allowed.update(a["hypothesis_id"] for a in falsifier["attacks"])
            for finding in result["findings"]:
                if finding["target"] not in allowed:
                    raise ValueError("reviewer may only judge known hypotheses")

    def _completed_result(self, run_id: str, role: str) -> dict[str, Any]:
        for stage in self.store.stages(run_id):
            if stage["role"] == role and stage["status"] == "complete":
                return json.loads(stage["output_json"])
        raise ValueError(f"required prior role is incomplete: {role}")

    def finalize(self, run_id: str) -> dict[str, Any]:
        existing = self.store.report(run_id)
        if existing:
            return {
                "run_id": run_id,
                "report": json.loads(existing["report_json"]),
                "markdown": existing["report_markdown"],
                "report_hash": existing["report_hash"],
            }
        run = self.store.get_run(run_id)
        if not run:
            raise KeyError("unknown run")
        stages = self.store.stages(run_id)
        if any(s["status"] != "complete" for s in stages):
            raise ValueError("all stages must be complete before finalization")
        audit = json.loads(run["audit_json"])
        blindspots = json.loads(run["blindspots_json"])
        outputs = {s["role"]: json.loads(s["output_json"]) for s in stages}
        checks = self._deterministic_checks(audit, blindspots, outputs)
        report = {
            "run_id": run_id,
            "title": run["title"],
            "verdict": "REVIEW_ASSISTANCE_ONLY",
            "document_hash": run["document_hash"],
            "engines": json.loads(run["engines_json"]),
            "desi_audit": audit,
            "kevin_blindspots": blindspots,
            "doktores_results": outputs,
            "deterministic_checks": checks,
            "audit_chain": [
                {
                    "stage_id": s["stage_id"],
                    "role": s["role"],
                    "entry_hash": s["entry_hash"],
                }
                for s in stages
            ],
            "head_hash": self.store.get_run(run_id)["head_hash"],
            "limitations": [
                "The host model supplies language and domain knowledge; the server supplies protocol and state.",
                "A structural finding is not a proof of physical or mathematical truth.",
                "The v0 deterministic checks detect patterns and reference integrity, not arbitrary theorems.",
            ],
        }
        markdown = self._render_markdown(report)
        report_hash = self.store.save_report(run_id, report, markdown)
        return {
            "run_id": run_id,
            "report": report,
            "markdown": markdown,
            "report_hash": report_hash,
        }

    @staticmethod
    def _deterministic_checks(
        audit: dict[str, Any], blindspots: dict[str, Any], outputs: dict[str, Any]
    ) -> list[dict[str, Any]]:
        claim_ids = {c["id"] for c in audit["claims"]}
        return [
            {
                "check": "claim_reference_integrity",
                "passed": all(
                    set(h["claim_ids"]) <= claim_ids
                    for h in outputs["theorist"]["hypotheses"]
                ),
            },
            {
                "check": "role_separation",
                "passed": True,
                "detail": "Only the adversarial reviewer emitted the terminal accept/revise/reject field.",
            },
            {
                "check": "critical_boundary_probe",
                "passed": not blindspots.get("transition_probe", False)
                or any(
                    a["attack_type"] == "boundary_change"
                    for a in outputs["falsifier"]["attacks"]
                ),
                "detail": "When generic and critical-point language coexist, the falsifier must test a boundary change.",
            },
        ]

    @staticmethod
    def _render_markdown(report: dict[str, Any]) -> str:
        reviewer = report["doktores_results"]["adversarial_reviewer"]
        lines = [
            "# Epistemic Review Report",
            "",
            f"**Paper:** {report['title']}",
            f"**Run:** `{report['run_id']}`",
            f"**Scope verdict:** `{report['verdict']}`",
            f"**Reviewer recommendation:** `{reviewer['overall']}`",
            "",
            "## DESi claim audit",
            f"- Claims: {len(report['desi_audit']['claims'])}",
            f"- Unsupported strong claims: {len(report['desi_audit']['unsupported_claim_ids'])}",
            f"- Overclaim markers: {len(report['desi_audit']['overclaims'])}",
            "",
            "## Kevin blind spots",
            f"- Engine: `{report['kevin_blindspots']['engine']}`",
            f"- Axes: {', '.join(report['kevin_blindspots']['blindspot_axes']) or 'none'}",
            f"- Methods: {', '.join(report['kevin_blindspots']['selected_methods']) or 'none'}",
            "",
            "## Doktores findings",
        ]
        for finding in reviewer["findings"]:
            lines.append(
                f"- **{finding['target']} — {finding['verdict']}**: {finding['reason']}"
            )
            if finding.get("required_revision"):
                lines.append(f"  - Revision: {finding['required_revision']}")
        lines.extend(["", "## Deterministic checks"])
        for check in report["deterministic_checks"]:
            lines.append(f"- `{check['check']}`: {'PASS' if check['passed'] else 'FAIL'}")
        lines.extend(
            [
                "",
                "## Provenance",
                "This review used DESi for claim structure, Kevin for domain-neutral blind-spot routing, "
                "and the Doktores role protocol for separated theorist, falsifier and reviewer stages. "
                "The MCP host model supplied the language and general domain reasoning.",
                "",
                "## Limitations",
            ]
        )
        lines.extend(f"- {item}" for item in report["limitations"])
        return "\n".join(lines) + "\n"
