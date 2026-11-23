#!/usr/bin/env python3
"""Run root unittest discovery and refuse zero executed or entirely skipped tests."""
import argparse
import sys
import unittest

# Local machines may lack LibreOffice, Poppler or symlink rights; a larger gap means the suite did not really run.
DEFAULT_MAX_SKIPPED = 25


def is_complete(result, max_skipped=None):
    not_run = len(result.skipped) + len(result.expectedFailures)
    if max_skipped is not None and not_run > max_skipped:
        return False
    return result.wasSuccessful() and result.testsRun > not_run


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-skipped', type=int, default=DEFAULT_MAX_SKIPPED,
                        help=f'fail when more tests than this did not run (default {DEFAULT_MAX_SKIPPED})')
    args = parser.parse_args(argv)
    suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not is_complete(result, args.max_skipped):
        print(f'TEST-RUN: FAILED, NO EXECUTED TESTS, OR MORE THAN {args.max_skipped} NOT RUN', file=sys.stderr)
        return 1
    print(f'TEST-RUN: {result.testsRun} discovered, {len(result.skipped)} skipped, '
          f'{len(result.expectedFailures)} expected failures')
    return 0


if __name__ == '__main__':
    sys.exit(main())
