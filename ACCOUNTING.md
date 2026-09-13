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
used U          = R_open−R
daily left      = 100·A/P, only when P > 0 and opening is supported
weekly days     = 6−i
bucket countdown= S+(i+1)·D/7−now
```

Unused allowance and previous overspending are already reflected in R; debt is never
subtracted a second time. All arithmetic uses `Fraction`, including future fractional
snapshots. Seven base grants total exactly 100. Every nonnegative displayed amount is
floored; the ratio is calculated **before** flooring. Bars use the displayed percentage,
bounded visually to 0–100. A small positive amount displayed as zero is not exhaustion.
Negative net changes are corrections, stored without dropping their sign. Ratios above
100 remain above 100 in the label and arithmetic; only their bar is clamped.

Plans and use are derived from minimal balance evidence, not recomputed launch baselines.
A supported opening needs a verified source observation at the exact boundary; its first
balance remains frozen. A response received after a boundary does not establish that
balance. The current app-server contract has no provider sampling timestamp: the collector
stores request-start and receipt instants, marks timing as receipt-only and leaves the
source timestamp null. Even close or identical readings straddling a boundary do not
prove where consumption occurred. Boundary refreshes preserve useful evidence without
silently converting it into an exact opening. Source rounding is a separate uncertainty.

Unknown openings mean unknown Plan, Used and daily percentage; A and R remain calculable.
The equal base plan is used only as a future forecast. Supported openings, when available,
produce 100% at opening for positive plans, including surplus or debt. For historical
full-bucket Used, both opening and closing evidence are required; a last pre-boundary
reading is not a full closing balance. Offline gaps are never assigned to later buckets.
The ledger's source-timestamp path is covered with explicitly synthetic supported-opening
fixtures; it is not claimed as a capability of the installed provider contract.

The original screenshot's late balance 88 mathematically produced Plan 116/7 and, at
balance 87, daily left 109/116 × 100 = 93% after flooring. It was a launch-time basis,
not evidence of the bucket opening. Schema migration retains that legacy row and all
snapshots for export, but excludes unsupported legacy baselines from full-bucket metrics.
No historical usage is inferred from total weekly consumption or token counts.

Whole-number snapshots do not establish the provider's rounding rule, an error bound
or exactly zero consumption between identical readings. The ledger records reported
precision separately from timing quality. Observation timestamps are local receipt
instants, not independently verified provider sampling timestamps. Repeated readings
create no synthetic consumption; used net differences telescope through corrections.
This is a pacing guide, not enforcement or a guarantee that a shorter quota window
permits immediate use. A reported exhausted shorter window gets a conditional notice.

The Monday-first calendar assigns exactly seven bucket IDs to their **start** dates.
Future P shows floored 100/7; future U is unknown. Adjacent month/year edge weeks are
included when needed. Rare duplicate civil start dates keep both IDs in that cell's
tooltip. All dates with nonempty overlap with [S,E) have a subtle connected background, and
all dates overlapping the active virtual bucket have a light-blue fill. The actual
local date has a separate dark-red outline which advances at civil midnight. Midnight
boundaries are converted separately through the local timezone, including DST; they
never define a second quota schedule. A final partial date can be highlighted without
an eighth P/U entry. An exact-midnight E does not include its new civil date.

## State and process lifetime

State lives in `${XDG_STATE_HOME:-~/.local/state}/omarchy/codex-pace/` with private
permissions: `ledger.sqlite3`, `settings.json`, a lock file and optional installation
backups. SQLite schema version 2 stores epochs, seven bucket IDs, balance snapshots and minimal
scheduling metadata transactionally. Snapshots retain account/quota through epoch identity,
bucket ID, raw balance, receipt/source/request times, precision and timing quality.
Legacy baseline columns remain archival; no redundant live plans, reserves or countdowns
are written. Exact source openings are derived from retained snapshots across restarts. It contains no credentials,
email addresses, conversation text or model preferences. Old snapshots and archived
epochs are pruned on successful refresh (90 days by default).

One native QML service serves every monitor. Its Python helper owns at most one
app-server child, uses bounded lines/timeouts, ignores unrelated notifications/reply IDs,
redacts RPC errors and closes only its own process. An advisory lock also serializes
helpers across hot reloads. EOF/SIGTERM/SIGINT cancel requests and reap the owned child.
Five-minute polling deadlines and error backoff survive ordinary reloads. Backoff doubles
up to an hour, respecting longer server retry guidance. Opening/resume refreshes stale-enough data; each virtual boundary requests one read.
Manual refresh bypasses the normal polling delay but respects server retry guidance.
Only one automatic timer runs; local countdown/age ticks do not spawn requests. Readings are marked stale at two missed intervals;
last good data retains its original timestamp. The display is recalculated each second
without extra provider requests. Quota notifications are not treated as a complete
record of other clients' activity.
