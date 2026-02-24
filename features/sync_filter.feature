Feature: Sync with include/exclude filters

  Scenario: Include by type downloads all directions
    Given recordings for the past "1d" of types "N,P", directions "F,R"
    When blackvuesync runs with include "N"
    Then blackvuesync exits with code 0
    Then the destination contains "N" recordings
    Then the destination does not contain "P" recordings

  Scenario: Include by type and direction
    Given recordings for the past "1d" of types "N,P", directions "F,R"
    When blackvuesync runs with include "NF"
    Then blackvuesync exits with code 0
    Then the destination contains "NF" recordings
    Then the destination does not contain "NR" recordings
    Then the destination does not contain "P" recordings

  Scenario: Exclude by type
    Given recordings for the past "1d" of types "N,P,E", directions "F"
    When blackvuesync runs with exclude "P"
    Then blackvuesync exits with code 0
    Then the destination contains "N" recordings
    Then the destination contains "E" recordings
    Then the destination does not contain "P" recordings

  Scenario: Include and exclude combined
    Given recordings for the past "1d" of types "N", directions "F,R"
    When blackvuesync runs with include "N" exclude "NR"
    Then blackvuesync exits with code 0
    Then the destination contains "NF" recordings
    Then the destination does not contain "NR" recordings

  Scenario: Include multiple codes
    Given recordings for the past "1d" of types "N,P,E", directions "F"
    When blackvuesync runs with include "N,E"
    Then blackvuesync exits with code 0
    Then the destination contains "N" recordings
    Then the destination contains "E" recordings
    Then the destination does not contain "P" recordings
