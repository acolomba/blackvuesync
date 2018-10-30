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
import re
import os
import urllib
import urllib.parse
import urllib.request


def get_filenames(base_url):
    url = urllib.parse.urljoin(base_url, "blackvue_vod.cgi")
    request = urllib.request.Request(url)
    response = urllib.request.urlopen(request)

    if response.getcode() != 200:
        raise Exception("bad response")

    charset = response.info().get_param('charset', 'UTF-8')
    file_lines = [x.decode(charset) for x in response.readlines()]

    filenames = []
    for file_line in file_lines:
        filename_match = re.search("n:/Record/(.*\.mp4),s:1000000\r\n", file_line)
        # the first line is "v:1.00", which won't match, so we skip it
        if filename_match:
            filenames.append(filename_match.group(1))

    return filenames


def download_file(base_url, filename, destination):
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


def sync(address, destination):
    base_url = "http://%s" % address
    filenames = get_filenames(base_url)
    for filename in filenames:
        download_recording(base_url, filename, destination)


def prepare_destination(destination):
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


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(description="Synchronizes BlackVue dashcam recordings with a local directory.",
                                         epilog="Bug reports: https://github.com/acolomba/BlackVueSync")
    arg_parser.add_argument("address", help="dashcam IP address or name")
    arg_parser.add_argument("-d", "--destination", metavar="DEST",
                            help="destination directory (defaults to current directory)")
    arg_parser.add_argument("--dry-run", help="", action='store_true')
    args = arg_parser.parse_args()

    # dry-run is a global setting
    dry_run = args.dry_run

    # prepares the local file destination
    destination = args.destination or os.getcwd()
    prepare_destination(destination)

    sync(args.address, destination)
