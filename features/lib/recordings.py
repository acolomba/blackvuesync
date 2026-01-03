"""recording file generation and management for tests"""

from __future__ import annotations

import datetime
import random
import re
import shutil
from collections.abc import Generator
from pathlib import Path


def parse_period(period: str) -> datetime.timedelta:
    """parses a period string (e.g., "1d", "2w") into a timedelta"""
    period_match = re.fullmatch(r"(?P<range>\d+)(?P<unit>[dw]?)", period)
    if not period_match:
        raise ValueError(
            f"invalid period format: '{period}'. "
            f"expected format: <number>[d|w] (e.g., '1d', '2d', '1w'). "
            f"d=days, w=weeks"
        )

    period_range = int(period_match.group("range"))

    if period_range < 0:
        raise ValueError(f"period range must be >= 0, got {period_range} in '{period}'")

    period_unit = period_match.group("unit") or "d"

    if period_unit == "d":
        return datetime.timedelta(days=period_range)

    if period_unit == "w":
        return datetime.timedelta(weeks=period_range)

    # this indicates a coding error since the regex only allows [dw]
    raise ValueError(f"unexpected period unit: '{period_unit}' in '{period}'")


def generate_recording_filenames(
    recording_types_str: str,
    recording_directions_str: str,
    recording_others_str: str,
    from_period: str,
    to_period: str,
) -> Generator[str, None, None]:
    """procedurally generates deterministic recording filenames based on criteria

    generates recordings between (today - from_period) and (today - to_period)

    args:
        recording_types_str: recording types (e.g., "NE")
        recording_directions_str: recording directions (e.g., "FR")
        recording_others_str: other flags (e.g., "LS")
        from_period: start of time range, furthest in the past (e.g., "2w")
        to_period: end of time range, closest to today (e.g., "1d")
    """
    today = datetime.date.today()

    # determines date range
    start_date = today - parse_period(from_period)
    end_date = today - parse_period(to_period)

    if start_date > end_date:
        raise ValueError(
            f"from_period ({from_period}) must be further in the past than to_period ({to_period})"
        )

    # calculates number of days to generate
    day_range = (end_date - start_date).days

    if day_range == 0:
        return

    # parses recording types
    recording_types = list(recording_types_str) if recording_types_str else []

    # parses recording directions
    recording_directions = (
        list(recording_directions_str) if recording_directions_str else []
    )

    # parses other flags
    recording_others = list(recording_others_str) if recording_others_str else []

    # generates 5-10 recordings per day for each type
    random.seed(42)  # deterministic generation

    for day_offset in range(day_range):
        date = start_date + datetime.timedelta(days=day_offset)
        recordings_per_day = random.randint(5, 10)

        # picks a random starting time for this set of recordings
        start_hour = random.randint(0, 22)
        start_minute = random.randint(0, 59)
        start_second = random.randint(0, 59)

        # creates base datetime for this day
        base_datetime = datetime.datetime(
            date.year, date.month, date.day, start_hour, start_minute, start_second
        )

        # spreads recordings over 5-10 minutes from the start time
        for i in range(recordings_per_day):
            # calculates timestamp: adds i minutes to base time
            recording_datetime = base_datetime + datetime.timedelta(minutes=i)

            # generates recordings for each type, staggered by 1 second
            for type_offset, recording_type in enumerate(recording_types):
                # staggers each type by 1 second
                type_datetime = recording_datetime + datetime.timedelta(
                    seconds=type_offset
                )

                # builds base filename with timestamp and type
                base_filename = f"{type_datetime.year:04d}{type_datetime.month:02d}{type_datetime.day:02d}_{type_datetime.hour:02d}{type_datetime.minute:02d}{type_datetime.second:02d}"

                # yields video and thumbnail files for each direction (includes direction in filename)
                for recording_direction in recording_directions:
                    # generates files for each upload flag, or once if no flags
                    for recording_other in recording_others or [""]:
                        yield f"{base_filename}_{recording_type}{recording_direction}{recording_other}.mp4"
                        yield f"{base_filename}_{recording_type}{recording_direction}{recording_other}.thm"

                # yields metadata files (no direction in filename)
                for recording_other in recording_others or [""]:
                    yield f"{base_filename}_{recording_type}{recording_other}.3gf"
                    yield f"{base_filename}_{recording_type}{recording_other}.gps"


def extract_date_from_recording_filename(filename: str) -> datetime.date:
    """extracts the date from a recording filename.

    args:
        filename: recording filename (e.g., "20190219_104220_NF.mp4")

    returns:
        date extracted from filename

    raises:
        ValueError: if filename doesn't match expected pattern
    """
    pattern = re.compile(r"^(\d{4})(\d{2})(\d{2})_\d{6}_")
    if not (match := pattern.match(filename)):
        raise ValueError(
            f"invalid recording filename format: '{filename}'. "
            f"expected format: YYYYMMDD_HHMMSS_<type><direction>.<ext>"
        )

    year = int(match.group(1))
    month = int(match.group(2))
    day = int(match.group(3))
    return datetime.date(year, month, day)


def filter_recording_filenames_by_period(
    filenames: list[str],
    from_period: str,
    to_period: str,
) -> list[str]:
    """filters recording filenames to those within the specified time period.

    args:
        filenames: list of recording filenames to filter
        from_period: start of time range, furthest in the past (e.g., "2w")
        to_period: end of time range, closest to today (e.g., "1d"), exclusive

    returns:
        filtered list of filenames within the period [start_date, end_date)

    raises:
        ValueError: if any filename doesn't match expected pattern
    """
    today = datetime.date.today()
    start_date = today - parse_period(from_period)
    end_date = today - parse_period(to_period)

    if start_date > end_date:
        raise ValueError(
            f"from_period ({from_period}) must be further in the past than to_period ({to_period})"
        )

    return [
        filename
        for filename in filenames
        if start_date <= extract_date_from_recording_filename(filename) <= end_date
    ]


def get_mock_file_for_extension(mock_dir: Path, extension: str) -> Path:
    """returns the path to the mock file for a given extension.

    args:
        mock_dir: directory containing mock files
        extension: file extension (e.g., "mp4", "gps")

    returns:
        path to mock.{extension} in mock_dir
    """
    return mock_dir / f"mock.{extension}"


def create_recording_files(
    dest_dir: Path,
    recording_types: str,
    recording_directions: str,
    recording_other: str,
    from_period: str,
    to_period: str,
) -> list[str]:
    """creates recording files in the destination directory.

    generates filenames based on the criteria and copies mock files from
    mock_dashcam/files to the destination with the generated names.

    returns the list of created filenames.
    """
    # generate filenames using the same logic as mock dashcam
    filenames = list(
        generate_recording_filenames(
            recording_types,
            recording_directions,
            recording_other,
            from_period,
            to_period,
        )
    )

    # copies mock files to destination with generated filenames
    mock_dir = Path(__file__).parent.parent / "mock_dashcam" / "files"
    for filename in filenames:
        extension = filename.split(".")[-1]
        source_file = get_mock_file_for_extension(mock_dir, extension)
        dest_path = dest_dir / filename
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source_file, dest_path)

    return filenames
