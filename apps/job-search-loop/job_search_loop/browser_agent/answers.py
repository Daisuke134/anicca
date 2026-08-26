from __future__ import annotations

import hashlib
import json
from collections.abc import Awaitable, Callable

from .answer_memory import AnswerMemory
from .candidate_memory import CandidateMemoryView
from .contracts import FieldQuestionV1, ResolvedAnswerV1


ModelResolver = Callable[
    [FieldQuestionV1, CandidateMemoryView], Awaitable[tuple[str, str, object, tuple[str, ...]] | None]
]
_KINDS = {"exact", "derived", "generated", "conservative"}


def _answer_sha(value: object) -> str:
    payload = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode()).hexdigest()


def _option(options: tuple[str, ...]) -> str:
    preferred = (
        "prefer not to say", "decline to answer", "i don't wish to answer",
        "not applicable", "none", "no",
    )
    normalized = {value.casefold().strip(): value for value in options}
    for value in preferred:
        if value in normalized:
            return normalized[value]
    return options[0]


def _conservative(question: FieldQuestionV1) -> object:
    if question.options:
        return _option(question.options)
    kind = question.field_type.casefold()
    if kind in {"checkbox", "boolean", "radio"}:
        return False
    if kind in {"number", "integer"}:
        return 0
    return "Not provided"


class AnswerResolver:
    """Resolve every question without a missing-context or blocked outcome."""

    def __init__(
        self,
        candidate_memory: CandidateMemoryView,
        answer_memory: AnswerMemory,
        model_resolver: ModelResolver,
    ) -> None:
        self._candidate = candidate_memory
        self._answers = answer_memory
        self._model = model_resolver

    async def resolve(self, question: FieldQuestionV1) -> ResolvedAnswerV1:
        if not question.label.strip():
            raise ValueError("field label is required")
        known_concept = self._answers.concept_for_question(question.label)
        if known_concept:
            record = self._answers.lookup(known_concept)
            if record is not None and (not question.options or record.answer in question.options):
                return ResolvedAnswerV1(
                    record.concept, record.kind, record.answer, record.provenance,
                    _answer_sha(record.answer),
                )

        proposal = await self._model(question, self._candidate)
        if proposal is not None:
            concept, kind, value, provenance = proposal
        else:
            concept = f"field.{hashlib.sha256(question.label.casefold().encode()).hexdigest()}"
            kind, value, provenance = "conservative", _conservative(question), ("least_claiming_fallback",)
        if not concept.strip() or kind not in _KINDS or not provenance:
            concept = f"field.{hashlib.sha256(question.label.casefold().encode()).hexdigest()}"
            kind, value, provenance = "conservative", _conservative(question), ("least_claiming_fallback",)
        if question.options and value not in question.options:
            kind, value, provenance = "conservative", _option(question.options), ("current_option_fallback",)
        self._answers.remember(
            concept=concept,
            answer=value,
            kind=kind,
            provenance=tuple(provenance),
            question_variants=(question.label,),
        )
        return ResolvedAnswerV1(concept, kind, value, tuple(provenance), _answer_sha(value))
