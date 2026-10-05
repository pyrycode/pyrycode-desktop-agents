"""Pre-verifier check tests. Each case builds a throwaway git repository shaped
like the Desktop app, with main as the base branch. No network: labels come
from --labels, or from an API address nothing listens on."""
import importlib.machinery
import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

sys.dont_write_bytecode = True
SCRIPT = Path(__file__).with_name("pre-verify-check")
loader = importlib.machinery.SourceFileLoader("pre_verify_check", str(SCRIPT))
spec = importlib.util.spec_from_loader("pre_verify_check", loader)
check = importlib.util.module_from_spec(spec)
loader.exec_module(check)

LEGS = """export function hostLeg(up: boolean): string {
  // 'Host Gone' in a comment is not a producer
  return up ? 'Host Connected' : 'Host Offline'
}
"""
ROW = """import { hostLeg } from './legs'
export function HostRow({ up }: { up: boolean }) {
  return (
    <div className="host-row">
      <span data-testid="host-dot" role="img" aria-label={hostLeg(up)} />
      <button>Rename host</button>
    </div>
  )
}
"""
SPEC = """import { test, expect } from '@playwright/test'
test('host row', async ({ page }) => {
  await expect(page.getByTestId('host-dot')).toBeVisible()
  await expect(page.getByRole('img', { name: 'Host Connected' })).toHaveCount(1)
  await page.getByText('Rename host').click()
})
"""


class Repo:
    def __init__(self, root):
        self.root = Path(root)
        self.git("init", "-q", "-b", "main")
        self.git("config", "user.email", "test@example.com")
        self.git("config", "user.name", "Test")
        self.git("config", "commit.gpgsign", "false")

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.root, check=True, capture_output=True, text=True).stdout

    def write(self, path, text):
        target = self.root / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(text)

    def commit(self, message="change"):
        self.git("add", "-A")
        self.git("commit", "-q", "-m", message)

    def run(self, *args, labels="", suite=False, env=None):
        command = [sys.executable, str(SCRIPT), "--base", "main", *args]
        if labels is not None:
            command += ["--labels", labels]
        if not suite:
            command.append("--no-suite")
        result = subprocess.run(command, cwd=self.root, capture_output=True, text=True,
                                env=dict(os.environ, **(env or {})))
        return result.returncode, result.stdout + result.stderr


class PreVerifyTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.repo = Repo(self.tmp.name)
        self.repo.write("src/legs.ts", LEGS)
        self.repo.write("src/HostRow.tsx", ROW)
        self.repo.write("src/other.ts", "export const unrelated = 'Unrelated text'\n")
        self.repo.write("e2e/host.spec.ts", SPEC)
        self.repo.commit("base")
        self.repo.git("checkout", "-q", "-b", "feature/42")

    def tearDown(self):
        self.tmp.cleanup()

    def plan(self, text):
        self.repo.write("docs/specs/architecture/42-host-row.md", "# Plan\n\n## Design\nx\n" + text)

    # -- main merged

    def test_passes_when_nothing_is_wrong(self):
        self.plan("")
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 0, out)
        self.assertIn("pre-verify: PASS, 3 checks passed, 2 skipped", out)

    def test_fails_when_main_is_not_merged(self):
        self.repo.git("checkout", "-q", "main")
        self.repo.write("src/other.ts", "export const unrelated = 'Moved on'\n")
        self.repo.commit("main moves")
        self.repo.git("checkout", "-q", "feature/42")
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("main merged: HEAD does not contain main", out)

    def test_fails_on_an_unfinished_merge(self):
        self.repo.git("checkout", "-q", "main")
        self.repo.write("src/other.ts", "export const unrelated = 'Main side'\n")
        self.repo.commit("main side")
        self.repo.git("checkout", "-q", "feature/42")
        self.repo.write("src/other.ts", "export const unrelated = 'Branch side'\n")
        self.repo.commit("branch side")
        subprocess.run(["git", "merge", "main"], cwd=self.repo.root, capture_output=True)
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("an unfinished merge is in the worktree (src/other.ts)", out)

    # -- security review

    def test_labelled_issue_without_security_section_fails(self):
        self.plan("")
        self.repo.commit()
        code, out = self.repo.run(labels="enhancement,security-sensitive")
        self.assertEqual(code, 1, out)
        self.assertIn("#42 carries security-sensitive, but docs/specs/architecture/42-host-row.md has no '## Security review'", out)

    def test_labelled_issue_with_security_verdict_passes(self):
        self.plan("\n## Security review\n\n**Verdict:** PASS\n\n### Findings\n- none\n")
        self.repo.commit()
        code, out = self.repo.run(labels="security-sensitive")
        self.assertEqual(code, 0, out)
        self.assertIn("has a ## Security review with a verdict", out)

    def test_security_heading_without_a_verdict_fails(self):
        self.plan("\n## Security review\n\nTo do.\n\n## Testing strategy\nVerdict lives elsewhere.\n")
        self.repo.commit()
        code, out = self.repo.run(labels="security-sensitive")
        self.assertEqual(code, 1, out)

    def test_labelled_issue_without_a_plan_fails(self):
        code, out = self.repo.run(labels="security-sensitive")
        self.assertEqual(code, 1, out)
        self.assertIn("no plan exists at docs/specs/architecture/42-*.md", out)

    def test_issue_number_comes_from_the_branch_or_the_flag(self):
        self.repo.git("checkout", "-q", "-b", "scratch")
        code, out = self.repo.run(labels="security-sensitive")
        self.assertIn("security review: skipped: no issue number", out)
        code, out = self.repo.run("--issue", "42", labels="security-sensitive")
        self.assertIn("#42 carries security-sensitive", out)

    def test_unreadable_labels_skip_the_security_check_without_failing(self):
        self.plan("")
        self.repo.commit()
        self.repo.git("remote", "add", "origin", "https://github.com/pyrycode/pyrycode-desktop.git")
        code, out = self.repo.run(labels=None, env={"PYRY_PRE_VERIFY_API": "http://127.0.0.1:9",
                                                    "GH_TOKEN": "", "GITHUB_TOKEN": ""})
        self.assertEqual(code, 0, out)
        self.assertIn("security review: skipped: could not read the labels of #42", out)

    # -- removed strings

    def test_removed_test_id_still_expected_by_a_browser_test_fails(self):
        self.repo.write("src/HostRow.tsx", ROW.replace(' data-testid="host-dot"', ""))
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("'host-dot' (removed from src/): e2e/host.spec.ts:3", out)

    def test_removed_jsx_text_still_expected_fails(self):
        self.repo.write("src/HostRow.tsx", ROW.replace("<button>Rename host</button>", "<button>Edit</button>"))
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("'Rename host' (removed from src/): e2e/host.spec.ts:5", out)

    def test_string_whose_only_producer_lost_its_caller_fails(self):
        # The #1695 shape: the label text stays in src/, but nothing renders it.
        row = ROW.replace("import { hostLeg } from './legs'\n", "").replace(" aria-label={hostLeg(up)}", "")
        self.repo.write("src/HostRow.tsx", row)
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("'Host Connected' (only producer `hostLeg` in src/legs.ts lost its last production caller): "
                      "e2e/host.spec.ts:4", out)

    def test_string_still_rendered_elsewhere_passes(self):
        self.repo.write("src/Other.tsx", "export const Other = () => <span data-testid=\"host-dot\" />\n")
        self.repo.write("src/HostRow.tsx", ROW.replace(' data-testid="host-dot"', ""))
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 0, out)

    def test_string_only_left_in_a_comment_still_counts_as_removed(self):
        self.repo.write("src/HostRow.tsx", ROW.replace(' data-testid="host-dot"', "")
                        + "// the old data-testid was 'host-dot'\n")
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)

    def test_negative_assertions_and_lines_this_branch_wrote_pass(self):
        self.repo.write("src/HostRow.tsx", ROW.replace(' data-testid="host-dot"', ""))
        self.repo.write("e2e/host.spec.ts", SPEC.replace(
            "await expect(page.getByTestId('host-dot')).toBeVisible()",
            "await expect(page.getByTestId('host-dot')).toHaveCount(0)"))
        self.repo.write("e2e/gone.spec.ts", "test('x', async ({ page }) => {\n"
                        "  await expect(page.getByTestId('host-dot')).not.toBeVisible()\n})\n")
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 0, out)

    def test_negative_assertion_already_on_main_passes(self):
        self.repo.git("checkout", "-q", "main")
        self.repo.write("e2e/absent.spec.ts", "test('x', async ({ page }) => {\n"
                        "  await expect(\n    page.getByRole('img', { name: 'Host Offline' })\n  ).toHaveCount(0)\n})\n")
        self.repo.commit("absent spec")
        self.repo.git("checkout", "-q", "feature/42")
        self.repo.git("merge", "-q", "main")
        row = ROW.replace("import { hostLeg } from './legs'\n", "").replace(" aria-label={hostLeg(up)}", "")
        self.repo.write("src/HostRow.tsx", row)
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("'Host Connected'", out)
        self.assertNotIn("Host Offline", out)

    def test_text_a_template_still_produces_passes(self):
        # The #1651 shape: a literal became a template that still renders it.
        self.repo.write("src/HostRow.tsx", ROW.replace("<button>Rename host</button>",
                                                       "<button>{`Rename ${noun}`}</button>"))
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 0, out)

    def test_prose_fragment_of_a_removed_template_is_not_traced(self):
        self.repo.git("checkout", "-q", "main")
        self.repo.write("src/stop.ts", "export const stopText = (c: string) => `Stopped (Claude reported: ${c})`\n")
        self.repo.write("e2e/stop.spec.ts", "test('x', async ({ page }) => {\n"
                        "  await expect(page.getByText('Stopped (Claude reported: overloaded)')).toBeVisible()\n})\n")
        self.repo.commit("stop text")
        self.repo.git("checkout", "-q", "feature/42")
        self.repo.git("merge", "-q", "main")
        self.repo.write("src/stop.ts", "export const stopText = (c: string) => `Stopped (${agent} reported: ${c})`\n")
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 0, out)

    def test_deleted_production_file_counts(self):
        self.repo.write("src/HostRow.tsx", "export {}\n")
        (self.repo.root / "src/HostRow.tsx").unlink()
        self.repo.commit()
        code, out = self.repo.run()
        self.assertEqual(code, 1, out)
        self.assertIn("'host-dot' (removed from src/)", out)

    # -- typecheck and unit suite

    def test_suite_failure_is_summarised(self):
        self.plan("")
        self.repo.commit()
        failing = "printf ' FAIL  src/a.test.ts > adds\\n'; exit 1"
        code, out = self.repo.run("--typecheck-cmd", "true", "--test-cmd", failing, suite=True)
        self.assertEqual(code, 1, out)
        self.assertIn("✗ unit suite: `" + failing + "` exited 1:\n    FAIL  src/a.test.ts > adds", out)
        self.assertIn("✓ typecheck", out)

    def test_typecheck_errors_are_summarised(self):
        failing = "echo \"src/a.ts(1,7): error TS2322: Type 'number' is not assignable\"; exit 2"
        code, out = self.repo.run("--typecheck-cmd", failing, "--test-cmd", "true", suite=True)
        self.assertEqual(code, 1, out)
        self.assertIn("    src/a.ts(1,7): error TS2322", out)


class LexerTests(unittest.TestCase):
    def test_literals_comments_and_templates(self):
        lexed = check.Lexed("const a = 'one' // 'two'\n/* 'three' */ const b = `x-${y ? 'four' : `in`}-z`\n")
        self.assertEqual([v for _, _, v in lexed.literals], ["one", "x-", "four", "in", "-z"])
        self.assertNotIn("two", lexed.code)
        self.assertIn("'one'", lexed.code)
        self.assertNotIn("one", lexed.masked)

    def test_apostrophe_in_jsx_text_spoils_one_line_at_most(self):
        lexed = check.Lexed("<p>Don't panic</p>\nconst c = 'kept'\n")
        self.assertIn("kept", [v for _, _, v in lexed.literals])

    def test_class_lists_split_into_tokens(self):
        self.assertEqual(check.candidate_strings("channel-list__host-dot conn-dot--"), ["channel-list__host-dot"])
        self.assertEqual(check.candidate_strings("Send now"), ["Send now"])
        self.assertEqual(check.candidate_strings("./legs"), [])
        self.assertEqual(check.candidate_strings("ok"), [])


if __name__ == "__main__":
    unittest.main()
