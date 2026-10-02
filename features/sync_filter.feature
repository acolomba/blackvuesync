Feature: Sync with include and exclude filters

  Protects the --include and --exclude options, which select recordings by a
  type code such as "N" or a type and direction code such as "NF". The mock
  dashcam serves a mix of codes, and the destination must hold only the selected ones.

  Scenario: Include by type downloads all directions
    Given the dashcam has recordings for the past "1d" of types "N,P", directions "F,R"
    When blackvuesync runs with include "N"
    Then blackvuesync exits with code 0
    Then the destination contains only the "N" recordings

  Scenario: Include by type and direction downloads only that direction
    Given the dashcam has recordings for the past "1d" of types "N,P", directions "F,R"
    When blackvuesync runs with include "NF"
    Then blackvuesync exits with code 0
    Then the destination contains only the "NF" recordings

  Scenario: Exclude by type skips the recordings of that type
    Given the dashcam has recordings for the past "1d" of types "N,P,E", directions "F"
    When blackvuesync runs with exclude "P"
    Then blackvuesync exits with code 0
    Then the destination contains only the "N,E" recordings

  Scenario: Exclude by type and direction keeps the other directions
    Given the dashcam has recordings for the past "1d" of types "N", directions "F,R"
    When blackvuesync runs with exclude "NR"
    Then blackvuesync exits with code 0
    Then the destination contains only the "NF" recordings

  Scenario: Exclude narrows an include
    Given the dashcam has recordings for the past "1d" of types "N,P", directions "F,R"
    When blackvuesync runs with include "N" exclude "NR"
    Then blackvuesync exits with code 0
    Then the destination contains only the "NF" recordings

  Scenario: Include with several codes downloads every selected type
    Given the dashcam has recordings for the past "1d" of types "N,P,E", directions "F"
    When blackvuesync runs with include "N,E"
    Then blackvuesync exits with code 0
    Then the destination contains only the "N,E" recordings
