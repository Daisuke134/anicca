from __future__ import annotations

from .contracts import ChallengeAssessmentV1, ObservationV1


def assess_challenge(observation: ObservationV1) -> ChallengeAssessmentV1 | None:
    """Return only challenges that are visibly rendered in the fresh observation."""
    if not observation.visible_challenges:
        return None
    return ChallengeAssessmentV1(
        schema_version=1,
        observation_sha256=observation.content_sha256,
        visible_providers=tuple(dict.fromkeys(observation.visible_challenges)),
    )
