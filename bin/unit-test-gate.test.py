import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET


class UnitEvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('unit_gate', Path(__file__).with_name('unit-test-gate.py'))
        cls.gate = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.gate)

    def report(self, root, statuses=('passed', 'failed', 'skipped')):
        names = ["outer comma, apostrophe's case", 'another case', 'optional']
        cases = [dict(fullName=name, status=status, duration=1, failureMessages=['original red'] if status == 'failed' else [])
                 for name, status in zip(names, statuses)]
        return dict(numTotalTests=len(cases), numPassedTests=statuses.count('passed'),
                    numFailedTests=statuses.count('failed'), numPendingTests=statuses.count('skipped'), numTodoTests=0,
                    success='failed' not in statuses,
                    testResults=[dict(name=str(root / 'src/a.test.ts'), status='failed' if 'failed' in statuses else 'passed',
                                      message='', assertionResults=cases)])

    def test_complete_result_preserves_failures_and_exact_names(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cases = self.gate.read_report(self.report(root), root)
            xml = self.gate.junit(cases)
            leaves = ET.fromstring(xml).findall('testsuite/testcase')
            self.assertEqual(len(leaves), 3)
            self.assertEqual(leaves[0].get('name'), "outer comma, apostrophe's case")
            self.assertIsNotNone(leaves[1].find('failure'))
            self.assertIsNotNone(leaves[2].find('skipped'))

    def test_incomplete_unknown_duplicate_and_runner_failure_are_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            for change in ['count', 'duplicate', 'unfinished', 'unnamed-error', 'mixed-error', 'outside']:
                value = self.report(root)
                if change == 'count': value['numTotalTests'] += 1
                if change == 'duplicate': value['testResults'][0]['assertionResults'][1]['fullName'] = value['testResults'][0]['assertionResults'][0]['fullName']
                if change == 'unfinished': value['testResults'][0]['assertionResults'][0]['status'] = 'running'
                if change == 'unnamed-error': value['testResults'].append(dict(name=str(root/'src/b.test.ts'), status='failed', message='import failed', assertionResults=[]))
                if change == 'mixed-error': value['testResults'][0]['message'] = 'afterAll failed alongside assertion'
                if change == 'outside': value['testResults'][0]['name'] = str(root.parent / 'foreign.test.ts')
                with self.subTest(change=change), self.assertRaises(ValueError): self.gate.read_report(value, root)

    def test_global_errors_and_missing_audit_are_never_named_evidence(self):
        self.gate.check_audit({'version': 1, 'completed': True, 'suiteErrors': [], 'unhandledErrors': []})
        for value in [{}, {'version': 1, 'completed': True, 'suiteErrors': [], 'unhandledErrors': ['unhandled rejection']},
                      {'version': 1, 'completed': True, 'suiteErrors': ['afterAll failed'], 'unhandledErrors': []}]:
            with self.assertRaises(ValueError): self.gate.check_audit(value)

    def test_green_parameterized_duplicates_keep_full_coverage_but_cannot_be_selected(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            value = self.report(root, ('passed', 'passed', 'skipped'))
            cases = value['testResults'][0]['assertionResults']
            cases[1]['fullName'] = cases[0]['fullName']
            actual = self.gate.read_report(value, root)
            self.assertEqual(len(ET.fromstring(self.gate.junit(actual)).findall('.//testcase')), 3)
            self.gate.verify_selection(actual, files=['src/a.test.ts'])
            with self.assertRaises(ValueError): self.gate.verify_selection(actual, ['src/a.test.ts#'+cases[0]['fullName']])

    def test_selection_rejects_missing_skipped_and_extra_execution(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            cases = self.gate.read_report(self.report(root), root)
            for names in [['src/a.test.ts#missing'], ['src/a.test.ts#optional'], ["src/a.test.ts#outer comma, apostrophe's case"]]:
                with self.subTest(names=names), self.assertRaises(ValueError): self.gate.verify_selection(cases, names)
            self.gate.verify_selection(cases, ["src/a.test.ts#outer comma, apostrophe's case", 'src/a.test.ts#another case'])

    def test_literal_selection_rejects_paths_and_preserves_regex_characters(self):
        names = self.gate.parse_selection('["src/a.test.ts#outer [x], apostrophe\u0027s case"]', True)
        self.assertEqual(names, ["src/a.test.ts#outer [x], apostrophe's case"])
        for value in ['[]', '["../a.test.ts#x"]', '["src/a.test.ts"]', '["src/*.test.ts#x"]']:
            with self.subTest(value=value), self.assertRaises(ValueError): self.gate.parse_selection(value, True)


if __name__ == '__main__': unittest.main()
