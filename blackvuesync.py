#!/usr/bin/env python3

# Copyright 2018 Alessandro Colomba (https://github.com/acolomba)
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

import argparse
import datetime
from collections import namedtuple
import fcntl
import logging
import re
import os
import shutil
import stat
import urllib
import urllib.parse
import urllib.request


# logging
logging.basicConfig(format="%(asctime)s: %(levelname)s %(message)s")

# root logger
logger = logging.getLogger()

# the cron logger remains active in cron mode
cron_logger = logging.getLogger("cron")


def set_verbosity(verbosity, is_cron_mode):
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


# indicator that we're doing a dry run
dry_run = None

# max disk usage percent
max_disk_used_percent = None

# keep and cutoff date; only recordings from this date on are downloaded and kept
keep_re = re.compile(r"""(?P<range>\d+)(?P<unit>[dw]?)""", re.VERBOSE)
cutoff_date = None
today = datetime.date.today()


def calc_cutoff_date(keep):
    global today

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
Recording = namedtuple("Recording", "filename base_filename datetime type direction extension")


filename_re = re.compile(r"""(?P<base_filename>(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)
    _(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d))
    _(?P<type>[NEPM])
    (?P<direction>[FR])
    \.(?P<extension>\w+)""", re.VERBOSE)


def to_recording(filename):
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
    recording_type = filename_match.group("type")
    recording_direction = filename_match.group("direction")
    recording_extension = filename_match.group("extension")

    return Recording(filename, recording_base_filename, recording_datetime, recording_type, recording_direction,
                     recording_extension)


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
    """gets the recording filenames from the dashcam at the """
    try:
        url = urllib.parse.urljoin(base_url, "blackvue_vod.cgi")
        request = urllib.request.Request(url)
        response = urllib.request.urlopen(request)
    except urllib.error.URLError as e:
        raise UserWarning("Cannot communicate with dashcam at address : %s; error : %s" % (base_url, e))

    response_status_code = response.getcode()
    if response_status_code != 200:
        raise RuntimeError("Error response from : %s ; status code : %s" % (base_url, response_status_code))

    charset = response.info().get_param("charset", "UTF-8")
    file_lines = [x.decode(charset) for x in response.readlines()]

    return get_filenames(file_lines)


def download_file(base_url, filename, destination):
    """downloads a file from the dashcam to the destination directory; returns whether data was transferred"""
    global dry_run

    filepath = os.path.join(destination, filename)

    if os.path.exists(filepath):
        logger.debug("Ignoring already downloaded recording : %s", filename)
        return False

    temp_filepath = os.path.join(destination, ".%s" % filename)
    if os.path.exists(temp_filepath):
        logger.debug("Found incomplete download : %s", temp_filepath)

    url = urllib.parse.urljoin(base_url, "Record/%s" % filename)
    if not dry_run:
        urllib.request.urlretrieve(url, temp_filepath)
        os.rename(temp_filepath, filepath)
        logger.debug("Downloaded file : %s", filename)
    else:
        logger.debug("DRY RUN Would download file : %s", filename)

    return True


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

    # downloads the video recording
    filename = recording.filename
    transferred = download_file(base_url, filename, destination)

    # recording logger, depends on type of recording
    recording_logger = logger

    # downloads the gps data for normal recordings
    if recording.type == "N":
        # going to log in cron mode
        recording_logger = cron_logger

        gps_filename = "%s_N.gps" % recording.base_filename
        transferred |= download_file(base_url, gps_filename, destination)

        tgf_filename = "%s_N.3gf" % recording.base_filename
        transferred |= download_file(base_url, tgf_filename, destination)

    # logs if data was transferred (or would have been)
    if transferred:
        if not dry_run:
            recording_logger.info("Downloaded recording : %s", recording.filename)
        else:
            recording_logger.info("DRY RUN Would download recording : %s", recording.filename)


def get_destination_recordings(destination):
    """reads files from the destination directory and returns them as recording structures"""
    existing_files = os.listdir(destination)

    return [x for x in [to_recording(x) for x in existing_files] if x is not None]


def get_outdated_recordings(recordings):
    """returns the recordings prior to the cutoff date"""
    global cutoff_date

    return [] if cutoff_date is None else [x for x in recordings if x.datetime.date() < cutoff_date]


def get_current_recordings(recordings):
    """returns the recordings that are after or on the cutoff date"""
    global cutoff_date
    return recordings if cutoff_date is None else [x for x in recordings if x.datetime.date() >= cutoff_date]


def verify_destination(destination):
    """ensures the destination directory exists, creates if not, verifies it's writeable"""
    # if no destination, creates it
    if not os.path.exists(destination):
        os.makedirs(destination)
        return

    # destination exists, tests if directory
    if not os.path.isdir(destination):
        raise RuntimeError("destination is not a directory : %s" % destination)

    # destination is a directory, tests if writable
    if not os.access(destination, os.W_OK):
        raise RuntimeError("destination directory not writable : %s" % destination)


def prepare_destination(destination):
    """prepares the destination, esuring it's valid and removing excess recordings"""
    global dry_run
    global cutoff_date

    if cutoff_date:
        existing_recordings = get_destination_recordings(destination)
        outdated_recordings = get_outdated_recordings(existing_recordings)

        for outdated_recording in outdated_recordings:
            outdated_filepath = os.path.join(destination, outdated_recording.filename)
            if not dry_run:
                logger.info("Removing outdated recording : %s", outdated_recording.filename)
                os.remove(outdated_filepath)
            else:
                logger.info("DRY RUN Would remove outdated recording : %s", outdated_recording.filename)


def sync(address, destination):
    """synchronizes the recordings at the dashcam address with the destination directory"""
    prepare_destination(destination)

    base_url = "http://%s" % address
    dashcam_filenames = get_dashcam_filenames(base_url)
    dashcam_recordings = [to_recording(x) for x in dashcam_filenames]
    current_dashcam_recordings = get_current_recordings(dashcam_recordings)

    for recording in current_dashcam_recordings:
        download_recording(base_url, recording, destination)


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
    arg_parser = argparse.ArgumentParser(description="Synchronizes BlackVue dashcam recordings with a local directory.",
                                         epilog="Bug reports: https://github.com/acolomba/BlackVueSync")
    arg_parser.add_argument("address", metavar="ADDRESS",
                            help="dashcam IP address or name")
    arg_parser.add_argument("-d", "--destination", metavar="DEST",
                            help="destination directory (defaults to c  urrent directory)")
    arg_parser.add_argument("-k", "--keep", metavar="KEEP_RANGE",
                            help="""keeps recordings in the given range, removing the rest; defaults to days, but can
                            suffix with d, w for days or weeks respectively""")
    arg_parser.add_argument("-u", "--max-used-disk", metavar="DISK_USAGE_PERCENT", default=90,
                            type=int, choices=range(5, 99),
                            help="will not exceed more than DISK_USAGE_PERCENT used disk space; defaults to 90%%")
    arg_parser.add_argument("-v", "--verbose", action="count", default=0,
                            help="increases verbosity")
    arg_parser.add_argument("-q", "--quiet", action="store_true",
                            help="quiets down output messages; overrides verbosity options")
    arg_parser.add_argument("--cron", action="store_true",
                            help="cron mode, only logs normal recordings at default verbosity")
    arg_parser.add_argument("--dry-run", action="store_true",
                            help="shows what the program would do")
    arg_parser.add_argument("--version", action="version", version="%(prog)s 0.x",
                            help="shows this script's version and exists")

    return arg_parser.parse_args()


def run():
    # dry-run is a global setting
    global dry_run
    global max_disk_used_percent
    global cutoff_date

    args = parse_args()

    dry_run = args.dry_run
    if dry_run:
        logger.info("DRY RUN No action will be taken.")

    max_disk_used_percent = args.max_used_disk

    set_verbosity(-1 if args.quiet else args.verbose, args.cron)

    # lock file file descriptor
    lf_fd = None

    try:
        if args.keep:
            cutoff_date = calc_cutoff_date(args.keep)
            logger.info("Recording cutoff date : %s", cutoff_date)

        # prepares the local file destination
        destination = args.destination or os.getcwd()
        verify_destination(destination)

        lf_fd = lock(destination)

        sync(args.address, destination)
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
