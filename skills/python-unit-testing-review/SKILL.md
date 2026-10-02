---
name: python-unit-testing-review
description: Review Python unit tests against the project's unit testing rules -- pairing, coverage, structure, assertions, test doubles, hermeticity, and testable production design. Use when reviewing or revising test/**/*.py or the source modules they pair with.
---

# Python unit testing review

When revising, produce the **Good** form from `skills/python-unit-testing/SKILL.md`.

The central question for every case: **would a plausible wrong implementation still pass it?** Every case must discriminate the behavior named in its title -- a wrong implementation makes the assertion fail. A test with weak assertions costs all the maintenance of a test and gives none of the protection; that is the highest-value finding this review can produce.

## Verify with the toolchain

Run `pytest <test-path>` for the module under review and `scripts/coverage-direct.sh <source-path> <test-path>` for the source-test pair. A red command, or a review that never ran them, is itself a finding.

Run `scripts/check.sh` only when the change touched a shared contract, fake, `conftest.py`, or gate script. Otherwise the writer's green run and CI already cover the whole gate; a third run adds nothing.

## Tools

- Runner, fixtures, `monkeypatch`, `tmp_path`, and `pytest.raises()` come from pytest; assertions are PyHamcrest `assert_that()` calls with matchers; strict interaction mocks come from `unittest.mock.create_autospec()` and spies from `Mock(wraps=...)`; coverage comes from pytest-cov.
- `unittest.TestCase`, `pytest-mock`, `pytest-asyncio`, `freezegun`, `responses`, or a snapshot plugin in a unit test is a finding.

## Pairing and coverage

- The root-level application module `blackvuesync.py` pairs with `test/blackvuesync_test.py`, which imports it and owns its public behavior. Developer scripts and behavioral-test support are outside this pairing gate.
- No exclusions: re-exporting `__init__.py` modules, `__main__.py`, type-only modules, and one-function modules all pair. Only an `__init__.py` with nothing but a docstring is exempt. A module not worth a test gets folded into its consumer, not skipped.
- No tests under `src/`, no `test_*.py` names, no source module tested from another module's test. Test support (fakes, seeds, `conftest.py` fixtures) needs no meta-tests.
- The unit suite measures line and branch coverage and meets the coverage floor configured in `pyproject.toml`. Raise coverage as behavior changes; 100% is not a migration requirement.

## Case structure

- Independent pytest functions. No committed `skip`, `skipif`, or `xfail` marks and no `pytest.skip()` or `pytest.xfail()` calls, except the strict `xfail` broken participant of a shared contract.
- Test classes only one level deep, one per public entrypoint, and only when the module has several; no nesting, no grouping by private helpers, no class with `__init__`, attributes, or `setup_method()`.
- Fresh state and dependencies per case, preferably constructed inside the case. Fixtures holding stateful objects are function-scoped; only a stateless stub (a fixed `clock`) lives at module scope.
- Names state public behavior in a short snake-case sentence (`test_rejects_an_unknown_order`), never `test_works`, `test_happy_path`, or plan/phase/ticket references (a durable requirement ID may appear). A docstring restating the name is a finding.
- Phases marked with lowercase `# arrange`, `# act`, `# assert` in order, separated by blank lines; a `pytest.raises()` block is the act, and `# act & assert` marks it only when it is the whole assertion. No other comments unless setup is not obvious.

## Naming

- Values named after their production role: `order_service`, `order`, `expected_order` or the seed fixture `placed_order`, `put_spy`, `raised`, parametrized arguments `lines, total`.
- `result`, `res`, `ret`, `data`, `value`, `instance`, `subject`, `sut`, or a bare `actual` is a finding.
- A double is named for its role only (`orders`, `payments`, `clock`) -- no `mock`/`fake`/`stub` in the name; how it is created shows the kind.

## Assertions

- Conditions are stated with `assert_that(actual, matcher)`, so the matcher names the condition and a failure reports the expected and the actual value. A plain `assert` where a matcher states the condition is a finding; a plain `assert` for a condition that no matcher states is not. A reason passed as the third argument adds a fact the matcher does not report.
- The public result and public state are asserted before any interaction check; a call assertion never replaces a result assertion. A relocated case keeps its assertions unless the contract changed -- a revision that weakens assertions is a finding even when the tests still pass.
- Whole values compared with `equal_to()`, lists whose order is not the promise with `contains_inanyorder()`, identity with `same_instance()`. Asserting existence, length, or one attribute at a time when the whole value is the promise is a finding, and so is a matcher that passes for a partial value: `has_item()`, `has_items()`, `has_entries()`, `has_length()`, `instance_of()`. A standalone negative assertion (`assert_that(x, not_none())`, `assert_that(x, is_not(y))`) passes for almost any value; the test must assert what the value *is*.
- Errors asserted by class with `pytest.raises()` and by structured fields afterwards, not by message text; `match=` is a finding.
- When bytes are the contract (file, packet, archive, encoded value), the complete bytes are compared, with no decoding or normalizing consumers do not perform.
- Expected values are built independently: no calling the production formatter or serializer, no transforming the adapter result, no asking a harness for the answer, no snapshot assertions.
- An `async def` entrypoint is driven with `asyncio.run()` and every coroutine is awaited; a never-awaited coroutine fails under `filterwarnings = ["error"]`, and a filter added to silence it is a finding.

## Test doubles

Check the tool matches the role:

| Role | Use                                            | Assert                                                                |
| ---- | ---------------------------------------------- | --------------------------------------------------------------------- |
| Fake | A working, simplified, stateful implementation | The public result and resulting state                                 |
| Stub | A canned value or error that drives one path   | The module's result, not the stub's call count                        |
| Spy  | Real behavior with recorded calls              | Public behavior first; calls only when the observation is the promise |
| Mock | A prescribed interaction                       | The promised calls, arguments, and order                              |

- A stub with call assertions has been turned into a mock -- a finding. Incidental spy calls are not verified.
- **Fakes** stand in for stateful boundaries, live in the concern's `conftest.py`, are handed out fresh by a function-scoped fixture, are seeded through their public contract, and `copy.deepcopy()` mutable values at ingress and egress; not a graph of mocks, not a second real implementation.
- **Stubs** are plain functions or small classes that satisfy the port (`def ids() -> str: return "order-123"`); `Mock(side_effect=[...])` only when a plain function is not enough.
- **Spies** are `Mock(wraps=obj.method)` installed with `monkeypatch.setattr()`, only when real behavior must run and the observation is the promise; with a `return_value` or `side_effect` it is a stub.
- **Mocks** are `create_autospec()`, only where the interaction is public behavior (charging, publishing, notifying, transaction control, callbacks, commands):
  - created inside the case as `create_autospec(Port, instance=True, spec_set=True)` -- a bare `Mock()`/`MagicMock()`, or one missing `spec_set`, accepts calls and attributes the port does not have;
  - every return value and error the module uses is set; an unset autospecced method returns a `MagicMock` that hides the gap;
  - the case ends with a whole-list assertion, `assert_that(port.mock_calls, equal_to([call...]))`, after result and state assertions; `assert_called()`, `assert_called_once()`, `assert_any_call()`, `assert_has_calls()`, or a bare `call_count` passes with extra calls and is a finding; so is an assertion hidden in a fixture teardown or shared helper;
  - `ANY` only for an argument that cannot be compared by value, with its meaningful properties asserted separately;
  - an empty expected list, `assert_that(port.mock_calls, equal_to([]))`, is a legitimate proof that the module does not touch that port.
- When order across mocks is the promise, every mock is attached to one recorder with `attach_mock()` and the recorder's whole `mock_calls` list is compared.
- Plain data (`Cart`, `Order`) is a real instance, not a double. Logging gets a silent stub or goes unobserved; log records are asserted only in a module whose job is logging.
- Every double comes from the case or a function-scoped fixture, and every attribute, item, or environment change goes through `monkeypatch`. Patching a module's names (`mock.patch("blackvuesync.orders.datetime")`, `monkeypatch.setattr("blackvuesync.orders.requests", ...)`) is a finding -- the dependency gets injected instead.

## Test data

- Short self-describing literals (`"order-123"`, `"customer-1"`); no realistic prose, random generators, or long fixture blobs.
- Production types built for real (`Order(...)`), not dicts standing in for them, setting only what the case is about: `dataclasses.replace(placed_order, status="cancelled")`.
- Cross-case seeds are function-scoped fixtures in the concern's `conftest.py` returning fresh values -- never shared mutable constants. No test data computed with production code.

## Data-driven cases

- One case per row via `@pytest.mark.parametrize`, each row with an `id` that states it.
- Rows looped inside one case (stops at first failure) or a conditional in the case body (different branches belong in separate named cases) are findings.

## Types and hermeticity

- Tests pass mypy `--strict` like production; `Any`, `cast()`, or `# type: ignore` hiding an invalid double is a finding -- the production contract gets narrowed instead (a consumer-declared `Protocol`, doubles mypy checks where the port is expected).
- Cases run offline, in any order, with no credentials or developer setup. HTTP APIs, brokers, cloud services, identity providers, and remote repositories are faked, with no live-service fallback; a real adapter runs only against `tmp_path` or a loopback-only service owned by the case.
- No process global shared across cases without restoration. No production reset function added to clean up after a test.

## Test support organization

- Fakes, seeds, contracts, and fixtures sit in the `conftest.py` of their concern (`test/blackvuesync/orders/conftest.py`). A test module importing another test or support module, or a `test/helpers/`, `test/utils/`, or `test/mocks/` directory, is a finding. A `fixtures/` directory only where a concern has enough static files to need one.

## Production design for tests

- A test uses only the module's public names. A name made public, a reset hook, global mutator, state reader, test mode, or a `_private` member reached from a test is a finding -- the production design changes, never the test's access.
- Hidden dependencies (an imported `db`/`broker` singleton, inline `datetime.now()`, `time.time()`, `uuid.uuid4()`, an `os.environ` read inside logic) are design findings. The fix is exactly one of: extract a coherent concern into a named production module; make the hidden dependency an explicit parameter; inject a side-effecting port through a narrow consumer-declared `Protocol`; replace module-level mutable state with instance-owned state.
- No parameter defaults to a live boundary; real adapters wire up in one composition module; constructing a service or adapter opens no connection, reads no file, starts no thread or timer -- only its operations do.

## Patterns

- **Type-only modules:** the paired test holds typed assignments under `if TYPE_CHECKING:` and negatives marked with a specific `# type: ignore[code]`, which mypy `--strict` reports once it stops suppressing an error; zero runtime cases is correct -- added runtime assertions to look active are a finding.
- **Re-exports:** an existing re-exporting `__init__.py` gets a test asserting each re-export is its source object with `same_instance()`.
- **Filesystem:** real filesystem when files are the behavior, in the case's own `tmp_path`; `tmp_path_factory`, shared directories, or writes into the repository, home directory, or a fixed path are findings.
- **HTTP adapters:** the transport is a parameter, stubbed with a **fresh** response per call; when the request is the promise, its method, URL, headers, and body are asserted from the recorded request; a real client runs only against a loopback server the case owns.
- **Time:** an injected clock and an injected `sleep` whose requested delays are compared as a whole list; patching `time` or `datetime`, a real sleep, or polling is a finding.
- **Environment:** configuration passed as a parameter; a changed `os.environ` or global goes through `monkeypatch` before acting.
- **Shared adapter contracts:** a real adapter and its fake pass one set of contract cases, written once in the real adapter's test module against a fixture parametrized over every participant; every contract case gets a fresh instance; the categories (missing values, aliasing, overwrite, ordering, deletion, validation) are covered or their absence recorded; a private broken fake that answers every operation wrongly runs as a strict `xfail` participant, so each contract case is proven to discriminate.

## Classifying findings

- **BLOCKER** -- the suite lies or breaks: a case a wrong implementation would pass (weak, missing, or replaced assertions; expected values computed by production code; a partial mock-call assertion; a never-awaited coroutine), a changed source module with no paired test module, direct pair coverage below the configured floor, a hermeticity break (live network, shared global state, leaked filesystem writes), a committed `skip`/`xfail` outside a contract's negative control, or a test-only hook added to production code.
- **WARNING** -- structure and readability: a plain `assert` where a matcher states the condition, naming, AAA comments, test class shape, data style, support organization, double named after its kind.
