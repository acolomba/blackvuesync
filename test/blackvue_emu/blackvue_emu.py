"""emulates a the web service exposed by blackvue dashcams"""

from __future__ import annotations

import datetime
import re
from collections.abc import Generator
from dataclasses import dataclass

import flask

app = flask.Flask(__name__)


# represents a recording: filename and metadata
@dataclass(frozen=True)
class Recording:
    filename: str
    base_filename: str
    datetime: datetime.datetime
    type: str
    direction: str
    extension: str


# dashcam filename pattern
filename_re = re.compile(
    r"""(?P<base_filename>(?P<year>\d\d\d\d)(?P<month>\d\d)(?P<day>\d\d)
    _(?P<hour>\d\d)(?P<minute>\d\d)(?P<second>\d\d))
    _(?P<type>[NEPMIOATBRXG])
    (?P<direction>[FR]?)
    (?P<upload>[LS]?)
    \.(?P<extension>(3gf|gps|mp4|thm))""",
    re.VERBOSE,
)


def to_recording(filename: str) -> Recording | None:
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
    recording_type = filename_match.group("type")
    recording_direction = filename_match.group("direction")
    recording_extension = filename_match.group("extension")

    return Recording(
        filename,
        recording_base_filename,
        recording_datetime,
        recording_type,
        recording_direction,
        recording_extension,
    )


def generate_recording_filenames(
    day_range: int = 3, day_offset: int = 0
) -> Generator[str, None, None]:
    """procedurally generates deterministic recording filenames"""
    today = datetime.date.today() - datetime.timedelta(day_offset)

    for date in [today - datetime.timedelta(day) for day in range(0, day_range)]:
        for hour in [9, 18]:
            for minutes in range(10, 25, 3):
                for direction in ["F", "R"]:
                    yield f"{date.year:04d}{date.month:02d}{date.day:02d}_{hour:02d}{minutes:02d}00_N{direction}.mp4"
            for minutes in range(11, 25, 3):
                for direction in ["F", "R"]:
                    yield f"{date.year:04d}{date.month:02d}{date.day:02d}_{hour:02d}{minutes:02d}00_E{direction}.mp4"
            for minutes in range(13, 25, 3):
                for direction in ["F", "R"]:
                    yield f"{date.year:04d}{date.month:02d}{date.day:02d}_{hour:02d}{minutes:02d}00_A{direction}L.mp4"


@app.route("/blackvue_vod.cgi", methods=["GET"])
def vod() -> str:
    """returns the index of recordings"""
    filenames = list(generate_recording_filenames())
    return flask.render_template("vod.txt", filenames=filenames)  # type: ignore[no-any-return]


@app.route("/Record/<filename>", methods=["GET"])
def record(filename: str) -> flask.Response:
    """serves any file associated to recordings, as long as the name is valid"""
    if recording := to_recording(filename):
        filepath = f"files/mock.{recording.extension}"
        return flask.send_file(filepath)
    else:
        return flask.abort(404)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="BlackVue dashcam emulator")
    parser.add_argument(
        "--port", type=int, default=5000, help="Port to run on (default: 5000)"
    )
    args = parser.parse_args()
    app.run(host="0.0.0.0", port=args.port)
