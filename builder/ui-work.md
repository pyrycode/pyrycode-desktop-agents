# UI work — Pyrycode Desktop builder

Read this on a UI-visible ticket, before you plan the UI. There is no separate design stage: your plan is where design intent gets pinned, and the verifier compares the result against the Figma node it names. `CLAUDE.md` § UI-visible work says when the run stops instead, for a ticket with no `## Figma` section or a Figma node this run cannot read.

## Read the Figma node

The design file for this repo is `g2HIq2UyPhslEoHRokQmHG`. Take the node ID from the ticket's `## Figma` URL. URLs write it with a hyphen, as in `102-4`.

- **Design context.** `mcp__plugin_figma_figma__get_design_context(fileKey: "g2HIq2UyPhslEoHRokQmHG", nodeId: "<nodeId>")` returns the layout, typography, colour tokens and spacing. If a large frame comes back truncated, get the node map with `mcp__plugin_figma_figma__get_metadata` and read the children one at a time.
- **Screenshot.** `mcp__plugin_figma_figma__get_screenshot` with the same arguments. Look at it, and do not write the summary from the structured data alone. Keep it, because you compare your render against it before the PR.
- **Design tokens.** When the plan needs exact variable values, such as every mode of a new colour token, call `mcp__plugin_figma_figma__get_variable_defs` on a node that uses the variable, and find one by name with `mcp__plugin_figma_figma__search_design_system`. Write the hex values into the plan, so they survive a continuation leg or a rework.

These are the Claude tool names. A runner with no Figma tools cannot do this step, and the run stops as blocked.

## The plan's Design source section

```markdown
## Design source

**Figma:** https://www.figma.com/design/g2HIq2UyPhslEoHRokQmHG?node-id=<nodeId>

<One-to-three sentence visual summary>: layout shape (column / row / box), the React components used, key tokens (which theme color tokens, which text styles), and any notable decorations (gradients, icons, atmospheric overlays) that must be reproduced.
```

When the ticket's section reads `N/A — <justification>`, put that line under the heading instead, so the verifier knows the visual check is skipped on purpose.

## Translate the design into the app

Figma's output is reference data, not code to paste.

- **Colours** become the app's theme tokens or CSS variables, such as `var(--color-primary)`, never hex literals. Map Figma's scheme roles onto the app's role tokens.
- **Typography and spacing** use the app's type-scale and spacing tokens, derived from Figma's values rather than copied as numbers.
- **Components** come from the app's existing shared components first. Build a custom one only when the app has no equivalent.
- **Assets.** When the design context returns local SVG or PNG sources, download them under `src/renderer/src/assets/`. Use the design's asset rather than a placeholder or a new icon package.

## Compare the render before the PR

Follow `$AGENTS_REPO_PATH/docs/visual-review.md`. Capture an isolated component with its static screenshot helper, or an integrated screen with the existing fake-transport Electron fixture. Keep fixtures and images in your scratch folder, outside the worktree. Open the captured image and compare it with the Figma screenshot: layout, typography, colours, required states, assets and decorations. Passing static-markup tests are not visual evidence.

Record the viewport sizes and image paths in the PR's Visual evidence section. If a deviation remains, explain it in a code comment and in the PR body. A capture that cannot run is a missing piece of evidence to name in the PR, not a pass.
