"""
Base tool interface for CrisisWatch search tools.
"""

from abc import ABC, abstractmethod
from models.schemas import SearchResult


class BaseTool(ABC):
    """Abstract base class for all search tools."""
    
    name: str = "base_tool"
    description: str = "Base tool interface"
    
    @abstractmethod
    async def search(self, query: str, **kwargs) -> list[SearchResult]:
        """
        Execute a search query.
        
        Args:
            query: The search query string
            **kwargs: Additional tool-specific parameters
            
        Returns:
            List of SearchResult objects
        """
        pass
    
    @property
    def is_available(self) -> bool:
        """Check if the tool is properly configured and available."""
        return True
