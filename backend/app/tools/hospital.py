"""
SANDBOX Hospital API — simulates requesting medical documents.

This is a DEMO/SANDBOX tool. It does NOT connect to any real hospital system.
All data is synthetic and for demonstration purposes only.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


class DocumentRequest(BaseModel):
    document_type: str
    patient_id: str = "demo-patient-001"
    requesting_agent: str = "DocumentAgent"


class DocumentResponse(BaseModel):
    status: str  # "success" | "failure" | "pending"
    document_id: Optional[str] = None
    document_type: Optional[str] = None
    patient_id: Optional[str] = None
    issued_by: Optional[str] = None
    issue_date: Optional[str] = None
    metadata: dict = {}
    error: Optional[str] = None


# Synthetic document templates
_DOCUMENT_TEMPLATES = {
    "discharge_summary": {
        "issued_by": "City General Hospital (SANDBOX)",
        "metadata": {
            "admission_date": "2026-10-01",
            "discharge_date": "2026-10-06",
            "diagnosis": "Injuries sustained in road accident (DEMO DATA)",
            "treating_physician": "Dr. A. Sharma (SANDBOX)",
            "ward": "General Ward",
        },
    },
    "admission_note": {
        "issued_by": "City General Hospital (SANDBOX)",
        "metadata": {
            "admission_date": "2026-10-01",
            "admission_reason": "Road accident injuries (DEMO DATA)",
            "admitted_by": "Dr. R. Patel (SANDBOX)",
        },
    },
    "medical_certificate": {
        "issued_by": "City General Hospital (SANDBOX)",
        "metadata": {
            "valid_from": "2026-10-01",
            "valid_to": "2026-10-06",
            "reason": "Medical emergency requiring hospitalization (DEMO DATA)",
            "fit_to_resume": "2026-10-07",
        },
    },
}


class HospitalAPI:
    """Sandbox Hospital API for document requests."""

    DISCLAIMER = (
        "⚠️ SANDBOX: This is simulated demo data. "
        "Not connected to any real hospital system."
    )

    async def request_document(
        self, document_type: str, patient_id: str = "demo-patient-001"
    ) -> DocumentResponse:
        """
        Request a medical document from the hospital.

        Args:
            document_type: Type of document (discharge_summary, admission_note, etc.)
            patient_id: Patient identifier

        Returns:
            DocumentResponse with document metadata
        """
        logger.info(
            "HospitalAPI.request_document: type=%s patient=%s", document_type, patient_id
        )
        # Simulate async I/O delay
        await asyncio.sleep(0.5)

        template = _DOCUMENT_TEMPLATES.get(document_type.lower().replace(" ", "_"))
        if template is None:
            return DocumentResponse(
                status="failure",
                error=f"Unknown document type: {document_type}. "
                f"Available: {list(_DOCUMENT_TEMPLATES.keys())}",
            )

        doc_id = f"DOC-{uuid.uuid4().hex[:6].upper()}"
        return DocumentResponse(
            status="success",
            document_id=doc_id,
            document_type=document_type,
            patient_id=patient_id,
            issued_by=template["issued_by"],
            issue_date=datetime.utcnow().date().isoformat(),
            metadata={**template["metadata"], "disclaimer": self.DISCLAIMER},
        )
