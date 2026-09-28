"""
config/__init__.py
==================
المسار: config/__init__.py
الوظيفة: تفعيل Celery عند تحميل Django
         يضمن أن app.autodiscover_tasks() يعمل عند بدء Django
"""

# تأكد من تحميل Celery عند بدء Django
from .celery import app as celery_app

__all__ = ("celery_app",)
