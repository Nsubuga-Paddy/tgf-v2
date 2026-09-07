from __future__ import annotations

from decimal import Decimal

from django.conf import settings
from django.db import models
from django.utils import timezone


MAX_BORROWING_LIMIT = Decimal("10000000.00")
MIN_BORROWING_AMOUNT = Decimal("100000.00")
DEFAULT_MONTHLY_INTEREST_RATE = Decimal("0.015")
STAFF_MONTHLY_INTEREST_RATE = Decimal("0.010")
LOAN_INSURANCE_FEE_RATE = Decimal("0.010")
LOAN_PROCESSING_FEE = Decimal("20000.00")


class LoanApplication(models.Model):
    class Status(models.TextChoices):
        SUBMITTED = "submitted", "Submitted"
        UNDER_REVIEW = "under_review", "Under review"
        APPROVED = "approved", "Approved"
        REJECTED = "rejected", "Rejected"
        DISBURSED = "disbursed", "Disbursed"

    class Purpose(models.TextChoices):
        BUSINESS = "business", "Business expansion"
        EDUCATION = "education", "Education"
        MEDICAL = "medical", "Medical / emergency"
        HOUSING = "housing", "Housing"
        AGRICULTURE = "agriculture", "Agriculture"
        OTHER = "other", "Other"

    class RepaymentSource(models.TextChoices):
        MAIN_ACCOUNT = "main_account", "Main Account"
        MAIN_ACCOUNT_AND_SALARY = "main_account_and_salary", "Main Account + salary"
        BUSINESS_INCOME = "business_income", "Business income"

    user_profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="loan_applications",
    )
    reference = models.CharField(max_length=40, unique=True, db_index=True)
    purpose = models.CharField(max_length=30, choices=Purpose.choices)
    amount_requested = models.DecimalField(max_digits=14, decimal_places=2)
    term_months = models.PositiveSmallIntegerField(default=12)
    repayment_source = models.CharField(
        max_length=40,
        choices=RepaymentSource.choices,
        default=RepaymentSource.MAIN_ACCOUNT,
    )
    notes = models.TextField(blank=True)

    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SUBMITTED,
        db_index=True,
    )
    approved_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Amount to disburse. Defaults to requested amount if left blank.",
    )
    approved_term_months = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        help_text="Term to use at disbursement. Defaults to requested term.",
    )
    monthly_interest_rate = models.DecimalField(
        max_digits=7,
        decimal_places=4,
        default=DEFAULT_MONTHLY_INTEREST_RATE,
        help_text="Monthly rate as a decimal. 0.015 = 1.5% (members), 0.01 = 1% (MCS staff).",
    )
    committee_note = models.TextField(blank=True)
    rejection_reason = models.TextField(blank=True)

    submitted_at = models.DateTimeField(default=timezone.now)
    reviewed_at = models.DateTimeField(null=True, blank=True)
    disbursed_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="decided_loan_applications",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Loan application"
        verbose_name_plural = "Loan applications"
        indexes = [
            models.Index(fields=["user_profile", "status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference} - {self.user_profile}"


class MemberLoan(models.Model):
    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        OVERDUE = "overdue", "Overdue"
        CLOSED = "closed", "Closed"
        WRITTEN_OFF = "written_off", "Written off"

    user_profile = models.ForeignKey(
        "accounts.UserProfile",
        on_delete=models.CASCADE,
        related_name="member_loans",
    )
    application = models.OneToOneField(
        LoanApplication,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loan",
    )
    reference = models.CharField(max_length=40, unique=True, db_index=True)
    purpose = models.CharField(max_length=30, choices=LoanApplication.Purpose.choices)
    receipt_number = models.CharField(
        max_length=120,
        blank=True,
        help_text="Receipt/reference number for existing loans entered manually.",
    )
    principal = models.DecimalField(max_digits=14, decimal_places=2)
    insurance_fee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    processing_fee = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    total_deductions = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    net_disbursed_amount = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("0.00"))
    outstanding = models.DecimalField(max_digits=14, decimal_places=2)
    monthly_interest_rate = models.DecimalField(max_digits=7, decimal_places=4)
    term_months = models.PositiveSmallIntegerField()
    installment_amount = models.DecimalField(max_digits=14, decimal_places=2)
    paid_installments = models.PositiveSmallIntegerField(default=0)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.ACTIVE,
        db_index=True,
    )
    disbursed_date = models.DateField(default=timezone.localdate)
    first_due_date = models.DateField()
    closed_date = models.DateField(null=True, blank=True)
    disbursement_transaction = models.OneToOneField(
        "main_account.MainAccountTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="disbursed_loan",
    )
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_member_loans",
    )
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        verbose_name = "Member loan"
        verbose_name_plural = "Member loans"
        indexes = [
            models.Index(fields=["user_profile", "status", "-created_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference} - {self.user_profile}"

    @property
    def rate_display(self) -> str:
        pct = (self.monthly_interest_rate * Decimal("100")).quantize(Decimal("0.01"))
        return f"{pct.normalize()}% per month on principal"


class LoanInstallment(models.Model):
    class Status(models.TextChoices):
        PAID = "paid", "Paid"
        DUE = "due", "Due now"
        UPCOMING = "upcoming", "Upcoming"

    loan = models.ForeignKey(
        MemberLoan,
        on_delete=models.CASCADE,
        related_name="installments",
    )
    installment_number = models.PositiveSmallIntegerField()
    due_date = models.DateField()
    principal_amount = models.DecimalField(max_digits=14, decimal_places=2)
    interest_amount = models.DecimalField(max_digits=14, decimal_places=2)
    total_amount = models.DecimalField(max_digits=14, decimal_places=2)
    balance_after = models.DecimalField(max_digits=14, decimal_places=2)
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.UPCOMING,
        db_index=True,
    )

    class Meta:
        ordering = ["installment_number"]
        unique_together = [("loan", "installment_number")]
        verbose_name = "Loan installment"
        verbose_name_plural = "Loan installments"

    def __str__(self) -> str:
        return f"{self.loan.reference} installment {self.installment_number}"


class LoanRepayment(models.Model):
    class Method(models.TextChoices):
        MAIN_ACCOUNT = "main_account", "Main Account"
        BANK_TRANSFER = "bank_transfer", "Bank transfer"

    loan = models.ForeignKey(
        MemberLoan,
        on_delete=models.CASCADE,
        related_name="repayments",
    )
    amount = models.DecimalField(max_digits=14, decimal_places=2)
    outstanding_after = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Loan outstanding balance immediately after this repayment was posted.",
    )
    method = models.CharField(max_length=30, choices=Method.choices)
    reference = models.CharField(max_length=40, unique=True, db_index=True)
    external_reference = models.CharField(
        max_length=120,
        blank=True,
        help_text="Bank receipt/reference provided by the member.",
    )
    receipt = models.FileField(upload_to="loan-receipts/%Y/%m/", blank=True, null=True)
    notes = models.TextField(blank=True)
    main_account_transaction = models.OneToOneField(
        "main_account.MainAccountTransaction",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="loan_repayment",
    )
    posted_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="posted_loan_repayments",
    )
    posted_at = models.DateTimeField(default=timezone.now)

    class Meta:
        ordering = ["-posted_at", "-id"]
        verbose_name = "Loan repayment"
        verbose_name_plural = "Loan repayments"
        indexes = [
            models.Index(fields=["loan", "-posted_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.reference} - {self.loan.reference}"
