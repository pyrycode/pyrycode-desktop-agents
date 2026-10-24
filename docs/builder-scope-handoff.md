# Builder scope and replacement splits

Check scope before planning, during implementation and at the start of each repair. When the work contains separable useful results, split the ticket yourself through the managed workflow bridge. Builders have no nesting-depth limit. The three-child-level limit applies only to ordinary refiners.

A long description, a file count or another attempt at the same defect is not enough reason to split. Keep a bug with its regression. Each child needs an independently useful result, full assigned requirements, meaningful checks, security and acceptance requirements, and explicit dependencies. Preserve the original feature root through every split. Do not repeatedly reproduce the same unchanged scope in new tickets.

## Preserve the work

Keep existing commits, partial files, branches, pull requests, plans and failed evidence. Record their exact references in the children, including which completed work to reuse and what remains. Never reset, discard, delete or overwrite work to make a split look new. Do not mark unfinished implementation complete. Keep one-use helpers with their consumers.

## Perform the split

1. Create self-contained children through the managed GitHub bridge. Keep them in Inbox until finalization. Link every child to this ticket. Assign every original requirement and unresolved finding to a named child. Retain the original feature-root and policy markers.
2. Use the installed pipeline helper's `split-inspect PARENT` operation. It returns current revisions, the complete child inventory and every existing dependent. The equivalent managed bridge request is GET `/repos/OWNER/REPO/issues/PARENT/split`.
3. Save the returned template outside the worktree in the approved publishing directory. Add a unique `commandId` and a short `summary`. Order children by their actual dependencies. Fill each child's `dependsOn` with earlier child numbers. For each existing dependent, fill `children` with the child numbers that now own its prerequisite. Preserve all existing blockers. Shared-file overlap alone is coordination, not a causal prerequisite.
4. Use `split-finalize PARENT ABSOLUTE_JSON_FILE`. The equivalent managed request is POST to the same endpoint with that JSON file. One transaction validates ownership, stage, current revisions, complete inventories, holds and active work. It activates the children in Backlog, transfers prerequisites and closes the replaced parent. Reuse the exact request after an uncertain reply. After a changed scope or workflow refusal, inspect and reconcile instead of inventing another split identity.
5. After confirmed finalization, stop this run. Codex returns `completed` with the replacement children and retained-work references. Claude ends with the same summary. This completes the split, not the implementation. The dispatcher reads the authority's receipt for this exact run and retains the parent worktree without auto-commit, push, implementation completion labels or normal verification of the replaced parent. Children continue through ordinary refinement, building, independent review and required checks.

Children remain held if this run stops before finalization. Do not release them by closing the parent separately or setting completion labels. Preserve the unfinished split for recovery.

## When no safe split is known

Stop expansion and retain the evidence. Codex returns `needs_scope_review` with the original and revised estimates, source revision, completed and remaining work, proposed useful results and all reuse references. Claude posts that assessment through the managed bridge, adds `error:builder:scope` and ends the run. This fallback requests recovery assessment. It is not the normal path when a safe partition is already known.

Permission rejections, missing access, infrastructure failures and flaky tests keep their existing routes. A split cannot bypass ownership, an operator hold, an approval rejection or acceptance requirements. The builder's lack of a depth limit does not grant authority over unrelated tickets.
