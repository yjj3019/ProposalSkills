"""Regression tests for the residual risks of the repository audit: hook evasions the guard can see in the command text."""
import unittest

import hook_guard_bash as hook


class HookEvasionTests(unittest.TestCase):
    DENIED = (
        "x=/; rm -rf $x", "x=/ && rm -rf ${x}", "export x=~; rm -rf $x", "c=rm; $c -rf /", "d=/; e=$d; rm -rf $e",
        "x=/ rm -rf /", "f(){ rm -rf /; }; f", "echo 'rm -rf /' | sh", "echo cm0gLXJmIC8= | base64 -d | bash",
        "base64 -d payload | python3", "cat x.txt | sudo bash -s", "ls | bash -",
        "Invoke-Expression ([Text.Encoding]::UTF8.GetString([Convert]::FromBase64String($x)))",
        "[Convert]::FromBase64String($x) | iex",
        "Remove-Item -Recurse C:\\Windows", "Remove-Item -r -Force $env:USERPROFILE", "Remove-Item -rec C:\\",
        "ri -Recurse -Force %USERPROFILE%", "rd /s /q C:\\Users", "Remove-Item C:\\Windows -Recurse",
    )
    ALLOWED = (
        "x=build; rm -rf $x", "x=./build && rm -rf \"$x\"", "d=/tmp/work/out; rm -rf $d", "export P=python; $P run.py",
        "cat notes.txt | grep foo", "echo ok | tee out.log", "base64 -d payload > out.bin", "ls | sort | head",
        "Remove-Item -Recurse .\\build", "Remove-Item -Recurse C:\\work\\project\\build\\out", "Remove-Item old.txt",
        "Get-ChildItem -Recurse | Where-Object Length -gt 1", "$env:PATH", "git push origin main",
    )

    def test_evasions_visible_in_the_command_text_are_denied(self):
        for command in self.DENIED:
            with self.subTest(command=command):
                self.assertIsNotNone(hook.deny_reason(command))

    def test_ordinary_variants_stay_allowed(self):
        for command in self.ALLOWED:
            with self.subTest(command=command):
                self.assertIsNone(hook.deny_reason(command))

    def test_unknown_variables_are_not_guessed(self):
        # The environment is invisible to a lexical guard; guessing would deny routine commands.
        self.assertIsNone(hook.deny_reason("$PY script.py"))
        self.assertIsNone(hook.deny_reason('rm -rf "$BUILD_DIR"'))

    def test_setup_covers_the_powershell_tool_and_states_the_limits(self):
        doc = hook.__doc__
        self.assertIn('"matcher": "Bash|PowerShell"', doc)
        for limit in ("earlier tool call", "python -c", "lexical guardrail"):
            self.assertIn(limit, doc)


if __name__ == "__main__":
    unittest.main()
