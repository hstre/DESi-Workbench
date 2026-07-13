"""One-shot seven-role plugin test for the Klein-bottle manuscript.

The manuscript itself is not stored in the repository. The runner downloads four
unreferenced encrypted Git blobs, decrypts them with a job-only environment key,
verifies the source hash, and executes the public MCP tool functions in order.
"""
from __future__ import annotations

import base64
import hashlib
import json
import lzma
import os
import urllib.request

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from app.mcp_server import (
    finalize_review,
    get_capabilities,
    get_next_stage,
    start_review,
    submit_stage,
)

BLOBS = (
    "d85c5b9a0fa42fbd779cd4bd8ea1b07a259fb989",
    "f5b8147b44205b788390ece3304e7c381d895325",
    "4edef4603fe3d36fc85bb7a11c8a98432b482fd9",
    "6ebd6b5941189a221017b19fce256dd9c91e7f1f",
)
SOURCE_SHA256 = "51d10f761dc3a3d2525a0e46db16072f789ab6823d9942dda1f465f42bf6725b"


def load_manuscript() -> bytes:
    parts: list[str] = []
    for sha in BLOBS:
        request = urllib.request.Request(
            f"https://api.github.com/repos/hstre/DESi-Workbench/git/blobs/{sha}",
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "DESi-Workbench-Test",
            },
        )
        with urllib.request.urlopen(request, timeout=30) as response:  # noqa: S310
            payload = json.load(response)
        parts.append(base64.b64decode(payload["content"]).decode("utf-8"))
    ciphertext = base64.b64decode("".join(parts))
    key = base64.b64decode(os.environ["KLEIN_KEY"])
    nonce = base64.b64decode(os.environ["KLEIN_NONCE"])
    compressed = AESGCM(key).decrypt(nonce, ciphertext, b"desi-klein-test-v1")
    raw = lzma.decompress(compressed)
    assert hashlib.sha256(raw).hexdigest() == SOURCE_SHA256
    return raw


def stage_results() -> list[dict]:
    return [
        {
            "hypotheses": [
                {
                    "id": "H1",
                    "claim_ids": ["claim_14", "claim_15", "claim_16", "claim_37", "claim_38", "claim_40"],
                    "statement": "The Klein-bottle quotient preserves one metric graviphoton and one orientation-twisted form vector because the relevant deck representations contain invariant zero modes.",
                    "assumptions": ["No additional flux or projection changes the stated flat quotient.", "The twisted field has the stated orientation-line monodromy."],
                    "testable_consequence": "Independent cellular and harmonic calculations must reproduce one ordinary and one twisted invariant vector mode.",
                },
                {
                    "id": "H2",
                    "claim_ids": ["claim_21", "claim_22", "claim_24", "claim_25", "claim_31", "claim_32", "claim_33", "claim_34", "claim_44", "claim_45"],
                    "statement": "The quotient glide projects fields and charges while the residual normalizer reflection produces diagonal charge conjugation and the disconnected bosonic group when the full background preserves it.",
                    "assumptions": ["The reflection is a symmetry of the complete quantum compactification.", "No independent single-photon reflection survives."],
                    "testable_consequence": "Geometry, minimal couplings and the integral charge lattice must all yield the same simultaneous inversion.",
                },
                {
                    "id": "H3",
                    "claim_ids": ["claim_47", "claim_48", "claim_51", "claim_107", "claim_114", "claim_116"],
                    "statement": "The exact AOA spectrum gives the full integral charge lattice, generic two-torus gauge group and self-dual U(2) enhancement with reduced bosonic coinvariants.",
                    "assumptions": ["Every relevant AOA sector is transcribed correctly.", "The displayed roots are the complete screening set."],
                    "testable_consequence": "A sector-by-sector partition-function reconstruction must reproduce the lattice, roots, character group and quotients.",
                },
                {
                    "id": "H4",
                    "claim_ids": ["claim_52", "claim_53", "claim_54", "claim_55", "claim_78", "claim_79", "claim_80", "claim_81", "claim_89"],
                    "statement": "For the enlarged Spin-compatible diagonal A1 completion under constant-modulus two-derivative Einstein assumptions, the cone has deficit pi and total tension one over eight G4.",
                    "assumptions": ["The diagonal quotient is the relevant microscopic filling.", "No long-range field or induced gravity term changes the matching."],
                    "testable_consequence": "Independent quotient-volume and regulated-curvature reductions must agree without an extra factor of two.",
                },
                {
                    "id": "H5",
                    "claim_ids": ["claim_2", "claim_56", "claim_57", "claim_58", "claim_59", "claim_60", "claim_61", "claim_62", "claim_63", "claim_64", "claim_91", "claim_92", "claim_93"],
                    "statement": "A Klein-bottle fibration with only the stated local-system data either projects out the twisted class or preserves a massless mode and cannot alone generate its Stueckelberg mass.",
                    "assumptions": ["The stated spectral sequence captures the selected reduction.", "No torsion, flux, non-harmonic mode or extra coupling is present."],
                    "testable_consequence": "The spectral sequence and a complete vector mass matrix must both show projection or a zero eigenvalue.",
                },
                {
                    "id": "H6",
                    "claim_ids": ["claim_70", "claim_73", "claim_74", "claim_75", "claim_123"],
                    "statement": "The residual bosonic reflection admits the stated effective Pin or enlarged Spin-compatible lift, while the minimal microscopic AOA operator remains unconstructed.",
                    "assumptions": ["Clifford and fermion-parity conventions are consistent.", "The effective nine-dimensional comparison applies."],
                    "testable_consequence": "An explicit operator must satisfy the normalizer relation and reproduce every charge and fermion sector action.",
                },
            ],
            "unresolved_terms": ["complete quantum background", "faithful stringy structure", "total asymptotic tension"],
        },
        {
            "related_work": ["AOA asymmetric orbifold [3]", "Alice electrodynamics [5-8]", "M-theory reflection parity [11,12]", "R7 defects [15,16,18,21,22]"],
            "competing_explanations": ["The residual map may exchange backgrounds rather than gauge one vacuum.", "The deficit may be specific to the chosen A1 filling."],
            "known_counterexamples": ["Flux, torsion, non-harmonic forms or BF couplings can generate masses beyond the minimal assumptions."],
            "datasets": ["AOA partition-function sector table", "manuscript charge lattice", "cellular boundary matrices"],
            "evidence": [
                {"target_hypothesis_ids": ["H1"], "stance": "context", "statement": "The manuscript derives ordinary and twisted harmonic representatives and the projection criterion.", "reference": "Sections 2-3; Appendix A", "source_type": "manuscript"},
                {"target_hypothesis_ids": ["H1"], "stance": "for", "statement": "Componentwise survival is attributed to established Klein-bottle compactification analyses.", "reference": "References [3] and [12]", "source_type": "citation"},
                {"target_hypothesis_ids": ["H2"], "stance": "context", "statement": "Normalizer action and field-charge covariance are developed as separate consistency checks.", "reference": "Sections 3.4-5; Appendix B", "source_type": "manuscript"},
                {"target_hypothesis_ids": ["H3"], "stance": "for", "statement": "Charge normalization and enhanced roots are claimed to follow from the exact AOA spectrum.", "reference": "Reference [3]; Section 6", "source_type": "citation"},
                {"target_hypothesis_ids": ["H4"], "stance": "context", "statement": "The tension claim is restricted to the enlarged diagonal A1 completion and lists its assumptions.", "reference": "Sections 7.2 and 9", "source_type": "manuscript"},
                {"target_hypothesis_ids": ["H5"], "stance": "context", "statement": "The spectral-sequence argument identifies the only outgoing differential and its vanishing target.", "reference": "Section 11.3", "source_type": "manuscript"},
                {"target_hypothesis_ids": ["H6"], "stance": "context", "statement": "The paper distinguishes an effective constraint from an explicit enlarged Spin construction.", "reference": "Section 7; Appendix D", "source_type": "manuscript"},
            ],
            "search_limitations": ["External papers were not independently opened in this run.", "Citation metadata and equations remain provisional."],
        },
        {
            "attacks": [
                {"hypothesis_id": "H1", "target_claim_ids": ["claim_14", "claim_15", "claim_16", "claim_40"], "attack_type": "missing_assumption", "argument": "Invariant-form counting requires the full parity assignment, kinetic normalizability and absence of flux-induced mixing.", "fatal": False},
                {"hypothesis_id": "H2", "target_claim_ids": ["claim_22", "claim_24", "claim_25", "claim_44", "claim_45", "claim_70"], "attack_type": "scope_overreach", "argument": "A bosonic normalizer isometry alone does not prove a gauged symmetry of one complete quantum vacuum.", "fatal": False},
                {"hypothesis_id": "H3", "target_claim_ids": ["claim_47", "claim_48", "claim_51", "claim_107", "claim_114", "claim_116"], "attack_type": "boundary_change", "argument": "Generic radius and the self-dual point are different regimes; an omitted sector or root changes the global-form result.", "fatal": False},
                {"hypothesis_id": "H3", "target_claim_ids": ["claim_47", "claim_48", "claim_114"], "attack_type": "missing_assumption", "argument": "The complete AOA bosonic charge lattice was not independently reconstructed in this run.", "fatal": False},
                {"hypothesis_id": "H4", "target_claim_ids": ["claim_52", "claim_53", "claim_54", "claim_55", "claim_79", "claim_80"], "attack_type": "scope_overreach", "argument": "The numerical tension belongs to the selected completion, not to charge-conjugation monodromy generally.", "fatal": False},
                {"hypothesis_id": "H4", "target_claim_ids": ["claim_53", "claim_78", "claim_89"], "attack_type": "missing_assumption", "argument": "Angular range, quotient volume and fixed-component counting can hide a factor-of-two error.", "fatal": False},
                {"hypothesis_id": "H5", "target_claim_ids": ["claim_58", "claim_60", "claim_61", "claim_62", "claim_63", "claim_93"], "attack_type": "missing_assumption", "argument": "One vanishing differential does not exclude masses produced by additional coupled fields or topological terms.", "fatal": False},
                {"hypothesis_id": "H6", "target_claim_ids": ["claim_70", "claim_73", "claim_75", "claim_123"], "attack_type": "type_mismatch", "argument": "Effective Clifford consistency constrains but does not construct the microscopic AOA symmetry operator.", "fatal": False},
            ],
            "surviving_hypothesis_ids": ["H1", "H2", "H3", "H4", "H5", "H6"],
            "weakest_assumption": "The residual reflection preserves one complete quantum AOA vacuum rather than exchanging distinct backgrounds.",
        },
        {
            "experiments": [
                {"id": "EX1", "target_hypothesis_ids": ["H1"], "design": "Recompute ordinary and twisted cohomology from independent cellular and harmonic constructions and verify all deck actions.", "baselines": ["ordinary coefficients", "circle compactification"], "metrics": ["cohomology ranks", "invariant vector count"], "stop_criteria": "Stop when two implementations agree on groups, representatives and zero modes.", "reproducibility_requirements": ["Publish boundary matrices and sign conventions."]},
                {"id": "EX2", "target_hypothesis_ids": ["H2"], "design": "Audit the normalizer action on deck generators, fields, couplings, charges and every ingredient of the quantum background.", "baselines": ["quotient glide", "background exchange"], "metrics": ["group-relation residuals", "covariance violations", "noninvariant ingredients"], "stop_criteria": "Stop only when geometry, couplings and the complete background give one consistent action.", "reproducibility_requirements": ["Publish transformation tables and fermionic conventions."]},
                {"id": "EX3", "target_hypothesis_ids": ["H3"], "design": "Reconstruct every AOA sector from the partition function and compute the normalized charge, root and character lattices.", "baselines": ["direct product global group", "index-two generic lattice"], "metrics": ["sector coverage", "integrality", "root rank", "coinvariant quotient"], "stop_criteria": "Stop when every sector is accounted for and independent lattice code reproduces both regimes.", "reproducibility_requirements": ["Publish the sector table and code."]},
                {"id": "EX4", "target_hypothesis_ids": ["H4"], "design": "Derive the cone and tension by both quotient-volume reduction and regulated distributional curvature with an explicit factor ledger.", "baselines": ["free-cone mapping torus", "single-reflection core"], "metrics": ["alpha", "deficit", "tension in G4 units", "factor discrepancy"], "stop_criteria": "Stop when both derivations agree and every quotient and multiplicity factor is explicit.", "reproducibility_requirements": ["Publish conventions and a symbolic curvature notebook."]},
                {"id": "EX5", "target_hypothesis_ids": ["H5"], "design": "Compute the local-system spectral sequence and the complete vector mass matrix for representative fibrations with and without extra couplings.", "baselines": ["no invariant section", "invariant section", "added BF coupling"], "metrics": ["Einfinity dimension", "mass-matrix rank", "zero eigenvalues"], "stop_criteria": "Stop when cohomology and explicit reduction agree in all controlled cases.", "reproducibility_requirements": ["Publish monodromies, field basis and mass matrices."]},
                {"id": "EX6", "target_hypothesis_ids": ["H6"], "design": "Construct a microscopic residual-symmetry operator and test its square, normalizer relation and action on all perturbative sectors.", "baselines": ["Pin-minus lift", "Pin-plus exchange", "enlarged Spin lift"], "metrics": ["operator-square phase", "relation residual", "sector coverage"], "stop_criteria": "Stop when one construction acts consistently on the complete minimal spectrum.", "reproducibility_requirements": ["Publish Clifford, GSO and sector conventions."]},
            ],
            "unresolved_constraints": ["External AOA and defect references must be inspected.", "Several tests require expert string-theory review."],
            "blocked_reason": None,
        },
        {
            "assessments": [
                {"experiment_id": "EX1", "verdict": "sound", "concerns": ["Local-coefficient signs can silently change."], "required_controls": ["Cross-check Poincare duality."], "measurement_risks": ["Counting nonglobal representatives."]},
                {"experiment_id": "EX2", "verdict": "repairable", "concerns": ["The full background is not machine-readable."], "required_controls": ["Include fermions, fluxes and branes."], "measurement_risks": ["Confusing background exchange with gauge redundancy."]},
                {"experiment_id": "EX3", "verdict": "repairable", "concerns": ["Sector transcription is load-bearing."], "required_controls": ["Independent reconstruction from reference [3]."], "measurement_risks": ["Inferring a global group from Lie algebra data."]},
                {"experiment_id": "EX4", "verdict": "repairable", "concerns": ["Quotient factors can compensate accidentally."], "required_controls": ["Use two coordinate conventions."], "measurement_risks": ["Applying the result to the minimal core."]},
                {"experiment_id": "EX5", "verdict": "repairable", "concerns": ["Coupled fields may be omitted."], "required_controls": ["Derive the complete mass matrix."], "measurement_risks": ["Equating a cohomology class with the physical vector."]},
                {"experiment_id": "EX6", "verdict": "repairable", "concerns": ["No minimal microscopic operator is supplied."], "required_controls": ["Check every perturbative sector."], "measurement_risks": ["Equating effective consistency with construction."]},
            ],
            "cross_cutting_limitations": ["External references were not independently checked.", "DESi over-flags internal theoretical derivations and emits irrelevant dataset questions."],
            "blocked_reason": None,
        },
        {
            "publication_kind": "report",
            "title": "Epistemic stress test: Two Photons from the Klein Bottle",
            "markdown": "# Epistemic stress test\n\nThe manuscript presents a coherent chain from Klein-bottle zero-mode projection through disconnected gauge structure, exact-spectrum normalization, defect coinvariants, an enlarged A1 completion and a fibration no-mass statement. All six hypotheses survive only conditionally. The principal unresolved dependencies are the complete quantum lift of the residual reflection, an independent reconstruction of the AOA charge sectors and global group, a factor-by-factor audit of the orbifold tension, and a full coupled mass-matrix check. The paper already limits several claims correctly by separating the minimal bosonic construction from the enlarged completion. External references and calculations were not independently verified in this run.\n\nRecommended status: revise before treating the strongest global and ultraviolet claims as independently established.",
            "included_hypothesis_ids": ["H1", "H2", "H3", "H4", "H5", "H6"],
            "included_experiment_ids": ["EX1", "EX2", "EX3", "EX4", "EX5", "EX6"],
            "limitations": ["No external citation verification.", "No independent partition-function or Einstein-reduction calculation.", "DESi support flags are syntactic."],
            "open_questions": ["Does the residual reflection act within one fixed minimal AOA background?", "Does the exact sector table reproduce U(2)?", "Is every factor of two in the tension fixed?", "Can additional coupled fields evade the no-mass result?"],
        },
        {
            "findings": [
                {"target": "H1", "verdict": "present", "reason": "The zero-mode mechanism is explicitly derived and directly reproducible.", "required_revision": "Add a compact parity and survival table.", "deterministic_check": "EX1"},
                {"target": "H2", "verdict": "borderline", "reason": "The bosonic action is coherent, but fixed-vacuum gauged status remains conditional on the full lift.", "required_revision": "Keep the conditional wording prominent.", "deterministic_check": "EX2"},
                {"target": "H3", "verdict": "borderline", "reason": "The global-form result depends on an exact AOA sector reconstruction not checked here.", "required_revision": "Include a complete reproducible sector table.", "deterministic_check": "EX3"},
                {"target": "H4", "verdict": "borderline", "reason": "The tension is carefully scoped but remains vulnerable to quotient and multiplicity factors.", "required_revision": "Publish two derivations and a factor ledger.", "deterministic_check": "EX4"},
                {"target": "H5", "verdict": "borderline", "reason": "The spectral-sequence argument is clear for the selected class but not the full coupled mass matrix.", "required_revision": "Add an explicit representative mass matrix.", "deterministic_check": "EX5"},
                {"target": "H6", "verdict": "borderline", "reason": "The effective lift constrains but does not construct the minimal microscopic operator.", "required_revision": "Identify the operator construction as open work.", "deterministic_check": "EX6"},
                {"target": "publication", "verdict": "borderline", "reason": "The limitations are unusually explicit, but the exact-spectrum and ultraviolet claims need independent checks.", "required_revision": "Prioritize the AOA table, tension ledger and audit wording.", "deterministic_check": "all experiments"},
            ],
            "overall": "revise",
            "blocking_issues": ["No independent AOA sector reconstruction.", "No minimal microscopic fermionic operator.", "No independent tension factor audit."],
            "limitations": ["Structural review only, not expert validation.", "External citations were not opened.", "DESi over-flags internal derivations."],
        },
    ]


def main() -> None:
    raw = load_manuscript()
    capabilities = get_capabilities()
    run = start_review(
        text=raw.decode("utf-8"),
        title="Two Photons from the Klein Bottle",
        focus="Full epistemic stress test of the final manuscript",
    )
    run_id = run["run_id"]
    stage_hashes: list[dict[str, str]] = []
    for ordinal, result in enumerate(stage_results(), 1):
        stage = get_next_stage(run_id)
        assert stage["stage_id"] == f"S{ordinal:02d}"
        response = submit_stage(run_id, stage["stage_id"], result)
        stage_hashes.append({"stage": stage["stage_id"], "role": stage["role"], "hash": response["entry_hash"]})
        print("STAGE_OK", stage["stage_id"], stage["role"])
    final = finalize_review(run_id)
    report = final["report"]
    summary = {
        "run_id": run_id,
        "document_hash": run["document_hash"],
        "source_sha256": hashlib.sha256(raw).hexdigest(),
        "protocol_version": run["protocol_version"],
        "claim_count": len(run["audit"]["claims"]),
        "unsupported_count": len(run["audit"]["unsupported_claim_ids"]),
        "overclaim_count": len(run["audit"]["overclaims"]),
        "reviewer_questions": run["audit"]["reviewer_questions"],
        "kevin": run["blindspots"],
        "capabilities": capabilities,
        "stage_hashes": stage_hashes,
        "reviewer_overall": report["doktores_results"]["adversarial_reviewer"]["overall"],
        "blocking_issues": report["doktores_results"]["adversarial_reviewer"]["blocking_issues"],
        "deterministic_checks": report["deterministic_checks"],
        "head_hash": report["head_hash"],
        "report_hash": final["report_hash"],
    }
    print("FULL_REVIEW_SUMMARY")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print("FULL_REPORT_MARKDOWN")
    print(final["markdown"])
    print("KLEIN_PLUGIN_FULL_OK")


if __name__ == "__main__":
    main()
