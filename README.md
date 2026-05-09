# DevCleaner

DevCleaner is a Windows-focused desktop application for finding and safely deleting large
development cleanup folders, especially Python `.venv` folders and web `node_modules`
directories.

It is built with Python, PySide6, and `uv`. The app scans a selected root folder, shows every
detected cleanup folder with useful metadata, and requires explicit confirmation before anything is
permanently deleted.

## What DevCleaner Does

Development workspaces often accumulate heavy dependency folders across many projects. Python
virtual environments and Node dependency folders can quietly consume many gigabytes of disk space.

DevCleaner helps you:

- Scan a workspace or parent folder recursively.
- Find `.venv` and `node_modules` directories.
- Review size, path, project name, modified date, and item counts.
- Delete only the folders you explicitly confirm.
- Track reclaimed space during the current session.

DevCleaner is intentionally conservative. It only deletes supported cleanup folder names inside the
selected root folder.

## Features

### Scanning

- Select any root folder and scan recursively.
- Scan for `.venv`, `node_modules`, or both.
- Cancel long-running scans.
- Background scan worker keeps the UI responsive.
- Configure hidden folder scanning, excluded folder names, and maximum scan depth.

### Dashboard

- Professional Windows-style dashboard.
- Shows detected cleanup folder count.
- Shows total cleanup footprint.
- Shows reclaimed space for the current session.
- Shows scanned folder count, scan summary, background worker status, and recent folders.

### Results

- Each cleanup folder appears as a separate result card.
- Result cards include:
  - Project name
  - Cleanup target type
  - Full cleanup folder path
  - Size
  - Last modified date
  - File and folder count
- Search by project name, path, or target type.
- Filter by target type.
- Sort by size, name, or modified date.
- Open the project folder in File Explorer.
- Reveal the cleanup folder in File Explorer.

### Safe Deletion

- Delete one folder at a time.
- Select multiple visible results and delete them together.
- Delete all visible filtered results.
- Permanent deletion always requires a review dialog.
- The review dialog shows target count, total size, target breakdown, and exact paths.
- Deletion runs in a background worker so the app remains responsive.
- Session deletion log shows successful deletions, failures, reclaimed space, and failure messages.

### Export

- Export visible results to JSON.
- Export visible results to CSV.
- Use exports for audits, cleanup reports, or manual review before deletion.

### Keyboard And Productivity

- `F11` fullscreen support.
- `Ctrl+K` command palette.
- Keyboard shortcuts for navigation, scanning, searching, selecting, deleting, and exporting.
- Optional shortcut hints in tooltips.
- Smooth UI transitions and count-up animations, with an option to disable animations.

## Requirements

- Windows 10 or Windows 11
- Python `3.11` or newer
- `uv`
- Git

DevCleaner installs its Python dependencies through `uv`. You do not need to install PySide6
manually.

## Download And Run

Open PowerShell and run:

```powershell
git clone https://github.com/suraj-yadav-aiml/DevCleaner.git
cd DevCleaner
uv sync
uv run devcleaner
```

## Alternative Development Run Command

The public app command is:

```powershell
uv run devcleaner
```

The internal Python package is still named `venvhunter`, so developers can also run:

```powershell
uv run python -m venvhunter
```

## How To Use DevCleaner

### 1. Open The App

Start DevCleaner from the project folder:

```powershell
uv run devcleaner
```

The app opens on the dashboard.

### 2. Choose A Root Folder

Click **Choose folder** or press `Ctrl+O`.

Pick a parent folder that contains your projects. For example:

```text
D:\Projects
D:\Learning
C:\Users\<you>\source\repos
```

DevCleaner scans inside the selected root folder only.

### 3. Select Scan Targets

On the dashboard, choose whether to scan for:

- `.venv`
- `node_modules`

You can enable one or both targets.

### 4. Start A Scan

Click **Start scan**, press `Ctrl+R`, or press `F5`.

The scan runs in the background. You can continue using the UI while scanning. Use **Cancel** if you
need to stop a long scan.

### 5. Review The Dashboard

After scanning, the dashboard shows:

- Number of detected cleanup folders
- Total disk footprint
- Reclaimed space this session
- Number of scanned folders
- Scan duration and warnings
- Largest detected cleanup folder
- Recent scanned folders

### 6. Review Scan Results

Open **Scan Results** from the sidebar or press `Ctrl+2`.

Use the results page to:

- Search by project or path.
- Filter by cleanup target.
- Sort results by size, name, or modified date.
- Select visible results.
- Export visible results.
- Open or reveal folders in File Explorer.

### 7. Delete Safely

You can delete cleanup folders in three ways:

- Use **Delete** on a single result card.
- Select results and use **Delete selected**.
- Use **Delete visible** to delete all currently visible filtered results.

Before deletion, DevCleaner shows a review dialog with the exact paths that will be permanently
deleted. Nothing is deleted unless you confirm.

### 8. Review The Deletion Log

Click **Deletion log** after deletion attempts.

The log shows:

- Removed folders
- Failed deletions
- Reclaimed disk space
- Error messages for permission or locked-file failures

## Keyboard Shortcuts

| Shortcut | Action |
| --- | --- |
| `F11` | Toggle fullscreen |
| `Esc` | Close the command palette or exit fullscreen |
| `Ctrl+K` | Open the command palette |
| `Ctrl+O` | Choose root folder |
| `Ctrl+R` | Start scan or rescan current root |
| `F5` | Start scan or rescan current root |
| `Ctrl+1` | Open Dashboard |
| `Ctrl+2` | Open Scan Results |
| `Ctrl+3` | Open Settings |
| `Ctrl+F` | Focus result search |
| `Ctrl+A` | Select visible results when the results page is active |
| `Delete` | Delete selected results after review confirmation |
| `Ctrl+E` | Export visible results as CSV |
| `Ctrl+?` | Show keyboard shortcuts |
| `Ctrl+/` | Show keyboard shortcuts |

You can also press `Ctrl+K` and search for commands by name.

## Safety Model

DevCleaner is designed around safe deletion workflows.

- Deletion is permanent.
- Deletion always requires explicit user confirmation.
- Only supported cleanup folder names are eligible:
  - `.venv`
  - `node_modules`
- Deletion is limited to folders inside the selected root directory.
- The selected root folder itself cannot be deleted.
- Symlink and reparse-point cleanup roots are refused.
- Permission errors and locked files are handled gracefully.
- Failed deletions are reported in the UI and recorded in the session deletion log.

Use the export feature if you want to review scan results before deleting anything.

## Settings

The Settings page includes:

- Theme mode: system, light, or dark.
- Show hidden folders while scanning.
- Excluded folder names.
- Maximum scan depth.
- Refresh result cards after deletion.
- Enable or disable UI animations.
- Show or hide keyboard shortcut hints.

Deletion confirmation is always required and cannot be disabled.

## Troubleshooting

### `uv` Is Not Installed

Install `uv` from the official documentation, then restart PowerShell and try again:

```powershell
uv --version
```

### Python Version Is Too Old

DevCleaner requires Python `3.11` or newer.

Check your Python version:

```powershell
python --version
```

If needed, install a newer Python version and run:

```powershell
uv python install 3.12
uv sync
```

### The App Does Not Open

From the project folder, reinstall dependencies and run again:

```powershell
uv sync
uv run devcleaner
```

If PowerShell shows an error, read the final error lines. They usually indicate a missing Python
version, missing dependency, or environment issue.

### No Cleanup Folders Are Found

Check that:

- You selected the correct root folder.
- The selected target is enabled.
- The folders are actually named `.venv` or `node_modules`.
- Hidden folder scanning is enabled if the folders are hidden.
- Maximum scan depth is not too restrictive.
- The folder name is not listed in excluded folders.

### Deletion Fails

A deletion can fail if:

- Files are open in an editor, terminal, or running process.
- Permission is denied.
- Antivirus or indexing software is using files.
- The folder is locked by another process.

Close related applications and try again. If needed, restart Windows and rerun the scan.

## Project Structure

```text
.
|-- pyproject.toml
|-- README.md
|-- src/
|   `-- venvhunter/
|       |-- __main__.py
|       |-- app.py
|       |-- models.py
|       |-- settings.py
|       |-- services/
|       |   |-- deletion.py
|       |   |-- exporter.py
|       |   `-- scanner.py
|       |-- ui/
|       |   |-- animations.py
|       |   |-- main_window.py
|       |   |-- theme.py
|       |   |-- widgets.py
|       |   `-- workers.py
|       `-- utils/
|           |-- formatting.py
|           `-- platform.py
`-- tests/
    |-- test_deletion.py
    |-- test_scanner.py
    `-- test_ui.py
```

## Architecture

DevCleaner separates filesystem logic from UI behavior.

- `services`: scanning, deletion, and export logic. These modules do not depend on Qt.
- `ui`: PySide6 windows, widgets, dialogs, animations, and worker integration.
- `ui.workers`: background `QThread` workers for scan and deletion operations.
- `models`: typed data objects for cleanup targets, scan results, and deletion results.
- `settings`: persisted app settings and recent folders.
- `utils`: formatting and Windows platform helpers.

The scanner uses `os.scandir` with an explicit stack for efficient traversal and precise control
over hidden folders, excludes, symlinks, reparse points, and scan depth.

Scanning and deletion are asynchronous from the user's perspective. Long filesystem operations run
on dedicated Qt worker threads and send progress back to the main UI thread through signals.

## Development

Install dependencies:

```powershell
uv sync
```

Run the app:

```powershell
uv run devcleaner
```

Run tests:

```powershell
uv run pytest
```

Run lint checks:

```powershell
uv run ruff check .
```

## Roadmap

Possible future improvements:

- Signed Windows installer.
- Optional recoverable deletion through the Windows Recycle Bin.
- Dry-run cleanup reports.
- Saved scan presets.
- Scheduled scan reminders.
- Richer metadata from `pyvenv.cfg`, `package.json`, and lock files.
- More export formats.
