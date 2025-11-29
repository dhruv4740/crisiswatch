"""
LLM providers for CrisisWatch.
Supports Google Gemini.
"""

from abc import ABC, abstractmethod
from typing import Optional
from config import get_settings


class BaseLLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    name: str = "base"
    
    @abstractmethod
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text from a prompt."""
        pass
    
    @property
    @abstractmethod
    def is_available(self) -> bool:
        """Check if the provider is configured."""
        pass


class GeminiProvider(BaseLLMProvider):
    """Google Gemini LLM provider."""
    
    name = "gemini"
    
    def __init__(self):
        self.settings = get_settings()
        self._client = None
        self._grounded_client = None
    
    @property
    def is_available(self) -> bool:
        return self.settings.has_gemini
    
    def _get_client(self):
        if self._client is None:
            import google.generativeai as genai
            genai.configure(api_key=self.settings.gemini_api_key)
            self._client = genai.GenerativeModel("gemini-2.0-flash")
        return self._client
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text using Gemini."""
        if not self.is_available:
            raise ValueError("Gemini API key not configured")
        
        client = self._get_client()
        
        full_prompt = prompt
        if system_prompt:
            full_prompt = f"{system_prompt}\n\n{prompt}"
        
        try:
            response = await client.generate_content_async(
                full_prompt,
                generation_config={
                    "temperature": temperature,
                    "max_output_tokens": max_tokens,
                }
            )
            return response.text
        except Exception as e:
            raise RuntimeError(f"Gemini generation error: {e}")
    
    async def search_with_grounding(
        self,
        query: str,
        sites: Optional[list[str]] = None,
    ) -> dict:
        """
        Use Gemini with Google Search grounding to find current information.
        
        Args:
            query: Search query
            sites: Optional list of sites to focus on (e.g., ["twitter.com", "reddit.com"])
            
        Returns:
            dict with search results and summary
        """
        if not self.is_available:
            raise ValueError("Gemini API key not configured")
        
        import google.generativeai as genai
        
        # Format site restrictions into query
        if sites:
            site_query = " OR ".join([f"site:{site}" for site in sites])
            full_query = f"({query}) ({site_query})"
        else:
            full_query = query
        
        prompt = f"""Search the web for recent information about: {full_query}

Focus on finding:
1. Viral claims or misinformation spreading on social media
2. Fact-checks that have been done on this topic
3. Official statements or debunking efforts

Return your findings in JSON format:
{{
    "trending_claims": [
        {{"claim": "text of claim", "source": "where found", "virality": "high/medium/low", "likely_false": true/false}}
    ],
    "fact_checks_found": [
        {{"title": "fact-check title", "verdict": "verdict", "source": "fact-checker name"}}
    ],
    "summary": "Brief summary of the current situation"
}}"""

        try:
            # Use Gemini with grounding
            client = self._get_client()
            response = await client.generate_content_async(
                prompt,
                generation_config={
                    "temperature": 0.3,
                    "max_output_tokens": 2048,
                }
            )
            
            # Parse response
            import json
            text = response.text.strip()
            if "```json" in text:
                text = text.split("```json")[1].split("```")[0]
            elif "```" in text:
                text = text.split("```")[1].split("```")[0]
            
            try:
                return json.loads(text)
            except json.JSONDecodeError:
                return {"summary": text, "trending_claims": [], "fact_checks_found": []}
            
        except Exception as e:
            return {"error": str(e), "trending_claims": [], "fact_checks_found": []}


class LLMManager:
    """Manages LLM provider (Gemini)."""
    
    def __init__(self):
        self.settings = get_settings()
        self.gemini = GeminiProvider()
    
    async def generate(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> str:
        """Generate text using Gemini."""
        if not self.gemini.is_available:
            raise ValueError("No LLM provider configured. Please set GEMINI_API_KEY")
        
        return await self.gemini.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
        )
