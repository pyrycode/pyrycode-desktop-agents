# Review criteria — Pyrycode Desktop

These criteria are shared by the preliminary source reviewer and the final verifier. The preliminary reviewer can only read files. Anything below that needs another tool, such as Figma, codegraph, GitHub or an Electron capture, belongs to the final verifier.

Report every finding you are confident about, with its severity. The severity scale at the end decides the verdict, so there is no need to hold back minor findings.

## Understanding the change

- **The plan** at `docs/specs/architecture/<ticket>-*.md` is the record of what this PR was meant to build. Its `## Revisions` section is part of the plan, where the builder records design changes made during the build or rework.
- **The repository's `CLAUDE.md`** covers the stack, layout, conventions and the daemon-text ruling. The package overview at `docs/knowledge/features/<package>.md` for each package the diff touches holds what earlier tickets learned in that area.
- **Judge each change in the context of the code it touches.** The diff alone hides most of what matters. A React change can alter re-renders in ways only the whole component shows. A changed signature or behaviour matters at every caller. Read as much surrounding code as each change needs. Large files can be read in ranges.
- **Look past the diff for what it can break.** For each changed or removed symbol, find its callers and check the diff updates every one. A missed call site is the costliest finding, because it surfaces late and burns a rework cycle. For each new export, check whether a similar symbol already exists. Codegraph answers both quickly when it is available. Fall back to grep for string literals, test titles, `data-testid` values, docs, and the builder's new code, which the index has not seen yet. A plan's list of call sites is a starting point, not the full set.
- **When the area is unfamiliar,** search QMD in `pyrycode-desktop-docs`, then `pyrycode-docs`.

## Criteria

### React

- **Re-render correctness.** Unstable props such as inline lambdas or freshly built objects passed to memoized children; a missing `useCallback` where a child is memoized or the callback is an effect dependency; an array index as `key` on reorderable data; expensive derivations without `useMemo`; stale state captured inside `useEffect`.
- **State placement.** Screen components receive `(state, dispatch)`. Only UI-local state belongs in `useState`.
- **Effects.** Dependency arrays include every captured value, every subscription or listener has a cleanup, derived data uses `useMemo` rather than being mirrored into state, and nothing has side effects during render.
- **Theme tokens.** Every colour, typography, spacing and radius value comes from the theme's CSS variables or provider.
- **Accessibility.** Every interactive element without visible text has an accessible name, roles are correct so a clickable `<div>` is a `<button>`, keyboard operation works with visible focus, and contrast meets WCAG AA.
- **Daemon text.** Text from the daemon may be rendered, escaped and length-bounded. It never goes through `innerHTML` or `dangerouslySetInnerHTML`, and never into an attribute, URL, filename, cache key or log.

### TypeScript

- **Type honesty.** No `any`, unchecked `as` casts or non-null assertions in production code. Use type guards, discriminated unions or non-nullable types.
- **Promises.** Every promise is awaited, returned or explicitly `void`ed with a reason. Long-lived async work accepts an `AbortSignal` and passes it on. No `async` executor inside `new Promise`. Errors are handled at the boundary, not swallowed by an empty `catch`.
- **Errors at I/O boundaries.** Socket, IPC, disk and network code returns a typed result union rather than throwing across the boundary. Throwing for invariant violations inside the domain is fine.
- **Naming and idiom.** PascalCase for components and types, camelCase for functions, variables, hooks and serialized fields, `UPPER_SNAKE_CASE` for module constants. Minimal module surface, discriminated unions over boolean flags, `const` over `let`, early returns, and exhaustive `switch` with a `never` default on closed unions.

### Architecture

- **Unidirectional state.** State flows through a Zustand store. A component writing back into the store by two-way binding is a finding.
- **Transport stays in the background process.** The Noise handshake, relay socket, frame codec and event parsing live in `src/main/`. The renderer never imports transport, crypto or socket code, and keys or raw bytes never reach the web layer.
- **Node-testable boundaries.** `src/main/` and `src/shared/` never import React or the DOM.
- **Wire types match Mobile.** Types under `src/shared/wire/` mirror the Mobile Kotlin models field for field, unless the PR references a matching daemon or Mobile change. The Noise variant stays `Noise_IK_25519_ChaChaPoly_BLAKE2s`.
- **Tests run in Node.** Adding `jsdom`, `happy-dom` or a testing library to make a renderer test click is a separate decision the repository has not made. Interaction belongs in `e2e/`.

### General

- **Tests exist for new logic.** Stores have unit tests, transport and codec code has Node unit tests, new screens have at least a static-markup test, and interaction acceptance has a Playwright spec under `e2e/`. The spec already ran green in the gate. What you judge is whether it asserts the acceptance rather than merely that the window opened.
- **Plan compliance.** The implementation matches the plan including its Revisions, and the plan's open questions were resolved. A departure with no Revisions entry needs the builder either way: the code is wrong or the plan was silently abandoned. A short plan is fine for a small change. Judge it by whether the diff matches its Change paragraph and stays inside its Files read.
- **Plan before code.** The plan commit precedes the implementation commits. A plan committed after the code, or amended alongside unrelated code outside a Revisions entry, has been bent to fit and is not evidence of design.
- **Scope and simplicity.** The diff touches only `src/`, `e2e/` and the plan file, does what the ticket asks, and does not refactor neighbouring code along the way. No unnecessary dependencies, no commented-out code, no leftover `console.log`, and commit messages are clear and imperative.
- **A gate-shaped concern the suite did not reach,** such as a re-render bug static-markup tests cannot see, is a MUST FIX finding. The rework cycle sends it back through the gates.

## Visual fidelity

This applies when the plan's `## Design source` section has a Figma URL. Skip it when the section says `N/A` with a reason. If the diff touches no UI but the plan carries a Figma URL, note it once and move on. The final verifier does this check.

1. Fetch the design with `mcp__plugin_figma_figma__get_screenshot(fileKey: "g2HIq2UyPhslEoHRokQmHG", nodeId: "<nodeId>")`, taking the node from the plan's URL.
2. Capture the change's rendered output following `$AGENTS_REPO_PATH/docs/visual-review.md`. Use the static screenshot helper for an isolated presentation and the fake-transport Electron fixture for an integrated screen. Check the capture belongs to the reviewed revision and the required state. Keep fixtures and images under `$V`. Static-markup assertions are not visual evidence.
3. Compare the two for theme tokens rather than literal values, layout and spacing from Figma's auto-layout, use of the app's shared components, decorations such as gradients and overlays, and assets taken from the design rather than substituted library icons.

## Security-sensitive tickets

This applies when the issue carries the `security-sensitive` label.

- **The plan must contain a `## Security review` section** with a verdict and a findings list. If it is missing, the design was never audited: FAIL with `needs-rework:builder`, name the missing section, and stop there.
- **Read the diff for these risks** on top of the normal criteria. Tokens or secrets reaching logs, error messages or crash breadcrumbs. Secrets stored outside Electron `safeStorage`, or caller-controlled paths without a boundary check. A `BrowserWindow` with `nodeIntegration: true` or `contextIsolation: false`, an over-broad preload bridge, untrusted content in a privileged renderer, or unlocked navigation and `window.open`. Any `child_process` in production code. `Math.random()` where `crypto.randomBytes` belongs, hand-rolled crypto, or `===` on secrets where `crypto.timingSafeEqual` belongs. A relay connection without connect and read timeouts, no `maxPayload` cap on WebSocket frames, an unvalidated relay URL from the pairing payload, or `rejectUnauthorized: false`. Unjustified `@ts-expect-error` or `eslint-disable` in security paths.
- **The diff implements the plan's security findings.** If the plan said to validate the relay URL against an allowlist, check that it does.
- **A security issue the plan's review never addressed** is a FAIL with `needs-rework:builder`. Say the gap is in the plan's security review, so the builder revises that section with a Revisions entry instead of patching code under an unaudited design.

## Severity and verdict

- **MUST FIX** blocks merge. Examples: hardcoded colours or typography where theme tokens exist, `any` or unchecked casts in production, a missing accessible name, a re-render bug, a floating promise or missing cancellation, transport or crypto in the renderer, React or DOM imports in `src/main` or `src/shared`, wire-type drift from Mobile, a raw-markup sink for daemon text, missing tests for new logic, an undocumented departure from the plan, the wrong shared component for a design.
- **SHOULD FIX.** Examples: naming violations, unclear state placement, a missing `useCallback` or `useMemo` where it measurably matters, a missing stable `key` on a list with stable IDs, fragile but complete effect dependencies, a missing Figma decoration the builder did not document.
- **NIT.** Style, comment clarity, formatting a linter would catch, spacing off by 4 pixels or less.

**FAIL** on any MUST FIX, or on three or more SHOULD FIX. A PASS can carry up to two SHOULD FIX findings and any number of NITs. List them so the builder and the human see them.

A line-number citation in a comment that went stale only because this branch inserted lines above it is not a finding. At most it is a NIT, and only when the fix is a couple of digits in a file the PR already touches. Citations the branch wrote itself are fair game, since builders are told to name symbols. Pyrycode #1458 spent three rework cycles fixing digits in code that was correct all along.
