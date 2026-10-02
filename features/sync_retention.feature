Feature: Retention policy

  Protects the --keep option: blackvuesync skips dashcam recordings older than
  the retention period and deletes older ones from the destination. Recordings
  dated relative to today stand in for days of driving.

  Scenario: Keep downloads only the recordings within the retention period
    Given the dashcam has recordings for the past "7d" of types "N", directions "F"
    When blackvuesync runs with keep "3d"
    Then blackvuesync exits with code 0
    Then the destination contains only the recordings between "3d" and "0d" ago

  Scenario: Keep longer than the dashcam history downloads every recording
    Given the dashcam has recordings for the past "2d" of types "N", directions "F"
    When blackvuesync runs with keep "7d"
    Then blackvuesync exits with code 0
    Then the destination contains all the recordings

  Scenario: Keep preserves pre-existing recent recordings
    Given the destination has recordings for the past "2d" of types "N", directions "F"
    Given the dashcam has recordings for the past "5d" of types "N", directions "F"
    When blackvuesync runs with keep "3d"
    Then blackvuesync exits with code 0
    Then the destination contains only the recordings between "3d" and "0d" ago

  Scenario: Keep removes old pre-existing recordings
    Given the destination has recordings for the past "7d" of types "N", directions "F"
    Given the dashcam has recordings for the past "2d" of types "N", directions "F"
    When blackvuesync runs with keep "3d"
    Then blackvuesync exits with code 0
    Then the destination contains only the recordings between "3d" and "0d" ago
