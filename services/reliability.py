"""
Source Reliability Scoring for CrisisWatch.
Assigns reliability scores to sources based on type and domain.
"""

from typing import Literal
import re


# High-reliability official/government domains
OFFICIAL_DOMAINS = {
    # International Organizations
    "who.int": 0.95,
    "un.org": 0.95,
    "unicef.org": 0.95,
    "worldbank.org": 0.90,
    "imf.org": 0.90,
    "icrc.org": 0.92,
    "ifrc.org": 0.92,
    
    # Indian Government
    "india.gov.in": 0.95,
    "pib.gov.in": 0.95,
    "ndma.gov.in": 0.95,
    "mha.gov.in": 0.95,
    "mohfw.gov.in": 0.95,
    "icmr.gov.in": 0.93,
    "imd.gov.in": 0.93,
    "incois.gov.in": 0.93,
    
    # US Government
    "cdc.gov": 0.95,
    "fema.gov": 0.95,
    "nih.gov": 0.95,
    "fda.gov": 0.95,
    "usgs.gov": 0.93,
    "noaa.gov": 0.93,
    
    # Other Government
    "gov.uk": 0.93,
    "europa.eu": 0.92,
}

# Major news organizations
MAJOR_NEWS_DOMAINS = {
    # Wire Services (highest reliability among news)
    "reuters.com": 0.90,
    "apnews.com": 0.90,
    "afp.com": 0.88,
    
    # Major International
    "bbc.com": 0.88,
    "bbc.co.uk": 0.88,
    "theguardian.com": 0.85,
    "nytimes.com": 0.85,
    "washingtonpost.com": 0.85,
    "economist.com": 0.85,
    "ft.com": 0.85,
    "aljazeera.com": 0.82,
    
    # Indian News
    "thehindu.com": 0.85,
    "indianexpress.com": 0.83,
    "hindustantimes.com": 0.82,
    "ndtv.com": 0.82,
    "timesofindia.indiatimes.com": 0.80,
    "news18.com": 0.78,
    "firstpost.com": 0.78,
    "scroll.in": 0.80,
    "thewire.in": 0.80,
    "theprint.in": 0.80,
}

# Fact-checking organizations (IFCN certified and others)
FACTCHECK_DOMAINS = {
    # IFCN Certified
    "snopes.com": 0.92,
    "politifact.com": 0.92,
    "factcheck.org": 0.92,
    "fullfact.org": 0.92,
    "boomlive.in": 0.90,
    "altnews.in": 0.90,
    "factchecker.in": 0.90,
    "thequint.com/news/webqoof": 0.88,
    "indiatoday.in/fact-check": 0.88,
    "vishvasnews.com": 0.88,
    "newschecker.in": 0.88,
    
    # Other fact-checkers
    "leadstories.com": 0.85,
    "africacheck.org": 0.88,
    "chequeado.com": 0.88,
}

# Academic/Research domains
ACADEMIC_DOMAINS = {
    ".edu": 0.80,
    ".ac.in": 0.80,
    ".ac.uk": 0.80,
    "nature.com": 0.92,
    "science.org": 0.92,
    "sciencedirect.com": 0.88,
    "pubmed.ncbi.nlm.nih.gov": 0.90,
    "arxiv.org": 0.75,  # Preprints, not peer-reviewed
    "medrxiv.org": 0.72,
    "biorxiv.org": 0.72,
}


def _extract_domain(url: str) -> str:
    """Extract domain from URL."""
    if not url:
        return ""
    # Remove protocol
    url = re.sub(r'^https?://', '', url.lower())
    # Remove path
    domain = url.split('/')[0]
    # Remove www
    domain = re.sub(r'^www\.', '', domain)
    return domain


def _check_domain_patterns(domain: str) -> tuple[float, str]:
    """Check domain against known patterns."""
    # Check exact matches first
    for domains_dict, source_type in [
        (OFFICIAL_DOMAINS, "official"),
        (FACTCHECK_DOMAINS, "fact_check"),
        (MAJOR_NEWS_DOMAINS, "news"),
        (ACADEMIC_DOMAINS, "official"),  # Map academic to 'official' for schema compatibility
    ]:
        if domain in domains_dict:
            return domains_dict[domain], source_type
    
    # Check suffix patterns for academic
    for suffix, score in [(".edu", 0.80), (".ac.in", 0.80), (".ac.uk", 0.80), (".gov", 0.90), (".gov.in", 0.93)]:
        if domain.endswith(suffix):
            return score, "official"  # Both gov and academic domains map to 'official'
    
    return 0.0, "web"  # Return 'web' instead of 'unknown' for schema compatibility


class SourceReliabilityScorer:
    """
    Scores source reliability based on domain, source type, and other signals.
    """
    
    # Base scores by source type (tool origin)
    BASE_SCORES = {
        "google_factcheck": 0.90,  # Already from fact-check orgs
        "snopes": 0.92,            # IFCN-certified fact-checker
        "politifact": 0.92,        # Pulitzer Prize winning
        "fullfact": 0.90,          # UK IFCN-certified
        "afp_factcheck": 0.90,     # Major wire service
        "reuters_factcheck": 0.90, # Trusted news agency
        "factcheck_aggregator": 0.90,  # Aggregated fact-checks
        "newsapi": 0.70,           # Varies by outlet
        "tavily": 0.60,            # Web search, mixed quality
        "wikipedia": 0.75,         # Generally reliable but can be edited
    }
    
    def __init__(self):
        pass
    
    def score(
        self,
        url: str = "",
        source_name: str = "",
        tool_source: str = "web",
    ) -> tuple[float, Literal["fact_check", "news", "official", "wikipedia", "web"]]:
        """
        Calculate reliability score for a source.
        
        Args:
            url: Source URL
            source_name: Name of the source
            tool_source: Which tool returned this result (tavily, newsapi, etc.)
            
        Returns:
            Tuple of (reliability_score, source_type)
        """
        domain = _extract_domain(url)
        
        # Check against known domains
        domain_score, source_type = _check_domain_patterns(domain)
        
        if domain_score > 0:
            return domain_score, source_type
        
        # Fall back to tool-based scoring
        base_score = self.BASE_SCORES.get(tool_source, 0.50)
        
        # Determine source type
        if tool_source == "google_factcheck":
            return base_score, "fact_check"
        elif tool_source == "wikipedia":
            return 0.75, "wikipedia"
        elif tool_source == "newsapi":
            # Try to match source name against known outlets
            source_lower = source_name.lower()
            for domain, score in MAJOR_NEWS_DOMAINS.items():
                if domain.split('.')[0] in source_lower:
                    return score, "news"
            return 0.65, "news"
        else:
            return base_score, "web"
    
    def score_evidence_list(
        self,
        search_results: list,
    ) -> list[tuple[float, str]]:
        """
        Score a list of search results.
        
        Args:
            search_results: List of SearchResult objects
            
        Returns:
            List of (score, source_type) tuples
        """
        scores = []
        for result in search_results:
            tool_source = result.source.split(":")[0] if ":" in result.source else result.source
            score, source_type = self.score(
                url=result.url,
                source_name=result.title,
                tool_source=tool_source,
            )
            scores.append((score, source_type))
        return scores


# Singleton instance
_scorer = None

def get_reliability_score(
    url: str = "",
    source_name: str = "",
    tool_source: str = "web",
) -> tuple[float, str]:
    """
    Get reliability score for a source.
    
    Convenience function using singleton scorer.
    """
    global _scorer
    if _scorer is None:
        _scorer = SourceReliabilityScorer()
    return _scorer.score(url, source_name, tool_source)


def calculate_source_diversity(search_results: list) -> float:
    """
    Calculate source diversity score based on domain variety and source type mix.
    
    Scoring factors:
    - Number of unique domains (more = higher score)
    - Mix of source types (fact_check, news, official, wikipedia, web)
    - Penalize if too many from same domain
    
    Args:
        search_results: List of SearchResult objects
        
    Returns:
        Diversity score from 0.0 to 1.0
    """
    if not search_results:
        return 0.0
    
    domains: dict[str, int] = {}
    source_types: set[str] = set()
    
    for result in search_results:
        # Extract domain
        domain = _extract_domain(result.url)
        if domain:
            domains[domain] = domains.get(domain, 0) + 1
        
        # Get source type
        tool_source = result.source.split(":")[0] if ":" in result.source else result.source
        _, source_type = get_reliability_score(
            url=result.url,
            source_name=result.title,
            tool_source=tool_source,
        )
        source_types.add(source_type)
    
    # Calculate domain diversity (0-0.5)
    unique_domains = len(domains)
    total_results = len(search_results)
    domain_score = min(0.5, (unique_domains / max(total_results, 1)) * 0.6)
    
    # Penalize domain clustering (reduce score if any domain has >40% of results)
    max_domain_ratio = max(domains.values()) / total_results if domains else 0
    if max_domain_ratio > 0.4:
        domain_score *= (1 - (max_domain_ratio - 0.4))
    
    # Calculate source type diversity (0-0.5)
    # Ideal: mix of fact_check, news, official, wikipedia, web
    ideal_types = {"fact_check", "news", "official", "wikipedia", "web"}
    type_coverage = len(source_types & ideal_types) / len(ideal_types)
    type_score = type_coverage * 0.5
    
    # Bonus for having fact-check or official sources
    if "fact_check" in source_types:
        type_score += 0.1
    if "official" in source_types:
        type_score += 0.1
    
    # Combine scores (cap at 1.0)
    diversity_score = min(1.0, domain_score + type_score)
    
    return round(diversity_score, 3)


def get_diversity_breakdown(search_results: list) -> dict:
    """
    Get detailed breakdown of source diversity.
    
    Args:
        search_results: List of SearchResult objects
        
    Returns:
        Dict with diversity metrics
    """
    if not search_results:
        return {
            "unique_domains": 0,
            "total_results": 0,
            "source_types": [],
            "domain_distribution": {},
            "diversity_score": 0.0,
        }
    
    domains: dict[str, int] = {}
    source_types: dict[str, int] = {}
    
    for result in search_results:
        # Extract domain
        domain = _extract_domain(result.url)
        if domain:
            domains[domain] = domains.get(domain, 0) + 1
        
        # Get source type
        tool_source = result.source.split(":")[0] if ":" in result.source else result.source
        _, source_type = get_reliability_score(
            url=result.url,
            source_name=result.title,
            tool_source=tool_source,
        )
        source_types[source_type] = source_types.get(source_type, 0) + 1
    
    return {
        "unique_domains": len(domains),
        "total_results": len(search_results),
        "source_types": list(source_types.keys()),
        "source_type_counts": source_types,
        "domain_distribution": dict(sorted(domains.items(), key=lambda x: x[1], reverse=True)[:10]),
        "diversity_score": calculate_source_diversity(search_results),
    }
