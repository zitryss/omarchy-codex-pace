# Codex Pace

A native Omarchy bar icon and dropdown for pacing an existing Codex subscription.
One actual provider week, seven equal elapsed-time planning buckets, and a small local ledger.
Python standard library + QML; no model calls, API key, token copies or credit redemption.

## Install

Requires Omarchy Quattro's native plugin system (`omarchy plugin`), Quickshell,
Python 3.11+, and a signed-in Codex CLI on the desktop session's PATH. Tested with
Omarchy **4.0.3-1**, Codex CLI **0.153.4** and Python **3.14** on Linux.
Older Omarchy versions without native plugins are unsupported; no OS upgrade is performed.
The shell's inherited PATH, CODEX_HOME and Codex credential store are respected.
If the CLI is not signed in, use the normal `codex login` with your subscription.

```bash
mkdir -p "${XDG_STATE_HOME:-$HOME/.local/state}/omarchy/codex-pace/backups"
cp -p ~/.config/omarchy/shell.json \
  "${XDG_STATE_HOME:-$HOME/.local/state}/omarchy/codex-pace/backups/shell.before-install.json"
omarchy plugin add https://github.com/zitryss/omarchy-codex-pace --yes
python3 -B ~/.config/omarchy/plugins/c3po.codex-pace/pace.py configure --bucket codex
omarchy plugin enable c3po.codex-pace --after omarchy.agents
```

The existing agents widget stays in place. To use the default right-hand placement,
omit `--after omarchy.agents`. The manifest ID `c3po.codex-pace` is a user namespace;
it does not depend on your Linux username. The installed folder is also a git checkout.
Update with `omarchy plugin update c3po.codex-pace --yes`.

`codex` is the general quota bucket selected for this installation. Other returned
buckets are never added together or chosen from model preferences. Multiple weekly
buckets require an explicit selection; one unambiguous weekly bucket may self-select.
Selections persist in local settings. If a selected bucket disappears, the view reports
it as unavailable. The backend account ID is required and stored only as a SHA-256 digest.
Each account/bucket/week has its own records.

```bash
python3 -B ~/.config/omarchy/plugins/c3po.codex-pace/pace.py configure --interval 300 --retention 90
python3 -B ~/.config/omarchy/plugins/c3po.codex-pace/pace.py status
omarchy-shell shell summon c3po.codex-pace
```

Refresh interval: 30–3600 seconds. Retention: 7–365 days. Defaults: **300 seconds / 90 days**.
The original unmarked 60-second saved default migrates to 300; identifiable custom
intervals are retained. `configure --interval 60` explicitly keeps a one-minute choice.
Panel opening/resume refreshes an old reading; virtual boundaries request one refresh.
The footer's two-arrow **Refresh** button, Enter, Space or R requests an immediate read.
Requests are deduplicated, including across monitors, and respect server retry guidance.
The button dims while pending. Failures retain the successful reading's original age.
Escape closes; Up/Down or J/K scroll. Tab focuses Refresh, then switches native panels.
The icon accepts mouse clicks and keyboard activation. No keybinding is installed.
Hover a calendar cell for overlapping bucket ranges and opening evidence; hover the
update status for the weekly deadline, correction and over-plan details.

## Accounting and local data

Seven exact 100/7 allocations follow the provider's actual 168-hour window. Surplus/debt
is reflected once in the frozen opening plan. All displayed amounts are floored after
exact rational calculation. With no supported opening balance, the **standard-plan
fallback** uses Plan 100/7, daily percentage `100 × available / (100/7)`, and Used
`max(0, 100/7 − available)`. The label may exceed 100%; only the bar is capped.
For bucket two at 86% weekly remaining: Available 14%, Plan 14, daily left 102%,
Used 0*. The full-precision available amount is 102/7, not exactly 14.

An asterisk and **“* estimated”** legend identify provisional Used values. Current Used
is a pacing shortfall, not reconstructed consumption. Completed buckets with missing
usage may share residual reported weekly usage equally after subtracting supported
full-bucket usage and current Used. Contradictions stay unresolved with diagnostic
details; future Used remains unknown. Estimates never enter stored source history.
Supported opening data takes precedence and freezes the actual opening plan, including
surplus/debt. Merely collecting more mid-bucket readings cannot establish that opening.
Hover the daily allowance or Plan/Used line for the basis and estimate explanation.

The calendar highlights every date overlapping the provider week; an active bucket has
a muted blue fill, and the actual local date has a dark-red outline. Seven P/U entries
remain attached once to bucket start dates. A midday reset normally touches eight dates;
an exact-midnight endpoint excludes the new date. Missing P defaults to the base 14 for past, current and future entries;
supported historical plans take precedence. See [ACCOUNTING.md](ACCOUNTING.md) for evidence semantics.
This is a pacing guide, not enforcement or a promise that a shorter limit permits use.

Private local state is under `${XDG_STATE_HOME:-~/.local/state}/omarchy/codex-pace/`.
The SQLite ledger has a versioned transactional schema, 90-day default retention and
separate accounts/buckets/epochs. It stores no credentials, conversation text or model
preferences. No local history, settings or authentication data belongs in git.

```bash
# Local export: contains your personal quota history; do not commit it.
python3 -B ~/.config/omarchy/plugins/c3po.codex-pace/pace.py export > codex-pace-history.json

# Disable (retains history and source).
omarchy plugin disable c3po.codex-pace

# Uninstall source (retains history/settings/backups).
omarchy plugin remove c3po.codex-pace --yes

# Optional explicit history deletion, only if desired, after disabling:
rm -f "${XDG_STATE_HOME:-$HOME/.local/state}/omarchy/codex-pace/ledger.sqlite3"
```

To roll back the initial bar change, disabling the plugin removes its entry without
resetting unrelated settings. For an exact saved-layout restore, **only if no later
layout changes should be retained**, copy the saved backup over `shell.json`:

```bash
cp -p "${XDG_STATE_HOME:-$HOME/.local/state}/omarchy/codex-pace/backups/shell.before-install.json" \
  ~/.config/omarchy/shell.json
```

QML edits normally hot-reload. The tested 4.0.3 host sometimes retains compiled QML
components after rescanning; `omarchy restart shell` applies those edits. This restarts
the existing desktop shell rather than launching a second shell. Python changes apply
on the next helper start. Configuration and ledger data remain outside the repository.

## Development and validation

```bash
python3 -B -m unittest discover -s tests -v
omarchy plugin validate .
```

`pace/engine.py` is pure accounting/calendar logic; `provider.py` owns RPC/validation;
`store.py` owns SQLite; `view.py` formats the projection; `pace.py` schedules collection.
`Service.qml` bridges that projection to the themed native `Widget.qml`.
The test suite covers arithmetic, boundaries, gaps, corrections, persistence, resets,
account separation, month/year/DST transitions, formatting, independent progress bars,
RPC/process failures, restart deduplication and persisted retry guidance. Synthetic RPC
servers use an isolated PATH/XDG directory and never access your account.

For a deliberate **60-second TEST FIXTURE** preview in the existing shell, substitute
your output name from `hyprctl monitors` below. These fixtures use temporary databases,
never write the live ledger, and restore the live view automatically:

```bash
omarchy-shell c3po.codex-pace.HDMI-A-1 preview correction
omarchy-shell shell summon c3po.codex-pace
omarchy-shell c3po.codex-pace.HDMI-A-1 clearPreview
```

Available fixtures: `normal`, `unknown`, `fallback`, `screenshot`, `debt`, `zero`, `correction`, `stale`, `expired`, `auth`,
`year`, `dst`. `tests/preview.py NAME` also emits their JSON without opening a window.
See [VALIDATION.md](VALIDATION.md) for recorded checks and live-test limits.

References: [Omarchy native shell](https://github.com/basecamp/omarchy/blob/quattro/shell/README.md),
[Codex app-server](https://learn.chatgpt.com/docs/app-server),
[Codex authentication](https://learn.chatgpt.com/docs/auth).
The installed Omarchy source and generated Codex schema take precedence over these references.

## Revision rollback

Version **1.2.0** retains the schema-2 ledger, settings and source observations unchanged.
To return to 1.1.0 without discarding history (from a clean plugin checkout):

```bash
omarchy plugin disable c3po.codex-pace
git -C ~/.config/omarchy/plugins/c3po.codex-pace switch --detach d8ae7b1c4c3c02bdcc33ab5c1b257ad2b3a8cd8f
omarchy plugin enable c3po.codex-pace --after omarchy.agents
omarchy restart shell
```

To return to the published revision, disable, `git switch main` in that checkout, then
re-enable and restart as above. Neither rollback nor ordinary uninstall erases history.
