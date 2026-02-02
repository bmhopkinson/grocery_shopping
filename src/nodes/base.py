"""
Shared infrastructure for graph nodes.

Provides singleton instances of LLM client, search tool, and common utilities.
"""

from typing import Any, TypeVar
import httpx
from langchain_openai import ChatOpenAI
from langchain_community.tools import DuckDuckGoSearchResults
from langchain_core.messages import HumanMessage
from pydantic import BaseModel


# Type variable for structured output
T = TypeVar("T", bound=BaseModel)

# Singleton instances
_llm: ChatOpenAI | None = None
_search_tool: DuckDuckGoSearchResults | None = None


def get_llm() -> ChatOpenAI:
    """Get the singleton LLM instance."""
    global _llm
    if _llm is None:
        _llm = ChatOpenAI(model="gpt-5.2", temperature=0)
    return _llm


def get_search_tool() -> DuckDuckGoSearchResults:
    """Get the singleton search tool."""
    global _search_tool
    if _search_tool is None:
        _search_tool = DuckDuckGoSearchResults(max_results=10)
    return _search_tool


def create_http_client(**kwargs) -> httpx.AsyncClient:
    """
    Create an async HTTP client with browser-like headers.

    This helps avoid 403 errors from sites that block non-browser requests.
    """
    default_headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    # Merge any provided headers with defaults
    headers = {**default_headers, **kwargs.pop("headers", {})}

    return httpx.AsyncClient(
        follow_redirects=True,
        timeout=30.0,
        headers=headers,
        **kwargs
    )


def invoke_structured(output_model: type[T], prompt: str) -> T:
    """
    Invoke LLM with structured output.

    Args:
        output_model: Pydantic model class for structured output
        prompt: The prompt to send to the LLM

    Returns:
        Instance of output_model with LLM response
    """
    llm = get_llm()
    structured_llm = llm.with_structured_output(output_model)
    return structured_llm.invoke([HumanMessage(content=prompt)])
