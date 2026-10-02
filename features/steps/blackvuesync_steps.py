"""blackvuesync run step definitions."""

from __future__ import annotations

import datetime
import re

from behave import when
from behave.runner import Context

from features.lib.runner import RunResult, run_direct, run_docker

# one or more long options with quoted values: include "N" exclude "NR"
OPTIONS_RE = re.compile(r'[a-z-]+ "[^"]*"(?: [a-z-]+ "[^"]*")*')
OPTION_RE = re.compile(r'([a-z-]+) "([^"]*)"')


def _write_run_log(context: Context, result: RunResult) -> None:
    """writes the output of the run to a numbered log in the scenario directory.

    the log stays with the scenario's preserved artifacts when it fails.
    """
    context.run_count += 1
    run_log = context.scenario_dir / f"run-{context.run_count}.log"
    run_log.write_text(
        f"exit code: {result.exit_code}\n"
        f"--- stdout ---\n{result.stdout}\n"
        f"--- stderr ---\n{result.stderr}\n"
    )


def _run_blackvuesync(context: Context, options: dict[str, str]) -> None:
    """runs blackvuesync against the scenario's dashcam session and destination."""
    # blackvuesync reads the date once at start-up, so a run that crosses
    # midnight has either date
    started_on = datetime.date.today()
    context.skip_metadata = set(options.get("skip-metadata", ""))
    context.grouping = options.get("grouping", "none")
    # the request log then covers this run only
    context.dashcam.clear_requests()

    if context.implementation == "docker":
        context.result = run_docker(
            context.docker_image_tag,
            context.docker_network,
            context.mock_dashcam_address,
            context.dest_dir,
            context.dashcam.affinity_key,
            options,
        )
    else:
        context.result = run_direct(
            context.mock_dashcam_address,
            context.dest_dir,
            context.dashcam.affinity_key,
            options,
            context.coverage_file,
        )
    context.run_dates = sorted({started_on, datetime.date.today()})
    _write_run_log(context, context.result)


@when("blackvuesync runs")
def run_blackvuesync(context: Context) -> None:
    """runs blackvuesync with the default options."""
    _run_blackvuesync(context, {})


@when("blackvuesync runs with {options}")
def run_blackvuesync_with_options(context: Context, options: str) -> None:
    """runs blackvuesync with long options written as name "value" pairs.

    examples: keep "3d", or include "N" exclude "NR".
    """
    if not OPTIONS_RE.fullmatch(options):
        raise ValueError(f'expected name "value" option pairs, got: {options}')
    pairs = OPTION_RE.findall(options)
    parsed = dict(pairs)
    if len(parsed) != len(pairs):
        raise ValueError(f"expected distinct option names, got: {options}")
    _run_blackvuesync(context, parsed)
