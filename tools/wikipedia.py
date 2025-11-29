"""
Wikipedia API tool for CrisisWatch.
Search Wikipedia for factual information.
"""

import httpx
from tools.base import BaseTool
from models.schemas import SearchResult


class WikipediaTool(BaseTool):
    """Wikipedia API for searching factual information."""
    
    name = "wikipedia"
    description = "Search Wikipedia for factual background information on topics"
    
    BASE_URL = "https://en.wikipedia.org/w/api.php"
    HEADERS = {
        "User-Agent": "CrisisWatch/1.0 (https://github.com/crisiswatch; contact@crisiswatch.dev) python-httpx/0.27"
    }
    
    @property
    def is_available(self) -> bool:
        # Wikipedia API is free and doesn't require API key
        return True
    
    async def search(
        self,
        query: str,
        language: str = "en",
        max_results: int = 5,
    ) -> list[SearchResult]:
        """
        Search Wikipedia for relevant articles.
        
        Args:
            query: Search query
            language: Language code (e.g., "en", "hi")
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        # Use language-specific Wikipedia
        base_url = f"https://{language}.wikipedia.org/w/api.php"
        
        # First, search for relevant pages
        search_params = {
            "action": "query",
            "list": "search",
            "srsearch": query,
            "srlimit": max_results,
            "format": "json",
            "utf8": 1,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0, headers=self.HEADERS) as client:
                # Search for pages
                response = await client.get(base_url, params=search_params)
                response.raise_for_status()
                search_data = response.json()
                
                results = []
                page_ids = []
                
                for item in search_data.get("query", {}).get("search", []):
                    page_ids.append(str(item["pageid"]))
                    results.append({
                        "pageid": item["pageid"],
                        "title": item["title"],
                        "snippet": item.get("snippet", "").replace("<span class=\"searchmatch\">", "").replace("</span>", ""),
                    })
                
                if not page_ids:
                    return []
                
                # Get extracts for the pages
                extract_params = {
                    "action": "query",
                    "pageids": "|".join(page_ids[:5]),
                    "prop": "extracts|info",
                    "exintro": True,
                    "explaintext": True,
                    "exsentences": 3,
                    "inprop": "url",
                    "format": "json",
                    "utf8": 1,
                }
                
                response = await client.get(base_url, params=extract_params)
                response.raise_for_status()
                extract_data = response.json()
                
                pages = extract_data.get("query", {}).get("pages", {})
                
                search_results = []
                for result in results:
                    page = pages.get(str(result["pageid"]), {})
                    extract = page.get("extract", result["snippet"])
                    url = page.get("fullurl", f"https://{language}.wikipedia.org/wiki/{result['title'].replace(' ', '_')}")
                    
                    search_results.append(SearchResult(
                        title=result["title"],
                        url=url,
                        snippet=extract[:500] if extract else result["snippet"],
                        source="wikipedia",
                        published_date=None,
                    ))
                
                return search_results
                
        except Exception as e:
            print(f"Wikipedia API error: {e}")
            return []
