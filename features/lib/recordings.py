"""recording filename generation, selection, and destination listing for tests."""

from __future__ import annotations

import datetime
import random
import re
import shutil
from collections.abc import Collection, Iterable, Iterator
from pathlib import Path, PurePosixPath

from features.lib import PROJECT_ROOT

# fixture files the mock dashcam serves for every recording, one per extension
MOCK_FILES_DIR = PROJECT_ROOT / "features" / "mock_dashcam" / "files"

# BlackVue recording filename: YYYYMMDD_HHMMSS_<type>[<direction>][<upload>].<ext>;
# .3gf and .gps files have no direction since one file covers every camera
RECORDING_FILENAME_RE = re.compile(
    r"""(?P<base_filename>(?P<year>\d{4})(?P<month>\d{2})(?P<day>\d{2})_\d{6})
    _(?P<type>[NEPMIOATBRXGDLYF])
    (?P<direction>[FRIO]?)
    (?P<upload>[LS]?)
    \.(?P<extension>mp4|thm|3gf|gps)""",
    re.VERBOSE,
)

# the lock file blackvuesync creates in the destination and leaves behind
LOCK_FILENAME = ".blackvuesync.lock"

# --skip-metadata codes and the extensions they skip
SKIP_METADATA_EXTENSIONS = {"t": ".thm", "3": ".3gf", "g": ".gps"}


def parse_period(period: str) -> datetime.timedelta:
    """parses a period such as "1d" or "2w" into a timedelta; days without a unit."""
    period_match = re.fullmatch(r"(?P<range>\d+)(?P<unit>[dw]?)", period)
    if not period_match:
        raise ValueError(
            f"invalid period {period!r}; expected <number>[d|w], e.g. '1d', '2w'"
        )

    period_range = int(period_match.group("range"))
    if period_match.group("unit") == "w":
        return datetime.timedelta(weeks=period_range)
    return datetime.timedelta(days=period_range)


def _date_range(
    from_period: str, to_period: str, today: datetime.date | None = None
) -> tuple[datetime.date, datetime.date]:
    """returns the dates from_period and to_period before today, oldest first.

    today defaults to the current date.
    """
    if today is None:
        today = datetime.date.today()
    start_date = today - parse_period(from_period)
    end_date = today - parse_period(to_period)

    if start_date > end_date:
        raise ValueError(
            f"from_period {from_period!r} must be further in the past than "
            f"to_period {to_period!r}"
        )

    return start_date, end_date


def generate_recording_filenames(
    recording_types: str, recording_directions: str, from_period: str, to_period: str
) -> Iterator[str]:
    """generates deterministic recording filenames dated in a period.

    the period runs from from_period to to_period before today, inclusive. the
    types and directions are codes such as "N,E" and "F,R".
    """
    start_date, end_date = _date_range(from_period, to_period)
    types = recording_types.replace(",", "")
    directions = recording_directions.replace(",", "")

    rng = random.Random(42)

    for day_offset in range((end_date - start_date).days + 1):
        date = start_date + datetime.timedelta(days=day_offset)
        recordings_per_day = rng.randint(5, 10)

        base_datetime = datetime.datetime(
            date.year,
            date.month,
            date.day,
            rng.randint(0, 22),
            rng.randint(0, 59),
            rng.randint(0, 59),
        )

        # spreads recordings one minute apart, staggering types by one second
        for i in range(recordings_per_day):
            for type_offset, recording_type in enumerate(types):
                recording_datetime = base_datetime + datetime.timedelta(
                    minutes=i, seconds=type_offset
                )
                base_filename = recording_datetime.strftime("%Y%m%d_%H%M%S")

                for direction in directions:
                    yield f"{base_filename}_{recording_type}{direction}.mp4"
                    yield f"{base_filename}_{recording_type}{direction}.thm"

                yield f"{base_filename}_{recording_type}.3gf"
                yield f"{base_filename}_{recording_type}.gps"


def copy_fixture_files(dest_dir: Path, filenames: Iterable[str]) -> None:
    """copies the fixture file for each recording filename into dest_dir."""
    for filename in filenames:
        extension = filename.rsplit(".", 1)[-1]
        shutil.copy2(MOCK_FILES_DIR / f"mock.{extension}", dest_dir / filename)


def create_recording_files(
    dest_dir: Path,
    recording_types: str,
    recording_directions: str,
    from_period: str,
    to_period: str,
) -> list[str]:
    """copies the fixture files into dest_dir under generated recording filenames.

    Returns:
        the generated filenames.
    """
    filenames = list(
        generate_recording_filenames(
            recording_types, recording_directions, from_period, to_period
        )
    )
    copy_fixture_files(dest_dir, filenames)
    return filenames


def _relative_paths(directory: Path, pattern: str) -> set[str]:
    """returns the paths, relative to directory, of the files matching pattern."""
    return {
        path.relative_to(directory).as_posix()
        for path in directory.rglob(pattern)
        if path.is_file()
    }


def list_files(directory: Path) -> set[str]:
    """returns the relative paths of the files under directory, dotfiles included."""
    return _relative_paths(directory, "*")


def list_failure_markers(directory: Path) -> set[str]:
    """returns the relative paths of the .failed marker files under directory."""
    return _relative_paths(directory, "*.failed")


def _parse(filename: str) -> re.Match[str]:
    """matches a recording filename, raising ValueError for anything else."""
    if (match := RECORDING_FILENAME_RE.fullmatch(filename)) is None:
        raise ValueError(f"invalid recording filename {filename!r}")
    return match


def _recording_date(filename: str) -> datetime.date:
    """returns the date in a recording filename."""
    match = _parse(filename)
    return datetime.date(
        int(match.group("year")), int(match.group("month")), int(match.group("day"))
    )


def grouped_path(filename: str, grouping: str) -> str:
    """returns the path, relative to the destination, of a downloaded recording file.

    mirrors --grouping: daily and weekly directories are named after the day
    and the monday of its week, YYYY-MM-DD; monthly after YYYY-MM; yearly
    after YYYY; none puts the file in the destination itself.
    """
    if grouping == "none":
        return filename

    date = _recording_date(filename)
    group_names = {
        "daily": date.isoformat(),
        "weekly": (date - datetime.timedelta(days=date.weekday())).isoformat(),
        "monthly": date.strftime("%Y-%m"),
        "yearly": date.strftime("%Y"),
    }
    return f"{group_names[grouping]}/{filename}"


def servable_filenames(
    filenames: Collection[str], legacy_api: bool, skip_metadata: Collection[str]
) -> set[str]:
    """returns the filenames blackvuesync downloads from a dashcam listing them.

    V1.009+ cameras have no accelerometer endpoint, so they never serve .3gf
    files; --skip-metadata drops the skipped extensions.
    """
    excluded = {SKIP_METADATA_EXTENSIONS[code] for code in skip_metadata}
    if not legacy_api:
        excluded.add(".3gf")

    return {
        filename for filename in filenames if not filename.endswith(tuple(excluded))
    }


def select_by_period(
    filenames: Collection[str],
    from_period: str,
    to_period: str,
    today: datetime.date | None = None,
) -> set[str]:
    """returns the recording files dated in a period.

    the files are filenames or paths relative to the destination. the period
    runs from from_period to to_period before today, inclusive. today defaults
    to the current date.
    """
    start_date, end_date = _date_range(from_period, to_period, today)
    return {
        filename
        for filename in filenames
        if start_date <= _recording_date(PurePosixPath(filename).name) <= end_date
    }


def _matches_code(match: re.Match[str], code: str) -> bool:
    """tests a recording against a --include/--exclude code such as "N" or "NF"."""
    return f"{match.group('type')}{match.group('direction')}".startswith(code)


def select_by_codes(filenames: Collection[str], codes: Collection[str]) -> set[str]:
    """returns the files of the recordings matching any of the codes.

    a .3gf or .gps file has no direction, so it belongs to a selected recording
    when a selected video shares its timestamp and type.
    """
    matches = [_parse(filename) for filename in filenames]

    selected = {
        match.string
        for match in matches
        if match.group("direction") and any(_matches_code(match, c) for c in codes)
    }
    selected_keys = {
        (match.group("base_filename"), match.group("type"))
        for match in matches
        if match.string in selected
    }

    return selected | {
        match.string
        for match in matches
        if not match.group("direction")
        and (match.group("base_filename"), match.group("type")) in selected_keys
    }
