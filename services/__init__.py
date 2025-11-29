"""CrisisWatch services."""

from .reliability import (
    SourceReliabilityScorer,
    get_reliability_score,
    get_source_credibility,
    calculate_source_diversity,
    get_diversity_breakdown,
)
from .claim_store import ClaimStore, get_claim_store
from .confidence import ConfidenceCalibrator, calibrate_confidence, calibrate_verdict
from .notifications import (
    NotificationService,
    NotificationChannel,
    NotificationPayload,
    get_notification_service,
)
from .similarity import (
    ClaimSimilarity,
    get_similarity_checker,
)

__all__ = [
    "SourceReliabilityScorer",
    "get_reliability_score",
    "get_source_credibility",
    "calculate_source_diversity",
    "get_diversity_breakdown",
    "ClaimStore",
    "get_claim_store",
    "ConfidenceCalibrator",
    "calibrate_confidence",
    "calibrate_verdict",
    "NotificationService",
    "NotificationChannel",
    "NotificationPayload",
    "get_notification_service",
    "ClaimSimilarity",
    "get_similarity_checker",
]
