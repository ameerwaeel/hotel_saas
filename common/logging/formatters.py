"""
common/logging/formatters.py
==============================
المسار: common/logging/formatters.py
الوظيفة: JSON Formatter للـ structured logging في Production.
         كل log entry يُحوَّل لـ JSON مع:
           - timestamp
           - level
           - message
           - request_id (إذا وجد)
           - module / function
           - traceback (للأخطاء)

لماذا JSON Logging؟
  - يُسهِّل استيعاب الـ logs في أنظمة مثل ELK Stack, Datadog, CloudWatch
  - يمكن الـ query بـ structured fields (مثلاً: filter by request_id)
  - يُصبح ضرورياً في Phase 12 (Monitoring + Production hardening)

مُسجَّل في settings LOGGING formatters:
  'json': {'()': 'common.logging.formatters.JSONFormatter'}
"""

import json
import logging
import traceback
from datetime import datetime, timezone


class JSONFormatter(logging.Formatter):
    """
    Formatter يحوِّل log records إلى JSON.

    الـ output:
    {
        "timestamp": "2025-01-01T12:00:00.000Z",
        "level": "ERROR",
        "logger": "hotel_saas.rooms",
        "message": "Database query failed",
        "module": "selectors",
        "function": "get_available_rooms",
        "line": 42,
        "request_id": "550e8400-...",
        "exception": "Traceback (most recent call last):..."
    }

    Args:
        logging.Formatter: Base formatter class
    """

    def format(self, record: logging.LogRecord) -> str:
        """
        تحويل LogRecord إلى JSON string.

        Args:
            record: LogRecord من الـ logging system

        Returns:
            JSON string
        """
        log_data = {
            "timestamp": datetime.fromtimestamp(record.created, tz=timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # إضافة extra fields (مثل request_id, hotel_id, user_id)
        if hasattr(record, "request_id"):
            log_data["request_id"] = record.request_id
        if hasattr(record, "hotel_id"):
            log_data["hotel_id"] = record.hotel_id
        if hasattr(record, "user_id"):
            log_data["user_id"] = record.user_id
        if hasattr(record, "path"):
            log_data["path"] = record.path
        if hasattr(record, "status_code"):
            log_data["status_code"] = record.status_code
        if hasattr(record, "error_code"):
            log_data["error_code"] = record.error_code

        # إضافة traceback للأخطاء
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)
        elif record.exc_text:
            log_data["exception"] = record.exc_text

        return json.dumps(log_data, ensure_ascii=False, default=str)
