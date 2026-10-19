# Splitting a ticket — Pyrycode Desktop refiner

Read this once you have decided a ticket must split. The decision itself is in the Sizing Guide of `CLAUDE.md`.

The commands named below are the Desktop pipeline helper's actions, described in the shared practice. Without the helper, the same effects come from `gh` and the GraphQL mutations `addSubIssue`, `addBlockedBy` and `updateProjectV2ItemPosition`. Resolve project, field, option and item ids at runtime and never hardcode them. `gh issue view --json projectItems` does not return the project item id that position and status changes need; the GraphQL `projectItems` query does.

## Split depth: stop at two

Before creating children, read `$AGENTS_REPO_PATH/docs/ticket-scope-policy.md` for the feature-root and policy markers. Preserve the original feature root on the parent and every child. Closing this parent replaces it with children; it does not complete the feature.

Check the ticket's parentage first, with `relations <ticket>`, which returns its parent and grandparent. Without the helper, this query does the same:

```bash
gh api graphql -f query='query($owner:String!,$repo:String!,$num:Int!){repository(owner:$owner,name:$repo){issue(number:$num){number parent{number parent{number}}}}}' \
  -f owner=pyrycode -f repo=pyrycode-desktop -F num=<TICKET> \
  --jq '.data.repository.issue | "parent \(.parent.number // "none") grandparent \(.parent.parent.number // "none")"'
```

If the ticket has a grandparent, do not split it. Add `needs-human:sizing`, comment with the split you would have made and why, then refine it in place as one ticket. Do not stop and wait for a person. Once splitting is off the table, the only outcomes are refining it now or refining it after an interruption, so the label marks the call for later review rather than asking a question.

This is a hard gate, because every softer rule failed to stop recursive splitting. Upstream on 2026-09-01, #1925 became #1937, which became #1940, which became #1943 and #1944: three levels in about seventy minutes, no code written, and each child's body longer than its parent. The #1714 family did the same on 2026-08-24, and writing the warning down did not prevent the repeat.

The gate reads sub-issue links, so it goes blind if a child is not linked to its parent. Blocker links are not parentage, as the shared practice explains.

## Finalize the split as one operation

Keep the parent open while preparing its children. Create each child with `issue-create`, add it to board 7 with `board-add`, and attach it with `add-child <parent> <child>`. Leave children in **Inbox** until finalization. Each child has a self-contained body, original acceptance allocated to it, its own Figma section where applicable, an Estimate, the feature-root markers and `Split from #N`. Preserve original requirements and security review obligations.

Do not activate children or move/close the parent with separate workflow commands. The shared authority finalizes the complete split transactionally:

1. Run `/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-pipeline-action split-inspect PARENT`. It reads fresh, complete GitHub family links and returns authoritative revisions for the parent, its children and every open dependent, including other imported projects. A truncated or unknown dependent inventory refuses finalization.
2. Save that JSON in your unique publishing folder. Add a fresh `commandId` and a short `summary`. Order children after the parent in dependency order. Fill each child's `dependsOn` with earlier child numbers it actually needs. Shared-file overlap alone is coordination, not a prerequisite. For each dependent, fill `children` with the child numbers that now own its existing prerequisite. Retain all returned revisions. An empty dependent mapping is not a valid handoff.
3. Run `/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-pipeline-action split-finalize PARENT ABSOLUTE_JSON_FILE` as one command. Keep that exact file and identity for retries after an uncertain reply. The finalizer verifies the complete family and revisions, activates children in Backlog after the parent, inherits priority/security/platform labels and original blockers, transfers declared prerequisites without removing existing blockers, records the handoff comments and closes the replaced parent in Done in **one database transaction**. Closing records replacement, not feature delivery.

Example request shape (use the actual inspection values, not these sample numbers):

```json
{
  "commandId": "split-500-unique",
  "revision": 8,
  "summary": "Two independently verifiable results preserve the original acceptance.",
  "children": [
    {"number": 501, "revision": 2, "dependsOn": []},
    {"number": 502, "revision": 3, "dependsOn": [501]}
  ],
  "dependents": [
    {"ticket": "pyrycode/pyrycode-desktop#600", "revision": 4, "children": [502]}
  ]
}
```

Read the result back before repeating any action. An identical committed request returns its saved result even after a lost reply or ended run. If workflow or content changed before commit, inspect again and review the changed scope before submitting a new request. Approval rejections, ownership conflicts, active dependents, pending support work and holds still stop finalization; the new operation never clears them. Follow shared practice after an approval rejection, without replaying a denied operation through another route.

A failure before commit leaves the parent open and the children inactive. Newly created, linked split children also have a durable admission hold while their parent remains open, even after the creator exits. An unfinished parent cannot be marked ready for implementation. Reuse the existing children and retained request when resuming; do not create replacements. The ordinary refiner can inspect and complete preserved partial work once it has an admitted parent run and any required operator authorization.

The children receive their own later refinement runs after the parent is replaced. Do not refine them further in this run.
