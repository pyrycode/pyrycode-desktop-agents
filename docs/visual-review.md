# Visual review

Builder and verifier use this recipe when a ticket requires a rendered comparison
with Figma. Capture an image, open it with the available image-reading tool, and
compare layout, typography, colours, assets and the states required by the ticket.
Source inspection and passing static-markup tests do not establish visual fidelity.

## Choose the capture before launching tools

- For an isolated presentation, use the static capture below. It needs no interactive
  Chrome tab, local-file browser navigation, application route or live host.
- For an integrated screen or interaction, use the existing fake-transport Electron
  fixture. See the application capture section below.

Use synthetic content. Keep fixtures, JSON and images in the role's scratch folder.
Do not add a production preview route or modify shared documentation for a capture.
The verifier may create scratch fixtures but must not edit the reviewed worktree.

These are the default visual-review methods. Follow the current tool permissions.
On macOS, request approved execution outside the Codex sandbox before launching
Chromium or Electron. Do not add permission rules, disable browser sandboxing, or
switch methods to evade a security rejection. A rejection follows the recovery
procedure in [shared practice](working-practice.md#recovery-after-a-rejected-action).

## Static component capture

Install the target worktree's dependencies as required by the role. Run the commands
from that worktree so imports and styles come from the revision under review.
The capture uses its installed Playwright and Chromium. A missing Chromium executable
is a prerequisite failure. Report it and use the normal approval path for installation.

Create `render.ts` in the role's scratch folder. This example uses the existing Edit
host view. Replace the imported view, supplied props and stylesheet list for the ticket.
Render the actual component, never a hand-written imitation of its markup.

```ts
import { createRequire } from 'node:module'
import { readFileSync, writeFileSync } from 'node:fs'
import { resolve, dirname } from 'node:path'
import { fileURLToPath } from 'node:url'
import { EditHostDialogView } from '@renderer/screens/channels/EditHostDialog'

const require = createRequire(resolve('package.json'))
const { createElement } = require('react')
const { renderToStaticMarkup } = require('react-dom/server')
const markup = renderToStaticMarkup(createElement(EditHostDialogView, {
  name: 'Preview host', status: 'idle', server: null,
  onNameChange() {}, onCancel() {}, onSave() {}
}))
const css = [
  'src/renderer/src/theme/tokens.css',
  'src/renderer/src/screens/channels/channels.css'
].map(path => readFileSync(resolve(path), 'utf8')).join('\n')
writeFileSync(resolve(dirname(fileURLToPath(import.meta.url)), 'fixture.json'),
  JSON.stringify({ markup, css }))
```

Include any caller wrapper that supplies inherited fonts, sizing or layout. Include
its real styles too. Flatten CSS imports and inline required image and font files as
data URLs. An external asset blocked during capture is missing evidence, not a pass.
Do not substitute fonts or change production styling to make a preview look right.

Run the render in the workspace sandbox, replacing `/absolute/scratch` with the
role's scratch directory:

```bash
node node_modules/vite-node/vite-node.mjs --config vitest.config.ts /absolute/scratch/render.ts
```

Then request approved execution for this capture command on macOS. Replace both
absolute directory placeholders. The dispatcher exports `AGENTS_REPO_PATH`:

```bash
node "$AGENTS_REPO_PATH/bin/capture-static-render.mjs" /absolute/worktree /absolute/scratch/fixture.json /absolute/scratch/preview.png 1280 800
```

The helper loads static markup into a fresh headless browser context. It disables
page scripts, service workers and network access, keeps Chromium sandboxing enabled,
and accepts only inline styles and data assets in the page. It does not open a file
URL or the user's browser profile. It saves the visible viewport and prints its size
plus the document dimensions. Review the PNG, not just the successful exit code.

Capture the design size and any constrained sizes required by the ticket. For a
window-constrained dialog, include the app's 800px minimum width and a short window.
A viewport screenshot does not prove that off-screen content is reachable. Prove
scrolling, clicks, focus, Escape and backdrop behaviour in the application test tier.
Static rendering cannot execute React effects or event handlers.

## Application capture

Use the target's existing `e2e/fixtures/launchPairedApp.ts` fixture and the focused spec
that exercises the changed screen. It launches the built Electron app with a fake
host and temporary app data. Builders may add a screenshot to a ticket-owned spec:

```ts
await page.screenshot({ path: '/absolute/scratch/screen.png', animations: 'disabled' })
```

Wait for the expected screen state first. Build before running the focused spec.
On this MacBook use the approved helper described in
[Electron tests](working-practice.md#electron-tests-on-macos):

```bash
/Users/juhanailmoniemi/.codex/bin/pyrycode-desktop-test /absolute/worktree e2e/selected.spec.ts
```

Verifiers use existing captures or request approved execution for a scratch capture
that reuses the fixture. They do not edit the reviewed spec or rerun green full suites
to obtain one image. Real-host recordings and screenshots retain their existing limits.

## Evidence and handoff

Record the source revision, component and supplied state, viewport sizes, screenshot
paths and comparison result in the PR or review. Keep capture artifacts through the
review. Name any missing interaction or integration proof explicitly. A rendering
failure and a product mismatch are different findings.
