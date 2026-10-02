Feature: Sync with grouping

  Protects the --grouping option: blackvuesync downloads each recording into a
  directory named after its date, such as 2019-06-15 for a day or the date of
  the monday for a week. Recordings dated over the past days stand in for
  days of driving.

  Scenario: Daily grouping downloads the recordings into a directory per day
    Given the dashcam has recordings for the past "2d" of types "N,E", directions "F,R"
    When blackvuesync runs with grouping "daily"
    Then blackvuesync exits with code 0
    Then the destination contains all the recordings
    Then the "mp4" files in the destination match the mock fixture

  Scenario: Weekly grouping downloads the recordings into a directory per week
    Given the dashcam has recordings for the past "2w" of types "N", directions "F"
    When blackvuesync runs with grouping "weekly"
    Then blackvuesync exits with code 0
    Then the destination contains all the recordings
