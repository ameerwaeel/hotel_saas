# Phase 5 Endpoints — Reservations + Availability Engine

Base URL: `http://localhost:8000/api/v1/`
Auth: `Authorization: Bearer <access_token>` + `X-Hotel-ID: <hotel_uuid>`

---

## 🔍 Availability Check

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/reservations/availability/` | ✅ JWT | Hotel member | Check available rooms for dates |

### GET `/reservations/availability/`
**Query Params:**
- `check_in=2026-10-15` (required)
- `check_out=2026-10-18` (required)
- `room_type_id=uuid` (optional)

**Response:**
```json
{
  "check_in": "2026-10-15",
  "check_out": "2026-10-18",
  "count": 3,
  "available_rooms": [
    {
      "id": "uuid",
      "room_number": "101",
      "floor": 1,
      "status": "available",
      "room_type": {
        "id": "uuid",
        "code": "DLX",
        "base_price": "200.00"
      }
    }
  ]
}
```

> **Algorithm:** Overlap query — finds all rooms NOT in reservations where `check_in < requested_checkout AND check_out > requested_checkin`. Uses composite index `(room_id, check_in, check_out)`.

---

## 📅 Reservations

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/reservations/` | ✅ JWT | reservations.view | List reservations |
| POST | `/reservations/` | ✅ JWT | reservations.manage | Create reservation |
| GET | `/reservations/{id}/` | ✅ JWT | reservations.view | Get reservation detail |
| PATCH | `/reservations/{id}/` | ✅ JWT | reservations.manage | Update reservation info |
| DELETE | `/reservations/{id}/` | ✅ JWT | reservations.manage | Cancel reservation |
| PATCH | `/reservations/{id}/status/` | ✅ JWT | reservations.manage | Transition status |
| POST | `/reservations/{id}/upgrade-room/` | ✅ JWT | reservations.manage | Upgrade/change room |

**List Query Params:** `?status=confirmed`, `?customer=uuid`, `?check_in_from=2026-10-01`, `?check_in_to=2026-10-31`

### POST `/reservations/` — Create Reservation
```json
{
  "customer": "uuid-of-customer",
  "booking_source": "uuid-of-booking-source",
  "check_in": "2026-10-15",
  "check_out": "2026-10-18",
  "adults": 2,
  "children": 1,
  "currency": "USD",
  "special_requests": "High floor preferred",
  "internal_notes": "VIP guest",
  "rooms": [
    {
      "room_id": "uuid-of-room",
      "adults": 2,
      "children": 1,
      "notes": ""
    }
  ]
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "status": "pending",
  "check_in": "2026-10-15",
  "check_out": "2026-10-18",
  "nights": 3,
  "total_price": "600.00",
  "currency": "USD",
  "customer_name": "Ahmed Hassan",
  "reservation_rooms": [...]
}
```

**Response (400 — room unavailable):**
```json
{
  "error": "Room 101 is not available for the selected dates."
}
```

### PATCH `/reservations/{id}/status/` — State Machine Transition
```json
{
  "action": "confirm",
  "reason": ""
}
```
Actions: `confirm`, `cancel`, `check_in`, `check_out`, `no_show`

**State Machine:**
```
pending    → confirm   → confirmed
pending    → cancel    → cancelled
confirmed  → check_in  → checked_in  (Room.status = OCCUPIED)
confirmed  → cancel    → cancelled
confirmed  → no_show   → no_show
checked_in → check_out → checked_out (Room.status = CLEANING + RoomCleaning created)
```

**Response (400 — invalid transition):**
```json
{
  "error": "Cannot transition from 'pending' to 'checked_in'. Allowed: ['confirmed', 'cancelled']"
}
```

### POST `/reservations/{id}/upgrade-room/` — Room Upgrade
```json
{
  "reservation_room_id": "uuid-of-reservation-room",
  "new_room_id": "uuid-of-new-room",
  "reason": "Guest requested upgrade"
}
```

**Behavior:**
- Validates new room is available for same dates
- Creates `ReservationRoomChange` history record
- Updates `nightly_price` snapshot
- Recalculates `Reservation.total_price`

**Response (400 — new room unavailable):**
```json
{
  "error": "New room is not available for the reservation dates."
}
```
