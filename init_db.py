"""DB 초기화 및 인원명단 적재."""

from __future__ import annotations

from config import SAMPLE_EMPLOYEE_CSV, find_roster_file
from db import (
    ensure_cafeteria_account,
    ensure_login_accounts,
    get_connection,
    import_employees_from_csv,
    import_employees_from_path,
    init_schema,
    seed_sample_auto_reservations,
    seed_week_menus,
)


def initialize_database() -> None:
    conn = get_connection()
    try:
        init_schema(conn)
        roster = find_roster_file()
        if roster:
            import_employees_from_path(conn, roster)
        elif SAMPLE_EMPLOYEE_CSV.exists():
            count = conn.execute("SELECT COUNT(*) AS cnt FROM employees").fetchone()
            if count and int(count["cnt"]) == 0:
                import_employees_from_csv(conn, SAMPLE_EMPLOYEE_CSV)
        ensure_login_accounts(conn)
        ensure_cafeteria_account(conn)
        seed_sample_auto_reservations(conn)
        seed_week_menus(conn)
    finally:
        conn.close()


if __name__ == "__main__":
    initialize_database()
    print("DB 초기화 완료: data/siksu.db")
    print("로그인 ID는 이름, 초기 비밀번호는 1111 입니다.")
    roster = find_roster_file()
    if roster:
        print(f"인원명단 파일: {roster}")
