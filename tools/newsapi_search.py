"""
NewsAPI tool for CrisisWatch.
Search recent news articles for fact-checking context.
"""

import httpx
from typing import Optional
from tools.base import BaseTool
from models.schemas import SearchResult
from config import get_settings


class NewsAPITool(BaseTool):
    """NewsAPI for searching recent news articles."""
    
    name = "newsapi"
    description = "Search recent news articles from 80,000+ sources for fact-checking context"
    
    BASE_URL = "https://newsapi.org/v2/everything"
    
    def __init__(self):
        self.settings = get_settings()
    
    @property
    def is_available(self) -> bool:
        return self.settings.has_newsapi
    
    async def search(
        self,
        query: str,
        language: str = "en",
        sort_by: str = "relevancy",
        max_results: int = 10,
        domains: Optional[str] = None,
    ) -> list[SearchResult]:
        """
        Search news articles.
        
        Args:
            query: Search query
            language: Language code (e.g., "en", "hi")
            sort_by: Sort order - "relevancy", "popularity", or "publishedAt"
            max_results: Maximum number of results
            domains: Comma-separated list of domains to search (e.g., "bbc.com,cnn.com")
            
        Returns:
            List of SearchResult objects
        """
        if not self.is_available:
            return []
        
        params = {
            "apiKey": self.settings.newsapi_key,
            "q": query,
            "language": language,
            "sortBy": sort_by,
            "pageSize": min(max_results, 100),
        }
        
        if domains:
            params["domains"] = domains
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
            
            if data.get("status") != "ok":
                print(f"NewsAPI error: {data.get('message', 'Unknown error')}")
                return []
            
            results = []
            for article in data.get("articles", []):
                source_name = article.get("source", {}).get("name", "Unknown")
                results.append(SearchResult(
                    title=article.get("title", ""),
                    url=article.get("url", ""),
                    snippet=article.get("description", "") or article.get("content", "")[:500],
                    source=f"newsapi:{source_name}",
                    published_date=article.get("publishedAt"),
                ))
            
            return results
            
        except Exception as e:
            print(f"NewsAPI error: {e}")
            return []
