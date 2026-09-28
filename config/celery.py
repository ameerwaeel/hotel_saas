"""
config/celery.py
=================
المسار: config/celery.py
الوظيفة: تجهيز Celery مع Django من البداية.
         ⚠️ Celery مُجهَّز ومربوط بـ Redis لكنه لن يُستخدم فعلياً حتى Phase 6.
         هذا يمنع أي refactoring مؤلم لاحقاً عند إضافة background tasks.

كيف يعمل:
  1. يقرأ DJANGO_SETTINGS_MODULE لتحميل settings المناسبة
  2. يستخدم CELERY_BROKER_URL من settings (مُعرَّف في base.py)
  3. يكتشف Tasks تلقائياً من كل app مسجلة في INSTALLED_APPS

الاستخدام:
  $ celery -A config worker -l info         # تشغيل worker
  $ celery -A config beat -l info           # تشغيل scheduler
  $ celery -A config flower                 # monitoring UI (يحتاج flower)
"""

import os
from celery import Celery

# تحديد الـ settings المستخدمة — يُقرأ من بيئة التشغيل
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

# إنشاء Celery instance باسم المشروع
app = Celery("hotel_saas")

# تحميل Celery configuration من Django settings (كل مفاتيح CELERY_*)
app.config_from_object("django.conf:settings", namespace="CELERY")

# اكتشاف Tasks تلقائياً من كل app في INSTALLED_APPS
# سيبحث عن tasks.py في كل app مسجلة
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """Task تجريبية للتأكد من أن Celery يعمل بشكل صحيح."""
    print(f"Request: {self.request!r}")
