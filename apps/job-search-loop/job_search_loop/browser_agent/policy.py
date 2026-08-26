from __future__ import annotations

from collections.abc import Awaitable, Callable

from .contracts import ActionPlanV1, PolicyContextV1


ModelDecision = Callable[[PolicyContextV1], Awaitable[ActionPlanV1]]


class AgentPolicy:
    """Gate one Luna-selected action against the current immutable observation."""

    def __init__(self, model_decision: ModelDecision) -> None:
        self._model_decision = model_decision

    async def next_step(self, context: PolicyContextV1) -> ActionPlanV1:
        if context.remaining_steps < 1:
            return ActionPlanV1(
                based_on_observation_sha256=context.observation_sha256,
                transition="checkpointed",
                reason="step_budget_exhausted",
            )
        if not context.row_goal.strip() or not context.observation_sha256:
            raise ValueError("policy requires a row goal and fresh observation hash")
        if (
            context.validation_feedback is not None
            and context.validation_feedback.observation_sha256 != context.observation_sha256
        ):
            raise RuntimeError("validation feedback is stale for the current observation")
        if context.challenge_assessment is not None:
            if context.challenge_assessment.observation_sha256 != context.observation_sha256:
                raise RuntimeError("challenge assessment is stale for the current observation")
            return ActionPlanV1(
                based_on_observation_sha256=context.observation_sha256,
                transition="checkpointed",
                reason="visible_provider_challenge",
            )
        plan = await self._model_decision(context)
        if plan.based_on_observation_sha256 != context.observation_sha256:
            raise RuntimeError("model plan is stale for the current observation")
        if (plan.action is None) == (plan.transition is None):
            raise ValueError("plan must contain exactly one action or transition")
        if plan.transition not in {None, "checkpointed", "ineligible", "post_submit_verification"}:
            raise ValueError("model cannot assert a terminal application outcome")
        return plan
