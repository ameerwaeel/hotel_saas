"""
customers/services.py
=====================
المسار: customers/services.py
Phase: 4 — Master Data
"""

from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as _
from customers.models import Customer, Employee


class CustomerService:
    """خدمات إدارة العملاء."""

    @staticmethod
    def create(hotel, first_name: str, last_name: str, phone: str = "",
               email: str = "", nationality: str = "", id_type: str = "",
               id_number: str = "", date_of_birth=None, notes: str = "",
               vip_status: bool = False, **kwargs) -> Customer:
        """إنشاء عميل جديد للفندق."""
        customer = Customer(
            hotel=hotel,
            first_name=first_name,
            last_name=last_name,
            phone=phone,
            email=email,
            nationality=nationality,
            id_type=id_type,
            id_number=id_number,
            date_of_birth=date_of_birth,
            notes=notes,
            vip_status=vip_status,
        )
        customer.full_clean()
        customer.save()
        return customer

    @staticmethod
    def update(customer: Customer, **kwargs) -> Customer:
        """تحديث بيانات عميل."""
        allowed = {
            "first_name", "last_name", "phone", "email",
            "nationality", "id_type", "id_number", "notes",
            "vip_status", "date_of_birth"
        }
        for key, value in kwargs.items():
            if key in allowed:
                setattr(customer, key, value)
        customer.full_clean()
        customer.save()
        return customer

    @staticmethod
    def increment_stays(customer: Customer) -> Customer:
        """زيادة عداد الإقامات (يُستدعى من ReservationService عند الـ checkout)."""
        Customer.objects.filter(id=customer.id).update(
            total_stays=customer.total_stays + 1
        )
        customer.refresh_from_db(fields=["total_stays"])
        return customer


class EmployeeService:
    """خدمات إدارة الموظفين."""

    @staticmethod
    def create(hotel, user, position: str = "", department: str = "",
               employee_id: str = "", hire_date=None, notes: str = "") -> Employee:
        """إنشاء ملف موظف مرتبط بحساب User."""
        # التحقق من أن المستخدم عضو في الفندق
        from accounts.models import HotelMembership
        if not HotelMembership.objects.filter(hotel=hotel, user=user, status="active").exists():
            raise ValidationError(_(
                "User must be an active member of the hotel to become an employee."
            ))

        employee = Employee(
            hotel=hotel,
            user=user,
            position=position,
            department=department,
            employee_id=employee_id,
            hire_date=hire_date,
            notes=notes,
        )
        employee.full_clean()
        employee.save()
        return employee

    @staticmethod
    def update(employee: Employee, **kwargs) -> Employee:
        """تحديث بيانات موظف."""
        allowed = {"position", "department", "employee_id", "hire_date", "notes", "is_active"}
        for key, value in kwargs.items():
            if key in allowed:
                setattr(employee, key, value)
        employee.full_clean()
        employee.save()
        return employee
