# Plan: Publish to PyPI with uv Support

## Goal

enable users to run blackvuesync directly with `uvx` after publishing to PyPI, with automated publication from GitHub Actions workflow on main branch

## Step 1: Prepare pyproject.toml for PyPI Publication

### Tasks

- add console script entry point in `pyproject.toml` (`[project.scripts]`)
- add PyPI classifiers (development status, license, python versions, etc.)
- verify version is set appropriately for initial PyPI release (currently "2.0a")
- verify build system requirements are correct

### Success Criteria

- `pyproject.toml` has `[project.scripts]` section with `blackvuesync` entry point
- all standard PyPI metadata fields are populated with proper classifiers
- package can be built locally with `python -m build` or `uv build`

## Step 2: Refactor GitHub Workflow for CI/CD

### Tasks

- rename `.github/workflows/test.yml` to `.github/workflows/ci.yml`
- update workflow name to "CI"
- add new `publish` job that:
  - runs only on main branch after tests pass
  - builds the package using `uv build`
  - publishes to PyPI using `pypa/gh-action-pypi-publish@release/v1`
  - requires both unit and integration tests to pass first
- add conditional logic to skip publish on pull requests

### Success Criteria

- workflow renamed and updated
- publish job configured with proper dependencies and conditionals
- workflow only publishes when tests pass on main branch
- uses trusted publishing (no API token needed in secrets)

## Step 3: Configure PyPI Trusted Publishing

### Tasks

- visit PyPI and configure trusted publishing for the repository
- add GitHub Actions as trusted publisher for `acolomba/blackvuesync`
- configure workflow name (`ci.yml`) and job name (`publish`)
- verify no API token is needed (using OIDC instead)

### Success Criteria

- PyPI trusted publishing is configured
- GitHub Actions can publish without manual token management
- security is improved by using OIDC instead of long-lived tokens

## Step 4: Test Local Build and Installation

### Tasks

- build the package locally (`uv build` or `python -m build`)
- test installation in clean environment with `uv pip install dist/blackvuesync-*.whl`
- verify the `blackvuesync` command works with `--help`
- verify zero runtime dependencies are actually needed
- test `uvx` with local wheel file if possible

### Success Criteria

- package builds without errors
- installed command runs successfully
- no unexpected dependencies are pulled in
- `blackvuesync --help` shows proper usage

## Step 5: Test with TestPyPI (Optional)

### Tasks

- optionally configure TestPyPI trusted publishing
- create a test workflow or manually publish to TestPyPI first
- test installation from TestPyPI: `uvx --index-url https://test.pypi.org/simple/ blackvuesync --help`
- verify full functionality with real-world test

### Success Criteria

- if used, package successfully uploads to TestPyPI
- `uvx` can install and run from TestPyPI
- all core functionality works (list, download, retention, etc.)

## Step 6: Trigger Production PyPI Publication

### Tasks

- merge PR to main branch to trigger workflow
- monitor GitHub Actions workflow execution
- verify package appears on PyPI after workflow completes
- test installation: `uvx blackvuesync --help`
- test with actual dashcam if available

### Success Criteria

- workflow successfully publishes to PyPI
- package is live on PyPI at <https://pypi.org/project/blackvuesync/>
- `uvx blackvuesync` works without any setup
- users can run the tool with just `uv` installed

## Step 7: Update Documentation

### Tasks

- update README.md with PyPI installation instructions
- add `uvx` as recommended installation method
- document traditional `pip install` method as alternative
- update Docker documentation to mention PyPI package option
- add note about zero dependencies and single-file design benefits
- document the automated publishing process for maintainers

### Success Criteria

- README shows `uvx blackvuesync` as primary installation method
- all installation methods are documented
- users understand the benefits of the uv approach
- maintainers know that publishing is automatic on main branch

## Dependencies

- need PyPI account to configure trusted publishing
- need `build` or `uv` installed for local testing
- need GitHub repository permissions to configure Actions

## Risks

- package name "blackvuesync" might already be taken on PyPI
- trusted publishing configuration might need adjustments
- workflow might need debugging on first run
