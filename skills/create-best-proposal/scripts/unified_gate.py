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
CHECK_TIMEOUT_SECONDS = 240


def _run_check(cmd: list[str]) -> tuple[int, str]:
    """Bound child checks; missing evidence is an execution error, never a pass."""
    try:
        proc = subprocess.run(
            cmd, capture_output=True, text=True, encoding="utf-8", errors="replace",
            env={**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"},
            timeout=CHECK_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return 2, f"{Path(cmd[1]).name}: check timed out after {CHECK_TIMEOUT_SECONDS}s"
    except OSError as exc:
        return 2, f"{Path(cmd[1]).name}: check could not start ({type(exc).__name__})"
    return proc.returncode, (proc.stdout or "") + (proc.stderr or "")


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


def _find_check_numbers() -> Path | None:
    env = os.environ.get("CHECK_NUMBERS_PATH")
    if env and Path(env).is_file():
        return Path(env)
    candidates = [
        SKILLS_ROOT / "create-proposal-document" / "scripts" / "check_numbers.py",
        SKILL_DIR / "vendor" / "check_numbers.py",
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


def run_deck_check(doc: Path) -> tuple[int, str]:
    checker = SKILLS_ROOT / "create-proposal-document" / "scripts" / "deck_check.py"
    if not checker.is_file():
        return 2, "deck_check.py not found (install create-proposal-document)"
    return _run_check([sys.executable, str(checker), str(doc), "--stage", "submission"])


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def _inputs_changed(inputs: dict[Path, str]) -> bool:
    # shortcut: endpoint hashes miss edits restored between reads; use immutable inputs when needed.
    try:
        return any(sha256_file(path) != digest for path, digest in inputs.items())
    except OSError:
        return True


def _norm_digest(value: object) -> str:
    """Normalize hashes: strip 'sha256:' and lowercase; return an empty string unless 64 hex characters remain."""
    if not isinstance(value, str):
        return ""
    v = value.strip().lower().removeprefix("sha256:")
    return v if re.fullmatch(r"[0-9a-f]{64}", v) else ""


def bind_document(data: dict, doc: Path) -> list[str]:
    """Compare the supplied actual file with the audit inspection hash. An audit records human review; without binding it to exact bytes, old decisions could be reused after prices or durations change."""
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


def run_check_numbers(doc: Path, audit_path: Path) -> tuple[int, str]:
    """Compare ledger values with the actual document body. The gate recalculates ledger sums and ratios, but must open the document to check slide values. Human-only comparison allows mismatched ledgers and slides to be submitted."""
    cn = _find_check_numbers()
    if cn is None:
        return 2, "check_numbers.py not found (install create-proposal-document " \
                  "or set CHECK_NUMBERS_PATH; use install_skill.py --with-deps)"
    return _run_check([sys.executable, str(cn), str(doc), "--audit", str(audit_path)])


def verify_bundle(data: dict, root: Path) -> list[str]:
    """Verify every submission attachment exists at its recorded location with its recorded contents. The audit attachments[] is a human record; hashing only the main file cannot detect changed or missing attachments still marked 'present: true'."""
    problems: list[str] = []
    root = root.resolve()
    for item in data.get("attachments", []):
        if not isinstance(item, dict) or not item.get("present") is True:
            continue
        digest = item.get("sha256")
        name = item.get("name") or "?"
        filename = item.get("file") or name
        if not isinstance(filename, str) or not filename.strip():
            problems.append(f"bundle: 첨부 파일명이 문자열이 아니다 — {name}")
            continue
        try:
            if "\x00" in filename:
                raise ValueError("embedded null in attachment path")
            path = (root / filename).resolve()
        except (OSError, RuntimeError, ValueError):
            problems.append(f"bundle: 첨부 경로를 해석할 수 없다 — {filename!r}")
            continue
        if Path(filename).is_absolute() or not path.is_relative_to(root):
            problems.append(f"bundle: 첨부 경로가 제출 폴더 밖을 가리킨다 — {filename}")
            continue
        if not path.is_file():
            problems.append(f"bundle: 첨부 파일 없음 — {filename} (attachment {name}) "
                            f"@ {root}")
            continue
        if not _norm_digest(digest):
            problems.append(f"bundle: {filename}에 유효한 sha256이 없다 — 미검사")
            continue
        actual = "sha256:" + sha256_file(path)
        if _norm_digest(digest) != _norm_digest(actual):
            problems.append(
                f"bundle: {filename}의 해시가 audit과 다르다 "
                f"(audit {_norm_digest(digest)[:12]}… vs 파일 {_norm_digest(actual)[:12]}…) "
                "— 검토 이후 이 파일이 바뀌었다")
    return problems


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
    return _run_check(cmd)


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("audit", type=Path, help="Audit JSON path")
    ap.add_argument("--doc", type=Path,
                    help="PPTX/DOCX to inspect and hash-bind (required when audit.mode=submission)")
    ap.add_argument("--stage", choices=["draft", "submission"], default="submission")
    ap.add_argument("--audit-only", action="store_true",
                    help="Inspect only the audit without a document; a pass yields AUDIT-VALID rather than SUBMISSION-READY")
    ap.add_argument("--lang", choices=["ko", "en", "both"], default="ko")
    ap.add_argument("--names", type=Path, help="Banned residual names file")
    ap.add_argument("--palette", help="Allowed hex palette comma-list")
    ap.add_argument("--bundle", type=Path, metavar="DIR",
                    help="Submission-bundle directory; compare attachments[] file/name and sha256 with actual files")
    ap.add_argument("--skip-numbers", action="store_true",
                    help="Skip ledger/document numerical comparison (only for environments without the comparison tool; do not use for submission decisions)")
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
        audit_bytes = args.audit.read_bytes()
        data = json.loads(audit_bytes.decode("utf-8-sig"))
    except (OSError, ValueError) as exc:
        print(f"INVALID: {exc}")
        return 2
    if not isinstance(data, dict):
        print("INVALID: audit root must be an object")
        return 2
    inputs = {args.audit: hashlib.sha256(audit_bytes).hexdigest()}

    try:
        mod = _load_gate_module(gate_path)
    except (ImportError, SyntaxError, OSError) as exc:
        print(f"INVALID: cannot load proposal_gate: {exc}", file=sys.stderr)
        return 2
    try:
        schema_failures = mod.validate_schema(data)
    except Exception as exc:  # Return schema failures as usage errors rather than tracebacks.
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
    # Enforce stages: checking a submission audit under draft rules downgrades [NEEDS INPUT]
    # to warnings and falsely yields SUBMISSION-READY. Keep purpose and check strength aligned.
    if audit_mode == "submission" and args.stage != "submission":
        print(f"INVALID: audit.mode=submission인데 --stage {args.stage} — "
              "제출 audit은 --stage submission으로만 검사한다", file=sys.stderr)
        return 2

    doc_failures: list[str] = []
    if args.doc:
        if not args.doc.is_file():
            print(f"INVALID: 문서 없음: {args.doc}", file=sys.stderr)
            return 2
        try:
            inputs[args.doc] = sha256_file(args.doc)
        except OSError:
            print("INVALID: 문서를 읽을 수 없다", file=sys.stderr)
            return 2
        code, qout = run_quality_gate(args.doc, args.stage, args.lang, args.names, args.palette)
        print("=== quality_gate ===")
        print(qout.rstrip() or "(no output)")
        if code == 2:
            print("INVALID: quality_gate usage/dependency failure")
            return 2
        if code != 0:
            if _inputs_changed(inputs):
                print("INVALID: 검사 중 audit 또는 문서가 변경되었거나 읽을 수 없다. 다시 검사한다")
                return 2
            print("BLOCKED: document quality_gate failed")
            return 1
        try:
            doc_failures = bind_document(data, args.doc)
        except OSError:
            print("INVALID: 검사 중 문서를 읽을 수 없다", file=sys.stderr)
            return 2
        if audit_mode == "submission" and args.doc.suffix.lower() == ".pptx":
            code, out = run_deck_check(args.doc)
            print("=== deck_check ===")
            print(out.rstrip() or "(no output)")
            if code == 2:
                print("INVALID: deck_check usage/dependency failure")
                return 2
            if code != 0:
                doc_failures.append("실제 PPTX가 레이아웃 검사를 통과하지 못했다")
        # Compare numerical ledger values with the document; without comparison, arithmetic completion
        # becomes a self-declaration again, so run this by default when a document is supplied.
        numbers = data.get("numbers")
        if isinstance(numbers, list) and numbers and not args.skip_numbers:
            code, nout = run_check_numbers(args.doc, args.audit)
            print("=== check_numbers ===")
            print(nout.rstrip() or "(no output)")
            if code == 2:
                print("INVALID: check_numbers usage/dependency failure")
                return 2
            if code != 0:
                doc_failures.append("원장 수치가 문서 본문과 일치하지 않는다 "
                                    "— 위 check_numbers 결과를 해소한다")
        elif isinstance(numbers, list) and numbers and args.skip_numbers:
            print("=== check_numbers ===")
            print("[NOT INSPECTED] --skip-numbers로 건너뜀 — 원장과 문서가 일치하는지 확인되지 않았다")
            if audit_mode == "submission":
                doc_failures.append("--skip-numbers는 제출 판정에 쓸 수 없다 "
                                    "— 미검사는 통과가 아니다")
    elif audit_mode == "submission" and data.get("artifact_required") is True and not args.audit_only:
        doc_failures = ["제출 판정에는 실제 산출물이 필요하다 — --doc <최종파일>로 다시 실행한다 "
                        "(문서 없이 audit만 보려면 --audit-only)"]

    if audit_mode == "submission" and args.doc and not args.bundle and any(
            isinstance(a, dict) and (a.get("required", True) is not False or a.get("present") is True)
            for a in data.get("attachments", [])):
        doc_failures.append("제출에는 첨부 실물 검사가 필요하다 — --bundle <제출폴더>로 다시 실행한다")
    try:
        failures = mod.evaluate(data)
    except Exception as exc:  # GateEnvironmentError and similar environment errors, not gate decisions.
        print(f"INVALID: gate error: {exc}", file=sys.stderr)
        return 2
    if args.bundle:
        if not args.bundle.is_dir():
            print(f"INVALID: 묶음 폴더 없음: {args.bundle}", file=sys.stderr)
            return 2
        try:
            bundle_problems = verify_bundle(data, args.bundle)
        except OSError:
            print("INVALID: 첨부 파일을 읽을 수 없다", file=sys.stderr)
            return 2
        print("=== bundle ===")
        print("\n".join(f"- {p}" for p in bundle_problems)
              or f"첨부 해시가 모두 일치한다 ({args.bundle})")
        doc_failures.extend(bundle_problems)
    # Bind the verdict to the bytes loaded/checked, not just to an earlier hash observation.
    if _inputs_changed(inputs):
        print("INVALID: 검사 중 audit 또는 문서가 변경되었거나 읽을 수 없다. 다시 검사한다")
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

    # Merge document comparison failures into gate blockers so labels and exit codes agree.
    failures = list(failures) + doc_failures

    # Derive labels only from proposal_gate.readiness so CLI, explanations, and scores
    # share one decision; separate calculations previously contradicted explanations.
    if hasattr(mod, "readiness"):
        display, exit_code = mod.readiness(data, failures)
    else:  # Compatibility with older proposal_gate versions.
        label, exit_code = classify(str(decision), failures)
        display = "SUBMISSION-READY" if label == "READY" and audit_mode == "submission" else \
            (f"{audit_mode.upper() or 'DRAFT'}-READY" if label == "READY" else label)
    if display == "SUBMISSION-READY" and not args.doc:
        # --audit-only does not inspect actual files and must not claim submission readiness.
        display = "AUDIT-VALID"
        print("NOTE: 문서 미검사(--audit-only) — audit 자체만 유효하다. "
              "제출 판정은 --doc <최종파일>로 다시 받는다.")
    if args.stage == "submission" and audit_mode != "submission":
        print(f"NOTE: audit.mode={audit_mode!r} — 제출 판정이 아니다. "
              "제출 게이트는 mode=submission audit으로 다시 실행한다.")
    print(f"=== proposal_gate → {display} ===")
    if explain and hasattr(mod, "explain_markdown"):
        # Pass the final display decision unchanged into explanations. Recalculation from the audit
        # could print submission-ready prose beside STATUS: AUDIT-VALID.
        try:
            print(mod.explain_markdown(data, [], failures, display))
        except TypeError:  # Compatibility with older proposal_gate versions.
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
