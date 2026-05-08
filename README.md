# pyrycode-mobile-agents

Agent instructions and dispatcher infrastructure for [pyrycode-mobile](https://github.com/pyrycode/pyrycode-mobile) — the Android client for [Pyrycode](https://github.com/pyrycode/pyrycode).

**Status: dormant.** Set up but not in use. Activation deferred until pyrycode-mobile reaches Phase 2 ticketing (conversation thread screen — many discrete sub-features, ticket-shaped). See the **Activation Checklist** below.

## What this is

A fork of [pyrycode/agents](https://github.com/pyrycode/agents) with the per-role agent prompts rewritten for Kotlin / Jetpack Compose. The dispatcher infrastructure (`dispatch/`) is unchanged — same WIP=1 supervisor, same GitHub Projects board flow, same recovery semantics, same JSONL replay procedure.

## Why a separate repo

Agent prompts are language-specific. The Go agents in `pyrycode/agents` know about `errgroup`, goroutine lifecycles, `context.Context`, channels, race conditions. The Kotlin agents here know about `viewModelScope`, `StateFlow` vs `SharedFlow`, recomposition correctness, Material 3 token usage, accessibility / `contentDescription`, Compose lifecycle (`LaunchedEffect` / `DisposableEffect`).

Reusing `pyrycode/agents` directly would either misguide every dev run (idiomatic Go-shaped Kotlin, missed Compose landmines) or require complex language-detection branches in every prompt — abstraction at N=2 consumers, exactly the "duplicate three times" anti-pattern.

Same dispatcher infrastructure, different agent prompts. Duplicate until divergence becomes an observed problem, then abstract.

## Repo layout

```
pyrycode-mobile-agents/
├── po/CLAUDE.md              # Product Owner agent — ticket refinement + sizing + splitting
├── architect/CLAUDE.md       # Architect agent — design specs, size enforcement
├── developer/CLAUDE.md       # Developer agent — Kotlin/Compose implementation, test-first
├── code-review/CLAUDE.md     # Code Review agent — Compose / Material 3 / a11y review
├── documentation/CLAUDE.md   # Documentation agent — evergreen docs, ADRs, lessons
└── dispatch/
    ├── src/
    │   ├── dispatch.ts       # Main supervisor loop
    │   ├── lib.ts            # Pure helpers (testable)
    │   ├── lib.test.ts
    │   ├── reconcile.ts      # Auto-advance / rework routing
    │   ├── reconcile.test.ts
    │   ├── github.ts         # GitHub GraphQL client
    │   └── types.ts          # Agent + ProjectItem types
    ├── package.json          # Bun/pnpm-compatible
    ├── pnpm-lock.yaml
    ├── tsconfig.json
    └── .env.example
```

## Cross-project reference

The agent prompts cite **worked examples** from `pyrycode/pyrycode` (the Go binary):
- #29, #40, #45 — sizing rationalization escapes that hit max_turns
- #75 — "26 mechanical edits" rationalization → 61-turn salvage
- #128 — bug-found-out-of-scope rule violation
- #55 — missing-spec-files-list cost the developer 84% of its turn budget
- #41 — missing `addBlockedBy` between dependent children

These are kept verbatim as historical learning material. The lessons (sizing, scope discipline, edit fan-out) are language-independent. Replace tooling references mentally — `errgroup` ↔ structured `coroutineScope`; channel ↔ `Flow`; Go interfaces ↔ Kotlin interfaces.

## Activation Checklist

When pyrycode-mobile reaches Phase 2 and the chat-screen sub-tickets can be drafted (see [project plan](https://github.com/pyrycode/pyrycode-mobile/blob/main/CLAUDE.md)), do the following before the first dispatcher run:

1. **Refactor the target-repo helper.** `resolvePyrycodeRepoRoot` in `dispatch/src/lib.ts` is hardcoded to look for a sibling dir named `pyrycode`. Rename to `resolveTargetRepoRoot` and have it look up the sibling matching `process.env.GITHUB_REPO`. Update `lib.test.ts` accordingly.
2. **Rename the env var override.** `PYRYCODE_REPO_PATH` → `TARGET_REPO_PATH` (or just `REPO_PATH`). Update `.env.example`, `dispatch.ts`, `lib.ts`, `lib.test.ts`. Mechanical.
3. **Create the GitHub Project board** for pyrycode-mobile (separate from pyrycode's). Define the same column states (Inbox / Backlog / In Architecture / In Development / In Review / In Documentation / Done). Get the `PROJECT_NUMBER` and `Status field option IDs`; populate them in `.env`.
4. **Bootstrap the labels.** `size:xs`, `size:s`, `ready:po`, `ready:architect`, `ready:developer`, `ready:code-review`, `ready:documentation`, `needs-rework:po`, `needs-rework:architect`, `needs-rework:developer`, `needs-rework:code-review`, `error:max_turns_salvaged`. Use `gh label create` (active account = `ilmoniemi`).
5. **Decide where the dispatcher runs.** Options:
   - Separate systemd unit on pyrybox (parallel to the pyrycode dispatcher) — same server, different `WorkingDirectory` and `.env`
   - Mac-side during active dev sessions only (start/stop manually with `bun start`)
   - Consider whether running both pipelines simultaneously creates Anthropic-API contention (unlikely at ticket cadence; flag if observed)
6. **Smoke-test with one dummy ticket.** Before throwing real Phase-2 work at it, drop a one-line "rename the app bar title" ticket into Backlog and watch it flow through PO → Architect → Developer → CR → Documentation. Confirm the agents read the rewritten prompts, not the Go-shaped originals.
7. **Update the vault**: project status flips from "agentic pipeline dormant" to "agentic pipeline active, Phase 2 ticketing."

## License

Same as pyrycode/agents — private, no public license. Internal use within the `pyrycode` GitHub org.

## Related

- [pyrycode/pyrycode-mobile](https://github.com/pyrycode/pyrycode-mobile) — the app this dispatches for
- [pyrycode/pyrycode](https://github.com/pyrycode/pyrycode) — Pyrycode CLI / Go binary
- [pyrycode/agents](https://github.com/pyrycode/agents) — upstream fork source
