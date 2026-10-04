# Phase 4 Endpoints — Master Data (Rooms + Customers)

Base URL: `http://localhost:8000/api/v1/`
Auth: `Authorization: Bearer <access_token>`
Tenant Header: `X-Hotel-ID: <hotel_uuid>` (Required for hotel-scoped endpoints — NOT needed for Global Languages)

---

## 🏨 Languages (Global)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/rooms/languages/` | ✅ JWT | Any member | List all active languages |
| POST | `/rooms/languages/` | ✅ JWT | Platform Admin | Create new language |
| GET | `/rooms/languages/{id}/` | ✅ JWT | Any member | Get language detail |
| DELETE | `/rooms/languages/{id}/` | ✅ JWT | Platform Admin | Delete language |

### POST `/rooms/languages/`
```json
{
  "code": "ar",
  "name": "Arabic",
  "native_name": "العربية",
  "is_rtl": true
}
```

---

## 🌍 Hotel Languages

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/rooms/hotel-languages/` | ✅ JWT | Hotel member | List hotel's languages |
| POST | `/rooms/hotel-languages/` | ✅ JWT | Hotel member | Add language to hotel |
| DELETE | `/rooms/hotel-languages/{id}/` | ✅ JWT | Hotel member | Remove language from hotel |

### POST `/rooms/hotel-languages/`
```json
{
  "language_code": "ar",
  "is_default": true
}
```

---

## 📋 Booking Sources

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/rooms/booking-sources/` | ✅ JWT | Hotel member | List booking sources |
| POST | `/rooms/booking-sources/` | ✅ JWT | Hotel member | Create booking source |
| GET | `/rooms/booking-sources/{id}/` | ✅ JWT | Hotel member | Get detail |
| PUT/PATCH | `/rooms/booking-sources/{id}/` | ✅ JWT | Hotel member | Update |
| DELETE | `/rooms/booking-sources/{id}/` | ✅ JWT | Hotel member | Delete |

### POST `/rooms/booking-sources/`
```json
{
  "name": "Booking.com",
  "is_online": true,
  "commission_rate": "15.00",
  "description": "Online booking platform"
}
```

---

## 🛏️ Room Types

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/rooms/room-types/` | ✅ JWT | rooms.view | List room types with translations |
| POST | `/rooms/room-types/` | ✅ JWT | rooms.manage | Create room type |
| GET | `/rooms/room-types/{id}/` | ✅ JWT | rooms.view | Get detail with translations |
| PUT/PATCH | `/rooms/room-types/{id}/` | ✅ JWT | rooms.manage | Update |
| DELETE | `/rooms/room-types/{id}/` | ✅ JWT | rooms.manage | Delete |

### POST `/rooms/room-types/`
```json
{
  "code": "DLX",
  "base_price": "200.00",
  "max_occupancy": 3,
  "sort_order": 2,
  "translations": [
    {"language_code": "en", "name": "Deluxe Room", "description": "Spacious deluxe room"},
    {"language_code": "ar", "name": "غرفة ديلوكس", "description": "غرفة واسعة وفاخرة"}
  ]
}
```

---

## 🚪 Rooms

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/rooms/rooms/` | ✅ JWT | rooms.view | List rooms (filter: status, room_type, floor) |
| POST | `/rooms/rooms/` | ✅ JWT | rooms.manage | Create room |
| GET | `/rooms/rooms/{id}/` | ✅ JWT | rooms.view | Get room detail |
| PUT/PATCH | `/rooms/rooms/{id}/` | ✅ JWT | rooms.manage | Update room |
| DELETE | `/rooms/rooms/{id}/` | ✅ JWT | rooms.manage | Deactivate room |
| PATCH | `/rooms/rooms/{id}/status/` | ✅ JWT | rooms.manage | Update room status |

### POST `/rooms/rooms/`
```json
{
  "room_type": "uuid-of-room-type",
  "room_number": "101",
  "floor": 1,
  "notes": ""
}
```

### PATCH `/rooms/rooms/{id}/status/`
```json
{
  "status": "available"
}
```
Status values: `available`, `occupied`, `cleaning`, `maintenance`, `out_of_order`

**Response 400 if blocking issue exists:**
```json
{
  "error": "Room 101 cannot be marked as AVAILABLE while it has open blocking maintenance issues."
}
```

---

## 👥 Customers

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/customers/customers/` | ✅ JWT | customers.view | List customers (search: ?search=Ahmed) |
| POST | `/customers/customers/` | ✅ JWT | customers.manage | Create customer |
| GET | `/customers/customers/{id}/` | ✅ JWT | customers.view | Get customer detail |
| PUT/PATCH | `/customers/customers/{id}/` | ✅ JWT | customers.manage | Update customer |
| DELETE | `/customers/customers/{id}/` | ✅ JWT | customers.manage | Deactivate customer |

### POST `/customers/customers/`
```json
{
  "first_name": "Ahmed",
  "last_name": "Hassan",
  "phone": "+201001234567",
  "email": "ahmed@example.com",
  "nationality": "EG",
  "id_type": "national_id",
  "id_number": "12345678901234",
  "date_of_birth": "1990-01-15",
  "vip_status": false
}
```

**Query Params:** `?search=Ahmed` (name/phone/email), `?vip_only=true`

---

## 👷 Employees

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/customers/employees/` | ✅ JWT | customers.view | List employees |
| POST | `/customers/employees/` | ✅ JWT | customers.manage | Create employee profile |
| GET | `/customers/employees/{id}/` | ✅ JWT | customers.view | Get employee detail |
| PUT/PATCH | `/customers/employees/{id}/` | ✅ JWT | customers.manage | Update employee |
| DELETE | `/customers/employees/{id}/` | ✅ JWT | customers.manage | Deactivate employee |

### POST `/customers/employees/`
```json
{
  "user": "uuid-of-user-with-active-membership",
  "employee_id": "EMP001",
  "position": "Front Desk Agent",
  "department": "front_desk",
  "hire_date": "2024-01-01"
}
```
Departments: `front_desk`, `housekeeping`, `maintenance`, `management`, `food_beverage`, `security`, `other`

> **⚠️ Important:** `user` must have an active `HotelMembership` for this hotel. Will raise 400 if not.
