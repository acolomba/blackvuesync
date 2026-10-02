# AGENTS.md

## Test Guidelines

### General

In test code, avoid defensive exception handling. Let exceptions bubble up so stack traces remain visible.

### Behave

#### Gherkin Features

- be concise and use active verbs
- use sentence casing for scenarios
- use lowercase for steps
- do not use `And`
- avoid "should"; use present tense
- use "these" for data tables (for example, "Given these recordings:")
- use "the" when referring to specific entities (for example, "the destination")

#### Step Definitions

- organize step definitions by function, not by feature file
- keep methods concise and use this naming pattern:
- `@given`: the thing that is given (for example, `downloaded_recordings`)
- `@when`: the action (for example, `run_blackvuesync`)
- `@then`: `assert_` + condition
- order methods as `@given`, `@when`, `@then`
