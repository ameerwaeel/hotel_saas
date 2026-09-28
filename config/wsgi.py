"""
config/wsgi.py
==============
المسار: config/wsgi.py
الوظيفة: WSGI application entry point للـ production server (gunicorn, uWSGI)
"""

import os
from django.core.wsgi import get_wsgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

application = get_wsgi_application()
