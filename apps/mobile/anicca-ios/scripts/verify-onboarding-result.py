#!/usr/bin/env python3
"""Fail closed unless xcresulttool reports exactly one passing, unskipped test."""
import json
import sys
from pathlib import Path


def main():
    try:
        summary = json.loads(Path(sys.argv[1]).read_text())
        expected = {'totalTestCount': 1, 'passedTests': 1, 'failedTests': 0,
                    'skippedTests': 0, 'expectedFailures': 0}
        if not isinstance(summary, dict) or any(summary.get(key) != value for key, value in expected.items()):
            raise ValueError('expected exactly one passed test, no skips/failures, and all count fields')
    except (IndexError, OSError, ValueError) as error:
        print(f'BLOCKED: invalid onboarding test result: {error}', file=sys.stderr)
        return 1
    print('PASS: xcresult contains one passed test and zero skips/failures')
    return 0


if __name__ == '__main__':
    sys.exit(main())
