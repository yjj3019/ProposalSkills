"""Regression tests for the repository audit: isolated rendering, CI limits and deliberate script copies."""
import ast
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "skills/create-proposal-document/scripts"))
import deck_check  # noqa: E402

# Each skill script must run alone after installation, so this strict JSON guard is copied on purpose.
JSON_GUARD_COPIES = (
    "skills/create-best-proposal/scripts/build_audit_from_meta.py",
    "skills/create-best-proposal/scripts/bulk_matrix.py",
    "skills/create-best-proposal/scripts/check_source_inventory.py",
    "skills/create-best-proposal/scripts/unified_gate.py",
    "skills/create-proposal-document/scripts/check_numbers.py",
    "skills/create-proposal-document/scripts/mapping_check.py",
    "skills/create-winning-proposal/scripts/compare_requirements.py",
    "skills/create-winning-proposal/scripts/proposal_gate.py",
)


def guard_behavior(relative):
    tree = ast.parse((ROOT / relative).read_text(encoding="utf-8"))
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == "_unique_json_members")
    namespace = {}
    exec(compile(ast.Module(body=[function], type_ignores=[]), relative, "exec"), namespace)
    return namespace["_unique_json_members"]


class RenderIsolationTests(unittest.TestCase):
    def test_each_render_uses_its_own_libreoffice_profile(self):
        commands = []

        def fake_run(command, **_kwargs):
            commands.append(command)
            return subprocess.CompletedProcess(command, 1, "", "stopped by test")

        with tempfile.TemporaryDirectory() as tmp, patch.object(deck_check.shutil, "which", return_value="soffice"), \
                patch.object(deck_check.subprocess, "run", fake_run):
            for _ in range(2):
                deck_check.render(Path(tmp) / "deck.pptx", None)
        profiles = [next(a for a in c if a.startswith("-env:UserInstallation=file:")) for c in commands]
        self.assertEqual(len(set(profiles)), 2)


class MaintenanceContractTests(unittest.TestCase):
    def test_every_ci_job_has_a_time_limit(self):
        workflow = (ROOT / ".github/workflows/ci.yml").read_text(encoding="utf-8")
        self.assertEqual(workflow.count("    runs-on:"), 2)
        self.assertIn("    runs-on: ubuntu-24.04\n    timeout-minutes:", workflow)
        self.assertIn("    runs-on: ${{ matrix.os }}\n", workflow)
        self.assertIn("    timeout-minutes: 60\n", workflow)

    def test_dependency_updates_cover_packages_and_actions(self):
        config = (ROOT / ".github/dependabot.yml").read_text(encoding="utf-8")
        for ecosystem in ("pip", "github-actions"):
            self.assertIn(f"package-ecosystem: {ecosystem}", config)
        self.assertIn("versioning-strategy: increase-if-necessary", config)

    def test_contributing_guide_states_the_data_rules_and_test_command(self):
        guide = (ROOT / "CONTRIBUTING.md").read_text(encoding="utf-8")
        for required in ("synthetic", "brand-assets", "python run_repo_tests.py", "python merge_guard.py"):
            self.assertIn(required, guide)

    def test_copies_of_the_json_guard_all_reject_duplicates(self):
        for relative in JSON_GUARD_COPIES:
            with self.subTest(relative=relative):
                guard = guard_behavior(relative)
                self.assertEqual(guard([("a", 1), ("b", 2)]), {"a": 1, "b": 2})
                with self.assertRaises(ValueError):
                    guard([("a", 1), ("a", 2)])


if __name__ == "__main__":
    unittest.main()
