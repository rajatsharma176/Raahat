"""
SANDBOX Bank API — simulates upcoming payment inspection.

NOTE: This tool NEVER executes real financial transactions.
It only retrieves payment schedule data. All data is synthetic.
"""
from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Any, Dict, List

from pydantic import BaseModel

logger = logging.getLogger(__name__)

DISCLAIMER = "⚠️ SANDBOX: Synthetic data. No real financial transactions are performed."


class Payment(BaseModel):
    payment_id: str
    description: str
    amount_inr: float
    due_date: str
    category: str  # rent | credit | emi | utility
    urgency: str  # critical | high | medium | low
    payee: str
    status: str = "pending"


class PaymentsResponse(BaseModel):
    account_id: str
    account_holder: str
    balance_inr: float
    payments: List[Payment]
    recommendations: List[str]
    disclaimer: str = DISCLAIMER


_DEMO_PAYMENTS = [
    Payment(
        payment_id="PAY-001",
        description="Monthly Rent",
        amount_inr=18000.0,
        due_date="2026-10-05",
        category="rent",
        urgency="critical",
        payee="Landlord - Mr. R. Verma (DEMO)",
    ),
    Payment(
        payment_id="PAY-002",
        description="Credit Card Bill",
        amount_inr=7200.0,
        due_date="2026-10-07",
        category="credit",
        urgency="high",
        payee="DemoBank Credit (SANDBOX)",
    ),
    Payment(
        payment_id="PAY-003",
        description="Mobile Plan",
        amount_inr=699.0,
        due_date="2026-10-10",
        category="utility",
        urgency="medium",
        payee="Demo Telecom",
    ),
    Payment(
        payment_id="PAY-004",
        description="Education Loan EMI",
        amount_inr=5500.0,
        due_date="2026-10-15",
        category="emi",
        urgency="high",
        payee="Demo Education Finance",
    ),
]


class BankAPI:
    """Sandbox Bank API — read-only payment inspection."""

    async def get_upcoming_payments(
        self, account_id: str = "ACC-DEMO-001"
    ) -> PaymentsResponse:
        """
        Retrieve upcoming payments within the next 30 days.

        IMPORTANT: This is read-only. No transactions are initiated.
        """
        await asyncio.sleep(0.3)
        logger.info("BankAPI.get_upcoming_payments: account=%s", account_id)

        today = datetime.utcnow().date()
        upcoming = [p for p in _DEMO_PAYMENTS if p.status == "pending"]

        recommendations = []
        critical = [p for p in upcoming if p.urgency == "critical"]
        if critical:
            recommendations.append(
                f"⚠️ Critical payment due soon: {critical[0].description} "
                f"(₹{critical[0].amount_inr:,.0f}) on {critical[0].due_date}"
            )
        recommendations.append(
            "💡 Consider requesting payment extensions from landlord "
            "during medical leave if needed."
        )
        recommendations.append(
            "💡 Credit card issuers often offer hardship programs "
            "during documented medical emergencies."
        )

        return PaymentsResponse(
            account_id=account_id,
            account_holder="Aryan Sharma (DEMO)",
            balance_inr=42350.0,
            payments=upcoming,
            recommendations=recommendations,
        )


# Module-level singleton
bank_api = BankAPI()
