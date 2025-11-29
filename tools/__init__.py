"""Search and ingestion tools for CrisisWatch."""

from .base import BaseTool
from .tavily_search import TavilySearchTool
from .google_factcheck import GoogleFactCheckTool
from .newsapi_search import NewsAPITool
from .wikipedia import WikipediaTool

# Fact-check scrapers
from .factcheck_scrapers import (
    SnopesSearchTool,
    PolitiFactSearchTool,
    FullFactSearchTool,
    AFPFactCheckTool,
    ReutersFactCheckTool,
    AggregatedFactCheckTool,
)

# URL and image extraction
from .url_extractor import URLClaimExtractor, ImageFactCheckTool

# Social media ingestion tools
from .twitter_ingest import TwitterIngestTool, Tweet
from .whatsapp_gateway import WhatsAppGatewayTool, WhatsAppMessage
from .youtube_comments import YouTubeCommentsTool, YouTubeComment, YouTubeVideo

__all__ = [
    # Base
    "BaseTool",
    
    # Search tools
    "TavilySearchTool",
    "GoogleFactCheckTool",
    "NewsAPITool",
    "WikipediaTool",
    
    # Fact-check scrapers
    "SnopesSearchTool",
    "PolitiFactSearchTool",
    "FullFactSearchTool",
    "AFPFactCheckTool",
    "ReutersFactCheckTool",
    "AggregatedFactCheckTool",
    
    # URL/Image tools
    "URLClaimExtractor",
    "ImageFactCheckTool",
    
    # Ingestion tools
    "TwitterIngestTool",
    "Tweet",
    "WhatsAppGatewayTool",
    "WhatsAppMessage",
    "YouTubeCommentsTool",
    "YouTubeComment",
    "YouTubeVideo",
]
