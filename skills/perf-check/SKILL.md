---
name: perf-check
description: Performance pass for every finished lane - read the diff for known slow patterns, then measure when the change is on a hot path (benchmarks, query plans, bundle size, test durations). Use after a lane passes verification, before the PR is reported.
---

# Performance check (every lane)

Evidence over opinion: a perf finding needs a measurement or a concrete count ("N queries per request for N items"). The result is appended to `$RUN/<lane>.verify.md` (the merge gate reads its last `PERF:` line there), never into the repo.

## 1. Read the diff for (always)
- Database: a query inside a loop (N+1), unbounded `SELECT` without `LIMIT`/pagination, a new `WHERE`/`JOIN`/`ORDER BY` column with no index, a transaction held across network calls.
- Go: allocation or `regexp.MustCompile`/`json` work inside hot loops, goroutines without a stop path (leaks), missing `context` timeouts on external calls, mutex held during I/O, reading whole files/bodies into memory.
- TypeScript/React: work inside render, effects that re-run every render, missing memo on large lists, unvirtualized long lists, new heavy imports in the main bundle.
- Python: per-row Python loops where a vectorized/batched call exists, unbounded caches.
- Everywhere: retries without backoff/limits, O(n²) over user-sized inputs, polling where an event exists.

## 2. Measure when the change is on a hot path or step 1 found something
- Go: benchmarks on the base branch and on the lane, compared: `go test -run '^$' -bench <Name> -count 10 ./<pkg> > <file>` for both, then `benchstat base.txt lane.txt`. No benchmark exists for a hot path: say so (and propose one) instead of guessing.
- SQL: `EXPLAIN (ANALYZE, BUFFERS)` of each new or changed query on the seeded fresh DB; flag sequential scans on large tables.
- Frontend: build size before/after (`npm run build`, compare output sizes); flag growth > 5% of a route's bundle.
- Test suites: duration before/after for the changed package; long suites (live/e2e) must stay well under their CI time limit.
- On a shared machine: mind the CPU budget (e.g. cap temp containers with `--cpus 2`).

## 3. Output (at most 30 lines, appended to `$RUN/<lane>.verify.md`)
`PERF: OK | REGRESSION | RISK` and `HEAD: <git rev-parse HEAD you checked>`, then each item: `file:line — pattern — measured numbers or count — smallest fix`. Then "Not verified" (what was not measured and why). A measured regression on a hot path blocks the PR report until fixed or the owner accepts it.
