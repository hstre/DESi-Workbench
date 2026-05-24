"""Shared test fixtures. Sets a temp data dir BEFORE the app is imported."""
from __future__ import annotations

import os
import tempfile

# Must run before `app.config` reads the environment at import time.
os.environ.setdefault(
    "DESI_WORKBENCH_DATA_DIR", tempfile.mkdtemp(prefix="wb-test-")
)

import pytest
from fastapi.testclient import TestClient

from app.main import app

SAMPLE_PAPER = """# A Novel Method That Solves Generalization

## Abstract
We present the first method that solves generalization. Our novel approach
proves robust under all conditions and shows significant gains, setting a
new state of the art.

## Results
Our approach achieves high accuracy and strong performance on a dataset.
We outperform on the task throughout.

## Conclusion
We have presented the first robust approach that generalizes to any task.
"""


@pytest.fixture(scope="session")
def client() -> TestClient:
    return TestClient(app)


@pytest.fixture
def sample() -> str:
    return SAMPLE_PAPER
