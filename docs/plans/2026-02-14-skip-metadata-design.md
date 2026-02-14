# Skip Metadata Files Design

GitHub issue: #14

## Problem

BlackVue recordings consist of a video file (`.mp4`) and three companion
metadata files (`.thm`, `.3gf`, `.gps`). Some users only want the video files
and consider the metadata files wasted space. Currently there is no way to skip
them, and deleting them externally causes blackvuesync to re-download them.

## Solution

A new `--skip-metadata` CLI option that takes a required string argument. Each
character maps to a metadata file type:

| Character | File type | Extension |
| ----------- | ----------- | ----------- |
| `t` | Thumbnail | `.thm` |
| `3` | Accelerometer | `.3gf` |
| `g` | GPS | `.gps` |

### Examples

- `--skip-metadata t3g` -- skip all metadata files
- `--skip-metadata g` -- skip only GPS
- `--skip-metadata 3g` -- skip accelerometer and GPS

### Validation

A custom argparse type function validates each character against the set
`{'t', '3', 'g'}`. Invalid characters produce an error like:

```text
error: argument --skip-metadata: invalid value 'tx': unknown metadata type 'x' (valid: t, 3, g)
```

### Internal flow

The parsed value becomes a `set[str]` stored in a module-level global (matching
the existing pattern for `dry_run`, `max_disk_used_percent`, etc.). In
`download_recording`, each companion download is guarded by a check against
that set.

### Docker support

A `SKIP_METADATA` env var in `blackvuesync.sh`, following the existing pattern:

```bash
skip_metadata=${SKIP_METADATA:+--skip-metadata $SKIP_METADATA}
```

### Out of scope

No changes to retention/cleanup logic -- skipped files that already exist
locally are left alone; they just won't be downloaded in the future.
