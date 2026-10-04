# Phase 7 Endpoints — Housekeeping + Maintenance + Complaints

Base URL: `http://localhost:8000/api/v1/`
Auth: `Authorization: Bearer <access_token>` + `X-Hotel-ID: <hotel_uuid>`

---

## 🧹 Housekeeping (Cleaning Tasks)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/housekeeping/cleanings/` | ✅ JWT | housekeeping.view | List cleaning tasks |
| POST | `/housekeeping/cleanings/` | ✅ JWT | housekeeping.manage | Create cleaning task manually |
| GET | `/housekeeping/cleanings/{id}/` | ✅ JWT | housekeeping.view | Get task detail |
| PATCH | `/housekeeping/cleanings/{id}/action/` | ✅ JWT | housekeeping.manage | Perform cleaning action |

> ⚠️ Cleaning tasks are **auto-created** when a reservation is checked out. Manual creation is also supported.

**Filter Params:** `?status=pending`, `?room=uuid`

### PATCH `/housekeeping/cleanings/{id}/action/` — Cleaning Workflow
```json
{
  "action": "start"
}
```
Actions:
- `start` → `pending` → `in_progress`
- `complete` → `in_progress` → `completed`
- `inspect` → `completed` → `inspected` + Room.status → `available`

**Response (400 — blocking issue on room):**
```json
{
  "error": "Room 101 cannot be marked as AVAILABLE while it has open blocking maintenance issues."
}
```

**Cleaning Workflow:**
```
[AUTO CREATED on checkout]
pending → start → in_progress → complete → completed → inspect → inspected
                                                                     ↓
                                                         Room.status = AVAILABLE
                                          (only if no blocking RoomIssue exists)
```

---

## 🔧 Maintenance (Room Issues)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/maintenance/issues/` | ✅ JWT | maintenance.view | List room issues |
| POST | `/maintenance/issues/` | ✅ JWT | maintenance.manage | Report room issue |
| GET | `/maintenance/issues/{id}/` | ✅ JWT | maintenance.view | Get issue detail |
| PATCH | `/maintenance/issues/{id}/` | ✅ JWT | maintenance.manage | Update issue |
| DELETE | `/maintenance/issues/{id}/` | ✅ JWT | maintenance.manage | Delete issue |
| PATCH | `/maintenance/issues/{id}/resolve/` | ✅ JWT | maintenance.manage | Mark as resolved |
| PATCH | `/maintenance/issues/{id}/assign/` | ✅ JWT | maintenance.manage | Assign to employee |

**Filter Params:** `?status=open`, `?priority=critical`, `?blocking=true`, `?room=uuid`

### POST `/maintenance/issues/` — Report Issue
```json
{
  "room": "uuid-of-room",
  "title": "AC not working",
  "description": "Air conditioning unit making loud noise and not cooling",
  "priority": "high",
  "blocking": true,
  "assigned_to": "uuid-of-employee"
}
```

Priority values: `low`, `medium`, `high`, `critical`

> ⚠️ **If `blocking=true`** — Room cannot be marked `available` until this issue is resolved.
> ⚠️ **If `priority=high` or `critical`** — Celery task fires immediately to notify management.

### PATCH `/maintenance/issues/{id}/resolve/`
```json
{
  "notes": "Replaced AC unit, tested and working"
}
```

### PATCH `/maintenance/issues/{id}/assign/`
```json
{
  "employee_id": "uuid-of-employee"
}
```
**Side Effect:** Issue status changes `open` → `in_progress`.

---

## 📋 Complaints

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/complaints/complaints/` | ✅ JWT | complaints.view | List complaints |
| POST | `/complaints/complaints/` | ✅ JWT | complaints.manage | Create complaint |
| GET | `/complaints/complaints/{id}/` | ✅ JWT | complaints.view | Get complaint detail |
| PATCH | `/complaints/complaints/{id}/` | ✅ JWT | complaints.manage | Update complaint |
| DELETE | `/complaints/complaints/{id}/` | ✅ JWT | complaints.manage | Delete complaint |
| PATCH | `/complaints/complaints/{id}/resolve/` | ✅ JWT | complaints.manage | Resolve complaint |
| PATCH | `/complaints/complaints/{id}/assign/` | ✅ JWT | complaints.manage | Assign to employee |

**Filter Params:** `?status=open`, `?priority=high`, `?category=Noise`

### POST `/complaints/complaints/`
```json
{
  "customer": "uuid-of-customer",
  "reservation": "uuid-of-reservation",
  "category": "Noise",
  "title": "Loud neighbors on floor 3",
  "description": "Guests in room 301 are very loud after midnight",
  "priority": "high",
  "assigned_to": "uuid-of-employee"
}
```

### PATCH `/complaints/complaints/{id}/resolve/`
```json
{
  "resolution_notes": "Spoke with guests in 301. Issue resolved."
}
```

**Complaint Lifecycle:**
```
open → assign → in_progress → resolve → resolved → (manually) → closed
```

---

## 🔔 Notifications (Maintenance Signal)

When a `RoomIssue` is created with `priority=high` or `priority=critical`:
1. Django `post_save` signal fires
2. Celery task `notify_high_priority_issue` is queued (decoupled from request)
3. Task logs the notification (Phase 8 will add real channels: In-App, Email, SMS)

The request completes immediately — notification is async.

**Signal Architecture:**
```
POST /maintenance/issues/ (priority=critical)
        ↓
RoomIssue.objects.create()
        ↓
post_save signal → maintenance.signals.on_room_issue_created()
        ↓
notify_high_priority_issue.delay(issue_id)  ← async, decoupled
        ↓
[background] Celery worker → log + (Phase 8: notify managers)
```
