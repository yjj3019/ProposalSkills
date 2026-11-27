#!/usr/bin/env python3
"""Measure with a real model whether each skill's description makes it trigger, and whether near misses leave it alone.

`test_skill_triggers.py` is an offline lint: it checks that a description still carries the words real requests use. It does not
show what a model does. This runs each prompt in `references/trigger-eval-cases.json` through a headless agent CLI several times
and records which of this repository's skills the model used.

    python trigger_eval_run.py                                # prints the plan and exits 3; nothing is sent
    python trigger_eval_run.py --yes                          # Claude Code, 3 runs per prompt
    python trigger_eval_run.py --yes --host all --runs 3 --max-invocations 200 --report trigger-report.json
    python trigger_eval_run.py --yes --host codex --skill create-best-proposal
    python trigger_eval_run.py --yes --host all --kind near-miss --max-invocations 100
    python trigger_eval_run.py --yes --host all --kind positive --control neutral-descriptions   # is it the description or browsing?

Hosts: `claude` (Claude Code), `codex` (OpenAI Codex CLI), `grok` (Grok Build). Each run gets a fresh temporary workspace, and the
descriptions under test are the ones in THIS checkout. A prompt that should trigger a skill gets a synthetic `rfp.md` (the repository's
mini-RFP fixture) so the model has something to work on; a near-miss prompt gets a workspace without it, because a proposal file
there makes a model read the proposal skill whatever it was asked: claude loads the
checkout as a session-only plugin (`--plugin-dir`), so its skills are not files in the workspace to browse; codex and grok have no such
option, so the current skills are copied into `.agents/skills` of the workspace. Grok is started with `--trust` for that temporary folder
only, because it ignores project skills in untrusted folders. No real file is read.

What counts as "used" (the first of the first --max-calls tool calls decides; a run that ends or times out earlier decides on what it
did):
  claude  a Skill tool call naming the skill (a plugin prefix such as `proposal-skills:` is accepted). Reading a `SKILL.md` while
          browsing the workspace is not counted: Claude has a Skill tool, so only that call is use
  codex   a command that names `<skill>/SKILL.md` (Codex loads a skill by reading its file; its sentence "I'll use the X skill" is
          not counted because a refusal can use the same words)
  grok    a tool call whose input names `<skill>/SKILL.md`
A `should_trigger` prompt passes when its skill, or the entry skill, is used in at least --min-rate of the completed runs. The entry
skill is the one without `disable-model-invocation`: the other two are explicit-only by design, so a model that answers "use
create-proposal-document" through the entry skill behaves as designed. A `should_not_trigger` prompt passes when no repository skill
is used in more than --max-false-rate of the runs. A run that produced events but did not finish in --timeout counts as "no skill
used by then" and is reported as a timeout; a run that produced nothing, or crashed, is an error and is never a pass.
Verdict: PASS (exit 0), FAIL (1), NOT VERIFIED (2: a CLI is missing, a run errored, or no run completed), plan only (3).

Control run: `--control neutral-descriptions` replaces every skill description in the workspace with "Reference material." and keeps
names and paths. Codex and Grok read skill files while browsing, so a high use rate alone does not show the description worked. Run
the same prompts with and without the control: a drop under the control is the part the description earns, and what remains is
browsing and the skill name. Claude is left out, because it only counts the Skill tool, which a neutral description cannot fake.

Limits to read the result with: Codex and Grok read files after listing the workspace, so a read of `SKILL.md` shows the skill was used,
not that its description alone caused it. Claude may also see an installed copy of the plugin. The model is not deterministic, so use
several runs and treat a borderline prompt as a reason to read the transcript, not as a verdict. Event shapes were taken from real
headless runs of `claude` 2.1, `codex-cli` 0.171 and `grok` 1.0.92; a CLI that changes its output format makes runs error or never
trigger, which this tool reports as NOT VERIFIED or FAIL, never PASS.

Cost and privacy: every run is a real model call on your account, so nothing runs without --yes and a plan larger than
--max-invocations is refused. Only the synthetic prompts from the cases file are sent. The result is a measurement, not a gate; CI never runs it.
"""
from __future__ import annotations

import argparse
import json
import os
import queue
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Iterable, Iterator

from install_skill import parse_frontmatter

ROOT = Path(__file__).resolve().parent
CASES = ROOT / "references" / "trigger-eval-cases.json"
SKILLS = ROOT / "skills"
RFP = ROOT / "skills" / "create-proposal-document" / "fixtures" / "e2e-mini-rfp" / "rfp.md"
MIN_RATE = 0.66  # two of three runs
MAX_FALSE_RATE = 0.34  # one of three runs
EXIT = {"PASS": 0, "FAIL": 1, "NOT VERIFIED": 2, "PLAN": 3}


@dataclass(frozen=True)
class Call:
    tool: str
    text: str  # the call's input with separators normalised to `/` and lower-cased
    skill: str | None = None  # the skill named by an explicit Skill tool call


def normalise(value: object) -> str:
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    return text.replace("\\\\", "/").replace("\\", "/").lower()


def claude_calls(event: dict) -> list[Call]:
    if event.get("type") != "assistant":
        return []
    calls = []
    for item in event.get("message", {}).get("content", []):
        if isinstance(item, dict) and item.get("type") == "tool_use":
            given = item.get("input", {}) if isinstance(item.get("input"), dict) else {}
            named = (str(given.get("skill", "")) or None) if item.get("name") == "Skill" else None
            calls.append(Call(str(item.get("name", "")), normalise(given), named))
    return calls


def codex_calls(event: dict) -> list[Call]:
    item = event.get("item", {})
    if event.get("type") != "item.started" or item.get("type") in {"agent_message", "reasoning"}:
        return []
    return [Call(str(item.get("type", "")), normalise(item.get("command") or item))]


def grok_calls(event: dict) -> list[Call]:
    if event.get("type") != "tool_call":
        return []
    return [Call(str(event.get("toolName", "")), normalise(event.get("rawInput", "")))]


@dataclass(frozen=True)
class Host:
    name: str
    executable: str
    argv: Callable[[str, "str | None", Path, Path], list[str]]
    calls: Callable[[dict], list[Call]]
    done: Callable[[dict], bool]
    places: tuple[str, ...]  # where this host discovers project skills
    reading_counts: bool  # whether reading `<skill>/SKILL.md` counts as use (hosts without a Skill tool)


def claude_argv(prompt: str, model: str | None, workspace: Path, root: Path) -> list[str]:
    return ["claude", "-p", prompt, "--output-format", "stream-json", "--verbose", "--plugin-dir", str(root),
            *(["--model", model] if model else [])]


def codex_argv(prompt: str, model: str | None, workspace: Path, root: Path) -> list[str]:
    return ["codex", "exec", "--json", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-C", str(workspace),
            *(["-m", model] if model else []), prompt]


def grok_argv(prompt: str, model: str | None, workspace: Path, root: Path) -> list[str]:
    return ["grok", "-p", prompt, "--output-format", "streaming-json", "--cwd", str(workspace), "--trust",
            "--permission-mode", "plan", *(["-m", model] if model else [])]


HOSTS = {
    "claude": Host("claude", "claude", claude_argv, claude_calls, lambda e: e.get("type") == "result", (), False),
    "codex": Host("codex", "codex", codex_argv, codex_calls,
                  lambda e: e.get("type") in {"turn.completed", "turn.failed", "error"}, (".agents/skills",), True),
    "grok": Host("grok", "grok", grok_argv, grok_calls, lambda e: False, (".agents/skills",), True),
}


def load_cases(path: Path = CASES) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8"))
    return {k: v for k, v in data.items() if not k.startswith("_")}


def entry_skills(skills_dir: Path, names: list[str]) -> list[str]:
    """The skills a model may start on its own: those without `disable-model-invocation: true`."""
    entry = []
    for name in names:
        try:
            front = parse_frontmatter((skills_dir / name / "SKILL.md").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if str(front.get("disable-model-invocation", "")).lower() != "true":
            entry.append(name)
    return entry or list(names)


def expectations(cases: dict[str, dict], only: str | None = None, entry: Iterable[str] = (), holdout: bool = False) -> list[dict]:
    """One row per prompt: the skill that must be used (or an entry skill), or None when no repository skill may be.
    `holdout` selects the prompts kept out of description tuning (a skill's optional "holdout" object) instead of the main lists."""
    rows = []
    for skill, spec in cases.items():
        if only and skill != only:
            continue
        if holdout:
            spec = spec.get("holdout", {})
        accept = sorted({skill, *entry})
        # "semantic_should_trigger": dev prompts without a route term, so the term lint skips them but a model run does not
        should = spec.get("should_trigger", []) + ([] if holdout else spec.get("semantic_should_trigger", []))
        rows += [{"owner": skill, "prompt": p, "expect": skill, "accept": accept} for p in should]
        rows += [{"owner": skill, "prompt": p, "expect": None, "accept": []} for p in spec.get("should_not_trigger", [])]
    return rows


def matches(called: str, names: Iterable[str]) -> str | None:
    for name in names:
        if called == name or called.endswith(":" + name):
            return name
    return None


def used_skill(call: Call, names: Iterable[str], reading_counts: bool = True) -> str | None:
    if call.skill:
        return matches(call.skill, names)
    if not reading_counts:
        return None
    for name in names:
        if re.search(rf"(?<![\w-]){re.escape(name)}/skill\.md", call.text):
            return name
    return None


def decide(events: Iterable[dict], names: list[str], host: Host, max_calls: int) -> tuple[str | None, list[str], str]:
    """(skill used within the first `max_calls` tool calls, the tools called, how the watch ended).
    It ends as used, limit (enough calls without one), done (the host said the turn ended), stream-end, or timeout. A timeout
    after the run produced events means no skill had been used by then; a timeout before any event is raised as an error."""
    tools: list[str] = []
    seen = False
    iterator = iter(events)
    while True:
        try:
            event = next(iterator)
        except StopIteration:
            return None, tools, "stream-end"
        except TimeoutError:
            if not seen:
                raise
            return None, tools, "timeout"
        seen = True
        for call in host.calls(event):
            tools.append(call.tool)
            found = used_skill(call, names, host.reading_counts)
            if found:
                return found, tools, "used"
            if len(tools) >= max_calls:
                return None, tools, "limit"
        if host.done(event):
            return None, tools, "done"


NEUTRAL_DESCRIPTION = "Reference material."


def neutral_description(text: str) -> str:
    """The SKILL.md text with its `description` replaced by a neutral one; every other field and the body are unchanged."""
    match = re.match(r"(---\r?\n)(.*?)(\r?\n---)", text, re.S)
    if not match:
        raise ValueError("SKILL.md has no frontmatter")
    kept: list[str] = []
    replaced = 0
    skipping = False
    for line in match.group(2).split("\n"):
        if re.match(r"description\s*:", line):
            kept.append(f'description: "{NEUTRAL_DESCRIPTION}"')
            replaced += 1
            skipping = True  # a folded or wrapped value continues on indented lines
        elif skipping and line[:1] in {" ", "\t"}:
            continue
        else:
            skipping = False
            kept.append(line)
    if replaced != 1:
        raise ValueError(f"expected one description in the frontmatter, found {replaced}")
    return text[:match.start(2)] + "\n".join(kept) + text[match.end(2):]


def make_workspace(destination: Path, places: tuple[str, ...] = (".claude/skills", ".agents/skills"), skills_dir: Path = SKILLS,
                   rfp: Path | None = RFP, neutral: bool = False) -> Path:
    """A fresh folder holding the current skills in the given discovery folders and, when given, one synthetic RFP.
    With `neutral` every skill keeps its name and path but gets a neutral description (the control of a trigger run)."""
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc")
    destination.mkdir(parents=True, exist_ok=True)
    for place in places:
        shutil.copytree(skills_dir, destination / place, ignore=ignore)
    if neutral:
        for place in places:
            for skill_file in (destination / place).glob("*/SKILL.md"):
                skill_file.write_text(neutral_description(skill_file.read_text(encoding="utf-8")), encoding="utf-8")
    if rfp is not None:
        shutil.copyfile(rfp, destination / "rfp.md")
    return destination


def launch_host(host: Host, prompt: str, model: str | None, workspace: Path, timeout: int) -> Iterator[dict]:
    """Stream the parsed events of one headless run; the process is stopped when the caller stops reading or time runs out."""
    env = {k: v for k, v in os.environ.items() if k != "CLAUDECODE"}  # lets the CLI run inside another Claude Code session
    process = subprocess.Popen(host.argv(prompt, model, workspace, ROOT), stdout=subprocess.PIPE, stderr=subprocess.DEVNULL,
                               stdin=subprocess.DEVNULL, text=True, encoding="utf-8", errors="replace", cwd=workspace, env=env)
    lines: queue.Queue = queue.Queue()

    def pump() -> None:
        for line in process.stdout:
            lines.put(line)
        lines.put(None)  # end of stream, also when nothing was printed

    threading.Thread(target=pump, daemon=True).start()
    deadline = time.monotonic() + timeout
    try:
        while True:
            try:
                line = lines.get(timeout=max(0.0, deadline - time.monotonic()))
            except queue.Empty:
                raise TimeoutError(f"no decision within {timeout}s") from None
            if line is None:
                return
            try:
                yield json.loads(line)
            except ValueError:
                continue
    finally:
        process.kill()
        process.wait()


Launch = Callable[[Host, str, "str | None", Path, int], Iterable[dict]]


def run_once(host: Host, prompt: str, names: list[str], model: str | None, timeout: int, max_calls: int, launch: Launch,
             skills_dir: Path, rfp: Path | None, neutral: bool = False) -> tuple[str | None, str | None, list[str], str]:
    """(skill used, error, tools called, how the watch ended). An error means the run says nothing either way."""
    events = None
    try:
        # a killed agent can leave a child process holding the folder for a moment; that must not turn a decision into an error
        with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as tmp:
            workspace = make_workspace(Path(tmp) / "workspace", host.places, skills_dir, rfp, neutral)
            events = launch(host, prompt, model, workspace, timeout)
            skill, tools, ended = decide(events, names, host, max_calls)
            close = getattr(events, "close", None)
            if close:
                close()  # stops the process as soon as the decision is known, before the workspace is removed
            return skill, None, tools, ended
    except (OSError, TimeoutError, ValueError) as exc:
        return None, f"{type(exc).__name__}: {exc}", [], "error"


def judge_prompt(row: dict, outcomes: list[tuple[str | None, str | None, list[str], str]], min_rate: float, max_false: float) -> dict:
    done = [skill for skill, error, _, _ in outcomes if error is None]
    errors = [error for _, error, _, _ in outcomes if error]
    result = {**row, "runs": len(outcomes), "completed": len(done), "errors": errors[:3], "used": sorted({s for s in done if s}),
              "timeouts": sum(1 for _, error, _, ended in outcomes if error is None and ended == "timeout"),
              "first_tools": [tools[:3] for _, error, tools, _ in outcomes if error is None][:3]}
    if not done:
        return {**result, "verdict": "NOT VERIFIED", "rate": None}
    if row["expect"]:
        accept = set(row.get("accept") or [row["expect"]])
        rate = sum(1 for s in done if s in accept) / len(done)
        passed = rate >= min_rate
    else:
        rate = sum(1 for s in done if s) / len(done)  # the false-trigger rate
        passed = rate <= max_false
    verdict = ("PASS" if passed else "FAIL") if not errors else ("FAIL" if not passed else "NOT VERIFIED")
    return {**result, "verdict": verdict, "rate": round(rate, 3)}


def overall(results: list[dict]) -> str:
    verdicts = {r["verdict"] for r in results}
    if "FAIL" in verdicts:
        return "FAIL"
    return "PASS" if verdicts == {"PASS"} else "NOT VERIFIED"


def main(argv: list[str] | None = None, launch: Launch | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--yes", action="store_true", help="actually call the model (without it only the plan is printed)")
    parser.add_argument("--host", default="claude", choices=[*HOSTS, "all"], help="CLI to run (default claude)")
    parser.add_argument("--runs", type=int, default=3, help="runs per prompt (default 3)")
    parser.add_argument("--skill", help="only the prompts of this skill")
    parser.add_argument("--control", choices=["none", "neutral-descriptions"], default="none",
                        help="neutral-descriptions: replace every description to separate what the description earns from browsing")
    parser.add_argument("--kind", choices=["all", "positive", "near-miss"], default="all", help="only should-trigger or only near-miss prompts")
    parser.add_argument("--set", dest="prompt_set", choices=["dev", "holdout"], default="dev",
                        help="dev: the prompts a description is tuned on (default); holdout: prompts kept out of tuning, to judge an edit")
    parser.add_argument("--model", help="model name passed to the CLI")
    parser.add_argument("--timeout", type=int, default=120, help="seconds allowed per run (default 120)")
    parser.add_argument("--max-calls", type=int, default=8, help="tool calls watched per run (default 8)")
    parser.add_argument("--min-rate", type=float, default=MIN_RATE, help="share of runs that must use the expected skill")
    parser.add_argument("--max-false-rate", type=float, default=MAX_FALSE_RATE, help="share of runs that may use a skill on a near miss")
    parser.add_argument("--max-invocations", type=int, default=60, help="refuse a plan larger than this (default 60)")
    parser.add_argument("--cases", type=Path, default=CASES)
    parser.add_argument("--skills-dir", type=Path, default=SKILLS)
    parser.add_argument("--rfp", type=Path, default=RFP, help="synthetic RFP placed in the workspace of should-trigger prompts")
    parser.add_argument("--report", type=Path, help="write the full result as JSON")
    args = parser.parse_args(argv)
    launch = launch or launch_host  # looked up now so a test can replace it
    cases = load_cases(args.cases)
    names = list(cases)
    rows = expectations(cases, args.skill, entry_skills(args.skills_dir, names), args.prompt_set == "holdout")
    if args.kind != "all":
        rows = [r for r in rows if bool(r["expect"]) == (args.kind == "positive")]
    hosts = list(HOSTS.values()) if args.host == "all" else [HOSTS[args.host]]
    if args.control != "none":
        if args.host != "all" and not hosts[0].reading_counts:
            print(f"TRIGGER-EVAL: NOT VERIFIED (--control is for hosts that read skill files; {hosts[0].name} uses a Skill tool)")
            return EXIT["NOT VERIFIED"]
        hosts = [h for h in hosts if h.reading_counts]
    if not rows or args.runs < 1 or args.max_calls < 1:
        print("TRIGGER-EVAL: NOT VERIFIED (no prompts selected)")
        return EXIT["NOT VERIFIED"]
    total = len(rows) * args.runs * len(hosts)
    if total > args.max_invocations:
        print(f"TRIGGER-EVAL: NOT VERIFIED (plan of {total} model calls exceeds --max-invocations {args.max_invocations})")
        return EXIT["NOT VERIFIED"]
    if not args.yes:
        print(f"plan: {len(rows)} prompts x {args.runs} runs x {len(hosts)} host(s) [{', '.join(h.name for h in hosts)}] = "
              f"{total} model calls on your account; nothing was sent.")
        print("Rerun with --yes to run it. Each run uses a temporary workspace with the current skills.")
        print("TRIGGER-EVAL: PLAN (not run)")
        return EXIT["PLAN"]
    results: list[dict] = []
    missing = [h.name for h in hosts if launch is launch_host and not shutil.which(h.executable)]
    for name in missing:
        print(f"[NOT VERIFIED] {name}: the `{name}` CLI is not on PATH")
        results.append({"host": name, "owner": "-", "prompt": "-", "expect": None, "verdict": "NOT VERIFIED", "rate": None,
                        "errors": ["CLI not on PATH"], "runs": 0, "completed": 0, "used": [], "timeouts": 0, "first_tools": []})
    lock = threading.Lock()

    def work(host: Host) -> None:
        for row in rows:
            rfp = args.rfp if row["expect"] else None  # a near miss gets no proposal material to be drawn to
            outcomes = [run_once(host, row["prompt"], names, args.model, args.timeout, args.max_calls, launch, args.skills_dir, rfp,
                                 args.control == "neutral-descriptions")
                        for _ in range(args.runs)]
            mark = {**judge_prompt(row, outcomes, args.min_rate, args.max_false_rate), "host": host.name}
            with lock:
                results.append(mark)
                print(f"[{mark['verdict']}] {host.name} | {row['owner']} | expect {row['expect'] or 'no skill'} | "
                      f"rate {mark['rate']} | timeouts {mark['timeouts']} | {row['prompt'][:60]}", flush=True)

    threads = [threading.Thread(target=work, args=(h,)) for h in hosts if h.name not in missing]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    verdict = overall(results)
    for host in hosts:
        mine = [r for r in results if r["host"] == host.name]
        passed = sum(r["verdict"] == "PASS" for r in mine)
        positives = [r for r in mine if r["expect"] and r["completed"]]
        rated = [r["rate"] for r in mine if r["rate"] is not None and r["expect"]]
        mean = f", mean use rate {sum(rated) / len(rated):.2f} over {len(rated)} should-trigger prompts" if rated else ""
        print(f"{host.name}: {overall(mine) if mine else 'NOT VERIFIED'} ({passed}/{len(mine)} prompts pass{mean})")
        if positives and not any(r["used"] for r in positives):
            print(f"note: {host.name} used no repository skill on any positive prompt; check the skills load for this CLI")
    if args.report:
        args.report.write_text(json.dumps({"verdict": verdict, "runs": args.runs, "max_calls": args.max_calls, "control": args.control,
                                           "results": results},
                                          ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"TRIGGER-EVAL: {verdict} ({sum(r['verdict'] == 'PASS' for r in results)}/{len(results)} prompts pass)")
    return EXIT[verdict]


if __name__ == "__main__":
    sys.exit(main())
