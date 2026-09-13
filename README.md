# Codex Pace

A native Omarchy bar icon and dropdown for pacing an existing Codex subscription.
One actual provider week, seven equal elapsed-time days, and a small local ledger.
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
python3 -B ~/.config/omarchy/plugins/c3po.codex-pace/pace.py configure --interval 60 --retention 90
python3 -B ~/.config/omarchy/plugins/c3po.codex-pace/pace.py status
omarchy-shell shell summon c3po.codex-pace
```

Refresh interval: 30–3600 seconds. Retention: 7–365 days. Defaults: 60 seconds / 90 days.
Panel opening and Enter, Space or R request a refresh only when the reading is old
enough; requests are deduplicated and cannot bypass an active retry delay. Escape closes,
Up/Down or J/K scroll on short screens, and Tab switches to a neighboring native panel.
The icon accepts mouse clicks and keyboard activation. No keybinding is installed.
Hover a calendar cell for its exact local range and baseline quality; hover the update
status for the weekly deadline, correction and over-plan details.

## Accounting and local data

Seven exact 100/7 grants follow the provider's actual 168-hour window. Carryover/debt
is reflected once in the frozen opening plan. All displayed amounts are floored after
exact rational calculation. Mid-bucket first runs are marked “Since tracking began”;
unknown observations stay unknown. Corrections are preserved, and expired weeks wait
for a fresh reading. The calendar contains exactly seven bucket start-date entries.
See [ACCOUNTING.md](ACCOUNTING.md) for formulas, timing/precision quality, reset handling
and collector design. This is a pacing guide, not enforcement or a promise that a
shorter quota window permits use.

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

Available fixtures: `normal`, `debt`, `zero`, `correction`, `stale`, `expired`, `auth`,
`year`, `dst`. `tests/preview.py NAME` also emits their JSON without opening a window.
See [VALIDATION.md](VALIDATION.md) for recorded checks and live-test limits.

References: [Omarchy native shell](https://github.com/basecamp/omarchy/blob/quattro/shell/README.md),
[Codex app-server](https://learn.chatgpt.com/docs/app-server),
[Codex authentication](https://learn.chatgpt.com/docs/auth).
The installed Omarchy source and generated Codex schema take precedence over these references.
