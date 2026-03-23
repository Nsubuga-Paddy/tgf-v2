from datetime import date
from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase

from .models import GWCFixedDeposit
from .services import deposit_to_display, gross_interest_simple, portfolio_summary_for_user

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
