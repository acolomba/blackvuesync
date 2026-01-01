"""general assertion step definitions"""

from behave import then
from behave.runner import Context
from hamcrest import assert_that, equal_to


@then("blackvuesync exits with code {code:d}")
def assert_blackvuesync_exit_code(context: Context, code: int) -> None:
    """verifies that blackvuesync exited with the expected code."""
    # validates prerequisites
    if not hasattr(context, "exit_code"):
        raise RuntimeError(
            "Cannot verify exit code: blackvuesync has not been run yet. "
            "This test scenario is missing the 'When blackvuesync runs' step."
        )

    assert_that(
        context.exit_code,
        equal_to(code),
        f"Expected exit code {code}, but got {context.exit_code}",
    )
