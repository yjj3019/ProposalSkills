#!/usr/bin/env python3
"""Do two versions of a gate decide the same?

A refactor of a gate promises that nothing it decides has changed. This replays both versions on the repository's audit
fixtures, on each fixture in every mode and bid decision, and on deletions and replacements of fields in them, and compares
what each returns, including the exception it raises. It is how `proposal_gate.evaluate` was split into section checks.

    python gate_replay.py --old-ref origin/main
    python gate_replay.py --old-file /tmp/proposal_gate_before.py [--new-file candidate.py]
    python gate_replay.py --old-ref HEAD~1 --target skills/x/scripts/other_gate.py --function check

Exit 0: identical on every case.  Exit 1: at least one difference (the first few are printed).
Exit 2: the versions could not be loaded, the function is missing, or there were no cases.
Identical on these cases is not a proof of equivalence; it covers the fixtures and field mutations that exist. The run is
deterministic for a given --seed. A behaviour change is proven the other way around, with revert_proof.py. Local tool; not run in CI.
"""
from __future__ import annotations

import argparse
import copy
import importlib.util
import json
import random
import subprocess
import sys
import tempfile
from pathlib import Path

DEFAULT_TARGET = "skills/create-winning-proposal/scripts/proposal_gate.py"
MODES = ("draft", "review", "submission")
DECISIONS = ("bid", "conditional-bid", "no-bid")
REPLACEMENTS = (None, True, False, 0, 1, -1, 1.5, "", "x", "submission", "public", "gap", "met", "fail", "pass", [], {}, ["x"])


class ReplayError(Exception):
    """A version could not be loaded or there was nothing to compare."""


def load_function(path: Path, name: str, label: str):
    spec = importlib.util.spec_from_file_location(f"gate_replay_{label}", path)
    if spec is None or spec.loader is None:
        raise ReplayError(f"{path} is not a Python module")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    sys.path.insert(0, str(path.parent))
    try:
        spec.loader.exec_module(module)
    except Exception as exc:  # the version under test may be broken in any way
        raise ReplayError(f"{label} version failed to load: {type(exc).__name__}: {exc}") from exc
    finally:
        sys.path.remove(str(path.parent))
    function = getattr(module, name, None)
    if not callable(function):
        raise ReplayError(f"{label} version has no function {name}()")
    return function


def seed_documents(repo: Path) -> list[dict]:
    done = subprocess.run(["git", "-C", str(repo), "ls-files", "*.json"], capture_output=True, text=True)
    names = done.stdout.split("\n") if done.returncode == 0 and done.stdout.strip() else \
        [str(p.relative_to(repo)) for p in sorted(repo.rglob("*.json"))]
    seeds = []
    for name in filter(None, names):
        try:
            data = json.loads((repo / name).read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if isinstance(data, dict) and "bid_decision" in data:
            seeds.append(data)
    return seeds


def paths(node, prefix=()):
    if isinstance(node, dict):
        for key, value in node.items():
            yield prefix + (key,)
            yield from paths(value, prefix + (key,))
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield prefix + (index,)
            yield from paths(value, prefix + (index,))


def mutate(data, path, value, delete):
    result = copy.deepcopy(data)
    node = result
    for part in path[:-1]:
        node = node[part]
    if delete:
        del node[path[-1]]
    else:
        node[path[-1]] = value
    return result


def cases(seeds: list[dict], per_seed: int, rng: random.Random):
    for seed in seeds:
        variants = [seed] + [{**seed, "mode": mode, "bid_decision": decision} for mode in MODES for decision in DECISIONS]
        for variant in variants:
            yield variant
            all_paths = list(paths(variant))
            for path in rng.sample(all_paths, min(per_seed, len(all_paths))):
                yield mutate(variant, path, None, True)
                yield mutate(variant, path, rng.choice(REPLACEMENTS), False)


def outcome(function, data):
    try:
        return ("ok", function(copy.deepcopy(data)))
    except Exception as exc:  # a difference in what is raised is also a difference
        return ("raise", type(exc).__name__, str(exc))


def old_version(args, repo: Path, tmp: Path) -> Path:
    if args.old_file:
        return args.old_file
    done = subprocess.run(["git", "-C", str(repo), "show", f"{args.old_ref}:{args.target}"], capture_output=True)
    if done.returncode != 0:
        raise ReplayError(f"git show {args.old_ref}:{args.target} failed: {done.stderr.decode('utf-8', 'replace').strip()[:160]}")
    path = tmp / Path(args.target).name
    path.write_bytes(done.stdout)
    return path


def replay(args) -> tuple[int, list[str]]:
    repo = args.repo.resolve()
    with tempfile.TemporaryDirectory() as tmp:
        old = load_function(old_version(args, repo, Path(tmp)), args.function, "old")
        new = load_function(args.new_file or repo / args.target, args.function, "new")
        seeds = seed_documents(repo)[: args.max_seeds or None]
        total = differences = compared = 0
        shown: list[str] = []
        for data in cases(seeds, args.per_seed, random.Random(args.seed)):
            total += 1
            before, after = outcome(old, data), outcome(new, data)
            compared += len(before[1]) if before[0] == "ok" and isinstance(before[1], list) else 0
            if before != after:
                differences += 1
                if len(shown) < args.max_diffs:
                    shown.append(f"  old: {str(before)[:240]}\n  new: {str(after)[:240]}")
    if not total:
        raise ReplayError("no audit fixtures with a bid_decision were found, so nothing was compared")
    summary = f"seeds={len(seeds)} cases={total} blockers_compared={compared}"
    if differences:
        return 1, [f"REPLAY: DIFFERENT ({summary} differences={differences})", *shown]
    return 0, [f"REPLAY: IDENTICAL ({summary}); equal on these cases, not a proof for every input"]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent)
    parser.add_argument("--target", default=DEFAULT_TARGET, help="gate script relative to the repository")
    parser.add_argument("--function", default="evaluate", help="function taking the audit dict and returning its result")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--old-ref", help="git ref holding the version before the change")
    source.add_argument("--old-file", type=Path, help="file holding the version before the change")
    parser.add_argument("--new-file", type=Path, help="version after the change (default: the working tree)")
    parser.add_argument("--per-seed", type=int, default=120, help="mutated paths sampled per fixture variant (default 120)")
    parser.add_argument("--max-seeds", type=int, default=0, help="use only the first N fixtures (0 = all)")
    parser.add_argument("--seed", type=int, default=20261124)
    parser.add_argument("--max-diffs", type=int, default=3)
    args = parser.parse_args(argv)
    try:
        code, lines = replay(args)
    except ReplayError as exc:
        print(f"REPLAY: ERROR ({exc})")
        return 2
    print("\n".join(lines))
    return code


if __name__ == "__main__":
    sys.exit(main())
