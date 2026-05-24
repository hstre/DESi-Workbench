"""File-based storage for reviews (no database in the MVP).

Layout:
    data/reviews/{review_id}/
      input.txt
      review.json     (DESi canonical JSON - byte-stable)
      report.md

No secrets are ever stored. ``review_id`` is a content hash, so it is
validated as hex to prevent path traversal.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

from . import desi_adapter
from .config import settings
from .models import ReviewResponse
from .report_renderer import render_report

_ID_RE = re.compile(r"^[a-f0-9]{8,128}$")


def _valid_id(review_id: str) -> bool:
    return bool(_ID_RE.match(review_id))


def _review_dir(review_id: str) -> Path:
    return settings.data_dir / review_id


def save_review(review: ReviewResponse, input_text: str) -> Path:
    if not _valid_id(review.review_id):
        raise ValueError("invalid review_id")
    d = _review_dir(review.review_id)
    d.mkdir(parents=True, exist_ok=True)
    (d / "input.txt").write_text(input_text, encoding="utf-8")
    (d / "review.json").write_text(
        desi_adapter.to_canonical_json(review.model_dump()), encoding="utf-8"
    )
    (d / "report.md").write_text(render_report(review), encoding="utf-8")
    return d


def load_review(review_id: str) -> ReviewResponse | None:
    if not _valid_id(review_id):
        return None
    path = _review_dir(review_id) / "review.json"
    if not path.is_file():
        return None
    return ReviewResponse.model_validate(json.loads(path.read_text(encoding="utf-8")))


def load_report(review_id: str) -> str | None:
    if not _valid_id(review_id):
        return None
    path = _review_dir(review_id) / "report.md"
    if not path.is_file():
        return None
    return path.read_text(encoding="utf-8")
