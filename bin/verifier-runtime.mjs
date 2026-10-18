// Load after op run resolves .env, before the shared dispatcher reads its gates.
import { fileURLToPath } from 'node:url'
import { realpathSync, existsSync, readFileSync } from 'node:fs'
import { parseEnv } from 'node:util'
import { spawnSync } from 'node:child_process'

const script = fileURLToPath(import.meta.url)
const quote = value => "'" + value.replaceAll("'", "'\\''") + "'"
const wrapper = mode => `${quote(process.execPath)} ${quote(script)} ${mode} -- `
const unit = /^npm test(?:\s|$)/
const electron = /^(?:npx )?playwright test(?:\s|$)/
const unitGate = `python3 ${quote(fileURLToPath(new URL('./unit-test-gate.py', import.meta.url)))}`
const nativePreparation = mode => `python3 ${quote(fileURLToPath(new URL('./native-preparation.py', import.meta.url)))} ${mode}`

export function prepareVerifierEnvironment(env) {
  // Desktop's default application suite includes captured client replay.
  // Retire label parking as well as execution, even with stale .env settings.
  // The shared dispatcher pin must understand ENABLED=0 before this rolls out.
  env.PYRY_REAL_CLAUDE_GATE_ENABLED = '0'
  env.PYRY_REAL_CLAUDE_GATE_CMD = ''
  if (env.PYRY_VERIFIER_GATES?.trim()) {
    const gates = []
    const configured = env.PYRY_VERIFIER_GATES.split(';').map(x => x.trim()).filter(Boolean)
    for (const [index, gate] of configured.entries()) {
      if (gate === 'npm run rebuild:node' && configured[index + 1] === 'npm test') continue
      if (gate === 'npm run rebuild:electron' && electron.test(configured[index + 1] ?? '')) continue
      const preparation = electron.test(gate) ? nativePreparation('electron') : null
      if (preparation && gates.at(-1) !== preparation) gates.push(preparation)
      gates.push(gate === 'npm test' ? unitGate : gate)
    }
    env.PYRY_VERIFIER_GATES = gates.join(';')
  }
  env.PYRY_VERIFIER_GATE_INPUTS_CMD ||= `python3 ${quote(fileURLToPath(new URL('./verifier-inputs.py', import.meta.url)))}`
  let formats = {}
  try { if (env.PYRY_VERIFIER_GATE_FORMATS?.trim()) formats = JSON.parse(env.PYRY_VERIFIER_GATE_FORMATS) } catch { return } // The dispatcher retains its normal configuration error.
  if (!formats || typeof formats !== 'object' || Array.isArray(formats)) return
  for (const spec of Object.values(formats)) {
    if (!spec || typeof spec.baseline !== 'string' || spec.baseline.includes(quote(script))) continue
    // Both same-tree diagnostics and fresh baseline worktrees use this template.
    if (spec.format === 'playwright-json') {
      spec.baseline = spec.baseline.replace(/\bnpx playwright test\b/, wrapper('electron') + 'npx playwright test')
    }
  }
  if (env.PYRY_VERIFIER_GATES?.split(';').includes(unitGate)) {
    formats[unitGate] = { format: 'junit-xml', baseline: `npm install --no-audit --no-fund >&2 && ${unitGate} --tests-json {{TESTS_JSON}}` }
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
  const preparation = spawnSync('python3', [fileURLToPath(new URL('./native-preparation.py', import.meta.url)), mode], { stdio: ['inherit', 2, 2] })
  if (preparation.error) console.error(preparation.error.message)
  if (preparation.status !== 0) process.exit(preparation.status ?? 1)
  const result = spawnSync(command, args, { stdio: 'inherit' })
  if (result.error) console.error(result.error.message)
  process.exit(result.status ?? 1)
} else {
  // Managed launchers may leave ordinary settings for dispatcher's later .env
  // load. Read only our two settings first, preserving inherited overrides and
  // empty values. Do not copy credentials or other configuration into the env.
  const keys = ['PYRY_VERIFIER_GATES', 'PYRY_VERIFIER_GATE_FORMATS']
  const file = new URL('../.env', import.meta.url)
  if (keys.some(key => process.env[key] === undefined) && existsSync(file)) {
    const saved = parseEnv(readFileSync(file, 'utf8'))
    for (const key of keys) if (process.env[key] === undefined && saved[key] !== undefined) process.env[key] = saved[key]
  }
  prepareVerifierEnvironment(process.env)
}
