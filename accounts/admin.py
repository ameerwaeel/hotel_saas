"""
accounts/admin.py
==================
المسار: accounts/admin.py
الوظيفة: Django Admin configuration لـ User و RBAC models.
"""

from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as DjangoUserAdmin
from .models import User, HotelMembership, Role, Permission, RolePermission


@admin.register(User)
class UserAdmin(DjangoUserAdmin):
    list_display = ["email", "username", "full_name", "is_platform_admin", "is_active", "date_joined"]
    list_filter = ["is_platform_admin", "is_active", "is_staff"]
    search_fields = ["email", "username", "first_name", "last_name"]
    ordering = ["-date_joined"]
    readonly_fields = ["id", "date_joined", "last_login"]

    fieldsets = DjangoUserAdmin.fieldsets + (
        ("Hotel SaaS", {"fields": ("phone", "avatar", "is_platform_admin", "preferred_language")}),
    )
    add_fieldsets = DjangoUserAdmin.add_fieldsets + (
        ("Hotel SaaS", {"fields": ("email", "phone", "is_platform_admin")}),
    )


class RolePermissionInline(admin.TabularInline):
    model = RolePermission
    extra = 1
    autocomplete_fields = ["permission"]


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ["name", "hotel", "is_system_role", "created_at"]
    list_filter = ["is_system_role", "hotel"]
    search_fields = ["name", "hotel__name"]
    readonly_fields = ["id", "created_at", "updated_at"]
    inlines = [RolePermissionInline]


@admin.register(Permission)
class PermissionAdmin(admin.ModelAdmin):
    list_display = ["code", "name", "module"]
    list_filter = ["module"]
    search_fields = ["code", "name"]


@admin.register(HotelMembership)
class HotelMembershipAdmin(admin.ModelAdmin):
    list_display = ["user", "hotel", "role", "status", "joined_at"]
    list_filter = ["status", "hotel"]
    search_fields = ["user__email", "hotel__name"]
    readonly_fields = ["id", "joined_at", "created_at"]
    autocomplete_fields = ["user", "hotel", "role"]
