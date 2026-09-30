# pyrycode-desktop-agents

Agent instructions and dispatcher infrastructure for [pyrycode-desktop](https://github.com/pyrycode/pyrycode-desktop) — the Electron desktop client for [Pyrycode](https://github.com/pyrycode/pyrycode).

**Status: dormant.** Set up but not running. The dispatcher waits for pyrycode-desktop ticketing to begin. Board #7, its labels, and the first Backlog tickets already exist; activation is gated on the operator running `bin/pyry-start`. See the **Activation Checklist** below.

## What this is

A fork of [pyrycode/agents](https://github.com/pyrycode/agents), by way of [pyrycode/pyrycode-mobile-agents](https://github.com/pyrycode/pyrycode-mobile-agents), with the per-role agent prompts rewritten for TypeScript / React / Electron. As of 2026-05-09 the dispatcher source itself lives in [`pyrycode/agent-dispatcher`](https://github.com/pyrycode/agent-dispatcher), consumed via git submodule at `dispatcher/` — same WIP-limited supervisor, same GitHub Projects board flow, same recovery semantics, same JSONL replay procedure.

The desktop app source lives in the sibling repo `pyrycode/pyrycode-desktop`. This repo houses only the orchestration layer: the desktop-specific agent prompts and the `bin/` launcher scripts that turn board tickets into agent runs against that codebase.

## Why a separate repo

Agent prompts are language-specific. The Go agents in `pyrycode/agents` know about `errgroup`, goroutine lifecycles, `context.Context`, channels, and race conditions. The TypeScript agents here know about React hooks and re-render correctness, Zustand stores, discriminated-union event shapes, async iterables for streams, the Electron main-versus-renderer process split, and keeping the transport and crypto out of the web layer.

Reusing `pyrycode/agents` directly would either misguide every dev run with idiomatic Go-shaped TypeScript, or require complex language-detection branches in every prompt — abstraction at two consumers, exactly the "duplicate three times before you abstract" anti-pattern.

Same dispatcher infrastructure, different agent prompts. Duplicate until divergence becomes an observed problem, then abstract.

## Repo layout

```
pyrycode-desktop-agents/
├── po/CLAUDE.md              # Product Owner agent — ticket refinement + sizing + splitting
├── architect/CLAUDE.md       # Architect agent — design specs, size enforcement, security-review pass
├── developer/CLAUDE.md       # Developer agent — TypeScript/React/Electron implementation, test-first
├── code-review/CLAUDE.md     # Code Review agent — React / TypeScript / a11y / visual-fidelity review
├── qa/CLAUDE.md              # QA agent — npm build + test gates, baseline comparison
├── documentation/CLAUDE.md   # Documentation agent — evergreen docs, ADRs, per-ticket notes
├── refiner/CLAUDE.md         # Builder set — the PO contract under its new name
├── builder/CLAUDE.md         # Builder set — plan, then implement, in one warm session
├── builder/security-review.md # Builder set — the adversarial checklist on security-sensitive plans
├── verifier/CLAUDE.md        # Builder set — triage of red gates, then judgment review
├── bin/                      # pyry-start, pyry-drain, pyry-status, pyry-test, ...
├── .env.example              # Copy to .env (gitignored)
└── dispatcher/               # submodule → pyrycode/agent-dispatcher
```

Two stage sets share this repo. The classic six-agent relay (po → architect → developer → qa → code-review → documentation) is the default. `PYRY_STAGE_SET=builder` in `.env` selects the four-role builder set (refiner → builder → verifier → documentation), piloted on pyrycode since 2026-09-01 and propagated here the same day: the builder plans and implements in one session, and the dispatcher runs `PYRY_VERIFIER_GATES` deterministically. The launcher enables preliminary source review alongside those checks for Claude and Codex. The final verifier waits for both, then completes design evidence and failure triage before publishing. Ticket concurrency remains separately configured. Board #7 keeps its In Architecture and In QA columns; the builder set simply never polls them. See `.env.example` for the knobs.

The target repo is `pyrycode/pyrycode-desktop`; the `.env` sets `TARGET_REPO_PATH` to its local checkout. Because the app is TypeScript, not Go, the `.env` overrides `SALVAGE_GATES="npm run build"` — the dispatcher's default gate is `go vet ./...; go build ./...`, which would fail on every Electron build and disable salvage. Do not drop that override.

## Cloning

```bash
git clone --recursive https://github.com/pyrycode/pyrycode-desktop-agents
```

If you forgot `--recursive`:

```bash
cd pyrycode-desktop-agents && git submodule update --init
```

`bin/pyry-start` runs `pnpm install --silent` in the submodule on every restart, so submodule SHA bumps land cleanly. To pull a newer dispatcher version:

```bash
cd dispatcher && git pull origin main && cd ..
git add dispatcher && git commit -m "chore: bump dispatcher to <sha>"
```

## Cross-project reference

The agent prompts cite **worked examples** from `pyrycode/pyrycode` (the Go binary):
- #29, #40, #45 — sizing rationalization escapes that hit max_turns
- #75 — "26 mechanical edits" rationalization → 61-turn salvage
- #128 — bug-found-out-of-scope rule violation
- #55 — missing-spec-files-list cost the developer 84% of its turn budget
- #41 — missing `addBlockedBy` between dependent children

These are kept verbatim as historical learning material. The lessons (sizing, scope discipline, edit fan-out) are language-independent. Replace tooling references mentally — Go's `errgroup` ↔ `Promise.all` over an async batch; a Go channel ↔ an async iterable or typed event emitter; a Go interface ↔ a TypeScript interface.

## Activation Checklist

Most of the setup landed on 2026-07-02. What remains is the decision to turn the pipeline on.

1. ~~Create the GitHub Project board.~~ — DONE. Board #7 with the mobile-parity Status columns for the pipeline flow (Inbox / Backlog / In Architecture / In Development / In QA / In Code Review / In Documentation / Done). `PROJECT_NUMBER=7` in `.env`.
2. ~~Bootstrap the labels.~~ — DONE. `size:xs`, `size:s`, the `done:*` and `needs-rework:*` set, `error:max_turns_salvaged`, `security-sensitive`, and the rest (48 labels).
3. ~~File the first tickets.~~ — DONE. 13 dependency-ordered Backlog tickets toward the connect-send-stream round-trip. Ready-to-dispatch set: #1 / #2 / #4 / #5 / #8.
4. **Decide where the dispatcher runs.** Options:
   - Mac-side during active dev sessions only — start and stop manually with `./bin/pyry-start`.
   - A separate systemd unit on pyrybox, parallel to the other dispatchers, with its own `WorkingDirectory` and `.env`.
   - Consider whether running several pipelines at once creates Anthropic-API contention. Unlikely at ticket cadence; flag if observed.
5. **Smoke-test with one small ticket.** Before real feature work, watch a single ticket flow through PO → Architect → Developer → QA → Code Review → Documentation. Confirm the agents read the rewritten TypeScript/Electron prompts, not any Go-shaped residue.
6. **Update the vault.** Flip the project status from "dispatch-ready, dormant" to "agentic pipeline active" in the [Pyrycode Desktop project note](https://github.com/pyrycode/pyrycode-desktop).

## License

Same as pyrycode/agents — private, no public license. Internal use within the `pyrycode` GitHub org.

## Related

- [pyrycode/pyrycode-desktop](https://github.com/pyrycode/pyrycode-desktop) — the app this dispatches for
- [pyrycode/pyrycode](https://github.com/pyrycode/pyrycode) — Pyrycode CLI / Go binary
- [pyrycode/agent-dispatcher](https://github.com/pyrycode/agent-dispatcher) — the dispatcher submodule
- [pyrycode/pyrycode-mobile-agents](https://github.com/pyrycode/pyrycode-mobile-agents) — sibling fork this was forked from
- [pyrycode/agents](https://github.com/pyrycode/agents) — upstream fork source
