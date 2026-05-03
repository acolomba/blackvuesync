from __future__ import annotations

import argparse
import datetime
import errno
import fcntl
import glob
import json
import logging
import os
import tempfile
import time
import urllib.request

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


def test_structured_log_formatter_outputs_json_with_extra_fields() -> None:
    """verifies structured logs include standard and extra fields."""
    formatter = blackvuesync.StructuredLogFormatter()
    record = logging.LogRecord(
        "blackvuesync",
        logging.INFO,
        __file__,
        1,
        "Downloaded recording : %s",
        ("20181029_131513",),
        None,
    )
    record.__dict__.update(
        {
            "event": "recording_downloaded",
            "recording_base_filename": "20181029_131513",
            "recording_type": "N",
        }
    )

    output = json.loads(formatter.format(record))

    assert output["level"] == "INFO"
    assert output["logger"] == "blackvuesync"
    assert output["message"] == "Downloaded recording : 20181029_131513"
    assert output["event"] == "recording_downloaded"
    assert output["recording_base_filename"] == "20181029_131513"
    assert output["recording_type"] == "N"
    assert "timestamp" in output
    assert "args" not in output


@pytest.mark.parametrize(
    "value, expected",
    [
        ("http://pushgateway:9091", "http://pushgateway:9091"),
        ("https://pushgateway.example.net/", "https://pushgateway.example.net"),
    ],
)
def test_parse_pushgateway_url(value: str, expected: str) -> None:
    assert blackvuesync.parse_pushgateway_url(value) == expected


@pytest.mark.parametrize("value", ["pushgateway:9091", "ftp://example.net", "http://"])
def test_parse_pushgateway_url_invalid(value: str) -> None:
    with pytest.raises(argparse.ArgumentTypeError):
        blackvuesync.parse_pushgateway_url(value)


def test_sync_metrics_records_downloads_and_failures(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verifies the metrics model tracks last-run counts and last success time."""
    monkeypatch.setattr(blackvuesync, "dry_run", False)
    metrics = blackvuesync.SyncMetrics(
        run_start_monotonic=time.perf_counter(),
        run_start_timestamp=time.time(),
    )

    metrics.record_file_download(6)
    metrics.record_file_download_failure("http")
    metrics.record_file_download_failure("bogus")
    metrics.record_run_failure("timeout")
    metrics.record_destination_disk_usage(25, 100)
    metrics.finalize(exit_code=2, sync_success=False)

    assert metrics.files_downloaded_last_run == 1
    assert metrics.bytes_downloaded_last_run == 6
    assert metrics.last_successful_file_pull_timestamp_seconds is not None
    assert metrics.file_download_failures_last_run == {
        "disk": 0,
        "http": 1,
        "network": 0,
        "timeout": 0,
        "unknown": 1,
    }
    assert metrics.last_run_failures == {
        "disk": 0,
        "http": 0,
        "network": 0,
        "timeout": 1,
        "unknown": 0,
    }
    assert metrics.destination_disk_used_ratio == 0.25
    assert metrics.last_run_exit_code == 2
    assert metrics.last_run_success == 0


def test_sync_metrics_dry_run_does_not_update_last_success(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verifies dry-run downloads do not update persisted last-success state."""
    monkeypatch.setattr(blackvuesync, "dry_run", True)
    metrics = blackvuesync.SyncMetrics(
        run_start_monotonic=time.perf_counter(),
        run_start_timestamp=time.time(),
        last_successful_file_pull_timestamp_seconds=123.0,
    )

    metrics.record_file_download(6)

    assert metrics.files_downloaded_last_run == 1
    assert metrics.last_successful_file_pull_timestamp_seconds == 123.0


def test_metrics_state_round_trip() -> None:
    """verifies metrics state persists the last successful file pull timestamp."""
    with tempfile.TemporaryDirectory() as destination:
        state_file = os.path.join(destination, "metrics-state.json")
        metrics = blackvuesync.SyncMetrics(
            run_start_monotonic=time.perf_counter(),
            run_start_timestamp=time.time(),
            last_successful_file_pull_timestamp_seconds=123.0,
        )

        blackvuesync.save_metrics_state(state_file, metrics)

        assert blackvuesync.load_metrics_state(state_file) == 123.0


def test_metrics_state_missing_or_corrupt_returns_none() -> None:
    """verifies invalid metrics state does not fail a run."""
    with tempfile.TemporaryDirectory() as destination:
        missing_state_file = os.path.join(destination, "missing.json")
        corrupt_state_file = os.path.join(destination, "corrupt.json")

        with open(corrupt_state_file, "w", encoding="utf-8") as f:
            f.write("{")

        assert blackvuesync.load_metrics_state(missing_state_file) is None
        assert blackvuesync.load_metrics_state(corrupt_state_file) is None


@pytest.mark.parametrize(
    "error, expected",
    [
        (UserWarning("Dashcam unavailable : <urlopen error timed out>"), "timeout"),
        (UserWarning("Dashcam unavailable : host unreachable"), "network"),
        (RuntimeError("Not enough disk space left"), "disk"),
        (
            RuntimeError("Error response from : http://dashcam ; status code : 500"),
            "http",
        ),
        (RuntimeError("other failure"), "unknown"),
    ],
)
def test_classify_run_failure(error: BaseException, expected: str) -> None:
    assert blackvuesync.classify_run_failure(error) == expected


def test_render_metrics_uses_last_run_gauges() -> None:
    """verifies rendered metrics use last-run gauge names and stable labels."""
    metrics = blackvuesync.SyncMetrics(
        run_start_monotonic=time.perf_counter(),
        run_start_timestamp=time.time(),
        last_successful_file_pull_timestamp_seconds=123.0,
    )
    metrics.record_file_download_failure("network")
    metrics.record_run_failure("network")
    metrics.files_downloaded_last_run = 2
    metrics.bytes_downloaded_last_run = 12
    metrics.finalize(exit_code=0, sync_success=True)

    output = blackvuesync.render_metrics(metrics)

    assert "# TYPE blackvuesync_files_downloaded_last_run gauge" in output
    assert 'blackvuesync_file_download_failures_last_run{reason="network"} 1' in output
    assert 'blackvuesync_last_run_failure{reason="network"} 1' in output
    assert "blackvuesync_file_download_failures_total" not in output
    assert "blackvuesync_last_run_success 1" in output
    assert "blackvuesync_last_run_exit_code 0" in output
    assert "blackvuesync_last_successful_file_pull_timestamp_seconds 123.0" in output


def test_write_metrics_file_replaces_target() -> None:
    """verifies metrics file writes replace the target file."""
    with tempfile.TemporaryDirectory() as destination:
        metrics_file = os.path.join(destination, "blackvuesync.prom")

        blackvuesync.write_metrics_file(metrics_file, "first\n")
        blackvuesync.write_metrics_file(metrics_file, "second\n")

        with open(metrics_file, encoding="utf-8") as f:
            assert f.read() == "second\n"


def test_pushgateway_metrics_url_quotes_grouping_values() -> None:
    """verifies Pushgateway grouping values are path-escaped."""
    assert (
        blackvuesync.get_pushgateway_metrics_url(
            "http://pushgateway:9091/", "blackvue sync", "dash/cam"
        )
        == "http://pushgateway:9091/metrics/job/blackvue%20sync/instance/dash%2Fcam"
    )


def test_push_metrics_uses_put_request(monkeypatch: pytest.MonkeyPatch) -> None:
    """verifies Pushgateway delivery uses PUT and text exposition content type."""
    requests: list[urllib.request.Request] = []
    timeouts: list[float] = []

    class FakeResponse:
        def __enter__(self) -> FakeResponse:
            return self

        def __exit__(self, exc_type: object, exc: object, tb: object) -> None:
            return None

    def fake_urlopen(request: urllib.request.Request, timeout: float) -> FakeResponse:
        requests.append(request)
        timeouts.append(timeout)
        return FakeResponse()

    monkeypatch.setattr(urllib.request, "urlopen", fake_urlopen)

    blackvuesync.push_metrics(
        "http://pushgateway:9091",
        "blackvuesync",
        "dashcam",
        "metric 1\n",
        1.5,
    )

    assert len(requests) == 1
    assert requests[0].full_url == (
        "http://pushgateway:9091/metrics/job/blackvuesync/instance/dashcam"
    )
    assert requests[0].get_method() == "PUT"
    assert requests[0].data == b"metric 1\n"
    assert requests[0].get_header("Content-type") == (
        "text/plain; version=0.0.4; charset=utf-8"
    )
    assert timeouts == [1.5]


def test_main_writes_metrics_for_cron_unavailable_dashcam(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verifies cron exit success is distinct from sync success in metrics."""
    with tempfile.TemporaryDirectory() as destination:
        metrics_file = os.path.join(destination, "blackvuesync.prom")
        args = argparse.Namespace(
            address="127.0.0.1",
            destination=destination,
            grouping="none",
            keep=None,
            priority="date",
            include=None,
            exclude=None,
            max_used_disk=90,
            timeout=1.0,
            retry_failed_after="1d",
            skip_metadata=set(),
            verbose=0,
            quiet=False,
            log_format="text",
            metrics_file=metrics_file,
            metrics_pushgateway_url=None,
            metrics_job="blackvuesync",
            metrics_instance=None,
            metrics_state_file=None,
            cron=True,
            dry_run=False,
            affinity_key=None,
        )

        def get_dashcam_filenames_raises(_base_url: str) -> list[str]:
            raise UserWarning("Dashcam unavailable")

        monkeypatch.setattr(blackvuesync, "parse_args", lambda: args)
        monkeypatch.setattr(
            blackvuesync, "get_dashcam_filenames", get_dashcam_filenames_raises
        )

        assert blackvuesync.main() == 0

        with open(metrics_file, encoding="utf-8") as f:
            output = f.read()

        assert "blackvuesync_last_run_success 0" in output
        assert "blackvuesync_last_run_exit_code 0" in output
        assert 'blackvuesync_last_run_failure{reason="network"} 1' in output


def test_main_writes_timeout_run_failure_metric(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """verifies index timeouts are visible as run-level timeout failures."""
    with tempfile.TemporaryDirectory() as destination:
        metrics_file = os.path.join(destination, "blackvuesync.prom")
        args = argparse.Namespace(
            address="127.0.0.1",
            destination=destination,
            grouping="none",
            keep=None,
            priority="date",
            include=None,
            exclude=None,
            max_used_disk=90,
            timeout=1.0,
            retry_failed_after="1d",
            skip_metadata=set(),
            verbose=0,
            quiet=False,
            log_format="text",
            metrics_file=metrics_file,
            metrics_pushgateway_url=None,
            metrics_job="blackvuesync",
            metrics_instance=None,
            metrics_state_file=None,
            cron=False,
            dry_run=False,
            affinity_key=None,
        )

        def get_dashcam_filenames_raises(_base_url: str) -> list[str]:
            raise UserWarning("Dashcam unavailable : <urlopen error timed out>")

        monkeypatch.setattr(blackvuesync, "parse_args", lambda: args)
        monkeypatch.setattr(
            blackvuesync, "get_dashcam_filenames", get_dashcam_filenames_raises
        )

        assert blackvuesync.main() == 1

        with open(metrics_file, encoding="utf-8") as f:
            output = f.read()

        assert "blackvuesync_last_run_success 0" in output
        assert "blackvuesync_last_run_exit_code 1" in output
        assert 'blackvuesync_last_run_failure{reason="timeout"} 1' in output
        assert (
            'blackvuesync_file_download_failures_last_run{reason="timeout"} 0' in output
        )


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
        skip_metadata=set(),
        verbose=0,
        quiet=False,
        log_format="text",
        metrics_file=None,
        metrics_pushgateway_url=None,
        metrics_job="blackvuesync",
        metrics_instance=None,
        metrics_state_file=None,
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
        lambda _address,
        _destination,
        _grouping,
        _priority,
        _include,
        _exclude,
        _metrics: None,
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
        skip_metadata=set(),
        verbose=0,
        quiet=False,
        log_format="text",
        metrics_file=None,
        metrics_pushgateway_url=None,
        metrics_job="blackvuesync",
        metrics_instance=None,
        metrics_state_file=None,
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
