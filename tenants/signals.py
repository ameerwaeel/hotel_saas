"""
tenants/signals.py
===================
المسار: tenants/signals.py
الوظيفة: Django Signals لموديل الفندق.

الإشارة (post_save):
  تتيح التكليفات التلقائية فور إنشاء كائن Hotel جديد.
  تُنشئ كائن HotelSettings مرتبطاً بالفندق افتراضياً.
"""

from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import Hotel, HotelSettings


@receiver(post_save, sender=Hotel)
def create_hotel_settings_on_hotel_creation(sender, instance, created, **kwargs):
    """
    إنشاء HotelSettings تلقائياً فور تسجيل/إنشاء أي فندق جديد في النظام.

    Args:
        sender: موديل Hotel
        instance: كائن Hotel المُنشأ
        created: بولين يحدد هل هو إنشاء جديد (True) أم تعديل (False)
    """
    if created:
        HotelSettings.objects.get_or_create(hotel=instance)
