# Routine — TDD per task

A repeatable loop for implementing any feature or fix. Follow the steps
in order. Do not start step N+1 until step N produces the evidence
required.

## When to apply

- You are about to change behaviour (new feature, bug fix, refactor
  with observable effect).
- You are implementing a task described in a plan or ticket.

## Pre-conditions

- The repository's test suite currently passes on the branch you are
  on. If it does not, stop and fix the suite first.
- You have a clear verbal description of the behaviour being added. If
  you cannot state it in one sentence, re-read the task.

## Steps

### 1. Write the failing test

Pick the smallest test that would fail without your change. Prefer an
integration test if the behaviour crosses boundaries; prefer a unit
test otherwise. Run it.

Expected evidence: a single failing assertion with a message that
mentions the thing you are about to build. If the test fails for the
wrong reason (import error, typo, missing fixture), fix that before
continuing.

### 2. Minimum implementation

Make the test pass with the smallest change. Ignore design pressure
that is not exercised by an existing test. If you feel the urge to
generalise, write a second test for the generalisation first.

Expected evidence: the test you wrote in step 1 passes. The rest of
the suite still passes.

### 3. Refactor if needed

Only now, after the test is green, restructure code for clarity. Keep
running the tests as you go.

Expected evidence: no behaviour change — every test still green,
including any you added for step 2's generalisation.

### 4. Commit

One commit per logical unit. Typical split:

- `test(<scope>): add failing test for <behaviour>`
- `feat(<scope>): implement <behaviour>`
- `refactor(<scope>): tidy <X> after <behaviour>` (optional)

## Anti-patterns

- **Writing implementation first, test after.** You lose the evidence
  that the test actually covers the code. If you must, squash the two
  into one commit but write the test such that commenting out the
  implementation makes it fail.
- **"I'll add tests later."** You won't. Later is a place where tests
  go to die.
- **Mega-tests.** A test that asserts 12 things fails obscurely. Keep
  each test focused on one behaviour.

## Done when

- A new test exists that exercises the new behaviour.
- `git log` on this branch shows a test-then-implementation pair.
- The full test suite passes locally and in CI.
