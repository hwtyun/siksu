"""식수체크 업무 규칙/집계 해석 검증."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import METHOD_AUTO, METHOD_UNSUBMITTED, TZ  # noqa: E402
from logic import (
    current_checkin_meal,
    is_dinner_closed,
    is_lunch_closed,
    meal_label,
    resolve_employee_application,
    should_materialize,
    to_bool_int,
    weekday_label,
)


def test_deadlines() -> None:
    day = date(2026, 9, 16)
    before_lunch = datetime(2026, 9, 16, 8, 39, tzinfo=TZ)
    at_lunch = datetime(2026, 9, 16, 8, 40, tzinfo=TZ)
    before_dinner = datetime(2026, 9, 16, 13, 39, tzinfo=TZ)
    at_dinner = datetime(2026, 9, 16, 13, 40, tzinfo=TZ)

    assert is_lunch_closed(day, before_lunch) is False
    assert is_lunch_closed(day, at_lunch) is True
    assert is_dinner_closed(day, before_dinner) is False
    assert is_dinner_closed(day, at_dinner) is True
    assert is_lunch_closed(date(2026, 9, 15), before_lunch) is True
    assert is_dinner_closed(date(2026, 9, 17), at_dinner) is False


def test_labels_and_convert() -> None:
    assert meal_label(1) == "먹음"
    assert meal_label(0) == "안 먹음"
    assert to_bool_int("먹음") == 1
    assert to_bool_int("안 먹음") == 0
    assert weekday_label(date(2026, 9, 16)) == "수"


def test_resolve_auto_and_unsubmitted() -> None:
    employee = {"id": 1, "name": "홍길동", "department": "공무팀"}
    auto = resolve_employee_application(employee, None, {"lunch": 1, "dinner": 0})
    assert auto["lunch"] == 1
    assert auto["dinner"] == 0
    assert auto["apply_method"] == METHOD_AUTO

    empty = resolve_employee_application(employee, None, None)
    assert empty["lunch"] == 0
    assert empty["dinner"] == 0
    assert empty["apply_method"] == METHOD_UNSUBMITTED

    saved = resolve_employee_application(
        employee,
        {"apply_date": "2026-09-16", "lunch": 0, "dinner": 1, "apply_method": "수동변경", "submitted_at": "x"},
        {"lunch": 1, "dinner": 0},
    )
    assert saved["lunch"] == 0
    assert saved["dinner"] == 1
    assert saved["apply_method"] == "수동변경"
    assert saved["source"] == "saved"


def test_materialize_timing() -> None:
    day = date(2026, 9, 16)
    before = datetime(2026, 9, 16, 8, 0, tzinfo=TZ)
    after = datetime(2026, 9, 16, 9, 0, tzinfo=TZ)
    assert should_materialize(day, before) is False
    assert should_materialize(day, after) is True
    assert should_materialize(date(2026, 9, 15), before) is True


def test_checkin_windows() -> None:
    day_dt = datetime(2026, 9, 16, 12, 30, tzinfo=TZ)
    assert current_checkin_meal(day_dt) == "lunch"
    assert current_checkin_meal(datetime(2026, 9, 16, 13, 29, tzinfo=TZ)) == "lunch"
    assert current_checkin_meal(datetime(2026, 9, 16, 13, 30, tzinfo=TZ)) is None
    assert current_checkin_meal(datetime(2026, 9, 16, 17, 0, tzinfo=TZ)) == "dinner"
    assert current_checkin_meal(datetime(2026, 9, 16, 17, 59, tzinfo=TZ)) == "dinner"
    assert current_checkin_meal(datetime(2026, 9, 16, 18, 0, tzinfo=TZ)) is None
    assert current_checkin_meal(datetime(2026, 9, 16, 10, 0, tzinfo=TZ)) is None


if __name__ == "__main__":
    test_deadlines()
    test_labels_and_convert()
    test_resolve_auto_and_unsubmitted()
    test_materialize_timing()
    test_checkin_windows()
    print("logic tests passed")
