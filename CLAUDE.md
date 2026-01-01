# CLAUDE.md

## Project Overview

BlackVue Sync is a single-file Python utility that synchronizes recordings from BlackVue dashcams to a local directory over HTTP. The project emphasizes simplicity and portability with zero third-party dependencies, packaged both as a standalone script and a Docker container.

This project is on GitHub: <https://github.com/acolomba/blackvuesync>

## Claude Code

- Prefer using the LSP plugin over textual search.
- When a sandbox operation fails, stop to ask the user. Avoid disabling the sandbox.
- Create plans under the `plans/` directory.

## Development Setup

The project uses `pyproject.toml` for dependency management. Development dependencies (black, Flask, pre-commit, pytest) are defined as optional dependencies.

### Setup

Create a virtual environment and install development dependencies:

```bash
# create virtual environment
python3 -m venv venv

# activate it
source venv/bin/activate

# install package in editable mode with dev dependencies
pip install -e ".[dev]"

# install pre-commit hooks
pre-commit install

# install commit-msg hook for gitlint
pre-commit install --hook-type commit-msg
```

The `-e` flag installs in editable mode, so changes to `blackvuesync.py` take effect immediately without reinstalling.

Pre-commit hooks will automatically run on `git commit` to check code quality, format code, and scan for secrets. The hooks include Black, shellcheck, yamllint, trufflehog, and others.

## Guidelines

### Comments

Python docstrings and inline code comments in Python, YAML, shell, etc. are lowercase. The word "TODO" remains all-caps. Entities such as file names etc. preserve their casing.

Comments must be in the third-person, e.g. "installs", not "install", because they are descriptive. Avoid the imperative.

Keep comments concise, and non-obvious. Avoid documenting what everybody is expected to know.

### Python

Prefer Python idiomatic ("pythonic") style.

Always use type annotations.

### Code Formatting

Code formatting is handled automatically by pre-commit hooks (Black for Python, yamlfmt for YAML).

### Git

- Git commit messages must be longer than 5 characters, and each line must be less than 80.
- You can expect pre-commit hooks to fail when attempting to commit. Fix the errors.
- NEVER use `--no-verify` to skip the hooks.

## Architecture

### Single-File Design

The entire application is contained in `blackvuesync.py` - a self-contained script with no external dependencies. This design prioritizes portability and ease of deployment.

### Core Flow

1. **Lock acquisition**: Uses file locking (`fcntl`) to prevent concurrent runs on the same destination
2. **Destination preparation**: Creates directories, removes outdated recordings based on retention policy
3. **Dashcam communication**: HTTP requests to `blackvue_vod.cgi` endpoint to list recordings
4. **Recording parsing**: Filename-based extraction of metadata (date, type, direction)
5. **Download with resume**: Uses temporary dotfiles (`.filename.mp4`) for partial downloads
6. **Cleanup**: Removes temp files and empty grouping directories

### Recording Types

The filename regex (`filename_re`) parses BlackVue recording filenames to extract:

- **Timestamp**: `YYYYMMDD_HHMMSS`
- **Type**: N=Normal, E=Event, P=Parking, M=Manual, I=Impact, O=Overspeed, A=Acceleration, T=Cornering, B=Braking, R/X/G=Geofence, D/L/Y/F=DMS
- **Direction**: F=Front, R=Rear, I=Interior, O=Optional
- **Upload flag**: L=Live, S=Substream (optional)

Each recording consists of multiple files: `.mp4` (video), `.thm` (thumbnail), `.3gf` (accelerometer), `.gps` (GPS data).

### Grouping

Recordings can be organized into date-based directories (`--grouping`):

- `daily`: YYYY-MM-DD
- `weekly`: YYYY-MM-DD (Monday of week)
- `monthly`: YYYY-MM
- `yearly`: YYYY

Grouping speeds up loading in BlackVue Viewer and keeps directories manageable.

### Logging

Two logger hierarchies:

- `logger`: Root logger, respects verbosity and quiet flags
- `cron_logger`: Remains active in cron mode for Normal/Manual recordings and errors

## Testing

### Test Structure

- `test/blackvuesync_test.py`: Pytest-based unit tests for parsing, grouping, filtering
- `features/`: Behave-based BDD integration tests that verify end-to-end functionality with a mock BlackVue dashcam server

### Running Tests

Run all tests:

```bash
# unit tests
pytest test/blackvuesync_test.py -v

# integration tests
behave
```

## Important Constraints

### Python Version

Requires Python 3.9+ for modern type hints (`str | None`, walrus operator `:=`).

### No External Dependencies

The script deliberately uses only Python standard library. When adding features, maintain this constraint for portability.

### Backwards Compatibility

Recording filename patterns must remain compatible with existing BlackVue firmware. The filename regex is based on official BlackVue documentation.

### File Locking

Lock files are stored in the destination directory (`.blackvuesync.lock`). The destination must be on a local filesystem (not NFS) for `fcntl.lockf()` to work correctly.

## Docker-Specific Notes

The Docker image (`Dockerfile`):

- Uses Alpine Linux for minimal size
- Runs as `dashcam` user (UID/GID set via `PUID`/`PGID` env vars)
- Internal cron job runs every 15 minutes (see `crontab` file)
- `entrypoint.sh` handles user switching and cron setup
- `blackvuesync.sh` wrapper translates env vars to CLI args
