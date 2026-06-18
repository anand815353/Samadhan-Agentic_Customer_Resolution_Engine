"""In-memory policy retrieval stub for tests and demo until T-044 Qdrant service."""

from __future__ import annotations

from collections.abc import Iterable

from app.rag.schemas import RetrievedPolicyChunk, RetrievalRequest, RetrievalResult
from app.seed.demo_policies import (
    POL_BUREAU,
    POL_EMI,
    POL_FRAUD,
    POL_KYC,
    POL_LOAN_STATUS,
    POL_NOC,
    POL_REFUND,
    POL_REJECTION,
    POL_RM,
    POL_SAFETY,
    POL_TOPUP,
)


def default_demo_policy_chunks() -> list[RetrievedPolicyChunk]:
    """Fixture chunks keyed by seed policy domains for unit tests."""
    return [
        RetrievedPolicyChunk(
            document_id=POL_LOAN_STATUS,
            title="Loan Application Status Policy",
            document_type="policy",
            domain="loan_status",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text=(
                "Customers may request part-prepayment after the minimum lock-in period "
                "subject to demo policy review."
            ),
            relevance_score=0.91,
            source_filename="loan_application_status_policy.md",
        ),
        RetrievedPolicyChunk(
            document_id=POL_KYC,
            title="KYC Document Policy",
            document_type="policy",
            domain="kyc",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text=(
                "Accepted KYC documents include Aadhaar, PAN, and address proof per "
                "approved demo policy."
            ),
            relevance_score=0.93,
            source_filename="kyc_document_policy.md",
        ),
        RetrievedPolicyChunk(
            document_id=POL_TOPUP,
            title="Top-Up Offer Policy",
            document_type="policy",
            domain="topup",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text=(
                "Pre-approved top-up offers in demo records are eligibility displays only "
                "and do not imply disbursement."
            ),
            relevance_score=0.9,
            source_filename="topup_offer_policy.md",
        ),
        RetrievedPolicyChunk(
            document_id=POL_REJECTION,
            title="Rejection Reason Communication Policy",
            document_type="policy",
            domain="rejection",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text="Only customer-safe rejection reasons may be shared in demo responses.",
            relevance_score=0.88,
            source_filename="rejection_reason_policy.md",
        ),
        RetrievedPolicyChunk(
            document_id=POL_EMI,
            title="EMI Payment Dispute SOP",
            document_type="sop",
            domain="emi",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text="Duplicate EMI disputes require human review in the demo workflow.",
            relevance_score=0.87,
            source_filename="emi_payment_dispute_sop.md",
            internal_only=True,
            customer_visible=False,
        ),
        RetrievedPolicyChunk(
            document_id=POL_REFUND,
            title="Refund and Reversal Policy",
            document_type="policy",
            domain="refund",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text="Refund disputes are reviewed; no real reversal occurs in the demo.",
            relevance_score=0.86,
            source_filename="refund_reversal_policy.md",
        ),
        RetrievedPolicyChunk(
            document_id=POL_NOC,
            title="NOC and Loan Statement SOP",
            document_type="sop",
            domain="noc",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text="Loan statement and NOC requests are fulfilled via mock service requests.",
            relevance_score=0.85,
            source_filename="noc_and_loan_statement_sop.md",
        ),
        RetrievedPolicyChunk(
            document_id=POL_BUREAU,
            title="Bureau and CIBIL Reporting Policy",
            document_type="policy",
            domain="bureau",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text="Bureau reporting updates may lag; mismatches require human review.",
            relevance_score=0.84,
            source_filename="bureau_reporting_policy.md",
        ),
        RetrievedPolicyChunk(
            document_id=POL_FRAUD,
            title="Fraud and Security SOP",
            document_type="sop",
            domain="fraud",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text="Fraud cases are escalated immediately; internal investigation steps are confidential.",
            relevance_score=0.83,
            source_filename="fraud_security_sop.md",
            internal_only=True,
            customer_visible=False,
        ),
        RetrievedPolicyChunk(
            document_id=POL_RM,
            title="RM Callback SOP",
            document_type="sop",
            domain="rm",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text="RM callback requests are mock records only in the demo environment.",
            relevance_score=0.82,
            source_filename="rm_callback_sop.md",
        ),
        RetrievedPolicyChunk(
            document_id=POL_SAFETY,
            title="Customer Response Safety Policy",
            document_type="policy",
            domain="safety",
            version="1.0",
            effective_date="2026-01-01",
            chunk_index=0,
            chunk_text="Customer responses must avoid unsupported financial action claims.",
            relevance_score=0.8,
            source_filename="customer_response_safety_policy.md",
        ),
    ]


class InMemoryPolicyRetrievalService:
    """Domain-filtered in-memory retrieval for tests and local demo."""

    def __init__(self, chunks: Iterable[RetrievedPolicyChunk] | None = None) -> None:
        self._chunks = list(chunks) if chunks is not None else default_demo_policy_chunks()
        self.last_request: RetrievalRequest | None = None

    async def retrieve(self, request: RetrievalRequest) -> RetrievalResult:
        self.last_request = request
        candidates = list(self._chunks)

        if request.approved_only:
            candidates = [
                chunk for chunk in candidates if chunk.approval_status == "approved"
            ]
        if request.customer_visible_only:
            candidates = [
                chunk
                for chunk in candidates
                if chunk.customer_visible and not chunk.internal_only
            ]
        if request.domain:
            candidates = [chunk for chunk in candidates if chunk.domain == request.domain]

        query_lower = request.query.lower()
        if query_lower:
            matched = [
                chunk
                for chunk in candidates
                if query_lower in chunk.chunk_text.lower()
                or query_lower in chunk.title.lower()
                or query_lower in chunk.domain.lower()
            ]
            if matched:
                candidates = matched

        if request.min_score is not None:
            candidates = [
                chunk
                for chunk in candidates
                if chunk.relevance_score is None or chunk.relevance_score >= request.min_score
            ]

        candidates.sort(
            key=lambda chunk: chunk.relevance_score if chunk.relevance_score is not None else 0.0,
            reverse=True,
        )
        selected = candidates[: request.top_k]
        confidence = selected[0].relevance_score if selected else None
        return RetrievalResult(
            chunks=selected,
            confidence=confidence,
            total_results=len(selected),
            requested_top_k=request.top_k,
            applied_domain_filter=request.domain,
            applied_score_threshold=request.min_score,
        )
