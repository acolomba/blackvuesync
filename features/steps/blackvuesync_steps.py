"""blackvuesync execution step definitions"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from behave import when
from behave.runner import Context

logger = logging.getLogger("features.steps")


def execute_blackvuesync(
    context: Context,
    address: str,
    destination: str,
    session_key: str,
    grouping: str | None = None,
    keep: str | None = None,
    priority: str | None = None,
    filter_list: list[str] | None = None,
    max_used_disk: int | None = None,
    timeout: float | None = None,
    verbose: int | None = None,
    quiet: bool = False,
    cron: bool = False,
    dry_run: bool = False,
) -> None:
    """executes blackvuesync with specified parameters and stores results in context."""
    # locates blackvuesync.py
    project_root = Path(__file__).parent.parent.parent
    blackvuesync_script = project_root / "blackvuesync.py"

    # checks if coverage collection is enabled
    collect_coverage = context.config.userdata.getbool("collect_coverage", False)

    # builds command
    if collect_coverage:
        cmd = [
            "coverage",
            "run",
            "--parallel-mode",
            "--source=.",
            str(blackvuesync_script),
            address,
            "-d",
            destination,
            "--session-key",
            session_key,
        ]
    else:
        cmd = [
            "python3",
            str(blackvuesync_script),
            address,
            "-d",
            destination,
            "--session-key",
            session_key,
        ]

    if grouping:
        cmd.extend(["-g", grouping])

    if keep:
        cmd.extend(["-k", keep])

    if priority:
        cmd.extend(["-p", priority])

    if filter_list:
        cmd.append("-f")
        cmd.extend(filter_list)

    if max_used_disk is not None:
        cmd.extend(["-u", str(max_used_disk)])

    if timeout is not None:
        cmd.extend(["-t", str(timeout)])

    if verbose is not None:
        cmd.extend(["-v"] * verbose)

    if quiet:
        cmd.append("-q")

    if cron:
        cmd.append("--cron")

    if dry_run:
        cmd.append("--dry-run")

    logger.info("Running: %s", cmd)

    # prepares environment for coverage collection
    env = os.environ.copy()
    if collect_coverage:
        # stores coverage data in scenario directory
        coverage_dir = context.scenario_dir / "coverage"
        coverage_dir.mkdir(parents=True, exist_ok=True)
        env["COVERAGE_FILE"] = str(coverage_dir / ".coverage")
        logger.info("Coverage data will be saved to: %s", env["COVERAGE_FILE"])

    # runs blackvuesync with timeout
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,  # 2 minute timeout
            env=env,
        )
    except subprocess.TimeoutExpired as e:
        logger.error("blackvuesync timed out after 120 seconds")

        if e.stdout:
            logger.error("stdout: %r", e.stdout)

        if e.stderr:
            logger.error("stderr: %r", e.stderr)
        raise RuntimeError(
            "blackvuesync did not complete within 120 seconds. The process may be hanging or encountering an infinite loop."
        ) from e

    # stores results in context
    context.exit_code = result.returncode
    context.stdout = result.stdout
    context.stderr = result.stderr

    logger.info("blackvuesync exited with code %s", result.returncode)


@when("blackvuesync runs")
def run_blackvuesync(context: Context) -> None:
    """executes blackvuesync with configured parameters."""
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
    )
