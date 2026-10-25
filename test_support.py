"""Tests invoke skill scripts in-process by default. subprocess adds interpreter/import overhead, plus Windows process creation and antivirus costs (measured: the same 401 cases took 47 seconds on Linux and 46 minutes on Windows). Impractical local suites encourage CI-only validation, which caused an incident in the previous batch. Gate-decision tests therefore call main(argv) -> int directly. Keep real child processes for console encoding (such as cp949), shell exit-code propagation, and direct python <script> installed smoke checks. run_script(..., isolated=True) provides that path."""
from __future__ import annotations

import contextlib
import importlib.util
import inspect
import io
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

REPO = Path(__file__).resolve().parent
_MODULES: dict[Path, object] = {}


@dataclass
class Result:
    """Match subprocess.CompletedProcess shape to preserve callers."""
    returncode: int
    stdout: str
    stderr: str


def _load(script: Path):
    script = script.resolve()
    if script not in _MODULES:
        sys.path.insert(0, str(script.parent))
        name = f"script_{script.parent.parent.name.replace('-', '_')}_{script.stem}"
        spec = importlib.util.spec_from_file_location(name, script)
        module = importlib.util.module_from_spec(spec)
        sys.modules[name] = module
        spec.loader.exec_module(module)
        _MODULES[script] = module
    return _MODULES[script]


def _call_main(module, argv: list[str], script: Path) -> int:
    main = getattr(module, "main", None)
    if main is None:
        raise AssertionError(f"{script} has no main()")
    params = inspect.signature(main).parameters
    if not params:
        # quality_gate.main() reads sys.argv directly.
        saved, sys.argv = sys.argv, [str(script), *argv]
        try:
            return main()
        finally:
            sys.argv = saved
    if getattr(module, "__name__", "").endswith("proposal_gate"):
        # proposal_gate.main(argv) expects sys.argv form, including the program name.
        return main([str(script), *argv])
    return main(argv)


def run_script(script: Path, *args: object, isolated: bool = False,
               env: dict[str, str] | None = None, cwd: Path | None = None) -> Result:
    """Run a script and return (exit code, stdout, stderr). isolated=True uses a real child process for encoding/exit-code contracts; supplying env automatically enables isolation."""
    argv = [str(a) for a in args]
    if isolated or env is not None:
        global SPAWNS
        SPAWNS += 1
        proc = subprocess.run([sys.executable, str(script), *argv], capture_output=True,
                              text=True, encoding="utf-8", errors="replace",
                              env={**os.environ, **(env or {})}, cwd=str(cwd or REPO))
        return Result(proc.returncode, proc.stdout, proc.stderr)
    out, err = io.StringIO(), io.StringIO()
    try:
        module = _load(Path(script))
        with contextlib.redirect_stdout(out), contextlib.redirect_stderr(err):
            code = _call_main(module, argv, Path(script))
    except SystemExit as exc:  # argparse usage errors and similar exits.
        code = exc.code if isinstance(exc.code, int) else 2
    return Result(int(code or 0), out.getvalue(), err.getvalue())


SPAWNS = 0  # Count actual child-process launches; tests verify this.


# --- Slide generation cache ---
# Multiple tests regenerate identical decks. Results are deterministic, so generate once
# and copy; preserve test inputs while removing redundant generation cost.
_DECKS: dict[tuple, Path] = {}


def build_deck_cached(build_script: Path, spec: Path, out: Path, *args: object) -> Result:
    import hashlib
    import shutil
    key = (hashlib.sha256(Path(spec).read_bytes()).hexdigest(), tuple(str(a) for a in args))
    cached = _DECKS.get(key)
    if cached is not None and cached.is_file():
        shutil.copy2(cached, out)
        return Result(0, f"wrote {out} (cached)\n", "")
    result = run_script(build_script, spec, "-o", out, *args)
    if result.returncode == 0 and Path(out).is_file():
        keep = REPO / ".pytest_cache" / "decks"
        keep.mkdir(parents=True, exist_ok=True)
        cached = keep / f"{key[0][:16]}_{abs(hash(key[1]))}.pptx"
        shutil.copy2(out, cached)
        _DECKS[key] = cached
    return result
