#!/usr/bin/env python3
"""Run root unittest discovery and refuse zero executed or entirely skipped tests."""
import sys
import unittest


def is_complete(result):
    not_run = len(result.skipped) + len(result.expectedFailures)
    return result.wasSuccessful() and result.testsRun > not_run


def main():
    suite = unittest.defaultTestLoader.discover('.', pattern='test_*.py')
    result = unittest.TextTestRunner(verbosity=2).run(suite)
    if not is_complete(result):
        print('TEST-RUN: FAILED OR NO EXECUTED TESTS', file=sys.stderr)
        return 1
    print(f'TEST-RUN: {result.testsRun} discovered, {len(result.skipped)} skipped, '
          f'{len(result.expectedFailures)} expected failures')
    return 0


if __name__ == '__main__':
    sys.exit(main())
