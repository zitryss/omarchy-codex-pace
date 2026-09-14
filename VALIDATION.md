# Validation record

Version **1.3.0** validated locally on 2026-09-14 with Omarchy 4.0.3-1, Codex CLI 0.153.4,
Python 3.14.7 and the installed Qt 6/Quickshell runtime.

- **76 tests passed** (`python3 -B -m unittest discover -s tests -v`, 26.9 seconds).
- Installed `omarchy plugin validate .` passed.
- QML analysis passed with zero remaining warnings/errors after treating the installed
  host's dynamic-property metadata and Quickshell's missing `QProcess::ExitStatus`
  metadata as informational. The live engine loaded both QML entrypoints successfully.
- Live read-only account/rate-limit RPC succeeded using the existing CLI login.
  `codex` was explicitly selected; no model preference or credential file was edited.
- The normal panel renders four reusable metric rows: daily quota, bucket countdown,
  weekly quota and actual weekly countdown. Both clocks use independent elapsed-time fills.
  Plan/Used, calendar overlap, estimate markers, reset credits and refresh remain compact.
- Normal panel content and viewport both measured 645 logical pixels: scrolling disabled.
  Native wheel input caused no movement. Long-error fixtures enable scrolling when needed.
- Live previews covered normal, above-100%, zero plan, zero quota, missing data, stale,
  expired, exact boundary and near-reset states. Unknown rows use dashes and null fills.
  Boundary clocks showed 24h and full gray; near-reset clocks had tiny green fills.
- Native QML palette probes checked both light and dark surfaces at fractions 0, .25,
  .5, .75 and 1. Quota endpoints were red/green, clock endpoints green/gray; each tested
  fill had contrast above 3:1 against its surface. The user's desktop theme was preserved.
- A temporary 2× native output provided a 472-pixel logical viewport. All four rows fit
  horizontally, scrolling reached the rest, and Tab focused the refresh control at the
  bottom even in a long-error state. Both outputs shared one projection and collector.
  The temporary output was removed. Normal-state wheel and keyboard behavior was retained.
- Settings and bar layout were compared with the pre-update backup and preserved. The
  SQLite schema, account selection, source history and five-minute polling are unchanged.
- A fresh live screenshot was published through a completed GitHub issue and embedded
  by its direct image URL in the user-focused README.
- No local settings, quota database or credentials are included in the repository.
  The README screenshot was explicitly authorized for publication.

## Automated coverage

Exact 100/7 conservation; every half-open bucket boundary; start/internal/expiry clock
values; 24h/1h/1m/subminute displays; integer/fractional snapshots; flooring and ratios
before flooring; carryover/debt; zero/unknown openings; repeated readings and net
corrections; negative correction display; no synthetic gap consumption; persisted plans;
uncertain boundary observations; stale/out-of-order readings; offline expiry; confirmed early
resets; distinct accounts and buckets; retention and schema versions; seven calendar IDs;
month/year/DST changes and duplicate civil dates; independent bar projections;
missing/zero/count-only reset credits; invalid RPC data, timeouts, child exit and large
output; interleaved notifications/reply IDs; redacted errors; owned-process cleanup;
lock/reload deduplication; preserved server retry guidance; simulated resume gaps; five-minute polling/default migration; immediate deduplicated
manual refresh; boundary-triggered collection; failures preserving successful timestamps;
eight touched dates with seven IDs; active buckets spanning two cells; and civil-midnight
outline changes without changing the virtual bucket; exact 102/130/60 fallback ratios;
above-100% visual clamping; supported-opening precedence; standard-basis persistence;
nonmutation of stored evidence; equal residual allocation with fractional conservation;
negative/inconsistent usage diagnostics; no future allocation; estimated corrections;
epoch/account isolation of provisional estimates; independent countdown fractions; weekly
duration formatting; and null countdown fields for missing/unverified/expired windows.

## Reproduce QML analysis

Quickshell supplies the `qs` import namespace dynamically. For standalone qmllint:

```bash
pace_lint_dir=$(mktemp -d)
ln -s "$OMARCHY_PATH/shell" "$pace_lint_dir/qs"
/usr/lib/qt6/bin/qmllint -I "$pace_lint_dir" \
  --missing-property info --signal-handler-parameters info -W 0 Widget.qml Service.qml MetricRow.qml
rm "$pace_lint_dir/qs"
rmdir "$pace_lint_dir"
```

These informational categories reflect incomplete static metadata for runtime-provided
Omarchy/Quickshell objects; runtime rendering and shell logs were checked as well.
The installed host sometimes caches changed QML through a plugin rescan, so a supported
`omarchy restart shell` was used to apply final QML changes.

## Live-test limits

A physical second monitor was unavailable; a temporary native virtual output was tested.
Actual OS suspend, real reset events and timezone changes were not forced. Deterministic
tests cover their accounting/time behavior. The current desktop theme was inspected live;
light/dark palette colors were checked in native QML instances without switching the theme.
The current provider has no verified sampling timestamp; exact-opening calculations use
explicitly synthetic evidence in tests. No reset credit was redeemed and the collector
ran no model turns.
