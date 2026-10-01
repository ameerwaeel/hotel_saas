"""
accounts/signals.py
====================
المسار: accounts/signals.py
الوظيفة: Django Signals لمسح cache الصلاحيات عند تغيير Role أو RolePermission.

المشكلة التي تحلها:
  صلاحيات المستخدم تُخزَّن في cache بـ key "perms:{user_id}:{hotel_id}".
  عند تغيير Role أو RolePermission، يجب مسح الـ cache المرتبط.

  بدون هذا الـ signals:
    - تغيير دور موظف → لا يزال الموظف بنفس الصلاحيات القديمة لمدة 5 دقائق ⚠️
    - حذف صلاحية من دور → لا يزال الأعضاء يملكونها لمدة 5 دقائق ⚠️

الـ Signals:
  1. HotelMembership post_save → invalidate cache عند تغيير role
  2. RolePermission post_save → invalidate cache لكل أعضاء الـ role
  3. RolePermission post_delete → invalidate cache لكل أعضاء الـ role

⚠️ تحذير: تجنب Signals المتشابكة (signal بينده signal).
   هنا كل signal تستدعي دالة مباشرة (invalidate_permission_cache)
   وليس signal أخرى.

⚠️ تسجيل الـ signals في accounts/apps.py:
    def ready(self):
        import accounts.signals  # noqa
"""

import logging
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from common.permissions.hotel_permissions import invalidate_permission_cache

logger = logging.getLogger("hotel_saas")


@receiver(post_save, sender="accounts.HotelMembership")
def invalidate_cache_on_membership_change(sender, instance, created, **kwargs):
    """
    يُمسح cache الصلاحيات عند تغيير HotelMembership.

    يُفعَّل عند:
        - تغيير role المستخدم في فندق
        - تغيير status العضوية (active/inactive)
        - إنشاء عضوية جديدة

    Args:
        sender: HotelMembership class
        instance: HotelMembership instance المُعدَّل
        created: True إذا كان إنشاء جديد
    """
    user_id = instance.user_id
    hotel_id = instance.hotel_id

    invalidate_permission_cache(user_id, hotel_id)
    logger.info(
        "Permission cache invalidated due to membership change",
        extra={
            "user_id": str(user_id),
            "hotel_id": str(hotel_id),
            "is_created": created,
        },
    )


@receiver(post_save, sender="accounts.RolePermission")
def invalidate_cache_on_role_permission_add(sender, instance, created, **kwargs):
    """
    يُمسح cache الصلاحيات لكل أعضاء الـ Role عند إضافة صلاحية جديدة.

    ⚠️ N+1 المحتمل هنا:
        لكل عضو في الـ Role → invalidate cache بشكل منفصل.
        الحل: query واحدة لجلب كل الأعضاء ثم مسح الـ cache في loop.
        هذا مقبول لأن تغيير الصلاحيات نادر الحدوث.

    Args:
        sender: RolePermission class
        instance: RolePermission instance الجديد/المُعدَّل
        created: True إذا كان إنشاء جديد
    """
    _invalidate_role_members_cache(instance.role)


@receiver(post_delete, sender="accounts.RolePermission")
def invalidate_cache_on_role_permission_remove(sender, instance, **kwargs):
    """
    يُمسح cache الصلاحيات لكل أعضاء الـ Role عند حذف صلاحية.

    Args:
        sender: RolePermission class
        instance: RolePermission instance المحذوف
    """
    _invalidate_role_members_cache(instance.role)


def _invalidate_role_members_cache(role):
    """
    مسح cache صلاحيات كل أعضاء دور معين.

    Args:
        role: Role instance
    """
    try:
        from accounts.models import HotelMembership
        memberships = HotelMembership.objects.filter(
            role=role,
            status="active",
        ).values_list("user_id", "hotel_id")

        for user_id, hotel_id in memberships:
            invalidate_permission_cache(user_id, hotel_id)

        logger.info(
            "Permission cache invalidated for all role members",
            extra={
                "role_id": str(role.id),
                "role_name": role.name,
                "members_count": len(list(memberships)),
            },
        )
    except Exception as e:
        logger.error(
            "Failed to invalidate permission cache for role",
            extra={"role_id": str(role.id), "error": str(e)},
        )
