import datetime
from typing import Optional

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
        ("20181029_131513_NX.mp4", None),
        ("20181029_131513_PX.mp4", None),
        ("20181029_131513_PF.mp3", None),
        ("invalid.gif", None),
    ],
)
def test_to_recording(
    filename: str, expected_recording: Optional[blackvuesync.Recording]
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
    filename: str, expected_recording: Optional[blackvuesync.DownloadedRecording]
) -> None:
    recording = blackvuesync.to_downloaded_recording(filename, "none")

    assert expected_recording == recording


@pytest.mark.parametrize(
    "recording_datetime, expected_daily_group_name, expected_weekly_group_name, "
    "expected_monthly_group_name, expected_yearly_group_name",
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
