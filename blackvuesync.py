#!/usr/bin/env python3
"""
Synchronizes recordings from a BlackVue dashcam with a local directory over a LAN.
https://github.com/acolomba/blackvuesync
"""
# pylint: disable=too-many-lines

from __future__ import annotations

# Copyright 2018-2026 Alessandro Colomba (https://github.com/acolomba)
#
# Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated
# documentation files (the "Software"), to deal in the Software without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit
# persons to whom the Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all copies or substantial portions of the
# Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE
# WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR
# COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR
# OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

__version__ = "2.1.1"

import argparse
import contextlib
import datetime
import errno
import fcntl
import glob
import http.client
import logging
import os
import re
import shutil
import socket
import stat
import sys
import time
import urllib
import urllib.parse
import urllib.request
from collections.abc import Callable
from dataclasses import dataclass

# logging
logging.basicConfig(format="%(asctime)s: %(levelname)s %(message)s")

# root logger
logger = logging.getLogger()

# cron logger (remains active in cron mode)
cron_logger = logging.getLogger("cron")


def set_logging_levels(verbosity: int, is_cron_mode: bool) -> None:
    """sets up the logging levels according to the desired verbosity and operation mode"""
    if verbosity == -1:
        logger.setLevel(logging.ERROR)
        cron_logger.setLevel(logging.ERROR)
    elif verbosity == 0:
        logger.setLevel(logging.ERROR if is_cron_mode else logging.WARN)
        cron_logger.setLevel(logging.INFO if is_cron_mode else logging.WARN)
    elif verbosity == 1:
        logger.setLevel(logging.INFO)
        cron_logger.setLevel(logging.INFO)
    else:
        logger.setLevel(logging.DEBUG)
        cron_logger.setLevel(logging.DEBUG)


def flush_logs() -> None:
    """flushes all logging handlers"""
    for handler in logging.root.handlers:
        handler.flush()


# max disk usage percent
max_disk_used_percent = None  # pylint: disable=invalid-name

# socket timeout
socket_timeout = None  # pylint: disable=invalid-name

# indicator that we're doing a dry run
dry_run = None  # pylint: disable=invalid-name

# hours to wait before retrying a failed download
retry_failed_after_hours: float = 24.0  # pylint: disable=invalid-name

# affinity key reserved for test isolation
affinity_key: str | None = None  # pylint: disable=invalid-name

# keep and cutoff date; only recordings from this date on are downloaded and kept
keep_re = re.compile(r"""(?P<range>\d+)(?P<unit>[dw]?)""")
cutoff_date: datetime.date | None = None  # pylint: disable=invalid-name

# errno codes for unavailable dashcam
dashcam_unavailable_errno_codes = (
    errno.EHOSTDOWN,  # host is down
    errno.EHOSTUNREACH,  # host is unreachable
    errno.ENETUNREACH,  # network is unreachable
    errno.ETIMEDOUT,  # connection timed out
)

# for unit testing
today = datetime.date.today()


def calc_cutoff_date(keep: str) -> datetime.date:
    """given a retention period, calculates the date before which files should be deleted"""

    if (keep_match := re.fullmatch(keep_re, keep)) is None:
        raise RuntimeError("KEEP must be in the format <number>[dw]")

    keep_range = int(keep_match.group("range"))

    if keep_range < 1:
        raise RuntimeError("KEEP must be greater than one.")

    keep_unit = keep_match.group("unit") or "d"

    if keep_unit == "d" or keep_unit is None:
        keep_range_timedelta = datetime.timedelta(days=keep_range)
    elif keep_unit == "w":
        keep_range_timedelta = datetime.timedelta(weeks=keep_range)
    else:
        # this indicates a coding error
        raise RuntimeError(f"unknown KEEP unit : {keep_unit}")

    return today - keep_range_timedelta


@dataclass(frozen=True)
class Recording:
    """represents a recording from the dashcam; the dashcam serves the list of video recording filenames (front and rear)"""

    filename: str
    base_filename: str
    group_name: str | None
    datetime: datetime.datetime
    type: str
    direction: str


# dashcam recording filename regular expression
#
# references:
# - https://support.blackvue.com.au/hc/en-us/articles/13301776266895-Video-File-Naming
# N: Normal
# E: Event
# P: Parking motion detection
# M: Manual
# I: Parking impact
# O: Overspeed
# A: Hard acceleration
# T: Hard cornering
# B: Hard braking
# R: Geofence-enter (Fleet)
# X: Geofence-exit (Fleet)
# G: Geofence-pass (Fleet)
# D: Drowsiness (DMS)
# L: Distraction (DMS)
# Y: Seatbelt not detected (DMS)
# F: Driver undetected (DMS)
#
# F: Front camera
# R: Rear camera
# I: Interior camera
# O: Optional camera
#
# L or S: upload flag, Substream or Live
filename_re = re.compile(
    r"""(?P<base_filename>(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)
    _(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d))
    _(?P<type>[NEPMIOATBRXGDLYF])
    (?P<direction>[FRIO])
    (?P<upload>[LS]?)
    \.(?P<extension>mp4)""",
    re.VERBOSE,
)


def to_recording(filename: str, grouping: str) -> Recording | None:
    """extracts recording information from a filename"""
    if (filename_match := re.fullmatch(filename_re, filename)) is None:
        return None

    year = int(filename_match.group("year"))
    month = int(filename_match.group("month"))
    day = int(filename_match.group("day"))
    hour = int(filename_match.group("hour"))
    minute = int(filename_match.group("minute"))
    second = int(filename_match.group("second"))
    recording_datetime = datetime.datetime(year, month, day, hour, minute, second)

    recording_base_filename = filename_match.group("base_filename")
    recording_group_name = get_group_name(recording_datetime, grouping)
    recording_type = filename_match.group("type")
    recording_direction = filename_match.group("direction")

    return Recording(
        filename,
        recording_base_filename,
        recording_group_name,
        recording_datetime,
        recording_type,
        recording_direction,
    )


# pattern of a recording filename as returned in each line from from the dashcam index page
file_line_re = re.compile(r"n:/Record/(?P<filename>.*\.mp4),s:1000000\r\n")


def get_filenames(file_lines: list[str]) -> list[str]:
    """extracts the recording filenames from the lines returned by the dashcam index page"""
    filenames = []
    for file_line in file_lines:
        # the first line is "v:1.00", which won't match, so we skip it
        if file_line_match := re.fullmatch(file_line_re, file_line):
            filenames.append(file_line_match.group("filename"))

    return filenames


def get_dashcam_filenames(base_url: str) -> list[str]:
    """gets the recording filenames from the dashcam"""
    try:
        url = urllib.parse.urljoin(base_url, "blackvue_vod.cgi")
        request = urllib.request.Request(url)
        if affinity_key:
            request.add_header("X-Affinity-Key", affinity_key)

        with urllib.request.urlopen(request) as response:
            response_status_code = response.getcode()
            if response_status_code != 200:
                raise RuntimeError(
                    f"Error response from : {base_url} ; status code : {response_status_code}"
                )

            charset = response.info().get_param("charset", "UTF-8")
            file_lines = [x.decode(charset) for x in response.readlines()]

        return get_filenames(file_lines)
    except urllib.error.URLError as e:
        if isinstance(e.reason, OSError) and (
            isinstance(e.reason, TimeoutError)
            or e.reason.errno in dashcam_unavailable_errno_codes
        ):
            raise UserWarning(f"Dashcam unavailable : {e}") from e

        raise RuntimeError(
            f"Cannot obtain list of recordings from dashcam at address : {base_url}; error : {e}"
        ) from e
    except socket.timeout as e:
        raise UserWarning(
            f"Timeout communicating with dashcam at address : {base_url}; error : {e}"
        ) from e
    except http.client.RemoteDisconnected as e:
        raise UserWarning(
            f"Dashcam disconnected without a response; address : {base_url}; error : {e}"
        ) from e


def get_group_name(recording_datetime: datetime.datetime, grouping: str) -> str | None:
    """determines the group name for a given recording according to the indicated grouping"""
    if grouping == "daily":
        return recording_datetime.date().isoformat()

    if grouping == "weekly":
        recording_date = recording_datetime.date()

        # day of the week (mon = 0, ..., sun = 6)
        recording_weekday = recording_date.weekday()
        recording_weekday_delta = datetime.timedelta(days=recording_weekday)
        recording_mon_date = recording_date - recording_weekday_delta
        return recording_mon_date.isoformat()

    if grouping == "monthly":
        return recording_datetime.date().strftime("%Y-%m")

    if grouping == "yearly":
        return recording_datetime.date().strftime("%Y")

    return None


# download speed units for conversion to a natural representation
speed_units = [(1000000, "Mbps"), (1000, "Kbps"), (1, "bps")]


def to_natural_speed(speed_bps: int) -> tuple[int, str]:
    """returns a natural representation of a given download speed in bps as an scalar+unit tuple (base 10)"""
    for speed_unit_multiplier, speed_unit_name in speed_units:
        if speed_bps > speed_unit_multiplier:
            return int(speed_bps / speed_unit_multiplier), speed_unit_name

    return 0, "bps"


def format_natural_speed(speed_bps: int | None) -> str:
    """formats download speed in bps as a human-readable string like ' (123Mbps)', or empty string if None"""
    if not speed_bps:
        return ""

    speed_value, speed_unit = to_natural_speed(speed_bps)
    return f" ({speed_value}{speed_unit})"


def get_filepath(destination: str, group_name: str | None, filename: str) -> str:
    """constructs a path for a recording file from the destination, group name and filename (or glob pattern)"""
    if group_name:
        return os.path.join(destination, group_name, filename)
    return os.path.join(destination, filename)


def get_failed_marker_filepath(destination: str, filename: str) -> str:
    """returns the filepath for a .failed marker file"""
    return os.path.join(destination, f".{filename}.failed")


def is_download_blocked_by_failure(destination: str, filename: str) -> bool:
    """checks if a recent failure marker exists for this file"""
    marker_filepath = get_failed_marker_filepath(destination, filename)

    if not os.path.exists(marker_filepath):
        return False

    try:
        with open(marker_filepath, encoding="utf-8") as f:
            timestamp_str = f.read().strip()

        failure_time = datetime.datetime.fromisoformat(timestamp_str)
        elapsed_hours = (
            datetime.datetime.now() - failure_time
        ).total_seconds() / 3600.0

        return elapsed_hours < retry_failed_after_hours
    except (ValueError, OSError):
        # marker file is corrupted or unreadable; treat as stale and retry
        return False


def mark_download_failed(destination: str, filename: str) -> None:
    """creates or updates a .failed marker file with the current timestamp"""
    marker_filepath = get_failed_marker_filepath(destination, filename)

    try:
        with open(marker_filepath, "w", encoding="utf-8") as f:
            f.write(datetime.datetime.now().isoformat())
    except OSError as e:
        logger.debug("Could not create failure marker : %s; error : %s", filename, e)


def remove_failed_marker(destination: str, filename: str) -> None:
    """removes a .failed marker file if it exists"""
    marker_filepath = get_failed_marker_filepath(destination, filename)

    try:
        if os.path.exists(marker_filepath):
            os.remove(marker_filepath)
    except OSError as e:
        logger.debug("Could not remove failure marker : %s; error : %s", filename, e)


def download_file(
    base_url: str, filename: str, destination: str, group_name: str | None
) -> tuple[bool, int | None]:
    """downloads a file from the dashcam to the destination directory; returns whether data was transferred"""
    # pylint: disable=too-many-locals
    # if we have a group name, we may not have ensured it exists yet
    if group_name:
        group_filepath = os.path.join(destination, group_name)
        ensure_destination(group_filepath)

    destination_filepath = get_filepath(destination, group_name, filename)

    if os.path.exists(destination_filepath):
        logger.debug("Ignoring already downloaded file : %s", filename)
        return False, None

    # checks for recent failure marker to avoid retrying known-bad downloads
    if is_download_blocked_by_failure(destination, filename):
        logger.debug("Skipping recently failed download : %s", filename)
        return False, None

    temp_filepath = os.path.join(destination, f".{filename}")
    if os.path.exists(temp_filepath):
        logger.debug("Found incomplete download : %s", temp_filepath)

    if dry_run:
        logger.debug("DRY RUN Would download file : %s", filename)
        return True, None

    try:
        url = urllib.parse.urljoin(base_url, f"Record/{filename}")

        start = time.perf_counter()
        try:
            # request
            request = urllib.request.Request(url)
            if affinity_key:
                request.add_header("X-Affinity-Key", affinity_key)

            # downloads file
            with urllib.request.urlopen(request) as response:
                headers = response.info()
                size = headers.get("Content-Length")

                # writes response to temp file
                with open(temp_filepath, "wb") as f:
                    f.write(response.read())
        finally:
            end = time.perf_counter()
            elapsed_s = end - start

        os.rename(temp_filepath, destination_filepath)

        # successful download; removes any existing failure marker
        remove_failed_marker(destination, filename)

        speed_bps = int(10.0 * float(size) / elapsed_s) if size else None
        speed_str = format_natural_speed(speed_bps)
        logger.debug("Downloaded file : %s%s", filename, speed_str)

        return True, speed_bps
    except urllib.error.URLError as e:
        # data corruption may lead to error status codes; logs a warning (cron) and returns normally
        cron_logger.warning(
            "Could not download file : %s; error : %s; ignoring.", filename, e
        )
        # marks as failed to avoid repeated retries
        mark_download_failed(destination, filename)
        return False, None
    except socket.timeout as e:
        raise UserWarning(
            f"Timeout communicating with dashcam at address : {base_url}; error : {e}"
        ) from e


def download_recording(base_url: str, recording: Recording, destination: str) -> None:
    """downloads the set of recordings, including gps data, for the given filename from the dashcam to the destination
    directory"""
    # first checks that we have enough room left
    disk_usage = shutil.disk_usage(destination)
    disk_used_percent = disk_usage.used / disk_usage.total * 100.0

    if max_disk_used_percent is not None and disk_used_percent > max_disk_used_percent:
        raise RuntimeError(
            f"Not enough disk space left. Max used disk space percentage allowed : {max_disk_used_percent}%"
        )

    # whether any file of a recording (video, thumbnail, gps, accel.) was downloaded
    any_downloaded = False

    # downloads the video recording
    filename = recording.filename
    downloaded, speed_bps = download_file(
        base_url, filename, destination, recording.group_name
    )
    any_downloaded |= downloaded

    # downloads the thumbnail file
    thm_filename = (
        f"{recording.base_filename}_{recording.type}{recording.direction}.thm"
    )
    downloaded, _ = download_file(
        base_url, thm_filename, destination, recording.group_name
    )
    any_downloaded |= downloaded

    # downloads the accelerometer data
    tgf_filename = f"{recording.base_filename}_{recording.type}.3gf"
    downloaded, _ = download_file(
        base_url, tgf_filename, destination, recording.group_name
    )
    any_downloaded |= downloaded

    # downloads the gps data
    gps_filename = f"{recording.base_filename}_{recording.type}.gps"
    downloaded, _ = download_file(
        base_url, gps_filename, destination, recording.group_name
    )
    any_downloaded |= downloaded

    # logs if any part of a recording was downloaded (or would have been)
    if any_downloaded:
        # recording logger, depends on type of recording
        recording_logger = cron_logger if recording.type in ("N", "M") else logger

        if not dry_run:
            speed_str = format_natural_speed(speed_bps)
            recording_logger.info(
                "Downloaded recording : %s (%s%s)%s",
                recording.base_filename,
                recording.type,
                recording.direction,
                speed_str,
            )
        else:
            recording_logger.info(
                "DRY RUN Would download recording : %s (%s%s)",
                recording.base_filename,
                recording.type,
                recording.direction,
            )


def sort_recordings(recordings: list[Recording], recording_priority: str) -> None:
    """sorts recordings in place according to the given priority"""

    # preferred orderings (by type and direction)
    recording_types = "MEIBOATRXGNP"
    recording_directions = "FRIO"

    # tomorrow, for reverse datetime sorting
    tomorrow = datetime.datetime.now() + datetime.timedelta(days=1)

    def datetime_sort_key(recording: Recording) -> tuple[datetime.datetime, int]:
        """sorts by datetime, then front/rear direction, then recording type"""
        return recording.datetime, recording_directions.find(recording.direction)

    def rev_datetime_sort_key(recording: Recording) -> tuple[datetime.timedelta, int]:
        """sorts by newest to oldest datetime, then front/rear/interior direction"""
        return tomorrow - recording.datetime, recording_directions.find(
            recording.direction
        )

    def manual_event_sort_key(
        recording: Recording,
    ) -> tuple[int, datetime.datetime, int]:
        """sorts by recording type (manual and events first), then datetime, then front/rear/interior direction"""
        return (
            recording_types.find(recording.type),
            recording.datetime,
            recording_directions.find(recording.direction),
        )

    sort_key: Callable[[Recording], tuple[object, ...]]
    if recording_priority == "date":
        # least recent first
        sort_key = datetime_sort_key
    elif recording_priority == "rdate":
        # most recent first
        sort_key = rev_datetime_sort_key
    elif recording_priority == "type":
        # manual, event, normal, parking
        sort_key = manual_event_sort_key
    else:
        # this indicates a coding error
        raise RuntimeError(f"unknown recording priority : {recording_priority}")

    recordings.sort(key=sort_key)


# group name globs, keyed by grouping
group_name_globs = {
    "none": None,
    "daily": "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]",
    "weekly": "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]",
    "monthly": "[0-9][0-9][0-9][0-9]-[0-9][0-9]",
    "yearly": "[0-9][0-9][0-9][0-9]",
}


@dataclass(frozen=True)
class DownloadedRecording:
    """represents a recording downloaded to the destination; matches all files (video front/rear, gps, etc.)"""

    base_filename: str
    group_name: str | None
    datetime: datetime.datetime


# downloaded recording filename regular expression
downloaded_filename_re = re.compile(
    r"""^(?P<base_filename>(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)
    _(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d))_""",
    re.VERBOSE,
)


def to_downloaded_recording(filename: str, grouping: str) -> DownloadedRecording | None:
    """extracts destination recording information from a filename"""
    if (filename_match := re.match(downloaded_filename_re, filename)) is None:
        return None

    year = int(filename_match.group("year"))
    month = int(filename_match.group("month"))
    day = int(filename_match.group("day"))
    hour = int(filename_match.group("hour"))
    minute = int(filename_match.group("minute"))
    second = int(filename_match.group("second"))
    recording_datetime = datetime.datetime(year, month, day, hour, minute, second)

    recording_base_filename = filename_match.group("base_filename")
    recording_group_name = get_group_name(recording_datetime, grouping)

    return DownloadedRecording(
        recording_base_filename, recording_group_name, recording_datetime
    )


# downloaded recording filename glob pattern
DOWNLOADED_FILENAME_GLOB = (
    "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]_*.*"
)


def get_downloaded_recordings(
    destination: str, grouping: str
) -> set[DownloadedRecording]:
    """reads files from the destination directory and returns them as recording records"""
    group_name_glob = group_name_globs[grouping]

    downloaded_filepath_glob = get_filepath(
        destination, group_name_glob, DOWNLOADED_FILENAME_GLOB
    )

    downloaded_filepaths = glob.glob(downloaded_filepath_glob)

    return {
        r
        for p in downloaded_filepaths
        if (r := to_downloaded_recording(os.path.basename(p), grouping)) is not None
    }


def get_outdated_recordings(
    destination: str, grouping: str
) -> list[DownloadedRecording]:
    """returns the recordings prior to the cutoff date"""
    if cutoff_date is None:
        return []

    downloaded_recordings = get_downloaded_recordings(destination, grouping)

    return [x for x in downloaded_recordings if x.datetime.date() < cutoff_date]


def get_current_recordings(recordings: list[Recording]) -> list[Recording]:
    """returns the recordings that are after or on the cutoff date"""
    return (
        recordings
        if cutoff_date is None
        else [x for x in recordings if x.datetime.date() >= cutoff_date]
    )


def get_filtered_recordings(
    recordings: list[Recording], recording_filter: tuple[str, ...] | None
) -> list[Recording]:
    """returns recordings filtered by recording_filter"""
    return (
        recordings
        if recording_filter is None
        else [x for x in recordings if f"{x.type}{x.direction}" in recording_filter]
    )


def ensure_destination(destination: str) -> None:
    """ensures the destination directory exists, creates if not, verifies it's writeable"""
    # if no destination, creates it
    if not os.path.exists(destination):
        os.makedirs(destination)
        return

    # destination exists, tests if directory
    if not os.path.isdir(destination):
        raise RuntimeError(f"download destination is not a directory : {destination}")

    # destination is a directory, tests if writable
    if not os.access(destination, os.W_OK):
        raise RuntimeError(
            f"download destination directory not writable : {destination}"
        )


def prepare_destination(destination: str, grouping: str) -> None:
    """prepares the destination, ensuring it's valid and removing excess recordings"""
    # optionally removes outdated recordings
    if cutoff_date:
        outdated_recordings = get_outdated_recordings(destination, grouping)

        for outdated_recording in outdated_recordings:
            if dry_run:
                logger.info(
                    "DRY RUN Would remove outdated recording : %s",
                    outdated_recording.base_filename,
                )
                continue

            logger.info(
                "Removing outdated recording : %s", outdated_recording.base_filename
            )

            outdated_recording_glob = (
                f"{outdated_recording.base_filename}_[NEPMIOATBRXGDLYF]*.*"
            )
            outdated_filepath_glob = get_filepath(
                destination, outdated_recording.group_name, outdated_recording_glob
            )

            outdated_filepaths = glob.glob(outdated_filepath_glob)

            for outdated_filepath in outdated_filepaths:
                os.remove(outdated_filepath)


def sync(
    address: str,
    destination: str,
    grouping: str,
    download_priority: str,
    recording_filter: tuple[str, ...] | None,
) -> None:
    """synchronizes the recordings at the dashcam address with the destination directory"""
    prepare_destination(destination, grouping)

    base_url = f"http://{address}"
    dashcam_filenames = get_dashcam_filenames(base_url)
    dashcam_recordings = [
        r for x in dashcam_filenames if (r := to_recording(x, grouping)) is not None
    ]

    # figures out which recordings are current and should be downloaded
    current_dashcam_recordings = get_current_recordings(dashcam_recordings)

    # filters recordings according to recording_filter tuple
    current_dashcam_recordings = get_filtered_recordings(
        current_dashcam_recordings, recording_filter
    )

    # sorts the dashcam recordings so we download them according to some priority
    sort_recordings(current_dashcam_recordings, download_priority)

    for recording in current_dashcam_recordings:
        download_recording(base_url, recording, destination)


def is_empty_directory(dirpath: str) -> bool:
    """tests if a directory is empty, ignoring anything that's not a video recording"""
    return all(not x.endswith(".mp4") for x in os.listdir(dirpath))


# temp filename regular expression
TEMP_FILENAME_GLOB = ".[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]_[NEPMIOATBRXGDLYF]*.*"

# failed marker filename glob pattern
FAILED_MARKER_GLOB = ".[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]_[NEPMIOATBRXGDLYF]*.*.failed"


def clean_destination(
    destination: str, grouping: str
) -> None:  # pylint: disable=too-many-locals,too-many-branches
    """removes temporary artifacts from the destination directory"""
    # removes temporary files from interrupted downloads
    temp_filepath_glob = os.path.join(destination, TEMP_FILENAME_GLOB)
    temp_filepaths = glob.glob(temp_filepath_glob)

    for temp_filepath in temp_filepaths:
        if not dry_run:
            logger.debug("Removing temporary file : %s", temp_filepath)
            os.remove(temp_filepath)
        else:
            logger.debug("DRY RUN Would remove temporary file : %s", temp_filepath)

    # removes stale failure markers (older than retry period)
    failed_marker_glob = os.path.join(destination, FAILED_MARKER_GLOB)
    failed_marker_filepaths = glob.glob(failed_marker_glob)

    for marker_filepath in failed_marker_filepaths:
        try:
            with open(marker_filepath, encoding="utf-8") as f:
                timestamp_str = f.read().strip()
            failure_time = datetime.datetime.fromisoformat(timestamp_str)
            elapsed_hours = (
                datetime.datetime.now() - failure_time
            ).total_seconds() / 3600.0

            if elapsed_hours >= retry_failed_after_hours:
                if not dry_run:
                    logger.debug("Removing stale failure marker : %s", marker_filepath)
                    os.remove(marker_filepath)
                else:
                    logger.debug(
                        "DRY RUN Would remove stale failure marker : %s",
                        marker_filepath,
                    )
        except (ValueError, OSError):
            # corrupted marker; remove it
            if not dry_run:
                logger.debug("Removing corrupted failure marker : %s", marker_filepath)
                with contextlib.suppress(OSError):
                    os.remove(marker_filepath)
            else:
                logger.debug(
                    "DRY RUN Would remove corrupted failure marker : %s",
                    marker_filepath,
                )

    # removes empty grouping directories; ignores dotfiles such as .DS_Store
    group_name_glob = group_name_globs[grouping]
    if group_name_glob:
        group_filepath_glob = os.path.join(destination, group_name_glob)

        group_filepaths = glob.glob(group_filepath_glob)

        for group_filepath in group_filepaths:
            if is_empty_directory(group_filepath):
                if not dry_run:
                    logger.debug("Removing grouping directory : %s", group_filepath)
                    shutil.rmtree(group_filepath)
                else:
                    logger.debug(
                        "DRY RUN Would remove grouping directory : %s", group_filepath
                    )


def lock(destination: str) -> int:
    """creates a lock to ensure only one instance is running on a given destination; adapted from:
    https://stackoverflow.com/questions/220525/ensure-a-single-instance-of-an-application-in-linux
    """
    # Establish lock file settings
    lf_path = os.path.join(destination, ".blackvuesync.lock")
    lf_flags = os.O_WRONLY | os.O_CREAT
    lf_mode = stat.S_IWUSR | stat.S_IWGRP | stat.S_IWOTH  # This is 0o222, i.e. 146

    # Create lock file
    # Regarding umask, see https://stackoverflow.com/a/15015748/832230
    umask_original = os.umask(0)

    try:
        lf_fd = os.open(lf_path, lf_flags, lf_mode)
    finally:
        os.umask(umask_original)

    try:
        fcntl.lockf(lf_fd, fcntl.LOCK_EX | fcntl.LOCK_NB)

        return lf_fd
    except OSError as e:
        raise UserWarning(
            f"Another instance is already running for destination : {destination}"
        ) from e


def unlock(lf_fd: int) -> None:
    """unlocks the lock file; does not remove because another process may lock it in the meantime"""
    fcntl.lockf(lf_fd, fcntl.LOCK_UN)


def parse_args() -> argparse.Namespace:
    """parses the command-line arguments"""
    arg_parser = argparse.ArgumentParser(
        description="Synchronizes BlackVue dashcam recordings with a local directory.",
        epilog="Bug reports: https://github.com/acolomba/BlackVueSync",
    )
    arg_parser.add_argument(
        "address", metavar="ADDRESS", help="dashcam IP address or name"
    )
    arg_parser.add_argument(
        "-d",
        "--destination",
        metavar="DEST",
        help="sets the destination directory to DEST; defaults to the current directory",
    )
    arg_parser.add_argument(
        "-g",
        "--grouping",
        metavar="GROUPING",
        default="none",
        choices=["none", "daily", "weekly", "monthly", "yearly"],
        help="groups recording by day, week, month or year under a directory named after the date; so respectively 2019-06-15, 2019-06-09 (Mon), 2019-07 or 2019; defaults to none, indicating no grouping",
    )
    arg_parser.add_argument(
        "-k",
        "--keep",
        metavar="KEEP_RANGE",
        help="""keeps recordings in the given range, removing the rest; defaults to days, but can suffix with d, w for days or weeks respectively""",
    )
    arg_parser.add_argument(
        "-p",
        "--priority",
        metavar="DOWNLOAD_PRIORITY",
        default="date",
        choices=["date", "rdate", "type"],
        help="sets the recording download priority; date: downloads in chronological order from oldest to newest; rdate: downloads in chronological order from newest to oldest; type: prioritizes manual, event, normal and then parkingrecordings; defaults to date",
    )
    arg_parser.add_argument(
        "-f",
        "--filter",
        default=None,
        help="downloads recordings filtered by event type and camera direction; e.g.: --filter PF PR downloads only Parking Front and Parking Rear recordings",
        nargs="+",
    )
    arg_parser.add_argument(
        "-u",
        "--max-used-disk",
        metavar="DISK_USAGE_PERCENT",
        default=90,
        type=int,
        choices=range(5, 99),
        help="stops downloading recordings if disk is over DISK_USAGE_PERCENT used; defaults to 90",
    )
    arg_parser.add_argument(
        "-t",
        "--timeout",
        metavar="TIMEOUT",
        default=10.0,
        type=float,
        help="sets the connection timeout in seconds (float); defaults to 10.0 seconds",
    )
    arg_parser.add_argument(
        "--retry-failed-after",
        metavar="HOURS",
        default=24.0,
        type=float,
        help="hours to wait before retrying a failed download; defaults to 24.0",
    )
    arg_parser.add_argument(
        "-v", "--verbose", action="count", default=0, help="increases verbosity"
    )
    arg_parser.add_argument(
        "-q",
        "--quiet",
        action="store_true",
        help="quiets down output messages; overrides verbosity options",
    )
    arg_parser.add_argument(
        "--cron",
        action="store_true",
        help="cron mode, only logs normal recordings at default verbosity",
    )
    arg_parser.add_argument(
        "--dry-run", action="store_true", help="shows what the program would do"
    )
    arg_parser.add_argument(
        "--affinity-key",
        metavar="AFFINITY_KEY",
        help="affinity key; reserved for test isolation",
    )
    arg_parser.add_argument(
        "--version",
        action="version",
        default=__version__,
        version=f"%(prog)s {__version__}",
        help="shows the version and exits",
    )

    return arg_parser.parse_args()


def main() -> int:
    """run forrest run"""
    # dry-run is a global setting
    # pylint: disable=global-statement
    global dry_run
    global max_disk_used_percent
    global cutoff_date
    global socket_timeout
    global affinity_key
    global retry_failed_after_hours

    args = parse_args()

    dry_run = args.dry_run
    affinity_key = args.affinity_key
    if dry_run:
        logger.info("DRY RUN No action will be taken.")

    max_disk_used_percent = args.max_used_disk
    retry_failed_after_hours = args.retry_failed_after

    set_logging_levels(-1 if args.quiet else args.verbose, args.cron)

    # sets socket timeout
    socket_timeout = args.timeout
    if socket_timeout <= 0:
        raise argparse.ArgumentTypeError("TIMEOUT must be greater than zero.")
    socket.setdefaulttimeout(socket_timeout)

    # lock file file descriptor
    lf_fd = None

    try:
        if args.keep:
            cutoff_date = calc_cutoff_date(args.keep)
            logger.info("Recording cutoff date : %s", cutoff_date)

        # prepares the local file destination
        destination = args.destination or os.getcwd()
        ensure_destination(destination)

        # grouping
        grouping = args.grouping

        lf_fd = lock(destination)

        try:
            sync(args.address, destination, grouping, args.priority, args.filter)
        finally:
            # removes temporary files (if we synced successfully, these are temp files from lost recordings)
            clean_destination(destination, grouping)
    except UserWarning as e:
        logger.warning(e.args[0])
        return 0 if args.cron else 1
    except RuntimeError as e:
        logger.error(e.args[0])
        return 2
    except Exception as e:  # pylint: disable=broad-exception-caught
        logger.exception(e)
        return 3
    finally:
        if lf_fd:
            unlock(lf_fd)

        flush_logs()

    return 0


if __name__ == "__main__":
    sys.exit(main())
