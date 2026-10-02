"""general step definitions: exit status."""

from behave import then
from behave.runner import Context
from hamcrest import assert_that, equal_to


@then("blackvuesync exits with code {code:d}")
def assert_exit_code(context: Context, code: int) -> None:
    """verifies the exit code of the latest run."""
    result = context.result
    assert_that(
        result.exit_code,
        equal_to(code),
        f"exit code differs\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
    )
