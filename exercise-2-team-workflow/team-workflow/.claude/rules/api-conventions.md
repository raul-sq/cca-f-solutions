---
# Glob patterns are quoted: any pattern starting with * or { MUST be quoted in YAML.
paths:
  - "src/api/**/*"
---
# API Conventions

These rules load only while working on files under `src/api/`.

- Validate every request body and query param at the boundary (e.g. Zod / pydantic).
- Return a consistent JSON envelope: `{ "status", "data", "error" }`.
- Use kebab-case for URL paths and camelCase for JSON properties.
- Every endpoint logs a correlation id; never log secrets or full payment data.
- Map domain errors to explicit HTTP codes (400/403/404/409/422), never a bare 500.
- Every new endpoint requires an integration test in the matching `*.test.*` file.
