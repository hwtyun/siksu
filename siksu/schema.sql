-- 식수체크 시스템 SQLite 스키마

CREATE TABLE IF NOT EXISTS employees (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    affiliate TEXT NOT NULL DEFAULT '에이텍컴퓨터',
    username TEXT,
    qr_code TEXT UNIQUE,
    password_hash TEXT,
    must_change_password INTEGER NOT NULL DEFAULT 1,
    is_admin INTEGER NOT NULL DEFAULT 0,
    auto_enabled INTEGER NOT NULL DEFAULT 0,
    notify_before INTEGER NOT NULL DEFAULT 0,
    is_cafeteria INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL,
    UNIQUE(name, department),
    UNIQUE(affiliate, username)
);

CREATE TABLE IF NOT EXISTS auto_reservations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    employee_id INTEGER NOT NULL,
    weekday INTEGER NOT NULL,
    lunch_default INTEGER NOT NULL DEFAULT 0,
    dinner_default INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL,
    UNIQUE(employee_id, weekday),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS daily_applications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apply_date TEXT NOT NULL,
    employee_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    department TEXT NOT NULL,
    lunch INTEGER NOT NULL DEFAULT 0,
    dinner INTEGER NOT NULL DEFAULT 0,
    apply_method TEXT NOT NULL,
    submitted_at TEXT NOT NULL,
    UNIQUE(apply_date, employee_id),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS login_tokens (
    token TEXT PRIMARY KEY,
    employee_id INTEGER NOT NULL,
    expires_at TEXT NOT NULL,
    created_at TEXT NOT NULL,
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE TABLE IF NOT EXISTS menus (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    menu_date TEXT NOT NULL,
    meal_type TEXT NOT NULL,
    section TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    sort_order INTEGER NOT NULL DEFAULT 0,
    UNIQUE(menu_date, meal_type, section, name)
);

CREATE INDEX IF NOT EXISTS idx_daily_apply_date
    ON daily_applications(apply_date);

CREATE INDEX IF NOT EXISTS idx_auto_employee
    ON auto_reservations(employee_id);

CREATE INDEX IF NOT EXISTS idx_menus_date
    ON menus(menu_date, meal_type);

CREATE TABLE IF NOT EXISTS meal_checkins (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    apply_date TEXT NOT NULL,
    employee_id INTEGER NOT NULL,
    meal_type TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    UNIQUE(apply_date, employee_id, meal_type),
    FOREIGN KEY (employee_id) REFERENCES employees(id)
);

CREATE INDEX IF NOT EXISTS idx_checkins_date
    ON meal_checkins(apply_date, meal_type);

