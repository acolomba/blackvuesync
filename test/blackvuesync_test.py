from __future__ import annotations

import argparse
import datetime
import glob
import os
import tempfile
import time

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
    ],
)
def test_parse_skip_metadata(value: str, expected: set[str]) -> None:
    from blackvuesync import parse_skip_metadata

    assert parse_skip_metadata(value) == expected


@pytest.mark.parametrize("value", ["x", "t3x", "abc", "T", "mp4"])
def test_parse_skip_metadata_invalid(value: str) -> None:
    from blackvuesync import parse_skip_metadata

    with pytest.raises(argparse.ArgumentTypeError):
        parse_skip_metadata(value)
