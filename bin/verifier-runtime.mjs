// Load after op run resolves .env, before the shared dispatcher reads its gates.
import { fileURLToPath } from 'node:url'
import { realpathSync } from 'node:fs'
import { spawnSync } from 'node:child_process'

const script = fileURLToPath(import.meta.url)
const quote = value => "'" + value.replaceAll("'", "'\\''") + "'"
const wrapper = mode => `${quote(process.execPath)} ${quote(script)} ${mode} -- `
const unit = /^npm test(?:\s|$)/
const electron = /^(?:npx )?playwright test(?:\s|$)/

export function prepareVerifierEnvironment(env) {
  if (env.PYRY_VERIFIER_GATES?.trim()) {
    const gates = []
    for (const gate of env.PYRY_VERIFIER_GATES.split(';').map(x => x.trim()).filter(Boolean)) {
      const preparation = unit.test(gate) ? 'npm run rebuild:node' : electron.test(gate) ? 'npm run rebuild:electron' : null
      if (preparation && gates.at(-1) !== preparation) gates.push(preparation)
      gates.push(gate)
    }
    env.PYRY_VERIFIER_GATES = gates.join(';')
  }
  if (!env.PYRY_VERIFIER_GATE_FORMATS?.trim()) return
  let formats
  try { formats = JSON.parse(env.PYRY_VERIFIER_GATE_FORMATS) } catch { return } // The dispatcher retains its normal configuration error.
  if (!formats || typeof formats !== 'object' || Array.isArray(formats)) return
  for (const spec of Object.values(formats)) {
    if (!spec || typeof spec.baseline !== 'string' || spec.baseline.includes(quote(script))) continue
    // Both same-tree diagnostics and fresh baseline worktrees use this template.
    if (spec.format === 'playwright-json') {
      spec.baseline = spec.baseline.replace(/\bnpx playwright test\b/, wrapper('electron') + 'npx playwright test')
    }
  }
  env.PYRY_VERIFIER_GATE_FORMATS = JSON.stringify(formats)
}

if (process.argv[1] && realpathSync(process.argv[1]) === script) {
  const [mode, separator, command, ...args] = process.argv.slice(2)
  if (!['node', 'electron'].includes(mode) || separator !== '--' || !command) {
    console.error('Usage: verifier-runtime.mjs node|electron -- COMMAND [ARGS]')
    process.exit(2)
  }
  // Setup must not contaminate the JSON report on stdout. Failure never launches tests.
  const preparation = spawnSync('npm', ['run', `rebuild:${mode}`], { stdio: ['inherit', 2, 2] })
  if (preparation.error) console.error(preparation.error.message)
  if (preparation.status !== 0) process.exit(preparation.status ?? 1)
  const result = spawnSync(command, args, { stdio: 'inherit' })
  if (result.error) console.error(result.error.message)
  process.exit(result.status ?? 1)
} else {
  prepareVerifierEnvironment(process.env)
}
