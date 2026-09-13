# Validation record

Validated locally on 2026-09-13 with Omarchy 4.0.3-1, Codex CLI 0.153.4,
Python 3.14.7 and the installed Qt 6/Quickshell runtime.

- **61 tests passed** (`python3 -B -m unittest discover -s tests -v`, 26.9 seconds).
- Installed `omarchy plugin validate .` passed.
- QML analysis passed with zero remaining warnings/errors after treating the installed
  host's dynamic-property metadata and Quickshell's missing `QProcess::ExitStatus`
  metadata as informational. The live engine loaded both QML entrypoints successfully.
- Live read-only account/rate-limit RPC succeeded using the existing CLI login.
  `codex` was explicitly selected; no model preference or credential file was edited.
- The real panel rendered the three top metrics, two independently sized draining bars,
  honest unknown opening metrics, seven P/U start-date entries, eight overlapping dates,
  two active-bucket date fills, today’s red outline and reset count.
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
  opening fixtures, including the new overlap layers at 1× and 2× scale.
  Fixtures use temporary SQLite databases and never enter personal history.
- Disabling stopped the owned helper and preserved the ledger. Re-enabling restored
  the retained history with unsupported opening values unavailable. Reload and restart checks found no duplicate collectors.
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
outline changes without changing the virtual bucket.

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

A physical second monitor was unavailable; a native virtual output was tested instead.
The desktop was not physically suspended: an isolated helper was stopped/resumed in
the integration test. Real weekly resets, early resets, DST changes and expired-login
token refresh were not forced; reset/time behavior was covered with deterministic tests
and labeled previews. The current provider contract has no verified sampling timestamp; supported exact-opening
calculations were verified using synthetic evidence, not claimed from live receipt-only
responses. No reset credit was redeemed and no model turn was run by the collector.
