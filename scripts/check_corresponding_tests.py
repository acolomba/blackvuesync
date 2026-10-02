"""checks the pairing between root-level application modules and test/.

blackvuesync.py pairs with test/blackvuesync_test.py. each test module imports
its source module; test support and developer scripts are outside this gate.
"""

import ast
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
SOURCE_ROOT = PROJECT_ROOT
TEST_ROOT = PROJECT_ROOT / "test"
TEST_SUFFIX = "_test.py"


def module_name(source: Path) -> str:
    """returns the import path of a root-level application module."""
    return source.stem


def tested_module(test: Path) -> str:
    """returns the import path of the module a test module pairs with."""
    parts = test.relative_to(TEST_ROOT).parts
    return ".".join((*parts[:-1], parts[-1].removesuffix(TEST_SUFFIX)))


def expected_test(module: str) -> Path:
    """returns the path of the test module a module pairs with."""
    *packages, name = module.split(".")
    return TEST_ROOT.joinpath(*packages, f"{name}{TEST_SUFFIX}")


def imported_modules(test: Path) -> set[str]:
    """returns every import path a module imports, including the names it
    imports from a package, which may be modules."""
    modules: set[str] = set()
    for node in ast.walk(ast.parse(test.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Import):
            modules.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module and node.level == 0:
            modules.add(node.module)
            modules.update(f"{node.module}.{alias.name}" for alias in node.names)
    return modules


def problems() -> list[str]:
    """returns a line for each unpaired module."""
    sources = {module_name(path): path for path in sorted(SOURCE_ROOT.glob("*.py"))}
    found: list[str] = []

    for module, source in sources.items():
        test = expected_test(module)
        if not test.is_file():
            found.append(
                f"missing test {test.relative_to(PROJECT_ROOT)} "
                f"for {source.relative_to(PROJECT_ROOT)}"
            )
        elif module not in imported_modules(test):
            found.append(f"{test.relative_to(PROJECT_ROOT)} does not import {module}")

    for test in sorted(TEST_ROOT.rglob(f"*{TEST_SUFFIX}")):
        if tested_module(test) not in sources:
            found.append(
                f"missing source module {tested_module(test)} "
                f"for {test.relative_to(PROJECT_ROOT)}"
            )

    return found


def main() -> int:
    """prints the unpaired modules and returns the exit status."""
    found = problems()
    if not found:
        print("corresponding-tests gate passed.")
        return 0
    for problem in found:
        print(problem, file=sys.stderr)
    print(
        f"corresponding-tests gate failed with {len(found)} problem(s).",
        file=sys.stderr,
    )
    return 1


if __name__ == "__main__":
    sys.exit(main())
