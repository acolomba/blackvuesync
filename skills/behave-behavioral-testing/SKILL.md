---
name: behave-behavioral-testing
description: Rules for behave behavioral tests -- Gherkin wording, step definition organization, the per-scenario context, and fakes for external services. Apply when writing or changing features/**.
---

# Behave behavioral testing rules

Behavioral tests under `features/` describe the project from the outside: each scenario drives the real code through its public surface, such as running the application as a subprocess, against local stand-ins for every external service. No scenario needs an account, hardware, or the public network.

## Tools

Use behave for the runner, plain `assert` statements or PyHamcrest's `assert_that()` for assertions, and behave's `context` for scenario state. `behave.ini` configures the run, and `features/environment.py` holds the hooks.

```bash
behave
```

## Gherkin

- Be concise and use active verbs; avoid the passive voice unless the subject is unknown.
- Use sentence casing for scenario titles.
- Use exclusively lower case for steps.
- Do not use `And`. Repeat `Given`, `When`, or `Then`.
- Avoid "should". Use the present tense: `Then the exit code is 0`.
- Use "these" when referencing a data table: `Given these recordings:`.
- Use the definite article when something is specific: `the destination`, `the broker`.
- Prefer a feature-level description of two or three lines that states what the feature protects and what the scenarios stand in for.

## Step definitions

- Organize step definitions into modules under `features/steps/` by their function, not by the feature files they were created for. A step that checks the exit status goes in a general steps module.
- Order the definitions in each module `@given`, then `@when`, then `@then`.
- Keep each step short, and name its function after its role: a `@given` after the thing given (`configured_service`), a `@when` after the action taken (`run_application`), and a `@then` `assert_` followed by the condition asserted (`assert_exit_code`).
- Annotate every step: `def run_application(context: Context) -> None:`.
- Compare whole values, and put the observed output in the failure message so a failing scenario explains itself.

## The context

- `context` is the per-scenario world. behave removes the attributes a scenario sets when it ends. `features/environment.py` sets run-wide state in `before_all()` and per-scenario state in `before_scenario()`.
- The context owns the lifetime of each fake it hands out. Register the teardown with `context.add_cleanup()`, which runs in reverse order when the scenario ends, so no scenario leaks a listening socket, an open connection, a container, or a temporary directory into the next one.
- Keep scenario state on the context; do not use module-level mutable state in step modules.

## Fakes

- Fake every external service the code talks to (HTTP APIs, brokers, identity providers) with a loopback-only stand-in owned by the context; put each one in its own module under `features/`, outside `features/steps/`.
- A fake records what it receives and can be armed to fail the next request, so scenarios cover error paths.
- Do not catch exceptions defensively in test code. Let them bubble up: the stack trace is more useful than a log with fewer details.
