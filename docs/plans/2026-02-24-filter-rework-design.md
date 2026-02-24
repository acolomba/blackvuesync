# --include / --exclude filter rework

## Summary

Replace the half-implemented `--filter` option with `--include` and `--exclude`
options that let users select which recording types and directions to download.
Both options accept comma-separated codes. `--exclude` takes priority over
`--include`.

Addresses [#61](https://github.com/acolomba/blackvuesync/issues/61).

## Requirements

- Remove `--filter` / `-f`
- Add `--include` / `-i`: narrows downloads to matching recordings
- Add `--exclude` / `-e`: removes matching recordings from the result
- `--exclude` takes priority over `--include`
- Filter codes are comma-separated, no spaces (e.g. `--include PF,PR`)
- Each code is 1-2 characters: 1 char = type only (all directions),
  2 chars = type + direction
- Invalid codes produce an error and exit (strict validation)
- Docker support via `INCLUDE` and `EXCLUDE` env vars
- Full test coverage: unit and integration

## Parsing & validation

A new `parse_filter` function serves as the argparse `type` parameter for both
`--include` and `--exclude`. This follows the existing `parse_skip_metadata`
pattern.

Input: a single string like `"PF,PR"` or `"P"`.

Behavior:

1. Splits on commas
2. Validates each code:
   - 1 char: must be a valid type character
   - 2 chars: first char must be a valid type, second a valid direction
   - Anything else: raises `argparse.ArgumentTypeError`
3. Returns `tuple[str, ...]`

### Shared constants

Extract valid characters from `filename_re` into constants:

```python
RECORDING_TYPES = "NEPMIOATBRXGDLYF"
RECORDING_DIRECTIONS = "FRIO"
```

Both `filename_re` and `parse_filter` reference these constants. Single source
of truth.

## Matching logic

Replace `get_filtered_recordings` with a function that takes both include and
exclude tuples:

1. Start with all recordings
2. If include is specified, keep only recordings matching any include code
3. If exclude is specified, remove recordings matching any exclude code

A code matches a recording if:

- 1-char code: `recording.type == code`
- 2-char code: `recording.type + recording.direction == code`

Examples:

- `--include P` downloads all Parking recordings (any direction)
- `--exclude NR` downloads everything except Normal Rear
- `--include N --exclude NR` downloads Normal Front, Normal Interior,
  Normal Optional

## Docker support

Add to `blackvuesync.sh`:

```bash
include=${INCLUDE:+--include $INCLUDE}
exclude=${EXCLUDE:+--exclude $EXCLUDE}
```

Append `${include} ${exclude}` to the command line. Comma-separated format
means no quoting issues.

Remove the "filter option not supported in docker implementation" error from
integration test steps.

## Argparse definition

```python
arg_parser.add_argument(
    "-i",
    "--include",
    default=None,
    type=parse_filter,
    help="downloads only recordings matching the given codes; each code is a "
    "recording type optionally followed by a camera direction; e.g. "
    "--include P,NF downloads all Parking and Normal Front recordings",
)
arg_parser.add_argument(
    "-e",
    "--exclude",
    default=None,
    type=parse_filter,
    help="excludes recordings matching the given codes; takes priority over "
    "--include; e.g. --include N --exclude NR downloads all Normal "
    "recordings except Normal Rear",
)
```

## Tests

### Unit tests (`test/blackvuesync_test.py`)

`parse_filter`:

- Valid 2-char codes: `"PF,PR"` -> `("PF", "PR")`
- Valid 1-char code: `"P"` -> `("P",)`
- Mixed: `"P,NF"` -> `("P", "NF")`
- Invalid type char raises `ArgumentTypeError`
- Invalid direction char raises `ArgumentTypeError`
- Invalid length (3+ chars) raises `ArgumentTypeError`
- Empty string raises `ArgumentTypeError`

Matching function:

- Include only: type-only code, type+direction code, multiple codes
- Exclude only: type-only code, type+direction code
- Include + exclude: exclude takes priority
- Neither (both None): all recordings returned

### Integration tests (`features/filter.feature`)

- Sync with `--include` type+direction filter: only matching recordings
  downloaded
- Sync with `--include` type-only filter: all directions downloaded
- Sync with `--exclude`: matching recordings excluded
- Sync with `--include` and `--exclude` combined

## README

Add an `--include` / `--exclude` section documenting syntax, valid codes, and
examples. Include a reference table of type and direction codes.

## Breaking change

`--filter` / `-f` is removed entirely. No backwards compatibility. This is
acceptable because the option was undocumented and half-implemented.
