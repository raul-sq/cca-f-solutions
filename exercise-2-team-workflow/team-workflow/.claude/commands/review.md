---
description: Run the team code-review checklist on the current uncommitted changes.
argument-hint: [optional focus area]
allowed-tools: Bash(git diff:*), Bash(git status:*), Read, Grep, Glob
---
## Current changes
!`git status --short`
!`git diff HEAD`

## Instructions
Review the changes shown above against the team checklist. If $ARGUMENTS is provided,
focus on that area first.
1. Standards: 2-space indent, descriptive names, no leftover debug logging.
2. Errors: no silently swallowed exceptions; domain errors mapped to explicit codes.
3. API: input validation at the boundary; consistent `{ status, data, error }` envelope.
4. Tests: every change has tests; happy path + at least one error case covered.
5. Security: no secrets in code or logs; credentials read from env, never hardcoded.
Report findings grouped as Critical / Warning / Suggestion. If the diff is empty, say so.
