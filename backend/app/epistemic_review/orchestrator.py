"""Controlled DESi -> Kevin -> seven-role Doktores review circle."""
from __future__ import annotations

import hashlib
import json
from typing import Any

from pydantic import ValidationError

from . import adapters
from .schemas import STAGE_ORDER, STAGE_RESULT_MODELS, StageSubmission, StartReviewInput
from .state import RunStore, digest


PROTOCOL_VERSION = "epistemic-review-v1"

_ROLE_RULES: dict[str, dict[str, Any]] = {
    "theorist": {
        "task": "Formulate precise, falsifiable structural hypotheses from the supplied claims and Kevin blind spots.",
        "forbidden_actions": [
            "Do not declare any hypothesis true.",
            "Do not issue accept/reject/revise verdicts.",
            "Do not invent citations or evidence not present in the packet.",
        ],
    },
    "literature_scout": {
        "task": "Map related work, competing explanations, known counterexamples, datasets and evidence relevant to each hypothesis.",
        "forbidden_actions": [
            "Do not fabricate bibliographic references.",
            "Use source_type='unknown' and a null reference when no verifiable source is available.",
            "Do not decide whether a hypothesis survives.",
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
    "experimental_designer": {
        "task": "Design the smallest reproducible tests that could discriminate the surviving hypotheses from baselines.",
        "forbidden_actions": [
            "Do not report invented experimental results.",
            "Do not choose metrics that merely restate a hypothesis.",
            "Do not hide unresolved feasibility constraints.",
        ],
    },
    "method_reviewer": {
        "task": "Audit each proposed experiment for baselines, confounding, measurement error, stopping rules and reproducibility.",
        "forbidden_actions": [
            "Do not create new hypotheses.",
            "Do not rewrite an unsound design silently; list required controls instead.",
            "Do not express confidence as a probability of truth.",
        ],
    },
    "paper_builder": {
        "task": "Build a publication artifact only from the traceable hypotheses, evidence, experiments and method assessments already supplied.",
        "forbidden_actions": [
            "Do not add new evidence, results or citations.",
            "Do not conceal rejected hypotheses or methodological limitations.",
            "Do not issue the final accept/revise/reject verdict.",
        ],
    },
    "adversarial_reviewer": {
        "task": "Judge the complete package like a hard external reviewer and separate present, borderline and discard.",
        "forbidden_actions": [
            "Do not create new hypotheses.",
            "Do not silently resolve open conflicts.",
            "Do not treat confidence as probability of truth.",
        ],
    },
}

_VISIBLE_PRIOR_ROLES: dict[str, tuple[str, ...]] = {
    "theorist": (),
    "literature_scout": ("theorist",),
    "falsifier": ("theorist", "literature_scout"),
    "experimental_designer": ("theorist", "literature_scout", "falsifier"),
    "method_reviewer": ("falsifier", "experimental_designer"),
    "paper_builder": (
        "theorist",
        "literature_scout",
        "falsifier",
        "experimental_designer",
        "method_reviewer",
    ),
    "adversarial_reviewer": (
        "theorist",
        "literature_scout",
        "falsifier",
        "experimental_designer",
        "method_reviewer",
        "paper_builder",
    ),
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
            raise ValueError("document exceeds the 5 MB limit")
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
                "protocol": PROTOCOL_VERSION,
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
                "protocol": PROTOCOL_VERSION,
            }
        )
        stages: list[dict[str, Any]] = []
        prev_hash = seed
        for ordinal, role in enumerate(STAGE_ORDER, start=1):
            stage_id = f"S{ordinal:02d}"
            packet = self._stage_packet(
                role=role,
                audit=audit,
                blindspots=blindspots,
                prior_results={},
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
        prior_results: dict[str, dict[str, Any]],
        focus: str | None,
    ) -> dict[str, Any]:
        visible = {
            prior_role: prior_results[prior_role]
            for prior_role in _VISIBLE_PRIOR_ROLES[role]
            if prior_role in prior_results
        }
        packet: dict[str, Any] = {
            "protocol_version": PROTOCOL_VERSION,
            "role": role,
            "role_position": STAGE_ORDER.index(role) + 1,
            "role_count": len(STAGE_ORDER),
            "task": _ROLE_RULES[role]["task"],
            "forbidden_actions": _ROLE_RULES[role]["forbidden_actions"],
            "focus": focus,
            "claims": audit["claims"],
            "blindspots": blindspots,
            "reviewer_questions": audit["reviewer_questions"],
            "prior_stage_results": visible,
            "output_schema": STAGE_RESULT_MODELS[role].model_json_schema(),
        }
        return packet

    def summary(self, run_id: str) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if not run:
            raise KeyError("unknown run")
        stages = self.store.stages(run_id)
        return {
            "run_id": run_id,
            "protocol_version": PROTOCOL_VERSION,
            "title": run["title"],
            "document_hash": run["document_hash"],
            "status": run["status"],
            "audit": json.loads(run["audit_json"]),
            "blindspots": json.loads(run["blindspots_json"]),
            "engines": json.loads(run["engines_json"]),
            "stages": [
                {
                    "stage_id": stage["stage_id"],
                    "role": stage["role"],
                    "status": stage["status"],
                    "entry_hash": stage["entry_hash"],
                }
                for stage in stages
            ],
            "head_hash": run["head_hash"],
        }

    def next_stage(self, run_id: str) -> dict[str, Any]:
        run = self.store.get_run(run_id)
        if not run:
            raise KeyError("unknown run")
        stage_rows = self.store.stages(run_id)
        row = next((stage for stage in stage_rows if stage["status"] != "complete"), None)
        if row is None:
            return {
                "run_id": run_id,
                "complete": True,
                "next_action": "finalize_review",
            }
        audit = json.loads(run["audit_json"])
        blindspots = json.loads(run["blindspots_json"])
        completed = {
            stage["role"]: json.loads(stage["output_json"])
            for stage in stage_rows
            if stage["status"] == "complete" and stage["output_json"]
        }
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
        ordered_stages = self.store.stages(submission.run_id)
        stages = {stage["stage_id"]: stage for stage in ordered_stages}
        stage = stages.get(submission.stage_id)
        if not stage:
            raise KeyError("unknown stage")
        first_open = next(
            (candidate for candidate in ordered_stages if candidate["status"] != "complete"),
            None,
        )
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
        claim_ids = {claim["id"] for claim in json.loads(run["audit_json"])["claims"]}

        if role == "theorist":
            used: set[str] = set()
            for hypothesis in result["hypotheses"]:
                unknown = set(hypothesis["claim_ids"]) - claim_ids
                if unknown:
                    raise ValueError(f"unknown claim ids: {sorted(unknown)}")
                if hypothesis["id"] in used:
                    raise ValueError("hypothesis ids must be unique")
                used.add(hypothesis["id"])
            return

        theorist = self._completed_result(run_id, "theorist")
        hypothesis_ids = {hypothesis["id"] for hypothesis in theorist["hypotheses"]}

        if role == "literature_scout":
            for evidence in result["evidence"]:
                unknown = set(evidence["target_hypothesis_ids"]) - hypothesis_ids
                if unknown:
                    raise ValueError(
                        f"literature scout referenced unknown hypotheses: {sorted(unknown)}"
                    )
                if evidence["source_type"] in {"citation", "dataset", "counterexample"} and not evidence.get("reference"):
                    raise ValueError("verifiable literature evidence requires a reference")
            return

        if role == "falsifier":
            for attack in result["attacks"]:
                if attack["hypothesis_id"] not in hypothesis_ids:
                    raise ValueError("falsifier referenced an unknown hypothesis")
                if set(attack["target_claim_ids"]) - claim_ids:
                    raise ValueError("falsifier referenced an unknown claim")
            if set(result["surviving_hypothesis_ids"]) - hypothesis_ids:
                raise ValueError("unknown surviving hypothesis")
            return

        falsifier = self._completed_result(run_id, "falsifier")
        surviving_ids = set(falsifier["surviving_hypothesis_ids"])

        if role == "experimental_designer":
            used_experiments: set[str] = set()
            for experiment in result["experiments"]:
                if experiment["id"] in used_experiments:
                    raise ValueError("experiment ids must be unique")
                used_experiments.add(experiment["id"])
                unknown = set(experiment["target_hypothesis_ids"]) - surviving_ids
                if unknown:
                    raise ValueError(
                        f"experiments may target only surviving hypotheses: {sorted(unknown)}"
                    )
            return

        designer = self._completed_result(run_id, "experimental_designer")
        experiment_ids = {experiment["id"] for experiment in designer["experiments"]}

        if role == "method_reviewer":
            used_assessments: set[str] = set()
            for assessment in result["assessments"]:
                experiment_id = assessment["experiment_id"]
                if experiment_id not in experiment_ids:
                    raise ValueError("method reviewer referenced an unknown experiment")
                if experiment_id in used_assessments:
                    raise ValueError("each experiment may be assessed only once")
                used_assessments.add(experiment_id)
            return

        if role == "paper_builder":
            if set(result["included_hypothesis_ids"]) - surviving_ids:
                raise ValueError("publication included a non-surviving hypothesis")
            if set(result["included_experiment_ids"]) - experiment_ids:
                raise ValueError("publication included an unknown experiment")
            return

        if role == "adversarial_reviewer":
            allowed = hypothesis_ids | experiment_ids | {"publication"}
            for finding in result["findings"]:
                if finding["target"] not in allowed:
                    raise ValueError("reviewer may only judge traceable hypotheses, experiments or publication")

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
        if any(stage["status"] != "complete" for stage in stages):
            raise ValueError("all stages must be complete before finalization")
        audit = json.loads(run["audit_json"])
        blindspots = json.loads(run["blindspots_json"])
        engines = json.loads(run["engines_json"])
        outputs = {stage["role"]: json.loads(stage["output_json"]) for stage in stages}
        checks = self._deterministic_checks(audit, blindspots, engines, outputs)
        report = {
            "run_id": run_id,
            "protocol_version": PROTOCOL_VERSION,
            "title": run["title"],
            "verdict": "REVIEW_ASSISTANCE_ONLY",
            "document_hash": run["document_hash"],
            "engines": engines,
            "desi_audit": audit,
            "kevin_blindspots": blindspots,
            "doktores_results": outputs,
            "deterministic_checks": checks,
            "audit_chain": [
                {
                    "stage_id": stage["stage_id"],
                    "role": stage["role"],
                    "entry_hash": stage["entry_hash"],
                }
                for stage in stages
            ],
            "head_hash": self.store.get_run(run_id)["head_hash"],
            "limitations": [
                "The MCP host model supplies language and general domain reasoning; the server supplies protocol, schemas, references and state.",
                "The native Doktores package is capability-checked, but this MCP workflow executes a host-mediated role protocol rather than Doktores().run().",
                "A structural finding is not a proof of physical, mathematical or empirical truth.",
                "Deterministic checks verify traceability and required probes, not arbitrary theorems or external citations.",
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
        audit: dict[str, Any],
        blindspots: dict[str, Any],
        engines: dict[str, Any],
        outputs: dict[str, Any],
    ) -> list[dict[str, Any]]:
        claim_ids = {claim["id"] for claim in audit["claims"]}
        experiments = outputs["experimental_designer"]["experiments"]
        assessments = outputs["method_reviewer"]["assessments"]
        experiment_ids = {experiment["id"] for experiment in experiments}
        assessed_ids = {assessment["experiment_id"] for assessment in assessments}
        paper = outputs["paper_builder"]
        return [
            {
                "check": "claim_reference_integrity",
                "passed": all(
                    set(hypothesis["claim_ids"]) <= claim_ids
                    for hypothesis in outputs["theorist"]["hypotheses"]
                ),
            },
            {
                "check": "seven_role_separation",
                "passed": set(outputs) == set(STAGE_ORDER),
                "detail": "The seven Doktores roles were completed in their fixed order; only the adversarial reviewer emitted the terminal recommendation.",
            },
            {
                "check": "critical_boundary_probe",
                "passed": not blindspots.get("transition_probe", False)
                or any(
                    attack["attack_type"] == "boundary_change"
                    for attack in outputs["falsifier"]["attacks"]
                ),
                "detail": "When generic and critical-point language coexist, the falsifier must test a boundary change.",
            },
            {
                "check": "experiment_traceability",
                "passed": all(
                    bool(experiment["target_hypothesis_ids"])
                    and bool(experiment["metrics"])
                    and bool(experiment["stop_criteria"])
                    for experiment in experiments
                ) if experiments else bool(outputs["experimental_designer"].get("blocked_reason")),
            },
            {
                "check": "method_review_coverage",
                "passed": assessed_ids == experiment_ids
                if experiment_ids
                else bool(outputs["method_reviewer"].get("blocked_reason")),
            },
            {
                "check": "publication_traceability",
                "passed": set(paper["included_experiment_ids"]) <= experiment_ids,
            },
            {
                "check": "ecosystem_provenance",
                "passed": bool(engines["kevin"].get("status"))
                and bool(engines["doktores"].get("status")),
                "detail": "Native availability, versions, execution mode and fallbacks are recorded explicitly.",
            },
        ]

    @staticmethod
    def _render_markdown(report: dict[str, Any]) -> str:
        outputs = report["doktores_results"]
        reviewer = outputs["adversarial_reviewer"]
        literature = outputs["literature_scout"]
        experiments = outputs["experimental_designer"]["experiments"]
        assessments = outputs["method_reviewer"]["assessments"]
        paper = outputs["paper_builder"]
        lines = [
            "# Epistemic Review Report",
            "",
            f"**Paper:** {report['title']}",
            f"**Run:** `{report['run_id']}`",
            f"**Protocol:** `{report['protocol_version']}`",
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
            f"- Status: `{report['kevin_blindspots']['status']}`",
            f"- Axes: {', '.join(report['kevin_blindspots']['blindspot_axes']) or 'none'}",
            f"- Methods: {', '.join(report['kevin_blindspots']['selected_methods']) or 'none'}",
            "",
            "## Doktores research circle",
            f"- Hypotheses: {len(outputs['theorist']['hypotheses'])}",
            f"- Literature/evidence items: {len(literature['evidence'])}",
            f"- Falsification attacks: {len(outputs['falsifier']['attacks'])}",
            f"- Experiments: {len(experiments)}",
            f"- Method assessments: {len(assessments)}",
            f"- Publication artifact: `{paper['publication_kind']}` — {paper['title']}",
            "",
            "## Adversarial findings",
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
                "and the full seven-role Doktores protocol for separated research work. The MCP host "
                "model supplied language and general domain reasoning; package availability and actual "
                "execution modes are recorded in the JSON artifact.",
                "",
                "## Limitations",
            ]
        )
        lines.extend(f"- {item}" for item in report["limitations"])
        return "\n".join(lines) + "\n"
