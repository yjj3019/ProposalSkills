#!/usr/bin/env python3
"""Run root unittest discovery and refuse a run that is empty, mostly skipped, or smaller than the committed suite."""
import argparse
import sys
import unittest
from pathlib import Path

# Local machines may lack LibreOffice, Poppler or symlink rights; a larger gap means the suite did not really run.
DEFAULT_MAX_SKIPPED = 25
# The committed suite holds 67 test files and runs about 1,100 tests. A removed or renamed file, or one that stops
# defining tests, exits 0 and passes the skip limit, so the run must also reach these floors. Raise them when the
# suite grows; lower them only together with the deliberate removal that requires it.
DEFAULT_MIN_TESTS = 1000
DEFAULT_MIN_FILES = 60


def is_complete(result, max_skipped=None):
    not_run = len(result.skipped) + len(result.expectedFailures)
    if max_skipped is not None and not_run > max_skipped:
        return False
    return result.wasSuccessful() and result.testsRun > not_run


def floor_problem(tests_run, files, min_tests=DEFAULT_MIN_TESTS, min_files=DEFAULT_MIN_FILES):
    """Why the run is smaller than the committed suite, or None."""
    if files < min_files:
        return f'{files} test files found, floor {min_files}: a test file was probably removed or renamed'
    if tests_run < min_tests:
        return f'{tests_run} tests ran, floor {min_tests}: a suite probably stopped defining or loading tests'
    return None


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-skipped', type=int, default=DEFAULT_MAX_SKIPPED,
                        help=f'fail when more tests than this did not run (default {DEFAULT_MAX_SKIPPED})')
    parser.add_argument('--min-tests', type=int, default=DEFAULT_MIN_TESTS,
                        help=f'fail when fewer tests than this ran (default {DEFAULT_MIN_TESTS})')
    parser.add_argument('--min-files', type=int, default=DEFAULT_MIN_FILES,
                        help=f'fail when fewer test_*.py files than this exist in the root (default {DEFAULT_MIN_FILES})')
    args = parser.parse_args(argv)
    files = len(list(Path('.').glob('test_*.py')))
    early = floor_problem(args.min_tests, files, args.min_tests, args.min_files)
    if early:  # the file count is known before anything runs
        print(f'TEST-RUN: FAILED, {early}', file=sys.stderr)
        return 1
    suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not is_complete(result, args.max_skipped):
        print(f'TEST-RUN: FAILED, NO EXECUTED TESTS, OR MORE THAN {args.max_skipped} NOT RUN', file=sys.stderr)
        return 1
    late = floor_problem(result.testsRun, files, args.min_tests, args.min_files)
    if late:
        print(f'TEST-RUN: FAILED, {late}', file=sys.stderr)
        return 1
    print(f'TEST-RUN: {result.testsRun} discovered, {len(result.skipped)} skipped, '
          f'{len(result.expectedFailures)} expected failures')
    return 0


if __name__ == '__main__':
    sys.exit(main())
