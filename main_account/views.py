import csv

from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.utils import timezone

from .models import MainAccountTransaction


@login_required
def history_csv(request):
    """Download the member's main account statement as CSV."""
    profile = getattr(request.user, "profile", None)
    response = HttpResponse(content_type="text/csv")
    stamp = timezone.now().strftime("%Y%m%d")
    acct = getattr(profile, "account_number", "account") or "account"
    response["Content-Disposition"] = f'attachment; filename="main-account-{acct}-{stamp}.csv"'

    writer = csv.writer(response)
    writer.writerow(["Date", "Reference", "Category", "Direction", "Amount (UGX)", "Balance after (UGX)", "Source", "Description"])
    if profile is not None:
        txns = MainAccountTransaction.objects.filter(user_profile=profile).order_by("created_at", "id")
        for t in txns:
            writer.writerow([
                timezone.localtime(t.created_at).strftime("%Y-%m-%d %H:%M"),
                t.reference,
                t.get_category_display(),
                t.get_direction_display(),
                f"{t.signed_amount:.2f}",
                f"{t.balance_after:.2f}",
                t.source_label,
                t.description.replace("\n", " ").strip(),
            ])
    return response
