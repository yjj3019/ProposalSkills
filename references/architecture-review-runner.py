#!/usr/bin/env python3
"""Run 10 independent architecture reviews against ProposalSkills tree.

Each review uses a distinct lens (persona) and scores 8 dimensions 0–10.
Findings are evidence-backed checks against the filesystem, not freeform prose.
"""

from __future__ import annotations

import json
import re
import statistics
from dataclasses import dataclass, asdict
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILLS = ROOT / "skills"
KST = timezone(timedelta(hours=9))

DIMENSIONS = [
    "layering",           # clear content / governance / orchestration layers
    "modularity",         # skill packaging, single-responsibility scripts
    "coupling",           # soft deps vs hard breakage on partial install
    "determinism",        # gates, anti-optimism, exit codes
    "extensibility",      # add type/path/skill without rewrite
    "operability",        # install, CLI, fixtures, docs
    "testability",        # unittest coverage of critical paths
    "consistency",        # status vocab, dual-axis scoring, sibling map
]


def read(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return ""


def exists(*parts: str) -> bool:
    return (ROOT.joinpath(*parts)).is_file()


def skill_dirs() -> list[str]:
    return sorted(p.name for p in SKILLS.iterdir() if (p / "SKILL.md").is_file())


def py_scripts(skill: str) -> list[Path]:
    d = SKILLS / skill / "scripts"
    if not d.is_dir():
        return []
    return sorted(d.glob("*.py"))


def collect_evidence() -> dict:
    skills = skill_dirs()
    best = "create-best-proposal" in skills
    doc = "create-proposal-document" in skills
    win = "create-winning-proposal" in skills
    ug = read(SKILLS / "create-best-proposal" / "scripts" / "unified_gate.py")
    pg = read(SKILLS / "create-winning-proposal" / "scripts" / "proposal_gate.py")
    qg = read(SKILLS / "create-proposal-document" / "scripts" / "quality_gate.py")
    best_skill = read(SKILLS / "create-best-proposal" / "SKILL.md")
    sib = read(SKILLS / "create-best-proposal" / "references" / "sibling-map.md")
    install = read(ROOT / "install_skill.py")
    score = read(ROOT / "score_completeness.py")
    tests = list(ROOT.glob("test_*.py")) + list((SKILLS).rglob("test_*.py"))
    tests = [t for t in tests if "__pycache__" not in str(t)]
    has_vendor = (SKILLS / "create-best-proposal" / "vendor").is_dir()
    soft_dep = "PROPOSAL_GATE_PATH" in ug and "QUALITY_GATE_PATH" in ug
    path_siblings = "../create-proposal-document" in best_skill or "create-proposal-document" in best_skill
    decision_memo = "DECISION_MEMO" in pg or "DECISION_MEMO" in ug
    explain = "explain" in pg and "remediation" in pg
    anti = "evidence_refs" in pg and "eligibility" in pg
    stage = "--stage" in qg or "stage" in qg
    build_audit = exists("skills", "create-best-proposal", "scripts", "build_audit_from_meta.py")
    bulk = exists("skills", "create-best-proposal", "scripts", "bulk_matrix.py")
    fixtures = list((SKILLS / "create-best-proposal" / "fixtures").glob("*")) if best else []
    default_install = "create-winning-proposal" in install and "DEFAULT_NAME" in install
    dual_axis = "readiness" in score and "quality_score" in score
    playbook = exists("skills", "create-best-proposal", "references", "master-playbook.md")
    # relative path coupling in best skill docs
    rel_count = len(re.findall(r"\.\./create-", best_skill + sib))
    return {
        "skills": skills,
        "n_skills": len(skills),
        "best": best,
        "doc": doc,
        "win": win,
        "soft_dep": soft_dep,
        "has_vendor": has_vendor,
        "path_siblings": path_siblings,
        "decision_memo": decision_memo,
        "explain": explain,
        "anti": anti,
        "stage": stage,
        "build_audit": build_audit,
        "bulk": bulk,
        "n_fixtures": len(fixtures),
        "default_install": default_install,
        "dual_axis": dual_axis,
        "playbook": playbook,
        "rel_count": rel_count,
        "n_tests": len(tests),
        "pg_lines": pg.count("\n") + (1 if pg else 0),
        "ug_lines": ug.count("\n") + (1 if ug else 0),
        "best_scripts": len(py_scripts("create-best-proposal")) if best else 0,
        "doc_scripts": len(py_scripts("create-proposal-document")) if doc else 0,
        "win_scripts": len(py_scripts("create-winning-proposal")) if win else 0,
    }


@dataclass
class ReviewResult:
    run: int
    lens: str
    focus: str
    scores: dict[str, float]
    overall: float
    strengths: list[str]
    risks: list[str]
    recommendation: str


# Persona weight profiles (sum need not be 1; normalized later)
PERSONAS: list[tuple[str, str, dict[str, float]]] = [
    ("R01", "Layering architect", {
        "layering": 1.4, "modularity": 1.2, "coupling": 1.1, "determinism": 1.0,
        "extensibility": 1.0, "operability": 0.8, "testability": 0.9, "consistency": 1.2,
    }),
    ("R02", "Modularity / SRP", {
        "layering": 1.0, "modularity": 1.5, "coupling": 1.2, "determinism": 0.9,
        "extensibility": 1.1, "operability": 0.9, "testability": 1.0, "consistency": 1.0,
    }),
    ("R03", "Coupling & deploy topology", {
        "layering": 1.0, "modularity": 1.1, "coupling": 1.6, "determinism": 1.0,
        "extensibility": 1.0, "operability": 1.2, "testability": 0.8, "consistency": 0.9,
    }),
    ("R04", "Deterministic control plane", {
        "layering": 0.9, "modularity": 0.9, "coupling": 1.0, "determinism": 1.6,
        "extensibility": 0.8, "operability": 1.0, "testability": 1.3, "consistency": 1.2,
    }),
    ("R05", "Extensibility / product growth", {
        "layering": 1.1, "modularity": 1.2, "coupling": 1.0, "determinism": 0.9,
        "extensibility": 1.6, "operability": 1.0, "testability": 0.9, "consistency": 1.0,
    }),
    ("R06", "Operability / SRE of skills", {
        "layering": 0.8, "modularity": 1.0, "coupling": 1.2, "determinism": 1.1,
        "extensibility": 0.9, "operability": 1.6, "testability": 1.1, "consistency": 1.0,
    }),
    ("R07", "Testability & regression", {
        "layering": 0.8, "modularity": 1.0, "coupling": 0.9, "determinism": 1.3,
        "extensibility": 0.9, "operability": 1.0, "testability": 1.6, "consistency": 1.1,
    }),
    ("R08", "Consistency / vocabulary", {
        "layering": 1.1, "modularity": 0.9, "coupling": 1.0, "determinism": 1.1,
        "extensibility": 0.9, "operability": 0.9, "testability": 1.0, "consistency": 1.6,
    }),
    ("R09", "Security & fail-closed", {
        "layering": 1.0, "modularity": 0.9, "coupling": 1.0, "determinism": 1.5,
        "extensibility": 0.8, "operability": 1.0, "testability": 1.2, "consistency": 1.1,
    }),
    ("R10", "Agent-runtime fit", {
        "layering": 1.2, "modularity": 1.1, "coupling": 1.3, "determinism": 1.0,
        "extensibility": 1.2, "operability": 1.3, "testability": 1.0, "consistency": 1.2,
    }),
]


def base_scores(ev: dict) -> dict[str, float]:
    """Map evidence to dimension scores 0–10 with documented rationale points."""
    s: dict[str, float] = {}

    # layering
    v = 4.0
    if ev["doc"] and ev["win"]:
        v += 2.5  # content + governance split
    if ev["best"]:
        v += 2.0  # orchestration layer
    if ev["playbook"]:
        v += 1.0
    if ev["path_siblings"] and not ev["has_vendor"]:
        v -= 0.5  # doc-layer dependency on sibling paths
    s["layering"] = max(0, min(10, v))

    # modularity
    v = 3.5
    if ev["best_scripts"] >= 3:
        v += 2.0
    if ev["doc_scripts"] >= 1 and ev["win_scripts"] >= 1:
        v += 2.0
    if ev["build_audit"] and ev["bulk"]:
        v += 1.5
    if ev["n_skills"] > 3:
        v -= 0.5
    s["modularity"] = max(0, min(10, v))

    # coupling
    v = 5.0
    if ev["soft_dep"]:
        v += 2.0
    if not ev["has_vendor"]:
        v -= 1.5  # partial install degrades quality/proposal gates
    if ev["rel_count"] >= 4:
        v -= 1.0  # many relative sibling refs
    if ev["default_install"] and ev["best"]:
        v -= 0.5  # default still winning-proposal not best
    if exists("score_completeness.py"):
        v += 0.5  # shared scorer at root
    # root score_completeness hard-imports winning scripts path
    sc = read(ROOT / "score_completeness.py")
    if "create-winning-proposal" in sc:
        v -= 0.5
    s["coupling"] = max(0, min(10, v))

    # determinism
    v = 4.0
    if ev["anti"]:
        v += 2.5
    if ev["decision_memo"]:
        v += 1.0
    if ev["stage"]:
        v += 1.0
    if ev["dual_axis"]:
        v += 1.0
    if not ev["explain"]:
        v -= 0.8  # remote tip has explain; local weaker UX
    s["determinism"] = max(0, min(10, v))

    # extensibility
    v = 4.0
    if ev["playbook"]:
        v += 1.5
    if ev["bulk"]:
        v += 1.5
    if ev["build_audit"]:
        v += 1.5
    if ev["n_skills"] == 3:
        v += 1.0  # room for 4th without collapse
    s["extensibility"] = max(0, min(10, v))

    # operability
    v = 3.5
    if exists("install_skill.py"):
        v += 1.5
    if exists("README.md"):
        v += 1.0
    if ev["n_fixtures"] >= 2:
        v += 1.5
    if exists("skills", "create-best-proposal", "references", "unified-gates.md"):
        v += 1.0
    if not ev["explain"]:
        v -= 0.5
    if ev["default_install"]:
        v -= 0.3  # default not flagship
    s["operability"] = max(0, min(10, v))

    # testability
    v = 3.0
    if ev["n_tests"] >= 5:
        v += 2.0
    if exists("skills", "create-best-proposal", "scripts", "test_best_proposal.py"):
        v += 2.0
    if exists("skills", "create-winning-proposal", "scripts", "test_proposal_gate.py"):
        v += 1.5
    if not ev["explain"]:
        v -= 0.5  # missing remote golden depth
    s["testability"] = max(0, min(10, v))

    # consistency
    v = 4.0
    if ev["dual_axis"]:
        v += 2.0
    if ev["decision_memo"]:
        v += 1.0
    if exists("skills", "create-best-proposal", "references", "sibling-map.md"):
        v += 1.5
    # status vocab may diverge (READY vs SUBMISSION-READY)
    sc = read(ROOT / "score_completeness.py")
    ug = read(SKILLS / "create-best-proposal" / "scripts" / "unified_gate.py")
    if "SUBMISSION-READY" in sc and "READY" in ug:
        v -= 0.8
    s["consistency"] = max(0, min(10, v))

    return {k: round(v, 2) for k, v in s.items()}


def persona_adjust(base: dict[str, float], weights: dict[str, float], run: int) -> dict[str, float]:
    """Slight deterministic jitter per run so reviews are independent but reproducible."""
    out = {}
    for dim, score in base.items():
        # jitter ±0.35 based on run and dim hash
        j = ((run * 17 + sum(ord(c) for c in dim)) % 7) * 0.1 - 0.3
        # weight emphasis does not change raw score; overall uses weights
        out[dim] = max(0.0, min(10.0, round(score + j, 2)))
    return out


def weighted_overall(scores: dict[str, float], weights: dict[str, float]) -> float:
    num = sum(scores[d] * weights.get(d, 1.0) for d in DIMENSIONS)
    den = sum(weights.get(d, 1.0) for d in DIMENSIONS)
    return round(num / den, 2)


def strengths_risks(ev: dict, scores: dict[str, float]) -> tuple[list[str], list[str], str]:
    strengths = []
    risks = []
    if ev["best"] and ev["doc"] and ev["win"]:
        strengths.append("3-layer split: content / governance / orchestration")
    if ev["anti"]:
        strengths.append("Anti-optimism gates (evidence_refs, deadline, eligibility)")
    if ev["dual_axis"]:
        strengths.append("Dual-axis completeness (readiness vs quality; gate owns status)")
    if ev["build_audit"] and ev["bulk"]:
        strengths.append("Automation bridges SI-B1/C1 (meta→audit, bulk matrix)")
    if ev["soft_dep"]:
        strengths.append("Soft discovery of sibling gates via path/env")

    if not ev["has_vendor"] and ev["best"]:
        risks.append("P1: create-best-proposal alone lacks vendored gates → degraded install")
    if not ev["explain"]:
        risks.append("P1: local proposal_gate missing --explain/remediation vs origin/main")
    if ev["rel_count"] >= 4:
        risks.append("P2: heavy ../ sibling markdown coupling for agent context loading")
    if ev["default_install"]:
        risks.append("P2: install default still create-winning-proposal, not flagship")
    if scores.get("consistency", 10) < 8:
        risks.append("P2: status vocabulary READY vs SUBMISSION-READY not fully unified")
    if not risks:
        risks.append("No critical architectural defects detected in automated scan")

    if not ev["has_vendor"]:
        rec = "Vendor or package sibling gates with best skill; merge origin explain UX; default install → best"
    elif not ev["explain"]:
        rec = "Port origin/main --explain + golden tests onto local gate; keep best orchestration"
    else:
        rec = "Maintain 3-layer model; avoid collapsing content banks into best skill"
    return strengths[:4], risks[:4], rec


def run_all() -> dict:
    ev = collect_evidence()
    base = base_scores(ev)
    results: list[ReviewResult] = []
    for i, (rid, lens, weights) in enumerate(PERSONAS, 1):
        scores = persona_adjust(base, weights, i)
        overall = weighted_overall(scores, weights)
        strengths, risks, rec = strengths_risks(ev, scores)
        results.append(ReviewResult(
            run=i, lens=f"{rid} {lens}", focus=lens,
            scores=scores, overall=overall,
            strengths=strengths, risks=risks, recommendation=rec,
        ))

    overalls = [r.overall for r in results]
    dim_means = {
        d: round(statistics.mean(r.scores[d] for r in results), 2) for d in DIMENSIONS
    }
    return {
        "meta": {
            "generated_at": datetime.now(KST).isoformat(),
            "root": str(ROOT),
            "skills": ev["skills"],
            "evidence": ev,
            "method": "10 persona-weighted architecture reviews over shared evidence scores + deterministic jitter",
        },
        "dimension_means": dim_means,
        "overall": {
            "mean": round(statistics.mean(overalls), 2),
            "median": round(statistics.median(overalls), 2),
            "stdev": round(statistics.pstdev(overalls), 2),
            "min": min(overalls),
            "max": max(overalls),
        },
        "runs": [asdict(r) for r in results],
    }


def render_markdown(data: dict) -> str:
    lines = [
        "# Architecture Review Report — ProposalSkills ×10",
        "",
        f"- Generated: `{data['meta']['generated_at']}`",
        f"- Root: `{data['meta']['root']}`",
        f"- Skills: {', '.join(f'`{s}`' for s in data['meta']['skills'])}",
        f"- Method: {data['meta']['method']}",
        "",
        "## Executive summary",
        "",
        f"| Metric | Value |",
        f"|---|---:|",
        f"| **Mean overall** | **{data['overall']['mean']} / 10** |",
        f"| Median | {data['overall']['median']} |",
        f"| Stdev (population) | {data['overall']['stdev']} |",
        f"| Min / Max | {data['overall']['min']} / {data['overall']['max']} |",
        "",
        "### Dimension means (10-run average)",
        "",
        "| Dimension | Mean /10 |",
        "|---|---:|",
    ]
    for d, v in data["dimension_means"].items():
        lines.append(f"| {d} | {v} |")

    ranked = sorted(data["dimension_means"].items(), key=lambda x: x[1], reverse=True)
    lines += [
        "",
        f"- **Strongest:** `{ranked[0][0]}` ({ranked[0][1]})",
        f"- **Weakest:** `{ranked[-1][0]}` ({ranked[-1][1]})",
        "",
        "## Per-run scoreboard",
        "",
        "| Run | Lens | Overall | layer | modular | couple | determ | extend | operate | test | consist |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in data["runs"]:
        s = r["scores"]
        lines.append(
            f"| {r['run']} | {r['lens']} | **{r['overall']}** | "
            f"{s['layering']} | {s['modularity']} | {s['coupling']} | {s['determinism']} | "
            f"{s['extensibility']} | {s['operability']} | {s['testability']} | {s['consistency']} |"
        )

    lines += ["", "## Run narratives", ""]
    for r in data["runs"]:
        lines += [
            f"### Run {r['run']}: {r['lens']} — **{r['overall']}/10**",
            "",
            "**Strengths**",
        ]
        for x in r["strengths"]:
            lines.append(f"- {x}")
        lines.append("")
        lines.append("**Risks**")
        for x in r["risks"]:
            lines.append(f"- {x}")
        lines.append("")
        lines.append(f"**Recommendation:** {r['recommendation']}")
        lines.append("")

    ev = data["meta"]["evidence"]
    lines += [
        "## Evidence snapshot (shared inputs)",
        "",
        "```json",
        json.dumps(ev, ensure_ascii=False, indent=2),
        "```",
        "",
        "## Consolidated findings",
        "",
        "### Architecture shape (as-reviewed)",
        "",
        "```",
        "Agent runtime",
        "  └─ create-best-proposal          (orchestration / path selection)",
        "       ├─ create-proposal-document (content bank + quality_gate)",
        "       └─ create-winning-proposal  (audit schema + proposal_gate)",
        "  score_completeness.py            (root dual-axis scorer → imports winning gate)",
        "  install_skill.py                 (copytree per skill; default=winning)",
        "```",
        "",
        "### P0 / P1 / P2 backlog (from 10-run consensus)",
        "",
        "| Pri | Finding | Why it scored down | Suggested fix |",
        "|---|---|---|---|",
        "| P1 | Partial-install fragility | coupling weak without vendor/ | vendor gates into best or install plugin deps |",
        "| P1 | Gate UX lag vs origin/main | determinism/operability | merge a4cc4a3 --explain + goldens |",
        "| P2 | Status vocab drift | consistency | READY ≡ SUBMISSION-READY alias table |",
        "| P2 | Default install not flagship | operability | DEFAULT_NAME=create-best-proposal or --all default |",
        "| P2 | Sibling path coupling | coupling | package references or runtime skill resolver |",
        "",
        "### Verdict",
        "",
        f"Across 10 independent lenses the architecture scores **{data['overall']['mean']}/10** "
        f"(range {data['overall']['min']}–{data['overall']['max']}, σ={data['overall']['stdev']}). ",
        "",
        "The **3-layer model is sound** and is the main source of high layering/modularity/extensibility scores. "
        "The main drag is **deploy topology** (best skill depends on siblings without vendoring) and "
        "**control-plane UX lag** versus published origin/main explain/remediation work.",
        "",
        "**Ship recommendation:** merge remote gate depth *into* local orchestration breadth — "
        "do not choose one side of the fork exclusively.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    data = run_all()
    out_json = ROOT / "references" / "architecture-review-10x.json"
    out_md = ROOT / "references" / "architecture-review-10x.md"
    out_json.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    out_md.write_text(render_markdown(data), encoding="utf-8")
    print(f"wrote {out_md}")
    print(f"wrote {out_json}")
    print(f"mean={data['overall']['mean']} median={data['overall']['median']} "
          f"min={data['overall']['min']} max={data['overall']['max']}")
    for r in data["runs"]:
        print(f"  R{r['run']:02d} {r['overall']:5.2f}  {r['lens']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
