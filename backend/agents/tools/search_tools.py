import os
import logging
from typing import List, Dict, Any, Optional
from duckduckgo_search import DDGS
from tavily import TavilyClient

logger = logging.getLogger(__name__)

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")


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
    Searches recent news articles using DuckDuckGo News feed.
    """
    results = []
    try:
        with DDGS() as ddgs:
            ddg_news = list(ddgs.news(query, max_results=max_results))
            for item in ddg_news:
                results.append({
                    "title": item.get("title", ""),
                    "url": item.get("url", ""),
                    "snippet": item.get("body", ""),
                    "published_date": item.get("date", ""),
                    "source_type": "DUCKDUCKGO_NEWS"
                })
    except Exception as e:
        logger.error(f"News search failed: {str(e)}")
        # Fallback to general web search
        return search_web(f"news {query}", max_results=max_results)

    return results