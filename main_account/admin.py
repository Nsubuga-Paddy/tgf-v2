from django.contrib import admin, messages

from .models import (
    AdminMainAccountCredit,
    MainAccountTransaction,
    MainAccountWithdrawal,
    ProjectTransferRequest,
    ProjectTransferToMainAccount,
)
from .services import (
    approve_withdrawal,
    credit_member,
    post_transaction,
    reject_withdrawal,
    reverse_withdrawal,
)


@admin.register(AdminMainAccountCredit)
class AdminMainAccountCreditAdmin(admin.ModelAdmin):
    """Dedicated admin screen: credit ONE member's main account balance."""

    list_display = (
        "created_at",
        "user_profile",
        "amount",
        "balance_after",
        "source_label",
        "reference",
        "created_by",
    )
    list_filter = ("created_at",)
    search_fields = (
        "user_profile__account_number",
        "user_profile__user__username",
        "user_profile__user__first_name",
        "user_profile__user__last_name",
        "reference",
        "source_label",
        "description",
    )
    autocomplete_fields = ("user_profile",)
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")

    add_fieldsets = (
        (
            "Credit a member's main account",
            {
                "fields": ("user_profile", "amount", "source_label", "description"),
                "description": (
                    "Enter the amount to credit. This posts an Admin credit ledger entry "
                    "and immediately increases the member's main account available balance "
                    "(visible on their React / Django dashboard)."
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(
                direction=MainAccountTransaction.Direction.CREDIT,
                category=MainAccountTransaction.Category.ADMIN_CREDIT,
            )
            .select_related("user_profile", "user_profile__user", "created_by")
        )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return (
            (
                "Admin credit (read-only)",
                {
                    "fields": (
                        "user_profile",
                        "amount",
                        "balance_after",
                        "reference",
                        "source_label",
                        "description",
                        "created_by",
                        "created_at",
                    )
                },
            ),
        )

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return [f.name for f in self.model._meta.fields]
        return ()

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        if change:
            return
        try:
            tx = credit_member(
                obj.user_profile,
                obj.amount,
                source_label=obj.source_label or "Admin credit",
                description=obj.description or "",
                created_by=request.user,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return
        obj.pk = tx.pk
        obj.direction = tx.direction
        obj.category = tx.category
        obj.amount = tx.amount
        obj.balance_after = tx.balance_after
        obj.reference = tx.reference
        obj.created_by = request.user
        messages.success(
            request,
            f"Credited UGX {tx.amount:,.0f} to {obj.user_profile}. "
            f"New main account balance: UGX {tx.balance_after:,.0f}.",
        )


@admin.register(MainAccountTransaction)
class MainAccountTransactionAdmin(admin.ModelAdmin):
    """Append-only ledger. Prefer 'Credit member main account' for simple credits."""

    list_display = (
        "created_at",
        "user_profile",
        "direction",
        "category",
        "amount",
        "balance_after",
        "reference",
        "created_by",
    )
    list_filter = ("direction", "category", "created_at")
    search_fields = (
        "user_profile__account_number",
        "user_profile__user__username",
        "user_profile__user__first_name",
        "user_profile__user__last_name",
        "reference",
        "source_label",
    )
    autocomplete_fields = ("user_profile",)
    date_hierarchy = "created_at"

    add_fieldsets = (
        (
            "Credit / debit a member's main account",
            {
                "fields": ("user_profile", "direction", "category", "amount", "source_label", "description"),
                "description": (
                    "Post a single ledger entry for ONE member. For a normal staff credit, "
                    "use Main Account → Credit member main account instead."
                ),
            },
        ),
    )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return (
            (
                "Ledger entry (read-only)",
                {
                    "fields": (
                        "user_profile",
                        "direction",
                        "category",
                        "amount",
                        "balance_after",
                        "reference",
                        "source_label",
                        "description",
                        "created_by",
                        "created_at",
                    )
                },
            ),
        )

    def get_readonly_fields(self, request, obj=None):
        if obj is not None:
            return [f.name for f in self.model._meta.fields]
        return ("balance_after", "reference", "created_by")

    def get_changeform_initial_data(self, request):
        return {
            "direction": MainAccountTransaction.Direction.CREDIT,
            "category": MainAccountTransaction.Category.ADMIN_CREDIT,
        }

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def save_model(self, request, obj, form, change):
        if change:
            return  # immutable
        try:
            if (
                obj.direction == MainAccountTransaction.Direction.CREDIT
                and obj.category == MainAccountTransaction.Category.ADMIN_CREDIT
            ):
                tx = credit_member(
                    obj.user_profile,
                    obj.amount,
                    source_label=obj.source_label or "Admin credit",
                    description=obj.description or "",
                    created_by=request.user,
                )
            else:
                tx = post_transaction(
                    obj.user_profile,
                    direction=obj.direction,
                    category=obj.category,
                    amount=obj.amount,
                    source_label=obj.source_label,
                    description=obj.description,
                    created_by=request.user,
                )
        except ValueError as exc:
            messages.error(request, str(exc))
            return
        obj.pk = tx.pk
        obj.balance_after = tx.balance_after
        obj.reference = tx.reference
        obj.created_by = request.user
        messages.success(
            request,
            f"Posted {obj.get_direction_display()} of UGX {tx.amount:,.0f} to "
            f"{obj.user_profile}. New balance: UGX {tx.balance_after:,.0f}.",
        )


@admin.register(MainAccountWithdrawal)
class MainAccountWithdrawalAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "member_full_name",
        "account_number_display",
        "amount_display",
        "payout_method",
        "phone_display",
        "bank_summary",
        "funding_sources_preview",
        "status",
        "processed_by",
        "processed_at",
    )
    list_filter = ("status", "payout_method", "created_at")
    search_fields = (
        "user_profile__account_number",
        "user_profile__user__username",
        "user_profile__user__first_name",
        "user_profile__user__last_name",
        "user_profile__whatsapp_number",
        "user_profile__bank_account_number",
        "user_profile__bank_account_name",
        "payout_destination",
        "funding_note",
        "reason",
    )
    autocomplete_fields = ("user_profile",)
    date_hierarchy = "created_at"
    readonly_fields = (
        "member_full_name",
        "account_number_display",
        "phone_display",
        "bank_details_display",
        "payout_destination",
        "funding_note_display",
        "transaction",
        "reversal_transaction",
        "processed_by",
        "processed_at",
        "reversed_by",
        "reversed_at",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Member & payout details",
            {
                "fields": (
                    "member_full_name",
                    "account_number_display",
                    "phone_display",
                    "bank_details_display",
                    "payout_method",
                    "payout_destination",
                ),
                "description": (
                    "Use these details to send the payout. Phone and bank come from the "
                    "member profile; payout destination is the snapshot chosen at request time."
                ),
            },
        ),
        (
            "Where Main Account funds came from",
            {
                "fields": ("funding_note_display",),
                "description": (
                    "Context only — Main Account is a pooled balance. This note shows "
                    "project/dividend credits that funded this member's Main Account."
                ),
            },
        ),
        (
            "Request",
            {
                "fields": (
                    "user_profile",
                    "amount",
                    "reason",
                    "status",
                ),
                "description": (
                    "Use the admin actions to approve, reject, or reverse. "
                    "Approval posts a debit; reversal posts an equal credit adjustment."
                ),
            },
        ),
        (
            "Admin decision",
            {
                "fields": (
                    "admin_notes",
                    "processed_by",
                    "processed_at",
                    "transaction",
                    "reversal_transaction",
                    "reversed_by",
                    "reversed_at",
                ),
                "description": "Notes for the payment team (e.g. MoMo/bank reference).",
            },
        ),
        (
            "Timestamps",
            {
                "fields": ("created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )
    actions = (
        "action_approve",
        "action_reject",
        "action_reverse",
        "action_refresh_funding_notes",
    )

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .select_related("user_profile", "user_profile__user", "processed_by")
        )

    @admin.display(description="Full name", ordering="user_profile__user__first_name")
    def member_full_name(self, obj):
        return obj.user_profile.display_name

    @admin.display(description="Account #", ordering="user_profile__account_number")
    def account_number_display(self, obj):
        return obj.user_profile.account_number or "—"

    @admin.display(description="Phone / WhatsApp")
    def phone_display(self, obj):
        number = getattr(obj.user_profile, "whatsapp_number", None)
        return str(number) if number else "—"

    @admin.display(description="Bank")
    def bank_summary(self, obj):
        profile = obj.user_profile
        bank = (profile.bank_name or "").strip()
        acct = (profile.bank_account_number or "").strip()
        if not (bank or acct):
            return "—"
        return f"{bank} · {acct}".strip(" ·")

    @admin.display(description="Bank details")
    def bank_details_display(self, obj):
        from django.utils.html import format_html

        profile = obj.user_profile
        bank = (profile.bank_name or "").strip()
        acct = (profile.bank_account_number or "").strip()
        name = (profile.bank_account_name or "").strip()
        if not (bank and acct and name):
            return "Not provided on profile"
        return format_html(
            "{}<br>Account: {}<br>Name: {}",
            bank,
            acct,
            name,
        )

    @admin.display(description="Funding sources")
    def funding_sources_preview(self, obj):
        note = (obj.funding_note or "").strip()
        if not note:
            return "—"
        # Prefer the totals section if present
        for line in note.splitlines():
            if line.startswith("- ") and ":" in line and "UGX" in line:
                return line[2:60] + ("…" if len(line) > 62 else "")
        return note[:60] + ("…" if len(note) > 60 else "")

    @admin.display(description="Funding from projects / credits")
    def funding_note_display(self, obj):
        from django.utils.html import format_html

        note = (obj.funding_note or "").strip()
        if not note:
            from .services import build_funding_note

            note = build_funding_note(obj.user_profile)
        return format_html(
            '<pre style="white-space:pre-wrap;font-family:inherit;margin:0;">{}</pre>',
            note,
        )

    @admin.display(description="Amount", ordering="amount")
    def amount_display(self, obj):
        return f"UGX {obj.amount:,.0f}"

    @admin.display(description="Reason")
    def reason_preview(self, obj):
        if not obj.reason:
            return "—"
        return obj.reason[:50] + ("…" if len(obj.reason) > 50 else "")

    @admin.display(description="Reversal ref")
    def reversal_reference(self, obj):
        if obj.reversal_transaction_id:
            return obj.reversal_transaction.reference
        return "—"

    def save_model(self, request, obj, form, change):
        if not change or not obj.pk:
            return super().save_model(request, obj, form, change)

        previous = MainAccountWithdrawal.objects.select_related("user_profile").get(pk=obj.pk)
        if previous.status == obj.status:
            return super().save_model(request, obj, form, change)

        if previous.status != MainAccountWithdrawal.STATUS_PENDING:
            self.message_user(
                request,
                "Only pending withdrawals can change status manually. "
                "Use the 'Reverse approved withdrawals' action for approved requests.",
                level=messages.ERROR,
            )
            return

        notes = (obj.admin_notes or "").strip()
        try:
            if obj.status == MainAccountWithdrawal.STATUS_APPROVED:
                approve_withdrawal(previous, admin=request.user, admin_notes=notes)
                self.message_user(
                    request,
                    "Withdrawal approved and ledger debit posted.",
                    level=messages.SUCCESS,
                )
            elif obj.status == MainAccountWithdrawal.STATUS_REJECTED:
                reject_withdrawal(previous, admin=request.user, admin_notes=notes)
                self.message_user(request, "Withdrawal rejected.", level=messages.SUCCESS)
            else:
                return super().save_model(request, obj, form, change)
        except ValueError as exc:
            self.message_user(request, str(exc), level=messages.ERROR)

    @admin.action(description="Refresh funding notes from Main Account credits")
    def action_refresh_funding_notes(self, request, queryset):
        from .services import build_funding_note

        done = 0
        for wd in queryset.select_related("user_profile"):
            wd.funding_note = build_funding_note(wd.user_profile)
            wd.save(update_fields=["funding_note", "updated_at"])
            done += 1
        if done:
            self.message_user(
                request,
                f"Updated funding notes on {done} withdrawal request(s).",
                level=messages.SUCCESS,
            )

    @admin.action(description="Approve selected withdrawals (posts debit to ledger)")
    def action_approve(self, request, queryset):
        done = 0
        for wd in queryset.filter(status=MainAccountWithdrawal.STATUS_PENDING):
            try:
                approve_withdrawal(wd, admin=request.user)
                done += 1
            except ValueError as exc:
                self.message_user(request, f"{wd.user_profile}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(request, f"Approved {done} withdrawal(s).", level=messages.SUCCESS)

    @admin.action(description="Reject selected withdrawals")
    def action_reject(self, request, queryset):
        done = 0
        for wd in queryset.filter(status=MainAccountWithdrawal.STATUS_PENDING):
            reject_withdrawal(wd, admin=request.user)
            done += 1
        if done:
            self.message_user(request, f"Rejected {done} withdrawal(s).", level=messages.SUCCESS)

    @admin.action(description="Reverse approved withdrawals (posts credit adjustment)")
    def action_reverse(self, request, queryset):
        done = 0
        for wd in queryset.filter(status=MainAccountWithdrawal.STATUS_APPROVED):
            try:
                reverse_withdrawal(
                    wd,
                    admin=request.user,
                    admin_notes=wd.admin_notes or "Reversed by Administrator",
                )
                done += 1
            except ValueError as exc:
                self.message_user(request, f"{wd.user_profile}: {exc}", level=messages.ERROR)
        if done:
            self.message_user(
                request,
                f"Reversed {done} approved withdrawal(s) and posted credit adjustment(s).",
                level=messages.SUCCESS,
            )


@admin.register(ProjectTransferToMainAccount)
class ProjectTransferToMainAccountAdmin(admin.ModelAdmin):
    """
    Audit view of completed matured-project credits into Main Account.

    No approval workflow — members transfer from matured 52WSC / CGF (etc.)
    themselves. Refund requests remain under Real Estate admin.
    """

    list_display = (
        "created_at",
        "user_profile",
        "source_label",
        "amount_display",
        "balance_after",
        "reference",
        "description_preview",
        "created_by",
    )
    list_filter = ("source_label", "created_at")
    search_fields = (
        "user_profile__account_number",
        "user_profile__user__username",
        "user_profile__user__first_name",
        "user_profile__user__last_name",
        "source_label",
        "reference",
        "description",
    )
    date_hierarchy = "created_at"
    ordering = ("-created_at", "-id")

    def get_queryset(self, request):
        return (
            super()
            .get_queryset(request)
            .filter(
                direction=MainAccountTransaction.Direction.CREDIT,
                category=MainAccountTransaction.Category.PROJECT_TRANSFER_IN,
            )
            .select_related("user_profile", "user_profile__user", "created_by")
        )

    def get_readonly_fields(self, request, obj=None):
        return [f.name for f in self.model._meta.fields]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True  # allow opening detail (read-only fields)

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = "Project transfers to main account (completed)"
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Amount", ordering="amount")
    def amount_display(self, obj):
        return f"UGX {obj.amount:,.0f}"

    @admin.display(description="Description")
    def description_preview(self, obj):
        text = (obj.description or "").strip()
        if not text:
            return "—"
        return text[:70] + ("…" if len(text) > 70 else "")


@admin.register(ProjectTransferRequest)
class ProjectTransferRequestAdmin(admin.ModelAdmin):
    """Legacy approval queue — retained for history only."""

    list_display = (
        "created_at",
        "user_profile",
        "project_label",
        "amount",
        "status",
        "processed_by",
    )
    list_filter = ("status", "project_label", "created_at")
    search_fields = (
        "user_profile__account_number",
        "user_profile__user__username",
        "user_profile__user__first_name",
        "user_profile__user__last_name",
        "project_label",
    )
    autocomplete_fields = ("user_profile",)
    readonly_fields = (
        "user_profile",
        "project_label",
        "amount",
        "member_notes",
        "status",
        "admin_notes",
        "transaction",
        "processed_by",
        "processed_at",
        "created_at",
        "updated_at",
    )

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return True

    def has_delete_permission(self, request, obj=None):
        return request.user.is_superuser

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        extra_context["title"] = (
            "Legacy project transfer requests (historical). "
            "New matured transfers post instantly — see "
            "'Project transfers to main account'."
        )
        return super().changelist_view(request, extra_context=extra_context)
