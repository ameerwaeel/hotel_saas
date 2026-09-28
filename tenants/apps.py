"""
tenants/apps.py
================
المسار: tenants/apps.py
الوظيفة: إعداد وتفعيل تطبيق Tenants وتسجيل الإشارات (Signals).
"""

from django.apps import AppConfig


class TenantsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "tenants"
    verbose_name = "Tenants & Hotels"

    def ready(self):
        """تسجيل الإشارات عند بدء تشغيل تطبيق Django."""
        import tenants.signals  # noqa: F401
