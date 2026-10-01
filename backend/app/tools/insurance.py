"""
SANDBOX Insurance API — simulates claim submission with deliberate failure mode.

CRITICAL DEMO BEHAVIOR:
- First claim attempt WITHOUT discharge_summary → REJECTED (triggers replanning)
- Retry WITH discharge_summary → SUCCESS

DEMO/SANDBOX: Not connected to any real insurance company.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)

DISCLAIMER = "⚠️ SANDBOX: Simulated demo data. Not connected to any real insurer."


class InsurancePolicy(BaseModel):
    policy_id: str
    holder: str
    insurer: str
    coverage_type: str
    coverage_details: List[str]
    required_documents_for_claim: List[str]
    claim_filing_deadline_days: int
    disclaimer: str = DISCLAIMER


class ClaimResult(BaseModel):
    status: str  # "submitted" | "rejected" | "pending"
    claim_id: Optional[str] = None
    reason: Optional[str] = None
    missing_dependencies: List[str] = []
    message: str = ""
    disclaimer: str = DISCLAIMER


class InsuranceAPI:
    """Sandbox Insurance API for policy retrieval and claim submission."""

    def __init__(self) -> None:
        # Track whether discharge_summary has been provided
        self._claim_attempts: int = 0

    async def get_policy(self, policy_id: str = "HC-12345") -> InsurancePolicy:
        """Retrieve insurance policy details."""
        await asyncio.sleep(0.3)
        logger.info("InsuranceAPI.get_policy: policy_id=%s", policy_id)
        return InsurancePolicy(
            policy_id=policy_id,
            holder="Aryan Sharma (DEMO)",
            insurer="HealthCo Insurance (SANDBOX)",
            coverage_type="Comprehensive Health",
            coverage_details=[
                "Hospitalization: up to ₹5,00,000 per year",
                "Accident coverage: included",
                "Pre/post hospitalization: 30/60 days",
                "Day care procedures: covered",
            ],
            required_documents_for_claim=[
                "admission_note",
                "discharge_summary",
                "medical_bills",
                "treating_physician_report",
            ],
            claim_filing_deadline_days=30,
        )

    async def get_required_documents(self, claim_type: str = "hospitalization") -> Dict[str, Any]:
        """Get required documents for a specific claim type."""
        await asyncio.sleep(0.2)
        return {
            "claim_type": claim_type,
            "required": ["admission_note", "discharge_summary"],
            "optional": ["medical_bills", "pharmacy_receipts"],
            "notes": "Discharge summary is mandatory for hospitalization claims. (DEMO POLICY)",
        }

    async def create_claim(
        self,
        policy_id: str,
        documents: List[str],
        claim_type: str = "hospitalization",
    ) -> ClaimResult:
        """
        Submit an insurance claim.

        DEMO BEHAVIOR:
        - Missing discharge_summary → REJECTED with explicit missing_dependencies
        - All required docs present → SUCCESS

        This deliberate failure triggers the real replanning loop.
        """
        await asyncio.sleep(0.5)
        self._claim_attempts += 1
        provided = {d.lower().replace(" ", "_") for d in documents}

        logger.info(
            "InsuranceAPI.create_claim: attempt=%d policy=%s documents=%s",
            self._claim_attempts, policy_id, provided,
        )

        # Check for discharge_summary (mandatory)
        if "discharge_summary" not in provided:
            return ClaimResult(
                status="rejected",
                reason="Missing discharge summary — required for all hospitalization claims.",
                missing_dependencies=["discharge_summary"],
                message=(
                    "Claim rejected: Discharge summary is mandatory for "
                    "hospitalization claims. Please provide this document and resubmit."
                ),
            )

        # Check for admission_note (mandatory)
        if "admission_note" not in provided:
            return ClaimResult(
                status="rejected",
                reason="Missing admission note.",
                missing_dependencies=["admission_note"],
                message="Claim rejected: Admission note is required.",
            )

        claim_id = f"CLM-{uuid.uuid4().hex[:6].upper()}"
        return ClaimResult(
            status="submitted",
            claim_id=claim_id,
            message=(
                f"Insurance claim {claim_id} submitted successfully. "
                "Expected processing time: 7-10 business days. (DEMO)"
            ),
        )


# Module-level singleton
insurance_api = InsuranceAPI()
