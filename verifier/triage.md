# Triage — Pyrycode Desktop verifier

Read this when your gate note says **TRIAGE MODE**, or when no gate note arrived and you run the gates yourself. The goal is to decide, mechanically where possible, whether this PR caused the red. A PR that fixes one thing while unmasking older fragility elsewhere should not be sent back for rework it cannot do. Before this procedure existed, such PRs burned three or more rework cycles.

## Running the gates yourself

Only when no gate note was injected. Run them once, in this order, then follow the matching path: green goes to judgment, red goes through this file using your own logs.

```bash
npm install --no-audit --no-fund
npm run check:docs
npm test 2>&1 | tee "$V/test.log"
npm run build 2>&1 | tee "$V/build.log"
PLAYWRIGHT_JSON_OUTPUT_NAME="$V/e2e.json" npx playwright test --reporter=list,json 2>&1 | tee "$V/e2e.log"
```

## Classify the red

The injected failure context names the failing gate and carries its output tail. Classify before anything else:

| Observed | Classification | Next action |
|---|---|---|
| `npm install` failed | **infra failure** | Nothing about the diff was tested. Post the infra template. Do not route to rework. Go on to judgment; your verdict alone decides. |
| `npm run check:docs` failed | **red (docs failure)**, and almost always pre-existing | The builder cannot write `docs/knowledge/features/`, so this is rarely the PR's doing. Confirm at the merge-base before routing anywhere: reproduce, and if the merge-base is red too, treat it as pre-existing and route it as case 2 under "Routing after the comparison". Only a false heading or an oversized file inside the PR's own diff is a regression, and that routes to `needs-rework:builder`. |
| `npm run build` failed | **red (build failure)** | Always a regression (the PR's tree doesn't typecheck or build). `needs-rework:builder` immediately — no baseline run. |
| `npm test` failed and failing tests are extractable | **red (test failure)** | Run the baseline comparison (§ below). Routing depends on the regression vs pre-existing partition. |
| `npx playwright test` failed and failing specs are extractable | **red (e2e failure)** | Same baseline comparison, on the e2e tier (§ below). Electron e2e can flake, so the partition matters even more here. |
| `npm test` or `npx playwright test` non-zero but no parseable failing names (vitest crash, Electron failed to launch, OOM, missing dependency, no test output) | **infra failure** | Post the infra template. Do not route to rework on this signal alone. Go on to judgment; your verdict alone decides. |

The gates run in order and stop at the first red, so a docs failure in the note means only the install ran, a build failure means the docs guard and the unit suite already passed, a test failure means the build never ran, and an e2e failure means install, docs guard, unit suite and build all passed and `out/` in your worktree is fresh — say so in the verdict, and remember that `npm run build` is also part of the builder's own gate, so a red there is a builder that skipped its verification step.

**Getting the PR-side log.** Prefer the injected context: if it holds the full `npm test` output, save it to `$V/test.log`. If it is only a tail without parseable `FAIL` lines on a test-tier failure, reproduce once in the PR worktree — `npm install --no-audit --no-fund` first if `node_modules` is missing, then `npm test 2>&1 | tee "$V/test.log"` — to capture the full log. That reproduction is triage, not a judgment-mode gate re-run; it is the one situation where you run `npm test` yourself.

Extract failing test names. Vitest prints one line per failed test, shaped `FAIL <file> > <describe> > <test name>`:

```bash
grep -E '^\s*FAIL ' "$V/test.log" | sed -E 's/^\s*FAIL //' | sort -u
```

This yields `<file> > <test name>` per failing test — the `comm`-comparable name set the baseline run reuses. The durable fallback if the console format drifts is vitest's JSON reporter: `npm test -- --reporter=json --outputFile="$V/test.json"`, then `jq -r '.testResults[].assertionResults[] | select(.status=="failed") | "\(.ancestorTitles | join(" > ")) > \(.title)"' "$V/test.json" | sort -u`.

**For an e2e red**, the injected tail is Playwright's list-reporter output and rarely carries every failing spec. Reproduce once in the PR worktree — no rebuild, `out/` is fresh because the build gate passed — with the JSON reporter alongside the list one, then extract file-plus-title pairs. Line and column numbers are deliberately dropped, so a spec that merely moved still matches its baseline self:

```bash
PLAYWRIGHT_JSON_OUTPUT_NAME="$V/e2e.json" npx playwright test --reporter=list,json 2>&1 | tee "$V/e2e.log"
jq -r '[.. | objects | select(has("specs")) | .file as $f | .specs[] | select(.ok == false) | "\($f) › \(.title)"] | unique | .[]' "$V/e2e.json"
```

The JSON reporter nests `describe` blocks as suites, and every suite object carries its `file`, which is why the walk is recursive rather than `.suites[].specs[]`.

## Baseline comparison for a red test tier

Do not route a test failure to `needs-rework:builder` on sight. Re-run the failing tier against the PR's merge-base in a temporary worktree, then classify each failing test as `regression` (passed on baseline, failed on PR) or `pre_existing` (failed on both). **Skip the baseline run entirely if:** red:build or infra failure.

The script below is written for the unit tier. **For red:e2e, run the same procedure with three substitutions:** `PR_FAILS` comes from the `jq` extraction above; step 4 becomes `npm install --no-audit --no-fund && npm run build && PLAYWRIGHT_JSON_OUTPUT_NAME="$V/baseline-e2e.json" npx playwright test --reporter=list,json`, because the baseline worktree has no `out/` either; and `BASELINE_FAILS` comes from the same `jq` walk over `$V/baseline-e2e.json`. Budget for it: the tier runs one Electron process at a time and a full pass takes minutes, on top of the install and the build, so start the baseline run before reading anything else.

This is the deterministic safety net for the out-of-scope question. The pre-triage contract — "any red is rework" — meant that PRs which correctly fix one thing while unmasking pre-existing fragility elsewhere burned 3+ rework cycles. The baseline run answers "did THIS PR introduce these failures?" mechanically, with no diff-reasoning or call-graph guessing required. Per the **belt-and-suspenders** principle, the deterministic baseline run is the different-fabric net under the stochastic initial classification.

```bash
# 1. PR-side failing test names, already extracted above:
PR_FAILS=$(grep -E '^\s*FAIL ' "$V/test.log" | sed -E 's/^\s*FAIL //' | sort -u)
if [ -z "$PR_FAILS" ]; then
  # Defensive: red:test without parseable names should have classified as
  # infra-failure. If it didn't, fall through to standard red routing.
  echo "verifier: red:test with no parseable failing names; routing as standard red" >&2
else
  # 2. Resolve baseline ref — the merge-base captures "where this PR diverged from main."
  BASELINE_REF=$(git merge-base HEAD origin/main 2>/dev/null)
  if [ -z "$BASELINE_REF" ]; then
    echo "verifier: merge-base unresolved; routing as standard red" >&2
  else
    # 3. Detached worktree at the baseline. `git worktree add` accepts an
    #    existing EMPTY directory, which is what mktemp -d gives us.
    BASELINE_DIR=$(mktemp -d -t baseline-verifier-XXXXXX)
    if ! git worktree add --detach "$BASELINE_DIR" "$BASELINE_REF" >/dev/null 2>&1; then
      echo "verifier: baseline worktree add failed; routing as standard red" >&2
      rmdir "$BASELINE_DIR" 2>/dev/null || true   # nothing was checked out; don't leak the dir
    else
      # 4. Install deps (the baseline tree has no node_modules) and run npm test
      #    there. `&>` captures BOTH stdout and stderr — vitest writes some
      #    diagnostics to stderr and we need them in the log for accurate
      #    comparison. (`2>&1 > file` is wrong-ordered and would leak stderr.)
      (cd "$BASELINE_DIR" && npm install --no-audit --no-fund >/dev/null 2>&1 && npm test) &> "$V/baseline-test.log" || true
      if [ -s "$V/baseline-test.log" ]; then
        BASELINE_FAILS=$(grep -E '^\s*FAIL ' "$V/baseline-test.log" | sed -E 's/^\s*FAIL //' | sort -u)
        # 5. Partition: comm -23 = in PR_FAILS only (regressions, PR caused them);
        #    comm -12 = in both (pre_existing, PR did not cause them).
        REGRESSIONS=$(comm -23 <(echo "$PR_FAILS") <(echo "$BASELINE_FAILS"))
        PRE_EXISTING=$(comm -12 <(echo "$PR_FAILS") <(echo "$BASELINE_FAILS"))
      else
        echo "verifier: baseline log empty or not produced; routing as standard red" >&2
        REGRESSIONS="$PR_FAILS"
        PRE_EXISTING=""
      fi
      # 6. Clean up the baseline worktree (always — leaks rot the dispatcher's worktree list).
      git worktree remove --force "$BASELINE_DIR" >/dev/null 2>&1 || true
    fi
  fi
fi
```

**Routing after the comparison** — three cases:

1. **`REGRESSIONS` non-empty** → at least one failing test passed on the baseline but fails on this PR. Post the standard-red template, add `needs-rework:builder`, and **stop there and skip judgment.** The diff you would review is about to change. If `PRE_EXISTING` is also non-empty, mention those too, flagged as "pre-existing, tracked separately," and run § search-first dedupe before posting so the linkage is in the review body.

2. **`REGRESSIONS` empty AND `PRE_EXISTING` non-empty** → every failing test fails on the baseline too. The PR did not introduce them. Track the `PRE_EXISTING` set (§ search-first dedupe), post the out-of-scope-red template, add **no labels from the triage half**, then **go on to judgment in this same run** — the PR itself is reviewable, and your judgment verdict owns the labels from here.

3. **Baseline couldn't run** (merge-base unresolved, worktree add failed, baseline log missing) → fall back to standard red routing (`needs-rework:builder`). The deterministic gate failed; default to safe behaviour.

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
