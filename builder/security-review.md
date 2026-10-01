# Security review — adversarial audit of your own plan

Run this pass when the issue carries the `security-sensitive` label, which the refiner applies. It comes after you write the plan and before you commit it. The pass appends a `## Security review` section to the plan, and the verifier fails a labelled ticket whose plan has none.

## The stance

For this pass you are not the designer. You are an adversary looking for what an attacker, a buggy caller or a confused implementer could trigger, and you assume the plan has holes. The verdict stays FAIL until you have walked every category below.

Two things make this hard:

1. **Self-bias.** You wrote this plan minutes ago and you are about to implement it, so you believe in it twice over. If a category looks fine at a glance, look harder there, because that is where this pass earns its keep.
2. **Coverage theatre.** Marking each category "N/A" is worth nothing. For each one, either name a concrete finding, with the symbol it lives in or a scenario the plan does not handle, or name the design decision that makes the category not apply.

## Categories

For each category, ask: given this plan, what is the worst thing a hostile actor, a buggy caller or a confused implementer could trigger?

### 1. Trust boundaries

- Where does data cross from untrusted to trusted? Relay socket to main process, disk file to memory, renderer IPC message to main-process state, daemon response to parsed model.
- Is each boundary explicit, one function or one named type, or scattered across several parse sites?
- Does the plan say what "trusted" means at each boundary, and do downstream callers know which they hold? Branded types or discriminated unions make that visible.
- The renderer is untrusted relative to the main process. Every message crossing `contextBridge` or `ipcMain` is an untrusted-to-trusted boundary, even though both sides are our code.

### 2. Tokens, secrets, credentials

- Generation: `crypto.randomBytes` in Node or `crypto.getRandomValues` in WebCrypto, with enough entropy. `Math.random()` is for non-security uses only.
- Storage: Electron `safeStorage`, backed by the OS keychain. Reject plaintext JSON on disk and renderer `localStorage` or `sessionStorage` for tokens.
- Do tokens reach logs, error messages, thrown errors or stack traces?
- Lifecycle: creation, storage, rotation, revocation and expiry. Is revocation possible, per device or all at once, and how does it propagate between the daemon and the desktop client?

### 3. File and storage operations

- Path traversal: does any path concatenate untrusted input, such as a pairing payload, a deep-link argument or a daemon response field, without `path.resolve` and a prefix check against a known root? A raw `path.join` with `..` escapes the root.
- Check-then-use races: an `fs.existsSync()` followed by `fs.readFile()` on a caller-controlled path can be swapped in the gap. Prefer opening first and checking the file descriptor.
- Scope: sensitive data belongs under `app.getPath('userData')` with restrictive permissions, not in a world-readable temp folder or a synced cloud folder. Does the plan say so?
- Encryption at rest: `safeStorage.encryptString` and `decryptString` for device tokens and any decrypted cached message bodies. The plan names the choice and the fallback when `safeStorage.isEncryptionAvailable()` is false.
- Atomic writes: files that could be left half-written if the app is killed, such as `devices.json`, the conversation cache or draft state, are written to a temp file and renamed. A bare `fs.writeFile` can truncate, then die.
- Leaks through the OS or browser: crash dumps, `localStorage`, IndexedDB and the renderer's disk cache. Sensitive state stays out of renderer-side web storage.

### 4. Electron attack surface

- `webPreferences`: every window that can load app UI sets `contextIsolation: true`, `nodeIntegration: false` and `sandbox: true`. The plan justifies any deviation. A renderer with Node integration and a script-injection bug is a full-machine compromise.
- IPC surface: for every `contextBridge` API and `ipcMain.handle` or `ipcMain.on` channel the plan adds, is every argument validated for type, length, shape and allowed values before use? Is the API limited to exactly what the renderer needs, with no raw filesystem, raw socket or "run this"? Do not expose `ipcRenderer` or Node primitives through the bridge.
- Custom protocols and deep links: if the plan registers a scheme or calls `app.setAsDefaultProtocolClient`, what scheme, host and path checks stop a third-party app or a crafted link from triggering it with attacker data? Parse and validate the URL before acting on it.
- Navigation: a `will-navigate` guard and `setWindowOpenHandler` block untrusted origins and deny or externalise `window.open`. A renderer that navigates to attacker HTML runs attacker script with privileges.
- Remote content: never load remote or untrusted content into a renderer with IPC access to transport or keys. Web content goes in a sandboxed, isolated window with no IPC, or in the external browser. The plan says so explicitly.
- Process placement: transport, keys and the Noise handshake live in the main process. A secret or socket within the renderer's reach is a MUST FIX.

### 5. Cryptographic primitives

- Randomness: as in category 2.
- Standard primitives: TLS through Node and `ws` defaults, `crypto.createHash('sha256')` for hashing, `crypto.scrypt`, Argon2 from a vetted library, or `crypto.pbkdf2` for key derivation. Hand-rolled crypto is a finding on sight.
- Noise: `Noise_IK_25519_ChaChaPoly_BLAKE2s` comes from a vetted Noise implementation. Re-implementing any part of the handshake, key schedule or AEAD framing in TypeScript is a MUST FIX.
- Key storage: `safeStorage` at rest; static keys in main-process memory only, never serialised to the renderer or to a plaintext file.
- Key and nonce reuse: Noise nonces are per-direction counters, and a reset without a rekey is catastrophic. Confirm the plan never reuses a key and nonce pair across purposes or sessions.
- Comparison: `crypto.timingSafeEqual` on equal-length buffers wherever an attacker-controlled value is compared with a secret. Never `===`, `==` or `Buffer.equals` for tokens or MACs.

### 6. Network and I/O

- Frame size: the relay WebSocket sets `maxPayload`. An uncapped frame lets a hostile relay exhaust memory.
- Relay URL: the pairing payload carries it. The plan validates it before use: `wss://` only, a host check, no embedded credentials, and unexpected ports rejected if the design constrains them. Otherwise a malicious QR code points the client at an attacker's endpoint.
- Timeouts: connect, idle and per-message deadlines on the socket, whether `ws` or Electron `net`, plus a heartbeat with a liveness timeout that tears down a dead connection. Defaults can hang forever.
- TLS: `wss://` with TLS 1.2 or later, and no `ws://` in production. `rejectUnauthorized: false` anywhere is a MUST FIX unless pinned and justified.
- Pinning: does the plan pin the relay's certificate or CA, or verify the hostname beyond default TLS? If it rejects pinning because of rotation cost, it says so.
- Reconnects: exponential backoff on auth and connect failures, so a rejected token does not spin into a loop, and an `AbortController` cancels in-flight connects on teardown.
- Slow relays: a per-message read deadline beyond the connect timeout, so a relay that dribbles bytes cannot hold a handler open.

### 7. Errors, logs, telemetry

- User-facing errors in the renderer are generic. Detail goes to main-process logs.
- Error messages and crash or telemetry reports carry no tokens, keys, Noise transcripts, full headers, file paths, internal state or stack traces with secrets in them.
- The plan names what is never logged, such as message bodies, handshake transcripts, keys, tokens and full headers, and what is always logged, such as event type, server ID, connection ID and host.
- Log files under `userData` are readable by anything running as the user. Where do they live, and are they rotated and capped?
- Telemetry: does it collect identifying data without consent, and is it opt-in or opt-out?
- Main-process secrets never reach the renderer's DevTools console.

### 8. Concurrency

- Ownership: every long-lived async task the plan starts, such as the relay read loop, a reconnect timer or a pending daemon request, has an owner that cancels it. Work that outlives its window is a common leak.
- Cancellation: an `AbortSignal` is threaded through cancellable network and I/O calls and actually aborted on teardown; timers are cleared; listeners are removed, with no leaks and no double firing.
- Races across `await`: reading shared store state, awaiting, then mutating it lets a concurrent handler change it in the gap. Guard it with a queue, a single writer or a version check.
- Shutdown: on window close, `app.quit` or a kill mid-write or mid-send, is the relay socket closed cleanly, the Noise session torn down, listeners removed and temp files finalised, so the next start recovers?
- Duplicate connections: can a fast reconnect plus a stale socket leave two live transports? The design guarantees one, reusing or replacing rather than stacking.

### 9. Threat model alignment

- The wire-protocol security model lives in the `pyrycode` repo, in ADR 025 and the protocol docs. Does the design address each protocol-level threat that applies to the desktop client?
- Name each desktop threat and either address it or defer it explicitly:
  - **A malicious or compromised relay.** It cannot read inside the Noise session, but it is on the path and can drop, delay, reorder or flood. Does the design survive without leaking plaintext or hanging?
  - **Token theft from disk** by someone with read access to the user's files. Does `safeStorage` raise the bar, and what happens when the keychain is unavailable?
  - **A hostile daemon response,** malformed or oversized. Is every response parsed defensively?
  - **A compromised renderer** through script injection or a supply-chain bug. Does process isolation keep it away from keys, the token and the raw socket?
- A threat out of scope for this ticket is named as such, with who picks it up.

## Decision

Classify each finding:

- **MUST FIX**: exploitable as designed. The plan changes before you commit it.
- **SHOULD FIX**: concerning but recoverable during implementation. Note it in the plan, add the check in Phase B, and the verifier checks it landed. It does not block the commit.
- **OUT OF SCOPE**: deferred on purpose. Name the ticket that takes it.

The verdict is FAIL if any finding is MUST FIX. Revise the plan to address each one, then walk the categories again from the top, without committing in between. With no MUST FIX left, the verdict is PASS: append the section below, commit the plan and start Phase B.

## Output: append to the plan

Add this section at the end of `docs/specs/architecture/{ticket}-{slug}.md`:

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

"Nothing user-controlled flows here" is a finding too: record it under Trust boundaries, naming the symbol that enforces it. Each plan is reviewed on its own, so do not point at another ticket's review in place of this one.
