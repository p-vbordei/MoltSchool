# Routine — Git commit conventions

How to write commit messages on this team. Optimised for future readers
who will use `git log --oneline` to understand what happened and why.

## Format

```
<type>(<scope>): <one-line summary>

<optional body, wrapped at 72 chars>
```

### Types

| Type     | Use for                                              |
|----------|------------------------------------------------------|
| `feat`   | A new user-visible capability                        |
| `fix`    | A bug fix                                            |
| `test`   | Adding or improving tests                            |
| `docs`   | Documentation-only changes                           |
| `refactor` | Internal restructuring, no behaviour change        |
| `chore`  | Build, deps, CI config, repo plumbing                |
| `perf`   | Performance-only change                              |

### Scope

A short noun indicating the subsystem: `api`, `cli`, `ui`, `db`,
`auth`, etc. Leave off if truly cross-cutting.

### Summary

- Imperative mood (`add`, not `added` or `adds`).
- Lowercase except proper nouns.
- No trailing period.
- Under 72 characters.

## Size

Aim for commits small enough that the whole diff fits on one screen.
If a commit message has more than 3 bullet points in the body, you are
probably committing more than one thing.

## Examples

Good:

```
feat(cli): add kin leave command for revoking kindred membership
fix(api): reject invites whose body_b64 does not match issuer_sig
test(adversarial): add 50-payload injection corpus, 100% block gate
```

Bad:

```
update cli and api                              # no type, no scope, vague
feat: misc CLI improvements                     # "misc" = more than one thing
fix(cli): fix bug where sometimes kin didn't work  # what bug? what did it do?
```

## Frequency

Commit every time you reach a stable point — typically every 10-30
minutes of active coding. Pre-commit hooks enforce lint/format; if the
hook rejects your commit, fix the issue and make a NEW commit, do not
`--amend`.

## Done when

- Every commit on the branch has a valid type/scope/summary.
- A reader can understand the shape of the change from `git log
  --oneline` alone.
