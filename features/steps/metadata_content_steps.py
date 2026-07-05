"""metadata content verification step definitions"""

from pathlib import Path

from behave import then
from behave.runner import Context
from hamcrest import assert_that, equal_to, not_

_MOCK_FILES_DIR = Path(__file__).parent.parent / "mock_dashcam" / "files"


@then('the downloaded "{extension}" files match the mock fixture')
def assert_downloaded_files_match_fixture(context: Context, extension: str) -> None:
    """verifies every downloaded file of the given extension equals the mock fixture."""
    expected_bytes = (_MOCK_FILES_DIR / f"mock.{extension}").read_bytes()

    downloaded = [f for f in context.dest_dir.rglob(f"*.{extension}") if f.is_file()]
    assert_that(downloaded, not_(equal_to([])))
    for downloaded_file in downloaded:
        assert_that(downloaded_file.read_bytes(), equal_to(expected_bytes))
