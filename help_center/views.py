from django.db.models import Q
from django.views.generic import ListView

from .models import HelpVideo


class HelpCenterView(ListView):
    model = HelpVideo
    template_name = "help_center/guides.html"
    context_object_name = "videos"
    paginate_by = 12

    def get_queryset(self):
        qs = HelpVideo.objects.filter(is_published=True)
        category = self.request.GET.get("category", "").strip()
        if category and category in HelpVideo.Category.values:
            qs = qs.filter(category=category)
        query = self.request.GET.get("q", "").strip()
        if query:
            qs = qs.filter(
                Q(title__icontains=query) | Q(description__icontains=query)
            )
        return qs

    def get_context_data(self, **kwargs):
        queryset = self.get_queryset()
        ctx = super().get_context_data(**kwargs)
        ctx["categories"] = HelpVideo.Category.choices
        ctx["active_category"] = self.request.GET.get("category", "").strip()
        ctx["search_query"] = self.request.GET.get("q", "").strip()
        ctx["total_count"] = queryset.count()
        return ctx
