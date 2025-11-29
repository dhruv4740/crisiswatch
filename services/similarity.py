"""
Claim Similarity Detection for CrisisWatch.
Uses embeddings to find similar past claims.
"""

import re
from typing import Optional
from difflib import SequenceMatcher
from collections import Counter
import math


class ClaimSimilarity:
    """
    Detect similar claims using text similarity techniques.
    Uses a combination of:
    - Jaccard similarity for word overlap
    - Cosine similarity on word vectors
    - Sequence matching for exact phrases
    """
    
    def __init__(self, similarity_threshold: float = 0.7):
        self.threshold = similarity_threshold
    
    def _tokenize(self, text: str) -> list[str]:
        """Tokenize and normalize text."""
        text = text.lower().strip()
        # Remove punctuation and split
        text = re.sub(r'[^\w\s]', '', text)
        words = text.split()
        # Remove stopwords
        stopwords = {
            'the', 'a', 'an', 'is', 'it', 'that', 'this', 'was', 'were',
            'has', 'have', 'had', 'be', 'been', 'are', 'or', 'and', 'to',
            'in', 'on', 'at', 'for', 'of', 'with', 'as', 'by', 'from',
            'true', 'false', 'claim', 'claims', 'said', 'says', 'according'
        }
        return [w for w in words if w not in stopwords and len(w) > 2]
    
    def jaccard_similarity(self, text1: str, text2: str) -> float:
        """Calculate Jaccard similarity between two texts."""
        tokens1 = set(self._tokenize(text1))
        tokens2 = set(self._tokenize(text2))
        
        if not tokens1 or not tokens2:
            return 0.0
        
        intersection = tokens1.intersection(tokens2)
        union = tokens1.union(tokens2)
        
        return len(intersection) / len(union)
    
    def cosine_similarity(self, text1: str, text2: str) -> float:
        """Calculate cosine similarity using word frequency vectors."""
        tokens1 = self._tokenize(text1)
        tokens2 = self._tokenize(text2)
        
        if not tokens1 or not tokens2:
            return 0.0
        
        # Build word frequency vectors
        counter1 = Counter(tokens1)
        counter2 = Counter(tokens2)
        
        # Get all unique words
        all_words = set(counter1.keys()).union(set(counter2.keys()))
        
        # Calculate dot product and magnitudes
        dot_product = sum(counter1.get(w, 0) * counter2.get(w, 0) for w in all_words)
        mag1 = math.sqrt(sum(v**2 for v in counter1.values()))
        mag2 = math.sqrt(sum(v**2 for v in counter2.values()))
        
        if mag1 == 0 or mag2 == 0:
            return 0.0
        
        return dot_product / (mag1 * mag2)
    
    def sequence_similarity(self, text1: str, text2: str) -> float:
        """Calculate sequence similarity for exact phrase matching."""
        return SequenceMatcher(None, text1.lower(), text2.lower()).ratio()
    
    def combined_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate combined similarity score.
        Weights: Cosine (0.4) + Jaccard (0.3) + Sequence (0.3)
        """
        cosine = self.cosine_similarity(text1, text2)
        jaccard = self.jaccard_similarity(text1, text2)
        sequence = self.sequence_similarity(text1, text2)
        
        return 0.4 * cosine + 0.3 * jaccard + 0.3 * sequence
    
    def find_similar(
        self,
        claim: str,
        past_claims: list[dict],
        threshold: Optional[float] = None
    ) -> list[dict]:
        """
        Find similar claims from a list of past claims.
        
        Args:
            claim: The new claim to check
            past_claims: List of dicts with 'claim_text' and other fields
            threshold: Similarity threshold (default: self.threshold)
        
        Returns:
            List of similar claims with similarity scores, sorted by score
        """
        threshold = threshold or self.threshold
        similar = []
        
        for past in past_claims:
            past_text = past.get('claim_text', '') or past.get('normalized', '')
            if not past_text:
                continue
            
            score = self.combined_similarity(claim, past_text)
            
            if score >= threshold:
                similar.append({
                    **past,
                    'similarity_score': round(score, 3)
                })
        
        # Sort by similarity score descending
        similar.sort(key=lambda x: x['similarity_score'], reverse=True)
        
        return similar[:5]  # Return top 5 similar claims
    
    def is_duplicate(self, claim: str, past_claims: list[dict]) -> Optional[dict]:
        """
        Check if claim is a near-duplicate (>90% similar).
        
        Returns:
            The matching claim dict if duplicate found, else None
        """
        similar = self.find_similar(claim, past_claims, threshold=0.9)
        return similar[0] if similar else None


# Global instance
_similarity_checker: Optional[ClaimSimilarity] = None


def get_similarity_checker() -> ClaimSimilarity:
    """Get or create the global similarity checker."""
    global _similarity_checker
    if _similarity_checker is None:
        _similarity_checker = ClaimSimilarity()
    return _similarity_checker
