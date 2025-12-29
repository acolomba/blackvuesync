# CHANGELOG

## 2.0a

* Modernize for Python 3.9, now that it's available in Debian Bullseye oldoldstable, the earliest LTS-supported Debian release. Now uses type hints, f-strings; walrus operator.
* Logging uses lazy evaluation.
* Add initial Claude Code settings and AI contribution policy.
* Build Docker images for amd64, arm64, and armv7 architectures. (#12)

## 1.10 (2025-12-28)

* Add `--filter` option to filter which events are downloaded. (#6)
* Add support for the interior camera found on the DR750X-3CH. (#7)
* Download GPS data for all recording types. (#9)
* Flush logs on exit. (#20)
* Silence host/network down/unreachable and timeout in cron mode (inspired by #23).
* Propagate exit status code to calling process. In cron mode, expected errors produce a success exit status.
* Add "rdate" priority, to download from newest to oldest.
* Upgrade alpine image to 3.23.2.

## 1.9 (2021-08-08)

* Properly removes outdated recordings with new event types and upload flags from May 2021 firmware. (#4)

## 1.8 (2021-05-24)

* Supports new event types produced by the May 2021 [BlackVue firmware update](https://blackvue.com/major-update-improved-blackvue-app-ui-dark-mode-live-event-upload-and-more/). (#3)
* The Docker image respects the KEEP option now.
* Docker compose file for a possibly quicker quickstart.
* Friendlier hardware requirement descriptions. (#2)
* More reliable removal of outdated directories when grouping by day, month or year.
* Better handling of unexpected 500 errors or remote disconnections.
* Upgraded docker image to alpine 3.13.5

## 1.7 (2019-07-14)

* Allows grouping recordings by date, with daily, weekly, monthly and yearly granularities.
* Docker image layers are more cacheable.
* Upgraded docker image to alpine 3.10.1

## 1.6 (2019-06-01)

* Logs file/recording download speed to help troubleshoot unreliable/slow Wi-Fi setups.
* Fixed a spurious error log during the first run after midnight.
* Does a better job at cleaning up temp files from interrupted downloads.
* Better handling of network errors while reading the file list.

## 1.5 (2019-03-03)

* Downloads .thm (thumbnail) files for all recordings.
* New ``--priority` switch allows downloading by either a) date or b) type (manual, event, normal, parking in that order.)
* Now downloads front and rear recordings together.

## 1.4 (2019-02-26)

* Downloads gps data for all but parking recording types, and accelerometer data for all.
* 500 errors while downloading are logged but ignored, so we don't get stuck on files we can't download.
* Tests that outdated gps/accelerometer files exist before deleting them, so it doesn't error out.

## 1.3 (2019-02-09)

* Removes gps data for outdated recordings along with the video.
* Gracefully handles low-level socket timeouts.

## 1.2 (2019-02-02)

* Removes temporary files upon successful completion.

## 1.1 (2019-02-01)

* No more sporadically getting stuck forever trying to connect to the dashcam.
* Connection timeout defaults to 10 seconds and is configurable.

## 1.0 (2019-01-30)

* initial release
