Feature: Retry failed downloads

  Scenario: Failed downloads create failure markers
    Given recordings for the past "1d" of types "N", directions "F"
    Given the first 2 mp4 recordings are configured to fail
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the successful recordings are downloaded
    Then failure markers exist for the failed recordings

  Scenario: Failed downloads are skipped on next sync
    Given recordings for the past "1d" of types "N", directions "F"
    Given the first 2 mp4 recordings are configured to fail
    When blackvuesync runs
    When download errors are cleared
    When blackvuesync runs with retry-failed-after "1h"
    Then blackvuesync exits with code 0
    Then the previously failed recordings are not downloaded

  Scenario: Failed downloads are retried after retry window expires
    Given recordings for the past "1d" of types "N", directions "F"
    Given the first 2 mp4 recordings are configured to fail
    When blackvuesync runs
    When download errors are cleared
    When 2 seconds elapse
    When blackvuesync runs with retry-failed-after "1s"
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then no failure markers exist

  Scenario: Transient download errors recover within a single sync run
    Given recordings for the past "1d" of types "N", directions "F"
    Given the first 2 mp4 recordings have 2 transient errors
    When blackvuesync runs with retry-count "3"
    Then blackvuesync exits with code 0
    Then all the recordings are downloaded
    Then no failure markers exist
