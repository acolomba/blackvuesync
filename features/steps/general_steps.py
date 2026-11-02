"""general step definitions: exit status."""

from behave import then
from behave.runner import Context
from hamcrest import assert_that, contains_string, equal_to, not_
from hamcrest.core.matcher import Matcher


@then("blackvuesync exits with code {code:d}")
def assert_exit_code(context: Context, code: int) -> None:
    """verifies the exit code of the latest run."""
    result = context.result
    assert_that(
        result.exit_code,
        equal_to(code),
        f"exit code differs\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}",
    )


@then('stderr contains "{message}"')
def assert_stderr_contains(context: Context, message: str) -> None:
    """checks an actionable error or debug message on stderr."""
    assert_that(context.result.stderr, contains_string(message))


@then('stderr does not contain "{message}"')
def assert_stderr_omits(context: Context, message: str) -> None:
    """checks that routine runs omit the selected message."""
    stderr: str = context.result.stderr
    omitted_message: Matcher[str] = not_(contains_string(message))
    assert_that(stderr, omitted_message)


@then("stderr reports an invalid camera api")
def assert_invalid_camera_api(context: Context) -> None:
    """checks that invalid input produces the entry point's validation message."""
    message = (
        "Invalid CAMERA_API" if context.implementation == "docker" else "invalid choice"
    )
    assert_that(context.result.stderr, contains_string(message))
