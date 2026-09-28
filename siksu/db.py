"""SQLite 접근 계층."""

from __future__ import annotations

import sqlite3
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import pandas as pd

from auth import default_password_hash, new_token, token_expiry_iso, verify_password
from config import AFFILIATES, DB_PATH, DEFAULT_AFFILIATE, METHOD_AUTO, METHOD_MANUAL, SCHEMA_PATH
from logic import (
    is_dinner_service_ended,
    is_lunch_closed,
    is_lunch_service_ended,
    now_kst,
    resolve_employee_application,
    should_materialize,
    to_bool_int,
    today_kst,
)

EMPLOYEE_NEW_COLUMNS = [
    ("username", "TEXT"),
    ("password_hash", "TEXT"),
    ("must_change_password", "INTEGER NOT NULL DEFAULT 1"),
    ("is_admin", "INTEGER NOT NULL DEFAULT 0"),
    ("auto_enabled", "INTEGER NOT NULL DEFAULT 0"),
    ("notify_before", "INTEGER NOT NULL DEFAULT 0"),
    ("affiliate", "TEXT NOT NULL DEFAULT '에이텍컴퓨터'"),
    ("qr_code", "TEXT"),
    ("is_cafeteria", "INTEGER NOT NULL DEFAULT 0"),
]

PUBLIC_EMPLOYEE_FIELDS = (
    "id",
    "name",
    "department",
    "affiliate",
    "username",
    "qr_code",
    "must_change_password",
    "is_admin",
    "auto_enabled",
    "notify_before",
    "is_cafeteria",
)

MENU_TEMPLATES = {
    0: {
        "lunch": [
            ("메인 요리", "제육볶음", "오늘의 메인 메뉴"),
            ("국 & 반찬", "된장국", ""),
            ("국 & 반찬", "시금치나물", ""),
            ("국 & 반찬", "김치", ""),
        ],
        "dinner": [
            ("메인 요리", "김치찌개", "오늘의 저녁 메뉴"),
            ("국 & 반찬", "계란말이", ""),
            ("국 & 반찬", "멸치볶음", ""),
        ],
    },
    1: {
        "lunch": [
            ("메인 요리", "치킨마요덮밥", "오늘의 메인 메뉴"),
            ("국 & 반찬", "유부국", ""),
            ("국 & 반찬", "콩나물무침", ""),
            ("국 & 반찬", "깍두기", ""),
        ],
        "dinner": [
            ("메인 요리", "순두부찌개", "오늘의 저녁 메뉴"),
            ("국 & 반찬", "고등어구이", ""),
            ("국 & 반찬", "숙주나물", ""),
        ],
    },
    2: {
        "lunch": [
            ("메인 요리", "쌀밥", "오늘의 메인 메뉴"),
            ("메인 요리", "돈까스/소스", ""),
            ("국 & 반찬", "계란국", ""),
            ("국 & 반찬", "볶음우동", ""),
        ],
        "dinner": [
            ("메인 요리", "된장찌개", "오늘의 저녁 메뉴"),
            ("국 & 반찬", "잡채", ""),
            ("국 & 반찬", "오징어볶음", ""),
        ],
    },
    3: {
        "lunch": [
            ("메인 요리", "불고기", "오늘의 메인 메뉴"),
            ("국 & 반찬", "미역국", ""),
            ("국 & 반찬", "감자조림", ""),
            ("국 & 반찬", "배추김치", ""),
        ],
        "dinner": [
            ("메인 요리", "카레라이스", "오늘의 저녁 메뉴"),
            ("국 & 반찬", "샐러드", ""),
            ("국 & 반찬", "단무지", ""),
        ],
    },
    4: {
        "lunch": [
            ("메인 요리", "생선구이", "오늘의 메인 메뉴"),
            ("국 & 반찬", "북어국", ""),
            ("국 & 반찬", "호박볶음", ""),
            ("국 & 반찬", "열무김치", ""),
        ],
        "dinner": [
            ("메인 요리", "잔치국수", "오늘의 저녁 메뉴"),
            ("국 & 반찬", "김밥", ""),
            ("국 & 반찬", "단무지", ""),
        ],
    },
}


def get_connection(db_path: Path | None = None) -> sqlite3.Connection:
    path = db_path or DB_PATH
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def _table_columns(conn: sqlite3.Connection, table: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table})").fetchall()
    return {row[1] for row in rows}


def migrate_schema(conn: sqlite3.Connection) -> None:
    if "employees" in {
        row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
    }:
        cols = _table_columns(conn, "employees")
        for name, ddl in EMPLOYEE_NEW_COLUMNS:
            if name not in cols:
                conn.execute(f"ALTER TABLE employees ADD COLUMN {name} {ddl}")
        conn.execute(
            "UPDATE employees SET affiliate = ? WHERE affiliate IS NULL OR trim(affiliate) = ''",
            (DEFAULT_AFFILIATE,),
        )
        try:
            conn.execute("DROP INDEX IF EXISTS idx_employees_username")
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_affiliate_username "
                "ON employees(affiliate, username)"
            )
        except sqlite3.OperationalError:
            pass
        try:
            conn.execute(
                "CREATE UNIQUE INDEX IF NOT EXISTS idx_employees_qr_code ON employees(qr_code)"
            )
        except sqlite3.OperationalError:
            pass
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS meal_checkins (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            apply_date TEXT NOT NULL,
            employee_id INTEGER NOT NULL,
            meal_type TEXT NOT NULL,
            checked_at TEXT NOT NULL,
            UNIQUE(apply_date, employee_id, meal_type),
            FOREIGN KEY (employee_id) REFERENCES employees(id)
        )
        """
    )
    conn.execute(
        "CREATE INDEX IF NOT EXISTS idx_checkins_date ON meal_checkins(apply_date, meal_type)"
    )
    conn.commit()


def init_schema(conn: sqlite3.Connection) -> None:
    schema_sql = SCHEMA_PATH.read_text(encoding="utf-8")
    conn.executescript(schema_sql)
    migrate_schema(conn)
    conn.commit()


def public_employee(row: sqlite3.Row | dict[str, Any]) -> dict[str, Any]:
    data = dict(row)
    return {key: data.get(key) for key in PUBLIC_EMPLOYEE_FIELDS}


def list_employees(conn: sqlite3.Connection, include_cafeteria: bool = False) -> list[dict[str, Any]]:
    sql = """
        SELECT id, name, department, affiliate, username, qr_code, must_change_password,
               is_admin, auto_enabled, notify_before, is_cafeteria
        FROM employees
    """
    if not include_cafeteria:
        sql += " WHERE COALESCE(is_cafeteria, 0) = 0"
    sql += " ORDER BY affiliate, department, name"
    rows = conn.execute(sql).fetchall()
    return [public_employee(row) for row in rows]


def get_employee(conn: sqlite3.Connection, employee_id: int) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, name, department, affiliate, username, qr_code, must_change_password,
               is_admin, auto_enabled, notify_before, is_cafeteria
        FROM employees
        WHERE id = ?
        """,
        (employee_id,),
    ).fetchone()
    return public_employee(row) if row else None


def find_employee_for_checkin(
    conn: sqlite3.Connection,
    employee_id: int | None,
    username: str = "",
    qr_code: str = "",
) -> dict[str, Any] | None:
    token = (qr_code or "").strip()
    if token:
        row = conn.execute(
            """
            SELECT id, name, department, affiliate, username, qr_code, must_change_password,
                   is_admin, auto_enabled, notify_before, is_cafeteria
            FROM employees
            WHERE qr_code = ? AND COALESCE(is_cafeteria, 0) = 0
            """,
            (token,),
        ).fetchone()
        if row:
            return public_employee(row)
    if employee_id:
        found = get_employee(conn, employee_id)
        if found and not found.get("is_cafeteria"):
            return found
        if found:
            return None
    ident = (username or "").strip()
    if not ident:
        return None
    row = conn.execute(
        """
        SELECT id, name, department, affiliate, username, qr_code, must_change_password,
               is_admin, auto_enabled, notify_before, is_cafeteria
        FROM employees
        WHERE (username = ? OR name = ?) AND COALESCE(is_cafeteria, 0) = 0
        ORDER BY id
        LIMIT 1
        """,
        (ident, ident),
    ).fetchone()
    return public_employee(row) if row else None


def normalize_affiliate(value: str | None) -> str:
    affiliate = (value or "").strip()
    if affiliate in AFFILIATES:
        return affiliate
    return DEFAULT_AFFILIATE


def unique_username(
    conn: sqlite3.Connection,
    name: str,
    affiliate: str,
    employee_id: int | None = None,
) -> str:
    base = name.strip()
    candidate = base
    n = 2
    while True:
        row = conn.execute(
            """
            SELECT id FROM employees
            WHERE username = ? AND affiliate = ? AND (? IS NULL OR id != ?)
            """,
            (candidate, affiliate, employee_id, employee_id),
        ).fetchone()
        if not row:
            return candidate
        candidate = f"{base}{n}"
        n += 1


def ensure_login_accounts(conn: sqlite3.Connection) -> None:
    rows = conn.execute(
        "SELECT id, name, department, affiliate, username, password_hash FROM employees"
    ).fetchall()
    for row in rows:
        affiliate = normalize_affiliate(row["affiliate"])
        username = row["username"] or unique_username(conn, row["name"], affiliate, row["id"])
        password_hash = row["password_hash"] or default_password_hash()
        is_admin = 1 if row["department"] == "공무팀" else 0
        conn.execute(
            """
            UPDATE employees
            SET affiliate = ?, username = ?, password_hash = COALESCE(password_hash, ?),
                is_admin = CASE WHEN is_admin = 1 THEN 1 ELSE ? END
            WHERE id = ?
            """,
            (affiliate, username, password_hash, is_admin, row["id"]),
        )
    conn.commit()
    ensure_all_qr_codes(conn)


def new_employee_qr_code(conn: sqlite3.Connection) -> str:
    from qr_checkin import issue_qr_code

    while True:
        code = issue_qr_code()
        exists = conn.execute("SELECT id FROM employees WHERE qr_code = ?", (code,)).fetchone()
        if not exists:
            return code


def ensure_employee_qr_code(conn: sqlite3.Connection, employee_id: int) -> str:
    row = conn.execute("SELECT qr_code FROM employees WHERE id = ?", (employee_id,)).fetchone()
    if row and row["qr_code"]:
        return str(row["qr_code"])
    code = new_employee_qr_code(conn)
    conn.execute(
        "UPDATE employees SET qr_code = ? WHERE id = ? AND (qr_code IS NULL OR qr_code = '')",
        (code, employee_id),
    )
    conn.commit()
    latest = conn.execute("SELECT qr_code FROM employees WHERE id = ?", (employee_id,)).fetchone()
    return str(latest["qr_code"]) if latest and latest["qr_code"] else code


def ensure_all_qr_codes(conn: sqlite3.Connection) -> None:
    if "qr_code" not in _table_columns(conn, "employees"):
        return
    rows = conn.execute("SELECT id FROM employees WHERE qr_code IS NULL OR qr_code = ''").fetchall()
    for row in rows:
        ensure_employee_qr_code(conn, row["id"])


def ensure_cafeteria_account(conn: sqlite3.Connection) -> None:
    from config import CAFETERIA_AFFILIATE, CAFETERIA_DEPARTMENT, CAFETERIA_NAME, CAFETERIA_USERNAME

    now = now_kst().isoformat(timespec="seconds")
    pw_hash = default_password_hash()
    row = conn.execute(
        """
        SELECT id FROM employees
        WHERE (username = ? AND affiliate = ?)
           OR (name = ? AND department = ?)
        """,
        (CAFETERIA_USERNAME, CAFETERIA_AFFILIATE, CAFETERIA_NAME, CAFETERIA_DEPARTMENT),
    ).fetchone()
    if not row:
        conn.execute(
            """
            INSERT INTO employees (
                name, department, affiliate, username, created_at,
                password_hash, must_change_password, is_admin, is_cafeteria, auto_enabled
            )
            VALUES (?, ?, ?, ?, ?, ?, 0, 0, 1, 0)
            """,
            (
                CAFETERIA_NAME,
                CAFETERIA_DEPARTMENT,
                CAFETERIA_AFFILIATE,
                CAFETERIA_USERNAME,
                now,
                pw_hash,
            ),
        )
        conn.commit()
        return
    conn.execute(
        """
        UPDATE employees
        SET name = ?, department = ?, affiliate = ?, username = ?,
            password_hash = ?, is_cafeteria = 1, must_change_password = 0,
            is_admin = 0, auto_enabled = 0
        WHERE id = ?
        """,
        (
            CAFETERIA_NAME,
            CAFETERIA_DEPARTMENT,
            CAFETERIA_AFFILIATE,
            CAFETERIA_USERNAME,
            pw_hash,
            row["id"],
        ),
    )
    conn.commit()


def upsert_employees(conn: sqlite3.Connection, employees: list[tuple[str, str, str]]) -> int:
    inserted = 0
    now = now_kst().isoformat(timespec="seconds")
    for name, department, affiliate in employees:
        name = name.strip()
        department = department.strip()
        affiliate = normalize_affiliate(affiliate)
        if not name or not department:
            continue
        existing = conn.execute(
            "SELECT id FROM employees WHERE name = ? AND department = ?",
            (name, department),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE employees SET affiliate = ? WHERE id = ?",
                (affiliate, existing["id"]),
            )
            continue
        conn.execute(
            """
            INSERT INTO employees (name, department, affiliate, created_at)
            VALUES (?, ?, ?, ?)
            """,
            (name, department, affiliate, now),
        )
        inserted += 1
    conn.commit()
    ensure_login_accounts(conn)
    return inserted


def add_single_employee(conn: sqlite3.Connection, name: str, department: str, affiliate: str) -> str:
    name = (name or "").strip()
    department = (department or "").strip()
    if not name or not department:
        raise ValueError("이름과 부서를 입력해 주세요.")
    affiliate = normalize_affiliate(affiliate)
    existing = conn.execute(
        "SELECT id FROM employees WHERE name = ? AND department = ?",
        (name, department),
    ).fetchone()
    if existing:
        conn.execute("UPDATE employees SET affiliate = ? WHERE id = ?", (affiliate, existing["id"]))
        conn.commit()
        ensure_login_accounts(conn)
        return "updated"
    upsert_employees(conn, [(name, department, affiliate)])
    return "added"


def delete_employee(conn: sqlite3.Connection, employee_id: int) -> None:
    conn.execute("DELETE FROM login_tokens WHERE employee_id = ?", (employee_id,))
    conn.execute("DELETE FROM auto_reservations WHERE employee_id = ?", (employee_id,))
    conn.execute("DELETE FROM daily_applications WHERE employee_id = ?", (employee_id,))
    conn.execute("DELETE FROM meal_checkins WHERE employee_id = ?", (employee_id,))
    conn.execute("DELETE FROM employees WHERE id = ?", (employee_id,))
    conn.commit()


def import_employees_from_path(conn: sqlite3.Connection, path: Path) -> int:
    suffix = path.suffix.lower()
    if suffix in {".xlsx", ".xls"}:
        df = pd.read_excel(path)
        return import_employees_from_dataframe(conn, df)
    return import_employees_from_csv(conn, path)


def _employee_rows_from_df(df: pd.DataFrame) -> list[tuple[str, str, str]]:
    required = {"이름", "부서"}
    if not required.issubset(set(df.columns)):
        raise ValueError("파일에는 '이름', '부서' 컬럼이 필요합니다. 계열사 컬럼이 있으면 함께 반영됩니다.")
    has_affiliate = "계열사" in df.columns
    rows: list[tuple[str, str, str]] = []
    for _, row in df.iterrows():
        name = "" if pd.isna(row["이름"]) else str(row["이름"]).strip()
        department = "" if pd.isna(row["부서"]) else str(row["부서"]).strip()
        if not name or not department:
            continue
        if has_affiliate and not pd.isna(row["계열사"]):
            affiliate = str(row["계열사"])
        else:
            affiliate = DEFAULT_AFFILIATE
        rows.append((name, department, affiliate))
    if not rows:
        raise ValueError("등록할 직원 행이 없습니다.")
    return rows


def import_employees_from_csv(conn: sqlite3.Connection, csv_path: Path) -> int:
    df = pd.read_csv(csv_path, encoding="utf-8-sig")
    return upsert_employees(conn, _employee_rows_from_df(df))


def import_employees_from_dataframe(conn: sqlite3.Connection, df: pd.DataFrame) -> int:
    return upsert_employees(conn, _employee_rows_from_df(df))


def authenticate(
    conn: sqlite3.Connection,
    username: str,
    password: str,
    affiliate: str,
) -> dict[str, Any] | None:
    row = conn.execute(
        """
        SELECT id, name, department, affiliate, username, password_hash, must_change_password,
               is_admin, auto_enabled, notify_before, is_cafeteria, qr_code
        FROM employees
        WHERE username = ? AND affiliate = ?
        """,
        (username.strip(), normalize_affiliate(affiliate)),
    ).fetchone()
    if not row or not verify_password(password, row["password_hash"]):
        return None
    return public_employee(row)


def update_password(conn: sqlite3.Connection, employee_id: int, password_hash: str) -> None:
    conn.execute(
        """
        UPDATE employees
        SET password_hash = ?, must_change_password = 0
        WHERE id = ?
        """,
        (password_hash, employee_id),
    )
    conn.commit()


def reset_employee_password(conn: sqlite3.Connection, employee_id: int) -> dict[str, Any] | None:
    """비밀번호를 초기값(1111)으로 돌리고, 자동 로그인을 끊는다."""
    row = get_employee(conn, employee_id)
    if not row:
        return None
    must_change = 0 if row.get("is_cafeteria") else 1
    conn.execute(
        """
        UPDATE employees
        SET password_hash = ?, must_change_password = ?
        WHERE id = ?
        """,
        (default_password_hash(), must_change, employee_id),
    )
    conn.execute("DELETE FROM login_tokens WHERE employee_id = ?", (employee_id,))
    conn.commit()
    return get_employee(conn, employee_id)


def issue_login_token(conn: sqlite3.Connection, employee_id: int) -> str:
    token = new_token()
    now = now_kst().isoformat(timespec="seconds")
    conn.execute(
        "INSERT INTO login_tokens (token, employee_id, expires_at, created_at) VALUES (?, ?, ?, ?)",
        (token, employee_id, token_expiry_iso(), now),
    )
    conn.commit()
    return token


def get_employee_by_token(conn: sqlite3.Connection, token: str) -> dict[str, Any] | None:
    if not token:
        return None
    now = now_kst().isoformat(timespec="seconds")
    row = conn.execute(
        """
        SELECT e.id, e.name, e.department, e.affiliate, e.username, e.qr_code, e.must_change_password,
               e.is_admin, e.auto_enabled, e.notify_before, e.is_cafeteria
        FROM login_tokens t
        JOIN employees e ON e.id = t.employee_id
        WHERE t.token = ? AND t.expires_at > ?
        """,
        (token, now),
    ).fetchone()
    return public_employee(row) if row else None


def delete_login_token(conn: sqlite3.Connection, token: str | None) -> None:
    if not token:
        return
    conn.execute("DELETE FROM login_tokens WHERE token = ?", (token,))
    conn.commit()


def set_employee_flag(conn: sqlite3.Connection, employee_id: int, field: str, value: int) -> None:
    if field not in {"auto_enabled", "notify_before", "is_admin"}:
        raise ValueError("허용되지 않은 필드입니다.")
    conn.execute(f"UPDATE employees SET {field} = ? WHERE id = ?", (int(value), employee_id))
    conn.commit()


def get_auto_reservation_map(
    conn: sqlite3.Connection, employee_id: int
) -> dict[int, dict[str, int]]:
    rows = conn.execute(
        """
        SELECT weekday, lunch_default, dinner_default
        FROM auto_reservations
        WHERE employee_id = ?
        """,
        (employee_id,),
    ).fetchall()
    return {
        int(row["weekday"]): {
            "lunch": int(row["lunch_default"]),
            "dinner": int(row["dinner_default"]),
        }
        for row in rows
    }


def get_auto_reservation_for_weekday(
    conn: sqlite3.Connection, employee_id: int, weekday: int
) -> dict[str, int] | None:
    row = conn.execute(
        """
        SELECT ar.lunch_default, ar.dinner_default
        FROM auto_reservations ar
        JOIN employees e ON e.id = ar.employee_id
        WHERE ar.employee_id = ? AND ar.weekday = ? AND e.auto_enabled = 1
        """,
        (employee_id, weekday),
    ).fetchone()
    if not row:
        return None
    return {
        "lunch": int(row["lunch_default"]),
        "dinner": int(row["dinner_default"]),
    }


def upsert_auto_reservations(
    conn: sqlite3.Connection,
    employee_id: int,
    pattern: list[dict[str, Any]],
) -> None:
    now = now_kst().isoformat(timespec="seconds")
    for item in pattern:
        conn.execute(
            """
            INSERT INTO auto_reservations (
                employee_id, weekday, lunch_default, dinner_default, updated_at
            )
            VALUES (?, ?, ?, ?, ?)
            ON CONFLICT(employee_id, weekday) DO UPDATE SET
                lunch_default = excluded.lunch_default,
                dinner_default = excluded.dinner_default,
                updated_at = excluded.updated_at
            """,
            (
                employee_id,
                int(item["weekday"]),
                to_bool_int(item["lunch"]),
                to_bool_int(item["dinner"]),
                now,
            ),
        )
    conn.commit()


def toggle_auto_cell(
    conn: sqlite3.Connection,
    employee_id: int,
    weekday: int,
    meal: str,
) -> None:
    current = get_auto_reservation_map(conn, employee_id).get(weekday, {"lunch": 0, "dinner": 0})
    if meal == "lunch":
        current["lunch"] = 0 if current["lunch"] else 1
    else:
        current["dinner"] = 0 if current["dinner"] else 1
    upsert_auto_reservations(conn, employee_id, [{"weekday": weekday, **current}])


def get_daily_application(
    conn: sqlite3.Connection, employee_id: int, apply_date: date | None = None
) -> dict[str, Any] | None:
    target = (apply_date or today_kst()).isoformat()
    row = conn.execute(
        """
        SELECT id, apply_date, employee_id, name, department,
               lunch, dinner, apply_method, submitted_at
        FROM daily_applications
        WHERE employee_id = ? AND apply_date = ?
        """,
        (employee_id, target),
    ).fetchone()
    return dict(row) if row else None


def list_daily_applications(
    conn: sqlite3.Connection, apply_date: date
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT apply_date, employee_id, name, department,
               lunch, dinner, apply_method, submitted_at
        FROM daily_applications
        WHERE apply_date = ?
        ORDER BY department, name
        """,
        (apply_date.isoformat(),),
    ).fetchall()
    return [dict(row) for row in rows]


def list_daily_applications_range(
    conn: sqlite3.Connection, start_date: date, end_date: date
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT apply_date, employee_id, name, department,
               lunch, dinner, apply_method, submitted_at
        FROM daily_applications
        WHERE apply_date BETWEEN ? AND ?
        ORDER BY apply_date, department, name
        """,
        (start_date.isoformat(), end_date.isoformat()),
    ).fetchall()
    return [dict(row) for row in rows]


def upsert_daily_application(
    conn: sqlite3.Connection,
    employee: dict[str, Any],
    apply_date: date,
    lunch: int,
    dinner: int,
    apply_method: str,
    submitted_at: str | None = None,
) -> None:
    stamp = submitted_at or now_kst().isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO daily_applications (
            apply_date, employee_id, name, department,
            lunch, dinner, apply_method, submitted_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ON CONFLICT(apply_date, employee_id) DO UPDATE SET
            name = excluded.name,
            department = excluded.department,
            lunch = excluded.lunch,
            dinner = excluded.dinner,
            apply_method = excluded.apply_method,
            submitted_at = excluded.submitted_at
        """,
        (
            apply_date.isoformat(),
            employee["id"],
            employee["name"],
            employee["department"],
            int(lunch),
            int(dinner),
            apply_method,
            stamp,
        ),
    )
    conn.commit()


def seed_sample_auto_reservations(conn: sqlite3.Connection) -> None:
    """테스트용 자동예약 샘플. 이미 패턴이 있으면 건너뛴다."""
    existing = conn.execute("SELECT COUNT(*) AS cnt FROM auto_reservations").fetchone()
    if existing and int(existing["cnt"]) > 0:
        conn.execute(
            """
            UPDATE employees
            SET auto_enabled = 1
            WHERE name IN ('김민준', '이서연', '황태연', '정우진', '오준호', '강현우')
            """
        )
        hwang = conn.execute(
            "SELECT id FROM employees WHERE name = ? AND department = ?",
            ("황태연", "생산관리팀"),
        ).fetchone()
        if hwang:
            now = now_kst().isoformat(timespec="seconds")
            for weekday in range(7):
                dinner_default = 1 if weekday in {0, 1, 2, 3} else 0
                lunch_default = 1 if weekday <= 4 else 0
                conn.execute(
                    """
                    UPDATE auto_reservations
                    SET lunch_default = ?, dinner_default = ?, updated_at = ?
                    WHERE employee_id = ? AND weekday = ?
                    """,
                    (lunch_default, dinner_default, now, hwang["id"], weekday),
                )
        conn.commit()
        return

    samples = [
        ("김민준", "생산관리팀", {0, 1, 2, 3, 4}, 1, 0),
        ("이서연", "생산관리팀", {0, 1, 2, 3, 4}, 1, 1),
        ("황태연", "생산관리팀", {0, 1, 2, 3, 4}, 1, 0),
        ("정우진", "공무팀", {0, 1, 2, 3, 4}, 1, 0),
        ("오준호", "품질팀", {0, 1, 2, 3}, 1, 0),
        ("강현우", "생산1팀", {0, 1, 2, 3, 4, 5}, 1, 1),
    ]
    now = now_kst().isoformat(timespec="seconds")
    for name, department, weekdays, lunch, dinner in samples:
        emp = conn.execute(
            "SELECT id FROM employees WHERE name = ? AND department = ?",
            (name, department),
        ).fetchone()
        if not emp:
            continue
        conn.execute("UPDATE employees SET auto_enabled = 1 WHERE id = ?", (emp["id"],))
        for weekday in range(7):
            lunch_default = lunch if weekday in weekdays else 0
            dinner_default = dinner if weekday in weekdays else 0
            if name == "황태연":
                dinner_default = 1 if weekday in {0, 1, 2, 3} else 0
            conn.execute(
                """
                INSERT OR IGNORE INTO auto_reservations (
                    employee_id, weekday, lunch_default, dinner_default, updated_at
                )
                VALUES (?, ?, ?, ?, ?)
                """,
                (emp["id"], weekday, lunch_default, dinner_default, now),
            )
    conn.commit()


def list_menus(conn: sqlite3.Connection, menu_date: date, meal_type: str) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT section, name, description, sort_order
        FROM menus
        WHERE menu_date = ? AND meal_type = ?
        ORDER BY sort_order, id
        """,
        (menu_date.isoformat(), meal_type),
    ).fetchall()
    return [dict(row) for row in rows]


def replace_menus(
    conn: sqlite3.Connection,
    menu_date: date,
    meal_type: str,
    items: list[tuple[str, str, str]],
) -> None:
    conn.execute(
        "DELETE FROM menus WHERE menu_date = ? AND meal_type = ?",
        (menu_date.isoformat(), meal_type),
    )
    for idx, (section, name, description) in enumerate(items):
        conn.execute(
            """
            INSERT INTO menus (menu_date, meal_type, section, name, description, sort_order)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (menu_date.isoformat(), meal_type, section, name, description, idx),
        )
    conn.commit()


def seed_week_menus(conn: sqlite3.Connection, base: date | None = None) -> None:
    today = base or today_kst()
    monday = today - timedelta(days=today.weekday())
    for week_offset in (0, 1, -1):
        for i in range(5):
            day = monday + timedelta(days=i + (week_offset * 7))
            template = MENU_TEMPLATES.get(i, MENU_TEMPLATES[0])
            for meal_type, items in template.items():
                existing = conn.execute(
                    "SELECT COUNT(*) AS cnt FROM menus WHERE menu_date = ? AND meal_type = ?",
                    (day.isoformat(), meal_type),
                ).fetchone()
                if existing and int(existing["cnt"]) > 0:
                    continue
                replace_menus(conn, day, meal_type, items)


def determine_apply_method(
    auto_pattern: dict[str, int] | None,
    lunch: int,
    dinner: int,
) -> str:
    if auto_pattern is None:
        return METHOD_MANUAL
    if int(auto_pattern["lunch"]) == int(lunch) and int(auto_pattern["dinner"]) == int(dinner):
        return METHOD_AUTO
    return METHOD_MANUAL


def resolve_applications_for_date(
    conn: sqlite3.Connection, apply_date: date
) -> list[dict[str, Any]]:
    employees = list_employees(conn)
    saved_map = {
        int(row["employee_id"]): row
        for row in list_daily_applications(conn, apply_date)
    }
    weekday = apply_date.weekday()
    resolved: list[dict[str, Any]] = []
    for employee in employees:
        saved = saved_map.get(int(employee["id"]))
        auto_pattern = get_auto_reservation_for_weekday(conn, employee["id"], weekday)
        row = resolve_employee_application(employee, saved, auto_pattern)
        row["apply_date"] = apply_date.isoformat()
        resolved.append(row)
    return resolved


def meal_counts(conn: sqlite3.Connection, apply_date: date) -> tuple[int, int]:
    rows = resolve_applications_for_date(conn, apply_date)
    lunch = sum(1 for row in rows if int(row["lunch"]))
    dinner = sum(1 for row in rows if int(row["dinner"]))
    return lunch, dinner


def materialize_missing_applications(
    conn: sqlite3.Connection,
    apply_date: date,
    now=None,
) -> int:
    """마감이 지난 날짜의 미기록 인원을 자동예약 또는 미제출(안 먹음)으로 확정 저장한다."""
    if not should_materialize(apply_date, now):
        return 0
    if not is_lunch_closed(apply_date, now):
        return 0

    stamp = (now or now_kst()).isoformat(timespec="seconds")
    created = 0
    for row in resolve_applications_for_date(conn, apply_date):
        if row.get("source") == "saved":
            continue
        employee = {
            "id": row["employee_id"],
            "name": row["name"],
            "department": row["department"],
        }
        upsert_daily_application(
            conn,
            employee,
            apply_date,
            int(row["lunch"]),
            int(row["dinner"]),
            row["apply_method"],
            stamp,
        )
        created += 1
    return created


def checkin_map(conn: sqlite3.Connection, apply_date: date) -> dict[int, set[str]]:
    rows = conn.execute(
        "SELECT employee_id, meal_type FROM meal_checkins WHERE apply_date = ?",
        (apply_date.isoformat(),),
    ).fetchall()
    result: dict[int, set[str]] = {}
    for row in rows:
        result.setdefault(int(row["employee_id"]), set()).add(row["meal_type"])
    return result


def checkin_times(
    conn: sqlite3.Connection, apply_date: date, employee_id: int
) -> dict[str, str]:
    rows = conn.execute(
        """
        SELECT meal_type, checked_at
        FROM meal_checkins
        WHERE apply_date = ? AND employee_id = ?
        """,
        (apply_date.isoformat(), employee_id),
    ).fetchall()
    return {row["meal_type"]: row["checked_at"] for row in rows}


def list_checkin_details(
    conn: sqlite3.Connection, apply_date: date, meal_type: str
) -> list[dict[str, Any]]:
    rows = conn.execute(
        """
        SELECT c.checked_at, e.name, e.department, e.affiliate, e.id AS employee_id
        FROM meal_checkins c
        JOIN employees e ON e.id = c.employee_id
        WHERE c.apply_date = ? AND c.meal_type = ?
          AND COALESCE(e.is_cafeteria, 0) = 0
        ORDER BY c.checked_at DESC
        """,
        (apply_date.isoformat(), meal_type),
    ).fetchall()
    return [dict(row) for row in rows]


def record_checkin(
    conn: sqlite3.Connection,
    employee_id: int,
    meal_type: str,
    apply_date: date | None = None,
    now=None,
) -> str:
    meal = "dinner" if meal_type == "dinner" else "lunch"
    day = apply_date or today_kst()
    existing = conn.execute(
        """
        SELECT id FROM meal_checkins
        WHERE apply_date = ? AND employee_id = ? AND meal_type = ?
        """,
        (day.isoformat(), employee_id, meal),
    ).fetchone()
    if existing:
        return "duplicate"
    stamp = (now or now_kst()).isoformat(timespec="seconds")
    conn.execute(
        """
        INSERT INTO meal_checkins (apply_date, employee_id, meal_type, checked_at)
        VALUES (?, ?, ?, ?)
        """,
        (day.isoformat(), employee_id, meal, stamp),
    )
    conn.commit()
    return "ok"


def noshow_rows(
    conn: sqlite3.Connection, apply_date: date, now=None
) -> list[dict[str, Any]]:
    cmap = checkin_map(conn, apply_date)
    lunch_ended = is_lunch_service_ended(apply_date, now)
    dinner_ended = is_dinner_service_ended(apply_date, now)
    result: list[dict[str, Any]] = []
    for row in resolve_applications_for_date(conn, apply_date):
        meals = cmap.get(int(row["employee_id"]), set())
        if lunch_ended and int(row["lunch"]) and "lunch" not in meals:
            result.append({**row, "noshow_meal": "점심"})
        if dinner_ended and int(row["dinner"]) and "dinner" not in meals:
            result.append({**row, "noshow_meal": "저녁"})
    return result


def actual_attendance_rows(
    conn: sqlite3.Connection, start_date: date, end_date: date
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    cursor = start_date
    while cursor <= end_date:
        cmap = checkin_map(conn, cursor)
        resolved = {
            int(row["employee_id"]): row
            for row in resolve_applications_for_date(conn, cursor)
        }
        for employee_id, meals in cmap.items():
            if not meals:
                continue
            base = resolved.get(employee_id)
            if not base:
                employee = get_employee(conn, employee_id)
                if not employee:
                    continue
                base = {
                    "name": employee["name"],
                    "department": employee["department"],
                    "affiliate": employee.get("affiliate") or "",
                }
            times = checkin_times(conn, cursor, employee_id)
            rows.append(
                {
                    "apply_date": cursor.isoformat(),
                    "affiliate": base.get("affiliate") or "",
                    "name": base["name"],
                    "department": base["department"],
                    "lunch_attended": 1 if "lunch" in meals else 0,
                    "dinner_attended": 1 if "dinner" in meals else 0,
                    "lunch_checked_at": times.get("lunch") or "-",
                    "dinner_checked_at": times.get("dinner") or "-",
                }
            )
        cursor += timedelta(days=1)
    return rows

