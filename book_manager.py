"""Validate and import user-supplied Project Aon book files."""

from __future__ import annotations

import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Iterable

from runtime_paths import PATHS


REQUIRED_FILES = ("title.htm", "sect1.htm")


def _valid_book_directory(path: Path) -> bool:
    return path.is_dir() and all((path / name).is_file() for name in REQUIRED_FILES)


def discover_book_directories(source: Path, expected_folders: Iterable[str]) -> dict[str, Path]:
    """Find known book folders below a user-selected folder."""
    source = source.resolve()
    expected = {str(name) for name in expected_folders if str(name)}
    roots = [
        source,
        source / "lw",
        source / "books",
        source / "books" / "lw",
        # Project Aon's standard downloadable archives place each book here:
        # en/xhtml/lw/<book-folder>/title.htm
        source / "en" / "xhtml" / "lw",
    ]
    discovered: dict[str, Path] = {}
    for root in roots:
        if root.name in expected and _valid_book_directory(root):
            discovered[root.name] = root
        if not root.is_dir():
            continue
        for folder in expected:
            candidate = root / folder
            if folder not in discovered and _valid_book_directory(candidate):
                discovered[folder] = candidate
    return discovered


def _safe_extract(archive: Path, destination: Path) -> None:
    destination = destination.resolve()
    with zipfile.ZipFile(archive) as bundle:
        for member in bundle.infolist():
            member_path = (destination / member.filename).resolve()
            try:
                member_path.relative_to(destination)
            except ValueError as exc:
                raise ValueError(f"Unsafe ZIP entry: {member.filename}") from exc
        bundle.extractall(destination)


def import_books(
    sources: Iterable[str | Path],
    expected_folders: Iterable[str],
    destination: Path = PATHS.books_lw,
) -> dict:
    """Copy validated books from extracted folders or ZIP archives."""
    expected = tuple(str(folder) for folder in expected_folders if str(folder))
    destination.mkdir(parents=True, exist_ok=True)
    discovered: dict[str, Path] = {}
    temporary_roots: list[tempfile.TemporaryDirectory] = []
    try:
        for raw_source in sources:
            source = Path(raw_source).expanduser().resolve()
            if not source.exists():
                raise FileNotFoundError(f"Book source does not exist: {source}")
            if source.is_file():
                if source.suffix.lower() != ".zip":
                    raise ValueError(f"Book source is not a ZIP file: {source}")
                temporary = tempfile.TemporaryDirectory(prefix="lonewolf-books-")
                temporary_roots.append(temporary)
                extracted = Path(temporary.name)
                _safe_extract(source, extracted)
                found = discover_book_directories(extracted, expected)
            else:
                found = discover_book_directories(source, expected)
            discovered.update(found)

        if not discovered:
            raise ValueError(
                "No valid Project Aon book folders were found. Each book must contain "
                "title.htm and sect1.htm."
            )

        imported = []
        for folder, source in sorted(discovered.items()):
            target = destination / folder
            shutil.copytree(source, target, dirs_exist_ok=True)
            imported.append(folder)
        return {
            "Imported": imported,
            "Count": len(imported),
            "Destination": str(destination),
        }
    finally:
        for temporary in temporary_roots:
            temporary.cleanup()


def open_books_folder() -> str:
    PATHS.books_lw.mkdir(parents=True, exist_ok=True)
    if hasattr(__import__("os"), "startfile"):
        import os

        os.startfile(PATHS.books_lw)  # type: ignore[attr-defined]
    return str(PATHS.books_lw)
