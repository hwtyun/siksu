"""비밀번호 해시 및 로그인 토큰."""

from __future__ import annotations

import hashlib
import secrets
from datetime import timedelta

from config import DEFAULT_PASSWORD, MIN_PASSWORD_LEN
from logic import now_kst

PBKDF2_ROUNDS = 120_000


def hash_password(password: str, salt: str | None = None) -> str:
    salt = salt or secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ROUNDS,
    ).hex()
    return f"{salt}${digest}"


def verify_password(password: str, stored: str | None) -> bool:
    if not stored or "$" not in stored:
        return False
    salt, digest = stored.split("$", 1)
    check = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt.encode("utf-8"),
        PBKDF2_ROUNDS,
    ).hex()
    return secrets.compare_digest(check, digest)


def default_password_hash() -> str:
    return hash_password(DEFAULT_PASSWORD)


def validate_new_password(password: str, confirm: str) -> str | None:
    if len(password) < MIN_PASSWORD_LEN:
        return f"비밀번호는 {MIN_PASSWORD_LEN}자 이상이어야 합니다."
    if password != confirm:
        return "새 비밀번호가 서로 다릅니다."
    if password == DEFAULT_PASSWORD:
        return "초기 비밀번호(1111)는 사용할 수 없습니다."
    return None


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_expiry_iso(days: int = 365) -> str:
    return (now_kst() + timedelta(days=days)).isoformat(timespec="seconds")
