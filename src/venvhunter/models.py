from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from pathlib import Path


@dataclass(frozen=True)
class DirectoryStats:
    size_bytes: int = 0
    file_count: int = 0
    folder_count: int = 0
    errors: tuple[str, ...] = ()

    @property
    def total_items(self) -> int:
        return self.file_count + self.folder_count


class CleanupTarget(StrEnum):
    VENV = ".venv"
    NODE_MODULES = "node_modules"

    @property
    def folder_name(self) -> str:
        return self.value

    @property
    def display_name(self) -> str:
        if self is CleanupTarget.VENV:
            return "Python .venv"
        return "Node node_modules"

    @property
    def short_label(self) -> str:
        if self is CleanupTarget.VENV:
            return ".venv"
        return "node_modules"

    @classmethod
    def from_folder_name(cls, folder_name: str) -> CleanupTarget | None:
        normalized = folder_name.casefold()
        for target in cls:
            if target.folder_name.casefold() == normalized:
                return target
        return None

    @classmethod
    def defaults(cls) -> frozenset[CleanupTarget]:
        return frozenset(cls)


@dataclass(frozen=True)
class CleanupItem:
    target: CleanupTarget
    project_name: str
    project_path: Path
    cleanup_path: Path
    size_bytes: int
    modified_at: datetime
    file_count: int
    folder_count: int
    scan_errors: tuple[str, ...] = field(default_factory=tuple)

    @property
    def id(self) -> str:
        return f"{self.target.value}|{self.cleanup_path}".casefold()

    @property
    def item_count(self) -> int:
        return self.file_count + self.folder_count

    @property
    def target_label(self) -> str:
        return self.target.display_name


@dataclass(frozen=True)
class ScanResult:
    root_path: Path
    items: tuple[CleanupItem, ...]
    scanned_directories: int
    errors: tuple[str, ...]
    cancelled: bool
    elapsed_seconds: float

    @property
    def total_size_bytes(self) -> int:
        return sum(item.size_bytes for item in self.items)


@dataclass(frozen=True)
class DeleteResult:
    path: Path
    success: bool
    size_bytes: int = 0
    error: str | None = None
