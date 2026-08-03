# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [2.2.0] - 2026-08-03

### Added

- Support BlackVue firmware V1.009+ cameras. (#87)
- Add `--log-format` option to select `text` or `json` log output. (#73)
- Add Prometheus metrics export via `--metrics-file` and
  `--metrics-pushgateway-url`, configurable with `--metrics-job`,
  `--metrics-instance`, and `--metrics-state-file`. (#74)
- Add `--retry-failed-after` option to retry failed downloads after a
  configurable delay. (#58)
- Add `--skip-metadata` option to skip downloading metadata files (thumbnails,
  accelerometer, GPS). (#14)

### Changed

- Replace undocumented `--filter` with `--include` and `--exclude` options for
  filtering recordings by type and direction. Codes are comma-separated,
  direction is optional. (#61)
- Stream recording downloads in chunks to avoid buffering full files in memory.

### Fixed

- Close the lock file descriptor when lock acquisition fails and distinguish
  lock contention from other OS errors.
- Ensure lock descriptor `0` is always unlocked on exit.
- Handle `socket.timeout` surfaced as a URL error during downloads. (#75)

## [2.1.1] - 2026-01-11

### Changed

- Switch to semver.

## [2.1] - 2026-01-11

### Fixed

- Minor resource cleanup fix. (#52)

## [2.0] - 2026-01-03

### Added

- Add initial Claude Code settings and AI contribution policy.
- Build Docker images for amd64, arm64, and armv7 architectures. (#12)
- Add support for 'O' (Optional) camera direction on DR770X Box Pro and similar
  models. (inspired by grysage/blackvuesync)
- Add support for DMS (Driver Monitoring System) recording types: D
  (Drowsiness), L (Distraction), Y (Seatbelt), F (Undetected).
- Publish to PyPi. Can be run with `uvx blackvuesync` without explicitly
  installing.
- Introduce integration tests for some features.

### Changed

- Modernize for Python 3.9, now that it's available in Debian Bullseye
  oldoldstable, the earliest LTS-supported Debian release. Now uses type hints,
  f-strings; walrus operator.
- Logging uses lazy evaluation.

## [1.10] - 2025-12-28

### Added

- Add `--filter` option to filter which events are downloaded. (#6)
- Add support for the interior camera found on the DR750X-3CH. (#7)
- Add "rdate" priority, to download from newest to oldest.

### Changed

- Download GPS data for all recording types. (#9)
- Silence host/network down/unreachable and timeout in cron mode (inspired by
  #23).
- Propagate exit status code to calling process. In cron mode, expected errors
  produce a success exit status.
- Upgrade alpine image to 3.23.2.

### Fixed

- Flush logs on exit. (#20)

## [1.9] - 2021-08-08

### Fixed

- Properly removes outdated recordings with new event types and upload flags
  from May 2021 firmware. (#4)

## [1.8] - 2021-05-25

### Added

- Supports new event types produced by the May 2021 [BlackVue firmware
  update](https://blackvue.com/major-update-improved-blackvue-app-ui-dark-mode-live-event-upload-and-more/).
  (#3)
- Docker compose file for a possibly quicker quickstart.

### Changed

- Friendlier hardware requirement descriptions. (#2)
- Upgraded docker image to alpine 3.13.5

### Fixed

- The Docker image respects the KEEP option now.
- More reliable removal of outdated directories when grouping by day, month or
  year.
- Better handling of unexpected 500 errors or remote disconnections.

## [1.7] - 2019-07-14

### Added

- Allows grouping recordings by date, with daily, weekly, monthly and yearly
  granularities.

### Changed

- Docker image layers are more cacheable.
- Upgraded docker image to alpine 3.10.1

## [1.6] - 2019-06-01

### Added

- Logs file/recording download speed to help troubleshoot unreliable/slow Wi-Fi
  setups.

### Fixed

- Fixed a spurious error log during the first run after midnight.
- Does a better job at cleaning up temp files from interrupted downloads.
- Better handling of network errors while reading the file list.

## [1.5] - 2019-03-03

### Added

- Downloads .thm (thumbnail) files for all recordings.
- New `--priority` switch allows downloading by either a) date or b) type
  (manual, event, normal, parking in that order.)

### Changed

- Now downloads front and rear recordings together.

## [1.4] - 2019-02-26

### Added

- Downloads gps data for all but parking recording types, and accelerometer
  data for all.

### Fixed

- 500 errors while downloading are logged but ignored, so we don't get stuck on
  files we can't download.
- Tests that outdated gps/accelerometer files exist before deleting them, so it
  doesn't error out.

## [1.3] - 2019-02-09

### Changed

- Removes gps data for outdated recordings along with the video.

### Fixed

- Gracefully handles low-level socket timeouts.

## [1.2] - 2019-02-02

### Fixed

- Removes temporary files upon successful completion.

## [1.1] - 2019-02-01

### Added

- Connection timeout defaults to 10 seconds and is configurable.

### Fixed

- No more sporadically getting stuck forever trying to connect to the dashcam.

## [1.0] - 2018-12-02

### Added

- Initial release.

[unreleased]: https://github.com/acolomba/blackvuesync/compare/v2.2.0...HEAD
[2.2.0]: https://github.com/acolomba/blackvuesync/compare/v2.1.1...v2.2.0
[2.1.1]: https://github.com/acolomba/blackvuesync/compare/v2.0.0...v2.1.1
[2.1]: https://github.com/acolomba/blackvuesync/compare/v2.0.0...44f36e9
[2.0]: https://github.com/acolomba/blackvuesync/compare/1.10...v2.0.0
[1.10]: https://github.com/acolomba/blackvuesync/compare/1.9...1.10
[1.9]: https://github.com/acolomba/blackvuesync/compare/1.8...1.9
[1.8]: https://github.com/acolomba/blackvuesync/compare/1.7...1.8
[1.7]: https://github.com/acolomba/blackvuesync/compare/1.6...1.7
[1.6]: https://github.com/acolomba/blackvuesync/compare/1.5...1.6
[1.5]: https://github.com/acolomba/blackvuesync/compare/1.4...1.5
[1.4]: https://github.com/acolomba/blackvuesync/compare/1.3...1.4
[1.3]: https://github.com/acolomba/blackvuesync/compare/1.2...1.3
[1.2]: https://github.com/acolomba/blackvuesync/compare/1.1...1.2
[1.1]: https://github.com/acolomba/blackvuesync/compare/1.0...1.1
[1.0]: https://github.com/acolomba/blackvuesync/tree/1.0
