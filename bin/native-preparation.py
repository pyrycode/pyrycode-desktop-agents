#!/usr/bin/env python3
"""Prepare the database ABI and retain provenance before launching tests."""
from pathlib import Path
import runpy
import subprocess
import sys

support = runpy.run_path(str(Path(__file__).with_name('verifier-support.py')))


def main():
    if len(sys.argv) != 2 or sys.argv[1] not in {'node', 'electron'}:
        raise ValueError('choose node or electron preparation')
    root, mode = Path.cwd().resolve(), sys.argv[1]
    before = support['native_inputs'](root)
    result = subprocess.run(['npm', 'run', 'rebuild:' + mode], stdout=sys.stderr)
    if result.returncode: return result.returncode
    after = support['native_inputs'](root)
    if before != after: raise ValueError('native preparation changed its source inputs')
    support['record_native'](root, mode, after)
    return 0


if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        print(f'Desktop native preparation failed: {error}', file=sys.stderr)
        sys.exit(1)
