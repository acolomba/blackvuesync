Feature: Camera API selection

  Explicit modes skip firmware detection while preserving recording and metadata
  downloads. A mock camera records requests and serves both firmware protocols.

  Scenario Outline: Forced modes select the matching recording API
    Given the dashcam uses the "<mode>" API
    Given the dashcam has recordings for the past "1d" of types "N", directions "F,R"
    When blackvuesync runs with camera-api "<mode>"
    Then blackvuesync exits with code 0
    Then the dashcam receives these api selection requests:
      | path    |
      | <index> |
    Then the destination contains all the recordings
    Then the "mp4" files in the destination match the files on the dashcam
    Then the "thm" files in the destination match the files on the dashcam
    Then the "gps" files in the destination match the files on the dashcam
    When blackvuesync runs with camera-api "<mode>"
    Then blackvuesync exits with code 0
    Then the dashcam receives these api selection requests:
      | path    |
      | <index> |
    Then the dashcam receives no download requests

    Examples:
      | mode   | index             |
      | legacy | /blackvue_vod.cgi |
      | modern | /vodList          |

  Scenario Outline: Automatic mode retains firmware detection
    Given the dashcam uses the "<protocol>" API
    Given the dashcam has no recordings
    When blackvuesync runs with camera-api "auto"
    Then blackvuesync exits with code 0
    Then the dashcam receives these api selection requests:
      | path        |
      | /accessible |
      | <index>     |

    Examples:
      | protocol | index             |
      | legacy   | /blackvue_vod.cgi |
      | modern   | /vodList          |

  Scenario Outline: Invalid nonempty modes fail before camera communication
    When blackvuesync runs with camera-api "<mode>"
    Then blackvuesync exits with code 2
    Then stderr reports an invalid camera api
    Then the dashcam receives no api requests
    Then the destination contains no recordings

    Examples:
      | mode    |
      | invalid |
      | LEGACY  |

  Scenario Outline: Missing forced APIs suggest automatic detection
    Given the dashcam uses the "<mode>" API
    Given the dashcam returns http 404 for its recording index
    When blackvuesync runs with camera-api "<mode>"
    Then blackvuesync exits with code 2
    Then stderr contains "Recording API '<mode>'"
    Then stderr contains "HTTP 404"
    Then stderr contains "--camera-api auto"
    Then stderr contains "CAMERA_API=auto"
    Then the dashcam receives these api selection requests:
      | path    |
      | <index> |
    Then the destination contains no recordings

    Examples:
      | mode   | index             |
      | legacy | /blackvue_vod.cgi |
      | modern | /vodList          |

  Scenario: Automatic index errors retain normal error handling
    Given the dashcam uses the "modern" API
    Given the dashcam returns http 404 for its recording index
    When blackvuesync runs
    Then blackvuesync exits with code 2
    Then stderr contains "Cannot obtain list of recordings"
    Then stderr does not contain "try --camera-api auto"
    Then the dashcam receives these api selection requests:
      | path        |
      | /accessible |
      | /vodList    |

  Scenario: Cron runs omit the camera API mode at normal verbosity
    Given the dashcam uses the "legacy" API
    Given the dashcam has no recordings
    When blackvuesync runs with camera-api "legacy" cron "1"
    Then blackvuesync exits with code 0
    Then stderr does not contain "Camera API mode"

  Scenario: Debug output includes the selected mode
    Given the dashcam uses the "legacy" API
    Given the dashcam has no recordings
    When blackvuesync runs with camera-api "legacy" verbose "2"
    Then blackvuesync exits with code 0
    Then stderr contains "Camera API mode : legacy"

  @use.with_implementation=docker
  Scenario Outline: Empty Docker camera API values use automatic detection
    Given the dashcam uses the "<protocol>" API
    Given the docker environment variable "CAMERA_API" is empty
    Given the dashcam has no recordings
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the dashcam receives these api selection requests:
      | path        |
      | /accessible |
      | <index>     |

    Examples:
      | protocol | index             |
      | legacy   | /blackvue_vod.cgi |
      | modern   | /vodList          |

  @use.with_implementation=docker
  Scenario Outline: Omitted Docker camera API values use automatic detection
    Given the dashcam uses the "<protocol>" API
    Given the dashcam has no recordings
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the dashcam receives these api selection requests:
      | path        |
      | /accessible |
      | <index>     |

    Examples:
      | protocol | index             |
      | legacy   | /blackvue_vod.cgi |
      | modern   | /vodList          |

  @use.with_implementation=docker
  Scenario Outline: Unset Docker camera API values use automatic detection
    Given the dashcam uses the "<protocol>" API
    Given the docker environment variable "CAMERA_API" is unset
    Given the dashcam has no recordings
    When blackvuesync runs
    Then blackvuesync exits with code 0
    Then the dashcam receives these api selection requests:
      | path        |
      | /accessible |
      | <index>     |

    Examples:
      | protocol | index             |
      | legacy   | /blackvue_vod.cgi |
      | modern   | /vodList          |
