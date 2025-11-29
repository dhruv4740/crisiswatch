"""
Google Fact Check API tool for CrisisWatch.
Searches existing fact-checks from verified fact-checking organizations.
"""

import httpx
from tools.base import BaseTool
from models.schemas import SearchResult
from config import get_settings


class GoogleFactCheckTool(BaseTool):
    """Google Fact Check Tools API for searching existing fact-checks."""
    
    name = "google_factcheck"
    description = "Search existing fact-checks from verified fact-checking organizations worldwide"
    
    BASE_URL = "https://factchecktools.googleapis.com/v1alpha1/claims:search"
    
    def __init__(self):
        self.settings = get_settings()
    
    @property
    def is_available(self) -> bool:
        return self.settings.has_google_factcheck
    
    async def search(
        self,
        query: str,
        language_code: str = "en",
        max_results: int = 10,
    ) -> list[SearchResult]:
        """
        Search for existing fact-checks related to a claim.
        
        Args:
            query: The claim to search for
            language_code: Language code (e.g., "en", "hi")
            max_results: Maximum number of results
            
        Returns:
            List of SearchResult objects containing fact-check information
        """
        if not self.is_available:
            return []
        
        params = {
            "key": self.settings.google_factcheck_api_key,
            "query": query,
            "languageCode": language_code,
            "pageSize": max_results,
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.get(self.BASE_URL, params=params)
                response.raise_for_status()
                data = response.json()
            
            results = []
            for claim in data.get("claims", []):
                # Each claim may have multiple fact-check reviews
                claim_text = claim.get("text", "")
                claimant = claim.get("claimant", "Unknown")
                
                for review in claim.get("claimReview", []):
                    publisher = review.get("publisher", {})
                    results.append(SearchResult(
                        title=f"Fact-check by {publisher.get('name', 'Unknown')}: {review.get('title', '')}",
                        url=review.get("url", ""),
                        snippet=f"Claim: '{claim_text}' by {claimant}. Rating: {review.get('textualRating', 'N/A')}. {review.get('title', '')}",
                        source="google_factcheck",
                        published_date=review.get("reviewDate"),
                    ))
            
            return results
            
        except Exception as e:
            print(f"Google Fact Check API error: {e}")
            return []
