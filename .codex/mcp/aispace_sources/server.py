"""Read-only local MCP server for curated AiSpace engineering references."""

from __future__ import annotations

import json
import re
from collections import Counter
from pathlib import Path
from typing import Any

from mcp.server import MCPServer


BASE_DIR = Path(__file__).resolve().parent
SOURCES_PATH = BASE_DIR / "sources.json"
KNOWLEDGE_PATH = BASE_DIR / "knowledge.md"
MAX_SEARCH_RESULTS = 10
MAX_GUIDANCE_SECTIONS = 3
TOKEN_PATTERN = re.compile(r"[\w+#.-]+", re.UNICODE)
REQUIRED_SOURCE_FIELDS = {
    "id",
    "title",
    "url",
    "category",
    "tags",
    "summary",
    "project_relevance",
    "key_points",
}

INSTRUCTIONS = (
    "Use this server for architecture-sensitive or correctness-sensitive AiSpace work. "
    "It contains curated engineering references; prefer primary and official sources. "
    "The repository architecture and explicit project contracts remain authoritative. "
    "If guidance conflicts with an intentional project decision, report the conflict "
    "instead of silently changing the architecture. Retrieve only relevant sources or "
    "guidance sections rather than dumping the complete knowledge base."
)


def _load_catalog() -> list[dict[str, Any]]:
    payload = json.loads(SOURCES_PATH.read_text(encoding="utf-8"))
    sources = payload.get("sources")
    if not isinstance(sources, list):
        raise ValueError("sources.json must contain a 'sources' list")

    seen: set[str] = set()
    for source in sources:
        if not isinstance(source, dict) or not REQUIRED_SOURCE_FIELDS.issubset(source):
            raise ValueError("Every source must contain all required catalog fields")
        source_id = source["id"]
        if not isinstance(source_id, str) or not source_id:
            raise ValueError("Every source must have a non-empty string id")
        if source_id in seen:
            raise ValueError(f"Duplicate source id: {source_id}")
        seen.add(source_id)
    return sources


def _load_guidance() -> tuple[str, list[dict[str, str]]]:
    text = KNOWLEDGE_PATH.read_text(encoding="utf-8")
    sections: list[dict[str, str]] = []
    title: str | None = None
    body: list[str] = []

    for line in text.splitlines():
        if line.startswith("## "):
            if title is not None:
                sections.append({"title": title, "content": "\n".join(body).strip()})
            title = line.removeprefix("## ").strip()
            body = []
        elif title is not None:
            body.append(line)
    if title is not None:
        sections.append({"title": title, "content": "\n".join(body).strip()})
    return text, sections


SOURCES = _load_catalog()
SOURCES_BY_ID = {source["id"]: source for source in SOURCES}
KNOWLEDGE_TEXT, GUIDANCE_SECTIONS = _load_guidance()

mcp = MCPServer("AiSpace Sources", instructions=INSTRUCTIONS)


def _tokens(value: str) -> set[str]:
    return {match.group(0).casefold() for match in TOKEN_PATTERN.finditer(value)}


def _source_score(source: dict[str, Any], query: str) -> tuple[int, list[str]]:
    query_tokens = _tokens(query)
    if not query_tokens:
        return 0, []

    weighted_fields: tuple[tuple[int, str], ...] = (
        (9, source["title"]),
        (8, " ".join(source["tags"])),
        (5, source["project_relevance"]),
        (4, source["summary"]),
        (3, " ".join(source["key_points"])),
        (2, source["category"]),
        (1, source["id"]),
    )
    score = 0
    matched: set[str] = set()
    for weight, value in weighted_fields:
        field_tokens = _tokens(value)
        hits = query_tokens & field_tokens
        score += weight * len(hits)
        matched.update(hits)

    normalized_query = " ".join(query.casefold().split())
    searchable = " ".join(str(value) for _, value in weighted_fields).casefold()
    if normalized_query and normalized_query in searchable:
        score += 12
    return score, sorted(matched)


def _guidance_score(section: dict[str, str], topic: str) -> int:
    topic_tokens = _tokens(topic)
    title_tokens = _tokens(section["title"])
    body_tokens = _tokens(section["content"])
    score = 10 * len(topic_tokens & title_tokens) + 2 * len(topic_tokens & body_tokens)
    normalized_topic = " ".join(topic.casefold().split())
    if normalized_topic and normalized_topic in section["title"].casefold():
        score += 15
    return score


@mcp.tool()
def search_sources(query: str, category: str | None = None, limit: int = 6) -> dict[str, Any]:
    """Search the local source catalog and return concise, deterministic matches."""

    if not query.strip():
        return {"query": query, "category": category, "results": [], "error": "Query must not be blank."}

    bounded_limit = max(1, min(limit, MAX_SEARCH_RESULTS))
    normalized_category = category.casefold().strip() if category else None
    ranked: list[tuple[int, str, dict[str, Any], list[str]]] = []
    for source in SOURCES:
        if normalized_category and source["category"].casefold() != normalized_category:
            continue
        score, matched_terms = _source_score(source, query)
        if score > 0:
            ranked.append((score, source["id"], source, matched_terms))

    ranked.sort(key=lambda item: (-item[0], item[1]))
    results = [
        {
            "id": source["id"],
            "title": source["title"],
            "url": source["url"],
            "category": source["category"],
            "relevance": source["project_relevance"],
            "matched_terms": matched_terms,
        }
        for _, _, source, matched_terms in ranked[:bounded_limit]
    ]
    response: dict[str, Any] = {
        "query": query,
        "category": normalized_category,
        "limit": bounded_limit,
        "results": results,
    }
    if normalized_category and normalized_category not in {source["category"] for source in SOURCES}:
        response["error"] = f"Unknown category: {category}"
    return response


@mcp.tool()
def get_source(source_id: str) -> dict[str, Any]:
    """Return one complete curated source record by stable source id."""

    source = SOURCES_BY_ID.get(source_id)
    if source is None:
        return {"found": False, "source_id": source_id, "error": f"Unknown source id: {source_id}"}
    return {"found": True, **source}


@mcp.tool()
def list_categories() -> dict[str, Any]:
    """List source categories and their catalog counts."""

    counts = Counter(source["category"] for source in SOURCES)
    return {
        "categories": [
            {"category": category, "count": counts[category]} for category in sorted(counts)
        ],
        "total_sources": len(SOURCES),
    }


@mcp.tool()
def get_guidance(topic: str) -> dict[str, Any]:
    """Return only the most relevant AiSpace guidance sections for a topic."""

    if not topic.strip():
        return {"topic": topic, "sections": [], "error": "Topic must not be blank."}

    ranked = [
        (_guidance_score(section, topic), section["title"], section)
        for section in GUIDANCE_SECTIONS
    ]
    ranked = [item for item in ranked if item[0] > 0]
    ranked.sort(key=lambda item: (-item[0], item[1]))
    sections = [item[2] for item in ranked[:MAX_GUIDANCE_SECTIONS]]
    response: dict[str, Any] = {"topic": topic, "sections": sections}
    if not sections:
        response["error"] = f"No guidance matched topic: {topic}"
    return response


@mcp.resource("aispace://sources/index")
def source_index() -> str:
    """Return a compact index of curated source ids, titles, and categories."""

    return json.dumps(
        [
            {"id": source["id"], "title": source["title"], "category": source["category"]}
            for source in SOURCES
        ],
        ensure_ascii=False,
        indent=2,
    )


@mcp.resource("aispace://knowledge")
def knowledge_resource() -> str:
    """Return the complete AiSpace engineering cheat sheet when explicitly requested."""

    return KNOWLEDGE_TEXT


if __name__ == "__main__":
    mcp.run()
