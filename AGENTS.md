# blackvuesync

Synchronize recordings from BlackVue dashcams to a local directory

This project is on GitHub: <https://github.com/acolomba/blackvuesync>

## Guidelines

### General

Before editing any file, read it first. Before modifying a function, trace its callers. Research before you edit.

Prefer using the LSP plugin over textual search.

Create plans under the `docs/plans/` directory.

### Setup

Run `./scripts/init.sh` once in a fresh clone or worktree. It creates the `venv/` virtual environment with the development dependencies. Activate it with `source venv/bin/activate` before running the tools; Claude Code sessions activate it on start.

### Git

- NEVER commit to the main branch.
- Branch names: `main`, `features/*`, `releases/*`. New feature branches use `features/<name>`.
- Git commit messages and PR titles: Follow the [Conventional Commits specification](https://www.conventionalcommits.org/en/v1.0.0/#specification). Titles must be at least 5 characters and no more than 72 characters. Body lines must be no more than 80 characters.
- Run `pre-commit run --all-files` (or `pre-commit run --files <changed files>`) **before** attempting `git commit`. Fix any failures, restage, and re-run until clean. Do not commit and recover from hook failures after the fact -- a failed pre-commit hook means the commit did NOT happen, so iterating with `--amend` is wrong (it would alter the previous commit).
- NEVER use `--no-verify` to skip the hooks.
- NEVER rebase, never rewrite history. Update branches by merging.
- When committing from inside a worktree, prefix the commit with `SKIP=trufflehog`: the hook's git-mode scan cannot read a linked worktree's `.git` file. Confirm the change is clean first with a filesystem scan of the changed paths, `trufflehog filesystem <paths> --results=verified,unknown --fail`, using the binary under `~/.cache/pre-commit`.
- When writing PR descriptions, use the `simple-english` skill in Plain mode and the `humanizer` skill, if available.
- Always use `--squash` when merging PRs (`gh pr merge --squash`). The repository does not allow merge commits or rebase merges.

### Python

Rules for Python live under `skills/` and are not registered with any runtime; read the ones that apply before editing (skip any your prompt already carries under `<agent_skills>`):

- `skills/python-google-style-review/SKILL.md` and `skills/python-comments/SKILL.md` for every `.py` file
- `skills/python-unit-testing/SKILL.md` (write) and `skills/python-unit-testing-review/SKILL.md` (check) for `test/**/*.py`
- `skills/behave-behavioral-testing/SKILL.md` for `features/**`

Always use type annotations. Prefer idiomatic ("pythonic") code.

### Comments

Docstrings and inline code comments in Python, YAML, shell, etc. are lowercase. The word "TODO" remains all-caps. Entities such as file names etc. preserve their casing.

Comments must be in the third-person, e.g. "installs", not "install", because they are descriptive. Avoid the imperative.

Keep comments concise, and non-obvious. Avoid documenting what everybody is expected to know.

### Code formatting

The pre-commit hooks format code: Black and Ruff for Python, yamlfmt for YAML, and mdformat for Markdown.

### Testing

- `test/`: pytest unit tests, one test module per source module
- `features/`: behave behavioral tests

```bash
scripts/check.sh                                   # the merge gate CI runs
venv/bin/pytest test/blackvuesync_test.py                         # one test module
scripts/coverage-direct.sh blackvuesync.py test/blackvuesync_test.py   # one pair, at the 71% floor
venv/bin/behave                                     # behavioral tests
```

### Versioning

Before creating a PR, offer to bump the version in `blackvuesync.py` and `sonar-project.properties`. Concisely record changes in `CHANGELOG.md`.

## Project architecture

- Keep the application self-contained in `blackvuesync.py` with zero runtime third-party dependencies.
- Preserve Python 3.9 support and BlackVue filename compatibility.
- Package metadata reads the version from `blackvuesync.__version__`.
- Keep the Alpine Docker image, cron entrypoint, environment options, and user switching.
- Test both V1.009+ and legacy camera protocols; Docker tests run in `docker-build.yml`.
- Use `venv/bin/python`, `venv/bin/pip`, `venv/bin/pytest`, and `venv/bin/behave` directly; shell activation does not persist between tool calls.

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
