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
import re
import os
import urllib
import urllib.parse
import urllib.request

# represents a recording: filename and metadata
Recording = namedtuple('Recording', 'filename datetime type direction extension')

# globals
dry_run = None

filename_re = re.compile(r"""^(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)
    _(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d)
    _(?P<type>[NEPM])
    (?P<direction>[FR])
    \.(?P<extension>\w+)$""", re.VERBOSE)


def get_recording(filename):
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
    recording_type = filename_match.group("type")
    recording_direction = filename_match.group("direction")
    recording_extension = filename_match.group("extension")

    return Recording(filename, recording_datetime, recording_type, recording_direction, recording_extension)


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
    url = urllib.parse.urljoin(base_url, "blackvue_vod.cgi")
    request = urllib.request.Request(url)
    response = urllib.request.urlopen(request)

    if response.getcode() != 200:
        raise Exception("bad response")

    charset = response.info().get_param('charset', 'UTF-8')
    file_lines = [x.decode(charset) for x in response.readlines()]

    return get_filenames(file_lines)


def download_file(base_url, filename, destination):
    global dry_run

    filepath = os.path.join(destination, filename)

    if os.path.exists(filepath):
        print("Already downloaded : %s" % filename)
        return

    temp_filepath = os.path.join(destination, ".%s" % filename)
    if os.path.exists(temp_filepath):
        print("Found unfinished download : %s" % temp_filepath)

    url = urllib.parse.urljoin(base_url, "Record/%s" % filename)
    if not dry_run:
        print("Downloading : %s; to : %s..." % (filename, filepath), end="", flush=True)
        urllib.request.urlretrieve(url, temp_filepath)
        os.rename(temp_filepath, filepath)
        print("done.")
    else:
        print("Dry run: would download : %s; to : %s" % (filename, filepath))


def download_recording(base_url, filename, destination):
    download_file(base_url, filename, destination)

    # only normal recordings have gps data
    if filename.endswith("_NF.mp4"):
        base_filename = filename[:-7]

        gps_filename = "%s_N.gps" % base_filename
        download_file(base_url, gps_filename, destination)

        tgf_filename = "%s_N.3gf" % base_filename
        download_file(base_url, tgf_filename, destination)


def get_destination_recordings(destination):
    existing_files = os.listdir(destination)

    return [x for x in [get_recording(x) for x in existing_files] if x is not None]


def prepare_destination(destination, keep_range):
    global dry_run

    # if no destination, creates it
    if not os.path.exists(destination):
        os.makedirs(destination)
        return

    # destination exists, tests if directory
    if not os.path.isdir(destination):
        raise Exception("destination is not a directory : %s" % destination)

    # destination is a directory, tests if writable
    if not os.access(destination, os.W_OK):
        raise Exception("destination directory not writable : %s" % destination)

    if keep_range:
        keep_range_timedelta = datetime.timedelta(days=int(keep_range))

        existing_recordings = get_destination_recordings(destination)

        today = datetime.date.today()
        outdated_recordings = [x for x in existing_recordings
                               if today - x.datetime.date() > keep_range_timedelta]

        for outdated_recording in outdated_recordings:
            outdated_filepath = os.path.join(destination, outdated_recording.filename)
            if not dry_run:
                    os.remove(outdated_filepath)
            else:
                print("Would remove : %s" % outdated_filepath)


def sync(address, destination):
    base_url = "http://%s" % address
    filenames = get_dashcam_filenames(base_url)
    for filename in filenames:
        download_recording(base_url, filename, destination)


def run():
    # dry-run is a global setting
    global dry_run

    arg_parser = argparse.ArgumentParser(description="Synchronizes BlackVue dashcam recordings with a local directory.",
                                         epilog="Bug reports: https://github.com/acolomba/BlackVueSync")
    arg_parser.add_argument("address", metavar="ADDRESS",
                            help="dashcam IP address or name")
    arg_parser.add_argument("-d", "--destination", metavar="DEST",
                            help="destination directory (defaults to current directory)")
    arg_parser.add_argument("-k", "--keep", metavar="KEEP_RANGE",
                            help="keeps recordings in the given range, removing the rest (days)")
    arg_parser.add_argument("--dry-run", help="shows what the program would do", action='store_true')
    args = arg_parser.parse_args()

    dry_run = args.dry_run

    # prepares the local file destination
    destination = args.destination or os.getcwd()
    prepare_destination(destination, args.keep)

    sync(args.address, destination)


if __name__ == "__main__":
    run()
