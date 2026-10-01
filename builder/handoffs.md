# Builder handoffs — Pyrycode Desktop

Read this when a ticket has to leave your hands before or instead of a PR, or when you file a bug outside the ticket's scope. The table in `CLAUDE.md` § Labels and handoffs says which ending applies. This file says how to carry it out.

The two runners hand off differently. On Claude you post the comment and apply the label yourself. On Codex you return a status, and for a refinement handoff or a dependency wait the dispatcher posts your summary as the comment and applies the label, so write that summary to stand alone. On Codex on the MacBook, use the helper commands from the shared practice in place of the raw `gh` commands below: `relations`, `add-blocker`, `issue-create`, `board-add`, `board-status`, `issue-comment` and `add-label`.

Whatever the ending, leave the worktree untouched when no plan is committed. The dispatcher commits anything left dirty to `feature/<ticket>` and pushes it, so a draft plan or scratch file becomes stale junk on the branch.

## Oversized: propose a split

**Check the split depth first.** If the ticket's parent itself has a parent, do not propose another split. `$AGENTS_REPO_PATH/refiner/splitting.md`, under "Split depth: stop at two", explains why. Recursive splitting is a measured failure here: pyrycode #1925 became #1937, then #1940, then #1943 and #1944 in about seventy minutes with no code written.

```bash
gh api graphql -f query='query($owner:String!,$repo:String!,$num:Int!){repository(owner:$owner,name:$repo){issue(number:$num){number parent{number parent{number}}}}}' \
  -f owner=pyrycode -f repo=pyrycode-desktop -F num=<TICKET> \
  --jq '.data.repository.issue | "parent \(.parent.number // "none") grandparent \(.parent.parent.number // "none")"'
```

Count parent links, not blocker links. Several blockers do not make a ticket a grandchild.

**When a grandparent exists,** add `needs-human:sizing`, comment with the split you would have made and the measurement behind it, then build the ticket as it stands: plan, implement, PR. The label marks the judgement so it is findable on the board. It is not a question someone must answer before the ticket moves, because with splitting off the table the only choices are to build now or to build after an interruption that ends the same way. Pyrycode #1938, the first ticket to reach this point, stopped instead and gained nothing for a full extra run. State your measurement and your reading of it rather than leaving the call to the label. Never ask the operator to add a `wip:` label to restart you: that label means an agent is running right now, and it blocks dispatch.

**Otherwise, propose the split.** Apply the floor rule from `CLAUDE.md` first, so no child is a slice with one consumer in the same family. Write the proposal in this shape:

> **Oversized — split as follows:**
> - **A:** [first slice — what behaviour, what interfaces it introduces]
> - **B:** [second slice — what it consumes from A, what it adds; ...and so on]
>
> Each child stands alone. The refiner will write a self-contained body for each (no parent plan to reference — there's none). Each child's builder run produces its own plan from its own body.

When the split comes from re-counting a written plan, point each slice at a seam in your Design section, and do not commit the plan. The proposal lives on the issue, not in a file.

On Claude, post the proposal as an issue comment and add `needs-rework:refiner`. On Codex, return `needs_refinement` with the proposal as the summary. The ticket goes back to Backlog for the refiner.

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
inbox_option_id=$(echo "$field_json" | jq -r '.fields[] | select(.name == "Status") | .options[] | select(.name == "Inbox") | .id')

gh project item-edit --project-id "$project_id" --id "$item_id" \
  --field-id "$status_field_id" --single-select-option-id "$inbox_option_id"
```

Resolve the field and option IDs at run time, because editing a project field reissues them. The bug goes to Inbox, which is for human triage; the operator promotes it when it is ready. On Codex the same steps are `issue-create`, `board-add` and `board-status <issue> Inbox`.

Then skip the test that exposed it, linking the new ticket, and open your PR as usual. If even the failing test cannot be written without the fix, which is rare, send the ticket back to refinement with a one-line explanation so the refiner can sequence the bug ticket as a blocker.
