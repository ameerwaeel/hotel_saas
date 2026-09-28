#!/usr/bin/env python
"""
manage.py
=========
المسار: manage.py (جذر المشروع)
الوظيفة: Django management command entry point.
         تم تحديثه ليستخدم config.settings.development بدلاً من project.settings.
         يقرأ DJANGO_SETTINGS_MODULE من .env تلقائياً عبر config/settings/base.py.

الاستخدام:
  python manage.py runserver                    # تشغيل الـ server
  python manage.py migrate                      # تطبيق الـ migrations
  python manage.py createsuperuser              # إنشاء superuser
  python manage.py spectacular --file schema.yml  # توليد OpenAPI schema
"""

import os
import sys


def main():
    """Run administrative tasks."""
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")
    try:
        from django.core.management import execute_from_command_line
    except ImportError as exc:
        raise ImportError(
            "Couldn't import Django. Are you sure it's installed and "
            "available on your PYTHONPATH environment variable? Did you "
            "forget to activate a virtual environment?"
        ) from exc
    execute_from_command_line(sys.argv)


if __name__ == "__main__":
    main()
