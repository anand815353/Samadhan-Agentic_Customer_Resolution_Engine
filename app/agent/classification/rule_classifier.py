"""Deterministic rule-based intent classification engine (T-053)."""

from __future__ import annotations

import re
from dataclasses import dataclass

from app.agent.classification.rule_patterns import (
    EXCLUSION_DEFINITIONS,
    INTENT_PRECEDENCE,
    RULE_CLASSIFIER_VERSION,
    RULE_DEFINITIONS,
    RuleDefinition,
    intent_precedence_rank,
)
from app.core.config import Settings
from app.tickets.constants import TicketIntent

RULE_MIN_CANDIDATE_SCORE = 0.25
UNKNOWN_FALLBACK_CONFIDENCE = 0.20
MAX_REASON_LENGTH = 200
MULTI_RULE_BONUS = 0.05
MAX_CANDIDATES_STORED = 3

_TXN_REF_PATTERN = re.compile(r"\btxn[-_]?\w+\b", re.IGNORECASE)
_CURRENCY_PATTERN = re.compile(r"₹\s*\d+")
_RM_WORD_PATTERN = re.compile(r"\brm\b", re.IGNORECASE)


@dataclass(frozen=True)
class RuleMatch:
    """A single rule hit against the normalized message."""

    rule_id: str
    intent: TicketIntent
    weight: float
    matched_text: str


@dataclass(frozen=True)
class RuleClassificationResult:
    """Outcome of deterministic rule classification."""

    intent: TicketIntent
    confidence: float
    matched_rule_ids: tuple[str, ...]
    candidates: dict[TicketIntent, float]
    reason: str
    ambiguous: bool
    accepted_by_threshold: bool


def prepare_message_for_matching(message: str) -> str:
    """Normalize message text for deterministic keyword/phrase matching."""
    text = message.casefold()
    text = _TXN_REF_PATTERN.sub(" ", text)
    text = _CURRENCY_PATTERN.sub(" ", text)
    text = text.replace("-", " ")
    text = re.sub(r"[^\w\s]", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return f" {text} "


def _pattern_matches(prepared: str, pattern: str, *, kind: str) -> bool:
    if kind == "keyword" and pattern.strip() == "rm":
        return _RM_WORD_PATTERN.search(prepared) is not None
    needle = f" {pattern.casefold().strip()} "
    return needle in prepared


def _collect_matches(prepared: str) -> list[RuleMatch]:
    matches: list[RuleMatch] = []
    for rule in RULE_DEFINITIONS:
        if _pattern_matches(prepared, rule.pattern, kind=rule.kind):
            matches.append(
                RuleMatch(
                    rule_id=rule.rule_id,
                    intent=rule.intent,
                    weight=rule.weight,
                    matched_text=rule.pattern,
                )
            )
    return matches


def _apply_exclusions(prepared: str, scores: dict[TicketIntent, float]) -> dict[TicketIntent, float]:
    adjusted = dict(scores)
    for exclusion in EXCLUSION_DEFINITIONS:
        if _pattern_matches(prepared, exclusion.conflict_pattern, kind="phrase"):
            current = adjusted.get(exclusion.penalized_intent, 0.0)
            adjusted[exclusion.penalized_intent] = max(0.0, current - exclusion.penalty)
    return adjusted


def _score_intents(matches: list[RuleMatch]) -> dict[TicketIntent, float]:
    scores: dict[TicketIntent, float] = {}
    rule_ids_by_intent: dict[TicketIntent, set[str]] = {}
    for match in matches:
        scores[match.intent] = scores.get(match.intent, 0.0) + match.weight
        rule_ids_by_intent.setdefault(match.intent, set()).add(match.rule_id)

    for intent, rule_ids in rule_ids_by_intent.items():
        if len(rule_ids) > 1:
            scores[intent] = min(1.0, scores[intent] + MULTI_RULE_BONUS)

    return {intent: min(1.0, score) for intent, score in scores.items()}


def _rank_candidates(scores: dict[TicketIntent, float]) -> list[tuple[TicketIntent, float]]:
    candidates = [
        (intent, score)
        for intent, score in scores.items()
        if score >= RULE_MIN_CANDIDATE_SCORE
    ]
    candidates.sort(
        key=lambda item: (-item[1], intent_precedence_rank(item[0]), item[0]),
    )
    return candidates


def _select_primary_candidate(
    ranked: list[tuple[TicketIntent, float]],
) -> tuple[TicketIntent, float]:
    qualifying = [item for item in ranked if item[1] >= RULE_MIN_CANDIDATE_SCORE]
    if len(qualifying) >= 2:
        qualifying.sort(key=lambda item: (intent_precedence_rank(item[0]), -item[1], item[0]))
        return qualifying[0]
    if qualifying:
        return qualifying[0]
    return ranked[0]


def _truncate_reason(reason: str) -> str:
    if len(reason) <= MAX_REASON_LENGTH:
        return reason
    return f"{reason[: MAX_REASON_LENGTH - 3]}..."


def classify_by_rules(
    message: str,
    *,
    settings: Settings | None = None,
) -> RuleClassificationResult:
    """Classify a normalized customer message using deterministic rules."""
    _ = settings
    prepared = prepare_message_for_matching(message)
    matches = _collect_matches(prepared)
    scores = _apply_exclusions(prepared, _score_intents(matches))

    ranked = _rank_candidates(scores)
    if not ranked:
        return RuleClassificationResult(
            intent="unknown",
            confidence=UNKNOWN_FALLBACK_CONFIDENCE,
            matched_rule_ids=tuple(),
            candidates={},
            reason="no rule evidence",
            ambiguous=False,
            accepted_by_threshold=False,
        )

    accept_threshold = (
        settings.intent_classifier_rule_accept_threshold if settings is not None else 0.75
    )
    ambiguity_gap = settings.intent_classifier_ambiguity_gap if settings is not None else 0.15

    top_intent, top_score = _select_primary_candidate(ranked)
    second_score = next((score for intent, score in ranked if intent != top_intent), 0.0)
    ambiguous = (
        top_score < accept_threshold
        and len(ranked) > 1
        and second_score >= RULE_MIN_CANDIDATE_SCORE
        and (top_score - second_score) < ambiguity_gap
    )
    accepted = top_score >= accept_threshold and not ambiguous

    matched_rule_ids = tuple(
        match.rule_id for match in matches if match.intent == top_intent
    )
    reason = _truncate_reason(
        f"rule match: {top_intent} score={top_score:.2f} rules={','.join(matched_rule_ids) or 'none'}",
    )

    candidates = dict(ranked[:MAX_CANDIDATES_STORED])

    return RuleClassificationResult(
        intent=top_intent if accepted else top_intent,
        confidence=top_score,
        matched_rule_ids=matched_rule_ids,
        candidates=candidates,
        reason=reason,
        ambiguous=ambiguous,
        accepted_by_threshold=accepted,
    )


def rule_classifier_version() -> str:
    """Return the active rule classifier version identifier."""
    return RULE_CLASSIFIER_VERSION


def all_supported_intents_for_rules() -> tuple[TicketIntent, ...]:
    """Return intents covered by explicit rule precedence ordering."""
    return INTENT_PRECEDENCE
