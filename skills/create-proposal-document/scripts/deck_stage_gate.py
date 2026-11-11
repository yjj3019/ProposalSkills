#!/usr/bin/env python3
"""Gate a deck workspace by stage: brief, approved design spec, page plan, slides.json.

Building a deck in one shot hides decisions nobody approved. This gate checks a workspace folder that holds a
`stages.json` manifest and fails closed when a stage is missing, when the design spec was not approved or was
edited after approval, or when the page plan and `slides.json` disagree.

stages.json:
  {"route": "generate|template|edit|quick",
   "stages": {"brief":       {"file": "brief.md"},
              "design_spec": {"file": "design_spec.md", "approved_by": "<real name>", "approved_sha256": "<hex>"},
              "page_plan":   {"file": "page_plan.json"},
              "slides":      {"file": "slides.json"}}}
page_plan.json: {"slides": [{"id": "S1", "action_title": "<one claim per slide>", "req_ids": []}]}
  A row may set "prescribed": true when the buyer's RFP fixes the section name (common in Korean public bids); the
  label check is skipped for that row only.

Rules
  - generate/template need all four stages; edit needs slides; quick needs brief and slides (no approval gate).
  - generate/template: design_spec approval is BLOCKING. approved_sha256 must equal the file's current SHA-256, so
    any edit after approval invalidates it.
  - Each plan title must be a claim, not a topic label (too short or a bare label such as "개요"/"Overview").
  - Content slides in slides.json (not cover/toc/section/closing) must carry the plan titles, in order.

Exit codes: 0 pass, 1 blocked, 2 usage error. Approval here is a recorded fact, not authentication.

Usage: python deck_stage_gate.py WORKSPACE_DIR
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

ROUTES = {"generate": ("brief", "design_spec", "page_plan", "slides"),
          "template": ("brief", "design_spec", "page_plan", "slides"),
          "edit": ("slides",), "quick": ("brief", "slides")}
APPROVAL_ROUTES = {"generate", "template"}
STRUCTURAL = {"cover", "toc", "section", "closing"}
LABELS = {"개요", "현황", "결론", "목차", "배경", "소개", "요약", "overview", "summary", "conclusion",
          "introduction", "agenda", "background", "contents"}
MIN_TITLE = 12


def norm(text: str) -> str:
    return re.sub(r"\s+", " ", str(text)).strip()


def load_json(path: Path, problems: list[str], label: str):
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except (OSError, ValueError) as exc:
        problems.append(f"{label}: cannot read ({type(exc).__name__})")
        return None


def check(workspace: Path) -> list[str]:
    problems: list[str] = []
    manifest = load_json(workspace / "stages.json", problems, "stages.json")
    if not isinstance(manifest, dict):
        return problems or ["stages.json must be an object"]
    route = manifest.get("route")
    if route not in ROUTES:
        return [f"route must be one of {sorted(ROUTES)}"]
    stages = manifest.get("stages") if isinstance(manifest.get("stages"), dict) else {}
    files: dict[str, Path] = {}
    for name in ROUTES[route]:
        entry = stages.get(name)
        rel = entry.get("file") if isinstance(entry, dict) else None
        target = (workspace / rel).resolve() if isinstance(rel, str) and rel else None
        if target is None or workspace.resolve() not in target.parents:
            problems.append(f"stage {name}: file missing from manifest or outside the workspace")
        elif not target.is_file():
            problems.append(f"stage {name}: {rel} does not exist")
        else:
            files[name] = target
    if route in APPROVAL_ROUTES and "design_spec" in files:
        entry = stages["design_spec"]
        digest = hashlib.sha256(files["design_spec"].read_bytes()).hexdigest()
        if not norm(entry.get("approved_by", "")):
            problems.append("design_spec: not approved (approved_by is empty); this gate is blocking")
        elif str(entry.get("approved_sha256", "")).lower() != digest:
            problems.append("design_spec: changed after approval (approved_sha256 does not match the file)")
    plan = None
    if "page_plan" in files:
        plan = load_json(files["page_plan"], problems, "page_plan")
        rows = plan.get("slides") if isinstance(plan, dict) else None
        if not isinstance(rows, list) or not rows:
            problems.append("page_plan: needs a non-empty slides list")
            plan = None
        else:
            for row in rows:
                title = norm(row.get("action_title", "")) if isinstance(row, dict) else ""
                prescribed = isinstance(row, dict) and row.get("prescribed") is True
                if not prescribed and (len(title) < MIN_TITLE or title.lower() in LABELS):
                    problems.append(f"page_plan {row.get('id', '?') if isinstance(row, dict) else '?'}: "
                                    f"action_title is a label, not a claim: {title!r}")
    if plan and "slides" in files:
        deck = load_json(files["slides"], problems, "slides")
        slides = deck.get("slides") if isinstance(deck, dict) else None
        if isinstance(slides, list):
            deck_titles = [norm(s.get("title", "")) for s in slides
                           if isinstance(s, dict) and s.get("type") not in STRUCTURAL]
            plan_titles = [norm(r.get("action_title", "")) for r in plan["slides"] if isinstance(r, dict)]
            if deck_titles != plan_titles:
                problems.append(f"slides.json content titles do not match page_plan ({len(deck_titles)} vs {len(plan_titles)}, or order/text differs)")
        else:
            problems.append("slides.json: needs a slides list")
    return problems


def main(argv: list[str] | None = None) -> int:
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or not Path(args[0]).is_dir():
        print(__doc__, file=sys.stderr)
        return 2
    problems = check(Path(args[0]))
    for problem in problems:
        print(f"[BLOCKED] {problem}")
    print(f"DECK-STAGE-GATE: {'BLOCKED' if problems else 'PASS'} ({len(problems)} problem(s))")
    return 1 if problems else 0


if __name__ == "__main__":
    sys.exit(main())
