# Contributing

[AGENTS.md](AGENTS.md) holds the full repository rules. These are the ones every change must follow.

## Data

- This repository is public. Never commit real customer names, amounts, RFP excerpts, proposals, credentials, personal
  data, or local absolute paths.
- Examples and fixtures must be synthetic.
- `approved-examples` and `brand-assets` stay empty on purpose. Keep real templates and logos in your local copy only.

## Setup and tests

Use Python 3.10 or later. LibreOffice and Poppler are optional and enable the render checks.

```bash
python -m pip install -r requirements.txt
python run_repo_tests.py
python skill_audit.py
```

`run_repo_tests.py` fails when fewer than 1000 tests ran or fewer than 60 `test_*.py` files exist, so a removed suite
cannot pass quietly. Raise the floors in that file when the suite grows.

If you change a gate, add a reproduction test to `test_gate_integrity.py` and run `python gate_mutation_probe.py`.
Every catalogued mutation must be KILLED. Never weaken a gate or fixture to make a test pass.

## Pull requests

- Update code and documentation in the same change.
- `requirements.txt` declares tested minimums. Raise one only when the code needs it and the `dependency floor` CI job
  is updated with it.
- Before merging, run `python merge_guard.py <PR>`. All required checks must pass and none may be skipped.
