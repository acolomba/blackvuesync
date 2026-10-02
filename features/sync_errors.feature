Feature: Sync errors

  Protects the run-level error path: when the dashcam fails to list its
  recordings, blackvuesync downloads nothing and exits with an error code. The
  mock dashcam stands in for a camera that answers the list request with an error.

  Scenario: Sync exits with an error when the dashcam fails to list its recordings
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    Given the dashcam fails to list its recordings
    When blackvuesync runs
    Then blackvuesync exits with code 2
    Then the destination contains no recordings
