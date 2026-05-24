from __future__ import annotations


def test_health(client):
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert body["verdict"] == "REVIEW_ASSISTANCE_ONLY"
    assert body["desi"]["library"] == "desi-governance"
    assert body["desi"]["core_identity"] == 1.0


def test_config_is_offline_by_default(client):
    body = client.get("/config").json()
    assert body["offline_mode"] is True
    assert body["allow_live_llm_calls"] is False
    assert body["live_calls_enabled"] is False


def test_review_offline(client, sample):
    r = client.post("/api/review", json={"text": sample, "mode": "offline"})
    assert r.status_code == 200
    body = r.json()
    assert body["verdict"] == "REVIEW_ASSISTANCE_ONLY"
    assert body["claims"], "expected claims"
    assert body["overclaims"], "expected overclaim risks"
    assert body["evidence_gaps"], "expected evidence gaps"
    assert body["reproducibility_risks"], "expected reproducibility risks"
    assert body["replay"]["offline_mode"] is True
    assert body["replay"]["core_identity"] == 1.0
    # categories are from the fixed taxonomy
    cats = {c["category"] for c in body["claims"]}
    assert cats <= {
        "main_claim", "method_claim", "evidence_claim", "result_claim",
        "limitation_claim", "novelty_claim", "generalization_claim",
    }


def test_overclaim_terms_detected(client, sample):
    body = client.post("/api/review", json={"text": sample}).json()
    found = {t for oc in body["overclaims"] for t in oc["terms"]}
    for term in ("first", "novel", "robust", "significant", "generalizes", "solves"):
        assert term in found, f"missing overclaim term {term}"


def test_reproducibility_risks_detected(client, sample):
    body = client.post("/api/review", json={"text": sample}).json()
    types = {r["risk_type"] for r in body["reproducibility_risks"]}
    # The sample mentions "state of the art", which counts as a comparison
    # cue and suppresses missing_baselines - that is intended behaviour.
    assert {
        "missing_code", "missing_data", "missing_parameters",
        "unclear_dataset", "unsupported_metrics",
    } <= types


def test_deterministic_same_input(client, sample):
    a = client.post("/api/review", json={"text": sample}).json()
    b = client.post("/api/review", json={"text": sample}).json()
    assert a["review_id"] == b["review_id"]
    assert a["replay"]["output_hash"] == b["replay"]["output_hash"]
    assert a == b


def test_graph_valid(client, sample):
    body = client.post("/api/review", json={"text": sample}).json()
    graph = body["graph"]
    node_ids = {n["id"] for n in graph["nodes"]}
    assert "paper" in node_ids
    assert len(node_ids) == len(graph["nodes"]), "node ids must be unique"
    for edge in graph["edges"]:
        assert edge["source"] in node_ids, f"dangling source {edge['source']}"
        assert edge["target"] in node_ids, f"dangling target {edge['target']}"
    # claims and gaps appear as nodes
    types = {n["type"] for n in graph["nodes"]}
    assert "claim" in types


def test_report_generated_and_retrievable(client, sample):
    body = client.post("/api/review", json={"text": sample}).json()
    rid = body["review_id"]

    r = client.get(f"/api/review/{rid}/report.md")
    assert r.status_code == 200
    md = r.text
    for header in (
        "# DESi Workbench Review Report",
        "## Scope",
        "## Main Claims",
        "## Overclaim Risks",
        "## Evidence Gaps",
        "## Reproducibility Risks",
        "## Claim Graph Summary",
        "## Reviewer Questions",
        "## Replay Trace",
        "## Limitations",
    ):
        assert header in md
    assert "This is not peer review." in md


def test_get_review_and_graph_roundtrip(client, sample):
    rid = client.post("/api/review", json={"text": sample}).json()["review_id"]
    again = client.get(f"/api/review/{rid}")
    assert again.status_code == 200
    assert again.json()["review_id"] == rid

    g = client.get(f"/api/review/{rid}/graph")
    assert g.status_code == 200
    assert "nodes" in g.json() and "edges" in g.json()


def test_unknown_review_404(client):
    assert client.get("/api/review/" + "a" * 64).status_code == 404


def test_empty_text_rejected(client):
    assert client.post("/api/review", json={"text": "   "}).status_code == 400
