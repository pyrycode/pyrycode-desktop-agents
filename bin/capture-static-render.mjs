#!/usr/bin/env node
// Capture synthetic server-rendered markup. This does not drive the application.
import { readFile, access } from 'node:fs/promises'
import { createRequire } from 'node:module'
import { resolve } from 'node:path'

const [worktree, input, output, widthArg = '1280', heightArg = '800', ...extra] = process.argv.slice(2)
const width = Number(widthArg)
const height = Number(heightArg)
if (!worktree || !input || !output || extra.length || !output.endsWith('.png') ||
    !Number.isInteger(width) || !Number.isInteger(height) || width < 1 || height < 1) {
  throw new Error('Usage: node capture-static-render.mjs WORKTREE INPUT.json OUTPUT.png [WIDTH HEIGHT]')
}
if (process.platform === 'darwin' && process.env.CODEX_SANDBOX === 'seatbelt') {
  throw new Error('Request approved execution outside the Codex sandbox before launching Chromium')
}
const { markup, css } = JSON.parse(await readFile(input, 'utf8'))
if (typeof markup !== 'string' || typeof css !== 'string') {
  throw new Error('The input must contain markup and css strings')
}
const require = createRequire(resolve(worktree, 'package.json'))
const { chromium } = require('playwright')
const executablePath = chromium.executablePath()
await access(executablePath)
const browser = await chromium.launch({
  headless: true,
  executablePath,
  chromiumSandbox: true,
  env: Object.fromEntries(['PATH', 'HOME', 'TMPDIR', 'LANG']
    .filter(key => process.env[key] !== undefined).map(key => [key, process.env[key]]))
})
try {
  const context = await browser.newContext({
    viewport: { width, height }, deviceScaleFactor: 1,
    javaScriptEnabled: false, serviceWorkers: 'block', offline: true
  })
  await context.route('**/*', route => route.abort())
  const page = await context.newPage()
  const errors = []
  page.on('console', message => {
    if (message.type() === 'error') errors.push(message.text())
  })
  page.on('requestfailed', () => errors.push('A resource request failed'))
  await page.setContent(`<!doctype html><html><head><meta charset="utf-8">
    <meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; img-src data:; font-src data:; base-uri 'none'; form-action 'none'">
    <style>html,body{margin:0;min-height:100%}${css}</style>
    </head><body>${markup}</body></html>`)
  const layout = await page.evaluate(async () => {
    await document.fonts.ready
    if ([...document.images].some(image => !image.complete || !image.naturalWidth)) {
      throw new Error('Inline all image assets before capture')
    }
    return { documentWidth: document.documentElement.scrollWidth,
      documentHeight: document.documentElement.scrollHeight }
  })
  if (errors.length) {
    throw new Error('Capture has blocked resources or browser errors. Inline required CSS, fonts and images before retrying.')
  }
  await page.screenshot({ path: output, animations: 'disabled' })
  console.log(JSON.stringify({ screenshot: resolve(output), width, height, ...layout }))
} finally {
  await browser.close()
}
