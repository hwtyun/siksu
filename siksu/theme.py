"""ATEC 시그니처 컬러 모바일 UI."""

ATEC_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+KR:wght@400;500;600;700;800&display=swap');

html, body, [class*="css"] {
    font-family: "Noto Sans KR", sans-serif;
}

.stApp {
    background: linear-gradient(180deg, #FFE8F0 0%, #FFF7F9 120px, #F6F7FB 320px, #F6F7FB 100%);
}

header[data-testid="stHeader"],
[data-testid="stToolbar"],
[data-testid="stDecoration"],
#MainMenu,
footer,
[data-testid="stStatusWidget"],
[data-testid="collapsedControl"],
[data-testid="stSidebar"],
[data-testid="stSidebarCollapsedControl"] {
    display: none !important;
}

.block-container {
    padding: 0.6rem 1rem 7.2rem 1rem !important;
    max-width: 430px !important;
}

div[data-testid="stVerticalBlock"] {
    gap: 0.65rem;
}

.atec-logo {
    text-align: center;
    padding: 1.6rem 0 0.5rem 0;
}
.atec-logo h1 {
    color: #E2186A;
    font-size: 2.4rem;
    font-weight: 800;
    letter-spacing: 0.08em;
    margin: 0;
}
.atec-logo-sub,
.atec-logo p {
    color: #8A8FA3;
    margin: 0.45rem 0 0.2rem 0;
    font-size: 0.95rem;
    text-align: center;
}
div[data-testid="stImage"] img {
    object-fit: contain;
}
.atec-logo div[data-testid="stImage"] img {
    max-height: 56px;
}
.qr-wrap {
    text-align: center;
    margin: 0.4rem 0 0.2rem 0;
}
.qr-wrap div[data-testid="stImage"] img {
    width: min(100%, 340px) !important;
    max-width: 340px !important;
    max-height: none !important;
    height: auto !important;
}

.atec-card {
    background: #fff;
    border-radius: 22px;
    box-shadow: 0 10px 30px rgba(226, 24, 106, 0.08);
    padding: 1.3rem 1.15rem 1.2rem 1.15rem;
    margin-bottom: 0.8rem;
}
.atec-card h3 {
    margin: 0 0 0.25rem 0;
    font-size: 1.35rem;
    color: #1F2430;
}
.atec-muted {
    color: #8A8FA3;
    font-size: 0.9rem;
}

.hello-date {
    color: #E2186A;
    font-size: 0.86rem;
    font-weight: 600;
    margin-bottom: 0.15rem;
}
.hello-name {
    font-size: 1.55rem;
    font-weight: 800;
    color: #1F2430;
    margin: 0 0 0.9rem 0;
}

.section-title {
    display: flex;
    align-items: center;
    gap: 0.4rem;
    font-weight: 800;
    color: #2A2F3A;
    margin: 1rem 0 0.7rem 0;
    font-size: 1.02rem;
}

.resv-card {
    background: #fff;
    border-radius: 20px;
    box-shadow: 0 8px 24px rgba(31, 36, 48, 0.06);
    padding: 1rem 1.05rem 0.85rem 1.05rem;
    margin: 0 0 0.35rem 0;
}
.resv-card .title {
    font-size: 1.05rem;
    font-weight: 800;
    color: #1F2430;
    margin: 0;
}
.resv-card .meta {
    color: #8A8FA3;
    font-size: 0.82rem;
    margin-top: 0.28rem;
}
.resv-card .closed {
    margin-top: 0.55rem;
    background: #FFF1F4;
    color: #C2185B;
    border-radius: 10px;
    padding: 0.45rem 0.65rem;
    font-size: 0.8rem;
    font-weight: 700;
}

.menu-panel {
    display: flex;
    flex-direction: column;
    gap: 0.45rem;
}
.menu-sec {
    color: #E2186A;
    font-size: 0.8rem;
    font-weight: 800;
    margin: 0.35rem 0 0 0.15rem;
}
.menu-panel .menu-sec:first-child {
    margin-top: 0;
}
.menu-item {
    background: #fff;
    border-radius: 16px;
    padding: 0.9rem 1rem;
    box-shadow: 0 6px 18px rgba(31, 36, 48, 0.05);
}
.menu-item .nm {
    font-size: 1.02rem;
    font-weight: 800;
    color: #222;
}
.menu-item .desc {
    color: #8A8FA3;
    font-size: 0.82rem;
    margin-top: 0.15rem;
}

.meal-card {
    background: #fff;
    border-radius: 18px;
    box-shadow: 0 8px 24px rgba(31, 36, 48, 0.06);
    padding: 0.95rem 0.9rem;
    margin-bottom: 0.65rem;
}
.meal-kicker {
    font-size: 0.78rem;
    color: #9AA0B4;
}

.auto-table {
    width: 100%;
    border-collapse: collapse;
    background: #fff;
    border-radius: 16px;
    overflow: hidden;
    box-shadow: 0 8px 24px rgba(31, 36, 48, 0.06);
}
.auto-table th {
    background: #F7F8FC;
    color: #6B7287;
    font-size: 0.8rem;
    padding: 0.7rem 0.4rem;
    font-weight: 700;
}
.auto-table td {
    text-align: center;
    padding: 0.7rem 0.3rem;
    border-top: 1px solid #F1F2F6;
    font-weight: 700;
    color: #333;
}
.legend {
    color: #8A8FA3;
    font-size: 0.82rem;
    line-height: 1.7;
    margin: 0.6rem 0;
}
.info-box {
    background: #F4F6FB;
    border-radius: 14px;
    padding: 0.85rem 0.95rem;
    color: #5B6172;
    font-size: 0.84rem;
    line-height: 1.55;
}

.copyright {
    text-align: center;
    color: #B0B4C3;
    font-size: 0.78rem;
    margin-top: 1.4rem;
}
.st-key-cafe_gate {
    margin-top: 0.8rem;
}
.st-key-cafe_gate button {
    background: transparent !important;
    border: none !important;
    color: #B0B4C3 !important;
    box-shadow: none !important;
    font-size: 0.78rem !important;
    font-weight: 400 !important;
    min-height: 1.6rem !important;
    width: 100% !important;
}
.st-key-cafe_gate button:hover {
    background: transparent !important;
    color: #8A90A2 !important;
}
.qr-name {
    text-align: center;
    font-size: 1.25rem;
    font-weight: 800;
    color: #1F2430;
    margin: 0.7rem 0 0.15rem 0;
}

div.stButton > button {
    border-radius: 12px;
    font-weight: 700;
    min-height: 2.6rem;
}
div.stButton > button[kind="primary"] {
    background: #E2186A;
    border-color: #E2186A;
}
div.stButton > button[kind="primary"]:hover {
    background: #C41258;
    border-color: #C41258;
}
div.stButton > button[kind="secondary"] {
    background: #F3F4F8;
    color: #6B7287;
    border: 1px solid #E4E6EE;
}

div[data-testid="stTextInput"] input {
    border-radius: 12px;
    min-height: 2.8rem;
    background: #F7F8FC;
    border: 1px solid #EEF0F5;
}

div[data-testid="stCheckbox"] label {
    font-size: 0.9rem;
}

.nav-spacer { height: 0.2rem; }

[data-testid="stFormSubmitButton"] button {
    background: #E2186A !important;
    border-color: #E2186A !important;
    color: white !important;
    border-radius: 12px !important;
    height: 2.9rem !important;
    font-weight: 800 !important;
    width: 100%;
}

div[data-testid="stAlert"] {
    border-radius: 14px;
}

div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
    border-radius: 12px;
    min-height: 2.8rem;
    background: #F7F8FC;
    border: 1px solid #EEF0F5;
}

div[data-testid="stCustomComponentV1"] {
    height: 0 !important;
    min-height: 0 !important;
    max-height: 0 !important;
    overflow: hidden !important;
    margin: 0 !important;
    padding: 0 !important;
}

iframe[title*="atec_local_storage"],
iframe[title*="local_storage"] {
    display: none !important;
    height: 0 !important;
    position: absolute !important;
}
</style>
"""

BOTTOM_NAV_CSS = """
<style>
div[data-testid="stVerticalBlockBorderWrapper"] {
    background: #ffffff;
    border: 1px solid #EEF0F5 !important;
    border-radius: 18px !important;
    padding: 0.35rem 0.15rem 0.45rem 0.15rem;
    margin-bottom: 0.55rem;
}
.st-key-bottom_nav_pills {
    position: fixed !important;
    left: 0 !important;
    right: 0 !important;
    bottom: 0 !important;
    z-index: 1000;
    background: #ffffff;
    border-top: 1px solid #ECEFF3;
    padding: 0.45rem 0.6rem 0.9rem 0.6rem;
    max-width: 430px;
    margin: 0 auto;
}
.st-key-bottom_nav_pills [data-testid="stWidgetLabel"] {
    display: none !important;
}
.st-key-bottom_nav_pills div[role="group"],
.st-key-bottom_nav_pills [data-testid="stButtonGroup"] {
    display: flex !important;
    width: 100% !important;
    justify-content: space-between !important;
    gap: 0.25rem !important;
}
.st-key-bottom_nav_pills button {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    border: none !important;
    background: transparent !important;
    box-shadow: none !important;
    color: #9AA0B4 !important;
    font-size: 0.62rem !important;
    font-weight: 700 !important;
    min-height: 2.4rem !important;
    padding: 0.1rem 0.05rem !important;
}
.st-key-bottom_nav_pills button[kind="primary"],
.st-key-bottom_nav_pills button[aria-pressed="true"] {
    color: #E2186A !important;
    background: #FFE8F0 !important;
    border-radius: 12px !important;
}
.st-key-lunch_seg, .st-key-dinner_seg {
    margin: 0.15rem 0 0.2rem 0 !important;
}
.st-key-menu_day_seg, .st-key-menu_meal_seg {
    margin-bottom: 0.5rem;
}
.st-key-menu_day_seg [data-testid="stButtonGroup"],
.st-key-menu_meal_seg [data-testid="stButtonGroup"],
.st-key-menu_day_seg div[role="group"],
.st-key-menu_meal_seg div[role="group"] {
    display: flex !important;
    flex-wrap: nowrap !important;
    width: 100% !important;
    gap: 0.32rem !important;
}
.st-key-menu_day_seg button {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    white-space: pre-line !important;
    line-height: 1.45 !important;
    padding: 0.58rem 0.2rem 0.52rem 0.2rem !important;
    min-height: 3.55rem !important;
    font-size: 0.78rem !important;
    font-weight: 700 !important;
    letter-spacing: 0.04em !important;
    border-radius: 14px !important;
}
.st-key-menu_meal_seg button {
    flex: 1 1 0 !important;
    min-width: 0 !important;
    padding: 0.48rem 0.4rem !important;
    min-height: 2.55rem !important;
    font-size: 0.9rem !important;
    font-weight: 700 !important;
    border-radius: 12px !important;
}
</style>
"""
