"""blackvuesync execution step definitions"""

from __future__ import annotations

import logging
import os
import subprocess
from pathlib import Path

from behave import when
from behave.runner import Context
from testcontainers.core.container import DockerContainer

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
    # uses address as-is (should be mock dashcam container name on docker network)
    docker_address = address

    # gets current user's UID/GID
    puid = os.getuid()
    pgid = os.getgid()

    # creates container from pre-built image
    container = DockerContainer(image=context.docker_image.tag)

    # joins the same network as mock dashcam container
    container.with_network(context.docker_network)

    # configures volume mounting
    container.with_volume_mapping(str(destination), "/recordings", mode="rw")

    # configures core environment variables
    container.with_env("PYTHONUNBUFFERED", "1")
    container.with_env("ADDRESS", docker_address)
    container.with_env("SESSION_KEY", session_key)
    container.with_env("PUID", str(puid))
    container.with_env("PGID", str(pgid))

    # syncs timezone with host to ensure date calculations match
    # gets host timezone from TZ env var or system default
    if "TZ" in os.environ:
        host_tz = os.environ["TZ"]
    else:
        from tzlocal import get_localzone_name

        host_tz = get_localzone_name()

    logger.debug("setting docker container timezone to: %s", host_tz)
    container.with_env("TZ", host_tz)

    # sets RUN_ONCE=1 only if not in cron mode
    if not cron:
        container.with_env("RUN_ONCE", "1")

    # configures optional parameters
    if grouping:
        container.with_env("GROUPING", grouping)

    if keep:
        container.with_env("KEEP", keep)

    if priority:
        container.with_env("PRIORITY", priority)

    if filter_list:
        raise NotImplementedError(
            "filter option not supported in docker implementation"
        )

    if max_used_disk is not None:
        container.with_env("MAX_USED_DISK", str(max_used_disk))

    if timeout is not None:
        container.with_env("TIMEOUT", str(timeout))

    if verbose is not None:
        container.with_env("VERBOSE", str(verbose))

    if quiet:
        container.with_env("QUIET", "1")

    if cron:
        container.with_env("CRON", "1")

    if dry_run:
        container.with_env("DRY_RUN", "1")

    logger.info("Starting docker container with image: %s", context.docker_image.tag)

    # starts container and waits for completion
    try:
        with container:
            # waits for container to exit (max 120 seconds)
            result = container.get_wrapped_container().wait(timeout=120)

            # extracts exit code from result (can be int or dict with 'StatusCode')
            if isinstance(result, dict):
                exit_code = result.get("StatusCode", 1)
            else:
                exit_code = result

            # retrieves logs
            stdout = container.get_logs()[0].decode("utf-8")
            stderr = container.get_logs()[1].decode("utf-8")

    except Exception as e:
        logger.error("docker container execution failed: %s", e)
        raise RuntimeError(f"docker container execution failed: {e}") from e

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
