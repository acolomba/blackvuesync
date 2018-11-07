#!/usr/bin/env python3

import pytest
import datetime

import blackvuesync


@pytest.mark.parametrize("filename, expected_recording", [
    ("20181029_131513_PF.mp4", blackvuesync.Recording(
        "20181029_131513_PF.mp4", datetime.datetime(2018,10, 29, 13, 15, 13),
        "P", "F", "mp4")),
    ("invalid.gif", None),
])
def test_get_recording(filename, expected_recording):
    actual_recording = blackvuesync.get_recording(filename)

    assert expected_recording == actual_recording
