from django.contrib import admin
from django.utils.html import format_html

from .models import HelpVideo
from .services import youtube_embed_url, youtube_thumbnail_url


@admin.register(HelpVideo)
class HelpVideoAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "category",
        "is_published",
        "sort_order",
        "thumbnail_preview",
        "updated_at",
    )
    list_filter = ("category", "is_published")
    list_editable = ("is_published", "sort_order")
    search_fields = ("title", "description", "youtube_url", "youtube_video_id")
    readonly_fields = ("youtube_video_id", "slug", "embed_preview", "created_at", "updated_at")
    fieldsets = (
        (
            "Video",
            {
                "fields": (
                    "title",
                    "description",
                    "youtube_url",
                    "youtube_video_id",
                    "category",
                    "sort_order",
                    "is_published",
                ),
            },
        ),
        (
            "Preview",
            {
                "fields": ("slug", "embed_preview", "created_at", "updated_at"),
                "classes": ("collapse",),
            },
        ),
    )

    def thumbnail_preview(self, obj):
        if not obj.youtube_video_id:
            return "—"
        return format_html(
            '<img src="{}" alt="" style="height:40px;border-radius:4px;" />',
            youtube_thumbnail_url(obj.youtube_video_id),
        )

    thumbnail_preview.short_description = "Thumb"

    def embed_preview(self, obj):
        if not obj.youtube_video_id:
            return "—"
        return format_html(
            '<iframe width="320" height="180" src="{}" frameborder="0" '
            'allow="accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; '
            'picture-in-picture" allowfullscreen></iframe>',
            youtube_embed_url(obj.youtube_video_id),
        )

    embed_preview.short_description = "Embed preview"
