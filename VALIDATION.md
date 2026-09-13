# Validation record

Version **1.2.0** validated locally on 2026-09-13 with Omarchy 4.0.3-1, Codex CLI 0.153.4,
Python 3.14.7 and the installed Qt 6/Quickshell runtime.

- **71 tests passed** (`python3 -B -m unittest discover -s tests -v`, 26.9 seconds).
- Installed `omarchy plugin validate .` passed.
- QML analysis passed with zero remaining warnings/errors after treating the installed
  host's dynamic-property metadata and Quickshell's missing `QProcess::ExitStatus`
  metadata as informational. The live engine loaded both QML entrypoints successfully.
- Live read-only account/rate-limit RPC succeeded using the existing CLI login.
  `codex` was explicitly selected; no model preference or credential file was edited.
- The real panel rendered the three top metrics, two independently sized draining bars,
  standard-plan fallback metrics, seven P/U start-date entries, eight overlapping dates,
  muted active-bucket fills, the thicker current-date outline and reset count.
  The fallback fixture showed 102%, Plan 14, Used 0* and first-bucket U 14*.
  The supported-opening fixture showed 93%, Plan 16 and Used 1 without a current
  estimate marker. Both progress bars and the full basis tooltip rendered correctly.
  Text, contrast, spacing and popup anchoring were inspected on the running desktop.
- Native pointer clicks opened, closed and reopened the icon's dropdown. An outside
  click dismissed it. Enter/Space use the refresh handler; Enter and Escape were
  exercised live. Tab focused the native Refresh button. Pointer and keyboard refreshes
  each obtained a new successful reading; the pending state was observed. IPC/keyboard
  summoning acquired focus correctly.
- A temporary second native output at 2× scale showed the same shared data with only
  one Python collector and one desktop shell. Keyboard scrolling reached the bottom
  on its shorter logical viewport. The virtual output was removed afterward.
- Clearly labeled synthetic previews were inspected for ordinary carryover, debt/zero
  allowance, correction above 100%, stale data, expired reset and unavailable login in
  the initial release. This revision additionally inspected the screenshot and unknown
  opening fixtures in 1.1.0 at 1× and 2× scale. Version 1.2.0 rechecked fallback and
  supported-opening fixtures at 1×, including the restrained estimate legend.
  Fixtures use temporary SQLite databases and never enter personal history.
- Disabling stopped the owned helper and preserved the ledger. Re-enabling restored
  retained source history. Unsupported openings now use the standard-plan fallback.
  Reload and restart checks found no duplicate collectors; five-minute settings and
  the complete bar layout were unchanged by this revision.
- The pre-install `shell.json` backup was compared structurally with the final config
  after removing only the new plugin entry: all unrelated values and widget order matched.
- No screenshots, local settings, personal quota history, database or credentials are
  included in the repository.

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
and epoch/account isolation of provisional estimates.

## Reproduce QML analysis

Quickshell supplies the `qs` import namespace dynamically. For standalone qmllint:

```bash
pace_lint_dir=$(mktemp -d)
ln -s "$OMARCHY_PATH/shell" "$pace_lint_dir/qs"
/usr/lib/qt6/bin/qmllint -I "$pace_lint_dir" \
  --missing-property info --signal-handler-parameters info -W 0 Widget.qml Service.qml
rm "$pace_lint_dir/qs"
rmdir "$pace_lint_dir"
```

These informational categories reflect incomplete static metadata for runtime-provided
Omarchy/Quickshell objects; runtime rendering and shell logs were checked as well.
The installed host sometimes caches changed QML through a plugin rescan, so a supported
`omarchy restart shell` was used to apply final QML changes.

## Live-test limits

A physical second monitor was unavailable; a native virtual output was tested in 1.1.0.
The unchanged shared-service architecture was checked for one collector in 1.2.0.
The desktop was not physically suspended: an isolated helper was stopped/resumed in
the integration test. Real weekly resets, early resets, DST changes and expired-login
token refresh were not forced; reset/time behavior was covered with deterministic tests
and labeled previews. The current provider contract has no verified sampling timestamp; supported exact-opening
calculations were verified using synthetic evidence, not claimed from live receipt-only
responses. No reset credit was redeemed and no model turn was run by the collector.
