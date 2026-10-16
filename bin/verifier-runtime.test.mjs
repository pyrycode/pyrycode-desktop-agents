import { test } from 'node:test'
import assert from 'node:assert/strict'
import { readFileSync, writeFileSync, mkdtempSync, chmodSync, existsSync, rmSync, mkdirSync, symlinkSync } from 'node:fs'
import { join, resolve } from 'node:path'
import { tmpdir } from 'node:os'
import { spawnSync } from 'node:child_process'

const root = resolve(import.meta.dirname, '..')
const preload = join(root, 'bin/verifier-runtime.mjs')
const full = 'npm install --no-audit --no-fund;npm test;npm run build;npx playwright test --reporter=json'
const baseline = 'npm install --no-audit --no-fund >&2 && npm run build >&2 && npx playwright test --reporter=json -g {{TESTS}}'

function configure(gates = full, template = baseline) {
  const result = spawnSync(process.execPath, ['--import', preload, '-e', 'console.log(JSON.stringify({gates:process.env.PYRY_VERIFIER_GATES,formats:process.env.PYRY_VERIFIER_GATE_FORMATS}))'], {
    encoding: 'utf8', env: { ...process.env, AGENTS_REPO_PATH: root, PYRY_VERIFIER_GATES: gates,
      PYRY_VERIFIER_GATE_FORMATS: JSON.stringify({ 'npx playwright test --reporter=json': { format: 'playwright-json', baseline: template } }) }
  })
  assert.equal(result.status, 0, result.stderr)
  return JSON.parse(result.stdout)
}

function fixture() {
  const directory = mkdtempSync(join(tmpdir(), 'desktop-runtime-'))
  const log = join(directory, 'calls')
  const state = join(directory, 'runtime')
  const fake = `#!${process.execPath}
const fs=require('node:fs');const path=require('node:path');const args=process.argv.slice(2);const tool=path.basename(process.argv[1]);
fs.appendFileSync(process.env.TEST_RUNTIME_LOG,JSON.stringify([tool,...args])+'\\n');
if(tool==='npm'&&args[0]==='install')fs.writeFileSync(process.env.TEST_RUNTIME_STATE,'node');
if(tool==='npm'&&args[0]==='run'&&args[1].startsWith('rebuild:')){
 const mode=args[1].slice(8);console.log('preparing '+mode);if(process.env.TEST_RUNTIME_FAIL===mode)process.exit(23);fs.writeFileSync(process.env.TEST_RUNTIME_STATE,mode);
}
if(tool==='npm'&&args[0]==='test'&&fs.readFileSync(process.env.TEST_RUNTIME_STATE,'utf8')!=='node')process.exit(42);
if(tool==='npx'){
 if(fs.readFileSync(process.env.TEST_RUNTIME_STATE,'utf8')!=='electron')process.exit(43);
 console.log(JSON.stringify({executed:1,passed:1,failed:0}));
}
`
  for (const tool of ['npm', 'npx']) { const p = join(directory, tool); writeFileSync(p, fake); chmodSync(p, 0o755) }
  return {
    directory, log,
    env: { ...process.env, PATH: directory + ':' + process.env.PATH, TEST_RUNTIME_LOG: log, TEST_RUNTIME_STATE: state },
    calls() { return existsSync(log) ? readFileSync(log, 'utf8').trim().split('\n').map(JSON.parse) : [] },
    close() { rmSync(directory, { recursive: true }) }
  }
}
function run(command, f, failure = '') {
  return spawnSync('/bin/sh', ['-c', command], { cwd: f.directory, env: { ...f.env, TEST_RUNTIME_FAIL: failure }, encoding: 'utf8' })
}

test('real launcher applies preparation after the environment loader supplies old settings', () => {
  const f = fixture()
  try {
    for (const path of ['bin', 'target', 'dispatcher/src', 'dispatcher/scripts', 'dispatcher/node_modules/tsx']) mkdirSync(join(f.directory, path), { recursive: true })
    for (const name of ['pyry-start', 'verifier-runtime.mjs']) writeFileSync(join(f.directory, 'bin', name), readFileSync(join(root, 'bin', name)))
    writeFileSync(join(f.directory, '.env'), '')
    writeFileSync(join(f.directory, 'dispatcher/src/managed-dispatch.ts'), '')
    writeFileSync(join(f.directory, 'dispatcher/node_modules/tsx/package.json'), JSON.stringify({ type: 'module', exports: './index.mjs' }))
    writeFileSync(join(f.directory, 'dispatcher/node_modules/tsx/index.mjs'), 'export {}')
    writeFileSync(join(f.directory, 'dispatcher/src/dispatch-bin.ts'), `require('node:fs').writeFileSync(process.env.TEST_CONFIG_RESULT, JSON.stringify({gates:process.env.PYRY_VERIFIER_GATES,formats:process.env.PYRY_VERIFIER_GATE_FORMATS,managed:process.env.PYRY_MANAGED}))`)
    const scripts = {
      'dispatcher/scripts/install-deps.sh': '#!/bin/sh\nexit 0\n',
      access: '#!/bin/sh\nshift\nexec op "$@"\n',
      op: '#!/bin/sh\nwhile [ "$1" != -- ]; do shift; done\nshift\nexport PYRY_VERIFIER_GATES="$TEST_OLD_GATES"\nexport PYRY_VERIFIER_GATE_FORMATS="$TEST_OLD_FORMATS"\nexec "$@"\n',
      pgrep: '#!/bin/sh\nexit 1\n', sleep: '#!/bin/sh\nexit 0\n'
    }
    for (const [name, content] of Object.entries(scripts)) { const path = join(f.directory, name); writeFileSync(path, content); chmodSync(path, 0o755) }
    symlinkSync(process.execPath, join(f.directory, 'node'))
    const resultPath = join(f.directory, 'configured.json')
    const result = spawnSync('/bin/sh', [join(f.directory, 'bin/pyry-start'), '--managed', '--runner', 'codex'], {
      encoding: 'utf8', timeout: 15000,
      env: { ...f.env, TARGET_REPO_PATH: join(f.directory, 'target'), PYRY_AUTOMATION_ACCESS: join(f.directory, 'access'),
        TEST_CONFIG_RESULT: resultPath, TEST_OLD_GATES: full,
        TEST_OLD_FORMATS: JSON.stringify({ 'npx playwright test --reporter=json': { format: 'playwright-json', baseline } }) }
    })
    assert.equal(result.status, 0, result.stdout + result.stderr)
    const actual = JSON.parse(readFileSync(resultPath, 'utf8'))
    assert.equal(actual.managed, '1')
    assert.match(actual.gates, /rebuild:node;npm test/)
    assert.match(actual.gates, /npm run build;npm run rebuild:electron;npx playwright test --reporter=json/)
    assert.match(JSON.parse(actual.formats)['npx playwright test --reporter=json'].baseline, /verifier-runtime\.mjs.*electron -- npx playwright test/)
  } finally { f.close() }
})

test('full gate keeps selection and puts each preparation before its own runtime', () => {
  const f = fixture()
  try {
    const unprepared = run(full.replaceAll(';', ' && '), f)
    assert.equal(unprepared.status, 43, 'the old full gate reproduces the wrong-runtime launch')
    writeFileSync(f.log, '')
    const value = configure()
    const gates = value.gates.split(';')
    assert.deepEqual(gates, ['npm install --no-audit --no-fund', 'npm run rebuild:node', 'npm test', 'npm run build', 'npm run rebuild:electron', 'npx playwright test --reporter=json'])
    for (const gate of gates) assert.equal(run(gate, f).status, 0, gate)
    assert.deepEqual(f.calls().map(x => x.join(' ')), gates)
    assert.equal(JSON.parse(value.formats)['npx playwright test --reporter=json'].format, 'playwright-json')
  } finally { f.close() }
})

{
  const path = 'shared diagnostic/baseline template'
  for (const failure of ['', 'electron']) {
    test(`${path}: Electron preparation ${failure ? 'failure prevents launch' : 'runs after build and keeps report stdout clean'}`, () => {
      const f = fixture()
      try {
        const value = configure()
        const template = JSON.parse(value.formats)['npx playwright test --reporter=json'].baseline
        const result = run(template.replace('{{TESTS}}', "'the exact failing case'"), f, failure)
        const calls = f.calls().map(x => x.join(' '))
        assert.ok(calls.indexOf('npm run build') < calls.indexOf('npm run rebuild:electron'))
        if (failure) {
          assert.equal(result.status, 23)
          assert.ok(!calls.some(x => x.startsWith('npx ')))
          assert.equal(result.stdout, '')
          assert.match(result.stderr, /preparing electron/)
        } else {
          assert.equal(result.status, 0, result.stderr)
          assert.deepEqual(JSON.parse(result.stdout), { executed: 1, passed: 1, failed: 0 })
          assert.equal(calls.at(-1), 'npx playwright test --reporter=json -g the exact failing case')
        }
      } finally { f.close() }
    })
  }
}

test('a failed full-gate rebuild stops before any Electron launch', () => {
  const f = fixture()
  try {
    let result
    for (const gate of configure().gates.split(';')) { result = run(gate, f, 'electron'); if (result.status !== 0) break }
    assert.equal(result.status, 23)
    assert.ok(!f.calls().some(x => x[0] === 'npx'))
  } finally { f.close() }
})

test('explicitly disabled gates stay disabled', () => assert.equal(configure('').gates, ''))
