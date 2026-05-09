from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeyEvent
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QDialog,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from venvhunter.models import CleanupItem, CleanupTarget, DeleteResult
from venvhunter.utils.formatting import format_datetime, format_size, pluralize


@dataclass(frozen=True)
class CommandDefinition:
    command_id: str
    title: str
    shortcut: str
    description: str


class NavButton(QPushButton):
    def __init__(self, text: str, parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("NavButton")
        self.setCheckable(True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)


class MetricCard(QFrame):
    def __init__(
        self,
        label: str,
        value: str = "0",
        helper: str = "",
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("MetricCard")
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(118)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(22, 18, 22, 18)
        layout.setSpacing(7)

        label_widget = QLabel(label)
        label_widget.setObjectName("MetricLabel")

        self.value_label = QLabel(value)
        self.value_label.setObjectName("MetricValue")

        self.helper_label = QLabel(helper)
        self.helper_label.setObjectName("MetricHelper")
        self.helper_label.setWordWrap(True)

        layout.addWidget(label_widget)
        layout.addWidget(self.value_label)
        layout.addWidget(self.helper_label)
        layout.addStretch(1)

    def set_value(self, value: str) -> None:
        self.value_label.setText(value)

    def set_helper(self, helper: str) -> None:
        self.helper_label.setText(helper)


class CleanupCard(QFrame):
    delete_requested = Signal(object)
    open_project_requested = Signal(object)
    reveal_cleanup_requested = Signal(object)
    selection_changed = Signal(object, bool)

    def __init__(self, item: CleanupItem, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.item = item
        self.setObjectName("CleanupCard")
        self.setProperty("selected", False)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(22, 20, 22, 20)
        root_layout.setSpacing(14)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(14)

        self.checkbox = QCheckBox()
        self.checkbox.setCursor(Qt.CursorShape.PointingHandCursor)
        self.checkbox.toggled.connect(self._selection_toggled)
        header_layout.addWidget(self.checkbox, 0, Qt.AlignmentFlag.AlignTop)

        title_layout = QVBoxLayout()
        title_layout.setSpacing(4)
        title = QLabel(item.project_name)
        title.setObjectName("CardTitle")
        target_badge = QLabel(item.target.display_name)
        target_badge.setObjectName("TargetBadge")
        path = QLabel(str(item.cleanup_path))
        path.setObjectName("CardPath")
        path.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        path.setWordWrap(True)
        title_row = QHBoxLayout()
        title_row.setContentsMargins(0, 0, 0, 0)
        title_row.setSpacing(8)
        title_row.addWidget(title)
        title_row.addWidget(target_badge)
        title_row.addStretch(1)
        title_layout.addLayout(title_row)
        title_layout.addWidget(path)
        header_layout.addLayout(title_layout, 1)

        delete_button = QPushButton("Delete")
        delete_button.setObjectName("DangerButton")
        delete_button.setMinimumWidth(92)
        delete_button.setCursor(Qt.CursorShape.PointingHandCursor)
        delete_button.clicked.connect(lambda: self.delete_requested.emit(self.item))
        header_layout.addWidget(delete_button, 0, Qt.AlignmentFlag.AlignTop)

        root_layout.addLayout(header_layout)

        details_layout = QGridLayout()
        details_layout.setHorizontalSpacing(12)
        details_layout.setVerticalSpacing(10)
        self._add_detail(details_layout, 0, 0, "Size", format_size(item.size_bytes))
        self._add_detail(details_layout, 0, 1, "Modified", format_datetime(item.modified_at))
        self._add_detail(
            details_layout,
            0,
            2,
            "Contents",
            f"{pluralize(item.file_count, 'file')} / {pluralize(item.folder_count, 'folder')}",
        )
        root_layout.addLayout(details_layout)

        footer_layout = QHBoxLayout()
        footer_layout.addStretch(1)
        open_project = QPushButton("Open project")
        open_project.setObjectName("ToolbarButton")
        open_project.setCursor(Qt.CursorShape.PointingHandCursor)
        open_project.clicked.connect(lambda: self.open_project_requested.emit(self.item))

        reveal_cleanup = QPushButton("Reveal folder")
        reveal_cleanup.setObjectName("ToolbarButton")
        reveal_cleanup.setCursor(Qt.CursorShape.PointingHandCursor)
        reveal_cleanup.clicked.connect(lambda: self.reveal_cleanup_requested.emit(self.item))

        footer_layout.addWidget(open_project)
        footer_layout.addWidget(reveal_cleanup)
        root_layout.addLayout(footer_layout)

        if item.scan_errors:
            warning = QLabel("; ".join(item.scan_errors[:2]))
            warning.setObjectName("MutedText")
            warning.setWordWrap(True)
            root_layout.addWidget(warning)

    def set_selected(self, selected: bool) -> None:
        if self.checkbox.isChecked() == selected:
            return
        self.checkbox.setChecked(selected)

    def _selection_toggled(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        self.style().unpolish(self)
        self.style().polish(self)
        self.selection_changed.emit(self.item, selected)

    @staticmethod
    def _add_detail(
        layout: QGridLayout,
        row: int,
        column: int,
        label: str,
        value: str,
    ) -> None:
        label_widget = QLabel(label)
        label_widget.setObjectName("MetricLabel")
        value_widget = QLabel(value)
        value_widget.setWordWrap(True)

        container = QWidget()
        container.setObjectName("DetailPill")
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(12, 10, 12, 10)
        container_layout.setSpacing(3)
        container_layout.addWidget(label_widget)
        container_layout.addWidget(value_widget)

        layout.addWidget(container, row, column)


class CommandPaletteDialog(QDialog):
    command_requested = Signal(str)

    def __init__(
        self,
        commands: Sequence[CommandDefinition],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.commands = list(commands)
        self.setWindowTitle("Command Palette")
        self.setModal(False)
        self.setMinimumSize(620, 430)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Command Palette")
        title.setObjectName("SectionTitle")
        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search commands")
        self.command_list = QListWidget()

        layout.addWidget(title)
        layout.addWidget(self.search_box)
        layout.addWidget(self.command_list, 1)

        self.search_box.textChanged.connect(self._populate)
        self.command_list.itemActivated.connect(self._activate_item)
        self._populate()

    def command_ids(self) -> list[str]:
        return [command.command_id for command in self.commands]

    def showEvent(self, event: object) -> None:
        super().showEvent(event)
        self.search_box.setFocus(Qt.FocusReason.PopupFocusReason)
        self.search_box.selectAll()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in {Qt.Key.Key_Return, Qt.Key.Key_Enter}:
            current = self.command_list.currentItem()
            if current is not None:
                self._activate_item(current)
                return
        super().keyPressEvent(event)

    def _populate(self) -> None:
        query = self.search_box.text().strip().casefold()
        self.command_list.clear()
        for command in self.commands:
            haystack = f"{command.title} {command.shortcut} {command.description}".casefold()
            if query and query not in haystack:
                continue
            suffix = f"    {command.shortcut}" if command.shortcut else ""
            item = QListWidgetItem(f"{command.title}{suffix}")
            item.setData(Qt.ItemDataRole.UserRole, command.command_id)
            item.setToolTip(command.description)
            self.command_list.addItem(item)

        if self.command_list.count():
            self.command_list.setCurrentRow(0)

    def _activate_item(self, item: QListWidgetItem) -> None:
        command_id = item.data(Qt.ItemDataRole.UserRole)
        if isinstance(command_id, str):
            self.command_requested.emit(command_id)
        self.accept()


class ShortcutHelpDialog(QDialog):
    def __init__(
        self,
        commands: Sequence[CommandDefinition],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Keyboard Shortcuts")
        self.setMinimumSize(620, 460)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(18, 18, 18, 18)
        layout.setSpacing(12)

        title = QLabel("Keyboard Shortcuts")
        title.setObjectName("SectionTitle")
        table = QTableWidget(len(commands), 3)
        table.setHorizontalHeaderLabels(["Command", "Shortcut", "Description"])
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        for row, command in enumerate(commands):
            table.setItem(row, 0, QTableWidgetItem(command.title))
            table.setItem(row, 1, QTableWidgetItem(command.shortcut))
            table.setItem(row, 2, QTableWidgetItem(command.description))

        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout.addWidget(title)
        layout.addWidget(table, 1)
        layout.addWidget(buttons)


class DeletionReviewDialog(QDialog):
    def __init__(self, items: Sequence[CleanupItem], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.items = list(items)
        self.setWindowTitle("Review Permanent Deletion")
        self.setMinimumSize(720, 520)

        total_size = sum(item.size_bytes for item in self.items)
        breakdown = self._target_breakdown(self.items)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Review permanent deletion")
        title.setObjectName("SectionTitle")
        summary = QLabel(
            f"{len(self.items)} cleanup folder(s), {format_size(total_size)} total. "
            f"Targets: {breakdown}."
        )
        summary.setWordWrap(True)

        warning = QLabel(
            "These folders will be permanently deleted after you confirm. "
            "Only supported cleanup folder names are eligible."
        )
        warning.setObjectName("MutedText")
        warning.setWordWrap(True)

        path_list = QPlainTextEdit()
        path_list.setReadOnly(True)
        path_list.setPlainText("\n".join(str(item.cleanup_path) for item in self.items))

        buttons = QDialogButtonBox()
        cancel_button = buttons.addButton(QDialogButtonBox.StandardButton.Cancel)
        delete_button = buttons.addButton(
            "Delete permanently",
            QDialogButtonBox.ButtonRole.DestructiveRole,
        )
        buttons.rejected.connect(self.reject)
        cancel_button.clicked.connect(self.reject)
        delete_button.clicked.connect(self.accept)

        layout.addWidget(title)
        layout.addWidget(summary)
        layout.addWidget(warning)
        layout.addWidget(path_list, 1)
        layout.addWidget(buttons)

    @staticmethod
    def _target_breakdown(items: Sequence[CleanupItem]) -> str:
        parts: list[str] = []
        for target in CleanupTarget:
            count = sum(1 for item in items if item.target is target)
            if count:
                parts.append(f"{count} {target.short_label}")
        return ", ".join(parts) if parts else "none"


class DeletionLogDialog(QDialog):
    def __init__(
        self,
        results: Sequence[DeleteResult],
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setWindowTitle("Deletion Log")
        self.setMinimumSize(720, 500)

        success_count = sum(1 for result in results if result.success)
        failure_count = len(results) - success_count
        reclaimed = sum(result.size_bytes for result in results if result.success)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(12)

        title = QLabel("Deletion Log")
        title.setObjectName("SectionTitle")
        summary = QLabel(
            f"{success_count} removed, {failure_count} failed, "
            f"{format_size(reclaimed)} reclaimed this session."
        )
        summary.setWordWrap(True)

        table = QTableWidget(len(results), 4)
        table.setHorizontalHeaderLabels(["Status", "Size", "Path", "Message"])
        table.verticalHeader().setVisible(False)
        table.setAlternatingRowColors(True)
        table.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        table.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)

        for row, result in enumerate(results):
            table.setItem(row, 0, QTableWidgetItem("Removed" if result.success else "Failed"))
            table.setItem(row, 1, QTableWidgetItem(format_size(result.size_bytes)))
            table.setItem(row, 2, QTableWidgetItem(str(result.path)))
            table.setItem(row, 3, QTableWidgetItem(result.error or ""))

        table.resizeColumnsToContents()
        table.horizontalHeader().setStretchLastSection(True)

        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)

        layout.addWidget(title)
        layout.addWidget(summary)
        layout.addWidget(table, 1)
        layout.addWidget(buttons)
