"""Seed/refresh Discover catalog metadata for MCS projects.

Idempotent: safe to run repeatedly. Only fills catalog display fields; it does
not touch memberships. Admins can override any of these values in the admin.

    python manage.py seed_project_catalog
"""
from django.core.management.base import BaseCommand

from accounts.models import Project

CATALOG = [
    {
        "name": "52 Weeks Saving Challenge",
        "icon": "fa-piggy-bank",
        "summary": "Save every week for a year and earn interest on your matured savings.",
        "rate_display": "15% p.a.",
        "min_entry_display": "UGX 10,000 / week",
        "cycle_display": "52 weeks (Jan – Dec)",
        "dashboard_url_name": "savings_52_weeks:member_dashboard",
        "status": Project.Status.OPEN,
        "sort_order": 10,
    },
    {
        "name": "Generational Wealth Creation",
        "icon": "fa-hand-holding-heart",
        "summary": "Fixed deposits that grow your wealth for the next generation.",
        "rate_display": "Up to 22.5% p.a.",
        "min_entry_display": "UGX 100,000",
        "cycle_display": "6 – 24 month terms",
        "dashboard_url_name": "gwc:gwc",
        "status": Project.Status.OPEN,
        "sort_order": 20,
    },
    {
        "name": "Commercial Goat Farming",
        "icon": "fa-horse",
        "summary": "Invest in managed goat farming and earn from each breeding cycle.",
        "rate_display": "Cycle-based returns",
        "min_entry_display": "1 package",
        "cycle_display": "14-month cycle",
        "dashboard_url_name": "goat_farming:dashboard",
        "status": Project.Status.OPEN,
        "sort_order": 30,
    },
    {
        "name": "Real Estate Projects",
        "icon": "fa-city",
        "summary": "Own a stake in MCS real estate developments and land projects.",
        "rate_display": "Capital growth",
        "min_entry_display": "Project dependent",
        "cycle_display": "Multi-year",
        "dashboard_url_name": "realestate_projects:rep",
        "status": Project.Status.OPEN,
        "sort_order": 40,
    },
    {
        "name": "Cooperative Shareholding",
        "icon": "fa-landmark",
        "summary": "Become a shareholder and earn annual dividends.",
        "dashboard_url_name": "profile",
        "is_public": False,  # shown as the top-level equity block, not in Discover
        "status": Project.Status.OPEN,
        "sort_order": 5,
    },
    # ---- Discover-only projects (no dedicated member data yet) ----
    {
        "name": "Fixed Savings Account",
        "icon": "fa-lock",
        "summary": "Lock your savings for a fixed term and earn a guaranteed higher rate.",
        "rate_display": "10% p.a.",
        "min_entry_display": "UGX 500,000",
        "cycle_display": "6 – 24 months",
        "dashboard_url_name": "fsa",
        "status": Project.Status.OPEN,
        "sort_order": 50,
    },
    {
        "name": "Retirement Savings Scheme",
        "icon": "fa-user-clock",
        "summary": "A long-term plan that builds a reliable retirement fund.",
        "rate_display": "12% p.a.",
        "min_entry_display": "UGX 50,000 / month",
        "cycle_display": "Access at age 55+",
        "dashboard_url_name": "rss",
        "status": Project.Status.OPEN,
        "sort_order": 60,
    },
    {
        "name": "Clubs Account",
        "icon": "fa-users",
        "summary": "Pool resources with other members towards shared goals.",
        "rate_display": "8% p.a.",
        "min_entry_display": "UGX 20,000 joining",
        "cycle_display": "12 months",
        "dashboard_url_name": "clubs_account:clubs_account",
        "status": Project.Status.OPEN,
        "sort_order": 70,
    },
    {
        "name": "Coffee Farming",
        "icon": "fa-mug-hot",
        "summary": "Invest in managed coffee plantations and earn from harvest sales.",
        "rate_display": "18 – 25% / cycle",
        "min_entry_display": "UGX 2,000,000",
        "cycle_display": "First cycle Q1 2027",
        "status": Project.Status.COMING_SOON,
        "sort_order": 80,
    },
    {
        "name": "Cocoa Farming",
        "icon": "fa-seedling",
        "summary": "Participate in cocoa growing projects with strong export demand.",
        "rate_display": "20 – 28% / cycle",
        "min_entry_display": "UGX 2,500,000",
        "cycle_display": "First cycle Q2 2027",
        "status": Project.Status.COMING_SOON,
        "sort_order": 90,
    },
]


class Command(BaseCommand):
    help = "Seed/refresh Discover catalog metadata for MCS projects."

    def handle(self, *args, **options):
        created, updated = 0, 0
        for entry in list(CATALOG):
            data = dict(entry)
            name = data.pop("name")
            obj, was_created = Project.objects.get_or_create(name=name)
            for field, value in data.items():
                setattr(obj, field, value)
            obj.save()
            created += int(was_created)
            updated += int(not was_created)
            self.stdout.write(f"  {'created' if was_created else 'updated'}: {name}")
        self.stdout.write(self.style.SUCCESS(f"Done. {created} created, {updated} updated."))
