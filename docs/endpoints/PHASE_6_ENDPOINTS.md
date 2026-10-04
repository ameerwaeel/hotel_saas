# Phase 6 Endpoints — Payments + Finance + Closings

Base URL: `http://localhost:8000/api/v1/`
Auth: `Authorization: Bearer <access_token>` + `X-Hotel-ID: <hotel_uuid>`

> ⚠️ **Golden Rule:** All money amounts are `DecimalField` — never `float`. Never SUM across currencies.

---

## 💳 Payment Methods

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/payments/methods/` | ✅ JWT | payments.view | List payment methods |
| POST | `/payments/methods/` | ✅ JWT | payments.manage | Create payment method |
| GET | `/payments/methods/{id}/` | ✅ JWT | payments.view | Get detail |
| PUT/PATCH | `/payments/methods/{id}/` | ✅ JWT | payments.manage | Update |
| DELETE | `/payments/methods/{id}/` | ✅ JWT | payments.manage | Deactivate |

### POST `/payments/methods/`
```json
{
  "name": "Visa Card",
  "type": "credit_card",
  "description": "Visa credit card terminal"
}
```
Types: `cash`, `credit_card`, `debit_card`, `bank_transfer`, `online`, `cheque`, `other`

---

## 💰 Payments

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/payments/` | ✅ JWT | payments.view | List payments |
| POST | `/payments/` | ✅ JWT | payments.manage | Record payment |
| GET | `/payments/{id}/` | ✅ JWT | payments.view | Get payment detail |
| POST | `/payments/{id}/refund/` | ✅ JWT | payments.manage | Refund payment |

### POST `/payments/`
```json
{
  "reservation": "uuid-of-reservation",
  "method": "uuid-of-payment-method",
  "amount": "500.00",
  "currency": "USD",
  "payment_date": "2026-10-15",
  "reference": "TXN-001",
  "notes": "Partial payment"
}
```

**Side Effects:** Automatically creates a `FinancialTransaction` (income) for the same amount.

**Response (400 — date is closed):**
```json
{
  "error": "Business date 2026-10-15 is already closed. No financial transactions can be added or modified."
}
```

### POST `/payments/{id}/refund/`
```json
{
  "reason": "Customer cancelled reservation"
}
```

---

## 📊 Finance

### Daily Summary
| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/finance/daily-summary/` | ✅ JWT | finance.view | Get daily summary by currency |

### GET `/finance/daily-summary/?date=2026-10-15`
```json
{
  "date": "2026-10-15",
  "closing_status": "open",
  "summary_by_currency": {
    "USD": {
      "income": "1500.00",
      "expense": "300.00",
      "net": "1200.00"
    },
    "EUR": {
      "income": "200.00",
      "expense": "0.00",
      "net": "200.00"
    }
  }
}
```

---

### Finance Categories
| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/finance/categories/` | ✅ JWT | finance.view | List categories |
| POST | `/finance/categories/` | ✅ JWT | finance.manage | Create category |

### POST `/finance/categories/`
```json
{
  "name": "Utilities",
  "type": "expense",
  "description": "Electricity, water, etc."
}
```

---

### Financial Transactions
| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/finance/transactions/` | ✅ JWT | finance.view | List transactions |
| POST | `/finance/transactions/` | ✅ JWT | finance.manage | Create expense/adjustment transaction |

> Income transactions are auto-created by PaymentService — do not create manually.

### POST `/finance/transactions/`
```json
{
  "type": "expense",
  "category": "uuid-of-category",
  "amount": "150.00",
  "currency": "USD",
  "method": "uuid-of-payment-method",
  "transaction_date": "2026-10-15",
  "notes": "Electricity bill"
}
```

---

### Exchange Rates
| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/finance/exchange-rates/` | ✅ JWT | finance.manage | List exchange rates |
| POST | `/finance/exchange-rates/` | ✅ JWT | finance.manage | Create rate |

### POST `/finance/exchange-rates/`
```json
{
  "from_currency": "EUR",
  "to_currency": "USD",
  "rate": "1.081234",
  "effective_date": "2026-10-15"
}
```

---

## 🔒 Daily Closing

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/finance/daily-closings/` | ✅ JWT | finance.view | List closings |
| POST | `/finance/daily-closings/` | ✅ JWT | finance.manage | Close business day |
| GET | `/finance/daily-closings/{id}/` | ✅ JWT | finance.view | Get detail |

### POST `/finance/daily-closings/` — Close Day
```json
{
  "business_date": "2026-10-15",
  "notes": "End of day closing"
}
```

**Response (201):**
```json
{
  "id": "uuid",
  "business_date": "2026-10-15",
  "status": "closed",
  "total_income": "2500.00",
  "total_expense": "450.00",
  "net": "2050.00",
  "closed_at": "2026-10-15T23:00:00Z"
}
```

**Response (400 — already closed):**
```json
{
  "error": "Business date 2026-10-15 is already closed."
}
```

---

## 📆 Monthly Closing

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| GET | `/finance/monthly-closings/` | ✅ JWT | finance.manage | List monthly closings |
| POST | `/finance/monthly-closings/` | ✅ JWT | finance.manage | Close month |

### POST `/finance/monthly-closings/`
```json
{
  "year": 2026,
  "month": 9
}
```

---

## 📤 Financial Report Export (Async)

| Method | Endpoint | Auth | Permission | Description |
|--------|----------|------|-----------|-------------|
| POST | `/finance/export/` | ✅ JWT | finance.manage | Queue report export |

### POST `/finance/export/`
```json
{
  "year": 2026,
  "month": 10,
  "report_type": "pdf"
}
```

**Response (202 Accepted):**
```json
{
  "task_id": "celery-task-uuid",
  "status": "queued",
  "message": "Report generation started. Poll task status for result."
}
```

> Frontend should poll Celery task status endpoint. Full PDF/Excel generation requires Phase 8 (WeasyPrint/openpyxl).
