from __future__ import annotations

from pathlib import Path
from threading import Event

from PySide6.QtCore import QObject, Signal, Slot

from venvhunter.models import CleanupItem, DeleteResult, ScanResult
from venvhunter.services.deletion import CleanupDeletionService
from venvhunter.services.scanner import CleanupScanner, ScanOptions


class ScanWorker(QObject):
    item_found = Signal(object)
    progress = Signal(int, str)
    failed = Signal(str)
    finished = Signal(object)

    def __init__(self, root_path: Path, options: ScanOptions) -> None:
        super().__init__()
        self.root_path = root_path
        self.options = options
        self.cancel_event = Event()
        self.scanner = CleanupScanner()

    @Slot()
    def run(self) -> None:
        try:
            result = self.scanner.scan(
                self.root_path,
                self.options,
                progress_callback=self._emit_progress,
                item_found_callback=self._emit_item,
                cancel_event=self.cancel_event,
            )
        except Exception as exc:
            self.failed.emit(str(exc))
            result = ScanResult(
                root_path=self.root_path,
                items=(),
                scanned_directories=0,
                errors=(str(exc),),
                cancelled=False,
                elapsed_seconds=0,
            )

        self.finished.emit(result)

    def cancel(self) -> None:
        self.cancel_event.set()

    def _emit_progress(self, scanned_count: int, current_path: Path) -> None:
        self.progress.emit(scanned_count, str(current_path))

    def _emit_item(self, item: CleanupItem) -> None:
        self.item_found.emit(item)


class DeleteWorker(QObject):
    progress = Signal(int, int)
    deleted = Signal(object)
    failed_item = Signal(object)
    finished = Signal(list)

    def __init__(self, root_path: Path, items: list[CleanupItem]) -> None:
        super().__init__()
        self.root_path = root_path
        self.items = items
        self.service = CleanupDeletionService()

    @Slot()
    def run(self) -> None:
        results: list[DeleteResult] = []
        total = len(self.items)

        for index, item in enumerate(self.items, start=1):
            result = self.service.delete_cleanup_item(
                item.cleanup_path,
                item.target,
                self.root_path,
                item.size_bytes,
            )
            results.append(result)

            if result.success:
                self.deleted.emit(result)
            else:
                self.failed_item.emit(result)

            self.progress.emit(index, total)

        self.finished.emit(results)
