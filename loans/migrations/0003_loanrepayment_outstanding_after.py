from decimal import Decimal

from django.db import migrations, models


ZERO = Decimal("0.00")


def backfill_outstanding_after(apps, schema_editor):
    MemberLoan = apps.get_model("loans", "MemberLoan")
    LoanRepayment = apps.get_model("loans", "LoanRepayment")

    for loan in MemberLoan.objects.all():
        repayments = list(
            LoanRepayment.objects.filter(loan=loan).order_by("posted_at", "id")
        )
        if not repayments:
            continue

        total_paid = sum((payment.amount for payment in repayments), ZERO)
        running_outstanding = loan.outstanding + total_paid
        for payment in repayments:
            running_outstanding = max(ZERO, running_outstanding - payment.amount)
            payment.outstanding_after = running_outstanding
            payment.save(update_fields=["outstanding_after"])


class Migration(migrations.Migration):

    dependencies = [
        ("loans", "0002_memberloan_receipt_number"),
    ]

    operations = [
        migrations.AddField(
            model_name="loanrepayment",
            name="outstanding_after",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Loan outstanding balance immediately after this repayment was posted.",
                max_digits=14,
                null=True,
            ),
        ),
        migrations.RunPython(backfill_outstanding_after, migrations.RunPython.noop),
        migrations.AlterField(
            model_name="loanrepayment",
            name="outstanding_after",
            field=models.DecimalField(
                decimal_places=2,
                help_text="Loan outstanding balance immediately after this repayment was posted.",
                max_digits=14,
            ),
        ),
    ]
