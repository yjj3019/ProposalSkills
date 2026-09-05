#!/usr/bin/env python3
"""저장소 루트 호환 진입점 — 실제 구현은 skills/create-best-proposal/scripts/score_completeness.py."""
import importlib.util
import sys
from pathlib import Path

_IMPL = Path(__file__).resolve().parent / "skills" / "create-best-proposal" / "scripts" / "score_completeness.py"
_spec = importlib.util.spec_from_file_location("_score_completeness_impl", _IMPL)
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)
globals().update({k: v for k, v in vars(_mod).items() if not k.startswith("__")})

if __name__ == "__main__":
    raise SystemExit(_mod.main(sys.argv))
