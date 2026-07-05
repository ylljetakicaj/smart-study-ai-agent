"""
mcp_server.py — External knowledge MCP server for Smart Study AI Agent.

Exposes three tools via the Model Context Protocol:
  - wiki_summary(topic)     : short Wikipedia summary
  - arxiv_search(query)     : related academic papers
  - web_define(term)        : dictionary definition

Launched over stdio by the ADK agent as an MCPToolset.

Run standalone:
    python -m app.mcp_server
"""

from __future__ import annotations

import json
import urllib.parse
import urllib.request

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    raise SystemExit("Install the 'mcp' package: pip install mcp")


mcp = FastMCP("smart-study-external-tools")


def _http_get_json(url: str, timeout: int = 10) -> dict:
    """Simple JSON GET with a browser-like User-Agent."""
    req = urllib.request.Request(url, headers={"User-Agent": "SmartStudyAI/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


# ---------------------------------------------------------------------------
# Tool 1: Wikipedia summary
# ---------------------------------------------------------------------------
@mcp.tool()
def wiki_summary(topic: str) -> str:
    """Return a short Wikipedia summary of a topic.

    Useful when a student asks about a concept not in their uploaded notes.
    """
    title = urllib.parse.quote(topic.strip().replace(" ", "_"))
    url = f"https://en.wikipedia.org/api/rest_v1/page/summary/{title}"
    try:
        data = _http_get_json(url)
        extract = data.get("extract")
        if not extract:
            return f"No Wikipedia summary found for '{topic}'."
        page = data.get("content_urls", {}).get("desktop", {}).get("page", "")
        return f"{extract}\n\nSource: {page}"
    except Exception as exc:
        return f"Could not fetch Wikipedia summary for '{topic}': {exc}"


# ---------------------------------------------------------------------------
# Tool 2: arXiv paper search
# ---------------------------------------------------------------------------
@mcp.tool()
def arxiv_search(query: str, max_results: int = 3) -> str:
    """Search arXiv for academic papers matching a query.

    Useful for recommending further reading on a topic.
    """
    q = urllib.parse.quote(query.strip())
    url = (
        "http://export.arxiv.org/api/query?"
        f"search_query=all:{q}&start=0&max_results={max_results}"
    )
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "SmartStudyAI/1.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            xml = resp.read().decode("utf-8")
        entries = xml.split("<entry>")[1:]
        results = []
        for e in entries[:max_results]:
            title = e.split("<title>")[1].split("</title>")[0].strip() if "<title>" in e else "Untitled"
            link = e.split("<id>")[1].split("</id>")[0].strip() if "<id>" in e else ""
            results.append(f"- {title}\n  {link}")
        return "\n".join(results) if results else f"No arXiv papers found for '{query}'."
    except Exception as exc:
        return f"Could not search arXiv for '{query}': {exc}"


# ---------------------------------------------------------------------------
# Tool 3: Dictionary definition
# ---------------------------------------------------------------------------
@mcp.tool()
def web_define(term: str) -> str:
    """Return a concise dictionary definition of a term."""
    t = urllib.parse.quote(term.strip())
    url = f"https://api.dictionaryapi.dev/api/v2/entries/en/{t}"
    try:
        data = _http_get_json(url)
        meanings = data[0].get("meanings", [])
        if not meanings:
            return f"No definition found for '{term}'."
        defs = meanings[0].get("definitions", [])
        definition = defs[0].get("definition", "") if defs else ""
        pos = meanings[0].get("partOfSpeech", "")
        return f"{term} ({pos}): {definition}"
    except Exception as exc:
        return f"Could not define '{term}': {exc}"


if __name__ == "__main__":
    mcp.run(transport="stdio")
