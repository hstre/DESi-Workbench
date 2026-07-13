"""Pydantic contracts for the MCP epistemic-review workflow."""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, HttpUrl, model_validator


ReviewMode = Literal["audit", "extend", "adversarial"]
StageRole = Literal["theorist", "falsifier", "adversarial_reviewer"]
StageStatus = Literal["pending", "active", "complete"]


class FileRef(BaseModel):
    """ChatGPT file reference passed through ``openai/fileParams``."""

    download_url: HttpUrl
    file_id: str = Field(min_length=1)
    mime_type: str | None = None
    file_name: str | None = None


class StartReviewInput(BaseModel):
    title: str | None = None
    text: str | None = None
    paper: FileRef | None = None
    modes: tuple[ReviewMode, ...] = ("audit", "extend", "adversarial")
    focus: str | None = None

    @model_validator(mode="after")
    def exactly_one_source(self) -> "StartReviewInput":
        if bool(self.text and self.text.strip()) == bool(self.paper):
            raise ValueError("Provide exactly one of text or paper")
        if not self.modes:
            raise ValueError("At least one review mode is required")
        return self


class Hypothesis(BaseModel):
    id: str = Field(pattern=r"^H[0-9]+$")
    claim_ids: list[str] = Field(min_length=1)
    statement: str = Field(min_length=20)
    assumptions: list[str] = Field(default_factory=list)
    testable_consequence: str = Field(min_length=10)


class TheoristResult(BaseModel):
    hypotheses: list[Hypothesis] = Field(min_length=1, max_length=12)
    unresolved_terms: list[str] = Field(default_factory=list)


class Attack(BaseModel):
    hypothesis_id: str = Field(pattern=r"^H[0-9]+$")
    target_claim_ids: list[str] = Field(min_length=1)
    attack_type: Literal[
        "contradiction",
        "boundary_change",
        "type_mismatch",
        "missing_assumption",
        "simpler_explanation",
        "non_falsifiable",
        "scope_overreach",
    ]
    argument: str = Field(min_length=20)
    fatal: bool = False


class FalsifierResult(BaseModel):
    attacks: list[Attack] = Field(min_length=1, max_length=24)
    surviving_hypothesis_ids: list[str] = Field(default_factory=list)
    weakest_assumption: str = Field(min_length=10)


class ReviewedFinding(BaseModel):
    target: str = Field(min_length=1)
    verdict: Literal["present", "borderline", "discard"]
    reason: str = Field(min_length=20)
    required_revision: str | None = None
    deterministic_check: str | None = None


class AdversarialReviewerResult(BaseModel):
    findings: list[ReviewedFinding] = Field(min_length=1, max_length=24)
    overall: Literal["accept", "revise", "reject"]
    blocking_issues: list[str] = Field(default_factory=list)
    limitations: list[str] = Field(default_factory=list)


STAGE_RESULT_MODELS: dict[StageRole, type[BaseModel]] = {
    "theorist": TheoristResult,
    "falsifier": FalsifierResult,
    "adversarial_reviewer": AdversarialReviewerResult,
}


class StageSubmission(BaseModel):
    run_id: str = Field(min_length=12)
    stage_id: str = Field(pattern=r"^S[0-9]{2}$")
    result: dict[str, Any]
