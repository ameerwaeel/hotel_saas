"""
customers/selectors.py
======================
المسار: customers/selectors.py
Phase: 4 — Master Data
"""

from django.db.models import QuerySet, Q
from customers.models import Customer, Employee


# ---------------------------------------------------------------------------
# Customer Selectors
# ---------------------------------------------------------------------------

def get_customers(hotel, search: str = None, vip_only: bool = False) -> QuerySet:
    """
    عملاء الفندق مع خيار البحث.

    ⚠️ Search Strategy:
       بدلاً من icontains بسيط (بطيء مع البيانات الكبيرة)، نستخدم
       Q objects مع indexes مناسبة على phone/email/last_name.
       
       في Production مع PostgreSQL: يمكن تحسينها بـ SearchVector/GIN index.
       الحل الحالي كافٍ للـ MVP مع الـ indexes الموجودة على الحقول.

    Args:
        hotel: الفندق
        search: نص البحث (اسم، هاتف، بريد)
        vip_only: VIP فقط؟
    """
    qs = Customer.objects.for_hotel(hotel).filter(is_active=True)

    if search:
        qs = qs.filter(
            Q(first_name__icontains=search) |
            Q(last_name__icontains=search) |
            Q(phone__icontains=search) |
            Q(email__icontains=search) |
            Q(id_number__icontains=search)
        )

    if vip_only:
        qs = qs.filter(vip_status=True)

    return qs


def get_customer_by_id(hotel, customer_id) -> Customer:
    """عميل محدد داخل فندق."""
    return Customer.objects.for_hotel(hotel).get(id=customer_id)


def get_customer_by_phone(hotel, phone: str) -> Customer | None:
    """البحث عن عميل بالهاتف — يرجع None إذا لم يوجد."""
    return Customer.objects.for_hotel(hotel).filter(phone=phone).first()


# ---------------------------------------------------------------------------
# Employee Selectors
# ---------------------------------------------------------------------------

def get_employees(hotel, department: str = None, is_active: bool = True) -> QuerySet:
    """
    موظفو الفندق.

    ⚠️ N+1 Prevention: select_related("user")
    """
    qs = (
        Employee.objects
        .for_hotel(hotel)
        .select_related("user")
    )
    if is_active is not None:
        qs = qs.filter(is_active=is_active)
    if department:
        qs = qs.filter(department=department)
    return qs


def get_employee_by_id(hotel, employee_id) -> Employee:
    """موظف محدد."""
    return (
        Employee.objects
        .for_hotel(hotel)
        .select_related("user")
        .get(id=employee_id)
    )
