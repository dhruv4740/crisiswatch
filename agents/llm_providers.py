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
