# Contributing

## General

This project welcomes new [issues](https://github.com/acolomba/blackvuesync/issues) and [pull requests](https://github.com/acolomba/blackvuesync/pulls).

## Responsible AI contributions

The use of generative AI is welcome, provided these conditions are met:

- **Human ownership:** You as a human are responsible for the contents of your contribution.
- **Human oversight and expertise:** Please review, validate and revise issues and pull requests with your own expertise so that they reflect your personal understanding and voice.

This AI contribution policy is loosely based on the one in the [Microsoft Open Source CoC](https://opensource.microsoft.com/codeofconduct/).

## Development Setup

```bash
# clone and setup
git clone https://github.com/acolomba/blackvuesync.git
cd blackvuesync

# create virtual environment and install dependencies
python3 -m venv venv
source venv/bin/activate
pip install -e ".[dev]"

# install pre-commit hooks (runs linters, formatters, security checks)
pre-commit install
pre-commit install --hook-type commit-msg
```

Pre-commit hooks will automatically run quality checks on `git commit` and in pull requests.

## Tests

The project includes both unit tests and integration tests:

```bash
# run unit tests
pytest test/blackvuesync_test.py -v

# run integration tests
behave
```

A GitHub workflow automatically runs both unit and integration tests on all pull requests and merges to the main branch.
