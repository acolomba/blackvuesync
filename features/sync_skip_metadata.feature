Feature: Sync with skip-metadata option

  Scenario: Sync recordings skipping all metadata files
    Given recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs with skip-metadata "t3g"
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then the destination contains no "thm" files
    Then the destination contains no "3gf" files
    Then the destination contains no "gps" files

  Scenario: Sync recordings skipping only thumbnail files
    Given recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs with skip-metadata "t"
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then the destination contains no "thm" files

  Scenario: Sync recordings skipping only accelerometer files
    Given recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs with skip-metadata "3"
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then the destination contains no "3gf" files

  Scenario: Sync recordings skipping only gps files
    Given recordings for the past "1d" of types "N", directions "F"
    When blackvuesync runs with skip-metadata "g"
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then the destination contains no "gps" files
