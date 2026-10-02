---
name: python-unit-testing
description: Unit testing rules for Python -- pairing, coverage, case structure, naming, assertions, test doubles, test data, hermeticity, and production design for tests. Apply when writing or changing test/**/*.py or the source modules they pair with.
---

# Python unit testing rules

"Do" and "Do not" are hard rules. "Prefer" states the default and allows a justified exception. "May" grants a permission. Copy the **Good** form.

Every case must discriminate the behavior named in its title: a wrong implementation makes the assertion fail. A test with weak assertions costs all the maintenance of a test and gives none of the protection.

## Tools

Use pytest for the runner, fixtures, and the built-in `monkeypatch`, `tmp_path`, and `capsys` fixtures; PyHamcrest's `assert_that()` and its matchers for assertions; `pytest.raises()` for errors; `unittest.mock.create_autospec()` for strict interaction mocks and `unittest.mock.Mock(wraps=...)` for spies; pytest-cov for coverage.

```python
from unittest.mock import call, create_autospec

import pytest
from hamcrest import assert_that, equal_to
```

Do not add another runner, assertion library, or mocking library: no `unittest.TestCase`, `pytest-mock`, `pytest-asyncio`, `freezegun`, `responses`, or snapshot plugins.

## Pairing and coverage

- The root-level application module `blackvuesync.py` pairs with `test/blackvuesync_test.py`, which imports it and owns its public behavior. Developer scripts and behavioral-test support are outside this pairing gate.
- No exclusions. Re-exporting `__init__.py` modules, `__main__.py`, type-only modules, and one-function modules all need a test module. The one exemption is an `__init__.py` holding nothing but a docstring, which only marks a package. If a module is not worth a test, fold it into its consumer.
- `scripts/check_corresponding_tests.py`, run by pre-commit and by `scripts/check.sh`, fails when a module has no test module, when a test module does not import its module, or when a test module has no module.
- Do not put tests under `src/`, name them `test_*.py`, or test one source module from another module's test.
- Test support (fakes, seeds, fixtures in `conftest.py`) needs no meta-tests; a fake is verified through its shared contract.
- The unit suite measures line and branch coverage and meets the coverage floor configured in `pyproject.toml`. Raise coverage as behavior changes; 100% is not a migration requirement.
- Do not add `# pragma: no cover`, coverage `exclude_lines`, or `omit` entries. Remove dead code or cover it through a public-behavior case.
- Run `pytest <test-path>` while developing, `scripts/coverage-direct.sh <source-path> <test-path>` for the pair, and `scripts/check.sh` before completion.

## Case structure

- Write independent test functions: `def test_rejects_an_unknown_order() -> None:`.
- When a module has several public entrypoints, group each one's cases in a top-level class named after it (`class TestPlace:`, `class TestCancel:`). A single-entrypoint module keeps cases at module level. Do not nest classes.
- Do not group by private helpers or use a class to share mutable setup: a test class has no `__init__`, attributes, or `setup_method()`.
- Each case gets fresh state and dependencies. Prefer construction inside the case. A function-scoped fixture may create new per-case instances; do not use a `module`, `class`, `package`, or `session` scoped fixture for stateful objects. Only a stateless stub (a fixed `clock`) may live at module scope.
- Do not commit `@pytest.mark.skip`, `skipif`, or `xfail`, or calls to `pytest.skip()` or `pytest.xfail()`. The one exception is the strict negative control of a shared contract (see Patterns).
- Name each case with a short snake-case sentence stating public behavior: `test_rejects_an_unknown_order`, not `test_works`, `test_happy_path`, or `test_cancel`. A durable requirement ID may appear; plan, phase, or ticket references may not. The name is the title, so do not add a docstring that restates it.
- Mark phases with lowercase `# arrange`, `# act`, `# assert` comments, in that order, separated by a blank line. A `with pytest.raises(...)` block is the act; assert the error's fields after it under `# assert`. Use `# act & assert` only when that block is the whole assertion. Parametrized cases still use separate phases. Add no other comments unless setup is not obvious.

## Naming values

Name values after their production role. Do not use `result`, `res`, `ret`, `data`, `value`, `instance`, `subject`, `sut`, or a bare `actual`.

- Module under test: `order_service`. Its returned value: `order`.
- Expected value: `expected_order`, or the seed fixture that provides it (`placed_order`). Prefer an inline literal when it is short and used once.
- Test double: the production role only, `orders`, `payments`, `clock`. Do not add `mock`, `fake`, or `stub` to the name; how it is created shows the kind.
- Spy: the observed method with a `_spy` suffix, `put_spy`.
- Caught error: `raised`, from `pytest.raises(...) as raised`.
- Parametrized arguments: the parameter and the promised outcome, `lines, total`.

## Reference case

`OrderService(clock=..., events=..., ids=..., orders=..., payments=...)` takes every collaborator explicitly. `clock` and `ids` are stub functions, `orders` is a stateful fake from the concern's `conftest.py`, `payments` and `events` are strict mocks, and `cart` / `placed_order` are seed fixtures.

### Good

```python
def clock() -> datetime:
    return datetime(2026, 8, 28, 10, 0, tzinfo=timezone.utc)


def ids() -> str:
    return "order-123"


class TestPlace:
    def test_charges_the_customer_stores_the_order_and_publishes_order_placed(
        self, orders: OrderStore, cart: Cart, placed_order: Order
    ) -> None:
        # arrange
        payments = create_autospec(Payments, instance=True, spec_set=True)
        events = create_autospec(OrderEvents, instance=True, spec_set=True)
        order_service = OrderService(
            clock=clock, events=events, ids=ids, orders=orders, payments=payments
        )

        # act
        order = order_service.place(cart)

        # assert
        assert_that(order, equal_to(placed_order))
        assert_that(orders.get("order-123"), equal_to(placed_order))
        assert_that(payments.mock_calls, equal_to([call.charge("customer-1", 25)]))
        assert_that(
            events.mock_calls, equal_to([call.publish(OrderPlaced("order-123", total=25))])
        )
```

A mock whose expected call list is empty proves that the module does not touch that port: `assert_that(events.mock_calls, equal_to([]))`.

## Assertions

- Prefer PyHamcrest's `assert_that(actual, matcher)` to state the condition. The matcher names the condition, and a failure reports the expected and the actual value. Pass a reason as the third argument only when it adds a fact the matcher does not report. A plain `assert` is the exception, for a condition that no matcher states.
- Assert the public result and public state before any interaction. Do not replace a result assertion with a call assertion. When relocating a case, preserve its assertions unless the contract changed.
- Compare whole values with `equal_to()`. Use `contains_inanyorder()` for a list whose order is not part of the promise, and `same_instance()` for identity. Do not assert existence, length, or one attribute at a time when the whole value is the promise: `has_item()`, `has_items()`, `has_entries()`, `has_length()`, and `instance_of()` pass for a partial value. A standalone negative assertion (`assert_that(order, not_none())`, `assert_that(order, is_not(cancelled))`) passes for almost any value; assert what the value is.
- Assert errors by class and structured fields, not by message text; do not pass `match=` to `pytest.raises()`:

```python
# act
with pytest.raises(OrderNotFoundError) as raised:
    order_service.cancel("order-999")

# assert
assert_that(
    (raised.value.code, raised.value.order_id),
    equal_to(("ORDER_NOT_FOUND", "order-999")),
)
```

- When bytes are the contract (a file, packet, archive, encoded value), compare the complete bytes. Do not decode or normalize the output unless consumers do.
- Build expected values independently. Do not call the production formatter or serializer, transform the adapter result, ask a harness for the answer, or use a snapshot assertion.
- Drive an `async def` entrypoint with `asyncio.run()` inside the case, and await every coroutine. pytest runs with `filterwarnings = ["error"]`, so a coroutine that is never awaited fails the case instead of passing it.

## Test doubles

| Role | Use                                            | Assert                                                                |
| ---- | ---------------------------------------------- | --------------------------------------------------------------------- |
| Fake | A working, simplified, stateful implementation | The public result and resulting state                                 |
| Stub | A canned value or error that drives one path   | The module's result, not the stub's call count                        |
| Spy  | Real behavior with recorded calls              | Public behavior first; calls only when the observation is the promise |
| Mock | A prescribed interaction                       | The promised calls, arguments, and order                              |

Use the tool that matches the role. Do not turn a stub into a mock by asserting its calls. Do not verify incidental spy calls.

**Fakes.** A `FakeThing` class in the concern's `conftest.py`, handed out by a function-scoped fixture, stands in for a stateful boundary (store, repository, remote). Seed it through its public contract: `orders.put(placed_order)`. `copy.deepcopy()` mutable values at ingress and egress. Do not simulate a database or filesystem with a graph of mocks. Do not let a fake grow into a second real implementation.

**Stubs.** A plain function or small class that satisfies the port (`def ids() -> str: return "order-123"`) for a fixed clock, ID, one-shot failure, remote response, or capability flag; mypy checks it where the port is expected. Use `Mock(side_effect=[...])` only when a plain function is not enough, such as a sequence of answers. Assert the module's result, not the stub's calls.

**Spies.** `put_spy = Mock(wraps=orders.put)` installed with `monkeypatch.setattr(orders, "put", put_spy)`, only when real behavior must run and the observation is the promise ("writes exactly once", "does not rewrite"). Read `put_spy.mock_calls` after the result assertions. With a `return_value` or `side_effect` it is a stub.

**Mocks.** `create_autospec()`, only when the interaction is public behavior: charging, publishing, notifying, transaction control, invoking a callback, issuing a command.

- Create `create_autospec(Port, instance=True, spec_set=True)` inside the case. Autospec rejects a call that does not match the port's signature, and `spec_set` rejects an attribute the port does not have. A bare `Mock()` or `MagicMock()` accepts anything.
- Set every return value and error the module uses: `payments.charge.return_value = receipt`, `payments.charge.side_effect = PaymentDeclinedError("customer-1")`. An autospecced method returns a `MagicMock` by default, which hides a missing setup.
- Assert the complete call list with `equal_to()` at the end of the case, after result and state assertions: `assert_that(payments.mock_calls, equal_to([call.charge("customer-1", 25)]))`. It fails on a missing, extra, reordered, or differently argued call.
- Do not use `assert_called()`, `assert_called_once()`, `assert_any_call()`, or `assert_has_calls()`, which pass with extra calls, or a bare `call_count`. Do not assert in a fixture teardown or shared helper.
- Use `unittest.mock.ANY` only for an argument that cannot be compared by value (a callback, a stream), and assert its meaningful properties separately.

When order across mocks is the promise, attach every mock to one recorder and compare its whole call list:

```python
calls = Mock()
calls.attach_mock(payments, "payments")
calls.attach_mock(events, "events")
# ...
assert_that(
    calls.mock_calls,
    equal_to(
        [
            call.payments.charge("customer-1", 25),
            call.events.publish(OrderPlaced("order-123", total=25)),
        ]
    ),
)
```

**Not doubles.** Plain data (`Cart`, `Order`, `OrderPlaced`) is a real instance. Logging gets a silent stub or goes unobserved; assert log records (`caplog`) only in a module whose job is logging.

**Scope.** Every double comes from the case or a function-scoped fixture. Change attributes, items, and environment variables only through `monkeypatch`, which restores them after the case. Do not patch a module's names (`monkeypatch.setattr("blackvuesync.orders.datetime", ...)`, `mock.patch(...)`) to replace a dependency; inject the dependency instead.

## Test data

- Short self-describing literals: `"order-123"`, `"customer-1"`, `"sku-a"`. No realistic prose, random generators, or long fixture blobs.
- Build the production type (`Order(...)`), not a dict that stands in for it. Set only what the case is about: `dataclasses.replace(placed_order, status="cancelled")`.
- Seeds reused across cases are function-scoped fixtures in the concern's `conftest.py` that return fresh values, never shared mutable constants.
- Do not compute test data with production code.

## Data-driven cases

Create one case per row with `@pytest.mark.parametrize`, giving each row an `id` that states it. Do not loop over rows inside one case; it stops at the first failure. Do not put a conditional in the case body; different branches, dependencies, or expectations are separate named cases.

```python
@pytest.mark.parametrize(
    ("lines", "total"),
    [
        pytest.param([], 0, id="no lines"),
        pytest.param([Line("sku-a", quantity=2, unit_price=10)], 20, id="one line"),
    ],
)
def test_totals_the_lines(lines: list[Line], total: int) -> None:
    # act
    calculated_total = cart_total(lines)

    # assert
    assert_that(calculated_total, equal_to(total))
```

## Types and hermeticity

- mypy checks the tests with the same `--strict` settings as production. Do not use `Any`, `cast()`, or `# type: ignore` to pass an invalid double; narrow the production contract instead.
- Prefer a small port declared by the consumer (`class Payments(Protocol): def charge(self, customer_id: str, amount: int) -> None: ...`), so mypy checks a hand-built double where the port is expected.
- Cases run offline, in any order, with no credentials or developer setup. Fake HTTP APIs, brokers, cloud services, identity providers, and remote repositories. Do not fall back to a live service.
- Run a real adapter only against `tmp_path` or a loopback-only service owned by the case.
- Do not share a process global across cases without restoring it. Do not add a production reset function to clean up after a test.
- pytest turns warnings into errors. Fix the cause of a warning instead of filtering it.

## Test support organization

Keep fakes, seeds, contracts, and fixtures next to the tests of the concern they serve, in its `conftest.py`: `test/blackvuesync/orders/conftest.py`. Test modules do not import each other or a support module; pytest imports each test module by its path and hands out support through fixtures. Do not create `test/helpers/`, `test/utils/`, or `test/mocks/`. Use a `fixtures/` directory only when a concern has enough static files to need one. The `name-tests-test` pre-commit hook accepts only `*_test.py` and `conftest.py` modules under `test/`.

## Design production code for its tests

A test uses only the module's public names. When a module resists testing, change the production design, never the test's access.

Do not make a name public for a test, add a reset hook, global mutator, state reader, or test mode, or reach a `_private` member from a test. Assert a private rule through the public entrypoint that uses it.

Make dependencies explicit as a function parameter or a constructor parameter (`OrderService(clock=..., events=..., ids=..., orders=..., payments=...)`). An imported `db` or `broker` singleton, an inline `datetime.now()`, `time.time()`, `uuid.uuid4()`, or an `os.environ` read inside logic is a hidden dependency that makes the module untestable through its public names.

Make exactly one of these changes when a module resists testing:

1. Extract a coherent concern into a production module with a real name and API; it gets its own test module.
2. Make an existing hidden dependency an explicit parameter.
3. Inject a side-effecting port through a narrow `Protocol` declared in the consumer module.
4. Replace module-level mutable state with state owned by an instance.

Do not default a parameter to a live boundary (`clock: Clock = datetime.now`). Wire real adapters in one composition module, such as `__main__.py`. Constructing a service or adapter must not open a connection, read a file, or start a thread or timer; only its operations do.

## Patterns

**Type-only modules.** The paired test module holds typed assignments under `if TYPE_CHECKING:` so mypy checks them and nothing runs, with each negative marked by a specific `# type: ignore[code]`. mypy `--strict` reports an ignore that no longer suppresses an error, so the negative fails when the type stops rejecting it. pytest collects zero cases from the module. Do not add runtime assertions to make it look active.

```python
from typing import TYPE_CHECKING

from blackvuesync.orders.events import OrderEvent, OrderPlaced

if TYPE_CHECKING:
    placed: OrderEvent = OrderPlaced("order-123", total=25)
    # an event carries its total
    untotaled: OrderEvent = OrderPlaced("order-123")  # type: ignore[call-arg]
```

**Do not test what a gate already enforces.** Before writing a case, name the failure it catches and the gate that would miss it. If mypy, ruff, pylint, the pairing gate, or direct coverage already catches it, the case cannot fail and is a maintenance cost that proves nothing.

**Usage is not a property of a type.** Never enumerate a type's fields to detect an unused one (`dataclasses.fields()`, `__annotations__`, `Protocol` members). A test observes shape from outside; whether a member is read belongs to the call graph, which no test of the type can reach. Coverage does not reach it either: an unused field has no read site, so there is no line, and absent code produces no coverage record. Rely on mypy for required fields, since every construction that omits one stops type-checking, and on the consumer's own direct coverage for fields it reads. A field nothing reads is a dead-code question for static analysis, not a case.

```python
# wrong: pins the field list so a fourth field "cannot be added silently"
assert_that(
    [f.name for f in dataclasses.fields(EdgeDeps)],
    equal_to(["git_ops", "plugin_update", "import_claude_settings"]),
)
# right: pin the contract that carries meaning -- which fields are optional
EdgeDeps(git_ops=git_ops, plugin_update=plugin_update)
```

**Re-exports.** Prefer importing concrete modules. An existing re-exporting `__init__.py` gets a test module that asserts each re-export is the same object as its source with `same_instance()`.

**Filesystem.** Use the real filesystem when stored files, paths, permissions, encoding, or rendered bytes are the behavior. Use the case's own `tmp_path`, which pytest creates for each case. Do not share a directory across cases (`tmp_path_factory`) or write into the repository, the home directory, or a fixed path.

**HTTP adapters.** Give the adapter its transport as a parameter (a `requests.Session`, an `urllib.request.OpenerDirector`, or a narrow callable) and pass a stub that returns a fresh response on every call. When the request is the promise, record it and assert its method, URL, headers, and body. A real client runs only against a loopback `http.server.ThreadingHTTPServer(("127.0.0.1", 0), ...)` that the case starts and shuts down.

**Time.** Prefer an injected clock. When scheduling itself is the behavior (timeout, retry, backoff), inject the `sleep` function, record the delays it is asked for, and compare the whole list. Do not patch `time` or `datetime`, sleep for real, or poll.

**Environment.** Prefer configuration passed as a parameter: `load_orders_config({"ORDERS_DIR": "/srv/orders"})`. When `os.environ` or a global must change, change it with `monkeypatch.setenv()` or `monkeypatch.setattr()` before acting, so pytest restores it.

**Shared adapter contracts.** A real adapter and its fake pass one contract. Write the contract cases once, in the real adapter's test module, against a fixture parametrized over every participant; its `params` are the inventory of participants. The fake comes from its `conftest.py` fixture through `request.getfixturevalue()`. Adapter-specific cases stay in their own test modules. Give every contract case a fresh instance. Cover missing values, aliasing, overwrite, ordering, deletion, and validation, or record why a category does not apply. Prove that every contract case discriminates: add a deliberately broken fake, private to that test module, that answers every operation wrongly, as a strict `xfail` participant. A contract case that passes against it fails the run.

The participant fixture:

```python
@pytest.fixture(
    params=[
        "file",
        "fake",
        pytest.param("broken", marks=pytest.mark.xfail(strict=True, raises=AssertionError)),
    ]
)
def order_store(request: pytest.FixtureRequest, tmp_path: Path) -> OrderStore:
    if request.param == "file":
        return FileOrderStore(tmp_path)
    if request.param == "fake":
        orders: OrderStore = request.getfixturevalue("orders")
        return orders
    return BrokenOrderStore()
```

## Completion checklist

A unit-test change is complete when:

- [ ] Every changed production module, including `__init__.py`, `__main__.py`, and type-only modules, has one corresponding test module that imports it.
- [ ] Each test uses public production behavior only; no name was made public and no reset hook, mutator, or state reader was added for testing.
- [ ] Any production refactor created a coherent module, an explicit dependency, a narrow port, or removed hidden global state.
- [ ] Tests are independent pytest functions that state conditions with `assert_that()` and a matcher, with no `skip` or `xfail` beyond a contract's negative control.
- [ ] Every case marks its phases with `# arrange`, `# act`, and `# assert`; `# act & assert` appears only for a `pytest.raises()` block that is the whole assertion.
- [ ] Any test class is top-level, names a public entrypoint, and owns no state; each stateful case gets fresh dependencies from the case or a function-scoped fixture.
- [ ] Case names state public behavior; values and doubles are named after their production role.
- [ ] Fakes, stubs, spies, and mocks are chosen and asserted by role; plain data is a real instance; logging is not verified outside a logging module.
- [ ] Every mock is `create_autospec(..., instance=True, spec_set=True)`, has its return values set, and ends its case with a whole-list `mock_calls` assertion.
- [ ] Every attribute, item, and environment change goes through `monkeypatch`; no module name is patched to replace a dependency.
- [ ] Test data is small, self-describing, and built from seed fixtures that return fresh values.
- [ ] Filesystem behavior uses the case's own `tmp_path`.
- [ ] External transports are fake, local, or loopback-only; every stubbed transport returns a fresh response.
- [ ] Time comes from an injected clock and an injected `sleep`.
- [ ] Public results and state are asserted before promised interactions; whole values are compared; errors are asserted by class and fields.
- [ ] Expected values are independent from production and harness computations.
- [ ] No case restates a fact that mypy, ruff, pylint, the pairing gate, or direct coverage already enforces.
- [ ] Shared support lives in the concern's `conftest.py`, with no generic helper directory.
- [ ] Real and fake adapters pass the same contract, and every contract case fails against the strict `xfail` broken participant.
- [ ] The focused source-test pair meets the configured coverage floor, with no coverage exception added.
- [ ] Focused `pytest`, `scripts/coverage-direct.sh`, and `scripts/check.sh` pass.
