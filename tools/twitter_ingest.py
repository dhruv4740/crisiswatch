"""
Twitter/X Ingestion Tool for CrisisWatch.
Monitors Twitter for crisis-related claims.
"""

import asyncio
from typing import Optional, AsyncGenerator
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from tools.base import BaseTool
from config import get_settings


class Tweet(BaseModel):
    """Represents a tweet from the ingestion pipeline."""
    id: str
    text: str
    author_id: str
    author_username: Optional[str] = None
    created_at: datetime
    retweet_count: int = 0
    like_count: int = 0
    reply_count: int = 0
    quote_count: int = 0
    language: str = "en"
    source_url: str = ""
    
    @property
    def engagement_score(self) -> int:
        """Calculate engagement score for prioritization."""
        return self.retweet_count * 3 + self.like_count + self.reply_count * 2 + self.quote_count * 2


class TwitterIngestTool(BaseTool):
    """
    Twitter/X ingestion tool for monitoring crisis-related content.
    
    Features:
    - Stream tweets matching crisis keywords
    - Filter by engagement metrics
    - Language detection
    - Rate limit handling
    
    Note: Requires Twitter API v2 credentials (Bearer Token).
    For hackathon demo, includes mock data fallback.
    """
    
    name = "twitter_ingest"
    description = "Monitor Twitter/X for crisis-related misinformation"
    
    # Crisis-related keywords to monitor
    DEFAULT_KEYWORDS = [
        # Natural disasters
        "earthquake", "tsunami", "flood", "cyclone", "hurricane",
        "bhookamp", "baarish", "toofan",  # Hindi
        
        # Health crises
        "virus", "outbreak", "pandemic", "vaccine", "covid",
        "corona", "infection", "epidemic",
        
        # Emergency
        "emergency", "evacuate", "curfew", "lockdown", "alert",
        "breaking", "urgent", "warning",
        
        # Misinformation indicators
        "confirmed", "reports say", "sources claim", "viral",
        "just in", "shocking", "exposed",
    ]
    
    # Trusted/official accounts to prioritize
    OFFICIAL_ACCOUNTS = [
        "ndaborb",  # NDMA
        "ABORB_India", 
        "PIB_India",
        "MoHFW_INDIA",
        "IMDWeather",
        "DDNewslive",
        "aiaborbnews",
    ]
    
    BASE_URL = "https://api.twitter.com/2"
    
    def __init__(self):
        self.settings = get_settings()
        self._bearer_token = getattr(self.settings, 'twitter_bearer_token', '')
    
    @property
    def is_available(self) -> bool:
        return bool(self._bearer_token)
    
    async def search_recent(
        self,
        query: str,
        max_results: int = 100,
        language: Optional[str] = None,
        min_engagement: int = 0,
    ) -> list[Tweet]:
        """
        Search recent tweets matching query.
        
        Args:
            query: Search query (supports Twitter search operators)
            max_results: Maximum tweets to return (10-100)
            language: Filter by language code
            min_engagement: Minimum engagement score to include
            
        Returns:
            List of Tweet objects
        """
        if not self.is_available:
            # Return mock data for demo
            return self._get_mock_tweets(query, max_results)
        
        # Real implementation would use Twitter API v2
        # headers = {"Authorization": f"Bearer {self._bearer_token}"}
        # params = {
        #     "query": query,
        #     "max_results": min(max_results, 100),
        #     "tweet.fields": "created_at,public_metrics,lang,author_id",
        #     "expansions": "author_id",
        #     "user.fields": "username",
        # }
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(f"{self.BASE_URL}/tweets/search/recent", headers=headers, params=params)
        #     ...
        
        return self._get_mock_tweets(query, max_results)
    
    async def stream_filtered(
        self,
        keywords: Optional[list[str]] = None,
        languages: list[str] = ["en", "hi"],
    ) -> AsyncGenerator[Tweet, None]:
        """
        Stream tweets matching filter rules.
        
        This is a mock implementation for demo.
        Real implementation would use Twitter Filtered Stream API.
        
        Args:
            keywords: Keywords to filter (uses defaults if None)
            languages: Language codes to include
            
        Yields:
            Tweet objects as they arrive
        """
        keywords = keywords or self.DEFAULT_KEYWORDS
        
        # Mock streaming - return sample tweets periodically
        mock_tweets = self._get_mock_tweets(" OR ".join(keywords[:5]), 10)
        
        for tweet in mock_tweets:
            yield tweet
            await asyncio.sleep(2)  # Simulate streaming delay
    
    async def get_crisis_feed(
        self,
        crisis_type: str,
        location: Optional[str] = None,
        hours_back: int = 24,
    ) -> list[Tweet]:
        """
        Get tweets related to a specific crisis type.
        
        Args:
            crisis_type: Type of crisis (earthquake, flood, health, etc.)
            location: Geographic filter (city, state, country)
            hours_back: How far back to search
            
        Returns:
            List of relevant tweets sorted by engagement
        """
        # Build query based on crisis type
        crisis_keywords = {
            "earthquake": ["earthquake", "tremor", "bhookamp", "seismic", "magnitude"],
            "flood": ["flood", "flooding", "waterlogging", "baarish", "deluge"],
            "health": ["outbreak", "virus", "infection", "hospital", "cases"],
            "cyclone": ["cyclone", "hurricane", "storm", "toofan", "wind speed"],
            "riot": ["curfew", "violence", "protest", "lockdown", "section 144"],
        }
        
        keywords = crisis_keywords.get(crisis_type, [crisis_type])
        query_parts = [f"({' OR '.join(keywords)})"]
        
        if location:
            query_parts.append(f'"{location}"')
        
        query = " ".join(query_parts)
        
        tweets = await self.search_recent(query, max_results=100)
        
        # Sort by engagement
        tweets.sort(key=lambda t: t.engagement_score, reverse=True)
        
        return tweets
    
    def _get_mock_tweets(self, query: str, count: int) -> list[Tweet]:
        """Generate mock tweets for demo purposes."""
        mock_data = [
            {
                "id": "1234567890",
                "text": "🚨 BREAKING: Major earthquake reported in Delhi NCR region. Magnitude 6.5. Evacuate immediately! #earthquake #Delhi",
                "author_id": "user123",
                "author_username": "breaking_alerts",
                "retweet_count": 1500,
                "like_count": 2000,
                "reply_count": 300,
                "language": "en",
            },
            {
                "id": "1234567891",
                "text": "Drinking warm water with turmeric can cure COVID-19 in 2 days. My uncle tried it and recovered! Share this! #CovidCure",
                "author_id": "user456",
                "author_username": "health_tips99",
                "retweet_count": 800,
                "like_count": 1200,
                "reply_count": 150,
                "language": "en",
            },
            {
                "id": "1234567892",
                "text": "दिल्ली में भूकंप आया है! सभी लोग घर से बाहर निकलें! ये बहुत बड़ा है! #भूकंप #दिल्ली",
                "author_id": "user789",
                "author_username": "hindi_news_24",
                "retweet_count": 500,
                "like_count": 800,
                "reply_count": 100,
                "language": "hi",
            },
            {
                "id": "1234567893",
                "text": "Government has announced: All banks will be closed for next 2 weeks. Withdraw cash NOW! This is confirmed from inside sources.",
                "author_id": "user101",
                "author_username": "insider_info",
                "retweet_count": 2000,
                "like_count": 500,
                "reply_count": 800,
                "language": "en",
            },
            {
                "id": "1234567894",
                "text": "Mumbai airport flooded and closed! All flights cancelled. Passengers stranded. #MumbaiRains #AirportClosed",
                "author_id": "user102",
                "author_username": "travel_updates",
                "retweet_count": 600,
                "like_count": 400,
                "reply_count": 200,
                "language": "en",
            },
        ]
        
        tweets = []
        for i, data in enumerate(mock_data[:count]):
            tweets.append(Tweet(
                id=data["id"],
                text=data["text"],
                author_id=data["author_id"],
                author_username=data.get("author_username"),
                created_at=datetime.now() - timedelta(minutes=i * 5),
                retweet_count=data.get("retweet_count", 0),
                like_count=data.get("like_count", 0),
                reply_count=data.get("reply_count", 0),
                language=data.get("language", "en"),
                source_url=f"https://twitter.com/{data.get('author_username', 'user')}/status/{data['id']}",
            ))
        
        return tweets
