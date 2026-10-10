# Shared development practice

Every Pyrycode Desktop pipeline role reads this alongside its role file. Your role file decides what you may write; nothing here widens that. The last two sections apply only to the roles they name.

## Filing follow-up tickets

When your role authorises filing a bug or follow-up, search open issues for an existing ticket first. Link an existing ticket instead of creating a duplicate. Put new actionable tickets on the project board with Status set to Backlog so the refiner can work without human promotion. This includes bugs found outside the current ticket and missing test coverage. An unknown technical cause is investigation work for Backlog. Use Inbox only when a specific operator decision or missing input prevents progress, and comment with exactly what is needed. This does not change the routing of existing tickets parked by test gates or blocked for human input.

## Knowledge

Read the target repository's `docs/knowledge/INDEX.md` and the topic that owns the ticket. `docs/knowledge/CATALOG.md` is over 500 KB, so search it rather than reading it whole. Current code wins over an old observation. The per-ticket notes under `docs/knowledge/codebase/` and `docs/PROJECT-MEMORY.md` are history, not current instructions.

When sizing, building or reviewing code, use the target's `docs/knowledge/features/development-verification.md`. It covers source-search limits, validation boundaries, protocol tests, capture evidence and artifact survival. Read the section you need.

Claude local memory is disabled. Do not read or write it, and do not keep a private note of your own. Durable discoveries go where the next stage will find them: builders in the PR's Lessons learned section, verifiers in review comments, refiners on the issue, including work that ends without a PR. Link the finding from any child ticket that continues the work. The documentation stage folds product lessons into the owning topic. Workflow lessons are folded into this file or the dispatcher docs by their maintainer.

## GitHub API budget

Managed runs use the shared GitHub connection. Use the installed `gh` command and preserve its inherited `GH_CONFIG_DIR`. Do not clear that setting or use another API client to bypass the shared allowance. If the connection is unavailable, retain local results and report the temporary failure.

Every dispatcher, agent and interactive session shares one GitHub account and its 5000 GraphQL points an hour. When they run out, every `gh` call in the pipeline fails until the hourly reset.

- To learn a ticket's board column, read the ticket: `gh issue view <n> --json projectItems` costs about 2 points. Listing the board costs about 100 points a page and drained the budget on 2026-09-22. List it at most once a run, and only when you need every card.
- Check the budget with `gh api graphql -f query='{rateLimit{remaining resetAt}}'`. The `gh api rate_limit` endpoint misreports this bucket.

## GitHub writes

Pass every issue body, PR body and comment as a file, never as inline text in a command. Under Codex, even correctly quoted inline prose can stop the approved command from being recognised: on ticket 1237, escaped apostrophes in a comment sent the command to approval review instead.

Under Claude, `gh` with `--body-file` and the GraphQL equivalents of the helper actions below are fine, and the helpers work too. The rest of this section is what Codex needs on the MacBook.

### Codex approval rules on the MacBook

Juhana approved these on 2026-09-11. New Codex processes load the rules, so start a fresh process after a rules change.

**Reads.** Direct read rules match command prefixes only, so put the repository option immediately after the subcommand and before the number:

```bash
gh issue view --repo pyrycode/pyrycode-desktop 2271 --json title,body,labels
gh pr view --repo pyrycode/pyrycode-desktop 2339 --json title,body,files
gh pr diff --repo pyrycode/pyrycode-desktop 2339
```

The same order applies to issue list and status, and to PR list, status and checks. If the sandbox blocks the connection, request escalated execution of the same command. Do not add a second repository option or use shell substitutions.

**Writes.** Direct GitHub write commands have no automatic approval. Use `/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-pipeline-action` with the arguments below, as a separate command, not wrapped in Python, shell substitutions or scripts. If a sandboxed call cannot reach GitHub, request escalated execution of the same helper command.

| Arguments after the helper path | Effect |
| --- | --- |
| `push ISSUE` | Push the current `feature/ISSUE` branch normally. Requires the Pyrycode Desktop checkout or its worktree and the verified Pyrycode Desktop origin. |
| `issue-create TITLE BODY_FILE` | Create a Pyrycode Desktop issue. |
| `issue-edit ISSUE TITLE BODY_FILE` | Replace the issue title and body. Pass the current title when only the body changes. |
| `pr-create ISSUE TITLE BODY_FILE` | Open a PR from `feature/ISSUE` into `main` after pushing. |
| `pr-edit PR TITLE BODY_FILE` | Update a PR title and body. |
| `pr-review PR VERDICT BODY_FILE` | Post `comment`, `approve` or `request-changes`. GitHub forbids approving your own PR, and the pipeline has one identity, so use the role's comment verdict. |
| `issue-comment ISSUE BODY_FILE` or `pr-comment PR BODY_FILE` | Post a comment. |
| `issue-comment-edit-last ISSUE BODY_FILE` or `pr-comment-edit-last PR BODY_FILE` | Edit your last comment. |
| `issue-comment-delete-last ISSUE` or `pr-comment-delete-last PR` | Delete your last comment. |
| `label-edit NAME NEW_NAME COLOR DESCRIPTION` | Edit a label. Supply all fields, keeping existing values when unchanged. Color is six hexadecimal digits. |
| `board-add ISSUE` | Add the issue to Pyrycode Desktop board 7. |
| `board-status ISSUE STATUS` | Set its board status by exact name, such as `Backlog` or `In Development`. |
| `board-after ISSUE AFTER_ISSUE` | Place it after another Pyrycode Desktop issue on board 7. Use `top` instead of a number for first position. |
| `relations ISSUE` | Read parents, children and dependencies. Each list reports whether more than 100 exist; a truncated list is not complete. |
| `add-child PARENT CHILD` | Attach a child to its parent. |
| `remove-child PARENT CHILD` | Remove that parent-child link. |
| `add-blocker ISSUE BLOCKER` | Mark the first issue as blocked by the second. |
| `remove-blocker ISSUE BLOCKER` | Remove that dependency. |

Labels are added and removed with `/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-issue-action add-label ISSUE LABEL` or `remove-label ISSUE LABEL`, any label by name, exactly three arguments. Its `comment ISSUE TEXT` form exists for compatibility; pipeline roles use the body-file comment actions instead.

Pass titles and statuses as one quoted argument. Body files take absolute paths inside a unique subfolder per task of `/Users/juhanailmoniemi/.codex/publish/pyrycode-desktop/`. Put only intended GitHub content there. Symbolic links, hard links and parent-directory traversal are rejected. The helpers fix the repository, require numeric issue numbers, take no extra flags, URLs, remote or branch names or arbitrary queries, and resolve project field and item ids themselves. Add an issue to the board before setting its status or position.

This approval covers sending ticket implementation, tests and workflow text to `github.com/pyrycode/pyrycode-desktop`. The helpers do not merge PRs, force-push, delete branches, close issues or alter repository settings; those keep their existing approval policy. Permission does not change role ownership: the dispatcher still applies completion labels, and a builder returns its structured refinement outcome rather than routing the ticket itself.

## Denied and rejected actions

The pipeline is non-interactive, so a question reaches no one.

**Under Claude,** when the dispatcher denies an operation, such as a hard reset, a force push or a delete outside the worktree, do not try another form of it. Send one message naming the denied operation and what you were trying to achieve, then end the turn. The dispatcher applies `error:<agent>:permission_denied` and routes the ticket to the operator. On pyrycode #398 the developer asked an absent operator instead, burned its remaining turns, and stranded its work.

**Under Codex,** an approval-review rejection of a necessary action stops the run. Report status blocked with the rejected action and the reason. Do not retry it or change method to get around it.

### Recovery after a rejected action

A rejected action may be retried only after Juhana explicitly approves retrying it. That approval reaches the next run as a direct task instruction, or as an approval the maintainer records in this file. It applies only to the action and ticket it names, and once given it is not required again; earlier error comments do not cancel it. A redispatch, a removed error label or an unverified issue comment is not approval. A new rejection stops the run again. Changing the comment method or a general permission change does not clear an earlier rejection either.

No recorded approvals are outstanding. The 2026-09-11 approvals for tickets 1237 and 1242 were used, and both tickets closed that day.

## When an MCP or plugin tool is missing

If a tool you need from an MCP server or plugin, such as Figma, is missing from your tools or fails to connect, stop at once. Do no further work and do not look for a workaround. End your final message with this line, naming the server or plugin, as its very last line: `TOOL_UNAVAILABLE: <server or plugin name>`, for example `TOOL_UNAVAILABLE: figma`. Under Codex, return status `blocked` with that line last in the summary. The dispatcher retries the run a few times, then parks the ticket. This covers only a tool that is missing or cannot be reached. A tool that answers with an error, for example for a bad argument or a node that does not exist, is not this case. Neither is a tool your instructions give a fallback for, such as command-line search when a search tool is unavailable.

## Role completion and live acceptance

Complete the work and checks your role owns, and hand later stages theirs explicitly. Pending work owned by a later stage, including the dispatcher's live gate, is not an error, and it is never evidence that something passed. Permission rejections and unfinished work owned by your own role still block.

A builder that has implemented, passed its scoped checks and opened its PR reports completed and hands live acceptance to the dispatcher, keeping `needs-real-claude` on the issue. The verifier preserves that requirement.

The MacBook dispatcher runs the real-Claude gate automatically, with the Claude credential its startup loads through 1Password. Codex agents deliberately do not inherit that credential. Do not copy credentials into agent environments, or fetch them to duplicate the gate. The gate must record the tests that actually executed before it accepts live validation, and a missing credential in the gate itself is a blocking environment failure.

## For roles that size or plan work: refiner and builder

- Before carrying a new descriptive identifier through the code, ask what the user can do differently with it. Do not let a name imply a capability the code does not establish.
- Before trusting a dependent ticket's forecast, read the merged blocker's code and its production call sites. The blocker may have left a caller unwired, or may already have delivered the dependent's proof.
- Before sizing a type change, count its constructors, narrow interfaces and test doubles. Compare the nearest shipped change of the same kind, separating inserted from deleted lines and restricting the comparison to the new ticket's scope. Recalculate rather than copying old estimates, and use the current size table, not thresholds in historical notes.
- Parent-child links and blocker links are different. Split depth reads actual parentage: a missing parent link can hide a descendant, and several blockers do not make a root ticket a grandchild. Repair recorded lineage before using it as a gate input.

## For roles that run or review code: builder and verifier

**Labels and numbers.** Read security and routing labels from the issue, not the PR. The PR number is for the diff and comments; the issue number is for labels and the plan.

**Failures.** Mechanical gates belong to the dispatcher, as the role file describes. Read executed counts and failure evidence, not just exit codes. A one-test baseline can leave out a fixture-writing sibling that the branch's full run includes, so compare inputs and suite composition before attributing a failure to the change. Search existing issues before filing another.

**Visual review.** Use [the shared visual-review recipe](visual-review.md): a static component screenshot for an isolated presentation, the existing fake-transport Electron fixture for an integrated screen. Read it before choosing a capture tool. Keep preview fixtures and images in your scratch space.

### Electron tests on macOS

Under Codex, request approved execution outside the sandbox before the first Electron launch. This covers focused Playwright specs, full suites, baseline comparisons and real-daemon tests. Unit tests and builds can stay sandboxed. A sandbox launch rejection is an environment failure: do not count it as a product test failure or repeat it across the suite. Never unset `CODEX_SANDBOX` or change Electron security settings to get past the check.

On this MacBook, the approved test helper runs as a separate command:
`/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-test WORKTREE [SPEC]`.
Build first. It runs the built app's fake-transport suite, or one relative `e2e/*.spec.ts` path, and accepts only this Desktop checkout and its worktrees. Real-daemon tests and other test options use the normal approval path.

### Daemon binary used by live tests

Set `PYRY_BIN` to the dedicated test daemon at `/Users/juhanailmoniemi/.local/share/pyrycode-desktop-tests/pyry`. The maintainer builds it from a clean daemon revision containing the ticket's prerequisites. A closed daemon ticket does not mean the executable on PATH contains its change: ticket 1252's first credentialed run used a September 8 binary that predated its September 10 prerequisite and failed the model-change assertion. When a prerequisite needs a newer daemon, rebuild the test binary and record its source revision before rerunning the gate. This does not replace the daemon the running application uses.
