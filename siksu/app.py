"""ATEC 식사 예약 시스템 (Streamlit PoC)."""

from __future__ import annotations

import json
from datetime import date, timedelta
from io import BytesIO

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

from auth import hash_password, validate_new_password
from config import (
    ADMIN_PASSWORD,
    ADMIN_SESSION_KEY,
    AFFILIATES,
    APP_SUBTITLE,
    CAFETERIA_AFFILIATE,
    CAFETERIA_USERNAME,
    COMPANY_NAME,
    DEFAULT_AFFILIATE,
    DEFAULT_PASSWORD,
    DINNER_DEADLINE,
    LOGO_PATH,
    LUNCH_DEADLINE,
    MEAL_YES,
    MENU_TEMPLATE_PATH,
    NAV_SESSION_KEY,
    USER_SESSION_KEY,
    WEEKDAYS,
    WEEKDAYS_BIZ,
)
from db import (
    actual_attendance_rows,
    add_single_employee,
    authenticate,
    checkin_map,
    delete_employee,
    delete_login_token,
    determine_apply_method,
    ensure_employee_qr_code,
    find_employee_for_checkin,
    get_auto_reservation_for_weekday,
    get_auto_reservation_map,
    get_connection,
    get_daily_application,
    get_employee,
    get_employee_by_token,
    issue_login_token,
    list_checkin_details,
    list_employees,
    list_menus,
    materialize_missing_applications,
    meal_counts,
    noshow_rows,
    record_checkin,
    replace_menus,
    reset_employee_password,
    resolve_applications_for_date,
    set_employee_flag,
    toggle_auto_cell,
    update_password,
    upsert_daily_application,
)
from init_db import initialize_database
from logic import (
    current_checkin_meal,
    is_dinner_closed,
    is_dinner_service_ended,
    is_lunch_closed,
    is_lunch_service_ended,
    meal_label,
    now_kst,
    today_kst,
    weekday_label,
)
from storage import storage_io
from theme import ATEC_CSS, BOTTOM_NAV_CSS
from menu_import import import_menus_from_workbook
from qr_checkin import employee_qr_payload, parse_employee_qr, qr_png_bytes

NAV_HOME = "홈"
NAV_MENU = "식단표"
NAV_AUTO = "자동예약"
NAV_QR = "QR코드"
NAV_MY = "내 정보"
NAV_ITEMS = [NAV_HOME, NAV_MENU, NAV_AUTO, NAV_QR, NAV_MY]


@st.cache_resource
def get_conn():
    initialize_database()
    return get_connection()


def inject_css() -> None:
    st.markdown(ATEC_CSS, unsafe_allow_html=True)


def current_user() -> dict | None:
    return st.session_state.get(USER_SESSION_KEY)


def is_cafeteria_user(user: dict | None) -> bool:
    if not user:
        return False
    if user.get("is_cafeteria"):
        return True
    return user.get("username") == CAFETERIA_USERNAME and user.get("affiliate") == CAFETERIA_AFFILIATE


def refresh_user(conn, user: dict) -> dict:
    latest = get_employee(conn, user["id"]) or user
    st.session_state[USER_SESSION_KEY] = latest
    return latest


def queue_storage(items: list[dict]) -> None:
    st.session_state["_write_store"] = items


def sync_browser_storage(conn):
    """로그인한 뒤에는 storage iframe을 다시 그리지 않아 본문 위젯이 가려지지 않게 한다."""
    pending = st.session_state.pop("_write_store", None) or []
    user = current_user()
    if user and not pending:
        return user

    token_op, token_val = "get", ""
    saved_op, saved_val = "get", ""
    for item in pending:
        if item.get("key") == "atec_token":
            token_op = item.get("op", "get")
            token_val = item.get("value", "")
        elif item.get("key") == "atec_saved_id":
            saved_op = item.get("op", "get")
            saved_val = item.get("value", "")

    try:
        token_res = storage_io(token_op, "atec_token", token_val, widget_key="boot_token")
        saved_res = storage_io(saved_op, "atec_saved_id", saved_val, widget_key="boot_saved_id")
    except Exception:
        token_res, saved_res = None, None

    saved_id = ""
    if isinstance(saved_res, dict):
        saved_id = saved_res.get("value", "") or ""
    elif isinstance(saved_res, str):
        saved_id = saved_res
    if saved_id:
        username, affiliate = parse_saved_login(saved_id)
        st.session_state["saved_login_id"] = username
        st.session_state["saved_login_affiliate"] = affiliate

    if user:
        return user

    token = ""
    if isinstance(token_res, dict):
        token = token_res.get("value", "") or ""
    elif isinstance(token_res, str):
        token = token_res
    if token:
        found = get_employee_by_token(conn, token)
        if found:
            st.session_state[USER_SESSION_KEY] = found
            st.session_state["auth_token"] = token
            st.rerun()
    return None


def parse_saved_login(raw: str) -> tuple[str, str]:
    value = (raw or "").strip()
    if not value:
        return "", DEFAULT_AFFILIATE
    if value.startswith("{"):
        try:
            data = json.loads(value)
            username = str(data.get("id") or data.get("username") or "").strip()
            affiliate = str(data.get("affiliate") or DEFAULT_AFFILIATE).strip()
            if affiliate not in AFFILIATES:
                affiliate = DEFAULT_AFFILIATE
            return username, affiliate
        except json.JSONDecodeError:
            return value, DEFAULT_AFFILIATE
    return value, DEFAULT_AFFILIATE


def render_brand() -> None:
    st.markdown('<div class="atec-logo">', unsafe_allow_html=True)
    if LOGO_PATH.exists():
        left, mid, right = st.columns([0.45, 2.1, 0.45])
        with mid:
            st.image(str(LOGO_PATH), width="stretch")
    else:
        st.markdown(f"<h1>{COMPANY_NAME}</h1>", unsafe_allow_html=True)
    st.markdown(f'<p class="atec-logo-sub">{APP_SUBTITLE}</p>', unsafe_allow_html=True)
    st.markdown("</div>", unsafe_allow_html=True)


def render_login() -> None:
    saved_id = st.session_state.get("saved_login_id", "")
    saved_affiliate = st.session_state.get("saved_login_affiliate", DEFAULT_AFFILIATE)
    if saved_id and not st.session_state.get("login_username"):
        st.session_state["login_username"] = saved_id
    if "login_affiliate" not in st.session_state:
        st.session_state["login_affiliate"] = (
            saved_affiliate if saved_affiliate in AFFILIATES else DEFAULT_AFFILIATE
        )

    render_brand()
    st.markdown('<div class="atec-card">', unsafe_allow_html=True)
    st.markdown("### 환영합니다")
    st.caption("식사 예약을 위해 로그인해 주세요.")

    with st.form("login_form", border=False, clear_on_submit=False):
        affiliate = st.selectbox("계열사", AFFILIATES, key="login_affiliate")
        username = st.text_input("아이디", key="login_username", placeholder="이름")
        password = st.text_input("비밀번호", type="password", key="login_password", placeholder="비밀번호")
        left, right = st.columns(2)
        with left:
            save_id = st.checkbox("아이디 저장", value=bool(saved_id))
        with right:
            auto_login = st.checkbox("자동 로그인")
        submitted = st.form_submit_button("로그인")
    st.markdown("</div>", unsafe_allow_html=True)

    if st.button(
        f"© {now_kst().year} {COMPANY_NAME}. All rights reserved.",
        key="cafe_gate",
        type="tertiary",
    ):
        st.session_state["cafe_taps"] = int(st.session_state.get("cafe_taps") or 0) + 1
        if st.session_state["cafe_taps"] >= 5:
            st.session_state["show_cafeteria_login"] = True
        st.rerun()

    if st.session_state.get("show_cafeteria_login"):
        st.markdown('<div class="atec-card">', unsafe_allow_html=True)
        st.markdown("##### 식당 체크인")
        st.caption("리더기 전용 화면입니다.")
        with st.form("cafeteria_login_form", border=False):
            cafe_pw = st.text_input("비밀번호", type="password", key="cafe_login_pw")
            keep = st.checkbox("이 기기에서 유지", key="cafe_keep")
            cafe_submitted = st.form_submit_button("체크인 시작")
        st.markdown("</div>", unsafe_allow_html=True)
        if cafe_submitted:
            conn = get_conn()
            cafe_user = authenticate(conn, CAFETERIA_USERNAME, cafe_pw or "", CAFETERIA_AFFILIATE)
            if not cafe_user or not is_cafeteria_user(cafe_user):
                st.error("비밀번호가 올바르지 않습니다.")
            else:
                st.session_state[USER_SESSION_KEY] = cafe_user
                persist = [{"op": "remove", "key": "atec_saved_id"}]
                if keep:
                    token = issue_login_token(conn, cafe_user["id"])
                    st.session_state["auth_token"] = token
                    persist.append({"op": "set", "key": "atec_token", "value": token})
                queue_storage(persist)
                st.rerun()

    if not submitted:
        return

    conn = get_conn()
    user = authenticate(conn, username, password, affiliate)
    if not user:
        st.error("계열사, 아이디 또는 비밀번호가 올바르지 않습니다.")
        return

    st.session_state[USER_SESSION_KEY] = user
    persist = []
    cafeteria = is_cafeteria_user(user)
    if save_id and not cafeteria:
        persist.append(
            {
                "op": "set",
                "key": "atec_saved_id",
                "value": json.dumps(
                    {"id": user["username"], "affiliate": user.get("affiliate") or affiliate},
                    ensure_ascii=False,
                ),
            }
        )
    else:
        persist.append({"op": "remove", "key": "atec_saved_id"})
    if auto_login:
        token = issue_login_token(conn, user["id"])
        st.session_state["auth_token"] = token
        persist.append({"op": "set", "key": "atec_token", "value": token})
    else:
        persist.append({"op": "remove", "key": "atec_token"})
    queue_storage(persist)
    st.rerun()


def render_password_change(conn, user: dict, *, forced: bool) -> None:
    if forced:
        render_brand()
    st.markdown('<div class="atec-card">', unsafe_allow_html=True)
    st.markdown("### 비밀번호 변경")
    if forced:
        st.warning("초기 비밀번호(1111)입니다. 계속 사용하려면 비밀번호를 변경해 주세요.")

    with st.form(f"pw_change_form_{int(forced)}", border=False, clear_on_submit=False):
        new_pw = st.text_input("새 비밀번호", type="password", key=f"new_pw_{int(forced)}")
        confirm = st.text_input("새 비밀번호 확인", type="password", key=f"confirm_pw_{int(forced)}")
        submitted = st.form_submit_button("비밀번호 변경")

    if submitted:
        error = validate_new_password(new_pw or "", confirm or "")
        if error:
            st.error(error)
        else:
            update_password(conn, user["id"], hash_password(new_pw))
            refresh_user(conn, user)
            st.success("비밀번호를 변경했습니다.")
            st.rerun()

    if forced and st.button("로그아웃", width="stretch", key="pw_logout"):
        delete_login_token(conn, st.session_state.get("auth_token"))
        queue_storage([{"op": "remove", "key": "atec_token"}])
        st.session_state.pop(USER_SESSION_KEY, None)
        st.session_state.pop("auth_token", None)
        st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)


def resolved_today_meals(conn, user: dict) -> tuple[int, int]:
    today = today_kst()
    saved = get_daily_application(conn, user["id"], today)
    auto = get_auto_reservation_for_weekday(conn, user["id"], today.weekday())
    if saved:
        return int(saved["lunch"]), int(saved["dinner"])
    if auto:
        return int(auto["lunch"]), int(auto["dinner"])
    return 0, 0


def save_today_choice(conn, user: dict, meal: str, value: int) -> None:
    today = today_kst()
    now = now_kst()
    lunch, dinner = resolved_today_meals(conn, user)
    if meal == "lunch":
        if is_lunch_closed(today, now):
            return
        lunch = value
    else:
        if is_dinner_closed(today, now):
            return
        dinner = value
    auto = get_auto_reservation_for_weekday(conn, user["id"], today.weekday())
    method = determine_apply_method(auto, lunch, dinner)
    upsert_daily_application(conn, user, today, lunch, dinner, method)


def apply_meal_choice(conn, user: dict, meal: str, choice: str | None, closed: bool, current: int) -> None:
    if closed or choice is None:
        return
    value = 1 if choice == "O" else 0
    if value == current:
        return
    save_today_choice(conn, user, meal, value)
    st.rerun()


def remaining_text(closed: bool, deadline_label: str) -> str:
    if closed:
        return "마감되었습니다"
    now = now_kst()
    deadline_dt = now.replace(
        hour=int(deadline_label[:2]),
        minute=int(deadline_label[3:]),
        second=0,
        microsecond=0,
    )
    minutes = max(int((deadline_dt - now).total_seconds() // 60), 0)
    hours, mins = divmod(minutes, 60)
    if hours:
        return f"마감까지 {hours}시간 {mins}분"
    return f"마감까지 {mins}분"


def render_home(conn, user: dict) -> None:
    today = today_kst()
    now = now_kst()
    lunch_closed = is_lunch_closed(today, now)
    dinner_closed = is_dinner_closed(today, now)
    lunch, dinner = resolved_today_meals(conn, user)
    lunch_count, dinner_count = meal_counts(conn, today)

    st.markdown(
        f"""
        <div class="hello-date">{today.month}월 {today.day}일 {weekday_label(today)}요일</div>
        <div class="hello-name">안녕하세요, {user['name']}님</div>
        """,
        unsafe_allow_html=True,
    )
    st.markdown('<div class="section-title">🍴 오늘의 예약</div>', unsafe_allow_html=True)

    with st.container(border=True):
        st.markdown("**☀️ 점심 예약**")
        st.caption(f"신청 {lunch_count}명 · {remaining_text(lunch_closed, LUNCH_DEADLINE.strftime('%H:%M'))}")
        lunch_choice = st.segmented_control(
            "점심 여부",
            options=["O", "X"],
            default="O" if lunch else "X",
            key="lunch_seg",
            disabled=lunch_closed,
            label_visibility="collapsed",
            width="stretch",
        )
        if lunch_closed:
            st.caption("점심은 마감되어 수정할 수 없습니다.")
    apply_meal_choice(conn, user, "lunch", lunch_choice, lunch_closed, lunch)

    with st.container(border=True):
        st.markdown("**🌙 저녁 예약**")
        st.caption(f"신청 {dinner_count}명 · {remaining_text(dinner_closed, DINNER_DEADLINE.strftime('%H:%M'))}")
        dinner_choice = st.segmented_control(
            "저녁 여부",
            options=["O", "X"],
            default="O" if dinner else "X",
            key="dinner_seg",
            disabled=dinner_closed,
            label_visibility="collapsed",
            width="stretch",
        )
        if dinner_closed:
            st.caption("저녁은 마감되어 수정할 수 없습니다.")
    apply_meal_choice(conn, user, "dinner", dinner_choice, dinner_closed, dinner)

    st.markdown('<div class="section-title">📒 오늘의 식단 (점심)</div>', unsafe_allow_html=True)
    menus = list_menus(conn, today, "lunch")
    if not menus:
        st.info("오늘 등록된 점심 식단이 없습니다.")
    else:
        grouped: dict[str, list] = {}
        for item in menus[:6]:
            grouped.setdefault(item["section"], []).append(item)
        blocks: list[str] = ['<div class="menu-panel">']
        for section, rows in grouped.items():
            blocks.append(f'<div class="menu-sec">{section}</div>')
            for item in rows:
                desc = f'<div class="desc">{item["description"]}</div>' if item["description"] else ""
                blocks.append(
                    f'<div class="menu-item"><div class="nm">{item["name"]}</div>{desc}</div>'
                )
        blocks.append("</div>")
        st.markdown("\n".join(blocks), unsafe_allow_html=True)
    if st.button("식단표 전체 보기", width="stretch"):
        st.session_state[NAV_SESSION_KEY] = NAV_MENU
        st.session_state["bottom_nav_pills"] = NAV_MENU
        st.rerun()


def weekdays_this_week(selected: object | None = None):
    today = today_kst()
    monday = today - timedelta(days=today.weekday())
    days = [monday + timedelta(days=i) for i in range(5)]
    if selected in days:
        return days, selected
    if today.weekday() < 5:
        return days, today
    return days, days[0]


def render_weekly_menu(conn, user: dict) -> None:
    days, selected = weekdays_this_week(st.session_state.get("menu_day"))
    day_options = [day.isoformat() for day in days]
    if st.session_state.get("menu_day_seg") not in day_options:
        st.session_state["menu_day_seg"] = selected.isoformat()
    if st.session_state.get("menu_meal_seg") not in {"lunch", "dinner"}:
        st.session_state["menu_meal_seg"] = "lunch"

    st.caption("주간 식단표")
    st.markdown(f"반갑습니다, **{user['name']}님**")

    chosen_iso = st.segmented_control(
        "요일 선택",
        options=day_options,
        key="menu_day_seg",
        format_func=lambda iso: f"{WEEKDAYS[date.fromisoformat(iso).weekday()]}\n{date.fromisoformat(iso).day}",
        label_visibility="collapsed",
        width="stretch",
    )
    meal_type = st.segmented_control(
        "점심/저녁",
        options=["lunch", "dinner"],
        key="menu_meal_seg",
        format_func=lambda value: "점심" if value == "lunch" else "저녁",
        label_visibility="collapsed",
        width="stretch",
    )
    meal_type = meal_type or "lunch"
    chosen_iso = chosen_iso or selected.isoformat()
    selected_day = date.fromisoformat(chosen_iso)
    st.session_state["menu_day"] = selected_day
    st.session_state["menu_meal"] = meal_type

    meal_label_kr = "점심" if meal_type == "lunch" else "저녁"
    st.markdown(f"### 오늘의 {meal_label_kr} 메뉴")
    st.caption("식단은 텍스트로만 제공됩니다. 당일 사정에 따라 메뉴가 달라질 수 있습니다.")

    items = list_menus(conn, selected_day, meal_type)
    if not items:
        st.info("선택한 날짜의 식단이 없습니다.")
        return

    grouped: dict[str, list] = {}
    for item in items:
        grouped.setdefault(item["section"], []).append(item)
    blocks: list[str] = ['<div class="menu-panel">']
    for section, rows in grouped.items():
        blocks.append(f'<div class="menu-sec">{section}</div>')
        for item in rows:
            desc = f'<div class="desc">{item["description"]}</div>' if item["description"] else ""
            blocks.append(f'<div class="menu-item"><div class="nm">{item["name"]}</div>{desc}</div>')
    blocks.append("</div>")
    st.markdown("\n".join(blocks), unsafe_allow_html=True)


def cell_icon(meal: str, on: int) -> str:
    if meal == "lunch":
        return "☀️" if on else "·"
    return "🌙" if on else "·"


def render_auto(conn, user: dict) -> None:
    user = refresh_user(conn, user)
    enabled = bool(user.get("auto_enabled"))
    pattern = get_auto_reservation_map(conn, user["id"])

    head_l, head_r = st.columns([3, 1])
    with head_l:
        st.markdown("### 자동 예약 설정")
    with head_r:
        new_enabled = st.toggle(" ", value=enabled, key="auto_master", label_visibility="collapsed")
    if new_enabled != enabled:
        set_employee_flag(conn, user["id"], "auto_enabled", int(new_enabled))
        refresh_user(conn, user)
        st.rerun()

    if new_enabled:
        st.info("자동 예약이 활성화되어 있습니다. 수정하려면 토글을 꺼주세요.")
        st.caption("요일별 설정  ·  활성화됨")
    else:
        st.caption("토글을 끈 뒤 요일별 점심/저녁을 눌러 저장하세요.")

    header = st.columns([1.2, 1, 1])
    header[0].markdown("**요일**")
    header[1].markdown("**점심**")
    header[2].markdown("**저녁**")
    for idx, label in enumerate(WEEKDAYS_BIZ):
        row = st.columns([1.2, 1, 1])
        current = pattern.get(idx, {"lunch": 0, "dinner": 0})
        row[0].markdown(f"**{label}**")
        with row[1]:
            if st.button(
                cell_icon("lunch", current["lunch"]),
                key=f"auto_l_{idx}",
                disabled=new_enabled,
                type="primary" if current["lunch"] else "secondary",
                width="stretch",
            ):
                toggle_auto_cell(conn, user["id"], idx, "lunch")
                st.rerun()
        with row[2]:
            if st.button(
                cell_icon("dinner", current["dinner"]),
                key=f"auto_d_{idx}",
                disabled=new_enabled,
                type="primary" if current["dinner"] else "secondary",
                width="stretch",
            ):
                toggle_auto_cell(conn, user["id"], idx, "dinner")
                st.rerun()

    st.markdown(
        '<div class="legend">☀️ 점심 예약됨 &nbsp;&nbsp;🌙 저녁 예약됨 &nbsp;&nbsp;· 안먹음</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        '<div class="info-box">자동 예약이 켜져 있으면 매일 마감 전 해당 요일 기본값이 신청값으로 반영됩니다. '
        "예외가 있는 날만 홈 화면에서 오늘 값만 바꾸면 됩니다.</div>",
        unsafe_allow_html=True,
    )


def applications_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    data = [
        {
            "날짜": row["apply_date"],
            "계열사": row.get("affiliate") or "",
            "이름": row["name"],
            "부서": row["department"],
            "점심여부": meal_label(row["lunch"]),
            "석식여부": meal_label(row["dinner"]),
            "반영방식": row["apply_method"],
            "제출시각": row.get("submitted_at") or "-",
        }
        for row in rows
    ]
    return pd.DataFrame(data)


def to_excel_bytes(df: pd.DataFrame, sheet_name: str = "식수신청") -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name=sheet_name)
    return buffer.getvalue()


def render_qr(conn, user: dict) -> None:
    user = refresh_user(conn, user)
    code = ensure_employee_qr_code(conn, user["id"])
    user["qr_code"] = code
    payload = employee_qr_payload(user)
    png = qr_png_bytes(payload)
    st.markdown("### QR코드")
    st.caption("식당 입구 리더기에 이 코드를 보여 주세요. 저장한 이미지는 다시 받아도 같은 코드라 계속 쓸 수 있습니다.")
    st.markdown('<div class="qr-wrap">', unsafe_allow_html=True)
    st.image(png, width="stretch")
    st.markdown("</div>", unsafe_allow_html=True)
    st.markdown(f'<div class="qr-name">{user["name"]}</div>', unsafe_allow_html=True)
    st.caption(f"{user.get('affiliate') or ''}  ·  {user['department']}")
    st.download_button(
        "QR 이미지 저장",
        data=png,
        file_name=f"ATEC_QR_{user['name']}.png",
        mime="image/png",
        width="stretch",
        type="primary",
    )
    st.markdown(
        '<div class="info-box">신청만 하고 식당에서 스캔하지 않으면 노쇼로 집계됩니다.</div>',
        unsafe_allow_html=True,
    )


def apply_checkin(conn, raw: str, meal_type: str) -> tuple[str, str]:
    employee_id, username, qr_code = parse_employee_qr(raw)
    employee = find_employee_for_checkin(conn, employee_id, username, qr_code)
    if not employee:
        return "error", "등록되지 않은 QR입니다."
    status = record_checkin(conn, employee["id"], meal_type)
    meal_kr = "점심" if meal_type == "lunch" else "저녁"
    if status == "duplicate":
        return "info", f"{employee['name']}님은 이미 {meal_kr} 체크인되어 있습니다."
    return "ok", f"{employee['name']}님 {meal_kr} 실식수 체크인 완료"


def _scan_clock(value: str) -> str:
    text = value or ""
    if "T" in text and len(text) >= 19:
        return text[11:19]
    return text


def keep_scan_focus() -> None:
    components.html(
        """
        <script>
        const focusScan = () => {
          const doc = window.parent.document;
          const input = Array.from(doc.querySelectorAll('input')).find(
            (el) => (el.placeholder || '').includes('리더기')
          );
          if (input) input.focus();
        };
        focusScan();
        setInterval(focusScan, 400);
        </script>
        """,
        height=0,
    )


@st.fragment(run_every=1)
def render_cafeteria_live_board() -> None:
    conn = get_conn()
    day_iso = st.session_state.get("cafe_day") or today_kst().isoformat()
    selected_day = date.fromisoformat(day_iso)
    lunch_rows = list_checkin_details(conn, selected_day, "lunch")
    dinner_rows = list_checkin_details(conn, selected_day, "dinner")
    c1, c2 = st.columns(2)
    c1.metric("점심 실식수", f"{len(lunch_rows)}명")
    c2.metric("석식 실식수", f"{len(dinner_rows)}명")
    st.markdown("**점심 12:00–13:30**")
    if not lunch_rows:
        st.caption("아직 없습니다.")
    else:
        for row in lunch_rows:
            st.markdown(f"`{_scan_clock(row['checked_at'])}`  **{row['name']}**")
            st.caption(f"{row.get('affiliate') or ''} · {row['department']}")
    st.markdown("**석식 17:00–18:00**")
    if not dinner_rows:
        st.caption("아직 없습니다.")
    else:
        for row in dinner_rows:
            st.markdown(f"`{_scan_clock(row['checked_at'])}`  **{row['name']}**")
            st.caption(f"{row.get('affiliate') or ''} · {row['department']}")


def render_cafeteria_desk(conn, user: dict) -> None:
    today = today_kst()
    monday = today - timedelta(days=today.weekday())
    days = [monday + timedelta(days=i) for i in range(5)]
    options = [day.isoformat() for day in days]
    default_day = today.isoformat() if today.isoformat() in options else options[0]
    if st.session_state.get("cafe_day") not in options:
        st.session_state["cafe_day"] = default_day

    st.markdown("### 식당 식수 체크인")
    meal = current_checkin_meal()
    if meal == "lunch":
        st.success("점심 체크인 중  ·  12:00–13:30")
    elif meal == "dinner":
        st.success("석식 체크인 중  ·  17:00–18:00")
    else:
        st.warning("지금은 체크인 시간이 아닙니다. 점심 12:00–13:30, 석식 17:00–18:00")

    last = st.session_state.get("cafe_last_msg")
    kind = st.session_state.get("cafe_last_kind")
    if last and kind == "ok":
        st.success(last)
    elif last and kind == "info":
        st.info(last)
    elif last:
        st.error(last)

    with st.form("cafe_scan_form", clear_on_submit=True):
        code = st.text_input(
            "바코드",
            placeholder="리더기 스캔 대기 중...",
            label_visibility="collapsed",
        )
        scanned = st.form_submit_button("체크인")
    if scanned:
        if meal is None:
            st.session_state["cafe_last_kind"] = "error"
            st.session_state["cafe_last_msg"] = "점심(12:00~13:30) 또는 석식(17:00~18:00)에만 체크인됩니다."
        elif not (code or "").strip():
            st.session_state["cafe_last_kind"] = "error"
            st.session_state["cafe_last_msg"] = "QR 값이 없습니다."
        else:
            result_kind, message = apply_checkin(conn, code, meal)
            st.session_state["cafe_last_kind"] = result_kind
            st.session_state["cafe_last_msg"] = message
        st.rerun()

    keep_scan_focus()

    st.segmented_control(
        "요일",
        options=options,
        key="cafe_day",
        format_func=lambda iso: f"{WEEKDAYS[date.fromisoformat(iso).weekday()]}\n{date.fromisoformat(iso).day}",
        label_visibility="collapsed",
        width="stretch",
    )
    render_cafeteria_live_board()

    if st.button("로그아웃", width="stretch", key="cafe_logout"):
        delete_login_token(conn, st.session_state.get("auth_token"))
        queue_storage([{"op": "remove", "key": "atec_token"}])
        st.session_state.pop(USER_SESSION_KEY, None)
        st.session_state.pop("auth_token", None)
        st.session_state.pop("cafe_last_msg", None)
        st.rerun()


def render_checkin_panel(conn) -> None:
    default_meal = current_checkin_meal() or "lunch"
    st.markdown("##### 식수 체크인")
    st.caption("식당에 설치된 바코드 리더기로 QR을 스캔하면 실식수가 기록됩니다.")
    if st.session_state.get("checkin_meal") not in {"lunch", "dinner"}:
        st.session_state["checkin_meal"] = default_meal
    with st.form("checkin_form", clear_on_submit=True):
        meal = st.radio(
            "구분",
            ["lunch", "dinner"],
            format_func=lambda value: "점심" if value == "lunch" else "저녁",
            horizontal=True,
            key="checkin_meal",
        )
        code = st.text_input("QR/바코드", placeholder="스캔 대기 중...")
        submitted = st.form_submit_button("체크인")
    if not submitted:
        return
    if not (code or "").strip():
        st.error("QR 값이 없습니다.")
        return
    kind, message = apply_checkin(conn, code, meal or default_meal)
    if kind == "ok":
        st.success(message)
    elif kind == "info":
        st.info(message)
    else:
        st.error(message)


def render_checkin_kiosk(conn) -> None:
    st.markdown("### 식수 체크인")
    if st.button("← 관리자로"):
        st.session_state["kiosk_checkin"] = False
        st.rerun()
    render_checkin_panel(conn)
    cmap = checkin_map(conn, today_kst())
    lunch_n = sum(1 for meals in cmap.values() if "lunch" in meals)
    dinner_n = sum(1 for meals in cmap.values() if "dinner" in meals)
    left, right = st.columns(2)
    left.metric("오늘 점심 실식수", f"{lunch_n}명")
    right.metric("오늘 저녁 실식수", f"{dinner_n}명")


def attendance_to_dataframe(rows: list[dict]) -> pd.DataFrame:
    data = [
        {
            "날짜": row["apply_date"],
            "계열사": row.get("affiliate") or "",
            "이름": row["name"],
            "부서": row["department"],
            "점심실식수": meal_label(row["lunch_attended"]),
            "저녁실식수": meal_label(row["dinner_attended"]),
            "점심체크인": row.get("lunch_checked_at") or "-",
            "저녁체크인": row.get("dinner_checked_at") or "-",
        }
        for row in rows
    ]
    return pd.DataFrame(data)


def render_admin(conn) -> None:
    if st.session_state.get("kiosk_checkin"):
        render_checkin_kiosk(conn)
        return

    st.markdown("### 관리자 대시보드")
    st.caption("공무팀·급식 담당자용입니다. 신청부터 집계까지 승인 없이 자동 반영됩니다.")
    if st.button("← 내 정보로"):
        st.session_state["show_admin"] = False
        st.session_state[NAV_SESSION_KEY] = NAV_MY
        st.rerun()

    today = today_kst()
    today_noshows = noshow_rows(conn, today)
    lunch_noshows = [row for row in today_noshows if row["noshow_meal"] == "점심"]
    dinner_noshows = [row for row in today_noshows if row["noshow_meal"] == "저녁"]
    today_checkins = checkin_map(conn, today)
    lunch_actual = sum(1 for meals in today_checkins.values() if "lunch" in meals)
    dinner_actual = sum(1 for meals in today_checkins.values() if "dinner" in meals)

    st.markdown("##### 오늘 실식수 / 노쇼")
    a1, a2 = st.columns(2)
    a1.metric("점심 실식수", f"{lunch_actual}명")
    a2.metric("저녁 실식수", f"{dinner_actual}명")
    b1, b2 = st.columns(2)
    b1.metric("점심 노쇼", f"{len(lunch_noshows)}명")
    b2.metric("저녁 노쇼", f"{len(dinner_noshows)}명")
    if today_noshows:
        st.dataframe(
            pd.DataFrame(
                [
                    {
                        "구분": row["noshow_meal"],
                        "이름": row["name"],
                        "부서": row["department"],
                        "계열사": row.get("affiliate") or "",
                    }
                    for row in today_noshows
                ]
            ),
            width="stretch",
            hide_index=True,
        )
    elif is_lunch_service_ended(today) or is_dinner_service_ended(today):
        st.caption("오늘은 노쇼가 없습니다.")
    else:
        st.caption("식사 시간이 끝나면, 신청 후 식당에서 스캔하지 않은 인원이 노쇼로 표시됩니다.")

    if st.button("체크인 전용 화면", width="stretch"):
        st.session_state["kiosk_checkin"] = True
        st.rerun()
    render_checkin_panel(conn)

    selected_date = st.date_input("조회 날짜", value=today_kst(), format="YYYY-MM-DD")
    materialize_missing_applications(conn, selected_date)
    rows = resolve_applications_for_date(conn, selected_date)
    df = applications_to_dataframe(rows)
    lunch_count = int((df["점심여부"] == MEAL_YES).sum()) if not df.empty else 0
    dinner_count = int((df["석식여부"] == MEAL_YES).sum()) if not df.empty else 0

    c1, c2, c3 = st.columns(3)
    c1.metric("점심 신청", f"{lunch_count}명")
    c2.metric("저녁 신청", f"{dinner_count}명")
    c3.metric("등록 직원", f"{len(rows)}명")

    st.subheader("부서별 집계")
    if df.empty:
        st.info("표시할 데이터가 없습니다.")
    else:
        dept_df = (
            df.assign(
                점심신청=lambda x: (x["점심여부"] == MEAL_YES).astype(int),
                석식신청=lambda x: (x["석식여부"] == MEAL_YES).astype(int),
            )
            .groupby("부서", as_index=False)
            .agg(인원수=("이름", "count"), 점심신청=("점심신청", "sum"), 석식신청=("석식신청", "sum"))
            .sort_values("부서")
        )
        st.dataframe(dept_df, width="stretch", hide_index=True)

    st.subheader("전체 신청자 리스트")
    st.dataframe(df, width="stretch", hide_index=True)

    st.subheader("실식수 엑셀 다운로드")
    st.caption("QR 체크인한 실식수 인원만 기간을 지정해 내려받습니다. 노쇼는 포함되지 않습니다.")
    col_a, col_b = st.columns(2)
    with col_a:
        start_date = st.date_input("기간 시작", value=selected_date, format="YYYY-MM-DD", key="export_start")
    with col_b:
        end_date = st.date_input("기간 종료", value=selected_date, format="YYYY-MM-DD", key="export_end")
    if start_date <= end_date:
        export_df = attendance_to_dataframe(actual_attendance_rows(conn, start_date, end_date))
        st.download_button(
            "실식수 엑셀 다운로드 (.xlsx)",
            data=to_excel_bytes(export_df, "실식수"),
            file_name=f"실식수_{start_date.isoformat()}_{end_date.isoformat()}.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            width="stretch",
        )
    else:
        st.error("기간 시작이 종료보다 늦을 수 없습니다.")

    with st.expander("식단표 엑셀 업로드", expanded=True):
        st.caption("주간 메뉴표 양식(날짜 + 중식/석식)을 그대로 올리면 해당 주 식단이 등록됩니다.")
        if MENU_TEMPLATE_PATH.exists():
            st.download_button(
                "식단표 양식 다운로드",
                data=MENU_TEMPLATE_PATH.read_bytes(),
                file_name="식단표_양식.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                width="stretch",
                key="dl_menu_template",
            )
        menu_file = st.file_uploader("식단표 엑셀 선택", type=["xlsx", "xls"], key="menu_xlsx")
        if menu_file is not None:
            file_id = f"{menu_file.name}-{menu_file.size}"
            if st.session_state.get("last_menu_file") != file_id:
                try:
                    result = import_menus_from_workbook(conn, menu_file)
                    st.session_state["last_menu_file"] = file_id
                    st.session_state["last_menu_result"] = result
                except Exception as exc:
                    st.session_state["last_menu_file"] = file_id
                    st.session_state["last_menu_result"] = {"error": str(exc)}
            saved = st.session_state.get("last_menu_result") or {}
            if saved.get("error"):
                st.error(f"식단표 등록 실패: {saved['error']}")
            elif saved.get("start"):
                st.success(
                    f"{saved['start'].isoformat()} ~ {saved['end'].isoformat()} "
                    f"식단 {saved['meal_slots']}건, 메뉴 {saved['item_count']}개를 등록했습니다."
                )

    with st.expander("하루 식단 직접 수정"):
        menu_date = st.date_input("식단 날짜", value=today_kst(), key="admin_menu_date")
        meal_type = st.radio("구분", ["lunch", "dinner"], format_func=lambda x: "점심" if x == "lunch" else "저녁", horizontal=True)
        existing = list_menus(conn, menu_date, meal_type)
        default_text = "\n".join(
            f"{row['section']}|{row['name']}|{row['description'] or ''}" for row in existing
        )
        raw = st.text_area("한 줄에 구간|메뉴명|설명", value=default_text, height=160)
        if st.button("식단 저장"):
            items = []
            for line in raw.splitlines():
                parts = [p.strip() for p in line.split("|")]
                if len(parts) >= 2 and parts[0] and parts[1]:
                    items.append((parts[0], parts[1], parts[2] if len(parts) > 2 else ""))
            replace_menus(conn, menu_date, meal_type, items)
            st.success("식단을 저장했습니다.")

    with st.expander("인원 명단", expanded=True):
        me = current_user() or {}
        employees = list_employees(conn)
        st.caption(
            f"총 {len(employees)}명. 프로젝트 폴더에 `인원명단.xlsx`(이름, 부서, 계열사)를 넣으면 시작할 때 불러옵니다. "
            "PW초기화하면 비밀번호가 1111이 되고, 다음 로그인에서 새로 바꿔야 합니다."
        )
        reset_msg = st.session_state.pop("pw_reset_msg", None)
        if reset_msg:
            st.success(reset_msg)

        st.markdown("##### 한 명 추가")
        with st.form("add_one_emp", border=False):
            new_name = st.text_input("이름", key="add_emp_name")
            new_dept = st.text_input("부서", key="add_emp_dept")
            new_aff = st.selectbox("계열사", AFFILIATES, key="add_emp_aff")
            add_clicked = st.form_submit_button("추가")
        if add_clicked:
            try:
                status = add_single_employee(conn, new_name, new_dept, new_aff)
            except ValueError as exc:
                st.error(str(exc))
            else:
                if status == "updated":
                    st.warning("이미 있는 직원이어서 계열사만 수정했습니다.")
                st.rerun()

        filter_options = ["전체"] + AFFILIATES
        if st.session_state.get("emp_aff_filter") not in filter_options:
            st.session_state["emp_aff_filter"] = "전체"
        aff_filter = st.selectbox("계열사 보기", filter_options, key="emp_aff_filter")
        keyword = st.text_input("이름 검색", key="emp_search", placeholder="이름")
        keyword = (keyword or "").strip()
        shown = [
            emp
            for emp in employees
            if (aff_filter == "전체" or emp.get("affiliate") == aff_filter)
            and (not keyword or keyword in (emp.get("name") or ""))
        ]
        st.caption(f"{len(shown)}명 표시")
        for emp in shown:
            left, mid, right = st.columns([3.6, 1.4, 1.1])
            with left:
                st.markdown(f"**{emp['name']}**")
                st.caption(f"{emp.get('affiliate') or '-'}  ·  {emp['department']}")
            is_self = me.get("id") == emp["id"]
            with mid:
                if st.button("PW초기화", key=f"reset_pw_{emp['id']}", disabled=is_self, width="stretch"):
                    reset_employee_password(conn, emp["id"])
                    st.session_state["pw_reset_msg"] = (
                        f"{emp['name']} 비밀번호를 1111로 초기화했습니다. 다음 로그인 때 새 비밀번호로 바꿔야 합니다."
                    )
                    st.rerun()
            with right:
                if st.button("삭제", key=f"del_emp_{emp['id']}", disabled=is_self, width="stretch"):
                    delete_employee(conn, emp["id"])
                    st.rerun()


def render_mypage(conn, user: dict) -> None:
    user = refresh_user(conn, user)
    st.markdown("### 내 정보")
    st.markdown('<div class="atec-card">', unsafe_allow_html=True)
    st.markdown(f"**{user['name']}**")
    st.caption(
        f"{user.get('affiliate') or DEFAULT_AFFILIATE}  ·  {user['department']}  ·  아이디 {user['username']}"
    )
    st.markdown("</div>", unsafe_allow_html=True)

    with st.expander("비밀번호 변경"):
        render_password_change(conn, user, forced=False)

    if user.get("is_admin"):
        if st.button("관리자 대시보드", type="primary", width="stretch"):
            st.session_state["show_admin"] = True
            st.rerun()
    else:
        with st.expander("관리자 입장"):
            pw = st.text_input("관리자 비밀번호", type="password", key="admin_gate")
            if st.button("입장"):
                if pw == ADMIN_PASSWORD:
                    st.session_state[ADMIN_SESSION_KEY] = True
                    st.session_state["show_admin"] = True
                    st.rerun()
                else:
                    st.error("비밀번호가 올바르지 않습니다.")

    if st.button("로그아웃", width="stretch"):
        delete_login_token(conn, st.session_state.get("auth_token"))
        queue_storage([{"op": "remove", "key": "atec_token"}])
        st.session_state.pop(USER_SESSION_KEY, None)
        st.session_state.pop("auth_token", None)
        st.session_state["show_admin"] = False
        st.rerun()


def render_nav(current: str) -> str:
    st.markdown(BOTTOM_NAV_CSS, unsafe_allow_html=True)
    if st.session_state.get("bottom_nav_pills") not in NAV_ITEMS:
        st.session_state["bottom_nav_pills"] = current
    chosen = st.pills(
        "하단 메뉴",
        options=NAV_ITEMS,
        key="bottom_nav_pills",
        label_visibility="collapsed",
        width="stretch",
        wrap=False,
        format_func=lambda name: {
            NAV_HOME: "🏠 홈",
            NAV_MENU: "🍴 식단표",
            NAV_AUTO: "📅 자동예약",
            NAV_QR: "🔳 QR",
            NAV_MY: "👤 내정보",
        }[name],
    )
    return chosen or current


def main() -> None:
    st.set_page_config(
        page_title=f"{COMPANY_NAME} 식사 예약",
        page_icon="🍱",
        layout="centered",
        initial_sidebar_state="collapsed",
    )
    inject_css()
    conn = get_conn()
    user = sync_browser_storage(conn)

    if not user:
        render_login()
        return

    if is_cafeteria_user(user):
        render_cafeteria_desk(conn, user)
        return

    if user.get("must_change_password"):
        render_password_change(conn, user, forced=True)
        return

    if st.session_state.get("show_admin"):
        render_admin(conn)
        return

    page = st.session_state.get(NAV_SESSION_KEY, NAV_HOME)
    if page == NAV_HOME:
        render_home(conn, user)
    elif page == NAV_MENU:
        render_weekly_menu(conn, user)
    elif page == NAV_AUTO:
        render_auto(conn, user)
    elif page == NAV_QR:
        render_qr(conn, user)
    else:
        render_mypage(conn, user)

    selected = render_nav(page)
    if selected != page:
        st.session_state[NAV_SESSION_KEY] = selected
        st.rerun()


if __name__ == "__main__":
    main()
