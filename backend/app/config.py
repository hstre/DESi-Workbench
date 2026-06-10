"""Workbench configuration.

Offline by default. Two independent gates protect against accidental
live LLM calls: ``offline_mode`` must be False AND
``allow_live_llm_calls`` must be True. The MVP pipeline is offline-only
and makes no network calls regardless.

API keys are never read into serialized config, never logged, and never
sent to the frontend or written into reports. Only the NAME of the
environment variable that would hold a key is recorded.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

try:
    from dotenv import load_dotenv

    load_dotenv()  # load a local .env if present (never committed)
except Exception:  # pragma: no cover - dotenv optional at runtime
    pass

_TRUE = {"1", "true", "yes", "on"}

_BACKEND_ROOT = Path(__file__).resolve().parent.parent
# Repo root is one level above backend/.
_REPO_ROOT = _BACKEND_ROOT.parent


def _env_bool(name: str, default: bool) -> bool:
    raw = os.environ.get(name)
    if raw is None:
        return default
    return raw.strip().lower() in _TRUE


@dataclass(frozen=True)
class Settings:
    offline_mode: bool = True
    allow_live_llm_calls: bool = False
    api_key_env: str = "DESI_WORKBENCH_API_KEY"
    # OpenAI-compatible endpoint/model for the opt-in live SPL projection.
    # Not secrets (the key lives in the env var named by api_key_env).
    llm_base_url: str = "https://openrouter.ai/api/v1"
    llm_model: str = "deepseek/deepseek-chat"
    data_dir: Path = _REPO_ROOT / "data" / "reviews"
    cors_origins: tuple[str, ...] = ("http://localhost:3000",)

    @property
    def live_calls_enabled(self) -> bool:
        """Live LLM calls require BOTH gates: not offline AND allowed."""
        return (not self.offline_mode) and self.allow_live_llm_calls

    def public_dict(self) -> dict:
        """Config view that is SAFE to expose to the frontend / reports.

        Contains no secret - only the env-var NAME and a presence flag.
        """
        return {
            "offline_mode": self.offline_mode,
            "allow_live_llm_calls": self.allow_live_llm_calls,
            "live_calls_enabled": self.live_calls_enabled,
            "api_key_env": self.api_key_env,
            "api_key_present": bool(os.environ.get(self.api_key_env)),
        }


def load_settings() -> Settings:
    data_dir = os.environ.get("DESI_WORKBENCH_DATA_DIR")
    return Settings(
        offline_mode=_env_bool("DESI_WORKBENCH_OFFLINE_MODE", True),
        allow_live_llm_calls=_env_bool("DESI_WORKBENCH_ALLOW_LIVE_LLM_CALLS", False),
        api_key_env=os.environ.get("DESI_WORKBENCH_API_KEY_ENV", "DESI_WORKBENCH_API_KEY"),
        llm_base_url=os.environ.get("DESI_WORKBENCH_LLM_BASE_URL", "https://openrouter.ai/api/v1"),
        llm_model=os.environ.get("DESI_WORKBENCH_LLM_MODEL", "deepseek/deepseek-chat"),
        data_dir=Path(data_dir) if data_dir else (_REPO_ROOT / "data" / "reviews"),
    )


settings = load_settings()
