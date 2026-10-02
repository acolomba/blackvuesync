Feature: Retry failed downloads

  Protects the failure markers: a download the dashcam answers with an error
  leaves a marker, and --retry-failed-after holds off retries until the marker
  ages out. The mock dashcam stands in for a camera with unreadable recordings.

  Scenario: Failed downloads create failure markers
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    Given the dashcam fails to serve 2 "mp4" files
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination contains all but the failed recordings
    Then the destination contains failure markers for the failed recordings

  Scenario: Failed metadata downloads leave markers without failing the run
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    Given the dashcam fails to serve 2 "thm" files
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the destination contains all but the failed recordings
    Then the destination contains failure markers for the failed recordings

  Scenario: Blackvuesync skips failed downloads on the next sync
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    Given the dashcam fails to serve 2 "mp4" files
    When blackvuesync runs
    When the dashcam stops failing downloads
    When blackvuesync runs with retry-failed-after "1h"
    Then blackvuesync exits with code 0
    Then the dashcam receives no download requests
    Then the destination contains all but the failed recordings
    Then the destination contains failure markers for the failed recordings

  Scenario: Blackvuesync retries failed downloads after the retry window expires
    Given the dashcam has recordings for the past "1d" of types "N", directions "F"
    Given the dashcam fails to serve 2 "mp4" files
    When blackvuesync runs
    When the dashcam stops failing downloads
    When the failure markers age by 2 hours
    When blackvuesync runs with retry-failed-after "1h"
    Then blackvuesync exits with code 0
    Then the destination contains all the recordings
    Then the destination contains no failure markers
