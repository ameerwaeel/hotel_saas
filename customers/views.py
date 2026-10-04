"""
customers/views.py
==================
المسار: customers/views.py
Phase: 4 — Master Data
"""

from rest_framework import viewsets, status
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.filters import SearchFilter, OrderingFilter
from django_filters.rest_framework import DjangoFilterBackend
from drf_spectacular.utils import extend_schema, extend_schema_view

from common.permissions.hotel_permissions import IsHotelMember, HasHotelPermission
from customers.models import Customer, Employee
from customers.selectors import get_customers, get_customer_by_id, get_employees, get_employee_by_id
from customers.services import CustomerService, EmployeeService
from customers.serializers import (
    CustomerSerializer, CustomerWriteSerializer,
    EmployeeSerializer, EmployeeWriteSerializer
)


@extend_schema_view(
    list=extend_schema(summary="List customers (with search)", tags=["Customers"]),
    create=extend_schema(summary="Create customer", tags=["Customers"]),
    retrieve=extend_schema(summary="Get customer detail", tags=["Customers"]),
    update=extend_schema(summary="Update customer", tags=["Customers"]),
    destroy=extend_schema(summary="Deactivate customer", tags=["Customers"]),
)
class CustomerViewSet(viewsets.ModelViewSet):
    """Hotel guest management with indexed search."""
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, SearchFilter, OrderingFilter]
    filterset_fields = ["vip_status", "nationality"]
    search_fields = ["first_name", "last_name", "phone", "email"]
    ordering_fields = ["last_name", "total_stays", "created_at"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return CustomerWriteSerializer
        return CustomerSerializer

    def get_queryset(self):
        search = self.request.query_params.get("search")
        vip_only = self.request.query_params.get("vip_only") == "true"
        return get_customers(self.request.hotel, search=search, vip_only=vip_only)

    def perform_create(self, serializer):
        return CustomerService.create(
            hotel=self.request.hotel,
            **serializer.validated_data
        )

    def perform_update(self, serializer):
        return CustomerService.update(
            customer=self.get_object(),
            **serializer.validated_data
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("customers.view")]
        return [IsAuthenticated(), HasHotelPermission("customers.manage")]


@extend_schema_view(
    list=extend_schema(summary="List employees", tags=["Employees"]),
    create=extend_schema(summary="Create employee profile", tags=["Employees"]),
    update=extend_schema(summary="Update employee", tags=["Employees"]),
    destroy=extend_schema(summary="Deactivate employee", tags=["Employees"]),
)
class EmployeeViewSet(viewsets.ModelViewSet):
    """Hotel staff management."""
    permission_classes = [IsAuthenticated, IsHotelMember]
    filter_backends = [DjangoFilterBackend, OrderingFilter]
    filterset_fields = ["department", "is_active"]
    ordering_fields = ["hire_date", "created_at"]

    def get_serializer_class(self):
        if self.action in ["create", "update", "partial_update"]:
            return EmployeeWriteSerializer
        return EmployeeSerializer

    def get_queryset(self):
        return get_employees(
            hotel=self.request.hotel,
            department=self.request.query_params.get("department"),
        )

    def perform_create(self, serializer):
        data = serializer.validated_data
        return EmployeeService.create(
            hotel=self.request.hotel,
            user=data["user"],
            position=data.get("position", ""),
            department=data.get("department", "front_desk"),
            employee_id=data.get("employee_id", ""),
            hire_date=data.get("hire_date"),
            notes=data.get("notes", ""),
        )

    def perform_update(self, serializer):
        return EmployeeService.update(
            employee=self.get_object(),
            **serializer.validated_data
        )

    def get_permissions(self):
        if self.action in ["list", "retrieve"]:
            return [IsAuthenticated(), HasHotelPermission("customers.view")]
        return [IsAuthenticated(), HasHotelPermission("customers.manage")]
