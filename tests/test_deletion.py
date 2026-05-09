from __future__ import annotations

import shutil
import unittest
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from venvhunter.models import CleanupTarget
from venvhunter.services.deletion import CleanupDeletionService


@contextmanager
def workspace_temp_dir() -> Iterator[Path]:
    temp_root = Path(__file__).resolve().parents[1] / ".tmp-tests"
    temp_root.mkdir(exist_ok=True)
    temp_dir = temp_root / f"case-{uuid.uuid4().hex}"
    temp_dir.mkdir()
    try:
        yield temp_dir
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class CleanupDeletionServiceTests(unittest.TestCase):
    def test_delete_cleanup_item_removes_only_named_venv_inside_root(self) -> None:
        with workspace_temp_dir() as root:
            venv = root / "project" / ".venv"
            venv.mkdir(parents=True)
            (venv / "pyvenv.cfg").write_text("home = C:/Python\n", encoding="utf-8")

            result = CleanupDeletionService().delete_cleanup_item(
                venv,
                CleanupTarget.VENV,
                root,
                size_bytes=12,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.size_bytes, 12)
            self.assertFalse(venv.exists())

    def test_delete_rejects_non_venv_directory(self) -> None:
        with workspace_temp_dir() as root:
            target = root / "project" / "not-a-venv"
            target.mkdir(parents=True)

            result = CleanupDeletionService().delete_cleanup_item(target, CleanupTarget.VENV, root)

            self.assertFalse(result.success)
            self.assertTrue(target.exists())
            self.assertIn("non-.venv", result.error or "")

    def test_delete_rejects_target_outside_root(self) -> None:
        with workspace_temp_dir() as allowed_dir, workspace_temp_dir() as outside_dir:
            target = outside_dir / ".venv"
            target.mkdir()

            result = CleanupDeletionService().delete_cleanup_item(
                target,
                CleanupTarget.VENV,
                allowed_dir,
            )

            self.assertFalse(result.success)
            self.assertTrue(target.exists())
            self.assertIn("outside", result.error or "")

    def test_delete_node_modules_removes_only_named_target_inside_root(self) -> None:
        with workspace_temp_dir() as root:
            node_modules = root / "web-app" / "node_modules"
            node_modules.mkdir(parents=True)
            (node_modules / "package.json").write_text("{}", encoding="utf-8")

            result = CleanupDeletionService().delete_cleanup_item(
                node_modules,
                CleanupTarget.NODE_MODULES,
                root,
                size_bytes=20,
            )

            self.assertTrue(result.success)
            self.assertEqual(result.size_bytes, 20)
            self.assertFalse(node_modules.exists())


if __name__ == "__main__":
    unittest.main()
