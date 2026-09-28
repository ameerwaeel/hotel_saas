# 📄 Phase 0 — تجهيز وتأسيس المشروع (Project Setup & Bootstrap)

المسار في التوثيق: `docs/PHASE_0_DOCS.md`  
الهدف: إنشاء وتأسيس بنية مشروع Django وتجهيز الحزم وقواعد البيانات والملفات البيئية.

---

## 🛠️ الملفات التي تم إنشاؤها وتعديلها في Phase 0

| اسم الملف | المسار المباشر | الوظيفة والتفاصيل |
| :--- | :--- | :--- |
| `requirements.txt` | [requirements.txt](file:///c:/Users/smart%20zone/Desktop/hotel_saas/requirements.txt) | ملف الحزم والاعتماديات الخاصة بالمشروع (Django, DRF, Celery, Redis, Pytest, Pillow, SimpleJWT, Silk, Debug Toolbar) |
| `manage.py` | [manage.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/manage.py) | تعديل مسار `DJANGO_SETTINGS_MODULE` ليرير تلقائياً إلى `config.settings.development` |
| `.env` | [.env](file:///c:/Users/smart%20zone/Desktop/hotel_saas/.env) | ملف متغيرات البيئة الحساسة (مفتاح الأمان، اتصالات قواعد البيانات، إعدادات Redis، البريد) |
| `.gitignore` | [.gitignore](file:///c:/Users/smart%20zone/Desktop/hotel_saas/.gitignore) | ملف استبعاد الملفات الحساسة والتنفيذية من Git مثل `.env` و `db.sqlite3` و `env/` |
| `config/__init__.py` | [config/__init__.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/__init__.py) | تحميل وتفعيل Celery App عند بدء تشغيل تطبيق Django |
| `config/celery.py` | [config/celery.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/celery.py) | ضبط Celery ليعمل مع Redis مع اكتشاف المهام التلقائي (`autodiscover_tasks()`) |
| `config/urls.py` | [config/urls.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/urls.py) | ملف التوجيه الرئيسي المركزية للـ APIs ومستندات Swagger و ReDoc والـ Debug Toolbar |
| `config/wsgi.py` | [config/wsgi.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/wsgi.py) | نقطة الدخول للسيرفرات التقليدية (WSGI) |
| `config/asgi.py` | [config/asgi.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/asgi.py) | نقطة الدخول التزامنية والـ Async للسيرفرات اللاحقة (WebSockets) |
| `config/settings/base.py` | [config/settings/base.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/settings/base.py) | الإعدادات المركزية المشتركة (تحديد التطبيقات المحلية، إعدادات DRF، Pagination، Logging، JWT) |
| `config/settings/development.py` | [config/settings/development.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/settings/development.py) | إعدادات بيئة التطوير وتفعيل أدوات الفحص والتطوير `debug_toolbar` و `silk` |
| `config/settings/production.py` | [config/settings/production.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/settings/production.py) | إعدادات البيئة الحية والإنتاجية من أمان وسيرفرات Redis و SMTP |
| `config/settings/testing.py` | [config/settings/testing.py](file:///c:/Users/smart%20zone/Desktop/hotel_saas/config/settings/testing.py) | إعدادات بيئة الاختارات لتسريع Pytest بدون تعارضات الـ HTML Toolbar |

---

## 🔍 أهم المشاكل التي تم التعامل معها في هذه المرحلة:
1. **فصل البيئات الإعدادية (Environment Split):** تم تقسيم `settings.py` التقليدي إلى مجلد `settings/` يحتوي على `base.py`, `development.py`, `production.py`, `testing.py` لمنع التداخل بين التطوير والإنتاج.
2. **تجهيز المهام المجدولة من أول يوم:** تم ربط وتنسيق `celery.py` مع Redis مباشرة لتفادي إعادة الهيكلة في المراحل المتقدمة.

---

## 🌐 ملاحظات الفرونت إند (React - Phase 0):
> [!NOTE] تم إرجاء أجزاء الفرونت إند مؤقتاً لحين الانتهاء من الـ Backend APIs.
> الأجزاء المطلوبة لاحقاً:
> - إنشاء مشروع React باستخدام Vite تحت مجلد `frontend/`.
> - تثبيت `axios`, `react-router-dom`, `react-i18next`.
