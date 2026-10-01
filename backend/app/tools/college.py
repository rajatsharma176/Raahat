"""
SANDBOX College API — simulates student records, exam policy, and leave requests.

DEMO/SANDBOX: Not connected to any real educational institution.
"""
from __future__ import annotations

import asyncio
import logging
import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel

logger = logging.getLogger(__name__)


DISCLAIMER = "⚠️ SANDBOX: Simulated demo data. Not connected to any real institution."


class StudentRecord(BaseModel):
    student_id: str
    name: str
    program: str
    semester: int
    attendance_percentage: float
    status: str
    courses: List[Dict[str, Any]]
    upcoming_exams: List[Dict[str, Any]]
    disclaimer: str = DISCLAIMER


class ExamPolicy(BaseModel):
    policy_id: str
    institution: str
    title: str
    allows_deferral: bool
    min_attendance_for_deferral: float
    required_documents: List[str]
    submission_deadline: str
    notes: str
    disclaimer: str = DISCLAIMER


class ExamRequestResult(BaseModel):
    status: str  # "submitted" | "approved" | "rejected"
    request_id: Optional[str] = None
    message: str = ""
    next_exam_date: Optional[str] = None
    disclaimer: str = DISCLAIMER


# ── Synthetic demo data ───────────────────────────────────────────────────── #

_DEMO_STUDENT: Dict[str, Any] = {
    "student_id": "STU-2024-001",
    "name": "Aryan Sharma (DEMO)",
    "program": "B.Tech Computer Science",
    "semester": 5,
    "attendance_percentage": 68.0,
    "status": "active",
    "courses": [
        {"code": "CS501", "name": "Data Science", "instructor": "Prof. K. Mehta", "credits": 4},
        {"code": "CS502", "name": "Machine Learning", "instructor": "Prof. S. Gupta", "credits": 4},
        {"code": "CS503", "name": "Database Systems", "instructor": "Prof. R. Joshi", "credits": 3},
    ],
    "upcoming_exams": [
        {
            "course": "CS501",
            "name": "Data Science",
            "date": "2026-10-03",
            "time": "10:00",
            "venue": "Exam Hall A",
        },
        {
            "course": "CS502",
            "name": "Machine Learning",
            "date": "2026-10-08",
            "time": "14:00",
            "venue": "Exam Hall B",
        },
    ],
}


class CollegeAPI:
    """Sandbox College API for student records and exam management."""

    # Mutable state to allow world events to change exam dates
    _exam_overrides: Dict[str, str] = {}

    async def get_student_record(self, student_id: str = "STU-2024-001") -> StudentRecord:
        """Retrieve student record including attendance and upcoming exams."""
        await asyncio.sleep(0.3)
        logger.info("CollegeAPI.get_student_record: student_id=%s", student_id)

        record = dict(_DEMO_STUDENT)
        # Apply any exam date overrides (from world events)
        exams = []
        for exam in record["upcoming_exams"]:
            exam = dict(exam)
            override_key = f"{exam['course']}_date"
            if override_key in self._exam_overrides:
                exam["date"] = self._exam_overrides[override_key]
            exams.append(exam)
        record["upcoming_exams"] = exams

        return StudentRecord(**record)

    async def check_exam_policy(self) -> ExamPolicy:
        """Retrieve the institution's exam deferral policy."""
        await asyncio.sleep(0.2)
        logger.info("CollegeAPI.check_exam_policy")
        return ExamPolicy(
            policy_id="POL-EXAM-2024",
            institution="Demo University (SANDBOX)",
            title="Medical Absence and Exam Deferral Policy",
            allows_deferral=True,
            min_attendance_for_deferral=60.0,
            required_documents=["medical_certificate", "discharge_summary"],
            submission_deadline="Within 5 days of exam date",
            notes=(
                "Students absent due to documented medical emergencies "
                "may request exam deferral with supporting documents. "
                "Attendance must be at least 60% to qualify. (DEMO POLICY)"
            ),
        )

    async def submit_exam_request(
        self,
        student_id: str,
        course_code: str,
        reason: str,
        documents: List[str],
    ) -> ExamRequestResult:
        """Submit a medical leave / exam deferral request."""
        await asyncio.sleep(0.4)
        logger.info(
            "CollegeAPI.submit_exam_request: student=%s course=%s docs=%s",
            student_id, course_code, documents,
        )

        # Deterministic logic: check if at least one valid medical document is present
        valid_docs = {"admission_note", "discharge_summary", "medical_certificate"}
        provided = {d.lower().replace(" ", "_") for d in documents}

        if not (valid_docs & provided):
            return ExamRequestResult(
                status="rejected",
                message=f"Missing required documents: at least one of {valid_docs} is required",
            )

        request_id = f"REQ-{uuid.uuid4().hex[:6].upper()}"
        return ExamRequestResult(
            status="submitted",
            request_id=request_id,
            message=(
                f"Exam deferral request submitted successfully for {course_code}. "
                "You will be notified of the new exam date within 48 hours."
            ),
            next_exam_date="2026-10-15",  # deferred date
        )

    def update_exam_date(self, course_code: str, new_date: str) -> None:
        """Inject a world event — exam date change."""
        self._exam_overrides[f"{course_code}_date"] = new_date
        logger.info("CollegeAPI: Exam %s date updated to %s", course_code, new_date)


# Module-level singleton
college_api = CollegeAPI()
