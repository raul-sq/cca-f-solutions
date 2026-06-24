# Project: Team Development Workflow

Universal standards for everyone working in this repository. This file loads
automatically at the start of every Claude Code session, for every team member,
so behaviour stays consistent across the team. Keep it concise (under ~200 lines)
and front-load the most important rules.

## How to work in this repository
Before starting, identify the area you are touching and follow the matching rule
file in `.claude/rules/` (those load on demand when you open matching files):
- API code under `src/api/` -> `.claude/rules/api-conventions.md`
- Test files (`*.test.*`)   -> `.claude/rules/testing-conventions.md`

## Coding standards (all languages)
- Use 2-space indentation. No tabs.
- Prefer descriptive names over comments; comment the "why", not the "what".
- Keep functions single-purpose; extract once a function passes ~50 lines.
- Leave no commented-out code and no leftover `console.log` / `print` debugging.
- Handle errors explicitly. Never swallow exceptions silently.
- New public functions need a docstring/JSDoc covering inputs, outputs and errors.

## Testing conventions
- Every bug fix and every new feature ships with tests.
- Frameworks: Jest (JS/TS) and pytest (Python).
- Run the full suite before committing: `npm test` and/or `pytest -q`.
- Minimum line coverage for changed files: 80%.
- Name tests by behaviour: `it("returns 404 when the order is missing")`.

## Commits and pull requests
- Conventional Commits: `type(scope): summary` (feat, fix, chore, docs, test, refactor).
- One logical change per commit; reference the issue id in the body.
- Open a PR describing what changed and how it was tested.

## Tooling
- Team-shared MCP servers are defined in `.mcp.json` (setup in the report).
- Reusable workflows live in `.claude/skills/` and `.claude/commands/`.
