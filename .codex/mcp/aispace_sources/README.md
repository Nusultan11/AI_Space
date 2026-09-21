# AiSpace Sources MCP

A tiny, read-only project-local MCP server that gives Codex curated engineering references and AiSpace-specific guidance. It exists to make architecture- and correctness-sensitive changes easier to verify without live scraping, external services, or a RAG stack.

## Structure

- `server.py`: deterministic MCP v2 server and tools.
- `sources.json`: curated catalog of primary/official references.
- `knowledge.md`: compact AiSpace engineering guidance.
- `tests/test_server.py`: catalog, tool, resource, and STDIO checks.
- `pyproject.toml` / `uv.lock`: project-local Python environment.

## Tools and resources

- `search_sources(query, category?, limit?)`: ranked local catalog search.
- `get_source(source_id)`: one complete source record.
- `list_categories()`: categories and counts.
- `get_guidance(topic)`: only the most relevant cheat-sheet sections.
- Resources: `aispace://sources/index` and `aispace://knowledge` for explicit full-index or full-guidance reads.

Codex should search first, retrieve topic guidance, and open only the needed source record. Repository architecture and explicit project contracts remain authoritative.

## Run and test

```powershell
uv sync
uv run pytest
uv run python -m py_compile server.py
uv run python server.py
```

The final command starts STDIO and waits for an MCP client; stop it with Ctrl+C. Standard output is reserved for protocol traffic.

## Codex registration

The root `.codex/config.toml` registers `aispace_sources` with `uv run python server.py` and this directory as `cwd`. From the repository root, verify discovery with:

```powershell
codex mcp list
```

Start a new Codex session or restart the local client after changing project MCP configuration. In the new session, confirm the server is available and call `list_categories` or search for `booking overlap`.

## Update the catalog

Add a unique record with every required field to `sources.json`, prefer a primary or official URL, keep summaries conservative, update relevant source IDs in `knowledge.md`, and run the complete test suite. The server performs no network requests at runtime.
