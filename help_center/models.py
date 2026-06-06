from __future__ import annotations

from django.core.exceptions import ValidationError
from django.db import models
from django.utils.text import slugify

from .services import extract_youtube_video_id, youtube_embed_url, youtube_thumbnail_url


class HelpVideo(models.Model):
    class Category(models.TextChoices):
        GENERAL = "general", "General & platform"
        PROFILE = "profile", "Profile & account"
        SAVINGS_52 = "savings_52", "52 Weeks Saving Challenge"
        FIXED_SAVINGS = "fixed_savings", "Fixed Savings"
        GWC = "gwc", "Generational Wealth (GWC)"
        CGF = "cgf", "Commercial Goat Farming"
        COOPERATIVE = "cooperative", "Cooperative Shareholding"
        REAL_ESTATE = "real_estate", "Real Estate"
        MESU = "mesu", "MESU Academy"
        OTHER = "other", "Other"

    title = models.CharField(max_length=200)
    slug = models.SlugField(max_length=220, unique=True, blank=True)
    description = models.TextField(
        help_text="Explain what the member will learn from this video.",
    )
    youtube_url = models.URLField(
        max_length=500,
        help_text="Paste a full YouTube link (watch, youtu.be, or embed URL).",
    )
    youtube_video_id = models.CharField(max_length=20, editable=False, blank=True)
    category = models.CharField(
        max_length=32,
        choices=Category.choices,
        default=Category.GENERAL,
    )
    sort_order = models.PositiveIntegerField(
        default=0,
        help_text="Lower numbers appear first within a category.",
    )
    is_published = models.BooleanField(
        default=True,
        help_text="Only published videos are visible to members.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "-created_at"]
        verbose_name = "Help video"
        verbose_name_plural = "Help videos"

    def __str__(self) -> str:
        return self.title

    @property
    def embed_url(self) -> str:
        return youtube_embed_url(self.youtube_video_id) if self.youtube_video_id else ""

    @property
    def thumbnail_url(self) -> str:
        return youtube_thumbnail_url(self.youtube_video_id) if self.youtube_video_id else ""

    def clean(self):
        video_id = extract_youtube_video_id(self.youtube_url)
        if not video_id:
            raise ValidationError(
                {"youtube_url": "Enter a valid YouTube video URL."}
            )

    def save(self, *args, **kwargs):
        video_id = extract_youtube_video_id(self.youtube_url)
        if not video_id:
            raise ValidationError("Invalid YouTube URL.")
        self.youtube_video_id = video_id
        if not self.slug:
            base = slugify(self.title)[:200] or "video"
            slug = base
            n = 1
            while HelpVideo.objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base}-{n}"
                n += 1
            self.slug = slug
        super().save(*args, **kwargs)
