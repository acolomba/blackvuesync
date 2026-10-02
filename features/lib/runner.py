"""runs blackvuesync directly or in its docker image."""

from __future__ import annotations

import logging
import os
import subprocess
import sys
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

from testcontainers.core.container import DockerContainer
from testcontainers.core.network import Network
from tzlocal import get_localzone_name

from features.lib import PROJECT_ROOT

logger = logging.getLogger("features.runner")

BLACKVUESYNC_SCRIPT = PROJECT_ROOT / "blackvuesync.py"

# seconds a run may take before the test fails
RUN_TIMEOUT = 120

# long options with values and the environment variables blackvuesync.sh maps
# them from in the docker image
DOCKER_OPTION_ENV_VARS = {
    "exclude": "EXCLUDE",
    "grouping": "GROUPING",
    "include": "INCLUDE",
    "keep": "KEEP",
    "log-format": "LOG_FORMAT",
    "max-used-disk": "MAX_USED_DISK",
    "priority": "PRIORITY",
    "retry-failed-after": "RETRY_FAILED_AFTER",
    "skip-metadata": "SKIP_METADATA",
    "timeout": "TIMEOUT",
}


@dataclass(frozen=True)
class RunResult:
    """the outcome of one blackvuesync run."""

    exit_code: int
    stdout: str
    stderr: str


def _logged(result: RunResult) -> RunResult:
    """logs the outcome of a run at debug level and returns it."""
    logger.debug(
        "exit code %d\nstdout:\n%s\nstderr:\n%s",
        result.exit_code,
        result.stdout,
        result.stderr,
    )
    return result


def run_direct(
    address: str,
    destination: Path,
    affinity_key: str,
    options: Mapping[str, str],
    coverage_file: Path | None,
) -> RunResult:
    """runs blackvuesync.py as a subprocess, under coverage when coverage_file is set.

    options maps long option names, such as "keep", to their values.
    """
    cmd = [sys.executable]
    env = os.environ.copy()
    if coverage_file is not None:
        cmd += ["-m", "coverage", "run", "--parallel-mode", "--source=blackvuesync"]
        env["COVERAGE_FILE"] = str(coverage_file)

    cmd += [
        str(BLACKVUESYNC_SCRIPT),
        address,
        "--destination",
        str(destination),
        "--affinity-key",
        affinity_key,
    ]
    for name, value in options.items():
        cmd += [f"--{name}", value]

    logger.info("running (direct): %s", cmd)
    result = subprocess.run(
        cmd, capture_output=True, text=True, timeout=RUN_TIMEOUT, env=env, check=False
    )
    return _logged(RunResult(result.returncode, result.stdout, result.stderr))


def run_docker(
    image_tag: str,
    network: Network,
    address: str,
    destination: Path,
    affinity_key: str,
    options: Mapping[str, str],
) -> RunResult:
    """runs the blackvuesync image once on the network.

    options maps long option names, such as "retry-failed-after", to their
    values, which the image reads from environment variables such as
    RETRY_FAILED_AFTER.

    Raises:
        ValueError: an option has no environment variable in the image.
    """
    unknown = sorted(options.keys() - DOCKER_OPTION_ENV_VARS.keys())
    if unknown:
        raise ValueError(f"options without a docker environment variable: {unknown}")

    container = (
        DockerContainer(image=image_tag)
        .with_network(network)
        .with_volume_mapping(str(destination), "/recordings", mode="rw")
        .with_env("PYTHONUNBUFFERED", "1")
        .with_env("ADDRESS", address)
        .with_env("AFFINITY_KEY", affinity_key)
        .with_env("PUID", str(os.getuid()))
        .with_env("PGID", str(os.getgid()))
        # matches the host timezone so both sides agree on recording dates
        .with_env("TZ", os.environ.get("TZ") or get_localzone_name())
        .with_env("RUN_ONCE", "1")
        # clears the image's CRON default so the run matches direct mode
        .with_env("CRON", "")
    )
    for name, value in options.items():
        container.with_env(DOCKER_OPTION_ENV_VARS[name], value)

    logger.info("running (docker): %s with %s", image_tag, dict(options))
    with container:
        status = container.get_wrapped_container().wait(timeout=RUN_TIMEOUT)
        stdout, stderr = container.get_logs()

    return _logged(
        RunResult(status["StatusCode"], stdout.decode("utf-8"), stderr.decode("utf-8"))
    )
