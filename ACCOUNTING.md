# Accounting and data handling


The collector initializes `codex app-server` over local stdio, waits for success, sends
`initialized`, then reads `account/read` and `account/rateLimits/read`. It prefers
`rateLimitsByLimitId` and finds a window whose duration is **10080 minutes**, regardless
of whether it is named primary or secondary. It reads percentages in their original
units. Omarchy's built-in usage record is unsuitable because it normalizes percentages
and drops bucket identity and duration. No token/session files or private HTTP endpoints
are read. Reset credits use `rateLimitResetCredits.availableCount`; missing is unknown,
not zero. Monetary credit balances and individual credit-detail rows are ignored.

For reset E and verified duration D, the normal fixed window starts at S = E − D.
That inference is recorded. A supplied start must agree with the duration. Boundaries
are S + i·D/7; exact boundaries belong to the new bucket. UTC instants drive accounting;
local dates and DST only affect presentation. At E the view waits for fresh provider
data. An overlapping changed reset needs two matching independent readings before
starting a separate epoch. Changed/nonweekly durations stay unavailable. Corrections
with the same reset do not create grants. No observation is fabricated to close an old
week, and no carryover crosses an epoch, account or quota bucket.

For zero-based current bucket i, remaining R and frozen opening R_open:

```
base allocation = 100/7
reserve F       = 100·(6−i)/7
available A     = max(0, R−F)
opening plan P  = max(0, R_open−F)
observed O      = R_open−R
daily left      = 100·A/P, only when P > 0
weekly days     = 6−i
day countdown   = S+(i+1)·D/7−now
```

Unused allowance and previous overspending are already reflected in R; debt is never
subtracted a second time. All arithmetic uses `Fraction`, including future fractional
snapshots. Seven base grants total exactly 100. Every nonnegative displayed amount is
floored; the ratio is calculated **before** flooring. Bars use the displayed percentage,
bounded visually to 0–100. A small positive amount displayed as zero is not exhaustion.
Negative net changes are corrections, stored without dropping their sign. Ratios above
100 remain above 100 in the label and arithmetic; only their bar is clamped.

The immutable opening balance and baseline timestamp/quality persist, so refreshes and
restarts cannot shrink the plan to the latest balance. A mid-bucket first reading uses
“Since tracking began” for its ratio and leaves full-bucket Observed unknown. Missing
historical plans/use remain unknown. Close observations straddling a boundary (within
one poll interval on each side, capped at 120 seconds) may provide an explicitly
estimated opening using the preceding reading, without interpolation. Longer gaps are
not allocated to the later bucket. Observed values stop at the last actual observation;
past buckets are not assumed fully observed at their ending boundary. Cell details carry
quality, and the export includes actual last-observation timestamps.

Whole-number snapshots do not establish the provider's rounding rule, an error bound
or exactly zero consumption between identical readings. The ledger records reported
precision separately from timing quality. Observation timestamps are local receipt
instants, not independently verified provider sampling timestamps. Repeated readings
create no synthetic consumption; observed net differences telescope through corrections.
This is a pacing guide, not enforcement or a guarantee that a shorter quota window
permits immediate use. A reported exhausted shorter window gets a conditional notice.

The Monday-first calendar assigns exactly seven bucket IDs to their **start** dates.
Future P shows floored 100/7; future O is unknown. Adjacent month/year edge weeks are
included when needed. Rare duplicate civil start dates keep both IDs in that cell's
tooltip. The final reset date is never an eighth bucket.

## State and process lifetime

State lives in `${XDG_STATE_HOME:-~/.local/state}/omarchy/codex-pace/` with private
permissions: `ledger.sqlite3`, `settings.json`, a lock file and optional installation
backups. SQLite schema version 1 stores epochs, seven bucket records, timestamped
snapshots and minimal scheduling metadata in transactions. It contains no credentials,
email addresses, conversation text or model preferences. Old snapshots and archived
epochs are pruned on successful refresh (90 days by default).

One native QML service serves every monitor. Its Python helper owns at most one
app-server child, uses bounded lines/timeouts, ignores unrelated notifications/reply IDs,
redacts RPC errors and closes only its own process. An advisory lock also serializes
helpers across hot reloads. EOF/SIGTERM/SIGINT cancel requests and reap the owned child.
Successful polling deadlines and error backoff survive ordinary reloads. Backoff doubles
up to an hour, respecting longer server retry guidance. Clock/resume gaps trigger a
refresh when no retry delay is active. Readings are marked stale at two missed intervals;
last good data retains its original timestamp. The display is recalculated each second
without extra provider requests. Quota notifications are not treated as a complete
record of other clients' activity.
