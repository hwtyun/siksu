"""QR 체크인·노쇼·실식수 집계 검증."""

from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import CAFETERIA_AFFILIATE, CAFETERIA_USERNAME, TZ  # noqa: E402
from db import (  # noqa: E402
    actual_attendance_rows,
    add_single_employee,
    authenticate,
    ensure_cafeteria_account,
    ensure_employee_qr_code,
    get_connection,
    init_schema,
    list_employees,
    noshow_rows,
    record_checkin,
    upsert_daily_application,
)
from qr_checkin import employee_qr_payload, parse_employee_qr, qr_png_bytes  # noqa: E402


def test_qr_payload() -> None:
    payload = employee_qr_payload({"id": 7, "username": "황태연", "name": "황태연", "qr_code": "ATEC-AABBCCDD"})
    emp_id, username, qr_code = parse_employee_qr(payload)
    assert emp_id is None
    assert qr_code == "ATEC-AABBCCDD"
    png = qr_png_bytes(payload)
    assert png.startswith(b"\x89PNG")
    old_id, old_name, _ = parse_employee_qr("ATEC|7|황태연")
    assert old_id == 7
    assert old_name == "황태연"


def test_checkin_noshow_and_actual(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "checkin.db")
    init_schema(conn)
    add_single_employee(conn, "노쇼테스트", "생산관리팀", "에이텍컴퓨터")
    add_single_employee(conn, "실식수테스트", "생산관리팀", "에이텍컴퓨터")
    people = {row["name"]: row for row in list_employees(conn)}
    code1 = ensure_employee_qr_code(conn, people["실식수테스트"]["id"])
    code2 = ensure_employee_qr_code(conn, people["실식수테스트"]["id"])
    assert code1 == code2
    day = date(2026, 9, 16)
    upsert_daily_application(conn, people["노쇼테스트"], day, 1, 0, "수동변경", "2026-09-16T08:00:00")
    upsert_daily_application(conn, people["실식수테스트"], day, 1, 0, "수동변경", "2026-09-16T08:00:00")
    assert record_checkin(conn, people["실식수테스트"]["id"], "lunch", day) == "ok"
    assert record_checkin(conn, people["실식수테스트"]["id"], "lunch", day) == "duplicate"

    during_lunch = datetime(2026, 9, 16, 12, 0, tzinfo=TZ)
    assert noshow_rows(conn, day, during_lunch) == []

    after_lunch = datetime(2026, 9, 16, 14, 0, tzinfo=TZ)
    noshows = noshow_rows(conn, day, after_lunch)
    assert any(row["name"] == "노쇼테스트" and row["noshow_meal"] == "점심" for row in noshows)
    assert all(row["name"] != "실식수테스트" for row in noshows)

    actual = actual_attendance_rows(conn, day, day)
    assert len(actual) == 1
    assert actual[0]["name"] == "실식수테스트"
    assert actual[0]["lunch_attended"] == 1
    conn.close()


def test_cafeteria_account(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "cafe.db")
    init_schema(conn)
    ensure_cafeteria_account(conn)
    user = authenticate(conn, CAFETERIA_USERNAME, "1111", CAFETERIA_AFFILIATE)
    assert user is not None
    assert int(user.get("is_cafeteria") or 0) == 1
    assert int(user.get("must_change_password") or 0) == 0
    assert all(row["username"] != CAFETERIA_USERNAME for row in list_employees(conn))
    conn.close()


if __name__ == "__main__":
    import tempfile

    test_qr_payload()
    with tempfile.TemporaryDirectory() as folder:
        test_checkin_noshow_and_actual(Path(folder))
        test_cafeteria_account(Path(folder))
    print("checkin tests passed")
