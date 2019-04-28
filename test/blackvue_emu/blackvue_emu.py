import flask

from collections import namedtuple
import datetime
import re


app = flask.Flask(__name__)

# represents a recording: filename and metadata
Recording = namedtuple("Recording", "filename base_filename datetime type direction extension")

# dashcam filename pattern
filename_re = re.compile(r"""(?P<base_filename>(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)
    _(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d))
    _(?P<type>[NEPM])
    (?P<direction>[FR]?)
    \.(?P<extension>(3gf|gps|mp4|thm))""", re.VERBOSE)


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


def generate_recording_filenames(day_range=3):
    """procedurally generates deterministic recording filenames"""
    today = datetime.date.today()

    for date in [today - datetime.timedelta(day) for day in range(0, day_range)]:
        for hour in [9, 18]:
            for minutes in range(10, 25):
                for direction in ["F", "R"]:
                    yield "%04d%02d%02d_%02d%02d%02d_N%s.mp4" % (date.year, date.month, date.day, hour, minutes, 0,
                                                                 direction)


@app.route("/blackvue_vod.cgi", methods=['GET'])
def vod():
    """returns the index of recordings"""
    filenames = [filename for filename in generate_recording_filenames()]
    return flask.render_template("vod.txt", filenames=filenames)


@app.route("/Record/<filename>", methods=['GET'])
def record(filename):
    """serves any file associated to recordings, as long as the name is valid"""
    recording = to_recording(filename)

    if recording:
        filepath = "files/mock.%s" % recording.extension
        return flask.send_file(filepath)
    else:
        return flask.abort(404)
