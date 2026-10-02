"""general step definitions: exit status."""

from behave import then
from behave.runner import Context


@then("blackvuesync exits with code {code:d}")
def assert_exit_code(context: Context, code: int) -> None:
    """verifies the exit code of the latest run."""
    result = context.result
    assert result.exit_code == code, (
        f"expected exit code {code}, got {result.exit_code}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
