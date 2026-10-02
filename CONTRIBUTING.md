# Contributing

## General

This project welcomes [issues](https://github.com/acolomba/blackvuesync/issues) and [pull requests](https://github.com/acolomba/blackvuesync/pulls).

## Responsible AI contributions

The use of generative AI is welcome, provided these conditions are met:

- **Human ownership:** You as a human are responsible for the contents of your contribution.
- **Human oversight and expertise:** Please review, validate, and revise issues and pull requests with your own expertise so they reflect your personal understanding and voice.

This AI contribution policy is loosely based on the one in the [Microsoft Open Source CoC](https://opensource.microsoft.com/codeofconduct/).

## Development setup

Prerequisites:

- [Python](https://www.python.org/) 3.10 or newer for development tools. The application supports Python 3.9, which CI tests.
- [Node.js](https://nodejs.org/) with npm, for the agent tooling

Run this command to set up development tools and dependencies in a fresh clone or worktree.

```bash
./scripts/init.sh
```

It creates the `venv/` virtual environment with the development dependencies, installs the [pre-commit](https://pre-commit.com/) hooks, and fetches the third-party agent skills (`humanizer`, `simple-english`).

Activate the virtual environment before running the tools.

```bash
source venv/bin/activate
```

The hooks run the linters, the formatters, the type checks, and a secret scan before each commit, and they check the commit message against the Conventional Commits rules. Do not use `--no-verify` to skip them. A hook that fails stops the commit, so fix the report, stage the fix, and commit again.

## Checks

```bash
scripts/check.sh              # test pairing gate, unit tests at the 71% coverage floor, behave
pre-commit run --all-files    # linters, formatters, type checks, secret scan
```

`scripts/check.sh` and the pre-commit hooks are the merge gate CI runs on every pull request.

## Tests

The single application module `blackvuesync.py` pairs with `test/blackvuesync_test.py`. Behavioral tests live under `features/`.

```bash
pytest                                                   # unit tests
scripts/coverage-direct.sh blackvuesync.py test/blackvuesync_test.py   # one pair, at the 71% floor
./coverage.sh                                            # HTML coverage report
behave                                                   # behavioral tests
```

The merge gate runs behavioral tests against both the current and legacy camera protocols. Run `venv/bin/behave -D legacy_api=true` to test the legacy protocol alone. The Docker workflow also runs both protocols against the container image.

## Blueprint maintenance

This project adopts `acolomba/blueprint-python`; `.copier-answers.yml` records the revision and options. Claude Code, Codex, and Pi are enabled. GSD and CodeGraph are disabled.

Use `uvx --with copier-template-extensions copier update --trust --skip-tasks` on a clean feature branch for future updates. Review the merge carefully: this project keeps its single-file layout, dynamic version, Docker runtime, camera-protocol tests, and existing dependency versions.

The `publish.yml` workflow publishes tested and scanned artifacts, verifies the tag against `blackvuesync.__version__`, and creates a GitHub release. Configure the PyPI trusted publisher for `acolomba/blackvuesync`, workflow `publish.yml`, environment `pypi` before the next release.
