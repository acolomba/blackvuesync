Feature: API version parity

  Scenario Outline: sync yields the same recordings whether the camera is legacy
    Given the dashcam is legacy: <legacy_api>
    Given recordings for the past "1d" of types "NE", directions "FR"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded

    Examples:
      | legacy_api |
      | true       |
      | false      |

  Scenario: sync retrieves thumbnail and gps metadata on V1.009 cameras
    Given the dashcam is legacy: false
    Given recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then the downloaded "thm" files match the mock fixture
    Then the downloaded "gps" files match the mock fixture
    Then the destination contains no "3gf" files
