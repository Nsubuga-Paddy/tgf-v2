from django.apps import AppConfig


def pending_verification_count() -> int:
    """Members awaiting admin approval (used by UserAdmin list columns)."""
    from core.admin_badges import pending_user_verification_count

    return pending_user_verification_count()


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"

    def ready(self):
        from core.admin_badges import patch_admin_pending_badges

        patch_admin_pending_badges()
        import accounts.signals  # noqa: F401
