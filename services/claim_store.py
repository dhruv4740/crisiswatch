"""
Claim Store for CrisisWatch.
Tracks processed claims and prevents duplicate checking.
Supports in-memory caching with optional JSON persistence.
"""

import json
import hashlib
import os
from datetime import datetime, timedelta
from typing import Optional
from pathlib import Path
from threading import Lock

from models.schemas import FactCheckResult, VerdictType


class ClaimStore:
    """
    Stores and retrieves processed claims.
    
    Features:
    - In-memory cache for fast lookups
    - Optional JSON persistence
    - Similarity-based deduplication
    - TTL-based expiration
    """
    
    def __init__(
        self,
        persist_path: Optional[str] = None,
        cache_ttl_hours: int = 24,
        max_cache_size: int = 1000,
    ):
        """
        Initialize claim store.
        
        Args:
            persist_path: Path to JSON file for persistence (optional)
            cache_ttl_hours: Hours before cache entries expire
            max_cache_size: Maximum number of claims to keep in memory
        """
        self.persist_path = Path(persist_path) if persist_path else None
        self.cache_ttl = timedelta(hours=cache_ttl_hours)
        self.max_cache_size = max_cache_size
        
        self._cache: dict[str, dict] = {}
        self._lock = Lock()
        
        # Load from disk if persistence enabled
        if self.persist_path and self.persist_path.exists():
            self._load_from_disk()
    
    def _normalize_claim(self, claim_text: str) -> str:
        """Normalize claim text for comparison."""
        # Lowercase, remove extra whitespace
        text = claim_text.lower().strip()
        text = " ".join(text.split())
        # Remove common punctuation
        for char in ".,!?;:\"'()[]{}":
            text = text.replace(char, "")
        return text
    
    def _hash_claim(self, claim_text: str) -> str:
        """Generate hash for normalized claim."""
        normalized = self._normalize_claim(claim_text)
        return hashlib.sha256(normalized.encode()).hexdigest()[:16]
    
    def _is_expired(self, entry: dict) -> bool:
        """Check if cache entry has expired."""
        checked_at = datetime.fromisoformat(entry["checked_at"])
        return datetime.now() - checked_at > self.cache_ttl
    
    def _cleanup_expired(self):
        """Remove expired entries from cache."""
        with self._lock:
            expired_keys = [
                key for key, entry in self._cache.items()
                if self._is_expired(entry)
            ]
            for key in expired_keys:
                del self._cache[key]
    
    def _enforce_size_limit(self):
        """Remove oldest entries if cache exceeds size limit."""
        with self._lock:
            if len(self._cache) > self.max_cache_size:
                # Sort by checked_at and remove oldest
                sorted_items = sorted(
                    self._cache.items(),
                    key=lambda x: x[1]["checked_at"]
                )
                to_remove = len(self._cache) - self.max_cache_size
                for key, _ in sorted_items[:to_remove]:
                    del self._cache[key]
    
    def _load_from_disk(self):
        """Load cache from JSON file."""
        try:
            with open(self.persist_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                self._cache = data.get("claims", {})
                # Clean expired on load
                self._cleanup_expired()
        except (json.JSONDecodeError, KeyError) as e:
            print(f"Error loading claim store: {e}")
            self._cache = {}
    
    def _save_to_disk(self):
        """Save cache to JSON file."""
        if not self.persist_path:
            return
        
        try:
            # Ensure directory exists
            self.persist_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(self.persist_path, "w", encoding="utf-8") as f:
                json.dump({"claims": self._cache}, f, indent=2, default=str)
        except Exception as e:
            print(f"Error saving claim store: {e}")
    
    def exists(self, claim_text: str) -> bool:
        """
        Check if a claim has already been processed.
        
        Args:
            claim_text: The claim text to check
            
        Returns:
            True if claim exists and hasn't expired
        """
        claim_hash = self._hash_claim(claim_text)
        
        with self._lock:
            if claim_hash in self._cache:
                entry = self._cache[claim_hash]
                if not self._is_expired(entry):
                    return True
                else:
                    # Remove expired entry
                    del self._cache[claim_hash]
        
        return False
    
    def get(self, claim_text: str) -> Optional[dict]:
        """
        Get cached result for a claim.
        
        Args:
            claim_text: The claim text to look up
            
        Returns:
            Cached result dict or None if not found/expired
        """
        claim_hash = self._hash_claim(claim_text)
        
        with self._lock:
            if claim_hash in self._cache:
                entry = self._cache[claim_hash]
                if not self._is_expired(entry):
                    return entry
                else:
                    del self._cache[claim_hash]
        
        return None
    
    def store(
        self,
        claim_text: str,
        result: FactCheckResult,
    ) -> str:
        """
        Store a fact-check result.
        
        Args:
            claim_text: Original claim text
            result: FactCheckResult object
            
        Returns:
            Claim hash ID
        """
        claim_hash = self._hash_claim(claim_text)
        
        entry = {
            "claim_hash": claim_hash,
            "claim_text": claim_text,
            "normalized": self._normalize_claim(claim_text),
            "verdict": result.verdict.value,
            "confidence": result.confidence,
            "severity": result.severity.value,
            "explanation": result.explanation,
            "explanation_hindi": result.explanation_hindi,
            "correction": result.correction,
            "sources_checked": result.sources_checked,
            "overall_reliability": result.overall_reliability,
            "source_diversity": result.source_diversity,
            "checked_at": datetime.now().isoformat(),
        }
        
        with self._lock:
            self._cache[claim_hash] = entry
        
        # Cleanup and persist
        self._cleanup_expired()
        self._enforce_size_limit()
        self._save_to_disk()
        
        return claim_hash
    
    def find_similar(
        self,
        claim_text: str,
        threshold: float = 0.8,
    ) -> list[dict]:
        """
        Find similar claims in the cache.
        
        Uses simple word overlap similarity.
        
        Args:
            claim_text: Claim to find similar entries for
            threshold: Minimum similarity score (0-1)
            
        Returns:
            List of similar cached claims
        """
        normalized = self._normalize_claim(claim_text)
        words = set(normalized.split())
        
        if not words:
            return []
        
        similar = []
        
        with self._lock:
            for entry in self._cache.values():
                if self._is_expired(entry):
                    continue
                
                entry_words = set(entry["normalized"].split())
                if not entry_words:
                    continue
                
                # Jaccard similarity
                intersection = len(words & entry_words)
                union = len(words | entry_words)
                similarity = intersection / union if union > 0 else 0
                
                if similarity >= threshold:
                    similar.append({
                        **entry,
                        "similarity": similarity,
                    })
        
        return sorted(similar, key=lambda x: x["similarity"], reverse=True)
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = len(self._cache)
            
            # Count by verdict
            verdicts = {}
            severities = {}
            
            for entry in self._cache.values():
                v = entry.get("verdict", "unknown")
                s = entry.get("severity", "unknown")
                verdicts[v] = verdicts.get(v, 0) + 1
                severities[s] = severities.get(s, 0) + 1
            
            return {
                "total_claims": total,
                "by_verdict": verdicts,
                "by_severity": severities,
            }
    
    def clear(self):
        """Clear all cached claims."""
        with self._lock:
            self._cache = {}
        if self.persist_path and self.persist_path.exists():
            self.persist_path.unlink()


# Singleton instance
_store: Optional[ClaimStore] = None


def get_claim_store(
    persist_path: Optional[str] = "data/claim_cache.json",
) -> ClaimStore:
    """
    Get the singleton claim store instance.
    
    Args:
        persist_path: Path to persistence file
        
    Returns:
        ClaimStore instance
    """
    global _store
    if _store is None:
        _store = ClaimStore(persist_path=persist_path)
    return _store
