# Security review pass — adversarial audit of your own plan

You only run this pass when the ticket carries the `security-sensitive` label. The refiner applies that label during refinement. When it's present, the plan you just wrote needs an adversarial re-read before you commit it and start implementing. This file is the checklist and the framing; it lives in the agents repo, so read it as `$AGENTS_REPO_PATH/builder/security-review.md` — it is not inside your worktree.

## Mindset shift

You are no longer the designer. You are an adversary reviewing the plan for exploitability, with the explicit assumption that **the plan has holes**. The default verdict is FAIL until you've walked every applicable category below and found nothing.

Two failure modes to actively resist:

1. **Self-bias.** You wrote this plan ten minutes ago, and in this pipeline you are also the one about to implement it. You believe in it twice over. The whole point of this pass is to find what you missed. If your gut says "this looks fine," that's the smell — go deeper, not shallower.
2. **Coverage theatre.** Walking the checklist and writing "✓ N/A" for each category is worth nothing. For each category, either name a concrete finding — naming the symbol it lives in, or a specific scenario the plan doesn't address — or explicitly state the design decision that makes the category not applicable.

## Categories — walk each one

For each category, the question to answer is: *given this plan, what's the worst thing a hostile actor (or a buggy caller, or a confused implementer) could trigger?*

### 1. Trust boundaries

- Where in the design does data cross from "untrusted" to "trusted"? (Relay socket → main process, disk file → memory, renderer IPC message → main-process state, daemon response → parsed model.)
- Is the boundary explicit (single function, named type) or scattered (parsed in three places)?
- Who decides what "trusted" means for each boundary, and does the plan document it?
- Do downstream callers know they're now holding trusted vs untrusted data? (Type system signal — branded types, discriminated unions? Comment? Convention?)
- The renderer is untrusted relative to the main process. Every IPC message crossing `contextBridge` / `ipcMain` is an untrusted-to-trusted boundary, even though both sides are "our code."

### 2. Tokens, secrets, credentials

- How are tokens generated (`crypto.randomBytes` on Node / `crypto.getRandomValues` on WebCrypto vs `Math.random()`; sufficient entropy)? `Math.random()` is non-security only.
- How are tokens stored (plaintext JSON on disk? `localStorage` / `sessionStorage` in the renderer? Electron `safeStorage` backed by the OS keychain? what's the threat model that justifies the storage choice)? Reject plaintext files and `localStorage` for tokens on sight.
- Where do tokens appear in logs (`console.log`, log files), error messages, thrown errors, or stack traces?
- Token lifecycle — creation, storage, rotation, revocation, expiry. Are all four addressed?
- For revocation: is it possible? Granular (per-device) or all-or-nothing? How is revocation propagated from the daemon to the desktop client (and vice versa)?

### 3. File / storage operations

- Path traversal — does any code path concatenate untrusted input (QR pairing payload, custom-protocol / deep-link argument, daemon response field) into a filesystem path without resolving + boundary-checking (`path.resolve` then a prefix check against a known root)? A raw `path.join` with `..` in the input escapes the root.
- TOCTOU — does the plan do `fs.existsSync()` then `fs.readFile()` (or similar check-then-open) on a path the caller controls? If so, how does the design prevent the swap-during-the-gap attack? Prefer open-then-check on the file descriptor over check-then-open.
- Storage scope — is sensitive data under the app's per-user data directory (`app.getPath('userData')`) with restrictive file permissions, and NOT in a world-readable temp dir or a synced cloud folder? Does the plan say it explicitly?
- Encryption at rest — for secrets (device tokens, cached message bodies if decrypted): `safeStorage.encryptString` / `decryptString` (OS-keychain-backed), never a plaintext file. The plan must name the choice and note the `safeStorage.isEncryptionAvailable()` fallback path.
- Atomic writes — does the design write to a temp file then `fs.rename` (atomic on the same filesystem) for files that could leave partial state if the app is killed mid-write (devices.json, conversation cache, draft state)? A bare `fs.writeFile` can truncate then die.
- OS integration — does the plan consider whether secrets could leak through crash dumps, `localStorage`, IndexedDB, or the renderer's disk cache? Sensitive state must not touch renderer-side web storage.

### 4. Inter-process / Electron attack surface

- `BrowserWindow` `webPreferences` — is `contextIsolation: true`, `nodeIntegration: false`, and `sandbox: true` set for every window that can load app UI? Any deviation must be justified in the plan. A renderer with Node integration and a script-injection bug is a full-machine compromise.
- IPC surface — for every `contextBridge` API and `ipcMain.handle` / `ipcMain.on` channel the plan adds, what does it accept? Is every argument validated (type, length, shape, allowed values) before use? Is the exposed API minimised to exactly what the renderer needs, or does it hand the renderer a broad capability (raw filesystem, raw socket, "run this")? Never expose `ipcRenderer` or Node primitives directly through the bridge.
- Custom protocol / deep links — if the plan registers a custom scheme or `app.setAsDefaultProtocolClient` handler (e.g. a pairing fallback URL), what scheme/host/path constraints prevent a third-party app or a crafted link from triggering the handler with attacker-controlled data? Validate and parse the URL before acting on it.
- Navigation and window-open — does the plan set a `will-navigate` guard and `setWindowOpenHandler` to block navigation to untrusted origins and deny or externalise `window.open`? An unguarded renderer that navigates to attacker HTML runs attacker script in a privileged context.
- Remote / untrusted content — the plan must NEVER load remote or untrusted content into a privileged renderer (one with IPC access to transport/keys). If web content must be shown, it goes in a sandboxed, isolated, no-IPC window or an external browser. State this explicitly.
- Process placement — the transport, keys, and Noise handshake live in the background (main) process, never the renderer. Does the plan keep every secret and every socket out of renderer reach? A finding here is a MUST FIX.

### 5. Cryptographic primitives

- RNG: `crypto.randomBytes` (Node) / `crypto.getRandomValues` (WebCrypto) everywhere randomness is security-relevant; `Math.random()` is acceptable only for non-security uses (jitter, test fixtures, animation seeds).
- Primitives: pick standards (TLS via Node/`ws` defaults, hashing via `crypto.createHash('sha256')`, key derivation via `crypto.scrypt` / Argon2 from a vetted library, or `crypto.pbkdf2` if that's overkill). Reject hand-rolled crypto on sight.
- Noise handshake: `Noise_IK_25519_ChaChaPoly_BLAKE2s` MUST come from a vetted Noise implementation, not be re-implemented in TypeScript. If the plan hand-rolls any part of the handshake, key schedule, or AEAD framing, that's a MUST FIX.
- Key storage — `safeStorage` (OS-keychain-backed) for at-rest secrets; static keys held in main-process memory only, never serialised to the renderer or to a plaintext file.
- Key / nonce reuse — does the design accidentally reuse a key or a nonce for two purposes or two sessions? Noise nonces are per-direction counters; a reset-without-rekey is catastrophic. Verify the plan never reuses a `(key, nonce)` pair.
- Constant-time comparison — is `crypto.timingSafeEqual` (on equal-length `Buffer`s) used wherever attacker-controlled values are compared to secrets? Never `===`, `==`, or `Buffer.equals` for token or MAC compare.

### 6. Network & I/O

- Frame size limits — for the WebSocket connection to the relay, every inbound message needs a max-size cap. The `ws` library takes `maxPayload`; verify the plan sets it and doesn't leave it unbounded. An uncapped frame is a memory-exhaustion vector from a hostile relay.
- Relay URL validation — the QR pairing payload carries the relay URL. Does the plan validate it before use: scheme allowlist (`wss://` only), host check, no embedded credentials, reject unexpected ports if the design constrains them? An unvalidated relay URL lets a malicious QR point the client at an attacker-controlled endpoint.
- Timeout discipline — the socket (via `ws` or Electron `net`) must set connect, read/idle, and per-message deadlines. Defaults can hang forever on a slow or hostile relay. Is there a heartbeat / ping-pong with a liveness timeout that tears down a dead connection?
- TLS configuration — enforce `wss://` (TLS 1.2+). Reject `ws://` for production. Does the plan disable TLS verification anywhere (`rejectUnauthorized: false`)? That's a MUST FIX unless there's a pinned, justified reason.
- Certificate / host pinning — for the relay endpoint, does the plan pin the relay's certificate or CA, or verify the expected hostname beyond default TLS? Pinning has tradeoffs (rotation pain) — if the plan rejects pinning, it should say why.
- Reconnect discipline — is there exponential backoff on auth failure and on connect failure, so a rejected token doesn't spin into a reconnect / token-exhaustion loop? Is an `AbortController` used to cancel in-flight connects on teardown?
- Slow-server resistance — does the design have a per-message read deadline beyond the connect timeout, so a relay that dribbles bytes can't pin a handler open indefinitely?

### 7. Error messages, logs, telemetry

- What goes in error messages — generic for user-facing UI (renderer surfaces), specific for `console` / log files in the main process?
- Do error messages leak: tokens, keys, Noise transcripts, full headers, file paths, internal state, stack traces? Any crash/telemetry reporter captures stack traces and error objects — strip secrets before they reach it.
- Logs — what fields are MUST-NOT-log (message bodies, Noise handshake transcripts, static/ephemeral keys, tokens, full headers), what fields are MUST-log (event type, server-id, conn-id, host)?
- Log files on disk — where do they live, who can read them, and do they get rotated / size-capped? A verbose log file under `userData` is readable by anything running as the user.
- Telemetry/metrics — do they aggregate user-identifiable data the user didn't consent to? Are analytics opt-in or opt-out, and does the plan say which?
- Renderer console — does the plan pipe main-process secrets to the renderer's DevTools console? Secrets logged in the renderer are visible to anything that can open DevTools.

### 8. Concurrency

- Async ownership — for every long-lived async task the plan launches (relay read loop, reconnect timer, pending daemon request), what owns it and what cancels it? Long-lived work that outlives the window it belongs to is a common leak.
- Cancellation safety — does the design thread an `AbortController` / `AbortSignal` through cancellable network and I/O calls, and actually abort on teardown? Are `setTimeout` / `setInterval` handles cleared? Are event listeners and socket listeners removed on cleanup (no listener leak, no double-fire)?
- Check-then-act races on shared state — does the design read shared store state then mutate it across an `await`, where a concurrent handler could change it in the gap? Guard the critical section (a queue, a single-writer, or a version check), don't assume single-threaded serialisation across awaits.
- Shutdown safety — what happens on window close / `app.quit` / process kill mid-write? Mid-Noise-send? Is the relay socket closed cleanly (Noise session torn down, listeners removed, temp files finalised) so the next start recovers a consistent state?
- Duplicate connections — can two relay sockets open at once (rapid reconnect + a stale one that never closed)? Does the design guarantee a single live transport, and reuse or replace rather than stack connections?

### 9. Threat model alignment

- The wire-protocol security model lives upstream in the `pyrycode` repo (ADR 025 and the protocol docs). Does the design address each protocol-level threat that applies to the desktop client?
- Desktop-specific threats to name and either address or explicitly defer:
  - **Malicious / compromised relay** — it is content-blind (it can't read inside the Noise session) but it is on-path: it can drop, delay, reorder, or flood. Does the design survive a hostile relay without leaking plaintext or hanging?
  - **Token theft from disk** — an attacker with read access to the user's disk. Does `safeStorage` (OS keychain) actually raise the bar here, and what's the fallback when the keychain is unavailable?
  - **Hostile daemon response** — the daemon (or something impersonating it inside the session) returns malformed or oversized data. Is every daemon response parsed defensively?
  - **Renderer compromise reaching the transport** — a script-injection or supply-chain bug in the renderer. Does process isolation stop it from reaching keys, the token, or the raw socket?
- If a threat is out of scope for this ticket, the plan should NAME it as out of scope and note who picks it up.

## Decision

After walking the categories, classify each finding:

- **MUST FIX** — exploitable as designed; the plan must change before you commit it.
- **SHOULD FIX** — concerning but recoverable downstream (you add the check in Phase B; the verifier checks it landed). Note in the plan; don't gate on it.
- **OUT OF SCOPE** — explicitly deferred to a future ticket. Name the future ticket.

Verdict:
- **Any MUST FIX** → FAIL. Revise the plan to address each, then re-run this checklist from the top. Do not commit the plan yet.
- **No MUST FIX** → PASS. Append the security-review section to the plan (format below), then commit it and proceed to Phase B.

## Output format — append to the plan

Add a new section at the end of `docs/specs/architecture/{ticket}-{slug}.md`:

```markdown
## Security review

**Verdict:** PASS

**Findings:**

- [Trust boundaries] No findings — design has a single explicit boundary at `src/main/transport/pairing.ts`'s `validatePairingPayload` function; downstream code holds parsed types only.
- [Tokens] SHOULD FIX — plan doesn't specify storage choice for the device token. Use Electron `safeStorage` in Phase B, never a plaintext file or `localStorage`; the verifier must check.
- [Electron attack surface] No findings — every window sets `contextIsolation: true`, `nodeIntegration: false`, `sandbox: true`; IPC surface is a fixed allowlist validated in `src/main/ipc/handlers.ts`.
- [Network & I/O] No findings — plan inherits the `ws` client with `maxPayload` and connect/idle timeouts from `src/main/transport/relayClient.ts`'s pattern.
- [Concurrency] OUT OF SCOPE — application-lifetime relay socket lifecycle deferred to ticket #N.
- [...]

**Reviewer:** builder (self-review per `builder/security-review.md`)
**Date:** <YYYY-MM-DD>
```

If verdict is FAIL, do NOT commit the plan yet. Revise inline, then re-run.
