"""
config/settings/testing.py
============================
المسار: config/settings/testing.py
الوظيفة: إعدادات بيئة الـ Testing.
         تُورث من base.py وتُعطِّل:
           - debug_toolbar (يسبب مشاكل في tests لأن URLpatterns غير مكتملة)
           - django-silk (يُبطئ الـ tests)
           - Django Logger (يُسبب تعارض في الـ LogRecord fields)

⚠️ مشكلة Django المعروفة مع debug_toolbar في tests:
   debug_toolbar يحاول عرض HTML ويتحقق من 'djdt' namespace.
   في الـ tests، الـ HTML renderer غير ضروري والـ namespace غير موجود.
   الحل: تعطيل debug_toolbar في Testing settings.
"""

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Testing settings — تعطيل أدوات لا داعي لها في الـ tests
# ---------------------------------------------------------------------------
DEBUG = False

# إزالة debug_toolbar و silk من الـ tests
INSTALLED_APPS = [
    app for app in INSTALLED_APPS  # noqa: F405
    if app not in ("debug_toolbar", "silk")
]

MIDDLEWARE = [
    m for m in MIDDLEWARE  # noqa: F405
    if "debug_toolbar" not in m and "silk" not in m
]

# ---------------------------------------------------------------------------
# Database: SQLite in-memory للسرعة في الـ tests
# ---------------------------------------------------------------------------
DATABASES = {
    "default": {
        "ENGINE": "django.db.backends.sqlite3",
        "NAME": ":memory:",
        "TEST": {
            "NAME": ":memory:",
        },
    }
}

# ---------------------------------------------------------------------------
# Cache: LocMemCache بسيط (Redis غير ضروري في tests)
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "test-cache",
    }
}

# ---------------------------------------------------------------------------
# Logging: تعطيل JSON formatter في tests (يسبب KeyError مع 'created' field)
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": True,
    "handlers": {
        "null": {"class": "logging.NullHandler"},
    },
    "root": {
        "handlers": ["null"],
        "level": "CRITICAL",
    },
    "loggers": {
        "hotel_saas": {"handlers": ["null"], "level": "CRITICAL"},
        "django": {"handlers": ["null"], "level": "CRITICAL"},
    },
}

# ---------------------------------------------------------------------------
# Email: لا نرسل emails في tests
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.locmem.EmailBackend"

# ---------------------------------------------------------------------------
# Password Hashing: أسرع hasher للـ tests
# ---------------------------------------------------------------------------
PASSWORD_HASHERS = [
    "django.contrib.auth.hashers.MD5PasswordHasher",
]
