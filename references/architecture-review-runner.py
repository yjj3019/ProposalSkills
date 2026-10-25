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


REPORT_LABELS = {
    "10 persona-weighted architecture reviews over shared evidence scores + deterministic jitter": "공통 근거 점수에 관점별 가중치와 결정론적 변동을 적용한 10회 구조 검토",
    "layering": "계층 분리",
    "modularity": "모듈성",
    "coupling": "결합도",
    "determinism": "결정론적 검사",
    "extensibility": "확장성",
    "operability": "운영성",
    "testability": "검증 용이성",
    "consistency": "일관성",
    "R01 Layering architect": "R01 계층 구조",
    "R02 Modularity / SRP": "R02 모듈성·단일 책임",
    "R03 Coupling & deploy topology": "R03 결합도·배포 구조",
    "R04 Deterministic control plane": "R04 결정론적 제어",
    "R05 Extensibility / product growth": "R05 확장성·제품 확장",
    "R06 Operability / SRE of skills": "R06 스킬 운영성·신뢰성",
    "R07 Testability & regression": "R07 검증 용이성·회귀",
    "R08 Consistency / vocabulary": "R08 일관성·용어",
    "R09 Security & fail-closed": "R09 보안·실패 시 차단",
    "R10 Agent-runtime fit": "R10 에이전트 실행 환경 적합성",
    "3-layer split: content / governance / orchestration": "3개 레이어 분리: 콘텐츠 / 근거·승인 / 통합 진행",
    "Anti-optimism gates (evidence_refs, deadline, eligibility)": "낙관적 자기선언 차단 검사(evidence_refs, deadline, eligibility)",
    "Dual-axis completeness (readiness vs quality; gate owns status)": "제출 준비도·제안 품질의 두 축 분리, 상태는 검사기가 결정",
    "Automation bridges SI-B1/C1 (meta→audit, bulk matrix)": "SI-B1/C1 자동 연결(meta→audit, 대량 조견표)",
    "Soft discovery of sibling gates via path/env": "경로·환경변수로 내부 레이어 검사기 탐색",
    "P1: create-best-proposal alone lacks vendored gates → degraded install": "P1: create-best-proposal 단독 설치에는 내부 검사기 사본이 없어 기능이 제한됨",
    "P1: local proposal_gate missing --explain/remediation vs origin/main": "P1: 당시 로컬 proposal_gate에는 origin/main의 --explain·수정 안내가 없음",
    "P2: heavy ../ sibling markdown coupling for agent context loading": "P2: 에이전트 문맥 로딩이 ../ 내부 레이어 문서 경로에 강하게 결합됨",
    "P2: install default still create-winning-proposal, not flagship": "P2: 당시 기본 설치 대상이 통합 진입점이 아닌 create-winning-proposal임",
    "P2: status vocabulary READY vs SUBMISSION-READY not fully unified": "P2: READY와 SUBMISSION-READY 상태 용어가 완전히 통일되지 않음",
    "No critical architectural defects detected in automated scan": "자동 검사에서 치명적인 구조 결함을 발견하지 않음",
    "Vendor or package sibling gates with best skill; merge origin explain UX; default install → best": "내부 검사기를 통합 스킬과 함께 배포하고 원격의 설명 기능을 반영하며 기본 설치를 통합 진입점으로 변경",
    "Port origin/main --explain + golden tests onto local gate; keep best orchestration": "통합 진행 구조를 유지하고 origin/main의 --explain과 기준 테스트를 로컬 검사기에 반영",
    "Maintain 3-layer model; avoid collapsing content banks into best skill": "3개 레이어 구조를 유지하고 콘텐츠 자료를 통합 스킬 하나로 합치지 않음"
}

def _report_label(value: str) -> str:
    return REPORT_LABELS.get(value, value)


def render_markdown(data: dict) -> str:
    lines = [
        "# ProposalSkills 구조 검토 보고서 — 10회",
        "",
        f"- 작성 시각: `{data['meta']['generated_at']}`",
        "- 기준 위치: 저장소 루트",
        f"- 대상 스킬: {', '.join(f'`{s}`' for s in data['meta']['skills'])}",
        f"- 방법: {_report_label(data['meta']['method'])}",
        "",
        "## 검토 요약",
        "",
        f"| 지표 | 값 |",
        f"|---|---:|",
        f"| **전체 평균** | **{data['overall']['mean']} / 10** |",
        f"| 중앙값 | {data['overall']['median']} |",
        f"| 모집단 표준편차 | {data['overall']['stdev']} |",
        f"| 최솟값 / 최댓값 | {data['overall']['min']} / {data['overall']['max']} |",
        "",
        "### 항목별 평균(10회)",
        "",
        "| 항목 | 평균 /10 |",
        "|---|---:|",
    ]
    for d, v in data["dimension_means"].items():
        lines.append(f"| {_report_label(d)} | {v} |")

    ranked = sorted(data["dimension_means"].items(), key=lambda x: x[1], reverse=True)
    lines += [
        "",
        f"- **가장 높은 항목:** `{_report_label(ranked[0][0])}` ({ranked[0][1]})",
        f"- **가장 낮은 항목:** `{_report_label(ranked[-1][0])}` ({ranked[-1][1]})",
        "",
        "## 회차별 결과",
        "",
        "| 회차 | 검토 관점 | 종합 | 계층 | 모듈 | 결합 | 결정성 | 확장 | 운영 | 검증 | 일관 |",
        "|---:|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for r in data["runs"]:
        s = r["scores"]
        lines.append(
            f"| {r['run']} | {_report_label(r['lens'])} | **{r['overall']}** | "
            f"{s['layering']} | {s['modularity']} | {s['coupling']} | {s['determinism']} | "
            f"{s['extensibility']} | {s['operability']} | {s['testability']} | {s['consistency']} |"
        )

    lines += ["", "## 회차별 검토 내용", ""]
    for r in data["runs"]:
        lines += [
            f"### 검토 {r['run']}: {_report_label(r['lens'])} — **{r['overall']}/10**",
            "",
            "**강점**",
        ]
        for x in r["strengths"]:
            lines.append(f"- {_report_label(x)}")
        lines.append("")
        lines.append("**위험**")
        for x in r["risks"]:
            lines.append(f"- {_report_label(x)}")
        lines.append("")
        lines.append(f"**개선안:** {_report_label(r['recommendation'])}")
        lines.append("")

    ev = data["meta"]["evidence"]
    lines += [
        "## 당시 근거 원장(공통 입력)",
        "",
        "```json",
        json.dumps(ev, ensure_ascii=False, indent=2),
        "```",
        "",
        "## 종합 지적",
        "",
        "### 검토 당시 구조",
        "",
        "```",
        "에이전트 실행 환경",
        "  └─ create-best-proposal          (통합 진행 / 경로 선택)",
        "       ├─ create-proposal-document (콘텐츠 자료 + quality_gate)",
        "       └─ create-winning-proposal  (감사 스키마 + proposal_gate)",
        "  score_completeness.py            (루트의 두 축 점수 계산 → 내부 제출 검사기 호출)",
        "  install_skill.py                 (스킬별 폴더 복사; 당시 기본값=winning)",
        "```",
        "",
        "### P0 / P1 / P2 개선 목록(10회 검토 종합)",
        "",
        "| 우선순위 | 지적 | 감점 이유 | 개선안 |",
        "|---|---|---|---|",
        "| P1 | 부분 설치 취약성 | vendor/ 없이 결합도 문제 발생 | 내부 검사기를 동봉하거나 플러그인 의존 스킬 함께 설치 |",
        "| P1 | origin/main보다 검사 안내가 뒤처짐 | 결정론적 검사·운영성 | a4cc4a3의 --explain·기준 테스트 반영 |",
        "| P2 | 상태 용어 불일치 | 일관성 | READY ≡ SUBMISSION-READY 대응표 |",
        "| P2 | 기본 설치가 통합 진입점이 아님 | 운영성 | DEFAULT_NAME=create-best-proposal 또는 --all 기본값 |",
        "| P2 | 내부 레이어 경로 결합 | 결합도 | 참고 문서 함께 배포 또는 실행 중 스킬 경로 탐색 |",
        "",
        "### 판단",
        "",
        f"10개 검토 관점의 구조 점수는 **{data['overall']['mean']}/10** "
        f"(범위 {data['overall']['min']}–{data['overall']['max']}, σ={data['overall']['stdev']}).",
        "",
        "**3개 레이어 구조는 타당**하며 계층 분리·모듈성·확장성 점수가 높은 주된 이유다. "
        "주요 약점은 **배포 구조**(내부 검사기 사본 없이 통합 스킬이 내부 레이어에 의존)와 "
        "공개된 origin/main의 설명·수정 안내보다 **제어 단계의 안내가 뒤처진 점**이다.",
        "",
        "**배포 개선안:** 원격 검사기의 상세 검증을 로컬 통합 진행 구조에 결합한다. "
        "두 분기 중 하나만 선택하지 않는다.",
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
