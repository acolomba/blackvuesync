# Custom image and Portainer preparation

Prepared October 18, 2026. Deployment requires separate approval. No image was built on the production host, no stack was updated, and no container was restarted during implementation.

## Source and behavior

The implementation starts from upstream commit `0b45ef772b645f1473c4e0cef8dd7f08611cb402` (2.2.0 plus upstream unreleased development changes). The workspace originally contained no BlackVueSync source, so a separate clone was created at `/Users/jamiestephens/Documents/containers/blackvuesync` on branch `features/camera-api`. The project fork is [jamie75/blackvuesync](https://github.com/jamie75/blackvuesync); deployment remains a separate approval step.

Previously, every sync called `/accessible`: HTTP 404 selected the legacy index `/blackvue_vod.cgi`, while HTTP 200 selected `/vodList`. Other probe errors failed the run. No supported CLI or Docker override existed. The entrypoint runs `/blackvuesync.sh` once through `su -m dashcam`, then starts cron unless `RUN_ONCE` is set. The inherited environment is also used by cron.

`--camera-api` now flows from `main()` through `sync()` into inventory selection. `auto` preserves detection; `legacy` and `modern` skip it and select the existing legacy boolean. Video download, resume, retention, thumbnail, GPS, and accelerometer implementations are unchanged. Legacy downloads still use `/Record/`, including separate metadata; modern downloads still use the root video URL and `/vodMetadata`, with no accelerometer endpoint.

Docker sets `CAMERA_API=auto`, and the shell wrapper passes it as a quoted CLI argument. The entrypoint rejects unsupported values before user setup or scheduler startup. Python validates the CLI and direct inventory calls. An INFO startup event logs only the chosen mode and respects existing quiet/verbosity settings.

## Read-only deployment evidence

The Docker host was reached as `jstephens1@192.168.1.162`; the alias `docker` did not resolve from this Mac. Container inspection confirmed:

- Container and Compose project/service: `blackvuesync_970`.
- Image reference: `acolomba/blackvuesync`.
- Current image ID: `sha256:5b1ab15304baf9f279b8be3f5335693b43f90c0be2b733f22de344f591adcaa6`.
- Compose label path: `/data/compose/10/docker-compose.yml`. This is a Portainer path, not an assumed host filesystem path.
- Recording bind: `/mnt/camera/970x:/recordings`.
- Camera: `192.168.1.112`.
- Retention: `KEEP=12w`; grouping: `daily`; priority: `rdate`.
- Schedule: `*/15 * * * * /blackvuesync.sh`.
- Other inspected settings: `PUID=1000`, `PGID=0`, `TZ=America/New_York`, `MAX_USED_DISK=90`, `TIMEOUT=10`, `VERBOSE=1`, `CRON=1`.
- Restart policy: `unless-stopped`.

Additional environment variables exist. Preserve the entire current stack definition and environment, including any values not listed here. No credentials were collected or printed. The camera endpoint observations in the task were supplied by the user; implementation testing uses a loopback mock camera.

## Build a versioned image

The following commands are preparation instructions for a later authorized deployment session. Build on the Docker host so the image has its native architecture and is available to the local Portainer endpoint. The proposed image tag is `blackvuesync-local:2.2.0-camera-api.1`; use a new suffix if rebuilding different source.

Transfer this modified source, rather than cloning upstream alone:

```sh
# runs on the Mac after approval for host preparation
ssh jstephens1@192.168.1.162 'mkdir -p /opt/docker/build/blackvuesync-camera-api.1'
rsync -av --exclude='.git' --exclude='venv' --exclude='.venv' \
  --exclude='.env' --exclude='.coverage*' --exclude='coverage*' \
  --exclude='__pycache__' --exclude='.pytest_cache' --exclude='*.egg-info' \
  --exclude='.agents' --exclude='.claude' --exclude='.codex' --exclude='.pi' \
  /Users/jamiestephens/Documents/containers/blackvuesync/ \
  jstephens1@192.168.1.162:/opt/docker/build/blackvuesync-camera-api.1/
```

Then, on the Docker host:

```sh
cd /opt/docker/build/blackvuesync-camera-api.1
docker build --tag blackvuesync-local:2.2.0-camera-api.1 .
docker image inspect blackvuesync-local:2.2.0-camera-api.1 --format '{{.Id}}'
```

The existing Dockerfile keeps the current Alpine base, user switching, and bundled 15-minute cron schedule. The build does not mount recordings or start synchronization. A full Docker build/container integration run remains unverified in this workspace because its local Docker daemon is unavailable.

## Preserve rollback before updating

After approval, export the current Portainer stack YAML and its environment configuration to a secure backup. Do not paste secrets into chat or commit that backup. Reinspect the running image ID in case it changed since this preparation. Save the exact currently running image with a local versioned rollback tag (the command does not recreate the container):

```sh
rollback_image_id=$(docker inspect blackvuesync_970 --format '{{.Image}}')
docker image tag "$rollback_image_id" blackvuesync-local:rollback-20261018
```

Retain this tag and the stack backup until validation is complete. Rollback must use this saved image, since pulling the unversioned upstream reference may fetch different content.

## Portainer Compose change

In Portainer, open the existing `blackvuesync_970` stack editor. Keep its full definition and change only the service image and the new environment setting. This excerpt illustrates the intended final values; it is not a replacement stack:

```yaml
services:
  blackvuesync_970:
    image: blackvuesync-local:2.2.0-camera-api.1
    container_name: blackvuesync_970
    restart: unless-stopped
    volumes:
      - /mnt/camera/970x:/recordings
    environment:
      ADDRESS: 192.168.1.112
      CAMERA_API: legacy
      KEEP: 12w
      GROUPING: daily
      PRIORITY: rdate
      PUID: 1000
      PGID: 0
      TZ: America/New_York
      MAX_USED_DISK: 90
      TIMEOUT: 10
      VERBOSE: 1
      CRON: 1
      # all remaining existing environment entries and service options stay in place
```

Alternatively, `docker-compose.camera-api.yml` is a merge-only Compose overlay containing just the two intended changes. Do not use that overlay as a standalone stack. Portainer's single editor requires merging those two changes into the existing YAML; it does not automatically load a local overlay file.

Before the later update, review that the only differences are `image` and `CAMERA_API`; preserve all retention, scheduling, mount, network, restart, and environment configuration. Keep image re-pulling disabled for this local custom tag; do not enable a forced pull. Leave `RUN_ONCE` as currently configured. Updating the stack recreates the service and starts its initial sync, so the update itself must wait for approval.

## Validation after an approved deployment

Check the new container's image ID against the built image and confirm the unchanged bind mount. Verify the startup log contains `Camera API mode : legacy`, followed by successful inventory/download activity on a reachable camera. For request-level proof in a safe test environment, the regression tests assert the complete request sequence, including absence of `/accessible` in forced modes. Routine production logs alone do not prove request absence.

Confirm retention is still 12 weeks and the cron entry remains every 15 minutes. The camera's host-unreachable errors may still recur: skipping a probe removes a request, but inventory and downloads still depend on connectivity. This is not a confirmed fix for the network error.

## Rollback after approval

Restore the saved original stack definition and environment, but use `blackvuesync-local:rollback-20261018` as its image. Remove the added `CAMERA_API` entry. Update the same Portainer stack with forced image pulling disabled. Confirm the old image ID, unchanged `/mnt/camera/970x:/recordings` mount, environment, and cron schedule.

Do not remove volumes, delete recordings, run `docker compose down -v`, or prune the rollback image. Image rollback does not undo files downloaded or expired by a sync after deployment; existing retention behavior continues in either version.

## Validation results

Executed locally with Python 3.13:

- `scripts/check.sh`: passed the source/test pairing gate, all 185 pytest cases, and the 71% coverage floor (73.89% line/branch combined coverage).
- Modern behavioral suite: 27 scenarios passed, with one legacy-only scenario skipped by the suite's existing protocol tag.
- Legacy behavioral suite: all 28 scenarios passed.
- New regression coverage includes omitted/explicit automatic mode, both forced modes, invalid CLI and direct-call values, invalid Docker startup values, Docker environment-to-CLI argument forwarding, both inventory formats, correct video/metadata paths, and skipping existing downloads on the next run. Forced-mode cases assert the complete HTTP request sequence to prove `/accessible` is never requested.
- `bash -n entrypoint.sh blackvuesync.sh`: passed.
- All applicable pre-commit hooks passed, including Ruff, Black, mypy, pylint, shellcheck, YAML/Markdown checks, source/test pairing, and TruffleHog. The initial hook installer certificate error was resolved using the installed CA bundle; the full hook run was then repeated successfully.
- Docker image build and Docker-based behavioral suites were not run: the local Docker daemon is unavailable. No test containers or build files were added to the production Docker host. These remain validation steps for an approved build session.

## Changed files

- `blackvuesync.py`: CLI option, mode validation/logging, and explicit selection passed through synchronization.
- `blackvuesync.sh`: quoted `CAMERA_API` forwarding, defaulting to `auto` when omitted.
- `entrypoint.sh`: fail-fast environment validation before scheduling.
- `Dockerfile`: default `CAMERA_API=auto`.
- `test/blackvuesync_test.py`: regression cases and updated existing doubles for the new optional parameter.
- `README.md`, `docker-compose.yml`: option reference and default example.
- `docker-compose.camera-api.yml`: merge-only override for the existing service.
- `CHANGELOG.md`: unreleased feature entry.
- `docs/plans/camera-api.md` and this guide: implementation plan, deployment preparation, evidence, and rollback.
