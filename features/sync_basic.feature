Feature: Basic sync operations

  Protects the core sync: blackvuesync downloads every recording the dashcam
  serves and leaves the recordings already in the destination alone. A mock
  dashcam stands in for the camera and a temporary directory for the destination.

  Scenario: Sync downloads every dashcam recording to an empty destination
    Given the dashcam has recordings for the past "1d" of types "N,E", directions "F,R"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination contains all the recordings
    Then the "mp4" files in the destination match the mock fixture
    Then the "thm" files in the destination match the mock fixture
    Then the "gps" files in the destination match the mock fixture

  Scenario: Sync keeps destination recordings the dashcam does not list
    Given the destination has recordings between "2d" and "1d" ago of types "N,E", directions "F,R"
    Given the dashcam has recordings for the past "1d" of types "N,E", directions "F,R"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination contains all the recordings

  Scenario: Sync downloads only the recordings missing from the destination
    Given the dashcam has recordings for the past "2d" of types "N,E", directions "F,R"
    Given the destination has the dashcam recordings between "2d" and "1d" ago
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination contains all the recordings
    Then the dashcam receives download requests for only the missing recordings

  Scenario: Sync downloads nothing when the destination has every dashcam recording
    Given the destination has recordings for the past "2d" of types "N", directions "F,R"
    Given the dashcam has the destination recordings between "1d" and "0d" ago
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination contains all the recordings
    Then the dashcam receives no download requests

  Scenario: Sync with an empty dashcam leaves the destination empty
    Given the dashcam has no recordings
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination contains no recordings
