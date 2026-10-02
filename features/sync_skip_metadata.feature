Feature: Sync with the skip-metadata option

  Protects the --skip-metadata option: blackvuesync downloads the videos but
  never asks the dashcam for the skipped thumbnail, accelerometer, or gps
  files. The mock dashcam's request log shows what blackvuesync asked for.

  Scenario: Skipping all metadata downloads only the videos
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs with skip-metadata "t3g"
    Then blackvuesync exits with code 0
    Then the destination contains no "thm" files
    Then the destination contains no "3gf" files
    Then the destination contains no "gps" files
    Then the destination contains all the recordings
    Then the dashcam receives download requests for only the missing recordings

  Scenario: Skipping thumbnails downloads the recordings without thumbnails
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs with skip-metadata "t"
    Then blackvuesync exits with code 0
    Then the destination contains no "thm" files
    Then the destination contains all the recordings
    Then the dashcam receives download requests for only the missing recordings

  @use.with_protocol=legacy
  Scenario: Skipping accelerometer data downloads the recordings without it
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs with skip-metadata "3"
    Then blackvuesync exits with code 0
    Then the destination contains no "3gf" files
    Then the destination contains all the recordings
    Then the dashcam receives download requests for only the missing recordings

  Scenario: Skipping gps data downloads the recordings without it
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs with skip-metadata "g"
    Then blackvuesync exits with code 0
    Then the destination contains no "gps" files
    Then the destination contains all the recordings
    Then the dashcam receives download requests for only the missing recordings
