"""로그인 비밀번호 규칙 검증."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from auth import hash_password, validate_new_password, verify_password


def test_password_rules() -> None:
    stored = hash_password("secret12")
    assert verify_password("secret12", stored)
    assert not verify_password("1111", stored)
    assert validate_new_password("1111", "1111") is not None
    assert validate_new_password("abcd", "abce") is not None
    assert validate_new_password("abcd", "abcd") is None


if __name__ == "__main__":
    test_password_rules()
    print("auth tests passed")
