from __future__ import annotations

from dataclasses import dataclass
from typing import Dict


@dataclass
class MatchingWeights:
    intent: float = 0.25
    domain: float = 0.2
    urgency: float = 0.15
    region: float = 0.15
    budget: float = 0.15
    industry: float = 0.1


DEFAULT_WEIGHTS = MatchingWeights()


def weights_as_dict(weights: MatchingWeights = DEFAULT_WEIGHTS) -> Dict[str, float]:
    return {
        "intent": weights.intent,
        "domain": weights.domain,
        "urgency": weights.urgency,
        "region": weights.region,
        "budget": weights.budget,
        "industry": weights.industry,
    }
