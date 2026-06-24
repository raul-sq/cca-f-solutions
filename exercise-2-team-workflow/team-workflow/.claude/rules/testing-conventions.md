---
# "**/*.test.*" starts with * so it MUST be quoted, or the YAML frontmatter fails to parse.
paths:
  - "**/*.test.*"
---
# Testing Conventions

These rules load only while working on test files (`*.test.*`).

- Arrange-Act-Assert structure; one behaviour per test.
- Mock external services (network, DB, MCP servers); tests stay deterministic and offline.
- Cover the happy path plus at least one validation error and one permission/edge case.
- Name tests by observable behaviour, not by method name.
- No shared mutable state between tests; reset fixtures in setup/teardown.
