"""
reservations/models.py
======================
المسار: reservations/models.py
Phase: 5 — Reservations + Availability Engine + Room Upgrade

Models:
  ┌──────────────────────────────────────────────────────────────────────┐
  │  Reservation           → حجز رئيسي (customer + hotel + dates)        │
  │  ReservationRoom       → غرفة ضمن حجز (with price snapshot)          │
  │  ReservationRoomChange → سجل تغيير الغرفة أو الترقية                │
  └──────────────────────────────────────────────────────────────────────┘

مشاكل Django المحلولة:
  1. Overlap Query بدل per-day table → Composite index (room_id, check_in, check_out)
  2. Race Condition → select_for_update() + transaction.atomic() في ReservationService
  3. N+1 في list → select_related + prefetch_related multi-level
  4. Price Snapshot → DecimalField (أبداً FloatField للأموال)
  5. State Machine → ReservationStatus مع valid transitions في Service Layer
"""

from django.db import models
from django.utils.translation import gettext_lazy as _
from common.models.base import BaseModel, HotelOwnedMixin, SoftDeleteModel
from common.models.managers import TenantManager


# ---------------------------------------------------------------------------
# Reservation Status — State Machine
# ---------------------------------------------------------------------------

class ReservationStatus(models.TextChoices):
    """
    حالات الحجز — State Machine.
    Transitions صالحة (تُطبَّق في Service Layer):
      pending   → confirmed, cancelled
      confirmed → checked_in, cancelled, no_show
      checked_in → checked_out
      checked_out → (terminal state)
      cancelled → (terminal state)
      no_show → (terminal state)
    """
    PENDING = "pending", _("Pending")
    CONFIRMED = "confirmed", _("Confirmed")
    CHECKED_IN = "checked_in", _("Checked In")
    CHECKED_OUT = "checked_out", _("Checked Out")
    CANCELLED = "cancelled", _("Cancelled")
    NO_SHOW = "no_show", _("No Show")


# Valid state transitions (enforced in ReservationService)
VALID_TRANSITIONS = {
    ReservationStatus.PENDING: [ReservationStatus.CONFIRMED, ReservationStatus.CANCELLED],
    ReservationStatus.CONFIRMED: [ReservationStatus.CHECKED_IN, ReservationStatus.CANCELLED, ReservationStatus.NO_SHOW],
    ReservationStatus.CHECKED_IN: [ReservationStatus.CHECKED_OUT],
    ReservationStatus.CHECKED_OUT: [],
    ReservationStatus.CANCELLED: [],
    ReservationStatus.NO_SHOW: [],
}


# ---------------------------------------------------------------------------
# Reservation — main booking record
# ---------------------------------------------------------------------------

class Reservation(BaseModel, HotelOwnedMixin):
    """
    الحجز الرئيسي — يربط العميل بالفندق والتواريخ.

    ⚠️ N+1 في قائمة الحجوزات:
       Reservation.objects
           .select_related("customer", "booking_source", "created_by")
           .prefetch_related("reservation_rooms__room__room_type")

    ⚠️ Decimal للأسعار — لا FloatField.

    Fields:
        hotel: FK للفندق
        customer: FK للعميل
        booking_source: FK لمصدر الحجز
        status: حالة الحجز
        check_in: تاريخ الوصول
        check_out: تاريخ المغادرة
        adults: عدد البالغين
        children: عدد الأطفال
        total_price: السعر الإجمالي (snapshot)
        special_requests: طلبات خاصة
        internal_notes: ملاحظات داخلية
        created_by: من أنشأ الحجز
        confirmed_at: وقت التأكيد
        cancelled_at: وقت الإلغاء
        cancellation_reason: سبب الإلغاء
    """

    objects = TenantManager()

    customer = models.ForeignKey(
        "customers.Customer",
        on_delete=models.PROTECT,
        related_name="reservations",
        db_index=True,
        verbose_name=_("Customer"),
    )
    booking_source = models.ForeignKey(
        "rooms.BookingSource",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reservations",
        verbose_name=_("Booking Source"),
    )
    status = models.CharField(
        max_length=20,
        choices=ReservationStatus.choices,
        default=ReservationStatus.PENDING,
        db_index=True,
        verbose_name=_("Status"),
    )
    check_in = models.DateField(
        db_index=True,
        verbose_name=_("Check-in Date"),
    )
    check_out = models.DateField(
        db_index=True,
        verbose_name=_("Check-out Date"),
    )
    adults = models.PositiveSmallIntegerField(
        default=1,
        verbose_name=_("Adults"),
    )
    children = models.PositiveSmallIntegerField(
        default=0,
        verbose_name=_("Children"),
    )
    total_price = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        default=0,
        verbose_name=_("Total Price"),
        help_text="Price snapshot at booking time — DecimalField (never Float)",
    )
    currency = models.CharField(
        max_length=3,
        default="USD",
        verbose_name=_("Currency"),
        help_text="ISO 4217 currency code",
    )
    special_requests = models.TextField(
        blank=True,
        verbose_name=_("Special Requests"),
    )
    internal_notes = models.TextField(
        blank=True,
        verbose_name=_("Internal Notes"),
    )
    created_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="created_reservations",
        verbose_name=_("Created By"),
    )
    confirmed_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Confirmed At"))
    checked_in_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Checked In At"))
    checked_out_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Checked Out At"))
    cancelled_at = models.DateTimeField(null=True, blank=True, verbose_name=_("Cancelled At"))
    cancellation_reason = models.TextField(blank=True, verbose_name=_("Cancellation Reason"))

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Reservation")
        verbose_name_plural = _("Reservations")
        indexes = [
            models.Index(fields=["hotel", "status"], name="idx_reservation_hotel_status"),
            models.Index(fields=["hotel", "check_in", "check_out"], name="idx_reservation_hotel_dates"),
            models.Index(fields=["hotel", "customer"], name="idx_reservation_hotel_customer"),
        ]

    def __str__(self) -> str:
        return f"Res #{str(self.id)[:8]} — {self.customer} ({self.check_in} → {self.check_out})"

    @property
    def nights(self) -> int:
        """عدد الليالي."""
        return (self.check_out - self.check_in).days


# ---------------------------------------------------------------------------
# ReservationRoom — individual room within a reservation
# ---------------------------------------------------------------------------

class ReservationRoom(BaseModel, HotelOwnedMixin, SoftDeleteModel):
    """
    غرفة محددة داخل حجز معين (مع snapshot للسعر).

    ⚠️ SoftDeleteModel — لا نحذف سجلات مالية (ممنوع حذف ReservationRoom نهائياً).
    
    ⚠️ Composite Index (room_id, check_in, check_out):
       أهم index في المشروع للـ Availability overlap query.

    ⚠️ Price Snapshot: nightly_price يُحفظ وقت الحجز — لا يتغير مع تغيير RoomType.base_price.

    Fields:
        reservation: FK للحجز الرئيسي
        room: الغرفة المحجوزة (FK لـ Room)
        room_type: نوع الغرفة وقت الحجز (snapshot)
        check_in, check_out: تواريخ هذه الغرفة تحديداً
        nightly_price: سعر الليلة وقت الحجز (snapshot)
        nights: عدد الليالي
        adults, children: التوزيع في هذه الغرفة
    """

    objects = TenantManager()

    reservation = models.ForeignKey(
        Reservation,
        on_delete=models.CASCADE,
        related_name="reservation_rooms",
        db_index=True,
        verbose_name=_("Reservation"),
    )
    room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.PROTECT,
        related_name="reservation_rooms",
        db_index=True,
        verbose_name=_("Room"),
    )
    room_type = models.ForeignKey(
        "rooms.RoomType",
        on_delete=models.PROTECT,
        related_name="reservation_rooms",
        verbose_name=_("Room Type (snapshot)"),
        help_text="Snapshot of room type at booking time",
    )
    check_in = models.DateField(verbose_name=_("Check-in Date"))
    check_out = models.DateField(verbose_name=_("Check-out Date"))
    nightly_price = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        verbose_name=_("Nightly Price (snapshot)"),
        help_text="Price per night at booking time — immutable snapshot",
    )
    nights = models.PositiveSmallIntegerField(
        verbose_name=_("Nights"),
    )
    adults = models.PositiveSmallIntegerField(default=1, verbose_name=_("Adults"))
    children = models.PositiveSmallIntegerField(default=0, verbose_name=_("Children"))
    notes = models.TextField(blank=True, verbose_name=_("Notes"))

    class Meta(BaseModel.Meta, HotelOwnedMixin.Meta):
        verbose_name = _("Reservation Room")
        verbose_name_plural = _("Reservation Rooms")
        indexes = [
            # ⚠️ أهم composite index في المشروع — Availability Overlap Query
            models.Index(
                fields=["room", "check_in", "check_out"],
                name="idx_resroom_room_dates",
            ),
            models.Index(
                fields=["reservation"],
                name="idx_resroom_reservation",
            ),
        ]

    def __str__(self) -> str:
        return f"Room {self.room.room_number} in Res #{str(self.reservation_id)[:8]}"

    @property
    def total_price(self):
        """السعر الإجمالي لهذه الغرفة."""
        return self.nightly_price * self.nights


# ---------------------------------------------------------------------------
# ReservationRoomChange — room upgrade/change history
# ---------------------------------------------------------------------------

class ReservationRoomChange(models.Model):
    """
    سجل تاريخي لتغيير/ترقية غرفة داخل حجز.
    لا يرث BaseModel — لا يحتاج UUID أو is_active.

    Fields:
        reservation_room: ReservationRoom التي تغيرت
        old_room: الغرفة القديمة
        new_room: الغرفة الجديدة
        old_price: السعر القديم
        new_price: السعر الجديد
        price_difference: الفرق في السعر
        reason: سبب التغيير
        changed_by: من أجرى التغيير
        changed_at: وقت التغيير
    """

    reservation_room = models.ForeignKey(
        ReservationRoom,
        on_delete=models.CASCADE,
        related_name="changes",
        verbose_name=_("Reservation Room"),
    )
    old_room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.SET_NULL,
        null=True,
        related_name="old_reservation_changes",
        verbose_name=_("Old Room"),
    )
    new_room = models.ForeignKey(
        "rooms.Room",
        on_delete=models.SET_NULL,
        null=True,
        related_name="new_reservation_changes",
        verbose_name=_("New Room"),
    )
    old_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Old Nightly Price")
    )
    new_price = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("New Nightly Price")
    )
    price_difference = models.DecimalField(
        max_digits=10, decimal_places=2, verbose_name=_("Price Difference")
    )
    reason = models.TextField(blank=True, verbose_name=_("Reason"))
    changed_by = models.ForeignKey(
        "accounts.User",
        on_delete=models.SET_NULL,
        null=True,
        related_name="room_changes",
        verbose_name=_("Changed By"),
    )
    changed_at = models.DateTimeField(auto_now_add=True, verbose_name=_("Changed At"))

    class Meta:
        verbose_name = _("Reservation Room Change")
        verbose_name_plural = _("Reservation Room Changes")
        ordering = ["-changed_at"]

    def __str__(self) -> str:
        return f"Change: {self.old_room} → {self.new_room} (Δ{self.price_difference})"
