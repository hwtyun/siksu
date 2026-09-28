"""개인 QR 생성 및 식당 리더기 페이로드 해석."""

from __future__ import annotations

import secrets
from io import BytesIO
from typing import Any

import qrcode

from config import QR_PREFIX


def issue_qr_code() -> str:
    return f"{QR_PREFIX}-{secrets.token_hex(8).upper()}"


def employee_qr_payload(employee: dict[str, Any]) -> str:
    if employee.get("qr_code"):
        return str(employee["qr_code"])
    username = employee.get("username") or employee.get("name") or ""
    return f"{QR_PREFIX}|{employee['id']}|{username}"


def parse_employee_qr(raw: str) -> tuple[int | None, str, str]:
    """QR 문자열에서 (직원id, 아이디, 고정코드)를 꺼낸다."""
    text = (raw or "").strip()
    if not text:
        return None, "", ""
    compact = text.replace(" ", "")
    if compact.upper().startswith(f"{QR_PREFIX}-") and "|" not in compact:
        return None, "", compact.upper()
    parts = [p.strip() for p in compact.replace(",", "|").split("|") if p.strip()]
    if len(parts) >= 2 and parts[0].upper() in {QR_PREFIX, "SIKSU"}:
        ident = parts[1]
        username = parts[2] if len(parts) >= 3 else ""
        if ident.isdigit():
            return int(ident), username, ""
        return None, ident, ""
    if compact.isdigit():
        return int(compact), "", ""
    return None, compact, compact.upper()


def qr_png_bytes(payload: str) -> bytes:
    qr = qrcode.QRCode(border=1, box_size=18, error_correction=qrcode.constants.ERROR_CORRECT_M)
    qr.add_data(payload)
    qr.make(fit=True)
    image = qr.make_image(fill_color="black", back_color="white")
    buffer = BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()
