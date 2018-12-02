# BlackVue Sync

Synchronizes recordings from a BlackVue dashcam with a local directory over a LAN.

BlackVue dashcams expose an HTTP server -- sadly no HTTPS, that can be used to download all recordings. This project downloads only recordings that are not already downloaded, optionally limiting recordings in a local directory to a date range.

A typical setup would be a periodic cron job or a docker container running on a local server.


## Features

* *Portable runtimes:* 
    * A [single, self-contained Python script](https://github.com/acolomba/blackvuesync/blob/master/blackvuesync.py) with no third-party dependencies that can be can just be copied and run anywhere either [manually](#manual-usage) or [periodically](#unattended-usage); or:
    * A [docker image](#docker) that runs said script periodically via an internal cron job.
* *Smart*: Only downloads recordings that haven't been downloaded yet.
* *Resilient*: If a download interrupts for whatever reason, at the next run the script resumes where it left off. This is especially useful for possibly unreliable Wi-Fi connections from a garage.
* *Hands-off*: Optionally retains recordings for a limited amount of time, removing outdated ones.
* *Cron-friendly*: Only one process is allowed to run at any given time for a specific download destination.
* *Safe*: Stops executing if the disk is almost full.
* *Friendly*: Identifies a range of known error conditions and clearly communicates them.


## Prerequisites

* [Python](https://www.python.org/) 3.5+ or [Docker](https://docs.docker.com/).
* A [BlackVue](https://www.blackvue.com/) dashcam connected to the local network with a fixed IP address.
* Recordings must be downloaded to a destination on a local filesystem.

### Compatibility

Tested with: `DR750S`

Untested, but should work with: `DR900S`, `DR650S`, `DR590/590W`, `DR490/490L` Series.

Reports of models working or not other than those tested are appreciated.

### Verifying connectivity to the dashcam

For all examples, we will assume that the camera address is ```dashcam.example.net```. A numerical IP address works just as well.

A quick way to verify that the dashcam is available is by using curl. 

```
$ curl http://dashcam.example.net/blackvue_vod.cgi
v:1.00
n:/Record/20181026_135003_PF.mp4,s:1000000
n:/Record/20181026_140658_PF.mp4,s:1000000
n:/Record/20181026_140953_PF.mp4,s:1000000
...
$
```

Another way is to simply browse to: `http://dashcam.example.net/blackvue_vod.cgi`.


## Usage

### Manual Usage

The dashcam address is the only required parameter. Specifying ```--dry-run``` makes it so that the script communicates what it would do without actually doing anything. Example:

```
$ blackvuesync.py dashcam.example.net --dry-run
```

It's also possible to specify a destination directory other than the current using ```--destination```:

```
$ blackvuesync.py dashcam.example.net --destination /mnt/dashcam --dry-run
```

A retention period can be indicated with ```-keep``` -- e.g. two weeks. Recordings prior to the retention period will be removed from the destination. Accepted units are ```d``` for days and ```w``` for weeks. If no unit is indicated, days are assumed. 

```
$ blackvuesync.py dashcam.example.net --destination /mnt/dashcam --keep 2w --dry-run
```

A typical invocation would then be:

```
$ blackvuesync.py dashcam.example.net --destination /mnt/dashcam --keep 2w
```

Other options:
* ```--max-used-disk```: Downloads stop once the specified used disk percentage threshold is reached. Defaults to 90%.
* ```--quiet```: Quiets down output messages, except for unexpected errors. Takes precedence over ```-verbose```.
* ```--verbose```: Increases verbosity. Can be specified multiple times to indicate additional verbosity.

### Unattended Usage

#### Plain cron

The script can be automatically run periodically by setting up a [cron](https://en.wikipedia.org/wiki/Cron) job on UNIX systems.

Simple example with crontab for a hypothetical ```media``` user:

```
*/15 * * * * /home/media/bin/blackvuesync.py dashcam.example.net --keep 2w --destination /mnt/dashcam --cron
```

The ```--cron``` option changes the logging level with the assumption that the output will be emailed. When this option is enabled, the script will only log when normal recordings are downloaded and when unexpected error conditions occur. One would typically see an email only after driving or when something goes wrong.

Note that if the dashcam is unreachable for whatever reason, in ```--cron``` mode no output is generated, since this is an expected condition whenever the dashcam is away from the local network.

#### NAS

##### openmediavault

The [openmediavault](http://www.openmediavault.org/) NAS solution allows for [scheduled jobs](https://openmediavault.readthedocs.io/en/latest/administration/general/cron.html) with support for mail notifications.

Example:

![openmediavault Scheduled Job](https://raw.githubusercontent.com/acolomba/blackvuesync/master/docs/images/cron-example-openmediavault.png)

#### Docker

##### Overview

The [acolomba/blackvuesync](https://hub.docker.com/r/acolomba/blackvuesync/) docker image sets up a cron job internal to the container that runs the synchronization operation every 15 minutes.

##### Quick Start

It's a good idea to do a single, interactive dry run first with verbose logging: 

```
docker run -it --rm \
    -e ADDRESS=dashcam.example.net \
    -e DRY_RUN=1 \
    -e VERBOSE=1 \
    -e RUN_ONCE=1 \
    --name blackvuesync \
acolomba/blackvuesync
```

Once that works, a typical invocation would be similar to:

```
docker run -d --restart unless-stopped \
    -e ADDRESS=dashcam.example.net \
    -v /mnt/dashcam:/recordings \
    -e PUID=$(id -u)
    -e PGID=$(id -g)
    -e TZ="America/New_York"
    -e KEEP=2w \
    --name blackvuesync \
acolomba/blackvuesync
```

##### Reference

To operate correctly, the docker image requires at a minimum:

* The ```ADDRESS``` parameter set to the dashcam address.
* The ```/recordings``` volume mapped to the desired destination of the downloaded recordings.
* The ```PUID``` and ```PGID``` parameters set to the desired destination directory's user id and group id. 
* The ```TZ``` parameter set to the same timezone as the dashcam. Note that BlackVue dashcams do not respect Daylight Savings Time, so their clock needs to be adjusted periodically.

Other parameters:

* ```KEEP```: Sets the retention period of downloaded recordings. Recordings prior to the retention period will be removed from the destination. Accepted units are ```d``` for days and ```w``` for weeks. If no unit is indicated, days are assumed. (Default: empty, meaning recordings are kept forever.)
* ```MAX_USED_DISK```: If set to a percentage value, stops downloading if the amount of used disk space exceeds the indicated percentage value.  (Default: 90, i.e. 90%.)
* ```VERBOSE```: If set to a number greater than zero, increases logging verbosity. (Default: 0.)
* ```QUIET```: If set to a value, quiets down logs; only unexpected errors will be logged. (Default: empty.)
* ```CRON```: Set by default, makes it so downloads of normal recordings and unexpected error conditions are logged. Can be set to ```""``` to disable.
* ```DRY_RUN```: If set to a value, makes it so that the script communicates what it would do without actually doing anything. (Default: empty.)
* ```RUN_ONCE```: If set to a value, the docker image runs the sync operation once and exits without setting up the cron job. (Default: empty.)


## License

This project is licensed under the MIT License - see the [COPYING](COPYING) file for details

Copyright 2018 [Alessandro Colomba](https://github.com/acolomba)
