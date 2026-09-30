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

Juhana approved matching routine Codex permissions for Desktop on 2026-09-11.
Desktop-scoped helpers enforce this repository, board 7, its ticket branches and
its own publishing folder. See the shared practice for supported actions.

Land the companion product knowledge change before updating this consumer.
The new role prompts need its knowledge map and verification topic.
Update the local environment with `CLAUDE_CODE_DISABLE_AUTO_MEMORY=1` and
`PYRY_AUTOCURATE_MEMORY=0` so the background curator also skips this consumer.
The launcher exports these values too.

A running dispatcher retains its loaded code. Restart it in the operator's
foreground terminal to activate the new runtime. Use `bin/pyry-start --runner codex`
or `bin/pyry-start --runner claude`. No option preserves the saved runner setting.

## Review overlap, 2026-09-30

The launcher enables source review alongside deterministic checks for Claude and
Codex. The source phase is read-only. Only the final verifier can publish after
both finish. Both phases share the time budget. Claude also shares the turn limit.
The final phase still owns Figma, live evidence, remote queries and red-gate triage.

Desktop retains its saved Claude runner and ticket concurrency setting. Install
the updated shared dispatcher and set `PYRY_VERIFIER_PARALLEL_REVIEW=1` locally.
The running dispatcher keeps its loaded runtime until its next launch. This
rollout must not stop or restart it.
