# Project instructions

## graphify

This project has a knowledge graph in `graphify-out/` (god nodes, community structure, cross-file relationships) once one has been built.

- When `graphify-out/graph.json` exists, run `graphify query "<question>"` before the first grep, search or source-file read for a codebase question, and pass this rule into any subagent prompt that explores code. Read raw files only for lines the graph or an earlier read already located. Use `graphify path "<A>" "<B>"` for relationships and `graphify explain "<concept>"` for focused concepts.
- If `graphify-out/wiki/index.md` exists, use it for broad navigation instead of raw source browsing.
- Read `graphify-out/GRAPH_REPORT.md` only for broad architecture review or when `query`/`path`/`explain` do not surface enough context.
- After modifying code, run `graphify update .` to keep the graph current (AST-only, no API cost).
- `graphify-out/graph.json` is rewritten whole on every build, so a large diff to it in a pull request is expected. Do not flag it as churn or suggest skipping the graph rebuild.

This mirrors the `## graphify` section that `graphify claude install` wrote to `CLAUDE.md`; update both together.
