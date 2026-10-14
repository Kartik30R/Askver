from datetime import datetime, timedelta
import logging
from typing import List, Dict, Any

from ddgs import DDGS
from tavily import TavilyClient

from app.core.config import settings

logger = logging.getLogger(__name__)

TAVILY_API_KEY ="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"


def search_web(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Unified search utility. Attempts Tavily search first.
    Falls back to DuckDuckGo if Tavily key is missing or quota is exhausted.
    """
    results = []
    
    # 1. Try Tavily Search First
    if TAVILY_API_KEY:
        try:
            client = TavilyClient(api_key=TAVILY_API_KEY)

            end_date = datetime.now().date()
            start_date = end_date - timedelta(days=60)

            response = client.search(
                query=query, 
                max_results=max_results, 
                search_depth="advanced"
            )
            for item in response.get("results", []):
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("content", ""),
                    "source_type": "TAVILY_WEB"
                })
            if results:
                return results
        except Exception as e:
            logger.warning(f"Tavily search failed or quota exceeded ({str(e)}). Falling back to DuckDuckGo.")

    # 2. Fallback to DuckDuckGo
    try:
        with DDGS() as ddgs:
            ddg_results = list(ddgs.text(query, max_results=max_results))
            for item in ddg_results:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("href", ""),
                    "snippet": item.get("body", ""),
                    "source_type": "DUCKDUCKGO_WEB"
                })
    except Exception as e:
        logger.error(f"DuckDuckGo search also failed: {str(e)}")

    return results


def search_news(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    """
    Prefer direct web search for news-style queries and only use DDGS News as a fallback.
    This keeps the pipeline resilient when DDGS News returns empty results or stalls.
    """
    if not query or not query.strip():
        return []

    web_results = search_web(query, max_results=max_results)
    if web_results:
        normalized = []
        for item in web_results:
            normalized.append({
                "title": item.get("title", ""),
                "url": item.get("url", ""),
                "snippet": item.get("snippet", item.get("body", "")),
                "published_date": item.get("published_date"),
                "source_type": "WEB_SEARCH"
            })
        return normalized

    try:
        with DDGS() as ddgs:
            ddg_news = list(ddgs.news(query, max_results=max_results))
            results = []
            for item in ddg_news:
                if not isinstance(item, dict):
                    continue
                if not item.get("title") and not item.get("url"):
                    continue
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("body", ""),
                    "published_date": item.get("date", ""),
                    "source_type": "DUCKDUCKGO_NEWS"
                })
            if results:
                return results
    except Exception as e:
        logger.warning(f"News search failed for query '{query}': {str(e)}")

    logger.warning(f"No news or web results found for query '{query}'")
    return []