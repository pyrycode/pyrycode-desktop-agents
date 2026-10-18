#!/usr/bin/env python3
"""Snapshot external Desktop verifier inputs without exposing credentials."""
import hashlib
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys

HERE = Path(__file__).resolve().parent
support = runpy.run_path(str(HERE / 'verifier-support.py'))


def run(*args, cwd=None, timeout=3):
    return subprocess.check_output(args, cwd=cwd, stderr=subprocess.PIPE, timeout=timeout).decode().strip()


def checkout(path):
    path = path.resolve()
    if Path(run('git', '-C', str(path), 'rev-parse', '--show-toplevel')).resolve() != path:
        raise ValueError('uninitialised external checkout')
    if run('git', '-C', str(path), 'status', '--porcelain', '--untracked-files=no'):
        raise ValueError('changed external checkout')
    files = [path / name for name in run('git', '-C', str(path), 'ls-files', '--others', '--exclude-standard', '-z').split('\0') if name]
    return {'tree': run('git', '-C', str(path), 'rev-parse', 'HEAD^{tree}'),
            'untracked': support['files_digest'](files, path)}


def requirements(product):
    branch = run('git', 'branch', '--show-current', cwd=product)
    match = re.fullmatch(r'feature/(\d+)', branch)
    if not match: raise ValueError('unknown verifier ticket context')
    issue = json.loads(run('gh', 'issue', 'view', match[1], '--repo', 'pyrycode/pyrycode-desktop', '--json', 'labels,title,body', cwd=product))
    prs = json.loads(run('gh', 'pr', 'list', '--repo', 'pyrycode/pyrycode-desktop', '--head', branch,
                         '--state', 'open', '--json', 'number,body', '--limit', '1', cwd=product))
    labels = issue.get('labels')
    if (not isinstance(labels, list) or any(not isinstance(x, dict) or not isinstance(x.get('name'), str) for x in labels) or
            not isinstance(issue.get('title'), str) or 'body' not in issue or issue['body'] is not None and not isinstance(issue['body'], str) or
            not isinstance(prs, list) or len(prs) > 1 or
            any(not isinstance(p, dict) or not isinstance(p.get('number'), int) or 'body' not in p or p['body'] is not None and not isinstance(p['body'], str) for p in prs)):
        raise ValueError('incomplete ticket requirements')
    value = {'ticket': int(match[1]), 'title': issue['title'], 'body': issue['body'],
             'labels': sorted(x['name'] for x in labels), 'prs': prs,
             'base': run('git', 'merge-base', 'HEAD', 'origin/main', cwd=product)}
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def snapshot(root, product):
    native = support['native_inputs'](product)
    value = {'agents': checkout(root), 'dispatcher': checkout(root / 'dispatcher'),
             'nativePreparation': support['verify_native'](product, native),
             'requirements': requirements(product), 'python': support['digest'](Path(sys.executable).resolve())}
    value['installedTools'] = support['installed_tools'](product)
    for key in ['PYRY_BIN', 'RELAY_BIN', 'FAKE_CLAUDE_BIN']:
        if os.environ.get(key):
            path = Path(os.environ[key]).resolve()
            value[key] = {'path': str(path), 'binary': support['digest'](path)}
    for key in ['PYRYCODE_SRC', 'PYRYCODE_RELAY_SRC']:
        if os.environ.get(key): value[key] = checkout(Path(os.environ[key]))
    return value


if __name__ == '__main__':
    try: print(json.dumps(snapshot(HERE.parent, Path.cwd().resolve()), sort_keys=True))
    except (OSError, ValueError, KeyError, TypeError, subprocess.SubprocessError):
        print('Desktop verifier inputs are unknown or changed; retained reuse disabled.', file=sys.stderr)
        sys.exit(1)
