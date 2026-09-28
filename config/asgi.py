"""
config/asgi.py
==============
المسار: config/asgi.py
الوظيفة: ASGI application entry point للـ async support (Channels, Daphne)
         مُجهَّز الآن، سيُستخدم في Phase 8 لـ WebSocket notifications.
"""

import os
from django.core.asgi import get_asgi_application

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

application = get_asgi_application()
