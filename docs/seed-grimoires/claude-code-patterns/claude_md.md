# CLAUDE.md — Team defaults

Paste the section below into your repository's `CLAUDE.md`. It is the
minimum behavioural set we've converged on across teams.

---

## 1. Test-driven per task

For every task that changes behaviour:

1. Write the failing test first. Run it. See it fail for the right reason.
2. Make it pass with the smallest change that works.
3. Refactor without changing behaviour. Run tests again.

Do not skip step 1 because "it's obvious". The failing-test evidence is
the record that the test actually exercises the new code path.

## 2. One concept per commit

Every commit message describes exactly one thing. If you need the word
"and" in the subject line, split it. Commit early, commit often — small
commits are easier to review and easier to revert.

## 3. Stop when the task is done

Do not "while I was here" refactors. If you notice adjacent code that
needs work, file a follow-up task and keep the current change focused.

## 4. Show your work

When you fix a bug, the commit that fixes it should include the test
that reproduces it. When you add a feature, the first commit should be
the failing test, the second the implementation. Reviewers read commit
histories — make them tell the story.

## 5. Ask when you're stuck

If you're unsure about the shape of an API, the intent of a file, or
whether a pattern we use elsewhere applies, ask. Do not guess and then
defend the guess.

## 6. Match existing style

If the repo uses 4-space indents and you prefer 2, use 4. If the repo
uses `snake_case` and you prefer `camelCase`, use `snake_case`. Style
coherence matters more than any individual preference.
