Feature: Basic sync operations

  Scenario: Sync recordings from dashcam to empty destination
    Given recordings for the past "1d" of types "NE", directions "FR"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded

  Scenario: Sync when destination already has some recordings
    Given recordings for the past "1d" of types "NE", directions "FR"
    Given downloaded recordings for the past "2d" of types "N", directions "FR"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded

  Scenario: Sync with empty dashcam
    Given recordings for the past "0d" of types "N", directions "F"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination is empty

  Scenario: Sync downloads all recording file types
    Given recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
