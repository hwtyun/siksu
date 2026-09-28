"""식단표 엑셀 파서 및 직원 1명 추가 검증."""

from __future__ import annotations

from datetime import date
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from config import MENU_TEMPLATE_PATH  # noqa: E402
from db import (  # noqa: E402
    add_single_employee,
    delete_employee,
    get_connection,
    init_schema,
    list_employees,
    list_menus,
)
from menu_import import import_menus_from_workbook, parse_menu_workbook  # noqa: E402


def test_parse_real_template() -> None:
    parsed = parse_menu_workbook(MENU_TEMPLATE_PATH)
    monday = date(2026, 9, 14)
    wednesday = date(2026, 9, 16)
    friday = date(2026, 9, 18)
    assert monday in parsed and wednesday in parsed and friday in parsed

    lunch_names = [name for _, name, _ in parsed[wednesday]["lunch"]]
    assert "쌀밥" in lunch_names
    assert "계란국" in lunch_names
    assert "볶음우동" in lunch_names
    assert "돈까스/소스" in lunch_names
    assert "그린샐러드/소스" in lunch_names

    pork = [item for item in parsed[date(2026, 9, 17)]["lunch"] if item[1] == "제육볶음"]
    assert pork and "돈육:국내산" in pork[0][2]

    assert parsed[friday].get("dinner", []) == []
    dinner_names = [name for _, name, _ in parsed[monday]["dinner"]]
    assert "고추장찌개" in dinner_names


def test_import_and_add_employee(tmp_path: Path) -> None:
    conn = get_connection(tmp_path / "menu.db")
    init_schema(conn)
    result = import_menus_from_workbook(conn, MENU_TEMPLATE_PATH)
    assert result["item_count"] >= 40
    assert result["start"] == date(2026, 9, 14)
    wed_lunch = list_menus(conn, date(2026, 9, 16), "lunch")
    assert any(row["name"] == "볶음우동" for row in wed_lunch)
    fri_dinner = list_menus(conn, date(2026, 9, 18), "dinner")
    assert fri_dinner == []

    assert add_single_employee(conn, "테스트직원", "생산관리팀", "에이텍모빌리티") == "added"
    user = next(row for row in list_employees(conn) if row["name"] == "테스트직원")
    assert user["affiliate"] == "에이텍모빌리티"
    assert add_single_employee(conn, "테스트직원", "생산관리팀", "에이텍오토") == "updated"
    user = next(row for row in list_employees(conn) if row["name"] == "테스트직원")
    assert user["affiliate"] == "에이텍오토"
    delete_employee(conn, user["id"])
    assert all(row["name"] != "테스트직원" for row in list_employees(conn))
    conn.close()


if __name__ == "__main__":
    import tempfile

    test_parse_real_template()
    with tempfile.TemporaryDirectory() as folder:
        test_import_and_add_employee(Path(folder))
    print("menu import tests passed")
