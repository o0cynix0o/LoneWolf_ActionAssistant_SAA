"""Authoritative filesystem locations for Lone Wolf Action Assistant."""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path


APP_NAME = "Lone Wolf Action Assistant"
REGISTRY_KEY = r"Software\Lone Wolf Action Assistant"


def _resource_root() -> Path:
    """Return the read-only application resource root."""
    frozen_root = getattr(sys, "_MEIPASS", None)
    if frozen_root:
        return Path(frozen_root).resolve()
    return Path(__file__).resolve().parent


def _local_app_data() -> Path:
    value = os.environ.get("LOCALAPPDATA")
    if value:
        return Path(value)
    return Path.home() / "AppData" / "Local"


def _registry_books_dir() -> Path | None:
    """Read the installer-selected books directory, preferring HKCU."""
    if os.name != "nt":
        return None
    try:
        import winreg
    except ImportError:
        return None

    for hive in (winreg.HKEY_CURRENT_USER, winreg.HKEY_LOCAL_MACHINE):
        try:
            with winreg.OpenKey(hive, REGISTRY_KEY) as key:
                value, _ = winreg.QueryValueEx(key, "BooksDir")
            if str(value).strip():
                return Path(str(value)).expanduser()
        except OSError:
            continue
    return None


def _books_root(local_root: Path) -> Path:
    override = os.environ.get("LONEWOLF_SAA_BOOKS_DIR")
    if override:
        return Path(override).expanduser()
    installed = _registry_books_dir()
    if installed is not None:
        return installed
    return local_root / "books"


@dataclass(frozen=True)
class RuntimePaths:
    resource_root: Path
    resource_data: Path
    user_root: Path
    user_data: Path
    saves: Path
    logs: Path
    books: Path
    books_lw: Path
    current_position: Path
    ui_preferences: Path

    def ensure_writable(self) -> None:
        for directory in (
            self.user_root,
            self.user_data,
            self.saves,
            self.saves / "slots",
            self.logs,
            self.books,
            self.books_lw,
        ):
            directory.mkdir(parents=True, exist_ok=True)


def get_runtime_paths() -> RuntimePaths:
    resource_root = _resource_root()
    user_root = _local_app_data() / APP_NAME
    books = _books_root(user_root)
    return RuntimePaths(
        resource_root=resource_root,
        resource_data=resource_root / "data",
        user_root=user_root,
        user_data=user_root / "data",
        saves=user_root / "saves",
        logs=user_root / "logs",
        books=books,
        books_lw=books / "lw",
        current_position=user_root / "current-position.json",
        ui_preferences=user_root / "data" / "ui-preferences.json",
    )


PATHS = get_runtime_paths()
