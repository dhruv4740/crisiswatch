"""
Tavily web search tool for CrisisWatch.
AI-optimized web search for fact-checking.
"""

import httpx
from typing import Optional
from tools.base import BaseTool
from models.schemas import SearchResult
from config import get_settings


class TavilySearchTool(BaseTool):
    """Tavily AI-powered web search tool."""
    
    name = "tavily_search"
    description = "Search the web using Tavily AI-optimized search for fact-checking queries"
    
    BASE_URL = "https://api.tavily.com/search"
    
    def __init__(self):
        self.settings = get_settings()
    
    @property
    def is_available(self) -> bool:
        return self.settings.has_tavily
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
        search_depth: str = "advanced",
        include_domains: Optional[list[str]] = None,
        exclude_domains: Optional[list[str]] = None,
    ) -> list[SearchResult]:
        """
        Search the web using Tavily.
        
        Args:
            query: Search query
            max_results: Maximum number of results (default 5)
            search_depth: "basic" or "advanced" (default "advanced")
            include_domains: List of domains to include
            exclude_domains: List of domains to exclude
            
        Returns:
            List of SearchResult objects
        """
        if not self.is_available:
            return []
        
        payload = {
            "api_key": self.settings.tavily_api_key,
            "query": query,
            "max_results": max_results,
            "search_depth": search_depth,
            "include_answer": True,
        }
        
        if include_domains:
            payload["include_domains"] = include_domains
        if exclude_domains:
            payload["exclude_domains"] = exclude_domains
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(self.BASE_URL, json=payload)
                response.raise_for_status()
                data = response.json()
            
            results = []
            for item in data.get("results", []):
                results.append(SearchResult(
                    title=item.get("title", ""),
                    url=item.get("url", ""),
                    snippet=item.get("content", ""),
                    source="tavily",
                    published_date=item.get("published_date"),
                ))
            
            return results
            
        except Exception as e:
            print(f"Tavily search error: {e}")
            return []
