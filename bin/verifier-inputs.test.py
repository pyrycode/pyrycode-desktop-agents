import importlib.util
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch


class NativeProvenanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        spec = importlib.util.spec_from_file_location('support', Path(__file__).with_name('verifier-support.py'))
        cls.support = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(cls.support)

    def test_mode_switch_is_stable_and_binary_or_generator_change_disables_reuse(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d)
            binary = root / 'node_modules/better-sqlite3/build/Release/better_sqlite3.node'
            binary.parent.mkdir(parents=True)
            binary.write_bytes(b'node-native')
            source = {'versions': 'one'}
            with self.assertRaises(ValueError): self.support.verify_native(root, source)
            self.support.record_native(root, 'node', source)
            node = self.support.verify_native(root, source)
            binary.write_bytes(b'electron-native')
            with self.assertRaises(ValueError): self.support.verify_native(root, source)

            self.support.record_native(root, 'electron', source)
            self.assertEqual(node, self.support.verify_native(root, source))
            with self.assertRaises(ValueError): self.support.verify_native(root, {'versions': 'two'})
            binary.write_bytes(b'unknown')
            with self.assertRaises(ValueError): self.support.verify_native(root, source)

    def test_installed_runner_bytes_and_external_links_invalidate(self):
        with tempfile.TemporaryDirectory() as d:
            root = Path(d).resolve()
            runner = root / 'node_modules/vitest/vitest.mjs'
            runner.parent.mkdir(parents=True)
            runner.write_text('original runner')
            original = self.support.installed_tools(root)
            runner.write_text('changed runner with identical package version')
            self.assertNotEqual(original, self.support.installed_tools(root))
            runner.with_name('external').symlink_to(root / 'outside')
            with self.assertRaises(ValueError): self.support.installed_tools(root)



class RequirementInputsTests(unittest.TestCase):
    def test_ticket_body_labels_pr_body_and_merge_base_all_invalidate(self):
        spec = importlib.util.spec_from_file_location('inputs', Path(__file__).with_name('verifier-inputs.py'))
        inputs = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(inputs)
        state = {'issue': {'title': 'Repair', 'body': 'Required proof', 'labels': []},
                 'prs': [{'number': 22, 'body': 'PR requirements'}], 'base': 'a'*40}
        def run(*args, **kwargs):
            if args[0] == 'gh': return json.dumps(state['issue'] if args[1] == 'issue' else state['prs'])
            return 'feature/12' if args[-1] == '--show-current' else state['base']
        with patch.object(inputs, 'run', side_effect=run):
            old = inputs.requirements(Path('.'))
            for target, key, value in [('issue', 'body', 'Changed acceptance'), ('issue', 'labels', [{'name':'security-sensitive'}]),
                                       ('prs', 'body', 'Changed PR proof'), ('state', 'base', 'b'*40)]:
                item = state if target == 'state' else state[target][0] if target == 'prs' else state[target]
                original = item[key]
                item[key] = value
                self.assertNotEqual(old, inputs.requirements(Path('.')))
                item[key] = original
            state['issue']['labels'] = None
            with self.assertRaises(ValueError): inputs.requirements(Path('.'))



if __name__ == '__main__': unittest.main()
