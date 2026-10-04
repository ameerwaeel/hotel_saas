"""
customers/serializers.py
========================
المسار: customers/serializers.py
Phase: 4 — Master Data
"""

from rest_framework import serializers
from customers.models import Customer, Employee


class CustomerSerializer(serializers.ModelSerializer):
    full_name = serializers.CharField(read_only=True)

    class Meta:
        model = Customer
        fields = [
            "id", "first_name", "last_name", "full_name",
            "email", "phone", "nationality", "id_type", "id_number",
            "date_of_birth", "vip_status", "notes", "total_stays",
            "is_active", "created_at"
        ]
        read_only_fields = ["id", "full_name", "total_stays", "created_at"]


class CustomerWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Customer
        fields = [
            "first_name", "last_name", "email", "phone",
            "nationality", "id_type", "id_number", "date_of_birth",
            "vip_status", "notes"
        ]


class EmployeeSerializer(serializers.ModelSerializer):
    """
    ⚠️ N+1 Safe: user_name/user_email يقرأ من FK الذي يجب أن يكون
       مُجلَباً بـ select_related("user") في Selector.
    """
    user_name = serializers.CharField(source="user.full_name", read_only=True)
    user_email = serializers.EmailField(source="user.email", read_only=True)

    class Meta:
        model = Employee
        fields = [
            "id", "user", "user_name", "user_email",
            "employee_id", "position", "department", "hire_date",
            "notes", "is_active", "created_at"
        ]
        read_only_fields = ["id", "user_name", "user_email", "created_at"]


class EmployeeWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Employee
        fields = ["user", "employee_id", "position", "department", "hire_date", "notes"]
