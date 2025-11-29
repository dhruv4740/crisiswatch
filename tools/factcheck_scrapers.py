"""
Fact-Check Organization Scrapers for CrisisWatch.
Searches Snopes, PolitiFact, Full Fact, and other IFCN-certified fact-checkers.
"""

import httpx
import re
from typing import Optional
from bs4 import BeautifulSoup
from tools.base import BaseTool
from models.schemas import SearchResult


class SnopesSearchTool(BaseTool):
    """Search Snopes.com for existing fact-checks."""
    
    name = "snopes"
    description = "Search Snopes.com fact-checks - one of the oldest and most respected fact-checking sites"
    
    BASE_URL = "https://www.snopes.com"
    SEARCH_URL = "https://www.snopes.com/search/"
    
    @property
    def is_available(self) -> bool:
        return True  # No API key needed, uses web scraping
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """
        Search Snopes for fact-checks related to a claim.
        
        Args:
            query: The claim to search for
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects
        """
        results = []
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # Snopes search URL
                search_url = f"{self.SEARCH_URL}{query.replace(' ', '+')}"
                response = await client.get(search_url, headers=headers)
                
                if response.status_code != 200:
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find article cards in search results
                articles = soup.select('article.media-wrapper, .search-result, article')[:max_results]
                
                for article in articles:
                    try:
                        # Try different selectors for title and link
                        link_elem = article.select_one('a[href*="/fact-check/"], a[href*="/news/"], h3 a, .card-title a')
                        if not link_elem:
                            continue
                        
                        title = link_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        
                        if not url.startswith('http'):
                            url = f"{self.BASE_URL}{url}"
                        
                        # Get snippet/description
                        snippet_elem = article.select_one('.excerpt, .card-text, p')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else title
                        
                        # Get rating if available
                        rating_elem = article.select_one('.rating-label, .rating')
                        rating = rating_elem.get_text(strip=True) if rating_elem else ""
                        
                        if rating:
                            snippet = f"[{rating}] {snippet}"
                        
                        if title and url:
                            results.append(SearchResult(
                                title=f"Snopes: {title[:150]}",
                                url=url,
                                snippet=snippet[:500],
                                source="snopes",
                            ))
                    except Exception:
                        continue
                
        except Exception as e:
            print(f"Snopes search error: {e}")
        
        return results[:max_results]


class PolitiFactSearchTool(BaseTool):
    """Search PolitiFact.com for existing fact-checks."""
    
    name = "politifact"
    description = "Search PolitiFact - Pulitzer Prize-winning political fact-checking organization"
    
    BASE_URL = "https://www.politifact.com"
    SEARCH_URL = "https://www.politifact.com/search/"
    
    @property
    def is_available(self) -> bool:
        return True  # No API key needed
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """
        Search PolitiFact for fact-checks.
        """
        results = []
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            }
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                params = {"q": query}
                response = await client.get(self.SEARCH_URL, params=params, headers=headers)
                
                if response.status_code != 200:
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Find fact-check articles
                articles = soup.select('.o-listicle__item, .m-teaser, article')[:max_results]
                
                for article in articles:
                    try:
                        link_elem = article.select_one('a[href*="/factchecks/"], h3 a, .m-teaser__title a')
                        if not link_elem:
                            continue
                        
                        title = link_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        
                        if not url.startswith('http'):
                            url = f"{self.BASE_URL}{url}"
                        
                        # Get rating (Truth-O-Meter)
                        rating_elem = article.select_one('.m-statement__meter img, .c-image__original')
                        rating = ""
                        if rating_elem:
                            rating = rating_elem.get('alt', '') or rating_elem.get('title', '')
                        
                        # Get description
                        desc_elem = article.select_one('.m-teaser__description, .m-statement__quote')
                        snippet = desc_elem.get_text(strip=True) if desc_elem else title
                        
                        if rating:
                            snippet = f"[{rating}] {snippet}"
                        
                        if title and url:
                            results.append(SearchResult(
                                title=f"PolitiFact: {title[:150]}",
                                url=url,
                                snippet=snippet[:500],
                                source="politifact",
                            ))
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"PolitiFact search error: {e}")
        
        return results[:max_results]


class FullFactSearchTool(BaseTool):
    """Search Full Fact (UK-based fact-checker)."""
    
    name = "fullfact"
    description = "Search Full Fact - UK's independent fact-checking charity"
    
    BASE_URL = "https://fullfact.org"
    SEARCH_URL = "https://fullfact.org/search/"
    
    @property
    def is_available(self) -> bool:
        return True
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """Search Full Fact for fact-checks."""
        results = []
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                params = {"q": query}
                response = await client.get(self.SEARCH_URL, params=params, headers=headers)
                
                if response.status_code != 200:
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.select('.search-results article, .card')[:max_results]
                
                for article in articles:
                    try:
                        link_elem = article.select_one('a')
                        if not link_elem:
                            continue
                        
                        title_elem = article.select_one('h2, h3, .card-title')
                        title = title_elem.get_text(strip=True) if title_elem else link_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        
                        if not url.startswith('http'):
                            url = f"{self.BASE_URL}{url}"
                        
                        snippet_elem = article.select_one('p, .card-text')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else title
                        
                        if title and url:
                            results.append(SearchResult(
                                title=f"Full Fact: {title[:150]}",
                                url=url,
                                snippet=snippet[:500],
                                source="fullfact",
                            ))
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"Full Fact search error: {e}")
        
        return results[:max_results]


class AFPFactCheckTool(BaseTool):
    """Search AFP Fact Check for international fact-checks."""
    
    name = "afp_factcheck"
    description = "Search AFP Fact Check - Agence France-Presse's global fact-checking service"
    
    BASE_URL = "https://factcheck.afp.com"
    
    @property
    def is_available(self) -> bool:
        return True
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """Search AFP Fact Check."""
        results = []
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # AFP uses Google Custom Search
                search_url = f"{self.BASE_URL}/list/search"
                params = {"search": query}
                response = await client.get(search_url, params=params, headers=headers)
                
                if response.status_code != 200:
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.select('article, .card, .search-result')[:max_results]
                
                for article in articles:
                    try:
                        link_elem = article.select_one('a[href*="/doc.afp.com/"], a[href*="factcheck"], h3 a')
                        if not link_elem:
                            link_elem = article.select_one('a')
                        if not link_elem:
                            continue
                        
                        title_elem = article.select_one('h2, h3, .title')
                        title = title_elem.get_text(strip=True) if title_elem else link_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        
                        if url and not url.startswith('http'):
                            url = f"{self.BASE_URL}{url}"
                        
                        snippet_elem = article.select_one('p, .description')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else title
                        
                        if title and url:
                            results.append(SearchResult(
                                title=f"AFP Fact Check: {title[:150]}",
                                url=url,
                                snippet=snippet[:500],
                                source="afp_factcheck",
                            ))
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"AFP Fact Check search error: {e}")
        
        return results[:max_results]


class ReutersFactCheckTool(BaseTool):
    """Search Reuters Fact Check."""
    
    name = "reuters_factcheck"
    description = "Search Reuters Fact Check - Trusted news agency fact-checking service"
    
    BASE_URL = "https://www.reuters.com"
    SEARCH_URL = "https://www.reuters.com/site-search/"
    
    @property
    def is_available(self) -> bool:
        return True
    
    async def search(
        self,
        query: str,
        max_results: int = 5,
    ) -> list[SearchResult]:
        """Search Reuters for fact-checks."""
        results = []
        
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            }
            
            async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
                # Focus on fact-check section
                params = {"query": f"fact check {query}"}
                response = await client.get(self.SEARCH_URL, params=params, headers=headers)
                
                if response.status_code != 200:
                    return []
                
                soup = BeautifulSoup(response.text, 'html.parser')
                articles = soup.select('article, .search-result-content, [data-testid="search-result"]')[:max_results]
                
                for article in articles:
                    try:
                        link_elem = article.select_one('a[href*="/fact-check/"], a')
                        if not link_elem:
                            continue
                        
                        title_elem = article.select_one('h3, .media-story-card__headline')
                        title = title_elem.get_text(strip=True) if title_elem else link_elem.get_text(strip=True)
                        url = link_elem.get('href', '')
                        
                        if url and not url.startswith('http'):
                            url = f"{self.BASE_URL}{url}"
                        
                        snippet_elem = article.select_one('p')
                        snippet = snippet_elem.get_text(strip=True) if snippet_elem else title
                        
                        if title and url and 'fact' in url.lower():
                            results.append(SearchResult(
                                title=f"Reuters: {title[:150]}",
                                url=url,
                                snippet=snippet[:500],
                                source="reuters_factcheck",
                            ))
                    except Exception:
                        continue
                        
        except Exception as e:
            print(f"Reuters Fact Check search error: {e}")
        
        return results[:max_results]


# Aggregated tool that searches all fact-checkers
class AggregatedFactCheckTool(BaseTool):
    """Search multiple fact-checking organizations simultaneously."""
    
    name = "factcheck_aggregator"
    description = "Search Snopes, PolitiFact, Full Fact, AFP, and Reuters fact-checks simultaneously"
    
    def __init__(self):
        self.tools = [
            SnopesSearchTool(),
            PolitiFactSearchTool(),
            FullFactSearchTool(),
            AFPFactCheckTool(),
            ReutersFactCheckTool(),
        ]
    
    @property
    def is_available(self) -> bool:
        return True
    
    async def search(
        self,
        query: str,
        max_results_per_source: int = 3,
    ) -> list[SearchResult]:
        """
        Search all fact-checking sources in parallel.
        
        Returns aggregated results from all available fact-checkers.
        """
        import asyncio
        
        tasks = [tool.search(query, max_results=max_results_per_source) for tool in self.tools]
        results_lists = await asyncio.gather(*tasks, return_exceptions=True)
        
        all_results = []
        for results in results_lists:
            if isinstance(results, list):
                all_results.extend(results)
        
        return all_results
