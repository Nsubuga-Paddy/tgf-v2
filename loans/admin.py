from django import forms
from django.contrib import admin, messages
from django.utils.html import format_html, format_html_join
from django.utils.safestring import mark_safe

from .models import LoanApplication, LoanInstallment, LoanRepayment, MemberLoan
from .services import (
    add_months,
    approve_and_disburse,
    approval_blockers,
    calculate_eligibility,
    create_installment_schedule,
    generate_reference,
    monthly_installment,
    q,
    q_rate,
    record_bank_repayment,
    reject_application,
)


class LoanInstallmentInline(admin.TabularInline):
    model = LoanInstallment
    extra = 0
    can_delete = False
    fields = (
        "installment_number",
        "due_date",
        "principal_amount",
        "interest_amount",
        "total_amount",
        "balance_after",
        "status",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class LoanRepaymentInline(admin.TabularInline):
    model = LoanRepayment
    extra = 0
    can_delete = False
    fields = (
        "posted_at",
        "amount",
        "method",
        "reference",
        "external_reference",
        "posted_by",
    )
    readonly_fields = fields

    def has_add_permission(self, request, obj=None):
        return False


class MemberLoanAdminForm(forms.ModelForm):
    class Meta:
        model = MemberLoan
        fields = "__all__"

    def clean_principal(self):
        principal = q(self.cleaned_data.get("principal"))
        if principal <= 0:
            raise forms.ValidationError("Original principal must be greater than zero.")
        return principal

    def clean_monthly_interest_rate(self):
        rate = q_rate(self.cleaned_data.get("monthly_interest_rate"))
        if rate < 0:
            raise forms.ValidationError("Interest rate cannot be negative.")
        return rate

    def clean_term_months(self):
        term = int(self.cleaned_data.get("term_months") or 0)
        if term <= 0:
            raise forms.ValidationError("Repayment period must be greater than zero months.")
        return term


@admin.register(LoanApplication)
class LoanApplicationAdmin(admin.ModelAdmin):
    change_list_template = "admin/loans/loanapplication/change_list.html"
    change_form_template = "admin/loans/loanapplication/change_form.html"
    list_display = (
        "reference",
        "member_name",
        "applicant_type_flag",
        "pending_flag",
        "amount_requested_display",
        "approved_amount_display",
        "term_months",
        "status",
        "submitted_at",
        "decided_by",
    )
    list_filter = ("status", "purpose", "repayment_source", "submitted_at", "user_profile__is_mcs_staff")
    search_fields = (
        "reference",
        "user_profile__account_number",
        "user_profile__user__username",
        "user_profile__user__first_name",
        "user_profile__user__last_name",
    )
    autocomplete_fields = ("user_profile", "decided_by")
    readonly_fields = (
        "reference",
        "eligibility_checklist",
        "submitted_at",
        "reviewed_at",
        "disbursed_at",
        "decided_by",
        "created_at",
        "updated_at",
    )
    fieldsets = (
        (
            "Application",
            {
                "fields": (
                    "user_profile",
                    "reference",
                    "purpose",
                    "amount_requested",
                    "term_months",
                    "repayment_source",
                    "notes",
                    "status",
                )
            },
        ),
        (
            "Eligibility factor checklist",
            {
                "fields": ("eligibility_checklist",),
                "description": (
                    "Live checklist for the applicant. Shareholding and project "
                    "participation/savings are committee review factors for both members and staff."
                ),
            },
        ),
        (
            "Approval and disbursement",
            {
                "fields": (
                    "approved_amount",
                    "approved_term_months",
                    "monthly_interest_rate",
                    "committee_note",
                    "rejection_reason",
                    "decided_by",
                    "reviewed_at",
                    "disbursed_at",
                ),
                "description": (
                    "Set approval terms (staff default 1%, members 1.5%), then click "
                    "'Save, approve and disburse to Main Account' beside Save. "
                    "That one button saves the form, creates the member loan, and "
                    "credits the member's Main Account."
                ),
            },
        ),
        (
            "Timestamps",
            {"fields": ("submitted_at", "created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )
    actions = ("action_approve_and_disburse", "action_mark_under_review", "action_reject")

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user_profile", "user_profile__user", "decided_by")

    def changeform_view(self, request, object_id=None, form_url="", extra_context=None):
        extra_context = extra_context or {}
        obj = self.get_object(request, object_id) if object_id else None
        extra_context["show_approve_and_disburse"] = bool(
            obj
            and obj.status
            not in {
                LoanApplication.Status.DISBURSED,
                LoanApplication.Status.REJECTED,
            }
        )
        return super().changeform_view(request, object_id, form_url, extra_context)

    def save_model(self, request, obj, form, change):
        if change and obj.status == LoanApplication.Status.REJECTED:
            previous = self.model.objects.filter(pk=obj.pk).only("status").first()
            if previous and previous.status != LoanApplication.Status.REJECTED:
                if previous.status == LoanApplication.Status.DISBURSED:
                    self.message_user(
                        request,
                        "Disbursed applications cannot be rejected.",
                        messages.ERROR,
                    )
                    return
                reject_application(obj, admin=request.user, reason=obj.rejection_reason)
                self.message_user(
                    request,
                    f"Rejected {obj.reference} and notified the member.",
                    messages.SUCCESS,
                )
                return
        super().save_model(request, obj, form, change)

    def _approve_and_disburse_application(self, request, application) -> bool:
        blockers = approval_blockers(application)
        if blockers:
            self.message_user(
                request,
                format_html(
                    "Cannot approve and disburse {}:<ul>{}</ul>",
                    application.reference,
                    format_html_join("", "<li>{}</li>", ((blocker,) for blocker in blockers)),
                ),
                messages.ERROR,
            )
            return False
        try:
            loan = approve_and_disburse(
                application,
                admin=request.user,
                note=application.committee_note or "",
            )
        except ValueError as exc:
            self.message_user(
                request,
                f"{application.reference}: {exc}",
                messages.ERROR,
            )
            return False
        self.message_user(
            request,
            (
                f"Saved, approved and disbursed {application.reference}. "
                f"Member loan {loan.reference} credited UGX {loan.principal:,.0f} to Main Account."
            ),
            messages.SUCCESS,
        )
        return True

    def response_change(self, request, obj):
        if "_approve_and_disburse" in request.POST:
            self._approve_and_disburse_application(request, obj)
        return super().response_change(request, obj)

    def response_add(self, request, obj, post_url_continue=None):
        if "_approve_and_disburse" in request.POST:
            self._approve_and_disburse_application(request, obj)
        return super().response_add(request, obj, post_url_continue)

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        pending_count = self.model.objects.filter(status=LoanApplication.Status.SUBMITTED).count()
        extra_context["pending_applications_count"] = pending_count
        return super().changelist_view(request, extra_context=extra_context)

    @admin.display(description="Member", ordering="user_profile__user__first_name")
    def member_name(self, obj):
        return obj.user_profile.display_name

    @admin.display(description="Type", ordering="user_profile__is_mcs_staff")
    def applicant_type_flag(self, obj):
        if obj.user_profile.is_mcs_staff:
            return format_html(
                '<span style="display:inline-block;padding:3px 8px;border-radius:999px;'
                'background:#ecfdf5;color:#065f46;font-weight:700;font-size:11px;">Staff · 1%</span>'
            )
        return format_html(
            '<span style="display:inline-block;padding:3px 8px;border-radius:999px;'
            'background:#eff6ff;color:#1e40af;font-weight:700;font-size:11px;">Member · 1.5%</span>'
        )

    @admin.display(description="Flag", ordering="status")
    def pending_flag(self, obj):
        if obj.status == LoanApplication.Status.SUBMITTED:
            return format_html(
                '<span style="display:inline-block;padding:3px 8px;border-radius:999px;'
                'background:#fff7ed;color:#9a3412;font-weight:700;font-size:11px;">Pending</span>'
            )
        return format_html('<span style="color:#9ca3af;">-</span>')

    @admin.display(description="Eligibility checklist")
    def eligibility_checklist(self, obj):
        if not obj or not obj.pk or not obj.user_profile_id:
            return "Save the application first to load the checklist."
        eligibility = calculate_eligibility(obj.user_profile)
        rows = []
        for factor in eligibility.get("factors") or []:
            met = factor.get("met")
            if met is True:
                mark = format_html('<span style="color:#166534;font-weight:700;">Met</span>')
            elif met is False:
                mark = format_html('<span style="color:#b91c1c;font-weight:700;">Not met</span>')
            else:
                mark = format_html('<span style="color:#6b7280;font-weight:700;">Review</span>')
            soft = "Committee" if factor.get("soft") else "Required"
            rows.append(
                format_html(
                    "<tr>"
                    "<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;'>{}</td>"
                    "<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;'>{}</td>"
                    "<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;'>{}</td>"
                    "<td style='padding:6px 8px;border-bottom:1px solid #e5e7eb;'>{}</td>"
                    "</tr>",
                    factor.get("label") or "",
                    soft,
                    mark,
                    factor.get("detail") or "",
                )
            )
        return format_html(
            "<div style='margin-bottom:10px;'>"
            "<strong>{}</strong> · {} · Suggested rate: {}"
            "</div>"
            "<table style='width:100%;border-collapse:collapse;font-size:13px;'>"
            "<thead><tr>"
            "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #d1d5db;'>Factor</th>"
            "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #d1d5db;'>Type</th>"
            "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #d1d5db;'>Status</th>"
            "<th style='text-align:left;padding:6px 8px;border-bottom:2px solid #d1d5db;'>Detail</th>"
            "</tr></thead>"
            "<tbody>{}</tbody></table>",
            eligibility.get("applicantType") or "Member",
            eligibility.get("statusLabel") or "",
            eligibility.get("rateDisplay") or "",
            mark_safe("".join(rows)),
        )

    @admin.display(description="Requested", ordering="amount_requested")
    def amount_requested_display(self, obj):
        return f"UGX {obj.amount_requested:,.0f}"

    @admin.display(description="Approved", ordering="approved_amount")
    def approved_amount_display(self, obj):
        return f"UGX {obj.approved_amount:,.0f}" if obj.approved_amount else "-"

    @admin.action(description="Mark selected applications under review")
    def action_mark_under_review(self, request, queryset):
        updated = queryset.filter(status=LoanApplication.Status.SUBMITTED).update(
            status=LoanApplication.Status.UNDER_REVIEW
        )
        self.message_user(request, f"Marked {updated} application(s) under review.", messages.SUCCESS)

    @admin.action(description="Approve and disburse selected applications to Main Account")
    def action_approve_and_disburse(self, request, queryset):
        done = 0
        for application in queryset.select_related("user_profile", "user_profile__user"):
            if self._approve_and_disburse_application(request, application):
                done += 1
        if done:
            self.message_user(
                request,
                f"Approved and disbursed {done} loan application(s) to Main Account.",
                messages.SUCCESS,
            )

    @admin.action(description="Reject selected applications")
    def action_reject(self, request, queryset):
        done = 0
        for application in queryset.exclude(
            status__in=[
                LoanApplication.Status.DISBURSED,
                LoanApplication.Status.REJECTED,
            ]
        ):
            try:
                reject_application(application, admin=request.user, reason=application.rejection_reason)
                done += 1
            except ValueError as exc:
                self.message_user(request, f"{application.reference}: {exc}", messages.ERROR)
        if done:
            self.message_user(request, f"Rejected {done} application(s).", messages.SUCCESS)


@admin.register(MemberLoan)
class MemberLoanAdmin(admin.ModelAdmin):
    form = MemberLoanAdminForm
    list_display = (
        "reference",
        "member_name",
        "principal_display",
        "outstanding_display",
        "term_months",
        "status",
        "disbursed_date",
        "receipt_number",
        "closed_date",
    )
    list_filter = ("status", "purpose", "disbursed_date")
    search_fields = (
        "reference",
        "receipt_number",
        "application__reference",
        "user_profile__account_number",
        "user_profile__user__username",
        "user_profile__user__first_name",
        "user_profile__user__last_name",
    )
    autocomplete_fields = ("user_profile", "application", "created_by")
    readonly_fields = (
        "reference",
        "principal",
        "insurance_fee",
        "processing_fee",
        "total_deductions",
        "net_disbursed_amount",
        "outstanding",
        "installment_amount",
        "paid_installments",
        "disbursement_transaction",
        "created_by",
        "created_at",
        "updated_at",
    )
    inlines = (LoanInstallmentInline, LoanRepaymentInline)
    add_fieldsets = (
        (
            "Register existing member loan",
            {
                "fields": (
                    "user_profile",
                    "purpose",
                    "receipt_number",
                    "principal",
                    "net_disbursed_amount",
                    "monthly_interest_rate",
                    "term_months",
                    "disbursed_date",
                    "status",
                ),
                "description": (
                    "Use this form for loans that were already issued before the system. "
                    "The system will calculate the first due date, installment amount, "
                    "total outstanding balance, and repayment schedule. No Main Account "
                    "credit will be posted."
                ),
            },
        ),
    )
    change_fieldsets = (
        (
            "Loan",
            {
                "fields": (
                    "user_profile",
                    "application",
                    "reference",
                    "purpose",
                    "receipt_number",
                    "principal",
                    "insurance_fee",
                    "processing_fee",
                    "total_deductions",
                    "net_disbursed_amount",
                    "outstanding",
                    "monthly_interest_rate",
                    "term_months",
                    "installment_amount",
                    "paid_installments",
                    "status",
                    "disbursed_date",
                    "first_due_date",
                    "closed_date",
                    "disbursement_transaction",
                    "created_by",
                )
            },
        ),
        (
            "Timestamps",
            {"fields": ("created_at", "updated_at"), "classes": ("collapse",)},
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related("user_profile", "user_profile__user", "application")

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return self.change_fieldsets

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return (
                "reference",
                "insurance_fee",
                "processing_fee",
                "total_deductions",
                "outstanding",
                "installment_amount",
                "paid_installments",
                "first_due_date",
                "created_by",
                "created_at",
                "updated_at",
            )
        return self.readonly_fields

    @admin.display(description="Member", ordering="user_profile__user__first_name")
    def member_name(self, obj):
        return obj.user_profile.display_name

    @admin.display(description="Principal", ordering="principal")
    def principal_display(self, obj):
        return f"UGX {obj.principal:,.0f}"

    @admin.display(description="Outstanding", ordering="outstanding")
    def outstanding_display(self, obj):
        return f"UGX {obj.outstanding:,.0f}"

    def save_model(self, request, obj, form, change):
        if change:
            super().save_model(request, obj, form, change)
            return

        principal = q(obj.principal)
        term = int(obj.term_months)
        rate = q_rate(obj.monthly_interest_rate)
        obj.reference = generate_reference("LN")
        obj.application = None
        obj.principal = principal
        obj.insurance_fee = q(getattr(obj, "insurance_fee", 0))
        obj.processing_fee = q(getattr(obj, "processing_fee", 0))
        obj.total_deductions = q(obj.insurance_fee + obj.processing_fee)
        obj.net_disbursed_amount = q(obj.net_disbursed_amount or principal)
        obj.monthly_interest_rate = rate
        obj.installment_amount = monthly_installment(principal, term, rate)
        obj.outstanding = q(principal + (principal * rate * term))
        obj.first_due_date = add_months(obj.disbursed_date, 1)
        obj.disbursement_transaction = None
        obj.created_by = request.user
        super().save_model(request, obj, form, change)
        create_installment_schedule(obj)
        messages.success(
            request,
            f"Registered existing loan {obj.reference}. Outstanding balance is UGX {obj.outstanding:,.0f}.",
        )


@admin.register(LoanRepayment)
class LoanRepaymentAdmin(admin.ModelAdmin):
    list_display = (
        "posted_at",
        "loan",
        "member_name",
        "amount_display",
        "outstanding_after_display",
        "method",
        "reference",
        "external_reference",
        "posted_by",
    )
    list_filter = ("method", "posted_at")
    search_fields = (
        "reference",
        "external_reference",
        "loan__reference",
        "loan__user_profile__account_number",
        "loan__user_profile__user__username",
        "loan__user_profile__user__first_name",
        "loan__user_profile__user__last_name",
    )
    autocomplete_fields = ("loan", "posted_by")
    add_fieldsets = (
        (
            "Record bank transfer repayment",
            {
                "fields": ("loan", "amount", "external_reference", "receipt", "notes"),
                "description": (
                    "Use this form only after the member shares a bank receipt and staff "
                    "verify the funds in the MCS bank account."
                ),
            },
        ),
    )

    def get_queryset(self, request):
        return super().get_queryset(request).select_related(
            "loan",
            "loan__user_profile",
            "loan__user_profile__user",
            "posted_by",
        )

    def get_fieldsets(self, request, obj=None):
        if obj is None:
            return self.add_fieldsets
        return (
            (
                "Repayment",
                {
                    "fields": (
                        "loan",
                        "amount",
                        "outstanding_after_display",
                        "method",
                        "reference",
                        "external_reference",
                        "receipt",
                        "notes",
                        "main_account_transaction",
                        "posted_by",
                        "posted_at",
                    )
                },
            ),
        )

    def get_readonly_fields(self, request, obj=None):
        if obj is None:
            return ()
        return [field.name for field in self.model._meta.fields] + ["outstanding_after_display"]

    @admin.display(description="Member", ordering="loan__user_profile__user__first_name")
    def member_name(self, obj):
        return obj.loan.user_profile.display_name

    @admin.display(description="Amount", ordering="amount")
    def amount_display(self, obj):
        return f"UGX {obj.amount:,.0f}"

    @admin.display(description="Outstanding after payment", ordering="outstanding_after")
    def outstanding_after_display(self, obj):
        if obj.outstanding_after is None:
            return "-"
        return f"UGX {obj.outstanding_after:,.0f}"

    def save_model(self, request, obj, form, change):
        if change:
            return
        try:
            repayment = record_bank_repayment(
                obj.loan,
                obj.amount,
                external_reference=obj.external_reference,
                receipt=obj.receipt,
                notes=obj.notes,
                posted_by=request.user,
            )
        except ValueError as exc:
            messages.error(request, str(exc))
            return
        obj.pk = repayment.pk
        obj.method = repayment.method
        obj.reference = repayment.reference
        obj.posted_by = request.user
        obj.posted_at = repayment.posted_at
        messages.success(
            request,
            f"Posted bank repayment of UGX {repayment.amount:,.0f} to {repayment.loan.reference}.",
        )
