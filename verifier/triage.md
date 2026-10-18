# Triage — Pyrycode Desktop verifier

Read this when your gate note says **TRIAGE MODE**, or when no gate note arrived and you run the gates yourself. The goal is to decide, mechanically where possible, whether this PR caused the red. A PR that fixes one thing while unmasking older fragility elsewhere should not be sent back for rework it cannot do. Before this procedure existed, such PRs burned three or more rework cycles.

## Retained evidence comes first

Read the full stdout, stderr and structured gate reports at their retained paths. A tail is a pointer to those logs. Do not repeat a complete suite to obtain a longer excerpt. Preserve the original failure even when a later exact retry passes.

The dispatcher runs source review alongside the configured automatic checks. Every required step must finish before approval. A passing prefix never certifies an unfinished later step. Continue bounded source review on a red when the build and evidence make it reliable. Report all independent findings together.

## Running the gates yourself

Only when no gate note was supplied. Read the actual `PYRY_VERIFIER_GATES` list and run those steps once in order. Missing or empty configuration is a blocker. Do not substitute an old list or use a pipe that loses the process exit status. Keep separate stdout, stderr and status for every command.

The launcher installs a structured unit gate and prepares the native database separately for Node and Electron. A failed native preparation is an environment failure. Do not use a later manual pass to override a failed required gate.

## Classify the red

- A named unit or browser failure needs exact retry and unchanged-main attribution below.
- A failed branch or security check needs its named requirement repaired.
- A format or documentation error needs attribution against the same unchanged files and rules before assigning product rework.
- A build error with a confirmed source defect returns that finding to the builder.
- Missing results, a crashed runner, failed dependency installation, failed native preparation or an unavailable baseline leave evidence incomplete. Preserve the logs and report blocked. These signals alone do not establish a product defect.

## Exact failure comparisons

The automatic unit gate emits JUnit identities shaped `relative/test/file.test.ts#full test title`. Its saved JSON reports retain the original Vitest results. Browser checks retain their existing structured Playwright selection.

When automatic classification already completed, use its recorded results. Do not repeat its comparisons. Otherwise:

1. Read the exact unresolved failing identities from the retained complete report.
2. Read that gate's comparison template in `PYRY_VERIFIER_GATE_FORMATS`.
3. Retry only those names once on the proposed tree. Preserve the original failure separately.
4. Compare only names that still fail with the recorded merged-main commit in an isolated worktree. Use the same toolchain and native preparation. No complete-suite fallback is permitted.
5. Record selected names, actual executed identities and passed, failed and skipped counts. Every selected name must execute. A missing name, skipped result, extra executed name, setup failure or incomplete report leaves attribution unresolved.

For unit tests, the versioned helper takes `--tests-json` with a JSON array of exact `file#full title` strings. Pass the JSON as one argument. It escapes literal regular-expression characters and checks the actual returned identities. Never shorten a full title or replace the selector with a catch-all expression.

Use the configured browser template for Playwright. It still installs dependencies, builds and prepares the Electron database before the exact selected run. A baseline worktree needs all of those steps. Never launch Electron with a Node-built database library.

## Routing after comparison

- A named failure that passes on unchanged main and fails on the proposed change is a regression. Return the proven defect to the builder with the original evidence and independent source findings.
- A failure on both sources is inherited. A passing same-tree retry is intermittent. Keep the original red and link the existing tracker or use the search-first procedure below. These classifications do not waive later required gates.
- Missing attribution or required gate completion remains blocked. Do not publish PASS or guess that missing baseline execution proves a regression.

Approval requires the dispatcher's complete accepted evidence for every configured gate. A manual exact comparison cannot override a red or unfinished automatic gate.

## Redact before quoting any log

**Every** `<redacted tail>` in the templates below — the standard-red tail, the build-failure tail, the tracking-ticket comment — goes through this filter first. `pyrycode/pyrycode-desktop` is private, but test output can surface env vars and the cost of a leaked credential is high, so err toward redaction.

```bash
redact() {
  sed -E \
    -e 's/(sk-ant-[A-Za-z0-9_-]{10,})/[REDACTED-ANTHROPIC-KEY]/g' \
    -e 's/(ghp_[A-Za-z0-9]{36,})/[REDACTED-GITHUB-TOKEN]/g' \
    -e 's/(ghs_[A-Za-z0-9]{36,})/[REDACTED-GITHUB-TOKEN]/g' \
    -e 's/(ANTHROPIC_API_KEY=[^[:space:]]+)/ANTHROPIC_API_KEY=[REDACTED]/g' \
    -e 's/(CLAUDE_CODE_OAUTH_TOKEN=[^[:space:]]+)/CLAUDE_CODE_OAUTH_TOKEN=[REDACTED]/g' \
    -e 's/(GITHUB_TOKEN=[^[:space:]]+)/GITHUB_TOKEN=[REDACTED]/g' \
    -e 's/([Bb]earer[[:space:]]+)[A-Za-z0-9._-]+/\1[REDACTED]/g' \
    -e 's/([Aa]uthorization:[[:space:]]*)[^[:space:]]+/\1[REDACTED]/g' \
    -e 's/\b([0-9]{1,3}\.){3}[0-9]{1,3}\b/[REDACTED-IP]/g'
}

redact < "$V/test.log" | tail -n 5      # the standard-red "last 5 lines"
redact < "$V/e2e.log" | tail -n 10      # the same, for an e2e red — Playwright's summary block is longer
redact < "$V/build.log" | tail -n 10    # the build-failure "last 10 lines"
```

The injected failure context goes through the same filter before any of it is quoted — it is a raw gate log until proven otherwise.

## The tracking line

The red templates below carry a `` `<TRACKING-LINE>` `` placeholder. Replace the **whole line, backticks included**, with exactly one of these shapes, chosen by the KNOWN/NEW partition from § search-first dedupe:

- **All-KNOWN** — `Tracking (re-observed): #X (for check-A), #Y (for check-B)`
- **All-NEW** — `Filed as separate bug ticket: #Z`
- **Mixed** — two lines: `Tracking (re-observed): #X (for check-A)` then `Filed as new ticket: #Z (for check-B)`

All three use the parenthetical-with-attribution style so the linkage is unambiguous; there is no "with 'in', no attribution" variant. **Why the placeholder is wrapped in backticks:** GitHub Markdown silently strips unknown angle-bracket constructs from rendered output. A bare `<TRACKING-LINE>` renders as EMPTY SPACE if you forget to substitute — a worse failure mode than a half-substituted line, because an empty review LOOKS valid. The backticks force inline-code rendering, so an unsubstituted marker shows up as visible text that a human will catch.

## Triage templates

**Standard red (regressions present)** — `gh pr comment <PR-number> --body-file "$V/review.md" --repo pyrycode/pyrycode-desktop`:

````
❌ **Verification gates failed — regressions introduced by this PR**

Regressions (passed on baseline `<sha>`, fail on PR):
- <file> > <test name>
- <file> > <test name>

Pre-existing failures (fail on both baseline AND PR branch, NOT caused by this PR):
- <file> > <test name>

`<TRACKING-LINE>`

Last 5 lines of `npm test` (or last 10 of `npx playwright test`):
```
<redacted tail>
```
````

Then: `gh issue edit <ticket-number> --add-label needs-rework:builder --repo pyrycode/pyrycode-desktop`. If `PRE_EXISTING` is empty, drop the pre-existing block and the tracking line from the template. Name the tier that went red in the heading line when it was the e2e tier — the builder reads it to know whether to look at a unit test or a spec under `e2e/`.

**Out-of-scope red (all failures pre-existing)** — run § search-first dedupe first, then `gh pr comment <PR-number> --body-file "$V/review.md" --repo pyrycode/pyrycode-desktop`:

```
⚠️ **Verification gates RED — pre-existing failures (PR did not cause them)**

Failing test(s): <PR_FAILS, comma-separated>

Baseline-comparison verdict (run against `git merge-base HEAD origin/main`):
- Regressions introduced by this PR: **none**
- Pre-existing failures (fail on both baseline AND PR branch): <PRE_EXISTING, comma-separated>

Triage verdict: PASS (PR did not introduce these failures).

`<TRACKING-LINE>`

Continuing to judgment review in this run.
```

**No labels from the triage half on this path** — not `needs-rework:*`, and not `done:*` either. The judgment verdict owns the labels from here.

**Build failure** — `gh pr comment <PR-number> --body-file "$V/review.md" --repo pyrycode/pyrycode-desktop`:

````
❌ **Verification gates failed — build failure**

`npm run build` did not succeed on this PR. Build failures always route to rework — they mean the PR's tree doesn't typecheck or build.

Last 10 lines of `npm run build`:
```
<redacted tail>
```
````

Then: `gh issue edit <ticket-number> --add-label needs-rework:builder --repo pyrycode/pyrycode-desktop`.

**Infra failure (gate could not produce a verdict)** — `gh pr comment <PR-number> --body-file "$V/review.md" --repo pyrycode/pyrycode-desktop`:

```
⚠️ **Verification gate could not produce a verdict**

The gate returned non-zero but produced no parseable failing names. Likely causes: `npm install` failed, vitest crashed, Electron could not launch for the Playwright tier, OOM, a missing toolchain, environmental disruption.

(Name the specific anomaly visible in the log: e.g. "Cannot find module", "no test output before exit", "no space left on device".)

Proceeding to judgment review in this run; its verdict alone decides PASS/FAIL on this ticket. Operator may want to re-dispatch after addressing the environmental cause.
```

No label changes from the triage half on infra-failure.

## Filing pre-existing-failure tickets — search-first dedupe

**Rule.** Before filing a new bug ticket for a pre-existing failure, search open issues for an existing tracking ticket. If one exists, comment-and-link instead of creating a new one.

**Why this exists.** Without dedupe, every PR cycle that re-encounters the same unmasked pre-existing failure files a fresh duplicate. Real-world precedent (2026-05-23): `snapshot-drift` on `pyrycode/tui-driver` was re-filed as #75 → #83 → #92 across three PR cycles in 48 hours before this rule landed, each closed as superseded.

**Procedure.** For each check name in `PRE_EXISTING`, use the test name (the part after the last `>`), not the file path:

```bash
# Search open issues whose title contains the check name, as a literal string.
# `--limit 100` (gh max) so a generic name matching many issues doesn't push
# the true tracking ticket beyond the inspection window.
candidates=$(gh issue list --repo pyrycode/pyrycode-desktop --state open \
               --search "\"<check-name>\" in:title" \
               --json number,title,url --limit 100)
```

**Safe-naming note.** The check name is wrapped in literal-quotes for GitHub Search's exact-string syntax. If a name contains GitHub-search-special characters (`:` `(` `)` `+` `"`), backslash-escape them before substituting. A candidate qualifies as a tracking ticket for THIS check if its title contains the check name as a substring (case-insensitive) AND is *shaped* like a tracking ticket — marker words include, but are not limited to, `pre-existing`, `unmasked`, `drift`, `flaky`, `tracking`, `regression`, `bug`, `failure`, `broken`, `intermittent`.

**Cost asymmetry.** A false positive (commenting on a related-but-distinct issue) is one extra notification — recoverable. A false negative creates yet another duplicate, exactly what this rule exists to prevent. **When unsure, treat as a match and comment.** **Tiebreaker:** if MULTIPLE open issues match for one check, comment on the **oldest** (lowest number) — that's the canonical tracker — and link the others in the comment body so they consolidate over time.

**Partition `PRE_EXISTING`:** **KNOWN** — checks with a matching open tracking ticket (record the matched number per check). **NEW** — checks with no matching open ticket.

**For each KNOWN check**, comment on its tracking ticket — no board operations; the existing ticket is already on the board:

```bash
gh issue comment <matched-number> --repo pyrycode/pyrycode-desktop --body \
  "Re-observed as pre-existing failure on PR #<PR-number> (baseline-comparison
  against \`<baseline-sha>\` confirms not introduced by this PR's diff).
  Tracking continues here.

  Last 5 lines of \`npm test\` on PR branch: <redacted tail, fenced>"
```

**If NEW is non-empty**, file one bundled ticket for the NEW checks only. **If NEW is empty, skip this block entirely** — the steps below share `$url`, and running them without it errors.

```bash
# A. File ONE bundled bug ticket for the NEW set. Title lists ONLY the NEW checks.
#    Body: the NEW check names, the PR #, the baseline-comparison evidence (both
#    npm test tails, redacted), and "cause not yet diagnosed" unless you've
#    identified it. If KNOWN is non-empty, note those tickets too ("see also #X, #Y").
url=$(gh issue create --repo pyrycode/pyrycode-desktop \
  --title "<NEW-names>: pre-existing failures unmasked by PR #<PR>" \
  --label "bug" \
  --body-file "$V/bug.md")

# A.1 Add to board #7; resolve project + Status field + Backlog option at runtime.
#     Never hardcode option IDs — updateProjectV2Field mutations reissue them
#     (2026-05-22 board-mutation lesson).
item_id=$(gh project item-add 7 --owner pyrycode --url "$url" --format json --jq '.id')
project_id=$(gh project view 7 --owner pyrycode --format json --jq '.id')
field_json=$(gh project field-list 7 --owner pyrycode --format json)
status_field_id=$(echo "$field_json" | jq -r '.fields[] | select(.name == "Status") | .id')
backlog_option_id=$(echo "$field_json" | jq -r '.fields[] | select(.name == "Status") | .options[] | select(.name == "Backlog") | .id')

# A.2 Set Status = Backlog. `gh project item-add` does NOT set Status on its
#     own — without this the item lands invisible to every column query.
gh project item-edit --project-id "$project_id" --id "$item_id" \
  --field-id "$status_field_id" --single-select-option-id "$backlog_option_id"

# A.3 Move to top of project (= top of Backlog when the column filters).
#     Omitting afterId sends the item to position 1.
gh api graphql -f query='mutation($projectId: ID!, $itemId: ID!) {
  updateProjectV2ItemPosition(input: { projectId: $projectId, itemId: $itemId }) {
    clientMutationId
  }
}' -f projectId="$project_id" -f itemId="$item_id" > /dev/null
```

**Destination = Backlog, top position.** Backlog (not Inbox) because the ticket already carries agent-validated evidence — failing test names plus baseline-comparison logs proving these aren't this PR's regressions — so the refiner can refine without human pre-triage. Top of Backlog because an unmasked pre-existing failure means main has a real bug that just surfaced; it deserves priority over already-refined work below. **Belt-and-suspenders:** this dedupe is a stochastic-prompt-layer fix. If the same dedupe failure surfaces again, file a follow-up for a deterministic dispatcher-level gate at [agent-dispatcher](https://github.com/pyrycode/agent-dispatcher) (refuse issue-create when an open issue with a matching title-prefix exists). Per Evidence-Based Fix Selection, don't ship both at once.
