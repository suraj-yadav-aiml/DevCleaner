from __future__ import annotations

import os
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from threading import Event

from venvhunter.models import CleanupItem, CleanupTarget, DirectoryStats, ScanResult

FILE_ATTRIBUTE_HIDDEN = 0x2
FILE_ATTRIBUTE_REPARSE_POINT = 0x400

ProgressCallback = Callable[[int, Path], None]
ItemFoundCallback = Callable[[CleanupItem], None]


@dataclass(frozen=True)
class ScanOptions:
    show_hidden: bool = False
    excluded_folder_names: frozenset[str] = field(default_factory=frozenset)
    max_depth: int | None = None
    targets: frozenset[CleanupTarget] = field(default_factory=CleanupTarget.defaults)


class CleanupScanner:
    def scan(
        self,
        root_path: Path,
        options: ScanOptions | None = None,
        progress_callback: ProgressCallback | None = None,
        item_found_callback: ItemFoundCallback | None = None,
        cancel_event: Event | None = None,
    ) -> ScanResult:
        started = time.perf_counter()
        options = options or ScanOptions()
        root = root_path.expanduser().resolve()

        if not root.exists():
            raise FileNotFoundError(f"Root folder does not exist: {root}")
        if not root.is_dir():
            raise NotADirectoryError(f"Root path is not a folder: {root}")

        selected_targets = options.targets
        targets_by_name = {target.folder_name.casefold(): target for target in selected_targets}
        items: list[CleanupItem] = []
        errors: list[str] = []
        scanned_directories = 0
        stack: list[tuple[Path, int]] = [(root, 0)]

        while stack:
            if cancel_event and cancel_event.is_set():
                break

            current, depth = stack.pop()
            scanned_directories += 1
            if progress_callback:
                progress_callback(scanned_directories, current)

            try:
                entries = list(os.scandir(current))
            except OSError as exc:
                errors.append(f"Could not scan {current}: {exc}")
                continue

            child_dirs: list[tuple[Path, int]] = []
            cleanup_dirs: list[tuple[os.DirEntry[str], CleanupTarget]] = []

            for entry in entries:
                if cancel_event and cancel_event.is_set():
                    break

                if not self._is_directory(entry):
                    continue

                target = targets_by_name.get(entry.name.casefold())
                if target is not None:
                    cleanup_dirs.append((entry, target))
                    continue

                next_depth = depth + 1
                if self._should_skip_directory(entry, next_depth, options):
                    continue

                child_dirs.append((Path(entry.path), next_depth))

            for entry, target in cleanup_dirs:
                if cancel_event and cancel_event.is_set():
                    break

                info = self._build_cleanup_item(target, Path(entry.path), current, cancel_event)
                items.append(info)
                if item_found_callback:
                    item_found_callback(info)

            stack.extend(reversed(child_dirs))

        elapsed = time.perf_counter() - started
        return ScanResult(
            root_path=root,
            items=tuple(items),
            scanned_directories=scanned_directories,
            errors=tuple(errors),
            cancelled=bool(cancel_event and cancel_event.is_set()),
            elapsed_seconds=elapsed,
        )

    def _build_cleanup_item(
        self,
        target: CleanupTarget,
        cleanup_path: Path,
        project_path: Path,
        cancel_event: Event | None,
    ) -> CleanupItem:
        errors: list[str] = []

        try:
            stat_result = cleanup_path.stat()
            modified_at = datetime.fromtimestamp(stat_result.st_mtime)
        except OSError as exc:
            modified_at = datetime.fromtimestamp(0)
            errors.append(f"Could not read modified date for {cleanup_path}: {exc}")

        if self._path_is_symlink_or_reparse_point(cleanup_path):
            stats = DirectoryStats(
                errors=(
                    f"Skipped size scan because {cleanup_path} is a symlink or reparse point.",
                )
            )
        else:
            stats = self.compute_directory_stats(cleanup_path, cancel_event)

        return CleanupItem(
            target=target,
            project_name=project_path.name or str(project_path),
            project_path=project_path,
            cleanup_path=cleanup_path,
            size_bytes=stats.size_bytes,
            modified_at=modified_at,
            file_count=stats.file_count,
            folder_count=stats.folder_count,
            scan_errors=tuple(errors) + stats.errors,
        )

    def compute_directory_stats(
        self,
        directory: Path,
        cancel_event: Event | None = None,
    ) -> DirectoryStats:
        size_bytes = 0
        file_count = 0
        folder_count = 0
        errors: list[str] = []
        stack = [directory]

        while stack:
            if cancel_event and cancel_event.is_set():
                break

            current = stack.pop()
            try:
                entries = list(os.scandir(current))
            except OSError as exc:
                errors.append(f"Could not inspect {current}: {exc}")
                continue

            for entry in entries:
                if cancel_event and cancel_event.is_set():
                    break

                try:
                    if entry.is_dir(follow_symlinks=False):
                        folder_count += 1
                        if self._entry_is_symlink_or_reparse_point(entry):
                            continue
                        stack.append(Path(entry.path))
                    elif entry.is_file(follow_symlinks=False):
                        file_count += 1
                        size_bytes += entry.stat(follow_symlinks=False).st_size
                except OSError as exc:
                    errors.append(f"Could not inspect {entry.path}: {exc}")

        return DirectoryStats(
            size_bytes=size_bytes,
            file_count=file_count,
            folder_count=folder_count,
            errors=tuple(errors),
        )

    def _should_skip_directory(
        self,
        entry: os.DirEntry[str],
        depth: int,
        options: ScanOptions,
    ) -> bool:
        if options.max_depth is not None and depth > options.max_depth:
            return True
        if entry.name.casefold() in options.excluded_folder_names:
            return True
        if self._entry_is_symlink_or_reparse_point(entry):
            return True
        return not options.show_hidden and self._entry_is_hidden(entry)

    @staticmethod
    def _is_directory(entry: os.DirEntry[str]) -> bool:
        try:
            return entry.is_dir(follow_symlinks=False)
        except OSError:
            return False

    @staticmethod
    def _entry_is_hidden(entry: os.DirEntry[str]) -> bool:
        if entry.name.startswith("."):
            return True
        try:
            attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
        except OSError:
            return False
        return bool(attributes & FILE_ATTRIBUTE_HIDDEN)

    @staticmethod
    def _entry_is_symlink_or_reparse_point(entry: os.DirEntry[str]) -> bool:
        try:
            if entry.is_symlink():
                return True
            attributes = getattr(entry.stat(follow_symlinks=False), "st_file_attributes", 0)
        except OSError:
            return True
        return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)

    @staticmethod
    def _path_is_symlink_or_reparse_point(path: Path) -> bool:
        try:
            if path.is_symlink():
                return True
            attributes = getattr(path.stat(), "st_file_attributes", 0)
        except OSError:
            return True
        return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)
