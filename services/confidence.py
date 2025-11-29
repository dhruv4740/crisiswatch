"""
Confidence Calibration for CrisisWatch.
Post-processing rules to adjust confidence based on evidence patterns.
"""

from typing import Optional
from models.schemas import Evidence, VerdictType, SeverityLevel


# Known pseudoscience keywords that warrant high confidence FALSE verdicts
PSEUDOSCIENCE_KEYWORDS = [
    "urine cure", "cow urine", "gomutra", "urine therapy",
    "bleach cure", "mms cure", "miracle mineral",
    "5g cause", "5g corona", "5g covid",
    "vaccine autism", "vaccines cause autism",
    "flat earth", "earth is flat",
    "homeopathy cure cancer", "homeopathic cancer",
    "crystal heal", "healing crystals cure",
    "essential oil cure", "oils cure cancer",
    "alkaline water cure", "alkaline diet cancer",
    "black salve", "colloidal silver cure",
    "turpentine cure", "kerosene medicine",
    "magnetic therapy cure", "magnet heal",
]


class ConfidenceCalibrator:
    """
    Calibrates confidence scores based on evidence patterns.
    
    Rules:
    - If claim matches known pseudoscience → force high confidence
    - If 3+ high-reliability sources agree → boost confidence
    - If fact-check org already debunked → high confidence for FALSE verdict
    - If official source contradicts claim → boost confidence
    - If sources conflict → reduce confidence
    - Apply severity-based adjustments
    """
    
    # Thresholds
    HIGH_RELIABILITY_THRESHOLD = 0.8
    FACTCHECK_BOOST = 0.20  # Increased from 0.15
    OFFICIAL_BOOST = 0.15   # Increased from 0.12
    AGREEMENT_BOOST_PER_SOURCE = 0.06  # Increased from 0.05
    CONFLICT_PENALTY = 0.15
    MIN_CONFIDENCE = 0.1
    MAX_CONFIDENCE = 0.98
    PSEUDOSCIENCE_MIN_CONFIDENCE = 0.90  # Minimum for known pseudoscience
    
    def calibrate(
        self,
        base_confidence: float,
        verdict: VerdictType,
        evidence: list[Evidence],
        search_results: list = None,
        claim_text: str = None,
    ) -> tuple[float, str]:
        """
        Calibrate confidence score based on evidence.
        
        Args:
            base_confidence: Original confidence from LLM
            verdict: The verdict assigned
            evidence: List of Evidence objects
            search_results: Raw search results (optional)
            claim_text: Original claim text for pseudoscience detection (optional)
            
        Returns:
            Tuple of (calibrated_confidence, reasoning)
        """
        if not evidence:
            return max(self.MIN_CONFIDENCE, min(base_confidence, 0.4)), "Limited evidence available"
        
        confidence = base_confidence
        adjustments = []
        
        # Rule 0: Check for known pseudoscience patterns
        if claim_text and verdict in [VerdictType.FALSE, VerdictType.MOSTLY_FALSE]:
            claim_lower = claim_text.lower()
            for keyword in PSEUDOSCIENCE_KEYWORDS:
                if keyword in claim_lower:
                    if confidence < self.PSEUDOSCIENCE_MIN_CONFIDENCE:
                        old_conf = confidence
                        confidence = max(confidence, self.PSEUDOSCIENCE_MIN_CONFIDENCE)
                        adjustments.append(f"Boosted from {old_conf:.0%} to {confidence:.0%}: matches known debunked pseudoscience pattern")
                    break
        
        # Count stance distribution
        supports = sum(1 for e in evidence if e.stance == "supports")
        refutes = sum(1 for e in evidence if e.stance == "refutes")
        neutral = sum(1 for e in evidence if e.stance == "neutral")
        
        # Count high-reliability sources
        high_rel_supports = sum(
            1 for e in evidence 
            if e.reliability_score >= self.HIGH_RELIABILITY_THRESHOLD and e.stance == "supports"
        )
        high_rel_refutes = sum(
            1 for e in evidence 
            if e.reliability_score >= self.HIGH_RELIABILITY_THRESHOLD and e.stance == "refutes"
        )
        
        # Check for fact-check sources
        factcheck_sources = [e for e in evidence if e.source_type == "fact_check"]
        official_sources = [e for e in evidence if e.source_type == "official"]
        
        # Rule 1: Fact-check organization already debunked
        if factcheck_sources:
            factcheck_refutes = sum(1 for e in factcheck_sources if e.stance == "refutes")
            if factcheck_refutes > 0 and verdict in [VerdictType.FALSE, VerdictType.MOSTLY_FALSE]:
                confidence += self.FACTCHECK_BOOST * factcheck_refutes
                adjustments.append(f"+{self.FACTCHECK_BOOST * factcheck_refutes:.0%} from fact-check sources")
        
        # Rule 2: Official source contradicts claim
        if official_sources:
            official_refutes = sum(1 for e in official_sources if e.stance == "refutes")
            if official_refutes > 0:
                confidence += self.OFFICIAL_BOOST * official_refutes
                adjustments.append(f"+{self.OFFICIAL_BOOST * official_refutes:.0%} from official sources")
        
        # Rule 3: Multiple high-reliability sources agree
        if verdict in [VerdictType.FALSE, VerdictType.MOSTLY_FALSE] and high_rel_refutes >= 3:
            boost = self.AGREEMENT_BOOST_PER_SOURCE * (high_rel_refutes - 2)
            confidence += boost
            adjustments.append(f"+{boost:.0%} from {high_rel_refutes} agreeing high-reliability sources")
        elif verdict in [VerdictType.TRUE, VerdictType.MOSTLY_TRUE] and high_rel_supports >= 3:
            boost = self.AGREEMENT_BOOST_PER_SOURCE * (high_rel_supports - 2)
            confidence += boost
            adjustments.append(f"+{boost:.0%} from {high_rel_supports} agreeing high-reliability sources")
        
        # Rule 4: Source conflict penalty
        if supports > 0 and refutes > 0:
            # Significant conflict
            conflict_ratio = min(supports, refutes) / max(supports, refutes)
            if conflict_ratio > 0.5:  # Nearly equal split
                penalty = self.CONFLICT_PENALTY * conflict_ratio
                confidence -= penalty
                adjustments.append(f"-{penalty:.0%} due to conflicting sources")
        
        # Rule 5: Low evidence count penalty
        if len(evidence) < 3:
            confidence *= 0.85
            adjustments.append("-15% due to limited evidence")
        
        # Rule 6: Unverifiable should have lower confidence
        if verdict == VerdictType.UNVERIFIABLE:
            confidence = min(confidence, 0.5)
            adjustments.append("Capped at 50% for unverifiable claims")
        
        # Clamp to valid range
        confidence = max(self.MIN_CONFIDENCE, min(confidence, self.MAX_CONFIDENCE))
        
        reasoning = "; ".join(adjustments) if adjustments else "No calibration adjustments"
        
        return confidence, reasoning


def calibrate_confidence(
    base_confidence: float,
    verdict: VerdictType,
    evidence: list[Evidence],
    claim_text: str = None,
) -> tuple[float, str]:
    """
    Convenience function to calibrate confidence.
    
    Args:
        base_confidence: Original confidence score
        verdict: The verdict assigned
        evidence: List of Evidence objects
        claim_text: Original claim text for pseudoscience detection (optional)
        
    Returns:
        Tuple of (calibrated_confidence, reasoning)
    """
    calibrator = ConfidenceCalibrator()
    return calibrator.calibrate(base_confidence, verdict, evidence, claim_text=claim_text)
