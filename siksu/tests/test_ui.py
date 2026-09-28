"""Streamlit AppTest로 로그인 및 홈 화면을 검증한다."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from streamlit.testing.v1 import AppTest

from config import CAFETERIA_AFFILIATE, CAFETERIA_USERNAME, USER_SESSION_KEY
from db import authenticate, get_connection, list_employees
from init_db import initialize_database


def test_login_screen() -> None:
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
    at.run()
    assert not at.exception, at.exception
    assert len(at.text_input) >= 2
    assert len(at.selectbox) >= 1
    assert "에이텍컴퓨터" in at.selectbox[0].options


def test_home_after_login() -> None:
    initialize_database()
    conn = get_connection()
    user = next((row for row in list_employees(conn) if row["name"] == "황태연"), None)
    conn.close()
    assert user is not None

    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
    at.session_state[USER_SESSION_KEY] = {**user, "must_change_password": 0}
    at.session_state["nav_page"] = "홈"
    at.run()
    assert not at.exception, at.exception
    assert at.button


def test_qr_page() -> None:
    initialize_database()
    conn = get_connection()
    user = next((row for row in list_employees(conn) if row["name"] == "황태연"), None)
    conn.close()
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
    at.session_state[USER_SESSION_KEY] = {**user, "must_change_password": 0}
    at.session_state["nav_page"] = "QR코드"
    at.run()
    assert not at.exception, at.exception
    assert at.image


def test_cafeteria_desk() -> None:
    initialize_database()
    conn = get_connection()
    user = authenticate(conn, CAFETERIA_USERNAME, "1111", CAFETERIA_AFFILIATE)
    conn.close()
    assert user is not None
    at = AppTest.from_file(str(ROOT / "app.py"), default_timeout=20)
    at.session_state[USER_SESSION_KEY] = dict(user)
    at.run()
    assert not at.exception, at.exception
    markdown = " ".join(str(item.value) for item in at.markdown)
    assert "식당 식수 체크인" in markdown
    assert "점심 12:00–13:30" in markdown
    assert "석식 17:00–18:00" in markdown


if __name__ == "__main__":
    test_login_screen()
    test_home_after_login()
    test_qr_page()
    test_cafeteria_desk()
    print("ui tests passed")
