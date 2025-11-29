"""
YouTube Comments Ingestion Tool for CrisisWatch.
Monitors YouTube videos and comments for misinformation.
"""

import asyncio
from typing import Optional
from datetime import datetime, timedelta
from pydantic import BaseModel, Field

from tools.base import BaseTool
from config import get_settings


class YouTubeComment(BaseModel):
    """Represents a YouTube comment."""
    id: str
    text: str
    author_name: str
    author_channel_id: str
    video_id: str
    video_title: Optional[str] = None
    published_at: datetime
    like_count: int = 0
    reply_count: int = 0
    is_reply: bool = False
    parent_id: Optional[str] = None
    language: str = "en"
    
    @property
    def engagement_score(self) -> int:
        """Calculate engagement score."""
        return self.like_count * 2 + self.reply_count * 3


class YouTubeVideo(BaseModel):
    """Represents a YouTube video."""
    id: str
    title: str
    description: str
    channel_id: str
    channel_title: str
    published_at: datetime
    view_count: int = 0
    like_count: int = 0
    comment_count: int = 0
    tags: list[str] = Field(default_factory=list)
    language: str = "en"
    
    @property
    def url(self) -> str:
        return f"https://www.youtube.com/watch?v={self.id}"


class YouTubeCommentsTool(BaseTool):
    """
    YouTube comments and video monitoring tool.
    
    Features:
    - Search videos by crisis keywords
    - Extract comments from viral videos
    - Identify misinformation in video content and comments
    - Track engagement metrics
    
    Requires YouTube Data API v3 key.
    """
    
    name = "youtube_comments"
    description = "Monitor YouTube for crisis-related misinformation in videos and comments"
    
    BASE_URL = "https://www.googleapis.com/youtube/v3"
    
    # Keywords for crisis video search
    CRISIS_KEYWORDS = [
        # English
        "earthquake today", "flood news", "covid update", "virus outbreak",
        "breaking news india", "urgent alert", "fake news exposed",
        "truth revealed", "government hiding",
        
        # Hindi
        "भूकंप", "बाढ़", "कोरोना", "वायरस",
        "सच्चाई", "असली सच", "सरकार छुपा रही",
    ]
    
    # Channels known for misinformation
    SUSPICIOUS_CHANNELS = [
        # Would be populated with known problematic channels
    ]
    
    # Official/reliable news channels
    TRUSTED_CHANNELS = [
        "ABORB_NDTV", "ABORBToday", "republic",
        "DDNational", "PIBIndia", "DDNewslive",
    ]
    
    def __init__(self):
        self.settings = get_settings()
        self._api_key = getattr(self.settings, 'youtube_api_key', '')
    
    @property
    def is_available(self) -> bool:
        return bool(self._api_key)
    
    async def search_videos(
        self,
        query: str,
        max_results: int = 25,
        published_after: Optional[datetime] = None,
        order: str = "relevance",
    ) -> list[YouTubeVideo]:
        """
        Search for videos matching query.
        
        Args:
            query: Search query
            max_results: Maximum videos to return (max 50)
            published_after: Only return videos published after this date
            order: Sort order (relevance, date, viewCount, rating)
            
        Returns:
            List of YouTubeVideo objects
        """
        if not self.is_available:
            return self._get_mock_videos(query, max_results)
        
        # Real implementation would use YouTube Data API
        # params = {
        #     "part": "snippet",
        #     "q": query,
        #     "type": "video",
        #     "maxResults": min(max_results, 50),
        #     "order": order,
        #     "key": self._api_key,
        # }
        # if published_after:
        #     params["publishedAfter"] = published_after.isoformat() + "Z"
        # 
        # async with httpx.AsyncClient() as client:
        #     response = await client.get(f"{self.BASE_URL}/search", params=params)
        #     ...
        
        return self._get_mock_videos(query, max_results)
    
    async def get_video_comments(
        self,
        video_id: str,
        max_results: int = 100,
        order: str = "relevance",
    ) -> list[YouTubeComment]:
        """
        Get comments from a video.
        
        Args:
            video_id: YouTube video ID
            max_results: Maximum comments to return
            order: Sort order (relevance, time)
            
        Returns:
            List of YouTubeComment objects
        """
        if not self.is_available:
            return self._get_mock_comments(video_id, max_results)
        
        # Real implementation would use commentThreads API
        return self._get_mock_comments(video_id, max_results)
    
    async def get_crisis_videos(
        self,
        crisis_type: str,
        hours_back: int = 24,
        min_views: int = 1000,
    ) -> list[YouTubeVideo]:
        """
        Get videos related to a specific crisis.
        
        Args:
            crisis_type: Type of crisis
            hours_back: How far back to search
            min_views: Minimum view count
            
        Returns:
            List of relevant videos sorted by views
        """
        crisis_queries = {
            "earthquake": ["earthquake today", "भूकंप breaking news"],
            "flood": ["flood news today", "बाढ़ update"],
            "health": ["covid news", "virus outbreak", "health emergency"],
            "political": ["breaking political news", "government announcement"],
        }
        
        queries = crisis_queries.get(crisis_type, [crisis_type])
        all_videos = []
        
        for query in queries:
            videos = await self.search_videos(
                query=query,
                max_results=25,
                published_after=datetime.now() - timedelta(hours=hours_back),
                order="viewCount",
            )
            all_videos.extend(videos)
        
        # Filter by views and deduplicate
        seen_ids = set()
        filtered = []
        for video in all_videos:
            if video.id not in seen_ids and video.view_count >= min_views:
                seen_ids.add(video.id)
                filtered.append(video)
        
        return sorted(filtered, key=lambda v: v.view_count, reverse=True)
    
    async def extract_claims_from_comments(
        self,
        video_id: str,
        min_engagement: int = 10,
    ) -> list[dict]:
        """
        Extract potential claims from video comments.
        
        Args:
            video_id: YouTube video ID
            min_engagement: Minimum engagement score to consider
            
        Returns:
            List of dicts with claim text and metadata
        """
        comments = await self.get_video_comments(video_id, max_results=200)
        
        # Filter by engagement
        high_engagement = [c for c in comments if c.engagement_score >= min_engagement]
        
        # Look for claim-like patterns
        claim_indicators = [
            "i heard", "they say", "it's true", "confirmed",
            "don't believe", "fake news", "real truth",
            "सच है", "झूठ है", "पक्का",
        ]
        
        claims = []
        for comment in high_engagement:
            text_lower = comment.text.lower()
            if any(indicator in text_lower for indicator in claim_indicators):
                claims.append({
                    "text": comment.text,
                    "source": f"YouTube comment on {video_id}",
                    "engagement": comment.engagement_score,
                    "author": comment.author_name,
                    "url": f"https://www.youtube.com/watch?v={video_id}&lc={comment.id}",
                })
        
        return claims
    
    def _get_mock_videos(self, query: str, count: int) -> list[YouTubeVideo]:
        """Generate mock videos for demo."""
        mock_data = [
            {
                "id": "abc123",
                "title": "BREAKING: Major earthquake hits Delhi - Live Updates",
                "description": "Live coverage of the earthquake that hit Delhi NCR region today...",
                "channel_title": "News24 India",
                "view_count": 150000,
                "like_count": 5000,
                "comment_count": 1200,
            },
            {
                "id": "def456",
                "title": "EXPOSED: The truth about COVID vaccines they don't want you to know",
                "description": "In this video we reveal shocking facts about vaccines...",
                "channel_title": "Truth Seeker",
                "view_count": 500000,
                "like_count": 20000,
                "comment_count": 5000,
            },
            {
                "id": "ghi789",
                "title": "Government hiding earthquake prediction? NASA scientist speaks out",
                "description": "A scientist claims earthquakes can be predicted and government knows...",
                "channel_title": "Conspiracy Files",
                "view_count": 200000,
                "like_count": 8000,
                "comment_count": 2000,
            },
            {
                "id": "jkl012",
                "title": "PIB Fact Check: Top 5 fake news busted this week",
                "description": "Official fact-check of viral misinformation...",
                "channel_title": "PIB India",
                "view_count": 50000,
                "like_count": 3000,
                "comment_count": 500,
            },
        ]
        
        videos = []
        for i, data in enumerate(mock_data[:count]):
            videos.append(YouTubeVideo(
                id=data["id"],
                title=data["title"],
                description=data["description"],
                channel_id=f"channel_{i}",
                channel_title=data["channel_title"],
                published_at=datetime.now() - timedelta(hours=i * 2),
                view_count=data["view_count"],
                like_count=data["like_count"],
                comment_count=data["comment_count"],
            ))
        
        return videos
    
    def _get_mock_comments(self, video_id: str, count: int) -> list[YouTubeComment]:
        """Generate mock comments for demo."""
        mock_data = [
            {
                "text": "This is 100% true! My cousin works in government and confirmed this!",
                "author_name": "TruthTeller99",
                "like_count": 150,
                "reply_count": 20,
            },
            {
                "text": "FAKE NEWS! Don't believe this. Official sources say otherwise.",
                "author_name": "FactChecker",
                "like_count": 300,
                "reply_count": 50,
            },
            {
                "text": "Everyone share this video before it gets deleted! They don't want us to know!",
                "author_name": "WakeUp",
                "like_count": 500,
                "reply_count": 80,
            },
            {
                "text": "I heard from reliable sources this is going to happen again tomorrow. Stay safe everyone.",
                "author_name": "InsiderInfo",
                "like_count": 200,
                "reply_count": 30,
            },
        ]
        
        comments = []
        for i, data in enumerate(mock_data[:count]):
            comments.append(YouTubeComment(
                id=f"comment_{i}",
                text=data["text"],
                author_name=data["author_name"],
                author_channel_id=f"author_{i}",
                video_id=video_id,
                published_at=datetime.now() - timedelta(minutes=i * 10),
                like_count=data["like_count"],
                reply_count=data["reply_count"],
            ))
        
        return comments
