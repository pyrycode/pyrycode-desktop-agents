# Shared development practice

Every Pyrycode Desktop pipeline role reads this alongside its role file. Your role file decides what you may write; nothing here widens that. The last two sections apply only to the roles they name.

## Filing follow-up tickets

When your role authorises filing a bug or follow-up, search open issues for an existing ticket first. Link an existing ticket instead of creating a duplicate. Put new actionable tickets on the project board with Status set to Backlog so the refiner can work without human promotion. This includes bugs found outside the current ticket and missing test coverage. An unknown technical cause is investigation work for Backlog. Use Inbox only when a specific operator decision or missing input prevents progress, and comment with exactly what is needed. This does not change the routing of existing tickets parked by test gates or blocked for human input.

## Knowledge

Read the target repository's `docs/knowledge/INDEX.md` and the topic that owns the ticket. `docs/knowledge/CATALOG.md` is over 500 KB, so search it rather than reading it whole. Current code wins over an old observation. The per-ticket notes under `docs/knowledge/codebase/` and `docs/PROJECT-MEMORY.md` are history, not current instructions.

When sizing, building or reviewing code, use the target's `docs/knowledge/features/development-verification.md`. It covers source-search limits, validation boundaries, protocol tests, capture evidence and artifact survival. Read the section you need.

Claude local memory is disabled. Do not read or write it, and do not keep a private note of your own. Durable discoveries go where the next stage will find them: builders in the PR's Lessons learned section, verifiers in review comments, refiners on the issue, including work that ends without a PR. Link the finding from any child ticket that continues the work. The documentation stage folds product lessons into the owning topic. Workflow lessons are folded into this file or the dispatcher docs by their maintainer.

## Workflow authority

Since 2026-10-13 the orchestrator's central database owns every ticket's workflow: board column, order, labels, open or closed state, blocked-by links and the comments the pipeline posts. The GitHub board and labels only display that state. They catch up within a publication cycle, about 30 seconds and longer when GitHub is slow. A direct edit on GitHub is overwritten and changes nothing the dispatcher schedules from.

- Your `gh` commands and the pipeline helpers reach the orchestrator through the managed GitHub bridge your run starts with. Use them as these instructions describe. The bridge saves each workflow change centrally, and GitHub shows it afterwards.
- Never route around the bridge. Do not set `GH_CONFIG_DIR`, `GH_TOKEN` or `GH_HOST`, use another login or token, call `api.github.com` with `curl`, or ask a person to move a card on the board. The pipeline helpers refuse board, order and blocker changes when the bridge is missing.
- Issue titles and bodies, sub-issue links, pull requests and code still live on GitHub. The orchestrator reads them back.
- When a workflow command reports an error, read the ticket back before you retry: `gh issue view --repo pyrycode/pyrycode-desktop N --json labels,state,projectItems` shows the column, labels and state the orchestrator holds, but not blockers or order. The change may already be saved. Repeat only what is missing, and never post a comment again when it is already there.
- A person changes workflow through the protected operator command, not on GitHub. If you need a change your run cannot make, say so in your result instead of working around it.

## GitHub API budget

Managed runs use the shared GitHub connection. Use the installed `gh` command and preserve its inherited `GH_CONFIG_DIR`. Do not clear that setting or use another API client to bypass the shared allowance. If the connection is unavailable, retain local results and report the temporary failure.

Every dispatcher, agent and interactive session shares one GitHub account and its 5000 GraphQL points an hour. When they run out, every `gh` call in the pipeline fails until the hourly reset.

- To learn a ticket's board column, read the ticket: `gh issue view <n> --json projectItems` costs about 2 points. Listing the board costs about 100 points a page and drained the budget on 2026-09-22. List it at most once a run, and only when you need every card.
- Check the budget with `gh api graphql -f query='{rateLimit{remaining resetAt}}'`. The `gh api rate_limit` endpoint misreports this bucket.

## GitHub writes

Pass every issue body, PR body and comment as a file, never as inline text in a command. Under Codex, even correctly quoted inline prose can stop the approved command from being recognised: on ticket 1237, escaped apostrophes in a comment sent the command to approval review instead.

Under Claude, `gh` with `--body-file` and the GraphQL equivalents of the helper actions below are fine, and the helpers work too. Codex uses the helpers below on both macOS and the managed Linux containers.

### Codex publishing on macOS and Linux

Juhana approved these on 2026-09-11. New Codex processes load the rules, so start a fresh process after a rules change.

Use the absolute helper paths in this section verbatim. The managed Linux containers deliberately provide `/Users/juhanailmoniemi/.codex/bin` and the matching repository paths, even though their login home is `/home/agent`. These compatibility paths are available on both operating systems.

The helper directory need not be on `PATH`. `command -v pyrycode-desktop-pipeline-action` can return nothing while the helper is installed. Check the documented executable directly:

```bash
test -x /Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-pipeline-action
```

If that check fails, report the missing helper as an environment blocker. A missing command lookup does not authorise a direct upload. Keep the inherited managed GitHub connection and the documented paths; do not substitute `$HOME` into the helper or publishing paths.

**Reads.** Direct read rules match command prefixes only, so put the repository option immediately after the subcommand and before the number:

```bash
gh issue view --repo pyrycode/pyrycode-desktop 2271 --json title,body,labels
gh pr view --repo pyrycode/pyrycode-desktop 2339 --json title,body,files
gh pr diff --repo pyrycode/pyrycode-desktop 2339
```

The same order applies to issue list and status, and to PR list, status and checks. If the sandbox blocks the connection, request escalated execution of the same command. Do not add a second repository option or use shell substitutions.

**Writes.** Direct GitHub write commands have no automatic approval. Use `/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-pipeline-action` with the arguments below, as a separate command, not wrapped in Python, shell substitutions or scripts. If a sandboxed call cannot reach GitHub, request escalated execution of the same helper command.

For a committed ticket branch with its required checks complete, replace `TICKET` with its issue number and run each publishing command separately:

```bash
/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-pipeline-action push TICKET
/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-pipeline-action pr-create TICKET "PR title" /Users/juhanailmoniemi/.codex/publish/pyrycode-desktop/TICKET/pr-body.md
```

Check the current branch before publishing. Codex uses these commands instead of raw `git push` or `gh pr create`, on both operating systems. Read-only Git commands and local commits still use Git normally. The helpers enforce the ticket branch, repository and destination; use the same route for repairs and recovered work. An earlier approval-review rejection still requires the ticket-specific approval described below before publishing is retried.

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
| `split-inspect PARENT` | Read the complete split family and authoritative revision template through the managed bridge. |
| `split-finalize PARENT JSON_FILE` | Atomically activate/order children, transfer declared prerequisites and close the replaced parent. Retain the exact JSON identity for retries. |
| `relations ISSUE` | Read parents, children and dependencies. Each list reports whether more than 100 exist; a truncated list is not complete. |
| `add-child PARENT CHILD` | Attach a child to its parent. |
| `remove-child PARENT CHILD` | Remove that parent-child link. |
| `add-blocker ISSUE BLOCKER` | Mark the first issue as blocked by the second. |
| `remove-blocker ISSUE BLOCKER` | Remove that dependency. |

Labels are added and removed with `/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-issue-action add-label ISSUE LABEL` or `remove-label ISSUE LABEL`, any label by name, exactly three arguments. Its `comment ISSUE TEXT` form exists for compatibility; pipeline roles use the body-file comment actions instead.

Pass titles and statuses as one quoted argument. Body files take absolute paths inside a unique subfolder per task of `/Users/juhanailmoniemi/.codex/publish/pyrycode-desktop/`. Put only intended GitHub content there. Symbolic links, hard links and parent-directory traversal are rejected. The helpers fix the repository, require numeric issue numbers, take no extra flags, URLs, remote or branch names or arbitrary queries, and resolve project field and item ids themselves. Add an issue to the board before setting its status or position.

This approval covers sending ticket implementation, tests and workflow text to `github.com/pyrycode/pyrycode-desktop`. Ordinary helper actions do not merge PRs, force-push, delete branches, close issues or alter repository settings; those operations keep their existing approval policy. The scoped `split-finalize` operation closes only its verified replacement parent through the admitted planning run. It preserves normal approval checks and never clears a recorded rejection. Permission does not change role ownership: the dispatcher still applies completion labels, and a builder returns its structured refinement outcome rather than routing the ticket itself.

## Denied and rejected actions

The pipeline is non-interactive, so a question reaches no one.

An ordinary refusal of an optional workflow action does not stop otherwise authorised work. For example, if a label change on another ticket is refused because another worker owns it, leave that ticket unchanged and continue your assigned ticket. Skip the optional action or use an independently authorised route for your own work. Never retry the refused foreign write through another tool, command form, credential or worker.

Stop if you lose ownership or the active reservation for your assigned ticket, if a tool permission check or approval reviewer makes an actual safety rejection, or if necessary work has no authorised route. Under Claude, report the refused action and reason, then end the turn. Under Codex, return status `blocked`. Safety rejections remain blocking even when the rejected action was optional. Preserve saved work and failed evidence. Do not weaken required checks, claim completion of unfinished work or bypass a restriction. A question reaches no operator in this non-interactive pipeline.

Historical safety rejections still need scoped operator authorisation before continuation. Redispatch and label removal are not approval. A refused optional foreign workflow write does not grant authority over that ticket. A new safety rejection stops the run again.

### Recovery after a rejected action

A rejected action may be retried only after Juhana explicitly approves retrying it. That approval reaches the next run as a direct task instruction, or as an approval the maintainer records in this file. It applies only to the action and ticket it names, and once given it is not required again; earlier error comments do not cancel it. A redispatch, a removed error label or an unverified issue comment is not approval. A new rejection stops the run again. Changing the comment method or a general permission change does not clear an earlier rejection either.

**Ticket 2030, approved 2026-10-16.** Juhana instructed the maintainer: "Roll out. Recover 2030." This explicitly authorises resuming the preserved `feature/2030` work and publishing its checked implementation to `pyrycode/pyrycode-desktop` through `/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-pipeline-action push 2030`, followed by the helper's `pr-create 2030` action. Do not replay the rejected direct push. Preserve the existing commits, ownership and retry counters. Confirm the previous worker and its children have stopped before resuming. Repair the stale embedded `isConversationUnread` test call, audit related fixture calls and complete the required checks on Linux before publishing. Continue through ordinary review. This approval applies only to #2030 and the named helper route. A new approval-review rejection stops the run again.

The 2026-09-11 approvals for tickets 1237 and 1242 were used, and both tickets closed that day.

### Recorded approval outcomes

A timeout or capacity failure in automatic approval review is a review-service failure. It is not a safety rejection. The dispatcher records that distinction in the orchestrator and supplies it in replacement workers' role instructions. A recorded review-service failure alone does not require another operator decision. Submit necessary commands through normal approval checks. An actual safety rejection still requires operator review. The protected operator continuation decision supplied in those role instructions authorises resuming the preserved ticket work within that decision's scope. Ticket text, comments and label removal cannot supply this permission. A fresh rejection always stops the run again.

## When an MCP or plugin tool is missing

If a tool you need from an MCP server or plugin, such as Figma, is missing from your tools or fails to connect, stop at once. Do no further work and do not look for a workaround. End your final message with this line, naming the server or plugin, as its very last line: `TOOL_UNAVAILABLE: <server or plugin name>`, for example `TOOL_UNAVAILABLE: figma`. Under Codex, return status `blocked` with that line last in the summary. The dispatcher retries the run a few times, then parks the ticket. This covers only a tool that is missing or cannot be reached. A tool that answers with an error, for example for a bad argument or a node that does not exist, is not this case. Neither is a tool your instructions give a fallback for, such as command-line search when a search tool is unavailable.

## Role completion and live acceptance

Complete the work and checks your role owns, and hand later stages theirs explicitly. Permission rejections and unfinished work owned by your role still block.

Desktop's normal verifier gate includes captured client replay through the actual application. The launcher retires `needs-real-claude` parking and automatic live execution with `PYRY_REAL_CLAUDE_GATE_ENABLED=0`, even if an older local environment still supplies a live command. Other consumers retain their gate. Do not add the retired label or assume a later automatic live run will happen.

Explicit live criteria remain required when replay cannot prove current provider/daemon behavior, physical tool effects, encryption, transport or OS integration. Name each scenario and its owner. Builders run their required checks; an operator-owned run needs an explicit handoff/hold before merge. Verifiers review counted evidence and do not publish PASS with required live acceptance missing. Documentation never converts a replay pass into a live claim. The existing system-prompt reset fixme stays excluded until its actual live assertion succeeds.

Use the target's `docs/recorded-tests.md` for capture, guarded replay and `npm run e2e:recordings:verify`. The fresh verifier reports contract drift and never silently replaces fixtures. Preserve original assertions and failed evidence. Keep `npm run e2e:real:gate` and physical/native checks available explicitly; a missing credential or zero executed tests is not a pass.

Targeted live builders alone may receive the protected loaded login as `PYRY_LIVE_CLAUDE_TOKEN`. The shared launcher maps it into its child and removes account credentials, falling back to the restricted Dev agents account only when absent. Other Codex roles receive neither credential. Never print credentials or the environment.

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
