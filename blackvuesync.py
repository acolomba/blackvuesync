#!/usr/bin/env python3

# Copyright 2018-2019 Alessandro Colomba (https://github.com/acolomba)
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

__version__ = "1.8a"

import argparse
import datetime
from collections import namedtuple
import fcntl
import glob
import http.client
import logging
import re
import os
import shutil
import stat
import time
import urllib
import urllib.parse
import urllib.request
import socket

# logging
logging.basicConfig(format="%(asctime)s: %(levelname)s %(message)s")

# root logger
logger = logging.getLogger()

# cron logger (remains active in cron mode)
cron_logger = logging.getLogger("cron")


def set_logging_levels(verbosity, is_cron_mode):
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


# max disk usage percent
max_disk_used_percent = None

# socket timeout
socket_timeout = None

# indicator that we're doing a dry run
dry_run = None

# keep and cutoff date; only recordings from this date on are downloaded and kept
keep_re = re.compile(r"""(?P<range>\d+)(?P<unit>[dw]?)""")
cutoff_date = None

# for unit testing
today = datetime.date.today()


def calc_cutoff_date(keep):
    """given a retention period, calculates the date before which files should be deleted"""

    keep_match = re.fullmatch(keep_re, keep)

    if keep_match is None:
        raise RuntimeError("KEEP must be in the format <number>[dw]")

    keep_range = int(keep_match.group("range"))

    if keep_range < 1:
        raise RuntimeError("KEEP must be greater than one.")

    keep_unit = keep_match.group("unit") or "d"

    if keep_unit == "d" or keep_unit is None:
        keep_range_timedelta = datetime.timedelta(days=keep_range)
    elif keep_unit is "w":
        keep_range_timedelta = datetime.timedelta(weeks=keep_range)
    else:
        # this indicates a coding error
        raise RuntimeError("unknown KEEP unit : %s" % keep_unit)

    return today - keep_range_timedelta


# represents a recording: filename and metadata
Recording = namedtuple("Recording", "filename base_filename group_name datetime type direction extension")

# dashcam recording filename regular expression
filename_re = re.compile(r"""(?P<base_filename>(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)
    _(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d))
    _(?P<type>[NEPM])
    (?P<direction>[FR])
    \.(?P<extension>mp4)""", re.VERBOSE)


def to_recording(filename, grouping):
    """extracts recording information from a filename"""
    filename_match = re.fullmatch(filename_re, filename)

    if filename_match is None:
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
    recording_extension = filename_match.group("extension")

    return Recording(filename, recording_base_filename, recording_group_name, recording_datetime, recording_type,
                     recording_direction, recording_extension)


# pattern of a recording filename as returned in each line from from the dashcam index page
file_line_re = re.compile(r"n:/Record/(?P<filename>.*\.mp4),s:1000000\r\n")


def get_filenames(file_lines):
    """extracts the recording filenames from the lines returned by the dashcam index page"""
    filenames = []
    for file_line in file_lines:
        file_line_match = re.fullmatch(file_line_re, file_line)
        # the first line is "v:1.00", which won't match, so we skip it
        if file_line_match:
            filenames.append(file_line_match.group("filename"))

    return filenames


def get_dashcam_filenames(base_url):
    """gets the recording filenames from the dashcam"""
    try:
        url = urllib.parse.urljoin(base_url, "blackvue_vod.cgi")
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)

        response_status_code = response.getcode()
        if response_status_code != 200:
            raise RuntimeError("Error response from : %s ; status code : %s" % (base_url, response_status_code))

        charset = response.info().get_param("charset", "UTF-8")
        file_lines = [x.decode(charset) for x in response.readlines()]

        return get_filenames(file_lines)
    except urllib.error.URLError as e:
        raise RuntimeError("Cannot obtain list of recordings from dashcam at address : %s; error : %s"
                           % (base_url, e))
    except socket.timeout as e:
        raise UserWarning("Timeout communicating with dashcam at address : %s; error : %s" % (base_url, e))
    except http.client.RemoteDisconnected as e:
        raise UserWarning("Dashcam disconnected without a response; address : %s; error : %s" % (base_url, e))


def get_group_name(recording_datetime, grouping):
    """determines the group name for a given recording according to the indicated grouping"""
    if grouping == "daily":
        return recording_datetime.date().isoformat()
    elif grouping == "weekly":
        recording_date = recording_datetime.date()

        # day of the week (mon = 0, ..., sun = 6)
        recording_weekday = recording_date.weekday()
        recording_weekday_delta = datetime.timedelta(days=recording_weekday)
        recording_mon_date = recording_date - recording_weekday_delta
        return recording_mon_date.isoformat()
    elif grouping == "monthly":
        return recording_datetime.date().strftime("%Y-%m")
    elif grouping == "yearly":
        return recording_datetime.date().strftime("%Y")
    else:
        return None


# download speed units for conversion to a natural representation
speed_units = [(1000000, "Mbps"), (1000, "Kbps"), (1, "bps")]


def to_natural_speed(speed_bps):
    """returns a natural representation of a given download speed in bps as an scalar+unit tuple (base 10)"""
    for speed_unit in speed_units:
        speed_unit_multiplier, speed_unit_name = speed_unit
        if speed_bps > speed_unit_multiplier:
            return int(speed_bps / speed_unit_multiplier), speed_unit_name

    return 0, "bps"


def get_filepath(destination, group_name, filename):
    """constructs a path for a recording file from the destination, group name and filename"""
    if group_name:
        return os.path.join(destination, group_name, filename)
    else:
        return os.path.join(destination, filename)


def download_file(base_url, filename, destination, group_name):
    """downloads a file from the dashcam to the destination directory; returns whether data was transferred"""
    global dry_run

    # if we have a group name, we may not have ensured it exists yet
    if group_name:
        group_filepath = os.path.join(destination, group_name)
        ensure_destination(group_filepath)

    filepath = get_filepath(destination, group_name, filename)

    if os.path.exists(filepath):
        logger.debug("Ignoring already downloaded file : %s", filename)
        return False, None

    temp_filepath = os.path.join(destination, ".%s" % filename)
    if os.path.exists(temp_filepath):
        logger.debug("Found incomplete download : %s", temp_filepath)

    if not dry_run:
        try:
            url = urllib.parse.urljoin(base_url, "Record/%s" % filename)

            start = time.perf_counter()
            try:
                _, headers = urllib.request.urlretrieve(url, temp_filepath)
                size = headers["Content-Length"]
            finally:
                end = time.perf_counter()
                elapsed_s = end - start

            os.rename(temp_filepath, filepath)

            speed_bps = int(10. * float(size) / elapsed_s) if size else None
            logger.debug("Downloaded file : %s%s", filename,
                         " (%s%s)" % to_natural_speed(speed_bps) if speed_bps else "")

            return True, speed_bps
        except urllib.error.URLError as e:
            # data corruption may lead to error status codes; logs a warning (cron) and returns normally
            cron_logger.warning("Could not download file : %s; error : %s; ignoring.", filename, e)
            return False, None
        except socket.timeout as e:
            raise UserWarning("Timeout communicating with dashcam at address : %s; error : %s" % (base_url, e))
    else:
        logger.debug("DRY RUN Would download file : %s", filename)
        return True, None


def download_recording(base_url, recording, destination):
    """downloads the set of recordings, including gps data, for the given filename from the dashcam to the destination
    directory"""
    global max_disk_used_percent

    # first checks that we have enough room left
    disk_usage = shutil.disk_usage(destination)
    disk_used_percent = disk_usage.used / disk_usage.total * 100.0

    if disk_used_percent > max_disk_used_percent:
        raise RuntimeError("Not enough disk space left. Max used disk space percentage allowed : %s%%"
                           % max_disk_used_percent)

    # whether any file of a recording (video, thumbnail, gps, accel.) was downloaded
    any_downloaded = False

    # downloads the video recording
    filename = recording.filename
    downloaded, speed_bps = download_file(base_url, filename, destination, recording.group_name)
    any_downloaded |= downloaded

    # downloads the thumbnail file
    thm_filename = "%s_%s%s.thm" % (recording.base_filename, recording.type, recording.direction)
    downloaded, _ = download_file(base_url, thm_filename, destination, recording.group_name)
    any_downloaded |= downloaded

    # downloads the accelerometer data
    tgf_filename = "%s_%s.3gf" % (recording.base_filename, recording.type)
    downloaded, _ = download_file(base_url, tgf_filename, destination, recording.group_name)
    any_downloaded |= downloaded

    # downloads the gps data for normal, event and manual recordings
    if recording.type in ("N", "E", "M"):
        gps_filename = "%s_%s.gps" % (recording.base_filename, recording.type)
        downloaded, _ = download_file(base_url, gps_filename, destination, recording.group_name)
        any_downloaded |= downloaded

    # logs if any part of a recording was downloaded (or would have been)
    if any_downloaded:
        # recording logger, depends on type of recording
        recording_logger = cron_logger if recording.type in ("N", "M") else logger

        if not dry_run:
            recording_logger.info("Downloaded recording : %s%s", recording.base_filename,
                                  " (%s%s)" % to_natural_speed(speed_bps) if speed_bps else "")
        else:
            recording_logger.info("DRY RUN Would download recording : %s", recording.base_filename)


def sort_recordings(recordings, recording_priority):
    """sorts recordings in place according to the given priority"""

    def datetime_sort_key(recording):
        """sorts by datetime, then recording type, then front/rear direction"""
        return recording.datetime, "FR".find(recording.direction)

    def manual_event_sort_key(recording):
        """sorts by recording type, then datetime, then front/rear direction"""
        return "MENP".find(recording.type), recording.datetime, "FR".find(recording.direction)

    if recording_priority == "date":
        # least recent first
        sort_key = datetime_sort_key
    elif recording_priority == "type":
        # manual, event, normal, parking
        sort_key = manual_event_sort_key
    else:
        # this indicates a coding error
        raise RuntimeError("unknown recording priority : %s" % recording_priority)

    recordings.sort(key=sort_key)


# group name globs, keyed by grouping
group_name_globs = {
    "none": None,
    "daily": "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]",
    "weekly": "[0-9][0-9][0-9][0-9]-[0-9][0-9]-[0-9][0-9]",
    "monthly": "[0-9][0-9][0-9][0-9]-[0-9][0-9]",
    "yearly": "[0-9][0-9][0-9][0-9]",
}

# dashcam recording filename glob pattern
filename_glob = "[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]_[NEPM][FR].mp4"


def get_destination_recordings(destination, grouping):
    """reads files from the destination directory and returns them as recording records"""
    group_name_glob = group_name_globs[grouping]

    existing_filepath_glob = get_filepath(destination, group_name_glob, filename_glob)

    existing_filepaths = glob.glob(existing_filepath_glob)

    return [r for r in [to_recording(os.path.basename(p), grouping) for p in existing_filepaths] if r is not None]


def get_outdated_recordings(recordings):
    """returns the recordings prior to the cutoff date"""
    global cutoff_date

    return [] if cutoff_date is None else [x for x in recordings if x.datetime.date() < cutoff_date]


def get_current_recordings(recordings):
    """returns the recordings that are after or on the cutoff date"""
    global cutoff_date
    return recordings if cutoff_date is None else [x for x in recordings if x.datetime.date() >= cutoff_date]


def ensure_destination(destination):
    """ensures the destination directory exists, creates if not, verifies it's writeable"""
    # if no destination, creates it
    if not os.path.exists(destination):
        os.makedirs(destination)
        return

    # destination exists, tests if directory
    if not os.path.isdir(destination):
        raise RuntimeError("download destination is not a directory : %s" % destination)

    # destination is a directory, tests if writable
    if not os.access(destination, os.W_OK):
        raise RuntimeError("download destination directory not writable : %s" % destination)


def prepare_destination(destination, grouping):
    """prepares the destination, ensuring it's valid and removing excess recordings"""
    global dry_run
    global cutoff_date

    # optionally removes outdated recordings
    if cutoff_date:
        existing_recordings = get_destination_recordings(destination, grouping)
        outdated_recordings = get_outdated_recordings(existing_recordings)

        for outdated_recording in outdated_recordings:
            outdated_filepath = get_filepath(destination, outdated_recording.group_name, outdated_recording.filename)
            if not dry_run:
                logger.info("Removing outdated recording : %s", outdated_recording.base_filename)

                # removes the video recording
                os.remove(outdated_filepath)

                # removes the thumbnail file
                outdated_thm_filename = "%s_%s%s.thm" % (outdated_recording.base_filename, outdated_recording.type,
                                                         outdated_recording.direction)
                outdated_thm_filepath = get_filepath(destination, outdated_recording.group_name, outdated_thm_filename)
                if os.path.exists(outdated_thm_filepath):
                    os.remove(outdated_thm_filepath)

                # removes the accelerometer data
                outdated_tgf_filename = "%s_%s.3gf" % (outdated_recording.base_filename, outdated_recording.type)
                outdated_tgf_filepath = get_filepath(destination, outdated_recording.group_name, outdated_tgf_filename)
                if os.path.exists(outdated_tgf_filepath):
                    os.remove(outdated_tgf_filepath)

                # removes the gps data for normal, event and manual recordings
                if outdated_recording.type in ("N", "E", "M"):
                    outdated_gps_filename = "%s_%s.gps" % (outdated_recording.base_filename, outdated_recording.type)
                    outdated_gps_filepath = get_filepath(destination, outdated_recording.group_name,
                                                         outdated_gps_filename)
                    if os.path.exists(outdated_gps_filepath):
                        os.remove(outdated_gps_filepath)
            else:
                logger.info("DRY RUN Would remove outdated recording : %s", outdated_recording.base_filename)


def sync(address, destination, grouping, download_priority):
    """synchronizes the recordings at the dashcam address with the destination directory"""
    prepare_destination(destination, grouping)

    base_url = "http://%s" % address
    dashcam_filenames = get_dashcam_filenames(base_url)
    dashcam_recordings = [to_recording(x, grouping) for x in dashcam_filenames]

    # figures out which recordings are current and should be downloaded
    current_dashcam_recordings = get_current_recordings(dashcam_recordings)

    # sorts the dashcam recordings so we download them according to some priority
    sort_recordings(current_dashcam_recordings, download_priority)

    for recording in current_dashcam_recordings:
        download_recording(base_url, recording, destination)


def is_empty_directory(dirpath):
    """tests if a directory is empty, ignoring anything that's not a video recording"""
    return all(not x.endswith(".mp4") for x in os.listdir(dirpath))


# temp filename regular expression
temp_filename_glob = ".[0-9][0-9][0-9][0-9][0-9][0-9][0-9][0-9]_[0-9][0-9][0-9][0-9][0-9][0-9]_[NEPM]*.*"


def clean_destination(destination, grouping):
    """removes temporary artifacts from the destination directory"""
    global dry_run

    # removes temporary files from interrupted downloads
    temp_filepath_glob = os.path.join(destination, temp_filename_glob)
    temp_filepaths = glob.glob(temp_filepath_glob)

    for temp_filepath in temp_filepaths:
        if not dry_run:
            logger.debug("Removing temporary file : %s" % temp_filepath)
            os.remove(temp_filepath)
        else:
            logger.debug("DRY RUN Would remove temporary file : %s", temp_filepath)

    # removes empty grouping directories; dotfiles such as .DS_Store
    group_name_glob = group_name_globs[grouping]
    if group_name_glob:
        group_filepath_glob = os.path.join(destination, group_name_glob)

        group_filepaths = glob.glob(group_filepath_glob)

        for group_filepath in group_filepaths:
            if is_empty_directory(group_filepath):
                if not dry_run:
                    logger.debug("Removing grouping directory : %s" % group_filepath)
                    shutil.rmtree(group_filepath)
                else:
                    logger.debug("DRY RUN Would remove grouping directory : %s", group_filepath)


def lock(destination):
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
    except IOError:
        raise UserWarning("Another instance is already running for destination : %s" % destination)


def unlock(lf_fd):
    """unlocks the lock file; does not remove because another process may lock it in the meantime"""
    fcntl.lockf(lf_fd, fcntl.LOCK_UN)


def parse_args():
    """parses the command-line arguments"""
    global __version__

    arg_parser = argparse.ArgumentParser(description="Synchronizes BlackVue dashcam recordings with a local directory.",
                                         epilog="Bug reports: https://github.com/acolomba/BlackVueSync")
    arg_parser.add_argument("address", metavar="ADDRESS",
                            help="dashcam IP address or name")
    arg_parser.add_argument("-d", "--destination", metavar="DEST",
                            help="sets the destination directory to DEST; defaults to the current directory")
    arg_parser.add_argument("-g", "--grouping", metavar="GROUPING", default="none",
                            choices=["none", "daily", "weekly", "monthly", "yearly"],
                            help="groups recording by day, week, month or year under a directory named after the date; "
                                 "so respectively 2019-06-15, 2019-06-09 (Mon), 2019-07 or 2019; "
                                 "defaults to ""none"", indicating no grouping")
    arg_parser.add_argument("-k", "--keep", metavar="KEEP_RANGE",
                            help="""keeps recordings in the given range, removing the rest; defaults to days, but can
                            suffix with d, w for days or weeks respectively""")
    arg_parser.add_argument("-p", "--priority", metavar="DOWNLOAD_PRIORITY", default="date",
                            choices=["date", "type"],
                            help="sets the recording download priority; ""date"": downloads in chronological order "
                                 "from oldest to newest; ""type"": prioritizes manual, event, normal and then parking"
                                 "recordings; defaults to ""date""")
    arg_parser.add_argument("-u", "--max-used-disk", metavar="DISK_USAGE_PERCENT", default=90,
                            type=int, choices=range(5, 99),
                            help="stops downloading recordings if disk is over DISK_USAGE_PERCENT used; defaults to 90")
    arg_parser.add_argument("-t", "--timeout", metavar="TIMEOUT", default=10.0,
                            type=float,
                            help="sets the connection timeout in seconds (float); defaults to 10.0 seconds")
    arg_parser.add_argument("-v", "--verbose", action="count", default=0,
                            help="increases verbosity")
    arg_parser.add_argument("-q", "--quiet", action="store_true",
                            help="quiets down output messages; overrides verbosity options")
    arg_parser.add_argument("--cron", action="store_true",
                            help="cron mode, only logs normal recordings at default verbosity")
    arg_parser.add_argument("--dry-run", action="store_true",
                            help="shows what the program would do")
    arg_parser.add_argument("--version", action="version", default=__version__, version="%%(prog)s %s" % __version__,
                            help="shows the version and exits")

    return arg_parser.parse_args()


def run():
    """run forrest run"""
    # dry-run is a global setting
    global dry_run
    global max_disk_used_percent
    global cutoff_date
    global socket_timeout

    args = parse_args()

    dry_run = args.dry_run
    if dry_run:
        logger.info("DRY RUN No action will be taken.")

    max_disk_used_percent = args.max_used_disk

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
            sync(args.address, destination, grouping, args.priority)
        finally:
            # removes temporary files (if we synced successfully, these are temp files from lost recordings)
            clean_destination(destination, grouping)
    except UserWarning as e:
        logger.warning(e.args[0])
        return 1
    except RuntimeError as e:
        logger.error(e.args[0])
        return 2
    except Exception as e:
        logger.exception(e)
        return 3
    finally:
        if lf_fd:
            unlock(lf_fd)


if __name__ == "__main__":
    run()
