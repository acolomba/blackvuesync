"""recording file generation and management for tests"""

from __future__ import annotations

import datetime
import random
import re
import shutil
from collections.abc import Generator
from pathlib import Path


def generate_recording_filenames(
    period_past: str,
    recording_types_str: str,
    recording_directions_str: str,
    recording_others_str: str,
) -> Generator[str, None, None]:
    """procedurally generates deterministic recording filenames based on criteria"""
    # parses period_past (e.g., "1d", "2d", "1w", "2w") - matches logic from blackvuesync.py
    period_match = re.fullmatch(r"(?P<range>\d+)(?P<unit>[dw]?)", period_past)
    if not period_match:
        raise ValueError(
            f"invalid period format: '{period_past}'. "
            f"expected format: <number>[d|w] (e.g., '1d', '2d', '1w'). "
            f"d=days, w=weeks"
        )

    period_range = int(period_match.group("range"))

    if period_range < 0:
        raise ValueError(
            f"period range must be >= 0, got {period_range} in '{period_past}'"
        )

    if period_range == 0:
        return

    period_unit = period_match.group("unit") or "d"

    if period_unit == "d":
        period_range_timedelta = datetime.timedelta(days=period_range)
    elif period_unit == "w":
        period_range_timedelta = datetime.timedelta(weeks=period_range)
    else:
        # this indicates a coding error since the regex only allows [dw]
        raise ValueError(f"unexpected period unit: '{period_unit}' in '{period_past}'")

    today = datetime.date.today()
    cutoff_date = today - period_range_timedelta

    # calculates number of days to generate
    day_range = (today - cutoff_date).days

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

    for day_offset in range(0, day_range):
        date = today - datetime.timedelta(days=day_offset)
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
    period_past: str,
    recording_types: str,
    recording_directions: str,
    recording_other: str,
) -> list[str]:
    """creates recording files in the destination directory.

    generates filenames based on the criteria and copies mock files from
    mock_dashcam/files to the destination with the generated names.

    returns the list of created filenames.
    """
    # generate filenames using the same logic as mock dashcam
    filenames = list(
        generate_recording_filenames(
            period_past, recording_types, recording_directions, recording_other
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
