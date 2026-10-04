# Hotel SaaS — Implementation Plan: Phase 4 → Phase 7

**المسار:** `docs/IMPLEMENTATION_PLAN_PHASE_4_TO_7.md`  
**المرجع:** `HOTEL_SaaS_Full_Plan (2).md`  
**الحالة:** مُنفذ ومختبر وموثق بالكامل (Fully Implemented & Verified) ✅

---

## 🎯 الهدف العام (Goal)
بناء المراحل 4 و 5 و 6 و 7 من منصة Hotel SaaS طبقاً للمواصفات المعمارية الدقيقة في ملف `HOTEL_SaaS_Full_Plan (2).md`. تتضمن كل مرحلة بناء النماذج (Models)، الترحيلات (Migrations)، المحددات والاستعلامات الخالية من مشاكل الأداء (Selectors)، طبقة الأعمال الصارمة (Services)، المحولات (Serializers)، الصلاحيات وتعدد المستأجرين (Permissions & Tenancy)، واجهات الـ API، والتوثيق والاختبارات الشاملة (100% Tests Pass).

---

## 📐 القاعدة الذهبية للتنفيذ (The Golden Rule)
```
MODEL → MIGRATION → SELECTOR → SERVICE → SERIALIZER → PERMISSION → FEATURE CHECK → TENANT SCOPE → BUSINESS RULE → API → TESTS → DOCS
```

---

## 🏨 1. Phase 4 — Master Data (الغرف والبيانات الأساسية والموظفين)

### النماذج (Models)
1. **`Language` (تطبيق `rooms`):** جدول عام (Global Registry) بدون ارتباط بـ `hotel`.
2. **`HotelLanguage` (تطبيق `rooms`):** جدول وسيط يربط الفندق باللغات مع تحديد `is_default` بشكل ذري (`transaction.atomic`).
3. **`BookingSource` (تطبيق `rooms`):** مصادر الحجز (Booking.com, Walk-in, Expedia) مع نسبة العمولة وفهرسة الفندق.
4. **`RoomType` و `RoomTypeTranslation` (تطبيق `rooms`):** فئات الغرف مع دعم التدويل والترجمة متعددة اللغات.
5. **`Room` (تطبيق `rooms`):** الغرف الفردية، مع قيد فريد `UniqueConstraint(fields=["hotel", "room_number"])` للسماح بنفس الرقم في فنادق مختلفة ومنعه داخل الفندق الواحد، مع فهرسة على `status`.
6. **`Customer` (تطبيق `customers`):** ملفات الضيوف مع أنواع الهويات، علامة VIP، عدد الإقامات، وفهارس بحث على الهاتف والبريد والاسم.
7. **`Employee` (تطبيق `customers`):** موظفو الفندق مرتبطون بحساب المستخدم `User` مع التحقق الصارم من وجود عضوية فندق نشطة `HotelMembership` واختيار القسم.

### المحددات والخدمات (Selectors & Services)
- `rooms/selectors.py`: منع استعلامات N+1 بالكامل باستخدام `prefetch_related("translations")` و `select_related("room_type")`.
- `rooms/services.py`: إدارة دورة حياة الغرف وتحديث حالتها مع خطاف التحقق من الأعطال الحرجة `_check_no_blocking_issues()`.
- `customers/selectors.py`: استعلامات بحث سريعة ومفهرسة باستخدام `Q` objects للبحث بالهاتف أو البريد أو الاسم.
- `customers/services.py`: إنشاء الضيوف والموظفين وتحديث الإقامات.

### المخرجات الفنية
- **الملفات التوثيقية:** `docs/PHASE_4_DOCS.md` و `docs/endpoints/PHASE_4_ENDPOINTS.md`
- **ملف الاختبارات:** `tests/test_phase4.py` (27 اختباراً ناجحاً بنسبة 100%)

---

## 📅 2. Phase 5 — Reservations & Availability Engine (محرك الحجوزات والتوفر)

### النماذج (Models)
1. **`Reservation`:** الحجز الرئيسي مع آلة حالات دقيقة ومصفوفة انتقالات مسموحة `VALID_TRANSITIONS`:
   - `pending → confirmed / cancelled`
   - `confirmed → checked_in / cancelled / no_show`
   - `checked_in → checked_out`
2. **`ReservationRoom`:** غرف الحجز بلقطة سعرية غير قابلة للتعديل (`nightly_price`) وفهرس مركب أساسي للأداء:
   - `models.Index(fields=["room", "check_in", "check_out"], name="idx_resroom_room_dates")`
   - نموذج حذف مرن (`SoftDeleteModel`) لضمان عدم ضياع السجلات المالية.
3. **`ReservationRoomChange`:** سجل تاريخي لتغيير وترقية الغرف مع توثيق فرق السعر والسبب والمستخدم.

### خوارزمية فحص التوفر والوقاية من التضارب (Availability & Concurrency)
- **خوارزمية الاستعلام بالتداخل (Overlap Query):** لا يتم استخدام جدول لكل يوم بل استعلام تداخل سريع وفعال:
  $$\text{check\_in} < \text{requested\_checkout} \quad \text{AND} \quad \text{check\_out} > \text{requested\_checkin}$$
- **منع حجز الغرفة المتزامن (Race Condition Prevention):**
  استخدام `Room.objects.select_for_update()` داخل كتلة `transaction.atomic()` وإعادة التحقق من التوفر قبل تأكيد الحجز مباشرة لمنع ظاهرة (TOCTOU).

### الترابط عند تسجيل المغادرة (Checkout Hook)
عند تنفيذ `ReservationService.check_out()`:
- تتغير حالة الغرف تلقائياً إلى `CLEANING`.
- تُنشأ مهام تنظيف صريحة في `housekeeping.RoomCleaning` بدون إشارات متداخلة مبهمة.
- يُزاد عداد إقامات العميل `Customer.total_stays`.

### المخرجات الفنية
- **الملفات التوثيقية:** `docs/PHASE_5_DOCS.md` و `docs/endpoints/PHASE_5_ENDPOINTS.md`
- **ملف الاختبارات:** `tests/test_phase5.py` (19 اختباراً ناجحاً بنسبة 100%)

---

## 💰 3. Phase 6 — Payments, Finance & Multi-Currency (المدفوعات والماليات والإغلاقات)

### النماذج (Models)
1. **`PaymentMethod`:** طرق الدفع المفهرسة لكل فندق (كاش، فيزا، ماستركارد، تحويل بنكي).
2. **`Payment`:** عمليات الدفع بحذف مرن، وحقول مالية بنوع `DecimalField(max_digits=12, decimal_places=2)` حصراً وممنوع استخدام `FloatField`.
3. **`FinanceCategory`:** بنود الإيرادات والمصروفات.
4. **`FinancialTransaction`:** قيود المعاملات المالية الموثقة للمراجعة الجنائية والمحاسبية بدون حذف فيزيائي.
5. **`ExchangeRate`:** أسعار الصرف بدقة 6 خانات عشرية وتُستخدم لأغراض العرض فقط ولا تُحول السجلات المخزنة تلقائياً.
6. **`DailyClosing`:** إغلاق الأيام المالية مع حماية من الإغلاق المزدوج باستخدام `select_for_update()`.
7. **`MonthlyClosing`:** إغلاق الأشهر وتجميع الأيام المقفلة.

### القواعد المعمارية الصارمة (Strict Financial Rules)
- **عزل العملات:** ممنوع جمع مبالغ من عملات مختلفة نهائياً. يتم التجميع دائماً باستخدام:
  `GROUP BY currency`
- **إغلاق اليوم المالي:** عند إغلاق اليوم، يُمنع منعاً باتاً إضافة أو تعديل أي معاملة مالية أو دفعة على ذلك التاريخ.

### مهام الخلفية (Celery Tasks)
- `auto_close_previous_day`: مهمة دورية مجدولة (Celery Beat) تعمل في الساعة 01:00 فجراً يومياً.
- `export_financial_report`: مهمة توليد تقارير مالية بصيغ PDF/Excel بشكل غير متزامن تُرجع `task_id` للواجهة.

### المخرجات الفنية
- **الملفات التوثيقية:** `docs/PHASE_6_DOCS.md` و `docs/endpoints/PHASE_6_ENDPOINTS.md`
- **ملف الاختبارات:** `tests/test_phase6.py` (14 اختباراً ناجحاً بنسبة 100%)

---

## 🧹 4. Phase 7 — Housekeeping, Maintenance & Complaints (الإشراف والصيانة والشكاوى)

### النماذج ودورات العمل (Models & Workflows)
1. **`RoomCleaning` (Housekeeping):**
   - دورة الحياة: `pending → in_progress → completed → inspected`
   - عند الوصول إلى `inspected`: يتم استدعاء `RoomService.update_status(AVAILABLE)` لتحرير الغرفة.
2. **`RoomIssue` (Maintenance):**
   - حقل `blocking=True` يمنع تحويل حالة الغرفة إلى `AVAILABLE`.
   - فهرسة مشتركة على `(status, priority)` لتسريع استعلامات الأعطال المفتوحة ذات الأولوية.
3. **`CustomerComplaint` (Complaints):**
   - إدارة شكاوى النزلاء وربطها بالموظف المسؤول وتدوين ملاحظات الحل وتغيير الحالة.

### الربط بين المراحل السابقة (Completed Integrations)
- **تطبيق `rooms`:** تم تفعيل فحص `_check_no_blocking_issues()` للتحقق من عدم وجود أي عطل مانع مفتوح قبل جعل الغرفة متاحة.
- **تطبيق `reservations`:** تم تفعيل استدعاء `_create_cleaning_tasks()` صراحةً فور عمل checkout.
- **إشعارات الطوارئ المفصولة:** تم تفعيل Signal عند تسجيل عطل ذي أولوية حرجة أو عالية ليرسل مهمة خلفية `notify_high_priority_issue.delay()` دون تعطيل استجابة الطلب.
- **منع N+1 في استعلامات الغرف:** فحص الأعطال المانعة عبر `Exists` Subquery في مستوى الاستعلام بدلاً من استدعاءات متكررة.

### المخرجات الفنية
- **الملفات التوثيقية:** `docs/PHASE_7_DOCS.md` و `docs/endpoints/PHASE_7_ENDPOINTS.md`
- **ملف الاختبارات:** `tests/test_phase7.py` (18 اختباراً ناجحاً بنسبة 100%)

---

## 📊 جدول التحقق الشامل (Verification Summary)

| المرحلة | التطبيقات البرمجية | عدد الاختبارات | الحالة |
| :--- | :--- | :--- | :--- |
| **Phase 4** | `rooms`, `customers` | 27 Passed | ✅ مكتمل ومختبر |
| **Phase 5** | `reservations` | 19 Passed | ✅ مكتمل ومختبر |
| **Phase 6** | `payments`, `finance` | 14 Passed | ✅ مكتمل ومختبر |
| **Phase 7** | `housekeeping`, `maintenance`, `complaints` | 18 Passed | ✅ مكتمل ومختبر |
| **الإجمالي للمراحل 4-7** | **7 تطبيقات برمجية جديدة** | **74 Passed** | **✅ 100% نجاح** |
| **الإجمالي العام للمشروع** | **كامل المراحل من 0 إلى 7** | **112 Passed** | **✅ 100% نجاح** |
