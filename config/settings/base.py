"""
config/settings/base.py
=======================
المسار: config/settings/base.py
الوظيفة: الإعدادات الأساسية المشتركة بين جميع البيئات (development, production).
         لا تُستخدم مباشرةً، بل تُورث في development.py و production.py.

الـ Apps المُسجَّلة:
  - كل الـ Django apps الأساسية
  - كل الـ hotel SaaS apps (accounts, tenants, rooms, ... إلخ)
  - DRF, drf-spectacular, django-filter

الـ Middleware:
  - RequestIDMiddleware (مخصص) لتوليد request_id لكل طلب
  - TenantMiddleware (مخصص) لحقن request.hotel

Databases:
  - مُهيَّأ لقراءة القيم من .env عبر django-environ
  - CONN_MAX_AGE=60 لتقليل overhead اتصال قاعدة البيانات

REST_FRAMEWORK:
  - Pagination موحدة (HotelSaaSPagination من common/pagination)
  - Exception handler مخصص (common/exceptions)
  - API versioning عبر URL
  - JWT authentication افتراضي
"""

from pathlib import Path
import environ

# ---------------------------------------------------------------------------
# Base directory — جذر المشروع (حيث يوجد manage.py)
# ---------------------------------------------------------------------------
BASE_DIR = Path(__file__).resolve().parent.parent.parent

# ---------------------------------------------------------------------------
# django-environ — قراءة متغيرات البيئة من ملف .env
# ---------------------------------------------------------------------------
env = environ.Env(
    DEBUG=(bool, False),
    ALLOWED_HOSTS=(list, []),
    CONN_MAX_AGE=(int, 60),
)
environ.Env.read_env(BASE_DIR / ".env")

# ---------------------------------------------------------------------------
# Security
# ---------------------------------------------------------------------------
SECRET_KEY = env("SECRET_KEY")
DEBUG = env("DEBUG")
ALLOWED_HOSTS = env("ALLOWED_HOSTS")

# ---------------------------------------------------------------------------
# Application definition
# ---------------------------------------------------------------------------
DJANGO_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
]

THIRD_PARTY_APPS = [
    "rest_framework",
    "rest_framework_simplejwt",
    "rest_framework_simplejwt.token_blacklist",
    "drf_spectacular",
    "django_filters",
]

# تطبيقات الـ hotel SaaS — كلها مسجلة من البداية كما نص عليه Plan
LOCAL_APPS = [
    "accounts",
    "tenants",
    "features",
    "subscriptions",
    "rooms",
    "customers",
    "reservations",
    "payments",
    "finance",
    "housekeeping",
    "maintenance",
    "complaints",
]

INSTALLED_APPS = DJANGO_APPS + THIRD_PARTY_APPS + LOCAL_APPS

# ---------------------------------------------------------------------------
# Middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    # 🆔 Request-ID Middleware — يُضيف X-Request-ID لكل طلب (Phase 1)
    "common.middleware.request_id.RequestIDMiddleware",
    # 🏨 Tenant Middleware — يُحقن request.hotel من JWT/session (Phase 2)
    "common.middleware.tenant.TenantMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

# ---------------------------------------------------------------------------
# URLs
# ---------------------------------------------------------------------------
ROOT_URLCONF = "config.urls"

# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------
TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [BASE_DIR / "templates"],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"
ASGI_APPLICATION = "config.asgi.application"

# ---------------------------------------------------------------------------
# Database — يُقرأ من .env
# CONN_MAX_AGE=60 يقلل overhead إعادة الاتصال بـ PostgreSQL في Production
# ---------------------------------------------------------------------------
DATABASES = {
    "default": env.db(
        "DATABASE_URL",
        default=f"sqlite:///{BASE_DIR / 'db.sqlite3'}",
    )
}
DATABASES["default"]["CONN_MAX_AGE"] = env("CONN_MAX_AGE")

# ---------------------------------------------------------------------------
# Custom User Model
# AUTH_USER_MODEL يجب أن يُحدَّد قبل أي migration — Phase 3
# ---------------------------------------------------------------------------
AUTH_USER_MODEL = "accounts.User"

# ---------------------------------------------------------------------------
# Password Validation
# ---------------------------------------------------------------------------
AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# ---------------------------------------------------------------------------
# Internationalization
# ---------------------------------------------------------------------------
LANGUAGE_CODE = "en-us"
TIME_ZONE = "UTC"
USE_I18N = True
USE_TZ = True

# ---------------------------------------------------------------------------
# Static & Media Files
# ---------------------------------------------------------------------------
STATIC_URL = "/static/"
STATIC_ROOT = BASE_DIR / "staticfiles"
MEDIA_URL = "/media/"
MEDIA_ROOT = BASE_DIR / "media"

# ---------------------------------------------------------------------------
# Default Primary Key
# ---------------------------------------------------------------------------
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

# ---------------------------------------------------------------------------
# Django REST Framework — Global Configuration
# جميع الـ ViewSets سترث هذه الإعدادات تلقائياً
# ---------------------------------------------------------------------------
REST_FRAMEWORK = {
    # 🔐 Authentication: JWT فقط (لا session authentication في الـ API)
    "DEFAULT_AUTHENTICATION_CLASSES": [
        "rest_framework_simplejwt.authentication.JWTAuthentication",
    ],
    # 🔒 كل الـ endpoints تتطلب authentication افتراضياً
    "DEFAULT_PERMISSION_CLASSES": [
        "rest_framework.permissions.IsAuthenticated",
    ],
    # 📄 Pagination موحدة من common/pagination
    "DEFAULT_PAGINATION_CLASS": "common.pagination.pagination.HotelSaaSPagination",
    "PAGE_SIZE": 20,
    # 🔍 Filtering عبر django-filter
    "DEFAULT_FILTER_BACKENDS": [
        "django_filters.rest_framework.DjangoFilterBackend",
        "rest_framework.filters.SearchFilter",
        "rest_framework.filters.OrderingFilter",
    ],
    # ⚠️ Exception Handler مخصص — يرجع JSON ثابت الشكل لكل الأخطاء
    "EXCEPTION_HANDLER": "common.exceptions.handlers.custom_exception_handler",
    # 📌 API Versioning عبر URL (مثلاً: /api/v1/...)
    "DEFAULT_VERSIONING_CLASS": "rest_framework.versioning.URLPathVersioning",
    "DEFAULT_VERSION": "v1",
    "ALLOWED_VERSIONS": ["v1"],
    "VERSION_PARAM": "version",
    # 🎨 Renderer: JSON فقط في production (HTML renderer في dev فقط)
    "DEFAULT_RENDERER_CLASSES": [
        "rest_framework.renderers.JSONRenderer",
    ],
    # 📦 Parser: JSON + FormData
    "DEFAULT_PARSER_CLASSES": [
        "rest_framework.parsers.JSONParser",
        "rest_framework.parsers.FormParser",
        "rest_framework.parsers.MultiPartParser",
    ],
    # 📚 Schema: drf-spectacular
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# ---------------------------------------------------------------------------
# Simple JWT Configuration
# ---------------------------------------------------------------------------
from datetime import timedelta

SIMPLE_JWT = {
    "ACCESS_TOKEN_LIFETIME": timedelta(minutes=60),
    "REFRESH_TOKEN_LIFETIME": timedelta(days=7),
    "ROTATE_REFRESH_TOKENS": True,
    "BLACKLIST_AFTER_ROTATION": True,
    "UPDATE_LAST_LOGIN": True,
    "ALGORITHM": "HS256",
    "AUTH_HEADER_TYPES": ("Bearer",),
    "AUTH_HEADER_NAME": "HTTP_AUTHORIZATION",
    "USER_ID_FIELD": "id",
    "USER_ID_CLAIM": "user_id",
}

# ---------------------------------------------------------------------------
# drf-spectacular — OpenAPI/Swagger Documentation
# ---------------------------------------------------------------------------
SPECTACULAR_SETTINGS = {
    "TITLE": "Hotel SaaS API",
    "DESCRIPTION": "Multi-Tenant Hotel Management SaaS Platform",
    "VERSION": "1.0.0",
    "SERVE_INCLUDE_SCHEMA": False,
    "SCHEMA_PATH_PREFIX": r"/api/v[0-9]",
    "COMPONENT_SPLIT_REQUEST": True,
    "TAGS": [
        {"name": "auth", "description": "Authentication & Authorization"},
        {"name": "tenants", "description": "Hotel & Tenant Management"},
        {"name": "rooms", "description": "Room Management"},
        {"name": "customers", "description": "Customer Management"},
        {"name": "reservations", "description": "Reservation Management"},
        {"name": "payments", "description": "Payments & Finance"},
    ],
}

# ---------------------------------------------------------------------------
# Cache — Redis (يُفعَّل في development.py/production.py)
# ---------------------------------------------------------------------------
CACHES = {
    "default": {
        "BACKEND": "django.core.cache.backends.locmem.LocMemCache",
        "LOCATION": "hotel-saas-cache",
    }
}

# ---------------------------------------------------------------------------
# Celery — مُجهَّز منذ البداية، يُستخدم فعلياً من Phase 6
# ---------------------------------------------------------------------------
CELERY_BROKER_URL = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_RESULT_BACKEND = env("REDIS_URL", default="redis://localhost:6379/0")
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_TIMEZONE = TIME_ZONE
CELERY_BEAT_SCHEDULER = "django_celery_beat.schedulers:DatabaseScheduler"

# ---------------------------------------------------------------------------
# Logging — Structured JSON Logging للـ Production
# كل الـ logs تحتوي على request_id لتتبع الطلبات
# ---------------------------------------------------------------------------
LOGGING = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        # Formatter للـ Development (human-readable)
        "verbose": {
            "format": "[{asctime}] {levelname} [{name}:{lineno}] {message}",
            "style": "{",
        },
        # Formatter للـ Production (JSON structured)
        "json": {
            "()": "common.logging.formatters.JSONFormatter",
        },
    },
    "filters": {
        "require_debug_true": {
            "()": "django.utils.log.RequireDebugTrue",
        },
        "require_debug_false": {
            "()": "django.utils.log.RequireDebugFalse",
        },
    },
    "handlers": {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "verbose",
        },
        "console_json": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "formatter": "json",
            "filters": ["require_debug_false"],
        },
        "null": {
            "class": "logging.NullHandler",
        },
    },
    "loggers": {
        "django": {
            "handlers": ["console"],
            "level": "INFO",
            "propagate": False,
        },
        "django.request": {
            "handlers": ["console"],
            "level": "ERROR",
            "propagate": False,
        },
        "hotel_saas": {
            "handlers": ["console"],
            "level": "DEBUG",
            "propagate": False,
        },
    },
    "root": {
        "handlers": ["console"],
        "level": "WARNING",
    },
}
