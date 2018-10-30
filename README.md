# BlackVue Sync

Synchronizes recording from a BlackVue dashcam with a local directory over a LAN.

BlackVue cameras expose an HTTP server -- sadly no HTTPS -- that can be used to download all recordings. This projects downloads only recordings that are not already downloaded.

## Prerequisites

* Python 3.5+.
* A BlackVue dashcam. Tested with a DR750S.
* The BlackVue dash cam needs to be connected your LAN and reachable.

A quick way to verify that the camera is available is by using curl. For all examples, we will assume that the camera address is ```blackvue.home.net```.

```
$ curl http://blackvue.home.net/blackvue_vod.cgi
v:1.00
n:/Record/20181026_135003_PF.mp4,s:1000000
n:/Record/20181026_140658_PF.mp4,s:1000000
n:/Record/20181026_140953_PF.mp4,s:1000000
...
$
```

Another way is to simply browse to ```http://blackvue.home.net/blackvue_vod.cgi```.

### Usage

The most basic usage is to pass the dashcam address to the script:

```
$ blackvuesync.py blackvue.home.net
```

It's also possible to specify a destination directory other than the current:

```
$ blackvuesync.py blackvue.home.net --destination /mnt/blackvue
```

## License

This project is licensed under the MIT License - see the [COPYING](COPYING) file for details

Copyright 2018 [Alessandro Colomba](https://github.com/acolomba)
