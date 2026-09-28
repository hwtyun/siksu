"""식수체크 업무 규칙 (마감시간, 기본값, 집계 해석)."""

from __future__ import annotations

from datetime import date, datetime, time
from typing import Any

from config import (
    DINNER_DEADLINE,
    DINNER_SERVICE_END,
    DINNER_SERVICE_START,
    LUNCH_DEADLINE,
    LUNCH_SERVICE_END,
    LUNCH_SERVICE_START,
    MEAL_NO,
    MEAL_YES,
    METHOD_AUTO,
    METHOD_UNSUBMITTED,
    TZ,
    WEEKDAYS,
)


def now_kst() -> datetime:
    return datetime.now(TZ)


def today_kst() -> date:
    return now_kst().date()


def weekday_index(target: date | None = None) -> int:
    return (target or today_kst()).weekday()


def weekday_label(target: date | None = None) -> str:
    return WEEKDAYS[weekday_index(target)]


def is_past_deadline(deadline: time, target_date: date | None = None, now: datetime | None = None) -> bool:
    current = now or now_kst()
    day = target_date or today_kst()
    if day < current.date():
        return True
    if day > current.date():
        return False
    return current.time() >= deadline


def is_lunch_closed(target_date: date | None = None, now: datetime | None = None) -> bool:
    return is_past_deadline(LUNCH_DEADLINE, target_date, now)


def is_dinner_closed(target_date: date | None = None, now: datetime | None = None) -> bool:
    return is_past_deadline(DINNER_DEADLINE, target_date, now)


def is_lunch_service_ended(target_date: date | None = None, now: datetime | None = None) -> bool:
    return is_past_deadline(LUNCH_SERVICE_END, target_date, now)


def is_dinner_service_ended(target_date: date | None = None, now: datetime | None = None) -> bool:
    return is_past_deadline(DINNER_SERVICE_END, target_date, now)


def is_in_time_window(start: time, end: time, now: datetime | None = None) -> bool:
    current = now or now_kst()
    return start <= current.time() < end


def current_checkin_meal(now: datetime | None = None) -> str | None:
    if is_in_time_window(LUNCH_SERVICE_START, LUNCH_SERVICE_END, now):
        return "lunch"
    if is_in_time_window(DINNER_SERVICE_START, DINNER_SERVICE_END, now):
        return "dinner"
    return None


def meal_label(value: int | bool) -> str:
    return MEAL_YES if int(value) else MEAL_NO


def to_bool_int(value: Any) -> int:
    if isinstance(value, str):
        return 1 if value.strip() == MEAL_YES else 0
    return 1 if int(value) else 0


def default_meals_from_auto(auto_pattern: dict[str, int] | None) -> tuple[int, int]:
    if not auto_pattern:
        return 0, 0
    return int(auto_pattern["lunch"]), int(auto_pattern["dinner"])


def should_materialize(target_date: date, now: datetime | None = None) -> bool:
    """지난 날짜이거나, 오늘이면서 점심 마감이 지났으면 미제출 인원을 확정 기록한다."""
    current = now or now_kst()
    if target_date < current.date():
        return True
    if target_date > current.date():
        return False
    return is_lunch_closed(target_date, current)


def resolve_employee_application(
    employee: dict[str, Any],
    saved: dict[str, Any] | None,
    auto_pattern: dict[str, int] | None,
) -> dict[str, Any]:
    """저장된 신청이 있으면 그대로, 없으면 자동예약 또는 미제출(안 먹음)으로 해석한다."""
    if saved:
        return {
            "apply_date": saved["apply_date"],
            "employee_id": employee["id"],
            "name": employee["name"],
            "department": employee["department"],
            "affiliate": employee.get("affiliate") or "",
            "lunch": int(saved["lunch"]),
            "dinner": int(saved["dinner"]),
            "apply_method": saved["apply_method"],
            "submitted_at": saved.get("submitted_at"),
            "source": "saved",
        }

    lunch, dinner = default_meals_from_auto(auto_pattern)
    if auto_pattern is not None:
        method = METHOD_AUTO
    else:
        method = METHOD_UNSUBMITTED
        lunch, dinner = 0, 0

    return {
        "apply_date": None,
        "employee_id": employee["id"],
            "name": employee["name"],
            "department": employee["department"],
            "affiliate": employee.get("affiliate") or "",
            "lunch": lunch,
            "dinner": dinner,
        "apply_method": method,
        "submitted_at": None,
        "source": "resolved",
    }
