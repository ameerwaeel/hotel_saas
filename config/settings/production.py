"""
config/settings/production.py
==============================
المسار: config/settings/production.py
الوظيفة: إعدادات بيئة الإنتاج.
         تُورث من base.py وتُضيف:
           - Redis cache بدل LocMemCache
           - Security headers (HSTS, Secure cookies, إلخ)
           - JSON structured logging للـ production
           - Sentry error tracking (يتفعل لاحقاً في Phase 12)

⚠️ تأكد أن DJANGO_SETTINGS_MODULE=config.settings.production في بيئة الإنتاج
"""

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
DEBUG = False
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000  # 1 year
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_HSTS_PRELOAD = True
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
SECURE_BROWSER_XSS_FILTER = True
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = "DENY"

# ---------------------------------------------------------------------------
# Redis Cache في Production
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.redis.RedisCache",
        "LOCATION": env("REDIS_URL", default="redis://localhost:6379/1"),  # noqa: F405
        "OPTIONS": {
            "CLIENT_CLASS": "django_redis.client.DefaultClient",
            "CONNECTION_POOL_KWARGS": {"max_connections": 50},
        },
        "KEY_PREFIX": "hotel_saas",
        "TIMEOUT": 300,  # 5 minutes default
    }
}

# ---------------------------------------------------------------------------
# Email SMTP في Production
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.smtp.EmailBackend"
EMAIL_HOST = env("EMAIL_HOST", default="smtp.gmail.com")  # noqa: F405
EMAIL_PORT = env.int("EMAIL_PORT", default=587)  # noqa: F405
EMAIL_USE_TLS = True
EMAIL_HOST_USER = env("EMAIL_HOST_USER", default="")  # noqa: F405
EMAIL_HOST_PASSWORD = env("EMAIL_HOST_PASSWORD", default="")  # noqa: F405

# ---------------------------------------------------------------------------
# Logging: JSON structured في Production
# ---------------------------------------------------------------------------
LOGGING["handlers"]["console"]["formatter"] = "json"  # noqa: F405
LOGGING["loggers"]["hotel_saas"]["level"] = "INFO"  # noqa: F405
