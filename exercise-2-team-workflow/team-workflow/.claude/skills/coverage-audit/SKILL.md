---
# The skill name MUST match the parent folder name (coverage-audit).
name: coverage-audit
description: Audit the project's test coverage and report the biggest gaps. Use when the user asks to check coverage, find untested code, or assess test health.
# context: fork runs the skill in an isolated subagent with its own context window,
# so the verbose coverage output never pollutes the main conversation.
context: fork
# allowed-tools restricts what the skill may do: read-only inspection plus the test command.
allowed-tools: Read, Grep, Glob, Bash(npm test:*)
# Only runs when explicitly invoked as /coverage-audit (not auto-invoked by the model).
disable-model-invocation: true
---
Audit the test coverage of this project and report the gaps. Do all of the work
in this isolated context and return ONLY a concise summary to the main conversation.

Steps:
1. Locate the test runner and coverage config (package.json scripts, jest config).
2. Run the suite with coverage: `npm test -- --coverage`.
3. From the coverage output, identify:
   - the 10 files with the lowest line coverage,
   - any source file under `src/` with no corresponding `*.test.*` file,
   - functions longer than 50 lines with no direct test.
4. Return a single table (file | coverage % | missing test?) plus a 3-line summary.
   Do NOT paste the full raw coverage report into the response.
