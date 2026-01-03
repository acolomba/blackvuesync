Feature: Retention policy

  Scenario: Keep recordings within retention period
    Given recordings for the past "7d" of types "N", directions "F"
    When blackvuesync runs with keep "3d"
    Then blackvuesync exits with code 0
    Then recordings between "3d" and "0d" ago are downloaded
    Then no recordings between "7d" and "4d" ago exist

  Scenario: Keep all recordings when period is longer than available
    Given recordings for the past "2d" of types "N", directions "F"
    When blackvuesync runs with keep "7d"
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded

  Scenario: Keep preserves pre-existing recent recordings
    Given downloaded recordings for the past "2d" of types "N", directions "F"
    Given recordings for the past "5d" of types "N", directions "F"
    When blackvuesync runs with keep "3d"
    Then blackvuesync exits with code 0
    Then all the downloaded recordings exist
    Then recordings between "3d" and "0d" ago are downloaded
    Then no recordings between "5d" and "4d" ago exist

  Scenario: Keep removes old pre-existing recordings
    Given downloaded recordings for the past "7d" of types "N", directions "F"
    Given recordings for the past "2d" of types "N", directions "F"
    When blackvuesync runs with keep "3d"
    Then blackvuesync exits with code 0
    Then recordings between "3d" and "0d" ago are downloaded
    Then no recordings between "7d" and "4d" ago exist
    Then downloaded recordings between "3d" and "0d" ago exist
    Then no downloaded recordings between "7d" and "4d" ago exist
