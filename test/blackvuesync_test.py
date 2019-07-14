#!/usr/bin/env python3

import pytest
import datetime

import blackvuesync


@pytest.mark.parametrize("filename, expected_recording", [
    ("20181029_131513_NF.mp4", blackvuesync.Recording("20181029_131513_NF.mp4", "20181029_131513", None,
                                                      datetime.datetime(2018, 10, 29, 13, 15, 13), "N", "F", "mp4")),
    ("20181029_131513_EF.mp4", blackvuesync.Recording("20181029_131513_EF.mp4", "20181029_131513", None,
                                                      datetime.datetime(2018, 10, 29, 13, 15, 13), "E", "F", "mp4")),
    ("20181029_131513_PF.mp4", blackvuesync.Recording("20181029_131513_PF.mp4", "20181029_131513", None,
                                                      datetime.datetime(2018, 10, 29, 13, 15, 13), "P", "F", "mp4")),
    ("20181029_131513_MF.mp4", blackvuesync.Recording("20181029_131513_MF.mp4", "20181029_131513", None,
                                                      datetime.datetime(2018, 10, 29, 13, 15, 13), "M", "F", "mp4")),
    ("20181029_131513_NR.mp4", blackvuesync.Recording("20181029_131513_NR.mp4", "20181029_131513", None,
                                                      datetime.datetime(2018, 10, 29, 13, 15, 13), "N", "R", "mp4")),
    ("20181029_131513_ER.mp4", blackvuesync.Recording("20181029_131513_ER.mp4", "20181029_131513", None,
                                                      datetime.datetime(2018, 10, 29, 13, 15, 13), "E", "R", "mp4")),
    ("20181029_131513_PR.mp4", blackvuesync.Recording("20181029_131513_PR.mp4", "20181029_131513", None,
                                                      datetime.datetime(2018, 10, 29, 13, 15, 13), "P", "R", "mp4")),
    ("20181029_131513_MR.mp4", blackvuesync.Recording("20181029_131513_MR.mp4", "20181029_131513", None,
                                                      datetime.datetime(2018, 10, 29, 13, 15, 13), "M", "R", "mp4")),
    ("20181029_131513_NF.mp4", blackvuesync.Recording("20181029_131513_NF.mp4", "20181029_131513", None,
                                                      datetime.datetime(2018, 10, 29, 13, 15, 13), "N", "F", "mp4")),
    ("20181029_131513_NX.mp4", None),
    ("20181029_131513_PX.mp4", None),
    ("20181029_131513_PF.mp3", None),
    ("invalid.gif", None),
])
def test_to_recording(filename, expected_recording):
    recording = blackvuesync.to_recording(filename, "none")

    assert expected_recording == recording


@pytest.mark.parametrize("recording_datetime, expected_daily_group_name, expected_weekly_group_name, "
                         "expected_monthly_group_name, expected_yearly_group_name",
                         [(datetime.datetime(2019, 2, 19, 13, 15, 13), "2019-02-19", "2019-02-18", "2019-02", "2019")])
def test_get_group_name(recording_datetime, expected_daily_group_name, expected_weekly_group_name,
                        expected_monthly_group_name, expected_yearly_group_name):
    assert expected_daily_group_name == blackvuesync.get_group_name(recording_datetime, "daily")
    assert expected_weekly_group_name == blackvuesync.get_group_name(recording_datetime, "weekly")
    assert expected_monthly_group_name == blackvuesync.get_group_name(recording_datetime, "monthly")
    assert expected_yearly_group_name == blackvuesync.get_group_name(recording_datetime, "yearly")


@pytest.mark.parametrize("keep, expected_cutoff_date", [
    ("1d", datetime.datetime(2018, 10, 29)),
    ("2d", datetime.datetime(2018, 10, 28)),
    ("1w", datetime.datetime(2018, 10, 23)),
    ("2w", datetime.datetime(2018, 10, 16)),
])
def test_calc_cutoff_date(keep, expected_cutoff_date):
    try:
        blackvuesync.today = datetime.datetime(2018, 10, 30)

        cutoff_date = blackvuesync.calc_cutoff_date(keep)

        assert expected_cutoff_date == cutoff_date
    finally:
        blackvuesync.today = datetime.date.today()


@pytest.mark.parametrize("priority, filenames, expected_sorted_filenames", [
    ("date",
     ["20190219_104220_NF.mp4", "20190219_104220_NR.mp4", "20190219_104619_MF.mp4", "20190219_104619_MR.mp4",
      "20190219_223201_NF.mp4", "20190219_223201_NR.mp4", "20190219_224918_PF.mp4", "20190219_224918_PR.mp4",
      "20190224_172246_EF.mp4", "20190224_172246_ER.mp4", "20190224_172341_EF.mp4", "20190224_172341_ER.mp4"],
     ["20190219_104220_NF.mp4", "20190219_104220_NR.mp4", "20190219_104619_MF.mp4", "20190219_104619_MR.mp4",
      "20190219_223201_NF.mp4", "20190219_223201_NR.mp4", "20190219_224918_PF.mp4", "20190219_224918_PR.mp4",
      "20190224_172246_EF.mp4", "20190224_172246_ER.mp4", "20190224_172341_EF.mp4", "20190224_172341_ER.mp4"]),
    ("type",
     ["20190219_104220_NF.mp4", "20190219_104220_NR.mp4", "20190219_104619_MF.mp4", "20190219_104619_MR.mp4",
      "20190219_223201_NF.mp4", "20190219_223201_NR.mp4", "20190219_224918_PF.mp4", "20190219_224918_PR.mp4",
      "20190224_172246_EF.mp4", "20190224_172246_ER.mp4", "20190224_172341_EF.mp4", "20190224_172341_ER.mp4"],
     ["20190219_104619_MF.mp4", "20190219_104619_MR.mp4", "20190224_172246_EF.mp4", "20190224_172246_ER.mp4",
      "20190224_172341_EF.mp4", "20190224_172341_ER.mp4", "20190219_104220_NF.mp4", "20190219_104220_NR.mp4",
      "20190219_223201_NF.mp4", "20190219_223201_NR.mp4", "20190219_224918_PF.mp4", "20190219_224918_PR.mp4"]),
])
def test_sort_recordings(priority, filenames, expected_sorted_filenames):
    recordings = [blackvuesync.to_recording(f, "none") for f in filenames]
    expected_sorted_recordings = [blackvuesync.to_recording(f, "none") for f in expected_sorted_filenames]

    # copy
    sorted_recordings = recordings.copy()
    blackvuesync.sort_recordings(sorted_recordings, priority)

    assert expected_sorted_recordings == sorted_recordings
