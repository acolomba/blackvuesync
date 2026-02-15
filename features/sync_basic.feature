Feature: Basic sync operations

  Scenario: Sync recordings from dashcam to empty destination
    Given recordings for the past "1d" of types "NE", directions "FR"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded

  Scenario: Sync when destination already has some recordings
    Given downloaded recordings between "2d" and "1d" ago of types "NE", directions "FR"
    Given recordings for the past "1d" of types "NE", directions "FR"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then all the downloaded recordings exist

  Scenario: Sync when camera has subset of downloaded recordings
    Given downloaded recordings for the past "2d" of types "N", directions "FR"
    Given recordings same as the downloaded recordings between "2d" and "0d" ago
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then all the downloaded recordings exist

  Scenario: Sync with empty dashcam and empty destination
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination is empty
