"""
config/settings/development.py
===============================
المسار: config/settings/development.py
الوظيفة: إعدادات بيئة التطوير المحلية.
         تُورث من base.py وتُضيف:
           - django-debug-toolbar لفحص الـ SQL queries وكشف N+1
           - django-silk لـ profiling الطلبات
           - SQLite كقاعدة بيانات افتراضية (سهلة للتطوير)
           - Email backend يطبع في الـ console بدل الإرسال الفعلي
           - CORS مفتوح للتطوير المحلي

⚠️ ملاحظة: لا تُستخدم هذه الإعدادات أبداً في Production.
   تأكد أن DJANGO_SETTINGS_MODULE=config.settings.development في .env التطوير
"""

from .base import *  # noqa: F401, F403

# ---------------------------------------------------------------------------
# Debug Mode
# ---------------------------------------------------------------------------
DEBUG = True
ALLOWED_HOSTS = ["*", "localhost", "127.0.0.1"]

# ---------------------------------------------------------------------------
# Development-only Apps
# django-debug-toolbar: فحص SQL queries ومعرفة N+1 queries أثناء التطوير
# django-silk: profiling متقدم لكل request (وقت التنفيذ، عدد الـ queries)
# ---------------------------------------------------------------------------
INSTALLED_APPS += [  # noqa: F405
    "debug_toolbar",
    "silk",
]

# ---------------------------------------------------------------------------
# Middleware للـ Development
# يجب أن يكون debug_toolbar.middleware أول الـ middleware
# ---------------------------------------------------------------------------
MIDDLEWARE = [
    "debug_toolbar.middleware.DebugToolbarMiddleware",
    "silk.middleware.SilkyMiddleware",
] + MIDDLEWARE  # noqa: F405

# ---------------------------------------------------------------------------
# django-debug-toolbar: يُكتشف تلقائياً على localhost
# ---------------------------------------------------------------------------
INTERNAL_IPS = ["127.0.0.1", "localhost"]

DEBUG_TOOLBAR_CONFIG = {
    "SHOW_TOOLBAR_CALLBACK": lambda request: DEBUG,
    "SHOW_COLLAPSED": True,
}

# ---------------------------------------------------------------------------
# django-silk: Profiling settings
# ---------------------------------------------------------------------------
SILKY_PYTHON_PROFILER = True
SILKY_META = True
SILKY_ANALYZE_QUERIES = True

# ---------------------------------------------------------------------------
# Email: يطبع في الـ console بدل الإرسال الفعلي
# ---------------------------------------------------------------------------
EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# ---------------------------------------------------------------------------
# DRF: إضافة BrowsableAPIRenderer في التطوير فقط لسهولة الاختبار
# ---------------------------------------------------------------------------
REST_FRAMEWORK["DEFAULT_RENDERER_CLASSES"] += [  # noqa: F405
    "rest_framework.renderers.BrowsableAPIRenderer",
]

# ---------------------------------------------------------------------------
# Logging: مستوى DEBUG في التطوير
# ---------------------------------------------------------------------------
LOGGING["loggers"]["hotel_saas"]["level"] = "DEBUG"  # noqa: F405
