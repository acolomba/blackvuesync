Feature: Partial downloads

  Protects the recovery from interrupted runs: blackvuesync replaces a partial
  download with the full recording and removes the partial downloads it does
  not resume. A truncated copy of a dashcam video stands in for a download
  that a previous run left behind.

  Scenario: Sync replaces a partial download with the full recording
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    Given the destination has a partial download of a dashcam recording
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination contains all the recordings
    Then the "mp4" files in the destination match the files on the dashcam

  Scenario: Sync removes the partial download of a recording the dashcam does not list
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    Given the destination has a partial download of a recording from "3d" ago
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination contains all the recordings
