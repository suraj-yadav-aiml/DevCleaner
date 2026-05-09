from __future__ import annotations

import shutil
import unittest
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from pathlib import Path

from venvhunter.models import CleanupTarget
from venvhunter.services.scanner import CleanupScanner, ScanOptions


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


class CleanupScannerTests(unittest.TestCase):
    def test_scan_detects_venv_and_computes_size(self) -> None:
        with workspace_temp_dir() as root:
            project = root / "project-a"
            venv = project / ".venv"
            package_dir = venv / "Lib" / "site-packages"
            package_dir.mkdir(parents=True)
            (venv / "pyvenv.cfg").write_text("home = C:/Python\n", encoding="utf-8")
            (package_dir / "demo.py").write_bytes(b"x" * 2048)

            result = CleanupScanner().scan(root, ScanOptions(show_hidden=True))

            self.assertFalse(result.cancelled)
            self.assertEqual(len(result.items), 1)
            item = result.items[0]
            self.assertEqual(item.project_name, "project-a")
            self.assertEqual(item.cleanup_path, venv)
            self.assertEqual(item.target, CleanupTarget.VENV)
            self.assertGreaterEqual(item.size_bytes, 2048)
            self.assertGreaterEqual(item.file_count, 2)
            self.assertGreaterEqual(item.folder_count, 2)

    def test_scan_respects_excluded_folders(self) -> None:
        with workspace_temp_dir() as root:
            ignored = root / "ignored" / "project"
            (ignored / ".venv").mkdir(parents=True)

            result = CleanupScanner().scan(
                root,
                ScanOptions(show_hidden=True, excluded_folder_names=frozenset({"ignored"})),
            )

            self.assertEqual(result.items, ())

    def test_scan_detects_node_modules_when_selected(self) -> None:
        with workspace_temp_dir() as root:
            node_modules = root / "web-app" / "node_modules"
            package_dir = node_modules / "demo-package"
            package_dir.mkdir(parents=True)
            (package_dir / "index.js").write_bytes(b"x" * 1024)

            result = CleanupScanner().scan(
                root,
                ScanOptions(
                    show_hidden=True,
                    targets=frozenset({CleanupTarget.NODE_MODULES}),
                ),
            )

            self.assertEqual(len(result.items), 1)
            item = result.items[0]
            self.assertEqual(item.target, CleanupTarget.NODE_MODULES)
            self.assertEqual(item.cleanup_path, node_modules)
            self.assertGreaterEqual(item.size_bytes, 1024)

    def test_scan_target_selection_limits_results(self) -> None:
        with workspace_temp_dir() as root:
            (root / "python-app" / ".venv").mkdir(parents=True)
            (root / "web-app" / "node_modules").mkdir(parents=True)

            result = CleanupScanner().scan(
                root,
                ScanOptions(show_hidden=True, targets=frozenset({CleanupTarget.VENV})),
            )

            self.assertEqual(len(result.items), 1)
            self.assertEqual(result.items[0].target, CleanupTarget.VENV)

    def test_scan_detects_node_modules_before_excluding_traversal(self) -> None:
        with workspace_temp_dir() as root:
            node_modules = root / "web-app" / "node_modules"
            (node_modules / "nested-project" / ".venv").mkdir(parents=True)

            result = CleanupScanner().scan(
                root,
                ScanOptions(
                    show_hidden=True,
                    excluded_folder_names=frozenset({"node_modules"}),
                    targets=frozenset({CleanupTarget.NODE_MODULES, CleanupTarget.VENV}),
                ),
            )

            self.assertEqual(len(result.items), 1)
            self.assertEqual(result.items[0].target, CleanupTarget.NODE_MODULES)


if __name__ == "__main__":
    unittest.main()
