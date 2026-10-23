# Builder handoffs — Pyrycode Desktop

Read this when a ticket has to leave your hands before or instead of a PR, or when you file a bug outside the ticket's scope. The table in `CLAUDE.md` § Labels and handoffs says which ending applies. This file says how to carry it out.

The two runners hand off differently. On Claude you post the comment and apply the label yourself. On Codex you return a status, and for a refinement handoff or a dependency wait the dispatcher posts your summary as the comment and applies the label, so write that summary to stand alone. On Codex on the MacBook, use the helper commands from the shared practice in place of the raw `gh` commands below: `relations`, `add-blocker`, `issue-create`, `board-add`, `board-status`, `issue-comment` and `add-label`.

Whatever the ending, leave the worktree untouched when no plan is committed. The dispatcher commits anything left dirty to `feature/<ticket>` and pushes it, so a draft plan or scratch file becomes stale junk on the branch.

## Oversized or newly expanded scope

Follow [builder scope reassessment](../docs/builder-scope-handoff.md) before planning, during implementation and on repair. The builder proposes smaller useful results and stops further expansion. The orchestrator assesses the evidence and applies any split. Preserve existing work at every depth. Use `needs_scope_review` on Codex or `error:builder:scope` through the managed workflow bridge on Claude.

## A gap in the ticket

Send the ticket back to refinement when a cold reader could not plan from it:

- Acceptance criteria that cannot be turned into tests, or context the repository cannot supply.
- A missing or contradictory product contract.
- No `Estimate:` line.
- UI-visible work with no `## Figma` section.

Name exactly what is missing, so the refiner can fix it in one pass. On Claude, comment and add `needs-rework:refiner`. On Codex, return `needs_refinement` with that explanation. A pending documentation requirement is not a gap, since the documentation stage owns it.

## A real dependency on an in-flight ticket

Only for the two cases in `CLAUDE.md` § In-flight dependencies: your design needs what the other branch adds, or both rewrite the same block. Do not write the plan.

1. Mark this ticket blocked by each ticket it depends on:

   ```bash
   gh api graphql -f query='mutation($issueId: ID!, $blockingIssueId: ID!) {
     addBlockedBy(input: { issueId: $issueId, blockingIssueId: $blockingIssueId }) {
       issue { number }
     }
   }' -f issueId="$(gh issue view <THIS> --repo pyrycode/pyrycode-desktop --json id -q '.id')" \
      -f blockingIssueId="$(gh issue view <THAT> --repo pyrycode/pyrycode-desktop --json id -q '.id')"
   ```

2. Explain the dependency, in this form: *"Blocked by #N: this design needs <what #N adds> / rewrites <the same block> as #N. Will build once #N lands."* Add any design notes the next run needs, because the refiner is not involved and the next builder run starts from this comment and the merged code.
3. On Claude, post that as an issue comment and add `needs-rework:refiner`. Because the ticket now has an open blocker, the dispatcher treats the label as a wait rather than a rework: it strips the label, keeps the ticket in In Development, counts no rework, and runs you again when the blocker closes. On Codex, return `waiting_on_blocker` with the explanation as the summary. The dispatcher checks the open blocker and parks the ticket the same way.

## Missing access

When the role needs something this run cannot reach, stop and say what it is. The main case is a ticket with a Figma URL when the Figma tools are unavailable or every call fails, as on Desktop #1696. Other cases are a missing toolchain or an unset `AGENTS_REPO_PATH`. On Claude, end with one message naming what is missing and what you needed it for, and the dispatcher records the run as an error for the operator. On Codex, return `blocked` with the same content. Do not relabel missing access as a refinement handoff or a wait, and do not build around it.

## Filing a bug outside the ticket's scope

`CLAUDE.md` § Bugs outside the ticket says when. Here is how.

Write the body to a file outside the worktree. Give the smallest reproduction, expected and actual behaviour, the symbol where the bug lives rather than a line number, and a link to the test that surfaced it. A new issue is invisible to the dispatcher until it is on board 7 with a Status, and `gh project item-add` does not set one, so do all three steps:

```bash
url=$(gh issue create --repo pyrycode/pyrycode-desktop \
  --title "<one-line bug summary>" --label bug --body-file /tmp/builder-<ticket>/bug.md)

item_id=$(gh project item-add 7 --owner pyrycode --url "$url" --format json --jq '.id')
project_id=$(gh project view 7 --owner pyrycode --format json --jq '.id')
field_json=$(gh project field-list 7 --owner pyrycode --format json)
status_field_id=$(echo "$field_json" | jq -r '.fields[] | select(.name == "Status") | .id')
backlog_option_id=$(echo "$field_json" | jq -r '.fields[] | select(.name == "Status") | .options[] | select(.name == "Backlog") | .id')

gh project item-edit --project-id "$project_id" --id "$item_id" \
  --field-id "$status_field_id" --single-select-option-id "$backlog_option_id"
```

Resolve the field and option IDs at run time, because editing a project field reissues them. The bug goes to Backlog for refinement without human promotion. On Codex the same steps are `issue-create`, `board-add` and `board-status <issue> Backlog`. Use Inbox only when the ticket needs a specific decision or missing input from the operator, and comment with that need. An unknown technical cause is investigation work for Backlog.

Then skip the test that exposed it, linking the new ticket, and open your PR as usual. If even the failing test cannot be written without the fix, which is rare, send the ticket back to refinement with a one-line explanation so the refiner can sequence the bug ticket as a blocker.
