from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import GWCFixedDeposit
from .services import (
    deposit_to_display,
    gross_interest_simple,
    monthly_interest_ledger,
    portfolio_summary_for_user,
)

User = get_user_model()


class GWCInterestTests(TestCase):
    def test_simple_gross_one_year(self):
        p = Decimal("1000000")
        r = Decimal("25")
        g = gross_interest_simple(p, r, 365)
        self.assertEqual(g, Decimal("250000.00"))

    def test_deposit_display_simple(self):
        user = User.objects.create_user(username="gwc_t1", password="x")
        d = GWCFixedDeposit.objects.create(
            user=user,
            receipt_number="RCP-001",
            principal_amount=Decimal("12000000"),
            interest_rate=Decimal("25"),
            interest_method=GWCFixedDeposit.InterestMethod.SIMPLE,
            compounding_frequency=GWCFixedDeposit.CompoundingFrequency.ANNUALLY,
            transaction_date=date(2026, 3, 1),
            start_date=date(2026, 3, 1),
            maturity_date=date(2027, 3, 1),
            tax_rate=Decimal("0"),
        )
        row = deposit_to_display(d, as_of=date(2026, 3, 1))
        self.assertEqual(row["deposit_id"], d.deposit_id)
        self.assertEqual(row["completion_percent"], 0)
        self.assertEqual(row["status"], GWCFixedDeposit.Status.ACTIVE)

    def test_portfolio_excludes_withdrawn(self):
        user = User.objects.create_user(username="gwc_t2", password="x")
        GWCFixedDeposit.objects.create(
            user=user,
            receipt_number="RCP-002",
            principal_amount=Decimal("1000"),
            interest_rate=Decimal("10"),
            interest_method=GWCFixedDeposit.InterestMethod.SIMPLE,
            compounding_frequency=GWCFixedDeposit.CompoundingFrequency.ANNUALLY,
            transaction_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            maturity_date=date(2027, 1, 1),
            status=GWCFixedDeposit.Status.WITHDRAWN,
        )
        summary = portfolio_summary_for_user(user, as_of=date(2026, 6, 1))
        self.assertEqual(summary["total_principal"], Decimal("0"))

    def test_monthly_ledger_completed_months(self):
        user = User.objects.create_user(username="gwc_t3", password="x")
        d = GWCFixedDeposit.objects.create(
            user=user,
            receipt_number="RCP-003",
            principal_amount=Decimal("120000000"),
            interest_rate=Decimal("25"),
            interest_method=GWCFixedDeposit.InterestMethod.SIMPLE,
            compounding_frequency=GWCFixedDeposit.CompoundingFrequency.ANNUALLY,
            transaction_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            maturity_date=date(2027, 1, 1),
            tax_rate=Decimal("0"),
            redeemable_monthly_interest=True,
        )
        # On 1 Apr 2026, Jan–Mar are completed calendar months.
        ledger = monthly_interest_ledger(d, as_of=date(2026, 4, 1))
        self.assertTrue(ledger["enabled"])
        self.assertEqual(len(ledger["months"]), 3)
        self.assertGreater(ledger["total_earned"], Decimal("0"))
        self.assertEqual(ledger["total_redeemed"], Decimal("0"))
        self.assertEqual(ledger["redeemable"], ledger["total_earned"])
        self.assertTrue(ledger["can_redeem"])

    def test_monthly_ledger_disabled_cannot_redeem(self):
        user = User.objects.create_user(username="gwc_t4", password="x")
        d = GWCFixedDeposit.objects.create(
            user=user,
            receipt_number="RCP-004",
            principal_amount=Decimal("12000000"),
            interest_rate=Decimal("25"),
            interest_method=GWCFixedDeposit.InterestMethod.SIMPLE,
            compounding_frequency=GWCFixedDeposit.CompoundingFrequency.ANNUALLY,
            transaction_date=date(2026, 1, 1),
            start_date=date(2026, 1, 1),
            maturity_date=date(2027, 1, 1),
            tax_rate=Decimal("0"),
            redeemable_monthly_interest=False,
        )
        ledger = monthly_interest_ledger(d, as_of=date(2026, 6, 1))
        self.assertFalse(ledger["enabled"])
        self.assertFalse(ledger["can_redeem"])
