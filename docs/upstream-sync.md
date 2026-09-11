# Desktop workflow sync

Ported from Pyrycode on 2026-09-11.

| Source | Desktop adaptation |
| --- | --- |
| e37ade1 | Shared repository knowledge, disabled Claude auto memory, shared role practice. The product map and verification lessons land with the companion product change. |
| 12911b2, 63a175e, d978d4a | Selectable Claude or Codex runner, launch override, and executable preflight. |
| ab36c25 | Preserve documentation requirements through refinement, plans, reviews and the documentation stage. |
| 648a31f | Structured builder return to refinement, owned by the dispatcher. |
| 993595a in agent-dispatcher | Shared dispatcher version containing all of those runtime changes. |

Desktop retains its Electron, React and TypeScript rules, Figma requirements,
measured sizing limits, browser tests, and live-daemon gate configuration.
The daemon repository's live Go test instructions do not apply here.

The Pyrycode-only Codex permission helpers are not a valid Desktop destination.
They are intentionally absent from this consumer's practice until separate
Desktop-scoped permissions have been approved and installed.

Land the companion product knowledge change before updating this consumer.
The new role prompts need its knowledge map and verification topic.
Update the local environment with `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and
`PYRY_AUTOCURATE_MEMORY=0` so the background curator also skips this consumer.
The launcher exports these values too.

A running dispatcher retains its loaded code. Restart it in the operator's
foreground terminal to activate the new runtime. Use `bin/pyry-start --runner codex`
or `bin/pyry-start --runner claude`. No option preserves the saved runner setting.
