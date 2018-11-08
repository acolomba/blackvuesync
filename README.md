# BlackVue Sync

Synchronizes recording from a BlackVue dashcam with a local directory over a LAN.

BlackVue cameras expose an HTTP server -- sadly no HTTPS -- that can be used to download all recordings. This project downloads only recordings that are not already downloaded.

## Features

* *Portable:* Implemented as a single, self-contained Python script with zero dependencies. Can just be copied and run anywhere.
* *Smart*: Only downloads recordings that haven't been downloaded yet.
* *Resilient*: If the data transfer is interrupted for whatever reason, the script resumes where it left off at the next run.
* *Hands-off*: Optionally maintains recordings for a limited amount of time, removing outdated ones.
* *Cron-friendly*: Only one process is allowed to run at any given time for a sync destination.
* *Safe*: Stops executing if the disk is almost full.
* *Friendly*: Identifies error conditions and clearly communicates them.


## Prerequisites

* Python 3.5+.
* A BlackVue dashcam. Tested with a DR750S.
* The BlackVue dashcam needs to be connected your LAN and reachable.
* The destination directory must be on the local filesystem. Locking will not work with network shares.

### Verifying connectivity to the dashcam

A quick way to verify that the dashcam is available is by using curl. For all examples, we will assume that the camera address is ```dashcam.home.net```.

```
$ curl http://dashcam.home.net/blackvue_vod.cgi
v:1.00
n:/Record/20181026_135003_PF.mp4,s:1000000
n:/Record/20181026_140658_PF.mp4,s:1000000
n:/Record/20181026_140953_PF.mp4,s:1000000
...
$
```

Another way is to simply browse: `http://dashcam.home.net/blackvue_vod.cgi`.

### About locking

The script writes a hiden lock file to the destination directory, and then locks it. When the script terminates -- successfully or not -- the lock file is unlocked, but it remains in the destination directory. This is expected.

## Usage

The most basic usage is to pass the dashcam address to the script:

```
$ blackvuesync.py dashcam.home.net
```

It's also possible to specify a destination directory other than the current:

```
$ blackvuesync.py dashcam.home.net --destination /mnt/blackvue
```

A rentention period can be indicated, e.g. two weeks. Older recordings will be removed.

```
$ blackvuesync.py dashcam.home.net --destination /mnt/blackvue --keep 2w
```

## Compatibility

Tested with: `DR750S`

Should work with: `DR900S`, `DR750S`, `DR650S`, `DR590/590W`, `DR490/490L` Series

Reports of  models working or not other than those tested are appreciated.

## License

This project is licensed under the MIT License - see the [COPYING](COPYING) file for details

Copyright 2018 [Alessandro Colomba](https://github.com/acolomba)
