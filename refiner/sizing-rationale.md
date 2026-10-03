# Sizing rationale — Pyrycode Desktop refiner

The measurements behind the Sizing Guide in `CLAUDE.md`. Read this only when a sizing call is genuinely borderline, or when you are asked to revisit the table. The rules themselves live in `CLAUDE.md`; this file only explains them.

## Why the criteria count is not a template

On this repo on 2026-08-24, 66 of the last 80 refined tickets carried exactly five acceptance criteria, against a median body of 7757 characters, and 19 of the last 100 were closed as not planned. A limit that binds on four tickets in five regardless of size has stopped measuring the ticket. Upstream on 2026-09-01, five tickets to commit one captured test file each carried four or five criteria, and $213 was spent by mid-morning against a projection near $330. On 2026-09-07, eighteen tickets sat in the two pilot Backlogs at six to nine criteria because the filer had filled them; splitting those would have paid a refiner pass and a builder run per child for no work gained.

## Why padded bodies cause recursive splits

The builder sizes from the body. A body inflated to the ceiling measures as oversized, gets split, and each child written back up to the ceiling measures oversized again. Upstream #1714 on 2026-08-24 became #1728 and #1729, then #1728 became #1730 and #1731, then #1730 became #1732 and #1733: three rounds in one morning, none prompted by anything learned from code, and each child's body longer than its parent (3940 characters, then 10531, then 18683). The `Estimate:` line breaks that loop, because the builder then agrees or disagrees with a number instead of re-deriving one from prose length.

## Why total written work, not production lines

Three upstream specs on 2026-05-16 were sized by production lines alone and came in at 541, 596 and 1071 actual lines. All three needed salvage. Tests, helpers and per-branch log calls are routinely three to five times the production code, and a React state machine with its store, fixtures and log calls accumulates the same way.

## Why the floor wins over the ceiling

On the upstream #1720 split, 2026-09-02, four one-consumer pairs were cut apart to stay under the old 400-line ceiling: map then bound, retain then resolve, reconcile then wire, and a docs-only tail. Ten tickets carried what five would have. The first three children still measured over the ceiling and shipped at a third of the builder's budget.

## Why the ceiling is 800 lines

The 400-line, three-file table was set for the classic developer at 135 turns and 25 minutes. It was recalibrated to the builder on 2026-09-02. Across the builder's first 21 runs on this repo, on 2026-09-01 and 2026-09-02, no run exhausted its budget: the median run used 57 turns and 10 minutes, the heaviest 82 turns and 19 minutes (both #912). The median merged PR added about 920 lines including plan and docs, so most tickets were already landing above the old ceiling and inside a third of the budget. 800 lines sits inside a two-times margin of the heaviest run. Line count predicts effort weakly (#911 landed 1820 added lines in 47 turns, #912 landed 1310 in 82), so the ceiling bounds the tail rather than sizing the typical ticket, and the call-site and reject-branch lines bind regardless.

A five-file ceiling sat beside it until 2026-10-03, when it was removed. File count measured how a change is wired rather than how much work it is: a new `DaemonEvent` arm forces a one-line case in about eight files, so a 90-line change counted as twelve. It did not bound the tail either: #1249, estimated at 1300 lines over 12 files, built in 154 turns and 26 minutes. The call-site and exported-type lines still guard coupling.

**Revisit only on new evidence.** Re-measure after ten more builder runs before moving the number: read turns and duration from the usage block at the end of each builder log, and search the logs for `Resume leg`. A run that exhausts a second leg is the first real evidence for tightening. Record it on the ticket rather than tightening from memory of the old table.

## Why the default no longer leans towards splitting

Until 2026-09-02 the guide leaned towards splitting, because a run that exhausted its budget was salvaged into a draft PR, labelled `error:max_turns_salvaged`, and parked for a person. Pyrycode #29 and #40, the exhaustions that default cited, both ran before any resume existed. Under the Claude runner an exhausted builder run now gets one continuation leg in the same session before salvage. Under the Codex runner there is no automatic continuation.

Costs on this repo's builder set, measured 2026-09-02 from the run logs of #919, #920 and #921:

| Outcome | Measured cost |
|---|---|
| One ticket through refiner, builder, verifier and documentation, clean | ~$8-16, median ~$12 |
| The builder leg alone | ~$4-8 |
| Extra cost of one more split | ~$12, plus a refiner pass on each child |
| Extra cost of a budget miss that resumes | ~one builder leg |

An extra split costs about twice the resume leg it insured against, and under the old table it no longer bought the safety it used to. Upstream under the six-agent relay on 2026-09-01, across 88 tickets, the figures were about $32 per clean ticket, $16 per rework pass and $32 per extra split. The shape was the same.

## Why there is no M tier

An M tier with a "Sized M because" paragraph was removed on 2026-05-02 after pyrycode #45, sized M with five files of cross-package coordination and ten criteria, exhausted its implementation budget and needed recovery. The six-agent relay's design stage carried the same "why M, not split" escape and it went the same way. Both were rationalisation paths that reliably produced budget exhaustion.
