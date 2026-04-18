# Routine — Backend TDD style (Kindred edition)

The specific TDD cadence used while building `backend/`. Not a
philosophical treatise — a concrete cadence that produced 173+
passing tests across 6 plans.

## When to apply

- Any backend change that touches a request path, a service, or a
  data model.
- Any bugfix. The test is the reproducer.

## The cadence

### 1. Write the failing test

Choose its home:

- Route-shape changes → `tests/integration/test_*.py` (hits a real
  ASGI client).
- Pure function changes → `tests/unit/test_*.py` (no HTTP).
- Cross-cutting invariants (auth, sig verification, sanitization) →
  `tests/adversarial/` or `tests/policy/`.

Run it. Read the failure message. The message must name the thing
you are about to build. If the test fails for the wrong reason
(fixture missing, import typo), fix that first.

### 2. Minimal implementation

Make the test pass. No more.

If you find yourself wanting to generalise ("I'll add a parameter
so this is extensible"), resist until a second test demands it.

### 3. Tighten assertions

Once the behaviour is roughly right, sharpen the test:

- Exact error codes, not just "an error".
- Exact response shapes, not just "a dict".
- Exact audit log entries, not just "something was logged".

Lenient tests are a liability — they let regressions slip.

### 4. Commit the pair

```
test(<scope>): add failing test for <behaviour>
feat(<scope>): implement <behaviour>
```

Reviewers read commit-by-commit. Seeing the test alone first tells
them what shape you were aiming for before they see your
implementation.

## Repo-specific conventions

### Fixtures

`tests/conftest.py` ships:

- `db_session` — a transactional session rolled back per test.
- `client` — an async `httpx.AsyncClient` mounted on the ASGI app.
- `alice`, `bob`, `charlie` — three pre-created users with keypairs.
- `kindred` — a kindred with `alice` as owner.

Use them. Don't re-bootstrap state in individual tests.

### Naming

```python
def test_join_rejects_invite_with_bad_issuer_sig():
    ...
```

`test_<action>_<expected outcome>_<condition>`. Full sentence read
aloud = the test name passes the "future me reading CI logs at
2am" check.

### Assertion style

`pytest` raw `assert` is fine. Don't add `unittest`-style
wrappers. For HTTP responses:

```python
assert resp.status_code == 401
assert resp.json()["message"].startswith("signature")
```

Two assertions is fine. A test with ten assertions is probably two
tests in a trench coat.

### What NOT to mock

- The database — use the transactional session fixture.
- The HTTP layer — use the ASGI client.
- Crypto primitives — they're fast enough.

Mock the boundary only: outbound HTTP, LLM calls, wall clock
where time matters.

## Done when

- New behaviour has a test whose diff commit predates the
  implementation commit.
- Full suite passes locally and in CI.
- No skipped tests added for this change.
