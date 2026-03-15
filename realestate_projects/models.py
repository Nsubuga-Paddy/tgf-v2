from django.conf import settings
from django.db import models


class RealEstateProject(models.Model):
    STATUS_RUNNING = "running"
    STATUS_CLOSED = "closed"
    STATUS_UPCOMING = "upcoming"

    STATUS_CHOICES = [
        (STATUS_RUNNING, "Running"),
        (STATUS_CLOSED, "Closed"),
        (STATUS_UPCOMING, "Upcoming"),
    ]

    name = models.CharField(max_length=255)
    location = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    land_size = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Size of land being acquired (numeric value).",
    )
    land_size_unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Unit for land size, e.g. acres, hectares.",
    )
    vendor_total_amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total money required by the vendor.",
    )
    operational_costs = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Operational/overhead costs for this project.",
    )
    start_date = models.DateField()
    end_date = models.DateField()
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_UPCOMING
    )
    minimum_investment = models.CharField(
        max_length=120,
        blank=True,
        help_text="Optional label like 'From UGX 5,000,000'",
    )
    allowed_members = models.ManyToManyField(
        settings.AUTH_USER_MODEL,
        related_name="realestate_projects",
        blank=True,
        help_text=(
            "Users who can view full details and participate in this project. "
            "Other users will only see a limited summary."
        ),
    )
    show_in_sidebar = models.BooleanField(
        default=True,
        help_text="When checked and status is Running, this project will appear in the sidebar list.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-start_date", "name"]

    def __str__(self) -> str:
        return self.name


class RealEstateProjectTransaction(models.Model):
    TYPE_PAYMENT = "payment"
    TYPE_REFUND = "refund"
    TYPE_ADJUSTMENT = "adjustment"

    TYPE_CHOICES = [
        (TYPE_PAYMENT, "Payment"),
        (TYPE_REFUND, "Refund"),
        (TYPE_ADJUSTMENT, "Adjustment"),
    ]

    project = models.ForeignKey(
        RealEstateProject,
        related_name="transactions",
        on_delete=models.CASCADE,
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="realestate_transactions",
        on_delete=models.CASCADE,
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
    )
    acquisition_quantity = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Number of plots/acres covered by this transaction.",
    )
    acquisition_unit = models.CharField(
        max_length=50,
        blank=True,
        help_text="Unit for acquisition, e.g. plots, acres.",
    )
    balance_after = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Member's remaining balance after this transaction.",
    )
    PAYMENT_STATUS_PARTIAL = "partial"
    PAYMENT_STATUS_FULL = "full"
    PAYMENT_STATUS_CHOICES = [
        (PAYMENT_STATUS_PARTIAL, "Partially paid"),
        (PAYMENT_STATUS_FULL, "Fully paid"),
    ]
    payment_status = models.CharField(
        max_length=20,
        choices=PAYMENT_STATUS_CHOICES,
        default=PAYMENT_STATUS_PARTIAL,
        help_text="Whether this transaction leaves the member partially or fully paid.",
    )
    type = models.CharField(
        max_length=20,
        choices=TYPE_CHOICES,
        default=TYPE_PAYMENT,
    )
    note = models.TextField(blank=True)
    transaction_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date when this transaction was made.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.type} {self.amount} for {self.user} in {self.project}"


class RealEstateProjectJoinRequest(models.Model):
    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_CANCELLED = "cancelled"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    project = models.ForeignKey(
        RealEstateProject, related_name="join_requests", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="realestate_join_requests",
        on_delete=models.CASCADE,
    )
    status = models.CharField(
        max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING
    )
    message = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    decided_at = models.DateTimeField(null=True, blank=True)
    decided_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="realestate_join_decisions",
    )

    class Meta:
        unique_together = ("project", "user")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} → {self.project} ({self.status})"


class RealEstateProjectInterest(models.Model):
    project = models.ForeignKey(
        RealEstateProject, related_name="interests", on_delete=models.CASCADE
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="realestate_interests",
        on_delete=models.CASCADE,
    )
    note = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("project", "user")
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Interest: {self.user} → {self.project}"


class RealEstateProjectActionRequest(models.Model):
    ACTION_WITHDRAW = "withdraw"
    ACTION_TRANSFER_GWC = "transfer_gwc"
    ACTION_TRANSFER_NAMAYUMBA = "transfer_namayumba"

    ACTION_CHOICES = [
        (ACTION_WITHDRAW, "Withdraw cash"),
        (ACTION_TRANSFER_GWC, "Transfer to GWC"),
        (ACTION_TRANSFER_NAMAYUMBA, "Transfer to Namayumba estate"),
    ]

    STATUS_PENDING = "pending"
    STATUS_APPROVED = "approved"
    STATUS_REJECTED = "rejected"
    STATUS_PROCESSED = "processed"

    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_APPROVED, "Approved"),
        (STATUS_REJECTED, "Rejected"),
        (STATUS_PROCESSED, "Processed"),
    ]

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        related_name="realestate_action_requests",
        on_delete=models.CASCADE,
    )
    project = models.ForeignKey(
        RealEstateProject,
        related_name="action_requests",
        on_delete=models.CASCADE,
    )
    action_type = models.CharField(
        max_length=32,
        choices=ACTION_CHOICES,
    )
    amount = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Amount the user is requesting to withdraw or transfer.",
    )
    available_at_request = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Available amount at the time of request (for audit).",
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    reason = models.TextField(
        blank=True,
        help_text="Optional note from the user describing this action.",
    )
    admin_notes = models.TextField(
        blank=True,
        help_text="Internal admin notes about how the request was handled.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    processed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.user} → {self.project} ({self.get_action_type_display()})"
