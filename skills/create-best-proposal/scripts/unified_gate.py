#!/usr/bin/env python3
"""Unified proposal gate: audit + optional document quality (SI-B2/B3, S4).

Exit codes:
  0 READY or CONDITIONAL-GO (internal)  — SUBMISSION-READY only when audit.mode=submission,
    otherwise <MODE>-READY (e.g. DRAFT-READY)
  1 BLOCKED or DECISION_MEMO_ONLY
  2 INVALID / usage / missing dependency
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
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
    for attr in ("validate_schema", "evaluate"):
        if not hasattr(mod, attr):
            raise ImportError(f"{path} is not proposal_gate.py (missing {attr})")
    return mod


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _norm_digest(value: object) -> str:
    """비교용 정규화 — 'sha256:' 접두사 제거 + 소문자. 64 hex가 아니면 빈 문자열."""
    if not isinstance(value, str):
        return ""
    v = value.strip().lower().removeprefix("sha256:")
    return v if re.fullmatch(r"[0-9a-f]{64}", v) else ""


def bind_document(data: dict, doc: Path) -> list[str]:
    """전달된 실제 파일과 audit의 검사 대상 해시를 대조한다.

    audit은 사람이 한 검토의 기록이다. 그 기록이 '어느 바이트'에 적용되는지
    확인하지 않으면, 검토 이후 가격·기간이 바뀐 파일에 과거 판정을 재사용하게 된다.
    """
    actual = sha256_file(doc)
    problems: list[str] = []
    for field in ("render", "package"):
        block = data.get(field)
        if not isinstance(block, dict):
            continue
        declared = _norm_digest(block.get("artifact_hash"))
        if declared and declared != actual:
            problems.append(
                f"{field}.artifact_hash가 전달된 문서와 다르다 "
                f"(audit {declared[:12]}… vs {doc.name} {actual[:12]}…) — "
                "검토 이후 파일이 바뀌었다. 재검사 후 audit을 갱신한다")
    return problems


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
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    proc = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                          errors="replace", env=env)
    out = (proc.stdout or "") + (proc.stderr or "")
    return proc.returncode, out


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audit", type=Path, help="Audit JSON path")
    ap.add_argument("--doc", type=Path,
                    help="PPTX/DOCX to inspect and hash-bind (required when audit.mode=submission)")
    ap.add_argument("--stage", choices=["draft", "submission"], default="submission")
    ap.add_argument("--audit-only", action="store_true",
                    help="문서 없이 audit만 점검한다. 통과해도 SUBMISSION-READY가 아니라 AUDIT-VALID다")
    ap.add_argument("--lang", choices=["ko", "en", "both"], default="ko")
    ap.add_argument("--names", type=Path, help="Banned residual names file")
    ap.add_argument("--palette", help="Allowed hex palette comma-list")
    ap.add_argument("--explain", action=argparse.BooleanOptionalAction, default=True,
                    help="Print remediation markdown (default: on; --no-explain = labels only)")
    args = ap.parse_args(argv)
    explain = args.explain
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8", errors="replace")
        except (AttributeError, ValueError):
            pass

    gate_path = _find_proposal_gate()
    if gate_path is None:
        print("INVALID: proposal_gate.py not found "
              "(install create-winning-proposal or set PROPOSAL_GATE_PATH; "
              "use install_skill.py --with-deps)",
              file=sys.stderr)
        return 2

    try:
        data = json.loads(args.audit.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        print(f"INVALID: {exc}")
        return 2
    if not isinstance(data, dict):
        print("INVALID: audit root must be an object")
        return 2

    try:
        mod = _load_gate_module(gate_path)
    except (ImportError, SyntaxError, OSError) as exc:
        print(f"INVALID: cannot load proposal_gate: {exc}", file=sys.stderr)
        return 2
    try:
        schema_failures = mod.validate_schema(data)
    except Exception as exc:  # 스키마 검사가 터지면 트레이스백이 아니라 사용 오류로 반환
        print(f"INVALID: schema check failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 2
    if schema_failures:
        if explain and hasattr(mod, "explain_markdown"):
            print(mod.explain_markdown(data, schema_failures, []))
        else:
            print("INVALID")
            for f in schema_failures:
                print(f"- {f}")
        return 2

    audit_mode = str(data.get("mode", ""))
    # 단계 강제: submission audit을 draft 기준으로 검사하면 [NEEDS INPUT]이 경고로
    # 내려가 SUBMISSION-READY가 나온다. 목적과 검사 강도를 어긋나게 두지 않는다.
    if audit_mode == "submission" and args.stage != "submission":
        print(f"INVALID: audit.mode=submission인데 --stage {args.stage} — "
              "제출 audit은 --stage submission으로만 검사한다", file=sys.stderr)
        return 2

    doc_failures: list[str] = []
    if args.doc:
        if not args.doc.is_file():
            print(f"INVALID: 문서 없음: {args.doc}", file=sys.stderr)
            return 2
        code, qout = run_quality_gate(args.doc, args.stage, args.lang, args.names, args.palette)
        print("=== quality_gate ===")
        print(qout.rstrip() or "(no output)")
        if code == 2:
            print("INVALID: quality_gate usage/dependency failure")
            return 2
        if code != 0:
            print("BLOCKED: document quality_gate failed")
            return 1
        doc_failures = bind_document(data, args.doc)
    elif audit_mode == "submission" and data.get("artifact_required") is True and not args.audit_only:
        doc_failures = ["제출 판정에는 실제 산출물이 필요하다 — --doc <최종파일>로 다시 실행한다 "
                        "(문서 없이 audit만 보려면 --audit-only)"]

    try:
        failures = mod.evaluate(data)
    except Exception as exc:  # GateEnvironmentError 등 — 게이트 판정이 아닌 환경 오류
        print(f"INVALID: gate error: {exc}", file=sys.stderr)
        return 2
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

    # 문서 대조 실패는 게이트 차단 사유로 합류시킨다(라벨·종료코드가 함께 움직인다).
    failures = list(failures) + doc_failures

    # 라벨은 proposal_gate.readiness 하나에서 나온다 — CLI·explain·점수 보고서가
    # 같은 판정을 쓰도록 단일화(예전엔 여기서 별도 계산해 설명문과 어긋났다).
    if hasattr(mod, "readiness"):
        display, exit_code = mod.readiness(data, failures)
    else:  # 구버전 proposal_gate 호환
        label, exit_code = classify(str(decision), failures)
        display = "SUBMISSION-READY" if label == "READY" and audit_mode == "submission" else \
            (f"{audit_mode.upper() or 'DRAFT'}-READY" if label == "READY" else label)
    if display == "SUBMISSION-READY" and not args.doc:
        # --audit-only 경로: 실제 파일을 보지 않았으므로 제출 준비로 표시하지 않는다.
        display = "AUDIT-VALID"
        print("NOTE: 문서 미검사(--audit-only) — audit 자체만 유효하다. "
              "제출 판정은 --doc <최종파일>로 다시 받는다.")
    if args.stage == "submission" and audit_mode != "submission":
        print(f"NOTE: audit.mode={audit_mode!r} — 제출 판정이 아니다. "
              "제출 게이트는 mode=submission audit으로 다시 실행한다.")
    print(f"=== proposal_gate → {display} ===")
    if explain and hasattr(mod, "explain_markdown"):
        # 최종 판정(display)을 설명에도 그대로 넘긴다. 설명이 audit으로 상태를 다시
        # 계산하면 STATUS: AUDIT-VALID 옆에 "제출 가능"이 찍히는 모순이 생긴다.
        try:
            print(mod.explain_markdown(data, [], failures, display))
        except TypeError:  # 구버전 proposal_gate 호환
            print(mod.explain_markdown(data, [], failures))
    elif failures:
        for f in failures:
            print(f"- {f}")
    else:
        if display == "CONDITIONAL-GO":
            print("internal continuation only — not external submission clearance")
        else:
            print("all deterministic checks passed")
    print(f"STATUS: {display}")
    if display == "SUBMISSION-READY":
        print("ALIAS: READY ≡ SUBMISSION-READY")
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
