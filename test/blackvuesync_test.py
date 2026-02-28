from __future__ import annotations

import argparse
import datetime
import errno
import fcntl
import glob
import os
import socket
import tempfile
import time
import unittest.mock
import urllib.error
import urllib.request
from typing import Any

import pytest

import blackvuesync


@pytest.mark.parametrize(
    "filename, expected_recording",
    [
        (
            "20181029_131513_NF.mp4",
            blackvuesync.Recording(
                "20181029_131513_NF.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "N",
                "F",
            ),
        ),
        (
            "20181029_131513_EF.mp4",
            blackvuesync.Recording(
                "20181029_131513_EF.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "E",
                "F",
            ),
        ),
        (
            "20181029_131513_PF.mp4",
            blackvuesync.Recording(
                "20181029_131513_PF.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "P",
                "F",
            ),
        ),
        (
            "20181029_131513_MF.mp4",
            blackvuesync.Recording(
                "20181029_131513_MF.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "M",
                "F",
            ),
        ),
        (
            "20181029_131513_NR.mp4",
            blackvuesync.Recording(
                "20181029_131513_NR.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "N",
                "R",
            ),
        ),
        (
            "20181029_131513_ER.mp4",
            blackvuesync.Recording(
                "20181029_131513_ER.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "E",
                "R",
            ),
        ),
        (
            "20181029_131513_PR.mp4",
            blackvuesync.Recording(
                "20181029_131513_PR.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "P",
                "R",
            ),
        ),
        (
            "20181029_131513_MR.mp4",
            blackvuesync.Recording(
                "20181029_131513_MR.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "M",
                "R",
            ),
        ),
        (
            "20181029_131513_NF.mp4",
            blackvuesync.Recording(
                "20181029_131513_NF.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "N",
                "F",
            ),
        ),
        (
            "20181029_131513_NO.mp4",
            blackvuesync.Recording(
                "20181029_131513_NO.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "N",
                "O",
            ),
        ),
        (
            "20181029_131513_EO.mp4",
            blackvuesync.Recording(
                "20181029_131513_EO.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "E",
                "O",
            ),
        ),
        (
            "20181029_131513_DF.mp4",
            blackvuesync.Recording(
                "20181029_131513_DF.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "D",
                "F",
            ),
        ),
        (
            "20181029_131513_LI.mp4",
            blackvuesync.Recording(
                "20181029_131513_LI.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "L",
                "I",
            ),
        ),
        (
            "20181029_131513_YF.mp4",
            blackvuesync.Recording(
                "20181029_131513_YF.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "Y",
                "F",
            ),
        ),
        (
            "20181029_131513_FF.mp4",
            blackvuesync.Recording(
                "20181029_131513_FF.mp4",
                "20181029_131513",
                None,
                datetime.datetime(2018, 10, 29, 13, 15, 13),
                "F",
                "F",
            ),
        ),
        ("20181029_131513_NX.mp4", None),
        ("20181029_131513_PX.mp4", None),
        ("20181029_131513_PF.mp3", None),
        ("invalid.gif", None),
    ],
)
def test_to_recording(
    filename: str, expected_recording: blackvuesync.Recording | None
) -> None:
    recording = blackvuesync.to_recording(filename, "none")

    assert expected_recording == recording


@pytest.mark.parametrize(
    "filename, expected_recording",
    [
        (
            "20181029_131513_NFL.mp4",
            blackvuesync.DownloadedRecording(
                "20181029_131513", None, datetime.datetime(2018, 10, 29, 13, 15, 13)
            ),
        ),
        (
            "20181029_131513_EF.thm",
            blackvuesync.DownloadedRecording(
                "20181029_131513", None, datetime.datetime(2018, 10, 29, 13, 15, 13)
            ),
        ),
        (
            "20181029_131513_P.3gf",
            blackvuesync.DownloadedRecording(
                "20181029_131513", None, datetime.datetime(2018, 10, 29, 13, 15, 13)
            ),
        ),
        (
            "20181029_131513_M.gps",
            blackvuesync.DownloadedRecording(
                "20181029_131513", None, datetime.datetime(2018, 10, 29, 13, 15, 13)
            ),
        ),
        (
            "20181029_131513_JUNK.mp4",
            blackvuesync.DownloadedRecording(
                "20181029_131513", None, datetime.datetime(2018, 10, 29, 13, 15, 13)
            ),
        ),
        ("20181029_131513.mp4", None),
        ("invalid.gif", None),
    ],
)
def test_to_downloaded_recording(
    filename: str, expected_recording: blackvuesync.DownloadedRecording | None
) -> None:
    recording = blackvuesync.to_downloaded_recording(filename, "none")

    assert expected_recording == recording


@pytest.mark.parametrize(
    "recording_datetime, expected_daily_group_name, expected_weekly_group_name, expected_monthly_group_name, expected_yearly_group_name",
    [
        (
            datetime.datetime(2019, 2, 19, 13, 15, 13),
            "2019-02-19",
            "2019-02-18",
            "2019-02",
            "2019",
        )
    ],
)
def test_get_group_name(
    recording_datetime: datetime.datetime,
    expected_daily_group_name: str,
    expected_weekly_group_name: str,
    expected_monthly_group_name: str,
    expected_yearly_group_name: str,
) -> None:
    assert expected_daily_group_name == blackvuesync.get_group_name(
        recording_datetime, "daily"
    )
    assert expected_weekly_group_name == blackvuesync.get_group_name(
        recording_datetime, "weekly"
    )
    assert expected_monthly_group_name == blackvuesync.get_group_name(
        recording_datetime, "monthly"
    )
    assert expected_yearly_group_name == blackvuesync.get_group_name(
        recording_datetime, "yearly"
    )


@pytest.mark.parametrize(
    "keep, expected_cutoff_date",
    [
        ("1d", datetime.datetime(2018, 10, 29)),
        ("2d", datetime.datetime(2018, 10, 28)),
        ("1w", datetime.datetime(2018, 10, 23)),
        ("2w", datetime.datetime(2018, 10, 16)),
    ],
)
def test_calc_cutoff_date(keep: str, expected_cutoff_date: datetime.datetime) -> None:
    try:
        blackvuesync.today = datetime.datetime(2018, 10, 30)

        cutoff_date = blackvuesync.calc_cutoff_date(keep)

        assert expected_cutoff_date == cutoff_date
    finally:
        blackvuesync.today = datetime.date.today()


@pytest.mark.parametrize(
    "priority, filenames, expected_sorted_filenames",
    [
        (
            "date",
            [
                "20190219_104220_NF.mp4",
                "20190219_104220_NR.mp4",
                "20190219_104619_MF.mp4",
                "20190219_104619_MR.mp4",
                "20190219_223201_NF.mp4",
                "20190219_223201_NR.mp4",
                "20190219_224918_PF.mp4",
                "20190219_224918_PR.mp4",
                "20190224_172246_EF.mp4",
                "20190224_172246_ER.mp4",
                "20190224_172341_EF.mp4",
                "20190224_172341_ER.mp4",
            ],
            [
                "20190219_104220_NF.mp4",
                "20190219_104220_NR.mp4",
                "20190219_104619_MF.mp4",
                "20190219_104619_MR.mp4",
                "20190219_223201_NF.mp4",
                "20190219_223201_NR.mp4",
                "20190219_224918_PF.mp4",
                "20190219_224918_PR.mp4",
                "20190224_172246_EF.mp4",
                "20190224_172246_ER.mp4",
                "20190224_172341_EF.mp4",
                "20190224_172341_ER.mp4",
            ],
        ),
        (
            "rdate",
            [
                "20190219_104220_NF.mp4",
                "20190219_104220_NR.mp4",
                "20190219_104619_MF.mp4",
                "20190219_104619_MR.mp4",
                "20190219_223201_NF.mp4",
                "20190219_223201_NR.mp4",
                "20190219_224918_PF.mp4",
                "20190219_224918_PR.mp4",
                "20190224_172246_EF.mp4",
                "20190224_172246_ER.mp4",
                "20190224_172341_EF.mp4",
                "20190224_172341_ER.mp4",
            ],
            [
                "20190224_172341_EF.mp4",
                "20190224_172341_ER.mp4",
                "20190224_172246_EF.mp4",
                "20190224_172246_ER.mp4",
                "20190219_224918_PF.mp4",
                "20190219_224918_PR.mp4",
                "20190219_223201_NF.mp4",
                "20190219_223201_NR.mp4",
                "20190219_104619_MF.mp4",
                "20190219_104619_MR.mp4",
                "20190219_104220_NF.mp4",
                "20190219_104220_NR.mp4",
            ],
        ),
        (
            "type",
            [
                "20190219_104220_NF.mp4",
                "20190219_104220_NR.mp4",
                "20190219_104619_MF.mp4",
                "20190219_104619_MR.mp4",
                "20190219_223201_NF.mp4",
                "20190219_223201_NR.mp4",
                "20190219_224918_PF.mp4",
                "20190219_224918_PR.mp4",
                "20190224_172246_EF.mp4",
                "20190224_172246_ER.mp4",
                "20190224_172341_EF.mp4",
                "20190224_172341_ER.mp4",
            ],
            [
                "20190219_104619_MF.mp4",
                "20190219_104619_MR.mp4",
                "20190224_172246_EF.mp4",
                "20190224_172246_ER.mp4",
                "20190224_172341_EF.mp4",
                "20190224_172341_ER.mp4",
                "20190219_104220_NF.mp4",
                "20190219_104220_NR.mp4",
                "20190219_223201_NF.mp4",
                "20190219_223201_NR.mp4",
                "20190219_224918_PF.mp4",
                "20190219_224918_PR.mp4",
            ],
        ),
    ],
)
def test_sort_recordings(
    priority: str, filenames: list[str], expected_sorted_filenames: list[str]
) -> None:
    recordings = [
        r
        for r in [blackvuesync.to_recording(f, "none") for f in filenames]
        if r is not None
    ]
    expected_sorted_recordings = [
        r
        for r in [
            blackvuesync.to_recording(f, "none") for f in expected_sorted_filenames
        ]
        if r is not None
    ]

    # copy
    sorted_recordings = recordings.copy()
    blackvuesync.sort_recordings(sorted_recordings, priority)

    assert expected_sorted_recordings == sorted_recordings


@pytest.mark.parametrize(
    "duration, expected_timedelta",
    [
        ("1s", datetime.timedelta(seconds=1)),
        ("30s", datetime.timedelta(seconds=30)),
        ("1h", datetime.timedelta(hours=1)),
        ("12h", datetime.timedelta(hours=12)),
        ("1d", datetime.timedelta(days=1)),
        ("7d", datetime.timedelta(days=7)),
        ("1w", datetime.timedelta(weeks=1)),
        ("2w", datetime.timedelta(weeks=2)),
        ("3", datetime.timedelta(days=3)),
    ],
)
def test_parse_duration(duration: str, expected_timedelta: datetime.timedelta) -> None:
    assert expected_timedelta == blackvuesync.parse_duration(duration)


@pytest.mark.parametrize(
    "duration",
    ["0s", "0d", "0h", "0w", "abc", ""],
)
def test_parse_duration_invalid(duration: str) -> None:
    with pytest.raises(RuntimeError):
        blackvuesync.parse_duration(duration)


@pytest.mark.parametrize(
    "keep",
    ["1s", "1h", "12h", "30s"],
)
def test_calc_cutoff_date_rejects_sub_day_units(keep: str) -> None:
    """verifies that --keep rejects sub-day units (s, h)."""
    with pytest.raises(RuntimeError, match="does not support unit"):
        blackvuesync.calc_cutoff_date(keep)


class TestFailedMarker:
    """tests for failure marker functionality."""

    def test_get_failed_marker_filepath_no_grouping(self) -> None:
        """verifies the marker filepath without grouping."""
        filepath = blackvuesync.get_failed_marker_filepath(
            "/dest", None, "20181029_131513_NF.mp4"
        )
        assert filepath == "/dest/20181029_131513_NF.mp4.failed"

    def test_get_failed_marker_filepath_with_grouping(self) -> None:
        """verifies the marker filepath with grouping."""
        filepath = blackvuesync.get_failed_marker_filepath(
            "/dest", "2018-10-29", "20181029_131513_NF.mp4"
        )
        assert filepath == "/dest/2018-10-29/20181029_131513_NF.mp4.failed"

    def test_mark_download_failed_creates_marker(self) -> None:
        """verifies that marking a download as failed creates a marker file."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"

            blackvuesync.mark_download_failed(dest, None, filename)

            marker_filepath = blackvuesync.get_failed_marker_filepath(
                dest, None, filename
            )
            assert os.path.exists(marker_filepath)

            with open(marker_filepath, encoding="utf-8") as f:
                content = f.read()

            # verifies content is a valid ISO timestamp
            datetime.datetime.fromisoformat(content)

    def test_remove_download_failed_marker(self) -> None:
        """verifies that removing a marker works."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"

            blackvuesync.mark_download_failed(dest, None, filename)
            marker_filepath = blackvuesync.get_failed_marker_filepath(
                dest, None, filename
            )
            assert os.path.exists(marker_filepath)

            blackvuesync.remove_download_failed_marker(dest, None, filename)
            assert not os.path.exists(marker_filepath)

    def test_remove_download_failed_marker_nonexistent(self) -> None:
        """verifies that removing a nonexistent marker does not error."""
        with tempfile.TemporaryDirectory() as dest:
            blackvuesync.remove_download_failed_marker(
                dest, None, "20181029_131513_NF.mp4"
            )

    def test_is_download_blocked_by_failure_no_marker(self) -> None:
        """verifies that downloads are not blocked when no marker exists."""
        with tempfile.TemporaryDirectory() as dest:
            assert not blackvuesync.is_download_blocked_by_failure(
                dest, None, "20181029_131513_NF.mp4"
            )

    def test_is_download_blocked_by_failure_recent_marker(self) -> None:
        """verifies that downloads are blocked when a recent marker exists."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original = blackvuesync.retry_failed_after

            try:
                blackvuesync.retry_failed_after = datetime.timedelta(days=1)
                blackvuesync.mark_download_failed(dest, None, filename)

                assert blackvuesync.is_download_blocked_by_failure(dest, None, filename)
            finally:
                blackvuesync.retry_failed_after = original

    def test_is_download_blocked_by_failure_stale_marker(self) -> None:
        """verifies that downloads are not blocked when the marker is stale."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original = blackvuesync.retry_failed_after

            try:
                marker_filepath = blackvuesync.get_failed_marker_filepath(
                    dest, None, filename
                )
                old_time = datetime.datetime.now() - datetime.timedelta(hours=25)
                with open(marker_filepath, "w", encoding="utf-8") as f:
                    f.write(old_time.isoformat())

                blackvuesync.retry_failed_after = datetime.timedelta(days=1)

                assert not blackvuesync.is_download_blocked_by_failure(
                    dest, None, filename
                )
            finally:
                blackvuesync.retry_failed_after = original

    def test_is_download_blocked_by_failure_corrupted_marker(self) -> None:
        """verifies that corrupted markers are treated as stale."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"

            marker_filepath = blackvuesync.get_failed_marker_filepath(
                dest, None, filename
            )
            with open(marker_filepath, "w", encoding="utf-8") as f:
                f.write("not a valid timestamp")

            assert not blackvuesync.is_download_blocked_by_failure(dest, None, filename)

    def test_marker_in_grouping_directory(self) -> None:
        """verifies markers work within grouping subdirectories."""
        with tempfile.TemporaryDirectory() as dest:
            group_name = "2018-10-29"
            filename = "20181029_131513_NF.mp4"
            os.makedirs(os.path.join(dest, group_name))

            blackvuesync.mark_download_failed(dest, group_name, filename)

            marker_filepath = blackvuesync.get_failed_marker_filepath(
                dest, group_name, filename
            )
            assert os.path.exists(marker_filepath)
            assert group_name in marker_filepath

            original = blackvuesync.retry_failed_after
            try:
                blackvuesync.retry_failed_after = datetime.timedelta(days=1)
                assert blackvuesync.is_download_blocked_by_failure(
                    dest, group_name, filename
                )
            finally:
                blackvuesync.retry_failed_after = original

            blackvuesync.remove_download_failed_marker(dest, group_name, filename)
            assert not os.path.exists(marker_filepath)

    def test_mark_download_failed_refreshes_timestamp(self) -> None:
        """verifies that re-marking a failed download updates the timestamp."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"

            blackvuesync.mark_download_failed(dest, None, filename)

            marker_filepath = blackvuesync.get_failed_marker_filepath(
                dest, None, filename
            )
            with open(marker_filepath, encoding="utf-8") as f:
                first_timestamp = f.read().strip()

            time.sleep(0.01)
            blackvuesync.mark_download_failed(dest, None, filename)

            with open(marker_filepath, encoding="utf-8") as f:
                second_timestamp = f.read().strip()

            assert second_timestamp > first_timestamp

    def test_dry_run_ignores_failure_markers(self) -> None:
        """verifies that dry-run reports files as would-download even with failure markers."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_dry_run = blackvuesync.dry_run
            original_retry = blackvuesync.retry_failed_after

            try:
                blackvuesync.retry_failed_after = datetime.timedelta(days=1)
                blackvuesync.mark_download_failed(dest, None, filename)

                # enables dry-run mode
                blackvuesync.dry_run = True

                downloaded, _ = blackvuesync.download_file(
                    "http://127.0.0.1:0", filename, dest, None
                )

                # dry-run returns True (would download) despite failure marker
                assert downloaded is True
            finally:
                blackvuesync.dry_run = original_dry_run
                blackvuesync.retry_failed_after = original_retry

    def test_retention_removes_failed_markers(self) -> None:
        """verifies that retention cleanup removes .failed markers alongside recordings."""
        with tempfile.TemporaryDirectory() as dest:
            # creates an outdated recording file and its .failed marker
            base_filename = "20181029_131513"
            mp4_file = os.path.join(dest, f"{base_filename}_NF.mp4")
            thm_file = os.path.join(dest, f"{base_filename}_NF.thm")
            failed_marker = os.path.join(dest, f"{base_filename}_NF.mp4.failed")

            for filepath in [mp4_file, thm_file]:
                with open(filepath, "w") as f:
                    f.write("mock")
            with open(failed_marker, "w") as f:
                f.write(datetime.datetime.now().isoformat())

            # verifies the retention glob matches .failed files
            outdated_glob = os.path.join(dest, f"{base_filename}_[NEPMIOATBRXGDLYF]*.*")
            matched_files = glob.glob(outdated_glob)
            matched_names = {os.path.basename(f) for f in matched_files}

            assert f"{base_filename}_NF.mp4" in matched_names
            assert f"{base_filename}_NF.thm" in matched_names
            assert f"{base_filename}_NF.mp4.failed" in matched_names


@pytest.mark.parametrize(
    "value, expected",
    [
        ("t", {"t"}),
        ("3", {"3"}),
        ("g", {"g"}),
        ("t3g", {"t", "3", "g"}),
        ("3g", {"3", "g"}),
        ("tg", {"t", "g"}),
        ("t3", {"t", "3"}),
        ("ttt", {"t"}),
        ("t3gt3g", {"t", "3", "g"}),
    ],
)
def test_parse_skip_metadata(value: str, expected: set[str]) -> None:
    assert blackvuesync.parse_skip_metadata(value) == expected


@pytest.mark.parametrize("value", ["x", "t3x", "abc", "T", "mp4"])
def test_parse_skip_metadata_invalid(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        blackvuesync.parse_skip_metadata(value)


@pytest.mark.parametrize(
    "value, expected",
    [
        ("PF", ("PF",)),
        ("P", ("P",)),
        ("PF,PR", ("PF", "PR")),
        ("PF, PR", ("PF", "PR")),
        ("PF , PR", ("PF", "PR")),
        ("P,NF", ("P", "NF")),
        ("N", ("N",)),
        ("NF,NR,NI,NO", ("NF", "NR", "NI", "NO")),
        ("", ()),
        ("  ", ()),
    ],
)
def test_parse_filter(value: str, expected: tuple[str, ...]) -> None:
    assert blackvuesync.parse_filter(value) == expected


@pytest.mark.parametrize(
    "value",
    ["Z", "ZZ", "PX", "ABC", "pf", "1F"],
)
def test_parse_filter_invalid(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        blackvuesync.parse_filter(value)


def _recording(rec_type: str, direction: str) -> blackvuesync.Recording:
    """creates a minimal Recording for filter tests"""
    return blackvuesync.Recording(
        filename=f"20250101_120000_{rec_type}{direction}.mp4",
        base_filename="20250101_120000",
        group_name=None,
        datetime=datetime.datetime(2025, 1, 1, 12, 0, 0),
        type=rec_type,
        direction=direction,
    )


class TestApplyRecordingFilters:
    """tests for apply_recording_filters"""

    def test_no_filters_returns_all(self) -> None:
        recordings = [_recording("N", "F"), _recording("P", "R")]
        result = blackvuesync.apply_recording_filters(recordings, None, None)
        assert result == recordings

    def test_include_type_only(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("N", "R"),
            _recording("P", "F"),
        ]
        result = blackvuesync.apply_recording_filters(recordings, ("N",), None)
        assert result == [recordings[0], recordings[1]]

    def test_include_type_and_direction(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("N", "R"),
            _recording("P", "F"),
        ]
        result = blackvuesync.apply_recording_filters(recordings, ("NF",), None)
        assert result == [recordings[0]]

    def test_include_multiple_codes(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("P", "F"),
            _recording("E", "F"),
        ]
        result = blackvuesync.apply_recording_filters(recordings, ("N", "PF"), None)
        assert result == [recordings[0], recordings[1]]

    def test_exclude_type_only(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("P", "F"),
            _recording("E", "F"),
        ]
        result = blackvuesync.apply_recording_filters(recordings, None, ("P",))
        assert result == [recordings[0], recordings[2]]

    def test_exclude_type_and_direction(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("N", "R"),
        ]
        result = blackvuesync.apply_recording_filters(recordings, None, ("NR",))
        assert result == [recordings[0]]

    def test_include_and_exclude_combined(self) -> None:
        recordings = [
            _recording("N", "F"),
            _recording("N", "R"),
            _recording("P", "F"),
        ]
        result = blackvuesync.apply_recording_filters(recordings, ("N",), ("NR",))
        assert result == [recordings[0]]

    def test_empty_result(self) -> None:
        recordings = [_recording("N", "F")]
        result = blackvuesync.apply_recording_filters(recordings, ("P",), None)
        assert result == []

    def test_empty_include_returns_all(self) -> None:
        recordings = [_recording("N", "F"), _recording("P", "R")]
        result = blackvuesync.apply_recording_filters(recordings, (), None)
        assert result == recordings

    def test_empty_exclude_returns_all(self) -> None:
        recordings = [_recording("N", "F"), _recording("P", "R")]
        result = blackvuesync.apply_recording_filters(recordings, None, ())
        assert result == recordings


def test_download_file_streams_response_in_chunks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verifies downloads stream body data using the configured chunk size."""

    read_sizes: list[int] = []

    class FakeResponse:
        def __init__(self) -> None:
            self._chunks = [b"abc", b"def", b""]

        def getcode(self) -> int:
            return 200

        def info(self) -> dict[str, str]:
            return {"Content-Length": "6"}

        def read(self, size: int = -1) -> bytes:
            if size == -1:
                raise AssertionError("read() must be called with a chunk size")
            read_sizes.append(size)
            return self._chunks.pop(0)

        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    with tempfile.TemporaryDirectory() as destination:
        monkeypatch.setattr(urllib.request, "urlopen", lambda _request: FakeResponse())
        monkeypatch.setattr(blackvuesync, "dry_run", False)

        downloaded, _ = blackvuesync.download_file(
            "http://127.0.0.1:1",
            "20181029_131513_NF.mp4",
            destination,
            None,
        )

        assert downloaded is True
        assert all(s == blackvuesync.DOWNLOAD_CHUNK_SIZE for s in read_sizes)

        output_path = os.path.join(destination, "20181029_131513_NF.mp4")
        with open(output_path, "rb") as f:
            assert f.read() == b"abcdef"


def test_lock_closes_fd_when_lock_acquisition_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verifies lock closes the file descriptor when non-blocking lock fails due to contention."""
    opened_fd = 123
    close_calls: list[int] = []

    monkeypatch.setattr(os, "open", lambda *_args: opened_fd)
    monkeypatch.setattr(os, "close", lambda fd: close_calls.append(fd))

    def fake_lockf(_fd: int, _operation: int) -> None:
        raise OSError(errno.EAGAIN, "lock busy")

    monkeypatch.setattr(fcntl, "lockf", fake_lockf)

    with pytest.raises(UserWarning):
        blackvuesync.lock("/tmp")

    assert close_calls == [opened_fd]


def test_main_unlocks_fd_zero(monkeypatch: pytest.MonkeyPatch) -> None:
    """verifies main unlocks the lock file descriptor when it is zero."""
    unlock_calls: list[int] = []

    args = argparse.Namespace(
        address="127.0.0.1",
        destination="/tmp",
        grouping="none",
        keep=None,
        priority="date",
        include=None,
        exclude=None,
        max_used_disk=90,
        timeout=1.0,
        retry_failed_after="1d",
        retry_count=3,
        skip_metadata=set(),
        verbose=0,
        quiet=False,
        cron=False,
        dry_run=False,
        affinity_key=None,
    )

    monkeypatch.setattr(blackvuesync, "parse_args", lambda: args)
    monkeypatch.setattr(blackvuesync, "ensure_destination", lambda _destination: None)
    monkeypatch.setattr(blackvuesync, "lock", lambda _destination: 0)
    monkeypatch.setattr(
        blackvuesync,
        "sync",
        lambda _address, _destination, _grouping, _priority, _include, _exclude: None,
    )
    monkeypatch.setattr(
        blackvuesync, "clean_destination", lambda _destination, _grouping: None
    )
    monkeypatch.setattr(
        blackvuesync, "unlock", lambda lf_fd: unlock_calls.append(lf_fd)
    )

    assert blackvuesync.main() == 0
    assert unlock_calls == [0]


def test_lock_raises_runtime_error_for_non_contention_os_error(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verifies lock raises RuntimeError when lockf fails for reasons other than contention."""
    close_calls: list[int] = []

    monkeypatch.setattr(os, "open", lambda *_args: 42)
    monkeypatch.setattr(os, "close", lambda fd: close_calls.append(fd))

    def fake_lockf(_fd: int, _operation: int) -> None:
        raise OSError(errno.ENOLCK, "no locks available")

    monkeypatch.setattr(fcntl, "lockf", fake_lockf)

    with pytest.raises(RuntimeError, match="Could not acquire lock"):
        blackvuesync.lock("/tmp")

    assert close_calls == [42]


def test_lock_closes_fd_zero_when_lock_acquisition_fails(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verifies lock closes file descriptor 0 when non-blocking lock fails."""
    close_calls: list[int] = []

    monkeypatch.setattr(os, "open", lambda *_args: 0)
    monkeypatch.setattr(os, "close", lambda fd: close_calls.append(fd))

    def fake_lockf(_fd: int, _operation: int) -> None:
        raise OSError(errno.EAGAIN, "lock busy")

    monkeypatch.setattr(fcntl, "lockf", fake_lockf)

    with pytest.raises(UserWarning):
        blackvuesync.lock("/tmp")

    assert close_calls == [0]


def test_main_skips_unlock_when_lock_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    """verifies main does not call unlock when lock acquisition fails."""
    unlock_calls: list[int] = []

    args = argparse.Namespace(
        address="127.0.0.1",
        destination="/tmp",
        grouping="none",
        keep=None,
        priority="date",
        include=None,
        exclude=None,
        max_used_disk=90,
        timeout=1.0,
        retry_failed_after="1d",
        retry_count=3,
        skip_metadata=set(),
        verbose=0,
        quiet=False,
        cron=False,
        dry_run=False,
        affinity_key=None,
    )

    monkeypatch.setattr(blackvuesync, "parse_args", lambda: args)
    monkeypatch.setattr(blackvuesync, "ensure_destination", lambda _destination: None)

    def lock_raises(_destination: str) -> int:
        raise UserWarning("Another instance is already running")

    monkeypatch.setattr(blackvuesync, "lock", lock_raises)
    monkeypatch.setattr(
        blackvuesync, "unlock", lambda lf_fd: unlock_calls.append(lf_fd)
    )

    assert blackvuesync.main() == 1
    assert unlock_calls == []


class TestDownloadRetry:
    """tests for download retry logic."""

    def test_retry_succeeds_after_transient_urlerror(self) -> None:
        """verifies that a transient URLError is retried and succeeds."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count

            try:
                blackvuesync.retry_count = 3

                call_count = 0

                def mock_urlopen(_request: Any, **_kwargs: Any) -> Any:
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        raise urllib.error.URLError("Connection reset")
                    # returns a mock response on 2nd attempt
                    response = unittest.mock.MagicMock()
                    response.__enter__ = lambda s: s
                    response.__exit__ = unittest.mock.MagicMock(return_value=False)
                    response.info.return_value = {"Content-Length": "4"}
                    response.read.side_effect = [b"test", b""]
                    return response

                with (
                    unittest.mock.patch(
                        "urllib.request.urlopen", side_effect=mock_urlopen
                    ),
                    unittest.mock.patch("time.sleep"),
                ):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is True
                assert call_count == 2
                assert os.path.exists(os.path.join(dest, filename))
            finally:
                blackvuesync.retry_count = original_retry_count

    def test_retries_exhausted_no_failed_marker(self) -> None:
        """verifies that exhausted transient retries do not create a .failed marker."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count

            try:
                blackvuesync.retry_count = 3

                with (
                    unittest.mock.patch(
                        "urllib.request.urlopen",
                        side_effect=urllib.error.URLError("Connection reset"),
                    ),
                    unittest.mock.patch("time.sleep"),
                ):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is False
                marker = blackvuesync.get_failed_marker_filepath(dest, None, filename)
                assert not os.path.exists(marker)
            finally:
                blackvuesync.retry_count = original_retry_count

    def test_http_error_not_retried(self) -> None:
        """verifies that HTTPError is not retried and creates a .failed marker."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count
            call_count = 0

            try:
                blackvuesync.retry_count = 3

                def mock_urlopen(_request: Any, **_kwargs: Any) -> Any:
                    nonlocal call_count
                    call_count += 1
                    raise urllib.error.HTTPError(
                        "http://x",
                        500,
                        "Server Error",
                        None,  # type: ignore[arg-type]
                        None,
                    )

                with (
                    unittest.mock.patch(
                        "urllib.request.urlopen", side_effect=mock_urlopen
                    ),
                    unittest.mock.patch("time.sleep"),
                ):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is False
                assert call_count == 1  # only one attempt
                marker = blackvuesync.get_failed_marker_filepath(dest, None, filename)
                assert os.path.exists(marker)
            finally:
                blackvuesync.retry_count = original_retry_count

    def test_socket_timeout_retried_not_raised(self) -> None:
        """verifies that socket.timeout during download is retried, not raised."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count

            try:
                blackvuesync.retry_count = 2
                call_count = 0

                def mock_urlopen(_request: Any, **_kwargs: Any) -> Any:
                    nonlocal call_count
                    call_count += 1
                    if call_count == 1:
                        raise socket.timeout("timed out")
                    response = unittest.mock.MagicMock()
                    response.__enter__ = lambda s: s
                    response.__exit__ = unittest.mock.MagicMock(return_value=False)
                    response.info.return_value = {"Content-Length": "4"}
                    response.read.side_effect = [b"test", b""]
                    return response

                with (
                    unittest.mock.patch(
                        "urllib.request.urlopen", side_effect=mock_urlopen
                    ),
                    unittest.mock.patch("time.sleep"),
                ):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is True
                assert call_count == 2
            finally:
                blackvuesync.retry_count = original_retry_count

    def test_retry_count_one_no_retries(self) -> None:
        """verifies that --retry-count 1 means single attempt, no retries."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count
            call_count = 0

            try:
                blackvuesync.retry_count = 1

                def mock_urlopen(_request: Any, **_kwargs: Any) -> Any:
                    nonlocal call_count
                    call_count += 1
                    raise urllib.error.URLError("Connection reset")

                with (
                    unittest.mock.patch(
                        "urllib.request.urlopen", side_effect=mock_urlopen
                    ),
                    unittest.mock.patch("time.sleep"),
                ):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is False
                assert call_count == 1
            finally:
                blackvuesync.retry_count = original_retry_count

    def test_retry_succeeds_on_third_attempt(self) -> None:
        """verifies recovery after two consecutive transient errors."""
        with tempfile.TemporaryDirectory() as dest:
            filename = "20181029_131513_NF.mp4"
            original_retry_count = blackvuesync.retry_count

            try:
                blackvuesync.retry_count = 3
                call_count = 0

                def mock_urlopen(_request: Any, **_kwargs: Any) -> Any:
                    nonlocal call_count
                    call_count += 1
                    if call_count <= 2:
                        raise urllib.error.URLError("Connection reset")
                    response = unittest.mock.MagicMock()
                    response.__enter__ = lambda s: s
                    response.__exit__ = unittest.mock.MagicMock(return_value=False)
                    response.info.return_value = {"Content-Length": "4"}
                    response.read.side_effect = [b"test", b""]
                    return response

                with (
                    unittest.mock.patch(
                        "urllib.request.urlopen", side_effect=mock_urlopen
                    ),
                    unittest.mock.patch("time.sleep"),
                ):
                    downloaded, _ = blackvuesync.download_file(
                        "http://127.0.0.1:0", filename, dest, None
                    )

                assert downloaded is True
                assert call_count == 3
            finally:
                blackvuesync.retry_count = original_retry_count
