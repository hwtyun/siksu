"""브라우저 localStorage 브리지 (자동 로그인/아이디 저장)."""

from __future__ import annotations

import streamlit.components.v1 as components

from config import COMPONENT_DIR

_ls = components.declare_component("atec_local_storage", path=str(COMPONENT_DIR))


def storage_io(action: str, storage_key: str, value: str = "", widget_key: str | None = None):
    return _ls(
        action=action,
        storage_key=storage_key,
        value=value,
        default=None,
        key=widget_key or f"ls_{action}_{storage_key}",
    )


def read_storage(storage_key: str, widget_key: str | None = None):
    return storage_io("get", storage_key, widget_key=widget_key)


def write_storage(storage_key: str, value: str, widget_key: str | None = None):
    return storage_io("set", storage_key, value, widget_key=widget_key)


def clear_storage(storage_key: str, widget_key: str | None = None):
    return storage_io("remove", storage_key, widget_key=widget_key)
