#!/usr/bin/env python3
"""Retain fresh Vitest evidence and expose exact file#full-title JUnit identities."""
import argparse
import json
import os
from pathlib import Path
import re
import runpy
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
FILE = re.compile(r'(?:src|e2e|scripts)/(?:[A-Za-z0-9_-]+/)*[A-Za-z0-9_.-]+\.(?:test|spec)\.tsx?')


def parse_selection(raw, named):
    values = json.loads(raw)
    if not isinstance(values, list) or not 1 <= len(values) <= 64 or len(raw) > 32768:
        raise ValueError('selection must contain 1 to 64 exact file paths or file#full titles')
    for value in values:
        if not isinstance(value, str) or len(value) > 2048 or re.search(r'[\x00-\x1f\x7f]', value):
            raise ValueError('invalid test identity')
        file, separator, name = value.partition('#')
        if (not FILE.fullmatch(file) or '..' in file.split('/') or
                file.startswith('e2e/') and '.spec.' in file or
                named != bool(separator) or separator and not name.strip()):
            raise ValueError('selection requires exact unit file paths and full titles')
    return list(dict.fromkeys(values))


def read_report(report, root):
    root = root.resolve()
    if not isinstance(report, dict) or not isinstance(report.get('testResults'), list):
        raise ValueError('missing complete Vitest report')
    cases = {}
    for suite in report['testResults']:
        file = Path(suite['name']).resolve().relative_to(root).as_posix()
        if not FILE.fullmatch(file) or suite.get('status') not in {'passed', 'failed'} or suite.get('message'):
            raise ValueError('unknown unit suite identity or incomplete result')
        assertions = suite.get('assertionResults')
        if not isinstance(assertions, list): raise ValueError('missing assertions')
        if suite['status'] == 'failed' and not any(c.get('status') == 'failed' for c in assertions):
            raise ValueError('unnamed suite, setup or import failure')
        for case in assertions:
            name, status = case.get('fullName'), case.get('status')
            if not isinstance(name, str) or not name.strip() or re.search(r'[\x00-\x1f\x7f]', name):
                raise ValueError('unnamed test')
            if status not in {'passed', 'failed', 'pending', 'skipped', 'todo'}:
                raise ValueError('unfinished test result')
            identity = file + '#' + name
            if identity in cases: raise ValueError('ambiguous duplicate full test title')
            cases[identity] = {**case, 'file': file, 'status': status if status in {'passed', 'failed'} else 'skipped'}
    counts = {state: sum(c['status'] == state for c in cases.values()) for state in ['passed', 'failed', 'skipped']}
    if (report.get('numTotalTests') != len(cases) or report.get('numPassedTests') != counts['passed'] or
            report.get('numFailedTests') != counts['failed'] or
            report.get('numPendingTests', 0) + report.get('numTodoTests', 0) != counts['skipped'] or
            not counts['passed'] + counts['failed'] or
            report.get('success') != (counts['failed'] == 0) or report.get('snapshot', {}).get('failure')):
        raise ValueError('incomplete counts, no executed tests or unresolved runner failure')
    return cases


def check_audit(audit):
    if (not isinstance(audit, dict) or audit.get('version') != 1 or audit.get('completed') is not True or
            audit.get('suiteErrors') != [] or audit.get('unhandledErrors') != []):
        raise ValueError('suite lifecycle or global runner errors leave attribution unresolved')


def verify_selection(cases, names=None, files=None):
    executed = {name for name, case in cases.items() if case['status'] != 'skipped'}
    if names is not None and executed != set(names):
        raise ValueError('selected tests missing, skipped or extra tests executed')
    if files is not None and {cases[name]['file'] for name in executed} != set(files):
        raise ValueError('selected files missing, skipped or extra files executed')


def junit(cases):
    root = ET.Element('testsuites')
    for file in sorted({case['file'] for case in cases.values()}):
        selected = [case for case in cases.values() if case['file'] == file]
        suite = ET.SubElement(root, 'testsuite', name=file, tests=str(len(selected)),
                              failures=str(sum(c['status'] == 'failed' for c in selected)),
                              skipped=str(sum(c['status'] == 'skipped' for c in selected)))
        for case in selected:
            node = ET.SubElement(suite, 'testcase', classname=file, name=case['fullName'],
                                 time=str((case.get('duration') or 0) / 1000))
            if case['status'] == 'failed': ET.SubElement(node, 'failure').text = '\n'.join(case.get('failureMessages', []))
            if case['status'] == 'skipped': ET.SubElement(node, 'skipped')
    return ET.tostring(root, encoding='unicode')


def main():
    root = Path.cwd().resolve()
    policy = runpy.run_path(str(HERE.parent / 'dispatcher/scripts/test-selection.py'))
    policy['check'](root, 'desktop-unit', sys.argv[1:])
    parser = argparse.ArgumentParser(description=__doc__)
    selectors = parser.add_mutually_exclusive_group()
    selectors.add_argument('--tests-json')
    selectors.add_argument('--files-json')
    args = parser.parse_args()
    names = parse_selection(args.tests_json, True) if args.tests_json is not None else None
    files = parse_selection(args.files_json, False) if args.files_json is not None else None
    evidence = Path(os.environ.get('PYRY_GATE_EVIDENCE_DIR', root / 'build/dispatcher-tests')).resolve()
    evidence.mkdir(parents=True, exist_ok=True, mode=0o700)
    destination = Path(tempfile.mkdtemp(prefix='unit-', dir=evidence))
    preparation = subprocess.run([sys.executable, str(HERE / 'native-preparation.py'), 'node'], stdout=sys.stderr)
    if preparation.returncode: return preparation.returncode
    groups = {None: []} if names is None and files is None else {}
    for file in files or []: groups[file] = []
    for name in names or []:
        file, title = name.split('#', 1)
        groups.setdefault(file, []).append(title)
    combined, status = {}, 0
    for index, (file, titles) in enumerate(groups.items()):
        report = destination / f'{index}.json'
        # Vitest's mutable result cache sits inside node_modules by default.
        # Fresh execution keeps that output out of the installed-tool identity.
        command = ['node', str(root / 'node_modules/vitest/vitest.mjs'), 'run', '--no-cache']
        if file: command += [file]
        if titles: command += ['--testNamePattern', '^(?:' + '|'.join(re.escape(title) for title in titles) + ')$']
        audit_path = destination / f'{index}.audit.json'
        command += ['--reporter=json', '--reporter=' + str(HERE / 'unit-evidence-reporter.mjs'), '--outputFile=' + str(report)]
        env = {**os.environ, 'PYRY_DESKTOP_UNIT_AUDIT_PATH': str(audit_path)}
        with (destination / f'{index}.log').open('w') as log:
            result = subprocess.run(command, stdout=log, stderr=subprocess.STDOUT, env=env)
        check_audit(json.loads(audit_path.read_text()))
        cases = read_report(json.loads(report.read_text()), root)
        verify_selection(cases, [file + '#' + title for title in titles] if titles else None, [file] if file else None)
        if result.returncode and not any(c['status'] == 'failed' for c in cases.values()):
            raise ValueError('runner failed without complete named failure evidence')
        if combined.keys() & cases.keys(): raise ValueError('overlapping report identities')
        combined.update(cases)
        status = status or result.returncode
    xml = junit(combined)
    (destination / 'dispatcher.xml').write_text(xml + '\n')
    (destination / 'invocation.json').write_text(json.dumps({'exitCode': status, 'selectedTests': names,
        'selectedFiles': files, 'executed': sum(c['status'] != 'skipped' for c in combined.values())}) + '\n')
    print(xml)
    print(f'Desktop unit evidence: {destination}', file=sys.stderr)
    return status or int(any(c['status'] == 'failed' for c in combined.values()))


if __name__ == '__main__':
    try: sys.exit(main())
    except (OSError, ValueError, KeyError, ET.ParseError) as error:
        print(f'Desktop unit gate could not produce complete evidence: {error}', file=sys.stderr)
        sys.exit(1)
