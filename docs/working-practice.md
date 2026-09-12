# Shared development practice

This file applies to every Pyrycode Desktop pipeline role. It supplements the role prompt.
Repository-file ownership remains with each role. The refiner explicitly permits temporary publishing body files in the designated publishing folder.

## Knowledge

Read the target repository's `docs/knowledge/INDEX.md` and the topic relevant to
the ticket. Search the full catalog only when needed. Claude local memory is
disabled. Do not read or write it, and do not use the historical archive as
current instructions.

Builders record durable discoveries in the PR's Lessons learned section.
Verifiers record them in review comments. Refiners and product owners record them
on the issue, including work that ends without a PR. Link the finding from any
child that continues the work. Product lessons are folded into the owning topic
by the documentation stage. Workflow lessons are folded into this file or the
dispatcher docs by their maintainer. Do not create a second private note.

## Scope and sizing

Ask what the user can do differently before plumbing a descriptive identifier.
Do not imply capabilities that the identifier does not establish.

Read a merged blocker's code and its production call sites before trusting the
dependent ticket's forecast. The blocker can leave one caller unwired or already
have completed the dependent's proof. Check both possibilities.

Count constructors, narrow interfaces and test doubles before sizing a type change.
Compare the nearest shipped change of the same kind. Separate inserted lines from
deleted lines, and restrict the comparison to the new ticket's actual scope.
Recalculate measurements rather than copying old ticket estimates. Use the current
role's size limits, not thresholds in historical notes.

Dependency links and parent-child links are different. Check actual parentage for
split depth. A missing parent link can hide a descendant, while several blockers
do not make a root ticket a grandchild. Repair recorded lineage before using it as
a gate input. Follow the current split rules after that check.

## Review routing

Read security and routing labels from the issue, not the PR. Keep the two numbers
separate: PR for diff and comments, issue for labels and plan identity.

The pipeline uses one GitHub identity. GitHub cannot accept that author's approval
or change-request review on its own PR. Post the verdict as a PR comment and apply
the issue labels required by the role. Do not retry an impossible self-review.

Mechanical gates belong to the dispatcher as specified in the role prompt. Read
executed counts and failure evidence. A one-test baseline can omit a fixture-writing
sibling from the branch's full run. Compare the inputs and suite composition before
attributing a failure to the change. Search existing issues before filing another.

## Source and evidence checks

### Visual review

Builders and verifiers use [the shared visual-review recipe](visual-review.md).
Use a static component screenshot for isolated presentations and the existing
fake-transport Electron fixture for integrated screens. Read the recipe before
selecting a capture tool. Keep preview fixtures and images in role scratch space.

### Electron tests on macOS

Request approved execution outside the Codex sandbox before the first Electron
test launch. This applies to builders and verifiers, focused Playwright specs,
full suites, baseline comparisons and real-daemon tests. Unit tests and builds
can remain sandboxed. A sandbox launch rejection is an environment failure.
Do not count it as a product test failure or repeat it across the suite.
Never unset CODEX_SANDBOX or change Electron security settings to bypass the check.

On this MacBook, invoke the approved test helper as a separate command:
`/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-test WORKTREE [SPEC]`.
It runs the built app's fake-transport suite, or one relative `e2e/*.spec.ts` path.
Build first. The helper accepts only this Desktop checkout and its Git worktrees.
Use the normal approval path for real-daemon tests and other test options.
New Codex processes load the permission rule.

Use the target's `docs/knowledge/features/development-verification.md` when sizing,
building or reviewing code. It covers source-search limitations, validation boundaries,
protocol tests, capture evidence and artifact survival. Read the relevant section,
not the whole historical memory archive. Current code wins over an old observation.

## GitHub comments use body files

Write every issue or PR comment into a unique Markdown file under
`/Users/juhanailmoniemi/.codex/publish/pyrycode-desktop/`.
Create the file with the file-editing tool. Then call the approved pipeline helper
with `issue-comment ISSUE ABSOLUTE_BODY_PATH` or
`pr-comment PR ABSOLUTE_BODY_PATH` as a separate command.

Do not pass comment prose as an inline shell argument. Even valid shell quoting
can prevent Codex from recognizing the approved command. On ticket 1237, escaped
apostrophes in the comment caused the command to reach approval review instead.
The compatibility `comment ISSUE TEXT` form of the issue helper still exists,
but pipeline roles must use the body-file forms above.

Use the recovery rule below for a previously rejected action. Changing the
comment method alone does not clear a rejection.

## Codex approval rules on the MacBook

Juhana approved persistent Pyrycode Desktop reads, comment changes and any label edits
on 2026-09-11. Write helpers enforce `pyrycode/pyrycode-desktop`. Direct read rules match command prefixes only.
New Codex processes load them. Start a fresh process after a rules change.

For direct GitHub commands, put the repository option immediately after the
subcommand and before the issue or PR number. This order matches the rules:

```bash
gh issue view --repo pyrycode/pyrycode-desktop 2271 --json title,body,labels
gh pr view --repo pyrycode/pyrycode-desktop 2339 --json title,body,files
gh pr diff --repo pyrycode/pyrycode-desktop 2339
```

The same order applies to issue list/status and PR list/status/checks.
If the sandbox blocks the connection, request escalated execution for the same
repository-scoped command. These installed allow rules cover that request.
Do not override the repository with a second option or use shell substitutions.

The helper `/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-issue-action` also remains
approved. Use its absolute path with exactly three arguments:

- `comment ISSUE TEXT` is a compatibility form. Pipeline roles use body-file comments as required above.
- `add-label ISSUE LABEL` adds any label by name.
- `remove-label ISSUE LABEL` removes any label by name.

The helper fixes the repository and requires a numeric issue number.
There is no workflow-label whitelist. Extra arguments remain invalid.

Permission does not change role ownership. Builders return their structured
refinement outcome. The dispatcher still applies completion labels.
Other repository writes and unrelated issue edits retain their existing policy.
Previously rejected actions follow the recovery rule below.

### Remaining Codex pipeline actions

Juhana approved these routine operations on 2026-09-11. On this MacBook, use
`/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-pipeline-action` directly for the actions
below. These helper forms take precedence over raw Git and GitHub examples in
role prompts. Start a fresh Codex process to load the matching local allow rule.
If a sandbox call cannot reach GitHub, request escalated execution of the same
helper command. Do not wrap the helper in Python, shell substitutions or scripts.

| Arguments after the helper path | Effect |
| --- | --- |
| `push ISSUE` | Push the current `feature/ISSUE` branch normally. Requires the Pyrycode Desktop checkout or its worktree and the verified Pyrycode Desktop origin. |
| `issue-create TITLE BODY_FILE` | Create a Pyrycode Desktop issue. |
| `issue-edit ISSUE TITLE BODY_FILE` | Replace the issue title and body. Preserve the current title when only changing its body. |
| `pr-create ISSUE TITLE BODY_FILE` | Open a PR from `feature/ISSUE` into `main` after pushing. |
| `pr-edit PR TITLE BODY_FILE` | Update a PR title and body. |
| `pr-review PR VERDICT BODY_FILE` | Post `comment`, `approve` or `request-changes`. GitHub still forbids approving your own PR. Use the role's comment verdict when sharing an identity. |
| `issue-comment ISSUE BODY_FILE` or `pr-comment PR BODY_FILE` | Post a comment. |
| `issue-comment-edit-last ISSUE BODY_FILE` or `pr-comment-edit-last PR BODY_FILE` | Edit your last comment. |
| `issue-comment-delete-last ISSUE` or `pr-comment-delete-last PR` | Delete your last comment. |
| `label-edit NAME NEW_NAME COLOR DESCRIPTION` | Edit a label. Supply all fields, preserving existing values when unchanged. Color is six hexadecimal digits. |
| `board-add ISSUE` | Add the issue to Pyrycode Desktop board 7. |
| `board-status ISSUE STATUS` | Set its board status by exact name, such as `Backlog` or `In Development`. |
| `board-after ISSUE AFTER_ISSUE` | Place it after another Pyrycode Desktop issue on board 7. Use `top` instead of a number for first position. |
| `relations ISSUE` | Read parents, children and dependencies. Connection results report whether more than 100 exist. Do not treat a truncated result as complete. |
| `add-child PARENT CHILD` | Attach a child to its parent. Both are Pyrycode Desktop issue numbers. |
| `remove-child PARENT CHILD` | Remove that parent-child link. |
| `add-blocker ISSUE BLOCKER` | Mark the first issue as blocked by the second. |
| `remove-blocker ISSUE BLOCKER` | Remove that dependency. |

Pass titles and statuses as one quoted argument. Body files must have absolute
paths inside `/Users/juhanailmoniemi/.codex/publish/pyrycode-desktop/`.
Create a unique subfolder there for each task. Only put intended GitHub content
in this folder. Symbolic links, hard links and parent-directory traversal are
rejected. Direct GitHub comment and label-edit commands no longer have automatic
write approval. The helper takes no
extra flags, repository URLs, remote names, branch names or arbitrary API queries.
It resolves current project field and item IDs itself. Add an issue to the board
before setting its status or position. Existing comment and label commands above
remain available. Role ownership and the shared Git prohibitions still apply.

This approval covers sending ticket implementation, tests and workflow text to
`github.com/pyrycode/pyrycode-desktop`. The helper does not merge PRs, force-push, delete
branches, close issues or alter repository settings. Actions outside this set
retain their existing approval policy. General permission changes alone do not
clear a previously rejected action.

### Recovery after a rejected action

A new approval-review rejection stops the current run. Report the rejected
action and reason. Do not automatically retry it or change methods to evade it.

Operator review is complete when Juhana explicitly approves retrying the
identified action. Carry that approval into the next run as a direct task
instruction or a maintainer-recorded approval in this shared practice. Apply it
only to the action and ticket it names. Historical error comments do not cancel
that later approval. Do not require the same approval again.

Redispatch, an error-label removal, or an unverified issue comment alone is not
evidence of approval. If a new rejection occurs, stop and report it for review.

#### Approved recovery for ticket 1237, 2026-09-11

Juhana reviewed the rejection of the refinement comment on Desktop ticket 1237
and explicitly approved publishing the comment-method correction and retrying
that ticket. This approval was recorded by the maintaining assistant after the
operator conversation. The refiner may retry posting that refinement comment
using the approved body-file helper. The earlier rejection comments are history
of the reviewed failure, not an outstanding request for the same approval.
This approval does not cover a different action or a new rejection.


### Approved recovery for ticket 1242, 2026-09-11

Juhana asked the maintaining assistant to fix all five reported ticket failures using
the proposed solutions. This explicitly approves retrying the rejected refinement
comment for Desktop ticket 1242 through the approved body-file helper after fixing
the refiner's publishing-file restriction. The rejected direct GitHub command is
historical evidence of that reviewed action. This does not cover a new rejection.

## Role completion and live acceptance

Complete the work and checks assigned to your role. A builder that has implemented,
passed its scoped checks and opened its PR reports completed with an explicit handoff
of live acceptance to the dispatcher. Keep `needs-real-claude` on the issue. The
verifier reviews the implementation and preserves that gate requirement. Pending
live acceptance alone is not an agent error and is never evidence that the tests passed.

On the MacBook the Desktop dispatcher has an automatic real-Claude gate configured.
Its startup loads the existing Claude credential through 1Password. The gate retains
that credential; Codex agents deliberately do not inherit it. Do not copy credentials
into agent environments or ask an agent to obtain them to duplicate this gate.
The dispatcher must record actual executed tests before accepting live validation.
Missing credentials in the gate itself remain a blocking environment failure.
Permission rejections and unfinished work owned by the current role still block.


### Daemon binary used by live tests

Set `PYRY_BIN` to the dedicated test daemon under
`/Users/juhanailmoniemi/.local/share/pyrycode-desktop-tests/pyry` on this MacBook.
The maintainer builds it from a clean daemon revision containing the ticket's
prerequisites. Do not assume a closed daemon ticket means the executable on PATH
contains its change. Ticket 1252's first credentialed run used a September 8 binary
that predated its September 10 prerequisite and failed the model-change assertion.
When a new prerequisite requires a newer daemon, rebuild the test binary and record
the source revision before rerunning the gate. This does not replace the daemon
used by the running application.
