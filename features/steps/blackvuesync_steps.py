"""blackvuesync execution step definitions"""

from __future__ import annotations

import logging
import os
import subprocess
import uuid
from pathlib import Path

from behave import when
from behave.runner import Context

from features.lib.docker import IMAGE_TAG

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
    implementation = context.config.userdata.get("implementation", "direct")

    if implementation == "docker":
        _execute_docker(
            context,
            address,
            destination,
            session_key,
            grouping,
            keep,
            priority,
            filter_list,
            max_used_disk,
            timeout,
            verbose,
            quiet,
            cron,
            dry_run,
        )
    else:
        _execute_direct(
            context,
            address,
            destination,
            session_key,
            grouping,
            keep,
            priority,
            filter_list,
            max_used_disk,
            timeout,
            verbose,
            quiet,
            cron,
            dry_run,
        )


def _execute_direct(
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
    """executes blackvuesync directly via python."""
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

    logger.info("Running (direct): %s", cmd)

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


def _execute_docker(
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
    """executes blackvuesync via docker container."""
    # translates localhost address to host.docker.internal for container
    docker_address = address.replace("127.0.0.1", "host.docker.internal")

    # gets current user's UID/GID
    puid = os.getuid()
    pgid = os.getgid()

    # generates unique container name for this test run
    container_name = f"blackvuesync-test-{uuid.uuid4().hex[:8]}"

    # builds docker command
    cmd = [
        "docker",
        "run",
        "--name",
        container_name,
        "--add-host=host.docker.internal:host-gateway",
        "-v",
        f"{destination}:/recordings",
        "-e",
        "PYTHONUNBUFFERED=1",
        "-e",
        f"ADDRESS={docker_address}",
        "-e",
        f"SESSION_KEY={session_key}",
        "-e",
        f"PUID={puid}",
        "-e",
        f"PGID={pgid}",
    ]

    # sets RUN_ONCE=1 only if not in cron mode
    if not cron:
        cmd.extend(["-e", "RUN_ONCE=1"])

    if grouping:
        cmd.extend(["-e", f"GROUPING={grouping}"])

    if keep:
        cmd.extend(["-e", f"KEEP={keep}"])

    if priority:
        cmd.extend(["-e", f"PRIORITY={priority}"])

    if filter_list:
        raise NotImplementedError(
            "filter option not supported in docker implementation"
        )

    if max_used_disk is not None:
        cmd.extend(["-e", f"MAX_USED_DISK={max_used_disk}"])

    if timeout is not None:
        cmd.extend(["-e", f"TIMEOUT={timeout}"])

    if verbose is not None:
        cmd.extend(["-e", f"VERBOSE={verbose}"])

    if quiet:
        cmd.extend(["-e", "QUIET=1"])

    if cron:
        cmd.extend(["-e", "CRON=1"])

    if dry_run:
        cmd.extend(["-e", "DRY_RUN=1"])

    # adds image tag
    cmd.append(IMAGE_TAG)

    logger.info("Running (docker): %s", " ".join(cmd))

    # runs docker container with timeout
    exit_code = 0
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=120,
        )
        exit_code = result.returncode
    except subprocess.TimeoutExpired as e:
        logger.error("docker container timed out after 120 seconds")
        # cleans up timed-out container
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)
        raise RuntimeError(
            "docker container did not complete within 120 seconds"
        ) from e

    # retrieves container output using docker logs
    try:
        logs_result = subprocess.run(
            ["docker", "logs", container_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
        stdout = logs_result.stdout
        stderr = logs_result.stderr
    except subprocess.TimeoutExpired:
        logger.error("docker logs timed out after 30 seconds")
        stdout = ""
        stderr = ""
    finally:
        # cleans up container
        subprocess.run(["docker", "rm", "-f", container_name], capture_output=True)

    # logs on failure
    if exit_code != 0:
        logger.error("docker container failed")
        logger.error("stdout: %r (len=%d)", stdout, len(stdout))
        logger.error("stderr: %r (len=%d)", stderr, len(stderr))

    # stores results in context
    context.exit_code = exit_code
    context.stdout = stdout
    context.stderr = stderr

    logger.info("docker container exited with code %s", exit_code)


@when("blackvuesync runs")
def run_blackvuesync(context: Context) -> None:
    """executes blackvuesync with configured parameters."""
    execute_blackvuesync(
        context,
        context.mock_dashcam_address,
        str(context.dest_dir),
        context.scenario_token,
    )
