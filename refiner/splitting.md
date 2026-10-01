# Splitting a ticket — Pyrycode Desktop refiner

Read this once you have decided a ticket must split. The decision itself is in the Sizing Guide of `CLAUDE.md`.

The commands named below are the Desktop pipeline helper's actions, described in the shared practice. Without the helper, the same effects come from `gh` and the GraphQL mutations `addSubIssue`, `addBlockedBy` and `updateProjectV2ItemPosition`. Resolve project, field, option and item ids at runtime and never hardcode them. `gh issue view --json projectItems` does not return the project item id that position and status changes need; the GraphQL `projectItems` query does.

## Split depth: stop at two

Check the ticket's parentage first, with `relations <ticket>`, which returns its parent and grandparent. Without the helper, this query does the same:

```bash
gh api graphql -f query='query($owner:String!,$repo:String!,$num:Int!){repository(owner:$owner,name:$repo){issue(number:$num){number parent{number parent{number}}}}}' \
  -f owner=pyrycode -f repo=pyrycode-desktop -F num=<TICKET> \
  --jq '.data.repository.issue | "parent \(.parent.number // "none") grandparent \(.parent.parent.number // "none")"'
```

If the ticket has a grandparent, do not split it. Add `needs-human:sizing`, comment with the split you would have made and why, then refine it in place as one ticket. Do not stop and wait for a person. Once splitting is off the table, the only outcomes are refining it now or refining it after an interruption, so the label marks the call for later review rather than asking a question.

This is a hard gate, because every softer rule failed to stop recursive splitting. Upstream on 2026-09-01, #1925 became #1937, which became #1940, which became #1943 and #1944: three levels in about seventy minutes, no code written, and each child's body longer than its parent. The #1714 family did the same on 2026-08-24, and writing the warning down did not prevent the repeat.

The gate reads sub-issue links, so it goes blind if a child is not linked to its parent. Blocker links are not parentage, as the shared practice explains.

## What a finished split looks like

**One child issue per deliverable, each self-contained.** Write each body as if the parent never existed: full scope, its own criteria, its own `## Figma` section where UI-visible, its own `Estimate:` line, and links to any decision records in `docs/knowledge/decisions/`. Do not refer to sections of the parent or its plan, because the parent's plan is thrown away and each child's builder plans from its own body. The only tie to the parent is `Split from #N` at the bottom of the body and the sub-issue link. Create each with `issue-create`.

**Each child is on board 7 in Backlog, right after the parent, in dependency order.** Use `board-add`, then `board-status <child> Backlog`, then `board-after`: the first child after the parent, each later child after the previous one. Backlog, not Inbox, because the parent was already triaged. Adding an issue to the board does not set its status, and an item without one is invisible to every column query. Never place a child at the top: it would jump ahead of higher-priority tickets the parent was correctly behind.

**Each child is a sub-issue of the parent,** with `add-child <parent> <child>`.

**A child that needs another child is blocked by it,** with `add-blocker <later> <earlier>`. The dispatcher's open-blocker check is the only thing that keeps the order, because concurrent dispatch can build unrelated tickets side by side. Without the blocker, the later child's builder implements against an API that does not exist yet; pyrycode #41 burned about $4 that way.

**Siblings that write to the same spots are chained too,** even when neither needs the other. When two children follow the same precedent, or name the same insertion point in the same production file, the second one built before the first merges conflicts on every one of those lines, and a merge conflict parks the ticket for a human. Mobile #801 and #802, both told to follow the same earlier decode, collided in 16 places across six files on 2026-09-22. Touching the same large file is not the trigger. A shared precedent or insertion point is.

**Tickets that were blocked by the parent now point at the right child.** `relations <parent>` lists what the parent blocks. For each open dependent, find the child that holds what it actually needs, run `add-blocker <dependent> <child>`, and comment on the dependent: "Re-pointed from #<parent> to #<child> as part of #<parent>'s split. Original blocker now lives in #<child>." Leave the old parent blocker in place, since closed blockers are ignored. Without the re-point, closing the parent unblocks the dependent while its real prerequisite is still in flight.

**The parent is in Done and closed,** with a comment summarising the split. Set `board-status <parent> Done`, post the comment, then close the issue with `gh issue close`. The helper cannot close issues, so under Codex the close goes through approval review, and a rejection follows the shared practice's recovery rule.

The children reach your column on later dispatch cycles. Do not refine them further in this run.
