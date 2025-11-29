"""
URL Content Extraction and Claim Detection for CrisisWatch.
Extracts article content from URLs and identifies checkable claims.
"""

import httpx
import re
from typing import Optional
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field
from tools.base import BaseTool


class ExtractedArticle(BaseModel):
    """Extracted article content."""
    url: str
    title: str
    content: str
    author: Optional[str] = None
    published_date: Optional[str] = None
    domain: str
    word_count: int


class ExtractedClaim(BaseModel):
    """A claim extracted from article content."""
    text: str = Field(description="The claim text")
    context: str = Field(description="Surrounding context")
    claim_type: str = Field(description="Type of claim: factual, opinion, prediction")
    checkworthiness: float = Field(description="How checkworthy is this claim 0-1")


class URLClaimExtractor(BaseTool):
    """Extract article content and identify claims from URLs."""
    
    name = "url_claim_extractor"
    description = "Extract article content from URLs and identify factual claims"
    
    # Common selectors for article content
    CONTENT_SELECTORS = [
        'article',
        '[role="main"]',
        '.article-content',
        '.post-content', 
        '.entry-content',
        '.story-body',
        '#article-body',
        '.article-body',
        'main',
    ]
    
    # Common selectors for title
    TITLE_SELECTORS = [
        'h1',
        '.article-title',
        '.post-title',
        '[itemprop="headline"]',
        'title',
    ]
    
    @property
    def is_available(self) -> bool:
        return True
    
    def _extract_domain(self, url: str) -> str:
        """Extract domain from URL."""
        match = re.search(r'https?://(?:www\.)?([^/]+)', url)
        return match.group(1) if match else url
    
    def _clean_text(self, text: str) -> str:
        """Clean extracted text."""
        # Remove extra whitespace
        text = re.sub(r'\s+', ' ', text)
        # Remove common garbage
        text = re.sub(r'(Share|Tweet|Email|Print|Subscribe|Newsletter|Advertisement)', '', text, flags=re.IGNORECASE)
        return text.strip()
    
    async def extract_article(self, url: str) -> Optional[ExtractedArticle]:
        """
        Extract article content from a URL.
        
        Args:
            url: The URL to extract content from
            
        Returns:
            ExtractedArticle or None if extraction fails
        """
        try:
            headers = {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            }
            
            async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
                response = await client.get(url, headers=headers)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.text, 'html.parser')
                
                # Remove script and style elements
                for script in soup(['script', 'style', 'nav', 'header', 'footer', 'aside', 'iframe']):
                    script.decompose()
                
                # Extract title
                title = ""
                for selector in self.TITLE_SELECTORS:
                    title_elem = soup.select_one(selector)
                    if title_elem:
                        title = title_elem.get_text(strip=True)
                        break
                
                # Extract main content
                content = ""
                for selector in self.CONTENT_SELECTORS:
                    content_elem = soup.select_one(selector)
                    if content_elem:
                        # Get all paragraphs
                        paragraphs = content_elem.find_all('p')
                        if paragraphs:
                            content = ' '.join([p.get_text(strip=True) for p in paragraphs])
                            break
                
                # Fallback to all paragraphs
                if not content:
                    paragraphs = soup.find_all('p')
                    content = ' '.join([p.get_text(strip=True) for p in paragraphs[:50]])
                
                content = self._clean_text(content)
                
                if not content or len(content) < 100:
                    return None
                
                # Extract author
                author = None
                author_elem = soup.select_one('[rel="author"], .author, .byline, [itemprop="author"]')
                if author_elem:
                    author = author_elem.get_text(strip=True)
                
                # Extract date
                published_date = None
                date_elem = soup.select_one('[datetime], time, .published, [itemprop="datePublished"]')
                if date_elem:
                    published_date = date_elem.get('datetime') or date_elem.get_text(strip=True)
                
                return ExtractedArticle(
                    url=url,
                    title=title,
                    content=content,
                    author=author,
                    published_date=published_date,
                    domain=self._extract_domain(url),
                    word_count=len(content.split()),
                )
                
        except Exception as e:
            print(f"Article extraction error for {url}: {e}")
            return None
    
    def identify_claims(self, text: str, max_claims: int = 10) -> list[dict]:
        """
        Identify potential factual claims in text.
        
        Uses heuristics to find statements that could be fact-checked.
        """
        claims = []
        
        # Split into sentences
        sentences = re.split(r'(?<=[.!?])\s+', text)
        
        # Patterns that indicate factual claims
        claim_patterns = [
            r'\b(studies? show|research shows?|according to|experts? say|scientists? say)',
            r'\b(confirmed|proven|discovered|revealed|found that)',
            r'\b(\d+(?:\.\d+)?%|\d+(?:,\d{3})*(?:\.\d+)?)\s+(of|people|deaths?|cases?)',
            r'\b(is|are|was|were)\s+(?:the\s+)?(first|largest|biggest|smallest|only|most)',
            r'\b(causes?|leads? to|results? in|prevents?|cures?)',
            r'\b(never|always|all|every|none|no one)',
            r'\b(government|official|authority|organization)\s+(?:says?|claims?|announced?)',
        ]
        
        for sentence in sentences:
            sentence = sentence.strip()
            if len(sentence) < 30 or len(sentence) > 500:
                continue
            
            # Skip questions and quotes
            if sentence.startswith('"') or sentence.endswith('?'):
                continue
            
            # Check for claim patterns
            checkworthiness = 0.0
            claim_type = "factual"
            
            for pattern in claim_patterns:
                if re.search(pattern, sentence, re.IGNORECASE):
                    checkworthiness += 0.15
            
            # Contains numbers = more checkworthy
            if re.search(r'\d+', sentence):
                checkworthiness += 0.1
            
            # Contains absolute terms = more checkworthy
            if re.search(r'\b(never|always|all|every|none|impossible|guaranteed)\b', sentence, re.IGNORECASE):
                checkworthiness += 0.1
            
            # Medical/health terms = more checkworthy
            if re.search(r'\b(vaccine|virus|disease|cure|treatment|symptom|hospital|death)\b', sentence, re.IGNORECASE):
                checkworthiness += 0.15
            
            # Opinion indicators = less checkworthy
            if re.search(r'\b(I think|I believe|in my opinion|probably|might|could|may)\b', sentence, re.IGNORECASE):
                checkworthiness -= 0.2
                claim_type = "opinion"
            
            checkworthiness = max(0.0, min(1.0, checkworthiness))
            
            if checkworthiness >= 0.2:
                claims.append({
                    "text": sentence,
                    "context": "",  # Could extract surrounding sentences
                    "claim_type": claim_type,
                    "checkworthiness": round(checkworthiness, 2),
                })
        
        # Sort by checkworthiness and return top claims
        claims.sort(key=lambda x: x["checkworthiness"], reverse=True)
        return claims[:max_claims]


class ImageFactCheckTool(BaseTool):
    """
    Image fact-checking tool using reverse image search and OCR.
    
    Features:
    - Reverse image search via TinEye/Google Lens
    - OCR text extraction from screenshots
    - Deepfake detection heuristics
    """
    
    name = "image_factcheck"
    description = "Check images for manipulation and extract text from screenshots"
    
    TINEYE_URL = "https://tineye.com/search"
    
    @property
    def is_available(self) -> bool:
        return True
    
    async def reverse_image_search(self, image_url: str) -> list[dict]:
        """
        Perform reverse image search to find original sources.
        
        Args:
            image_url: URL of the image to search
            
        Returns:
            List of matches with source URLs and dates
        """
        results = []
        
        try:
            # Use TinEye API (would need API key for production)
            # For now, return guidance on how to check manually
            results.append({
                "source": "tineye",
                "match_url": f"https://tineye.com/search?url={image_url}",
                "instruction": "Visit this URL to see where this image has appeared before",
                "automated": False,
            })
            
            # Google Lens search
            results.append({
                "source": "google_lens",
                "match_url": f"https://lens.google.com/uploadbyurl?url={image_url}",
                "instruction": "Use Google Lens to find visually similar images",
                "automated": False,
            })
            
        except Exception as e:
            print(f"Reverse image search error: {e}")
        
        return results
    
    async def extract_text_from_image(self, image_url: str) -> Optional[str]:
        """
        Extract text from an image using OCR.
        
        Note: For production, integrate with Google Cloud Vision, AWS Textract, or Tesseract.
        """
        # Placeholder - would need OCR service integration
        return None
    
    def detect_manipulation_signs(self, image_metadata: dict) -> dict:
        """
        Analyze image metadata for signs of manipulation.
        
        Checks for:
        - Missing EXIF data (often stripped when edited)
        - Inconsistent timestamps
        - Known editing software signatures
        """
        signs = {
            "manipulation_score": 0.0,
            "warnings": [],
            "recommendations": [],
        }
        
        # Check for missing EXIF
        if not image_metadata.get("exif"):
            signs["warnings"].append("No EXIF data found - may have been stripped")
            signs["manipulation_score"] += 0.2
        
        # Check for editing software
        software = image_metadata.get("software", "").lower()
        if any(s in software for s in ["photoshop", "gimp", "lightroom", "snapseed"]):
            signs["warnings"].append(f"Edited with: {software}")
            signs["manipulation_score"] += 0.3
        
        signs["recommendations"] = [
            "Perform reverse image search to find original version",
            "Check if the image has been reported on fact-checking sites",
            "Look for visual inconsistencies (lighting, shadows, edges)",
        ]
        
        return signs
