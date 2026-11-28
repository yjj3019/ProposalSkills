"""trigger_eval_run.py: what counts as a skill being used on each host, how runs are judged, and that nothing is sent without consent.

The event samples have the shapes of real headless runs (claude 2.1, codex-cli 0.171, grok 1.0.92) with the paths shortened. The
Claude `Skill` tool call follows the documented tool input; the real runs seen so far only called other tools.
"""
import contextlib
import io
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import trigger_eval_run as ter

ROOT = Path(__file__).resolve().parent
NAMES = ["create-best-proposal", "create-proposal-document", "create-winning-proposal"]
CLAUDE, CODEX, GROK = ter.HOSTS["claude"], ter.HOSTS["codex"], ter.HOSTS["grok"]


def claude_call(name, **tool_input):
    return {"type": "assistant", "message": {"content": [{"type": "text", "text": "ok"},
                                                        {"type": "tool_use", "id": "toolu_1", "name": name, "input": tool_input}]}}


def codex_command(command, kind="item.started"):
    return {"type": kind, "item": {"id": "item_1", "type": "command_execution", "aggregated_output": "", "exit_code": None,
                                   "status": "in_progress", "command": command}}


def codex_read(skill):
    return codex_command('"C:\\\\WINDOWS\\\\System32\\\\WindowsPowerShell\\\\v1.0\\\\powershell.exe" -Command '
                         f"'Get-Content -Raw .agents/skills/{skill}/SKILL.md'")


def grok_call(tool, **raw):
    return {"type": "tool_call", "toolCallId": "call-1-0", "title": tool, "kind": "read", "status": "pending", "toolName": tool, "rawInput": raw}


def grok_read(skill):
    return grok_call("read_file", target_file=f"D:\\work\\ws\\.agents\\skills\\{skill}\\SKILL.md")


class ClaudeHostTests(unittest.TestCase):
    def decide(self, events, max_calls=8):
        return ter.decide(events, NAMES, CLAUDE, max_calls)[0]

    def test_the_real_skill_call_shape_is_recognised(self):
        # Seen in a real run: the input also carries the user's request, and the name carries the plugin prefix.
        real = claude_call("Skill", skill="proposal-skills:create-best-proposal", args="Run the submission gate on this deck")
        self.assertEqual(ter.decide([real], NAMES, CLAUDE, 8), ("create-best-proposal", ["Skill"], "used"))

    def test_a_skill_tool_call_names_the_skill_and_accepts_a_plugin_prefix(self):
        self.assertEqual(self.decide([claude_call("Skill", skill="create-best-proposal")]), "create-best-proposal")
        self.assertEqual(self.decide([claude_call("Skill", skill="proposal-skills:create-winning-proposal")]), "create-winning-proposal")

    def test_look_alikes_and_other_skills_do_not_count(self):
        self.assertIsNone(self.decide([claude_call("Skill", skill="not-create-best-proposal")]))
        self.assertIsNone(self.decide([claude_call("Skill", skill="someone-elses-skill")]))
        self.assertIsNone(ter.decide([codex_command("cat my-create-best-proposal/SKILL.md")], NAMES, CODEX, 8)[0])

    def test_browsing_a_skill_file_is_not_use_because_claude_has_a_skill_tool(self):
        read = claude_call("Read", file_path="C:\\w\\.claude\\skills\\create-proposal-document\\SKILL.md")
        self.assertIsNone(self.decide([claude_call("Glob", pattern="**/*"), read]))
        self.assertEqual(self.decide([read, claude_call("Skill", skill="create-proposal-document")]), "create-proposal-document")

    def test_a_skill_after_the_watched_calls_is_not_counted(self):
        events = [claude_call("Glob", pattern="**/*"), claude_call("Bash", command="ls"), claude_call("Skill", skill=NAMES[0])]
        self.assertEqual(self.decide(events, max_calls=3), NAMES[0])
        self.assertIsNone(self.decide(events, max_calls=2))

    def test_a_run_that_ends_without_a_skill_is_none(self):
        events = [claude_call("Glob", pattern="**/*"), {"type": "result", "result": "I can't find an RFP"}, claude_call("Skill", skill=NAMES[0])]
        self.assertIsNone(self.decide(events))
        self.assertEqual(ter.decide(events, NAMES, CLAUDE, 8), (None, ["Glob"], "done"))
        self.assertIsNone(self.decide([]))


class CodexHostTests(unittest.TestCase):
    def decide(self, events, max_calls=8):
        return ter.decide(events, NAMES, CODEX, max_calls)[0]

    def test_reading_the_skill_file_is_the_evidence(self):
        self.assertEqual(self.decide([codex_command("rg --files"), codex_read("create-best-proposal")]), "create-best-proposal")

    def test_a_sentence_about_using_the_skill_is_not_evidence(self):
        said = {"type": "item.completed", "item": {"type": "agent_message", "text": "I'll use the create-best-proposal skill"}}
        self.assertIsNone(self.decide([said, codex_command("rg --files")]))

    def test_the_finished_event_is_not_counted_a_second_time(self):
        events = [codex_command("rg --files", "item.completed"), codex_command("Get-Content a.txt"), codex_read("create-winning-proposal")]
        self.assertEqual(ter.decide(events, NAMES, CODEX, 8), ("create-winning-proposal", ["command_execution", "command_execution"], "used"))

    def test_a_timeout_after_events_means_no_skill_yet_but_a_silent_one_is_an_error(self):
        def stalls(after):
            yield from after
            raise TimeoutError("no decision within 150s")
        self.assertEqual(ter.decide(stalls([codex_command("rg --files")]), NAMES, CODEX, 8), (None, ["command_execution"], "timeout"))
        with self.assertRaises(TimeoutError):
            ter.decide(stalls([]), NAMES, CODEX, 8)

    def test_the_turn_ending_stops_the_watch(self):
        self.assertIsNone(self.decide([codex_command("rg --files"), {"type": "turn.completed"}, codex_read("create-best-proposal")]))


class GrokHostTests(unittest.TestCase):
    def decide(self, events, max_calls=8):
        return ter.decide(events, NAMES, GROK, max_calls)[0]

    def test_a_windows_path_to_the_skill_file_is_recognised(self):
        self.assertEqual(self.decide([grok_call("list_dir", target_directory="D:\\work\\ws"), grok_read("create-proposal-document")]),
                         "create-proposal-document")

    def test_updates_and_text_are_not_calls(self):
        events = [{"type": "text", "data": "create-best-proposal/SKILL.md"}, {"type": "tool_call_update", "toolCallId": "call-1-0"},
                  {"type": "available_commands", "tools": [], "commands": []}]
        self.assertIsNone(self.decide(events))

    def test_a_terminal_command_naming_the_file_counts(self):
        self.assertEqual(self.decide([grok_call("run_terminal_command", command="Get-Content .agents/skills/create-best-proposal/SKILL.md")]),
                         "create-best-proposal")


class WorkspaceAndCommandTests(unittest.TestCase):
    def test_the_workspace_holds_the_current_skills_only_where_the_host_reads_them(self):
        with tempfile.TemporaryDirectory() as tmp:
            for host in (CLAUDE, CODEX, GROK):
                workspace = ter.make_workspace(Path(tmp) / host.name, host.places)
                self.assertEqual(host.places == (), host.name == "claude")
                for place in host.places:
                    for name in NAMES:
                        self.assertTrue((workspace / place / name / "SKILL.md").is_file(), f"{host.name}: {place}/{name}")
                self.assertTrue((workspace / "rfp.md").is_file())
                self.assertEqual(list(workspace.rglob("__pycache__")), [])
            clean = ter.make_workspace(Path(tmp) / "clean", CODEX.places, rfp=None)
            self.assertFalse((clean / "rfp.md").exists())
            self.assertFalse((Path(tmp) / "claude" / ".agents").exists())
            self.assertFalse((Path(tmp) / "claude" / ".claude").exists())  # claude gets the checkout as a plugin, not as files
            self.assertFalse((Path(tmp) / "codex" / ".claude").exists())

    def test_commands_run_headless_in_the_workspace_and_trust_only_that_folder(self):
        ws = Path("W")
        claude, codex, grok = (h.argv("PROMPT", None, ws, ROOT) for h in (CLAUDE, CODEX, GROK))
        self.assertEqual(claude[:3], ["claude", "-p", "PROMPT"])
        self.assertIn("stream-json", claude)
        self.assertEqual(claude[claude.index("--plugin-dir") + 1], str(ROOT))
        self.assertEqual(codex[:3], ["codex", "exec", "--json"])
        self.assertIn("--ephemeral", codex)
        self.assertEqual(codex[codex.index("-s") + 1], "read-only")
        self.assertEqual(codex[codex.index("-C") + 1], "W")
        self.assertEqual(grok[grok.index("--cwd") + 1], "W")
        self.assertIn("--trust", grok)
        self.assertEqual(grok[grok.index("--permission-mode") + 1], "plan")
        for command in (claude, codex, grok):
            self.assertIn("PROMPT", command)
        self.assertEqual(ter.HOSTS["claude"].argv("p", "m1", ws, ROOT)[-2:], ["--model", "m1"])


class NeutralDescriptionTests(unittest.TestCase):
    SKILL = ('---\nname: demo\nlicense: MIT\ndescription: "Long text that routes requests, with: colons"\n'
             'disable-model-invocation: true\n---\n\n# Body\n\ndescription: not a field\n')

    def test_only_the_description_changes(self):
        out = ter.neutral_description(self.SKILL)
        self.assertIn('description: "Reference material."', out)
        for kept in ("name: demo", "license: MIT", "disable-model-invocation: true", "# Body", "description: not a field"):
            self.assertIn(kept, out)
        self.assertNotIn("Long text", out)
        self.assertEqual(out.count("Reference material."), 1)

    def test_a_wrapped_description_is_replaced_whole(self):
        wrapped = "---\nname: demo\ndescription: >\n  first line\n  second line\nlicense: MIT\n---\nbody\n"
        out = ter.neutral_description(wrapped)
        self.assertNotIn("first line", out)
        self.assertNotIn("second line", out)
        self.assertIn("license: MIT", out)

    def test_a_skill_it_cannot_rewrite_safely_is_an_error(self):
        for bad in ("no frontmatter here", "---\nname: demo\n---\nbody", "---\ndescription: a\ndescription: b\n---\n"):
            with self.subTest(bad=bad[:20]):
                with self.assertRaises(ValueError):
                    ter.neutral_description(bad)

    def test_the_control_workspace_keeps_names_and_paths_but_not_descriptions(self):
        with tempfile.TemporaryDirectory() as tmp:
            workspace = ter.make_workspace(Path(tmp) / "ws", CODEX.places, neutral=True)
            for name in NAMES:
                text = (workspace / ".agents/skills" / name / "SKILL.md").read_text(encoding="utf-8")
                self.assertIn(f"name: {name}", text)
                self.assertIn('description: "Reference material."', text)
            real = (ROOT / "skills/create-best-proposal/SKILL.md").read_text(encoding="utf-8")
            self.assertIn("proposal", real.split("---")[1].lower())  # the source file is untouched


class JudgeTests(unittest.TestCase):
    positive = {"owner": "create-best-proposal", "prompt": "p", "expect": "create-best-proposal", "accept": ["create-best-proposal"]}
    sibling = {"owner": "create-proposal-document", "prompt": "s", "expect": "create-proposal-document",
               "accept": ["create-best-proposal", "create-proposal-document"]}
    negative = {"owner": "create-best-proposal", "prompt": "n", "expect": None, "accept": []}

    def judge(self, row, outcomes):
        return ter.judge_prompt(row, [(s, e, ["Glob"], "error" if e else "done") for s, e in outcomes], ter.MIN_RATE, ter.MAX_FALSE_RATE)

    def test_a_positive_prompt_needs_the_expected_skill_often_enough(self):
        hit, miss = ("create-best-proposal", None), (None, None)
        self.assertEqual(self.judge(self.positive, [hit, hit, miss])["verdict"], "PASS")
        self.assertEqual(self.judge(self.positive, [hit, miss, miss])["verdict"], "FAIL")
        self.assertEqual(self.judge(self.positive, [("create-winning-proposal", None)] * 3)["verdict"], "FAIL")

    def test_a_sibling_prompt_accepts_the_entry_skill_because_siblings_are_explicit_only(self):
        entry = [("create-best-proposal", None)] * 3
        self.assertEqual(self.judge(self.sibling, entry)["verdict"], "PASS")
        self.assertEqual(self.judge(self.sibling, [("create-proposal-document", None)] * 3)["verdict"], "PASS")
        self.assertEqual(self.judge(self.sibling, [("create-winning-proposal", None)] * 3)["verdict"], "FAIL")

    def test_timeouts_are_counted_but_are_not_errors(self):
        outcomes = [(None, None, ["Glob"], "timeout")] * 3
        result = ter.judge_prompt(self.negative, outcomes, ter.MIN_RATE, ter.MAX_FALSE_RATE)
        self.assertEqual((result["verdict"], result["timeouts"], result["errors"]), ("PASS", 3, []))

    def test_a_timed_out_run_of_a_positive_prompt_is_unmeasured_not_a_miss(self):
        hit, miss, slow = ("create-best-proposal", None, ["Skill"], "done"), (None, None, ["Glob"], "done"), (None, None, ["Glob"], "timeout")

        def verdict(outcomes):
            result = ter.judge_prompt(self.positive, outcomes, ter.MIN_RATE, ter.MAX_FALSE_RATE)
            return result["verdict"], result["rate"], result["uses"]

        self.assertEqual(verdict([hit, hit, slow]), ("PASS", 1.0, 2))            # the missing run cannot make it fail
        self.assertEqual(verdict([miss, miss, slow]), ("FAIL", 0.0, 0))          # the missing run cannot make it pass
        self.assertEqual(verdict([hit, slow, slow]), ("NOT VERIFIED", 1.0, 1))   # the two missing runs decide it
        self.assertEqual(verdict([hit, miss, slow]), ("NOT VERIFIED", 0.5, 1))
        self.assertEqual(verdict([slow, slow, slow]), ("NOT VERIFIED", None, 0))

    def test_a_stored_row_is_judged_again_from_its_counts(self):
        old = {"expect": "create-best-proposal", "completed": 3, "timeouts": 2, "rate": 0.333, "errors": [], "verdict": "FAIL"}
        self.assertEqual(ter.rejudge(old, ter.MIN_RATE, ter.MAX_FALSE_RATE), "NOT VERIFIED")
        self.assertEqual(ter.rejudge({**old, "timeouts": 0}, ter.MIN_RATE, ter.MAX_FALSE_RATE), "FAIL")
        self.assertEqual(ter.rejudge({**old, "uses": 2, "timeouts": 1}, ter.MIN_RATE, ter.MAX_FALSE_RATE), "PASS")
        near_miss = {"expect": None, "completed": 3, "timeouts": 3, "rate": 0.0, "errors": []}
        self.assertEqual(ter.rejudge(near_miss, ter.MIN_RATE, ter.MAX_FALSE_RATE), "PASS")

    def test_a_near_miss_may_not_use_any_repository_skill_often(self):
        hit, miss = ("create-best-proposal", None), (None, None)
        self.assertEqual(self.judge(self.negative, [miss, miss, miss])["verdict"], "PASS")
        self.assertEqual(self.judge(self.negative, [miss, miss, hit])["verdict"], "PASS")
        self.assertEqual(self.judge(self.negative, [miss, hit, hit])["verdict"], "FAIL")

    def test_errors_are_never_a_pass(self):
        error = (None, "TimeoutError: no decision within 120s")
        self.assertEqual(self.judge(self.negative, [error, error])["verdict"], "NOT VERIFIED")
        result = self.judge(self.negative, [(None, None), error])
        self.assertEqual(result["verdict"], "NOT VERIFIED")
        self.assertEqual(result["errors"], [error[1]])
        self.assertEqual(self.judge(self.positive, [(None, None), error])["verdict"], "FAIL")

    def test_the_overall_verdict_is_the_weakest_prompt(self):
        self.assertEqual(ter.overall([{"verdict": "PASS"}, {"verdict": "PASS"}]), "PASS")
        self.assertEqual(ter.overall([{"verdict": "PASS"}, {"verdict": "NOT VERIFIED"}]), "NOT VERIFIED")
        self.assertEqual(ter.overall([{"verdict": "NOT VERIFIED"}, {"verdict": "FAIL"}]), "FAIL")


def reading_events(host_name, skill):
    return {"claude": [claude_call("Skill", skill=skill)], "codex": [codex_read(skill)], "grok": [grok_read(skill)]}[host_name]


def dev_positives(spec):
    return spec["should_trigger"] + spec.get("semantic_should_trigger", [])


class PlanTests(unittest.TestCase):
    def setUp(self):
        # No test in this class may start a real CLI: that would spend model calls. A bug here fails loudly instead.
        guard = patch.object(ter.subprocess, "Popen", side_effect=AssertionError("a test tried to start a real CLI"))
        guard.start()
        self.addCleanup(guard.stop)
        # Building the real workspace is tested once above; here a stub keeps hundreds of runs fast.
        stub = patch.object(ter, "make_workspace", side_effect=self.small_workspace)
        stub.start()
        self.addCleanup(stub.stop)

    neutral_calls: list = []

    @staticmethod
    def small_workspace(destination, places=(), skills_dir=None, rfp="synthetic", neutral=False):
        PlanTests.neutral_calls.append(neutral)
        destination.mkdir(parents=True, exist_ok=True)
        for place in places:
            for name in NAMES:
                (destination / place / name).mkdir(parents=True)
                (destination / place / name / "SKILL.md").write_text("x", encoding="utf-8")
        if rfp is not None:
            (destination / "rfp.md").write_text("x", encoding="utf-8")
        return destination

    def main(self, *argv, launch=None):
        out = io.StringIO()
        with contextlib.redirect_stdout(out):
            code = ter.main(list(argv), launch=launch) if launch else ter.main(list(argv))
        return code, out.getvalue()

    def test_the_cases_become_one_row_per_prompt(self):
        cases = ter.load_cases()
        rows = ter.expectations(cases, entry=["create-best-proposal"])
        self.assertEqual(len(rows), sum(len(dev_positives(v)) + len(v["should_not_trigger"]) for v in cases.values()))
        self.assertEqual({r["expect"] for r in rows if r["expect"]}, set(cases))
        sibling = next(r for r in rows if r["expect"] == "create-winning-proposal")
        self.assertEqual(sibling["accept"], ["create-best-proposal", "create-winning-proposal"])
        self.assertTrue(all(r["accept"] == [] for r in rows if not r["expect"]))
        self.assertEqual({r["owner"] for r in ter.expectations(cases, "create-best-proposal")}, {"create-best-proposal"})

    def test_holdout_prompts_are_separate_from_the_tuning_prompts(self):
        cases = ter.load_cases()
        dev = {r["prompt"] for r in ter.expectations(cases)}
        held = ter.expectations(cases, holdout=True)
        self.assertTrue(held, "a holdout set must exist")
        self.assertFalse(dev & {r["prompt"] for r in held}, "a prompt must not be in both sets")
        self.assertTrue(any(r["expect"] for r in held) and any(not r["expect"] for r in held))

    def test_semantic_prompts_run_with_the_dev_set_and_never_in_the_holdout(self):
        cases = ter.load_cases()
        semantic = set(cases["create-best-proposal"]["semantic_should_trigger"])
        self.assertTrue(semantic)
        self.assertTrue(semantic <= {r["prompt"] for r in ter.expectations(cases)})
        self.assertFalse(semantic & {r["prompt"] for r in ter.expectations(cases, holdout=True)})

    def test_the_entry_skill_is_the_one_a_model_may_start_by_itself(self):
        self.assertEqual(ter.entry_skills(ROOT / "skills", NAMES), ["create-best-proposal"])
        self.assertEqual(ter.entry_skills(ROOT / "no-such-dir", NAMES), NAMES)

    def test_nothing_runs_without_explicit_consent(self):
        def forbidden(*_a):
            raise AssertionError("the model must not be called without --yes")
        for host in ("claude", "all"):
            code, text = self.main("--host", host, "--max-invocations", "500", launch=forbidden)
            self.assertEqual(code, 3, text)
            self.assertIn("nothing was sent", text)
            self.assertIn("TRIGGER-EVAL: PLAN", text)
        self.assertIn("x 3 host(s) [claude, codex, grok]", text)

    def test_the_plan_is_capped_before_anything_runs(self):
        code, text = self.main("--yes", "--host", "all", "--runs", "5", launch=lambda *a: [])
        self.assertEqual(code, 2)
        self.assertIn("exceeds --max-invocations", text)

    def test_a_missing_cli_is_not_verified_and_never_hidden_by_the_others(self):
        with patch("shutil.which", return_value=None):
            code, text = self.main("--yes", "--runs", "1")
        self.assertEqual(code, 2)
        self.assertIn("not on PATH", text)

        should = {p: s for s, spec in ter.load_cases().items() for p in dev_positives(spec)}

        def correct(host, prompt, model, workspace, timeout):
            return iter(reading_events(host.name, should[prompt]) if prompt in should else [{"type": "result"}])
        only_claude = lambda exe: "claude" if exe == "claude" else None  # noqa: E731
        with patch("shutil.which", side_effect=only_claude), patch.object(ter, "launch_host", correct):
            code, text = self.main("--yes", "--host", "all", "--runs", "1", "--max-invocations", "100")
        self.assertEqual(code, 2, text)  # claude passes, yet the two missing CLIs keep the result from being PASS
        self.assertIn("[NOT VERIFIED] codex", text)
        self.assertIn("[NOT VERIFIED] grok", text)
        self.assertIn("claude: PASS", text)
        self.assertIn("TRIGGER-EVAL: NOT VERIFIED", text)

    def test_every_run_gets_a_workspace_and_only_a_should_trigger_prompt_gets_the_rfp(self):
        positives = {p for spec in ter.load_cases().values() for p in dev_positives(spec)}
        seen = []

        def spy(host, prompt, model, workspace, timeout):
            seen.append((host.name, prompt in positives, all((workspace / place / "create-best-proposal/SKILL.md").is_file()
                                                             for place in host.places), (workspace / "rfp.md").is_file()))
            return iter([])
        self.main("--yes", "--host", "all", "--runs", "1", "--skill", "create-winning-proposal", launch=spy)
        self.assertEqual({h for h, *_ in seen}, {"claude", "codex", "grok"})
        self.assertEqual({p for _, p, *_ in seen}, {True, False})
        self.assertTrue(all(skills for _, _, skills, _ in seen))
        self.assertTrue(all(rfp == positive for _, positive, _, rfp in seen), "the RFP is for should-trigger prompts only")

    def test_kind_selects_only_the_positives_or_only_the_near_misses(self):
        positives = {p for spec in ter.load_cases().values() for p in dev_positives(spec)}
        for kind, expected in (("positive", True), ("near-miss", False)):
            prompts = []

            def spy(host, prompt, model, workspace, timeout, prompts=prompts):
                prompts.append(prompt)
                return iter([])
            self.main("--yes", "--host", "claude", "--kind", kind, "--runs", "1", launch=spy)
            self.assertTrue(prompts, kind)
            self.assertTrue(all((p in positives) == expected for p in prompts), kind)

    def test_a_correct_model_on_every_host_passes_and_writes_the_report(self):
        cases = ter.load_cases()
        should = {p: s for s, spec in cases.items() for p in dev_positives(spec)}

        def fake(host, prompt, model, workspace, timeout):
            return iter(reading_events(host.name, should[prompt]) if prompt in should else [{"type": "result"}])

        with tempfile.TemporaryDirectory() as tmp:
            report = Path(tmp) / "report.json"
            code, text = self.main("--yes", "--host", "all", "--runs", "2", "--max-invocations", "200", "--report", str(report), launch=fake)
            data = json.loads(report.read_text(encoding="utf-8"))
        self.assertEqual(code, 0, text)
        self.assertIn("TRIGGER-EVAL: PASS", text)
        self.assertEqual({r["host"] for r in data["results"]}, {"claude", "codex", "grok"})
        self.assertEqual(data["verdict"], "PASS")

    def test_a_model_that_always_uses_a_skill_fails_the_near_misses(self):
        def eager(host, prompt, model, workspace, timeout):
            return iter(reading_events(host.name, "create-best-proposal"))
        code, text = self.main("--yes", "--host", "codex", "--runs", "2", "--skill", "create-best-proposal", launch=eager)
        self.assertEqual(code, 1, text)
        self.assertIn("codex: FAIL", text)

    def test_a_model_that_never_uses_a_skill_fails_and_is_told_to_check_loading(self):
        def idle(host, prompt, model, workspace, timeout):
            return iter([{"type": "result"}])
        code, text = self.main("--yes", "--host", "claude", "--runs", "1", "--skill", "create-best-proposal", launch=idle)
        self.assertEqual(code, 1, text)
        self.assertIn("used no repository skill on any positive prompt", text)

    def test_the_control_runs_only_hosts_that_read_skill_files_and_asks_each_run_for_a_neutral_workspace(self):
        PlanTests.neutral_calls.clear()
        hosts = []

        def idle(host, prompt, model, workspace, timeout):
            hosts.append(host.name)
            return iter([])
        code, text = self.main("--yes", "--host", "all", "--kind", "positive", "--runs", "1", "--control", "neutral-descriptions",
                               "--max-invocations", "100", launch=idle)
        self.assertEqual(set(hosts), {"codex", "grok"})
        self.assertTrue(PlanTests.neutral_calls and all(PlanTests.neutral_calls))
        self.assertEqual(code, 1, text)  # nothing was used, so the should-trigger prompts fail, as expected of a control
        self.assertIn("mean use rate 0.00", text)

    def test_the_control_is_refused_for_a_host_with_a_skill_tool(self):
        code, text = self.main("--yes", "--host", "claude", "--control", "neutral-descriptions", launch=lambda *a: iter([]))
        self.assertEqual(code, 2)
        self.assertIn("uses a Skill tool", text)

    def test_a_normal_run_does_not_ask_for_a_neutral_workspace(self):
        PlanTests.neutral_calls.clear()
        self.main("--yes", "--host", "codex", "--kind", "positive", "--runs", "1", "--skill", "create-winning-proposal",
                  launch=lambda *a: iter([]))
        self.assertTrue(PlanTests.neutral_calls and not any(PlanTests.neutral_calls))

    def test_a_crashing_run_is_not_verified(self):
        def broken(host, prompt, model, workspace, timeout):
            raise OSError("the CLI could not start")
        code, text = self.main("--yes", "--runs", "1", "--skill", "create-winning-proposal", launch=broken)
        self.assertEqual(code, 2, text)
        self.assertIn("NOT VERIFIED", text)


class LocalOnlyTests(unittest.TestCase):
    def test_ci_does_not_run_the_local_review_tools(self):
        workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
        for tool in ("trigger_eval_run", "revert_proof", "gate_replay"):
            self.assertNotIn(tool, workflow, tool)


class CompareTests(unittest.TestCase):
    @staticmethod
    def report(rows, **context):
        return {"runs": 3, "max_calls": 8, "control": "none", **context,
                "results": [{"host": "claude", "owner": "create-best-proposal", "prompt": prompt, "expect": "create-best-proposal",
                             "completed": 3, "timeouts": timeouts, "uses": uses, "errors": []} for prompt, uses, timeouts in rows]}

    def outcome(self, before, after):
        return ter.compare_reports(before, after)

    def test_identical_verdicts_are_no_difference_and_fail_fail_is_not_success(self):
        result = self.outcome(self.report([("a", 3, 0), ("b", 0, 0)]), self.report([("a", 2, 0), ("b", 1, 0)]))
        self.assertEqual((result["outcome"], result["counts"]["pass_pass"], result["counts"]["fail_fail"]), ("NO DIFFERENCE", 1, 1))

    def test_a_gain_and_a_regression(self):
        gain = self.outcome(self.report([("a", 0, 0), ("b", 3, 0)]), self.report([("a", 3, 0), ("b", 3, 0)]))
        self.assertEqual((gain["outcome"], gain["changed"][0]["prompt"]), ("GAINS ONLY", "a"))
        mixed = self.outcome(self.report([("a", 0, 0), ("b", 3, 0)]), self.report([("a", 3, 0), ("b", 0, 0)]))
        self.assertEqual(mixed["outcome"], "REGRESSIONS PRESENT")

    def test_an_undecided_pair_makes_the_comparison_inconclusive(self):
        result = self.outcome(self.report([("a", 0, 0), ("b", 3, 0)]), self.report([("a", 3, 0), ("b", 1, 2)]))
        self.assertEqual((result["outcome"], result["counts"]["undecided"], result["counts"]["fail_pass"]), ("INCONCLUSIVE", 1, 1))

    def test_different_prompts_or_settings_are_inconclusive(self):
        base = self.report([("a", 3, 0)])
        self.assertEqual(self.outcome(base, self.report([("a", 3, 0), ("b", 3, 0)]))["outcome"], "INCONCLUSIVE")
        self.assertEqual(self.outcome(base, self.report([("a", 3, 0)], runs=5))["context_mismatch"], ["runs"])
        self.assertEqual(self.outcome(base, self.report([("a", 3, 0)], control="neutral-descriptions"))["outcome"], "INCONCLUSIVE")
        self.assertEqual(self.outcome({"results": []}, {"results": []})["outcome"], "INCONCLUSIVE")

    def test_the_command_reads_two_reports_and_calls_no_model(self):
        with tempfile.TemporaryDirectory() as tmp:
            before, after = Path(tmp) / "before.json", Path(tmp) / "after.json"
            before.write_text(json.dumps(self.report([("a", 0, 0)])), encoding="utf-8")
            after.write_text(json.dumps(self.report([("a", 3, 0)])), encoding="utf-8")

            def forbidden(*_):
                raise AssertionError("--compare must not start a CLI")

            out = io.StringIO()
            with contextlib.redirect_stdout(out):
                code = ter.main(["--compare", str(before), str(after)], launch=forbidden)
            self.assertEqual(code, 0)
            self.assertIn("TRIGGER-COMPARE: GAINS ONLY", out.getvalue())
            self.assertIn("not a significance test", out.getvalue())
            after.write_text("[]", encoding="utf-8")
            with contextlib.redirect_stdout(out):
                self.assertEqual(ter.main(["--compare", str(before), str(after)], launch=forbidden), 2)
            with contextlib.redirect_stdout(out):
                self.assertEqual(ter.main(["--compare", str(before), str(Path(tmp) / "missing.json")], launch=forbidden), 2)


if __name__ == "__main__":
    unittest.main()
