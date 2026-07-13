from __future__ import annotations

import pytest

kevin = pytest.importorskip("kevin")
doktores = pytest.importorskip("doktores")

from app.epistemic_review.adapters import engine_manifest, kevin_blindspots  # noqa: E402


def test_native_ecosystem_packages_expose_expected_public_api():
    assert hasattr(kevin, "Kevin")
    assert hasattr(kevin, "Problem")
    assert hasattr(doktores, "Doktores")
    assert hasattr(doktores, "ResearchTask")


def test_manifest_discloses_native_packages_without_claiming_native_doktores_run():
    manifest = engine_manifest()
    assert manifest["kevin"]["available"] is True
    assert manifest["kevin"]["status"] == "ready"
    assert manifest["doktores"]["available"] is True
    assert manifest["doktores"]["status"] == "ready"
    assert manifest["doktores"]["native_run_invoked"] is False
    assert len(manifest["doktores"]["protocol_roles"]) == 7


def test_kevin_space_predictor_is_actually_used():
    claims = [
        {
            "id": "claim_1",
            "text": "The mechanism holds generically but changes at the critical point r=1.",
        },
        {"id": "claim_2", "text": "Evidence remains incomplete."},
    ]
    result = kevin_blindspots("Critical boundary test", claims)
    assert result["status"] == "native"
    assert result["engine"] == "kevin.space_predictor"
    assert result["fallback_reason"] is None
    assert result["transition_probe"] is True
    assert "limit_case_analysis" in result["selected_methods"]
