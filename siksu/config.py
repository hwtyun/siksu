"""식수체크 시스템 공통 설정."""

from __future__ import annotations

import os
from datetime import time
from pathlib import Path
from zoneinfo import ZoneInfo

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"


def _resolve_db_path() -> Path:
    override = os.environ.get("SIKSU_DB_PATH", "").strip()
    path = Path(override) if override else DATA_DIR / "siksu.db"
    path.parent.mkdir(parents=True, exist_ok=True)
    return path


DB_PATH = _resolve_db_path()
SAMPLE_EMPLOYEE_CSV = DATA_DIR / "sample_employees.csv"
MENU_TEMPLATE_PATH = DATA_DIR / "menu_template.xlsx"
ROSTER_FILENAMES = (
    "인원명단.xlsx",
    "인원명단.xls",
    "인원명단.csv",
    "직원명단.xlsx",
    "직원명단.xls",
    "직원명단.csv",
    "명단.xlsx",
    "명단.csv",
)
SCHEMA_PATH = BASE_DIR / "schema.sql"
COMPONENT_DIR = BASE_DIR / "components" / "local_storage"
LOGO_PATH = BASE_DIR / "assets" / "atec_logo.png"

TZ = ZoneInfo("Asia/Seoul")

LUNCH_DEADLINE = time(8, 40)
DINNER_DEADLINE = time(13, 40)
NOTIFY_TIME = time(7, 50)
LUNCH_SERVICE_START = time(12, 0)
LUNCH_SERVICE_END = time(13, 30)
DINNER_SERVICE_START = time(17, 0)
DINNER_SERVICE_END = time(18, 0)
QR_PREFIX = "ATEC"

CAFETERIA_NAME = "식당"
CAFETERIA_USERNAME = "식당"
CAFETERIA_AFFILIATE = "에이텍모빌리티"
CAFETERIA_DEPARTMENT = "식당"

WEEKDAYS = ["월", "화", "수", "목", "금", "토", "일"]
WEEKDAYS_BIZ = ["월", "화", "수", "목", "금"]
MEAL_YES = "먹음"
MEAL_NO = "안 먹음"
MEAL_OPTIONS = [MEAL_YES, MEAL_NO]

METHOD_AUTO = "자동예약 적용"
METHOD_MANUAL = "수동변경"
METHOD_UNSUBMITTED = "미제출"

ADMIN_PASSWORD = os.environ.get("SIKSU_ADMIN_PASSWORD", "admin1234")
ADMIN_SESSION_KEY = "admin_authenticated"
USER_SESSION_KEY = "current_user"
NAV_SESSION_KEY = "nav_page"

DEFAULT_PASSWORD = "1111"
MIN_PASSWORD_LEN = 4
COMPANY_NAME = "ATEC"
APP_SUBTITLE = "식사 예약 시스템"
AFFILIATES = ["에이텍컴퓨터", "에이텍모빌리티", "에이텍오토"]
DEFAULT_AFFILIATE = "에이텍컴퓨터"

PRIMARY_COLOR = "#E2186A"


def find_roster_file() -> Path | None:
    """프로젝트 폴더 또는 data 폴더의 인원명단 파일을 찾는다."""
    folders = []
    for folder in (BASE_DIR, DATA_DIR, DB_PATH.parent):
        if folder not in folders:
            folders.append(folder)
    for folder in folders:
        for name in ROSTER_FILENAMES:
            path = folder / name
            if path.is_file():
                return path
        for path in sorted(folder.glob("*명단*.xlsx")):
            if path.is_file():
                return path
        for path in sorted(folder.glob("*명단*.csv")):
            if path.is_file():
                return path
    return None
