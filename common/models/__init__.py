# common/models/__init__.py
# يُصدِّر الـ models الأساسية لسهولة الاستيراد
from .base import (
    UUIDModel,
    TimeStampedModel,
    ActiveModel,
    HotelOwnedMixin,
    BaseModel,
    SoftDeleteModel,
)
from .managers import TenantManager, TenantQuerySet

__all__ = [
    "UUIDModel",
    "TimeStampedModel",
    "ActiveModel",
    "HotelOwnedMixin",
    "BaseModel",
    "SoftDeleteModel",
    "TenantManager",
    "TenantQuerySet",
]
