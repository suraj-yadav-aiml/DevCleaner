from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest
from PySide6.QtWidgets import QApplication

from venvhunter.models import CleanupItem, CleanupTarget, DeleteResult
from venvhunter.ui.main_window import MainWindow


@pytest.fixture
def app() -> QApplication:
    existing = QApplication.instance()
    if existing is not None:
        return existing
    return QApplication([])


@pytest.fixture
def window(
    app: QApplication,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path,
) -> MainWindow:
    monkeypatch.setenv("APPDATA", str(tmp_path))
    main_window = MainWindow()
    yield main_window
    main_window.close()
    app.processEvents()


def test_main_window_constructs(window: MainWindow) -> None:
    assert window.windowTitle() == "DevCleaner"
    assert window.stack.count() == 3


def test_fullscreen_toggle_method(app: QApplication, window: MainWindow) -> None:
    window.show()
    app.processEvents()

    window._toggle_fullscreen()
    app.processEvents()
    assert window.isFullScreen()

    window._escape_pressed()
    app.processEvents()
    assert not window.isFullScreen()


def test_action_registry_contains_expected_commands(window: MainWindow) -> None:
    expected_commands = {
        "choose-folder",
        "start-scan",
        "toggle-fullscreen",
        "command-palette",
        "shortcuts-help",
        "delete-selected",
        "export-visible",
    }

    assert expected_commands.issubset(window.actions_by_id)


def test_command_palette_opens_and_lists_core_commands(
    app: QApplication,
    window: MainWindow,
) -> None:
    window._open_command_palette()
    app.processEvents()

    assert window.command_palette is not None
    assert {
        "choose-folder",
        "start-scan",
        "show-dashboard",
        "show-results",
        "show-settings",
    }.issubset(window.command_palette.command_ids())

    window.command_palette.close()
    app.processEvents()


def test_animations_disabled_page_navigation_is_instant(window: MainWindow) -> None:
    window.settings.animations_enabled = False
    window.animations.clear()

    window._navigate_to_page(1)

    assert window.stack.currentIndex() == 1
    assert not window.animations


def test_remaining_results_render_after_multiple_deletions(
    window: MainWindow,
    tmp_path: Path,
) -> None:
    window.settings.animations_enabled = False
    window.root_path = tmp_path
    window.items = [_cleanup_item(tmp_path, index) for index in range(5)]

    window._render_results()
    assert len(window.cards) == 5

    deleted_items = window.items[:2]
    for item in deleted_items:
        window._delete_succeeded(
            DeleteResult(
                path=item.cleanup_path,
                success=True,
                size_bytes=item.size_bytes,
            )
        )
    window._delete_finished(
        [
            DeleteResult(
                path=item.cleanup_path,
                success=True,
                size_bytes=item.size_bytes,
            )
            for item in deleted_items
        ]
    )

    assert len(window.items) == 3
    assert len(window.cards) == 3
    assert {card.item.cleanup_path for card in window.cards.values()} == {
        item.cleanup_path for item in window.items
    }


def _cleanup_item(root_path: Path, index: int) -> CleanupItem:
    project_path = root_path / f"project-{index}"
    cleanup_path = project_path / ".venv"
    return CleanupItem(
        target=CleanupTarget.VENV,
        project_name=project_path.name,
        project_path=project_path,
        cleanup_path=cleanup_path,
        size_bytes=1024 * 1024 * (index + 1),
        modified_at=datetime(2026, 1, 1),
        file_count=10,
        folder_count=2,
    )
