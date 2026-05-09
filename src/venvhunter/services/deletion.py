from __future__ import annotations

import os
import shutil
import stat
from pathlib import Path

from venvhunter.models import CleanupTarget, DeleteResult
from venvhunter.services.scanner import FILE_ATTRIBUTE_REPARSE_POINT


class UnsafeDeletionError(ValueError):
    """Raised when a deletion target does not satisfy DevCleaner safety rules."""


class CleanupDeletionService:
    def delete_cleanup_item(
        self,
        cleanup_path: Path,
        target_type: CleanupTarget,
        allowed_root: Path,
        size_bytes: int = 0,
    ) -> DeleteResult:
        try:
            target = cleanup_path.expanduser().resolve(strict=True)
            root = allowed_root.expanduser().resolve(strict=True)
            self._validate_target(target, target_type, root)
            shutil.rmtree(target, onerror=self._handle_remove_readonly)
        except Exception as exc:
            return DeleteResult(path=cleanup_path, success=False, size_bytes=0, error=str(exc))

        return DeleteResult(path=target, success=True, size_bytes=size_bytes)

    def _validate_target(
        self,
        target: Path,
        target_type: CleanupTarget,
        allowed_root: Path,
    ) -> None:
        if target.name.casefold() != target_type.folder_name.casefold():
            raise UnsafeDeletionError(
                f"Refusing to delete non-{target_type.folder_name} directory: {target}"
            )
        if not target.exists():
            raise FileNotFoundError(f"Target does not exist: {target}")
        if not target.is_dir():
            raise NotADirectoryError(f"Target is not a directory: {target}")
        if target.is_symlink() or self._is_reparse_point(target):
            raise UnsafeDeletionError(f"Refusing to delete symlink or reparse-point root: {target}")
        if target == allowed_root or not target.is_relative_to(allowed_root):
            raise UnsafeDeletionError(f"Target is outside the selected root: {target}")

    @staticmethod
    def _is_reparse_point(path: Path) -> bool:
        try:
            attributes = getattr(path.stat(), "st_file_attributes", 0)
        except OSError:
            return True
        return bool(attributes & FILE_ATTRIBUTE_REPARSE_POINT)

    @staticmethod
    def _handle_remove_readonly(function: object, path: str, _exc_info: object) -> None:
        os.chmod(path, stat.S_IWRITE)
        function(path)
