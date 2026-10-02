---
name: python-google-style-review
description: Review Python source against the Google Python Style Guide as this project adopts it -- the rules the toolchain does not enforce. Use when reviewing or revising .py files.
---

# Google style review

Points this project decides for itself, rather than taking from the guide, are marked *(project)*.

Review the files in the change under review. New files follow the rules completely; in an existing file, new code follows the file's conventions where the rules are silent but never violates a rule. Do not demand cleanups of unchanged code. Flag style-only churn mixed into a functional change; style-only edits go in their own change.

## Gate on the toolchain first

Confirm `pre-commit run --files <changed files>` passes. A failure is itself a finding; do not hand-review what the tools report. The toolchain gates: formatting, indentation, quotes, trailing commas, and line length (black, at 88 columns rather than the guide's 80 *(project)*), import order and grouping (ruff `I`), naming conventions (ruff `N`), unused imports, variables, and arguments (ruff `F`, `ARG`), mutable default arguments and other bugbear patterns (ruff `B`), bare `except:` and `== None` / `== True` comparisons (ruff `E`), assigned lambdas, outdated syntax such as `typing.List` (ruff `UP`), comprehension, `return`, and `if` simplifications (ruff `C4`, `RET`, `SIM`), complete type annotations with no implicit `Any` or implicit `Optional` (mypy `--strict`), and missing docstrings and `global` statements in `blackvuesync.py` (pylint). Do not open findings for these when the gate is green.

Where a rule overlaps a linter, review the part the linter cannot judge: every `# noqa`, `# type: ignore`, and `# pylint: disable` names the specific code (`# type: ignore[attr-defined]`, `# pylint: disable=protected-access`), carries a reason, and the reason holds for that line.

## Quick scan

Grep the changed files for these tokens; every hit needs a stated justification or becomes a finding:

`from x import *` · `global` · `nonlocal` · `eval(` / `exec(` / `compile(` · `__import__` / `importlib.import_module` · `getattr(` / `setattr(` / `hasattr(` with a literal name · `@staticmethod` · `assert` in `blackvuesync.py` · `except Exception` / `except BaseException` · `cast(` · `Any` · `TYPE_CHECKING` · `__del__` · `metaclass=` · `shell=True` · `pickle` · a `\` line continuation · `;` · an f-string or `.format()` inside a logging call · `datetime.now()` / `time.time()` / `uuid.uuid4()` / `os.environ` inside logic.

## Statements and formatting the tools do not check

- One statement per line; `if x: y()` on one line only when there is no `else`.
- No backslash line continuations; implicit joining inside parentheses instead. Long URLs and `# pylint: disable` comments may exceed the line length.
- Parentheses only where they group or join lines: none around a `return` value, an `if` or `while` condition, or a `for` target, unless the expression spans lines or is a tuple.
- A shebang only on a file meant to run directly: `#!/usr/bin/env python3`.

## Imports

- Absolute imports only; no relative imports, even inside the package.
- Classes, functions, and modules are imported by name alike: `from pathlib import Path`, `from blackvuesync.orders import order_service`. A module import (`import json`) when its names are generic (`json.loads`) or used from many places. *(project)*
- `import x as y` only for a standard abbreviation (`import numpy as np`), to avoid a collision, or to shorten an inconveniently long name.
- Imports needed only for annotations go under `if TYPE_CHECKING:` only to break an import cycle; a cycle is itself a design smell to report.

## Exceptions

- Raise built-in exceptions where they fit (`ValueError` for a violated precondition); a custom exception inherits from an existing exception class and its name ends in `Error`.
- `assert` never validates arguments or state in `blackvuesync.py`: `python -O` strips it. Raise instead.
- No catch-all `except Exception:` or `except BaseException:` unless it re-raises, or sits at an isolation boundary (a thread's top, a request handler, `main()`) and records the error.
- A `try` block covers only the statements that can raise; the rest sits in `else` or after it. Cleanup goes in `finally` or a `with` statement.
- An `except` block that only passes carries a comment stating why ignoring the error is correct.
- Error messages match the actual condition precisely, name the offending value, and stay greppable: `f"unknown order {order_id!r}"`.

## Global state and structure

- No mutable module-level state. Module-level constants are `CONSTANT_CASE`; an unavoidable mutable global is `_private` and reached through functions.
- A nested function or class only when it closes over a local value; a helper hidden from users becomes a `_private` module-level function instead.
- No `@staticmethod`; a module-level function instead. `@classmethod` only for a named constructor (`Order.from_row()`) or a class-specific routine.
- Properties only for cheap, side-effect-free computed attributes; no property that merely gets or sets an attribute, which stays a public attribute. Getter and setter methods (`get_x()`, `set_x()`) only when access is costly or meaningful.
- No power features: metaclasses, bytecode access, dynamic inheritance, object reparenting, import hacks, reflection shortcuts (`getattr` over a known name), `__del__` for cleanup, or changes to built-ins or other modules' attributes. `abc`, `dataclasses`, `enum`, and `functools` are fine.
- Plain data is a `@dataclass` (`frozen=True` when it never changes) or a `NamedTuple`, not a dict with fixed keys; a `TypedDict` only for data that crosses a JSON or other untyped boundary. A dependency a module calls through is a `typing.Protocol` declared by the consumer. *(project)*
- Executable code runs under `if __name__ == "__main__":`; module import has no side effects beyond definitions.
- Prefer small, focused functions; a function past about 40 lines is a hint to split it.

## Expressions and idioms

- Comprehensions and generator expressions stay simple: one `for` clause and at most one `if`. Anything more is a loop.
- Default iteration and membership: `for key in mapping`, `if key in mapping`, `for line in file`, never `.keys()` for these. No mutating a container while iterating over it.
- Lambdas fit on one line; a common operation uses `operator` (`operator.itemgetter(1)`) instead.
- A conditional expression only when each part fits on one line.
- No default argument evaluated with a side effect or a time-dependent value at import: `def f(now=time.time())` is a finding.
- Implicit false for sequences (`if not orders:`), but `is None` / `is not None` for `None`, and explicit comparisons (`if count == 0:`) where `0`, `""`, or an empty container is a valid value.
- Strings: f-strings for formatting; no `+` concatenation in a loop (collect and `"".join()`); `textwrap.dedent()` for multi-line literals.
- Logging calls pass a literal pattern and arguments, not an f-string: `logger.info("placed order %s", order_id)`.
- Files, sockets, locks, and other stateful resources close through `with`, or through `contextlib.closing()` / `ExitStack`.

## Naming

| Style           | Used for                                                             |
| --------------- | -------------------------------------------------------------------- |
| `CapWords`      | class, exception, type alias, `Protocol`, `TypeVar` (`_T`, `OrderT`) |
| `snake_case`    | module, package, function, method, variable, parameter, attribute    |
| `CONSTANT_CASE` | module-level constant                                                |

- Names are descriptive to a new reader; no ambiguous or project-private abbreviations, no dropped letters; single letters only for counters and iterators (`i`, `j`, `k`), `e` for a caught exception, and `f` for a file handle in a `with` statement.
- No type in the name (`id_to_name_dict`); no dashes in module names; no invented `__dunder__` names.
- A leading underscore marks module or class internals; no double leading underscore (name mangling).

## Types

- Every function signature is annotated (mypy enforces it); `self` and `cls` are not.
- A variable is annotated when inference is insufficient or a reader cannot see the type: `orders: dict[str, Order] = {}`.
- `cast()` and `# type: ignore[code]` only with a comment stating why the checker is wrong; a runtime check (`isinstance`) is preferred.
- Built-in generics (`list[int]`, `dict[str, Order]`), and `collections.abc` for abstract parameter types (`Sequence[Order]`, `Mapping[str, int]`); a function returns a concrete type.
- `tuple[int, ...]` for a variable-length tuple; a pair returns `tuple[A, B]` or a `NamedTuple`.
- A type alias is `CapWords` and annotated with `TypeAlias` (or declared with `type` on Python 3.12+).
- `Any` is avoided in favor of a specific type, a `TypeVar`, a `Protocol`, or `object`; an unavoidable `Any` carries a comment stating why.
- `str` for text, `bytes` for binary data; never `str` for bytes.

## Docstrings and comments

Follow `skills/python-comments/SKILL.md` for wording. Docstrings are lowercase and in the third person. *(project)*

- Docstrings use `"""`. The first line is a one-line summary ending in a period; a longer docstring leaves a blank line after it.
- Every module in `blackvuesync.py` starts with a docstring stating what it holds. A test module needs none.
- Every public function, method, and class has a docstring, as does any private one of nontrivial size or non-obvious logic. A function docstring describes the call, not the implementation: `"""returns the orders placed today."""`.
- `Args:`, `Returns:` (or `Yields:`), and `Raises:` sections only where they add information beyond the names and annotations; no types repeated in them. `Raises:` lists the exceptions that are part of the interface.
- A class docstring says what an instance represents; public attributes that need explaining go in an `Attributes:` section.
- Block and inline comments explain the tricky parts. They never restate the code.
- A `TODO` names the issue that tracks it when one exists: `# TODO: #123 - drop the fallback once the API returns ids`.

## Classifying findings

- **BLOCKER** when the violation can produce incorrect behavior or hide a defect: `assert` used for validation in `blackvuesync.py`, a catch-all `except` that swallows errors away from an isolation boundary, a `cast()` or `# type: ignore` whose reason does not hold, an implicit-false test where `0` or an empty value is valid, mutating a container while iterating over it, a default argument evaluated with a side effect, a resource not closed through `with`, a power feature, or mutable module-level state.
- **WARNING** otherwise: naming, documentation, import form, structure, and idiom findings degrade maintainability, not behavior.
