"""
accounts/apps.py
=================
المسار: accounts/apps.py
الوظيفة: تسجيل الـ signals عند بدء تشغيل الـ app.
"""

from django.apps import AppConfig


class AccountsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "accounts"
    verbose_name = "Accounts & Authentication"

    def ready(self):
        """
        يُستدعى عند بدء Django.
        يُسجِّل الـ signals لمسح cache الصلاحيات.
        """
        import accounts.signals  # noqa: F401
