#!/usr/bin/env python3
"""Unified proposal gate: audit + optional document quality (SI-B2/B3, S4).

Exit codes:
  0 READY or CONDITIONAL-GO (internal)  — alias SUBMISSION-READY for READY
  1 BLOCKED or DECISION_MEMO_ONLY
  2 INVALID / usage / missing dependency
"""

from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
from pathlib import Path


SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent
SKILLS_ROOT = SKILL_DIR.parent


def _find_proposal_gate() -> Path | None:
    env = os.environ.get("PROPOSAL_GATE_PATH")
    if env and Path(env).is_file():
        return Path(env)
    candidates = [
        SKILLS_ROOT / "create-winning-proposal" / "scripts" / "proposal_gate.py",
        SKILL_DIR / "vendor" / "proposal_gate.py",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _find_quality_gate() -> Path | None:
    env = os.environ.get("QUALITY_GATE_PATH")
    if env and Path(env).is_file():
        return Path(env)
    candidates = [
        SKILLS_ROOT / "create-proposal-document" / "scripts" / "quality_gate.py",
        SKILL_DIR / "vendor" / "quality_gate.py",
    ]
    for p in candidates:
        if p.is_file():
            return p
    return None


def _load_gate_module(path: Path):
    import importlib.util
    spec = importlib.util.spec_from_file_location("proposal_gate_mod", path)
    if spec is None or spec.loader is None:
        raise ImportError(f"cannot load {path}")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def classify(decision: str, failures: list[str]) -> tuple[str, int]:
    """Return (label, exit_code). READY ≡ SUBMISSION-READY (S8)."""
    if any(f.startswith("DECISION_MEMO_ONLY") for f in failures):
        return "DECISION_MEMO_ONLY", 1
    if decision in {"no-bid", "intake-incomplete"}:
        if failures:
            return "DECISION_MEMO_ONLY", 1
    if failures:
        return "BLOCKED", 1
    if decision == "conditional-bid":
        return "CONDITIONAL-GO", 0
    return "READY", 0


def run_quality_gate(doc: Path, stage: str, lang: str, names: Path | None,
                     palette: str | None) -> tuple[int, str]:
    qg = _find_quality_gate()
    if qg is None:
        return 2, "quality_gate.py not found (install create-proposal-document " \
                  "or set QUALITY_GATE_PATH; use install_skill.py --with-deps)"
    cmd = [sys.executable, str(qg), str(doc), "--stage", stage, "--lang", lang]
    if names:
        cmd += ["--names", str(names)]
    if palette:
        cmd += ["--palette", palette]
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("audit", type=Path, help="Audit JSON path")
    ap.add_argument("--doc", type=Path, help="Optional PPTX/DOCX for quality_gate")
    ap.add_argument("--stage", choices=["draft", "submission"], default="submission")
    ap.add_argument("--lang", choices=["ko", "en", "both"], default="ko")
    ap.add_argument("--names", type=Path, help="Banned residual names file")
    ap.add_argument("--palette", help="Allowed hex palette comma-list")
    ap.add_argument("--explain", action="store_true", default=True,
                    help="Print remediation markdown (default: on)")
    ap.add_argument("--no-explain", action="store_true",
                    help="Status labels only, no remediation table")
    args = ap.parse_args(argv)
    explain = not args.no_explain

    if args.doc:
        code, qout = run_quality_gate(args.doc, args.stage, args.lang, args.names, args.palette)
        print("=== quality_gate ===")
        print(qout.rstrip() or "(no output)")
        if code == 2:
            print("INVALID: quality_gate usage/dependency failure")
            return 2
        if code != 0:
            print("BLOCKED: document quality_gate failed")
            return 1

    gate_path = _find_proposal_gate()
    if gate_path is None:
        print("INVALID: proposal_gate.py not found "
              "(install create-winning-proposal or set PROPOSAL_GATE_PATH; "
              "use install_skill.py --with-deps)",
              file=sys.stderr)
        return 2

    try:
        data = json.loads(args.audit.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        print(f"INVALID: {exc}")
        return 2

    mod = _load_gate_module(gate_path)
    schema_failures = mod.validate_schema(data)
    if schema_failures:
        if explain and hasattr(mod, "explain_markdown"):
            print(mod.explain_markdown(data, schema_failures, []))
        else:
            print("INVALID")
            for f in schema_failures:
                print(f"- {f}")
        return 2

    failures = mod.evaluate(data)
    decision = data.get("bid_decision", "")
    if decision in {"no-bid", "intake-incomplete"}:
        enriched = []
        for f in failures:
            if f == "bid_decision must be 'bid' or accepted 'conditional-bid'":
                enriched.append(
                    f"DECISION_MEMO_ONLY: bid_decision={decision}; "
                    "full proposal drafting blocked; deliver decision memo only")
            else:
                enriched.append(f)
        failures = enriched

    label, exit_code = classify(str(decision), failures)
    # S8: READY ≡ SUBMISSION-READY
    display = "SUBMISSION-READY" if label == "READY" else label
    print(f"=== proposal_gate → {display} ===")
    if explain and hasattr(mod, "explain_markdown"):
        # Rebuild failures list for explain: restore raw evaluate for clean table
        raw = mod.evaluate(data)
        print(mod.explain_markdown(data, [], raw))
    elif failures:
        for f in failures:
            print(f"- {f}")
    else:
        if label == "CONDITIONAL-GO":
            print("internal continuation only — not external submission clearance")
        else:
            print("all deterministic checks passed")
    print(f"STATUS: {display}")
    if label == "READY":
        print("ALIAS: READY ≡ SUBMISSION-READY")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
