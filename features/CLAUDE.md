# CLAUDE.md

## Guidelines

### General

In test code, avoid being too defensive against exceptions. Let them bubble up instead of catching them and logging. The stack trace is more useful than a log with fewer details.

### Behave

#### Gherkin Features

Be concise and use active verbs; avoid the passive voice unless the subject is unknown.

Use sentence casing for scenarios.

Use exclusively lower cases for steps.

Don't use `And`.

Avoid "should". Use the present tense.

Use "these" when referencing data table. E.g. "Given these recordings:".

Use the determinate article when something is specific, e.g. "the destination".

#### Step definitions

Step definition methods must be organized into modules by their function, not by the feature files they happened to be created for. For instance, checking the exit status goes in a general step definitions file.

Step definition methods must be concise and follow this pattern:

- Given: the thing that is given, e.g. "downloaded_recordings"
- When: the action being taken, e.g. "run_blackvuesync"
- Then: `assert_` followed by the condition being asserted

Step definition methods must be ordered by `@given`, `@when`, `@then`.
