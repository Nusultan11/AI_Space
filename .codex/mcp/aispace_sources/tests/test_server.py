from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

import pytest
from mcp import Client

from server import KNOWLEDGE_TEXT, mcp


BASE_DIR = Path(__file__).resolve().parents[1]
CATALOG_PATH = BASE_DIR / "sources.json"
REQUIRED_FIELDS = {
    "id",
    "title",
    "url",
    "category",
    "tags",
    "summary",
    "project_relevance",
    "key_points",
}
REQUIRED_SOURCE_IDS = {
    "alembic",
    "deepseek_api",
    "deepseek_json_output",
    "docker_compose",
    "fastapi",
    "github_actions",
    "google_sre_book",
    "jwt_rfc7519",
    "mui",
    "nginx_reverse_proxy",
    "openai_python",
    "owasp_authentication",
    "owasp_password_storage",
    "owasp_rest_security",
    "pg_btree_gist",
    "pg_constraints",
    "pg_datetime",
    "pg_range_types",
    "pg_transaction_isolation",
    "playwright",
    "pydantic",
    "pyright",
    "pytest",
    "react",
    "react_hook_form",
    "ruff",
    "sqlalchemy_asyncio",
    "tanstack_query",
    "testcontainers_python",
    "twelve_factor_config",
    "typescript",
    "vite",
    "zod",
}


@pytest.fixture
def anyio_backend() -> str:
    return "asyncio"


@pytest.fixture
async def client():
    async with Client(mcp, raise_exceptions=True) as connected_client:
        yield connected_client


def _structured(result: Any) -> dict[str, Any]:
    assert result.is_error is False
    assert isinstance(result.structured_content, dict)
    return result.structured_content


def test_server_imports_with_expected_identity() -> None:
    assert mcp.name == "AiSpace Sources"


@pytest.mark.anyio
async def test_expected_tools_are_registered(client: Client) -> None:
    result = await client.list_tools()
    assert {tool.name for tool in result.tools} == {
        "get_guidance",
        "get_source",
        "list_categories",
        "search_sources",
    }


@pytest.mark.anyio
async def test_server_exposes_useful_instructions(client: Client) -> None:
    assert client.instructions is not None
    assert client.instructions.startswith("Use this server for architecture-sensitive")


@pytest.mark.anyio
async def test_read_only_resources_are_available(client: Client) -> None:
    listed = await client.list_resources()
    assert {str(resource.uri) for resource in listed.resources} == {
        "aispace://knowledge",
        "aispace://sources/index",
    }
    result = await client.read_resource("aispace://sources/index")
    assert result.contents
    assert "pg_range_types" in result.contents[0].text


@pytest.mark.anyio
async def test_overlap_search_returns_postgresql_references(client: Client) -> None:
    result = _structured(
        await client.call_tool("search_sources", {"query": "booking overlap tstzrange GiST"})
    )
    ids = {item["id"] for item in result["results"]}
    assert "pg_range_types" in ids
    assert "pg_constraints" in ids


@pytest.mark.anyio
async def test_llm_search_returns_deepseek_references(client: Client) -> None:
    result = _structured(
        await client.call_tool("search_sources", {"query": "DeepSeek LLM structured JSON validation"})
    )
    ids = {item["id"] for item in result["results"]}
    assert "deepseek_json_output" in ids
    assert all(item["category"] == "llm" for item in result["results"][:2])


@pytest.mark.anyio
async def test_category_filter_and_limit_are_respected(client: Client) -> None:
    result = _structured(
        await client.call_tool(
            "search_sources",
            {"query": "validation api async", "category": "backend", "limit": 2},
        )
    )
    assert len(result["results"]) <= 2
    assert result["results"]
    assert all(item["category"] == "backend" for item in result["results"])


@pytest.mark.anyio
async def test_limit_is_capped(client: Client) -> None:
    result = _structured(
        await client.call_tool("search_sources", {"query": "test", "limit": 1000})
    )
    assert result["limit"] == 10
    assert len(result["results"]) <= 10


@pytest.mark.anyio
async def test_get_source_returns_expected_record(client: Client) -> None:
    result = _structured(await client.call_tool("get_source", {"source_id": "pg_range_types"}))
    assert result["found"] is True
    assert result["url"] == "https://www.postgresql.org/docs/current/rangetypes.html"


@pytest.mark.anyio
async def test_unknown_source_id_is_controlled(client: Client) -> None:
    result = _structured(await client.call_tool("get_source", {"source_id": "missing"}))
    assert result == {
        "found": False,
        "source_id": "missing",
        "error": "Unknown source id: missing",
    }


@pytest.mark.anyio
async def test_guidance_returns_relevant_subset(client: Client) -> None:
    result = _structured(await client.call_tool("get_guidance", {"topic": "booking overlap"}))
    assert result["sections"]
    assert any("overlap" in section["title"].casefold() for section in result["sections"])
    returned_text = json.dumps(result["sections"], ensure_ascii=False)
    assert len(returned_text) < len(KNOWLEDGE_TEXT)


def test_source_catalog_is_complete_and_unique() -> None:
    payload = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))
    sources = payload["sources"]
    ids = [source["id"] for source in sources]
    assert len(ids) == len(set(ids))
    assert REQUIRED_SOURCE_IDS.issubset(ids)
    for source in sources:
        assert REQUIRED_FIELDS.issubset(source)
        assert source["url"].startswith(("http://", "https://"))
        assert source["tags"]
        assert source["key_points"]


@pytest.mark.anyio
async def test_categories_report_catalog_counts(client: Client) -> None:
    result = _structured(await client.call_tool("list_categories", {}))
    assert result["total_sources"] >= 33
    counts = {item["category"]: item["count"] for item in result["categories"]}
    assert counts["database"] == 5
    assert counts["frontend"] == 7


def test_stdio_server_starts_without_secrets() -> None:
    environment = os.environ.copy()
    environment.pop("DEEPSEEK_API_KEY", None)
    environment.pop("OPENAI_API_KEY", None)
    result = subprocess.run(
        [sys.executable, "server.py"],
        cwd=BASE_DIR,
        input="",
        text=True,
        capture_output=True,
        timeout=10,
        check=False,
        env=environment,
    )
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
