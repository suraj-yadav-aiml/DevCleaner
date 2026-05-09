from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import QPoint, QRect, QSize, Qt, QThread
from PySide6.QtGui import QAction, QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QButtonGroup,
    QCheckBox,
    QComboBox,
    QFileDialog,
    QFrame,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QSpinBox,
    QStackedWidget,
    QStyle,
    QTextEdit,
    QVBoxLayout,
    QWidget,
)

from venvhunter.models import CleanupItem, CleanupTarget, DeleteResult, ScanResult
from venvhunter.services.exporter import ScanResultExporter
from venvhunter.services.scanner import ScanOptions
from venvhunter.settings import AppSettings, SettingsStore
from venvhunter.ui.animations import animate_number, fade_in, fade_slide_in
from venvhunter.ui.theme import build_stylesheet
from venvhunter.ui.widgets import (
    CleanupCard,
    CommandDefinition,
    CommandPaletteDialog,
    DeletionLogDialog,
    DeletionReviewDialog,
    MetricCard,
    NavButton,
    ShortcutHelpDialog,
)
from venvhunter.ui.workers import DeleteWorker, ScanWorker
from venvhunter.utils.formatting import format_duration, format_size
from venvhunter.utils.platform import open_folder, reveal_in_file_manager


class MainWindow(QMainWindow):
    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("DevCleaner")
        self.setMinimumSize(QSize(1040, 680))

        self.settings_store = SettingsStore()
        self.settings = self.settings_store.load()
        self.root_path: Path | None = None
        self.items: list[CleanupItem] = []
        self.selected_ids: set[str] = set()
        self.reclaimed_size = 0
        self.cards: dict[str, CleanupCard] = {}
        self.animations: list[object] = []
        self.deletion_results: list[DeleteResult] = []
        self.actions_by_id: dict[str, QAction] = {}
        self.command_definitions: list[CommandDefinition] = []
        self.command_palette: CommandPaletteDialog | None = None
        self.shortcut_help_dialog: ShortcutHelpDialog | None = None
        self.deletion_log_dialog: DeletionLogDialog | None = None
        self.normal_window_geometry: QRect | None = None
        self.metric_numbers = {
            "detected": 0,
            "total_size": 0,
            "reclaimed": 0,
            "scanned": 0,
        }

        self.scan_thread: QThread | None = None
        self.scan_worker: ScanWorker | None = None
        self.delete_thread: QThread | None = None
        self.delete_worker: DeleteWorker | None = None
        self.last_scanned_count = 0
        self.last_scan_duration = 0.0
        self.last_scan_warning_count = 0

        self._build_ui()
        self._apply_theme()
        self._load_settings_into_controls()
        self._update_recent_roots()
        self._update_metrics()
        self._apply_shortcut_hints()
        self._set_worker_state("Idle", "No background work is running.")
        self._set_idle_status("Choose a root folder to begin.")

    def _build_ui(self) -> None:
        central = QWidget()
        central.setObjectName("AppRoot")
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)
        self.setCentralWidget(central)

        self.stack = QStackedWidget()
        root_layout.addWidget(self._build_sidebar())
        root_layout.addWidget(self.stack, 1)

        self.dashboard_page = self._build_dashboard_page()
        self.results_page = self._build_results_page()
        self.settings_page = self._build_settings_page()

        self.stack.addWidget(self.dashboard_page)
        self.stack.addWidget(self.results_page)
        self.stack.addWidget(self.settings_page)

        self.status_label = QLabel()
        self.status_progress = QProgressBar()
        self.status_progress.setFixedWidth(180)
        self.status_progress.setRange(0, 1)
        self.status_progress.setValue(0)
        self.statusBar().addWidget(self.status_label, 1)
        self.statusBar().addPermanentWidget(self.status_progress)

        self._create_actions()

    def _build_sidebar(self) -> QWidget:
        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(268)
        layout = QVBoxLayout(sidebar)
        layout.setContentsMargins(20, 22, 20, 20)
        layout.setSpacing(12)

        brand_panel = QFrame()
        brand_panel.setObjectName("BrandPanel")
        brand_layout = QVBoxLayout(brand_panel)
        brand_layout.setContentsMargins(14, 12, 14, 12)
        brand_layout.setSpacing(4)

        title = QLabel("DevCleaner")
        title.setObjectName("AppTitle")
        subtitle = QLabel("Python and Node cleanup")
        subtitle.setObjectName("PageSubtitle")
        brand_layout.addWidget(title)
        brand_layout.addWidget(subtitle)
        layout.addWidget(brand_panel)
        layout.addSpacing(14)

        self.nav_group = QButtonGroup(self)
        self.nav_group.setExclusive(True)

        self.dashboard_nav = NavButton("Dashboard")
        self.results_nav = NavButton("Scan Results")
        self.settings_nav = NavButton("Settings")

        for index, button in enumerate([self.dashboard_nav, self.results_nav, self.settings_nav]):
            self.nav_group.addButton(button, index)
            layout.addWidget(button)

        self.dashboard_nav.setChecked(True)
        self.nav_group.idClicked.connect(self._navigate_to_page)

        layout.addStretch(1)

        hint = QLabel("Deletes are always confirmed and limited to supported cleanup folders.")
        hint.setObjectName("SidebarHint")
        hint.setWordWrap(True)
        layout.addWidget(hint)
        return sidebar

    def _build_dashboard_page(self) -> QWidget:
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setObjectName("Page")

        page = QWidget()
        page.setObjectName("Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(36, 30, 36, 30)
        layout.setSpacing(18)

        header_layout = QHBoxLayout()
        header_layout.setSpacing(12)
        header_layout.addWidget(
            self._page_header(
                "Dashboard",
                "Workspace cleanup overview for Python and Node projects.",
            ),
            1,
        )
        self.worker_status_pill = QLabel("IDLE")
        self.worker_status_pill.setObjectName("StatusPill")
        header_layout.addWidget(self.worker_status_pill, 0, Qt.AlignmentFlag.AlignTop)
        layout.addLayout(header_layout)

        picker_panel = QFrame()
        picker_panel.setObjectName("ScanPanel")
        picker_layout = QVBoxLayout(picker_panel)
        picker_layout.setContentsMargins(24, 22, 24, 22)
        picker_layout.setSpacing(14)

        scan_header = QHBoxLayout()
        scan_title = QLabel("Workspace scan")
        scan_title.setObjectName("SectionTitle")
        scan_hint = QLabel("Recursive scan runs outside the UI thread.")
        scan_hint.setObjectName("MutedText")
        scan_header.addWidget(scan_title)
        scan_header.addStretch(1)
        scan_header.addWidget(scan_hint)
        picker_layout.addLayout(scan_header)

        target_layout = QHBoxLayout()
        target_layout.setSpacing(14)
        target_label = QLabel("Scan targets")
        target_label.setObjectName("MetricLabel")
        self.venv_target_checkbox = QCheckBox(".venv")
        self.node_target_checkbox = QCheckBox("node_modules")
        target_layout.addWidget(target_label)
        target_layout.addWidget(self.venv_target_checkbox)
        target_layout.addWidget(self.node_target_checkbox)
        target_layout.addStretch(1)
        picker_layout.addLayout(target_layout)

        self.root_path_label = QLabel("No folder selected")
        self.root_path_label.setObjectName("PathDisplay")
        self.root_path_label.setMinimumHeight(46)
        self.root_path_label.setWordWrap(True)
        self.root_path_label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)

        style = self.style()
        self.choose_button = QPushButton("Choose folder")
        self.choose_button.setObjectName("PrimaryButton")
        self.choose_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_DirOpenIcon))
        self.choose_button.clicked.connect(self._choose_root_folder)
        self.choose_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.scan_button = QPushButton("Start scan")
        self.scan_button.setObjectName("PrimaryButton")
        self.scan_button.setIcon(style.standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.scan_button.clicked.connect(self._start_scan)
        self.scan_button.setCursor(Qt.CursorShape.PointingHandCursor)

        self.cancel_scan_button = QPushButton("Cancel")
        self.cancel_scan_button.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogCancelButton)
        )
        self.cancel_scan_button.clicked.connect(self._cancel_scan)
        self.cancel_scan_button.setEnabled(False)
        self.cancel_scan_button.setCursor(Qt.CursorShape.PointingHandCursor)

        scan_body = QHBoxLayout()
        scan_body.setSpacing(12)
        scan_body.addWidget(self.root_path_label, 1)
        scan_body.addWidget(self.choose_button)
        scan_body.addWidget(self.scan_button)
        scan_body.addWidget(self.cancel_scan_button)
        picker_layout.addLayout(scan_body)
        layout.addWidget(picker_panel)

        metrics_layout = QHBoxLayout()
        metrics_layout.setSpacing(14)
        self.detected_metric = MetricCard("Detected", "0", "Cleanup folders")
        self.total_size_metric = MetricCard("Total footprint", "0.0 MB", "Across results")
        self.reclaimed_metric = MetricCard("Reclaimed", "0.0 MB", "This session")
        self.scanned_metric = MetricCard("Folders scanned", "0", "Last scan")
        for card in [
            self.detected_metric,
            self.total_size_metric,
            self.reclaimed_metric,
            self.scanned_metric,
        ]:
            metrics_layout.addWidget(card)
        layout.addLayout(metrics_layout)

        lower_grid = QGridLayout()
        lower_grid.setHorizontalSpacing(14)
        lower_grid.setVerticalSpacing(14)

        summary_panel = QFrame()
        summary_panel.setObjectName("SummaryPanel")
        summary_panel.setMinimumHeight(220)
        summary_layout = QGridLayout(summary_panel)
        summary_layout.setContentsMargins(22, 20, 22, 20)
        summary_layout.setHorizontalSpacing(18)
        summary_layout.setVerticalSpacing(12)
        summary_title = QLabel("Scan summary")
        summary_title.setObjectName("SectionTitle")
        summary_layout.addWidget(summary_title, 0, 0, 1, 2)
        self.summary_root_value = self._add_summary_row(
            summary_layout,
            1,
            "Root",
            "No folder selected",
        )
        self.summary_found_value = self._add_summary_row(summary_layout, 2, "Found", "0")
        self.summary_total_value = self._add_summary_row(summary_layout, 3, "Total size", "0.0 MB")
        self.summary_scanned_value = self._add_summary_row(summary_layout, 4, "Scanned", "0")
        self.summary_duration_value = self._add_summary_row(summary_layout, 5, "Duration", "-")
        self.summary_warning_value = self._add_summary_row(summary_layout, 6, "Warnings", "0")

        status_panel = QFrame()
        status_panel.setObjectName("StatusPanel")
        status_panel.setMinimumHeight(220)
        status_layout = QGridLayout(status_panel)
        status_layout.setContentsMargins(22, 20, 22, 20)
        status_layout.setHorizontalSpacing(18)
        status_layout.setVerticalSpacing(12)
        status_title = QLabel("Background activity")
        status_title.setObjectName("SectionTitle")
        status_layout.addWidget(status_title, 0, 0, 1, 2)
        self.worker_state_value = self._add_summary_row(status_layout, 1, "Worker", "Idle")
        self.worker_detail_value = self._add_summary_row(
            status_layout,
            2,
            "Status",
            "No background work is running.",
        )
        self.largest_venv_value = self._add_summary_row(status_layout, 3, "Largest", "-")
        self.average_size_value = self._add_summary_row(status_layout, 4, "Average size", "0.0 MB")
        self.dashboard_progress = QProgressBar()
        self.dashboard_progress.setRange(0, 1)
        self.dashboard_progress.setValue(0)
        status_layout.addWidget(self.dashboard_progress, 5, 0, 1, 2)

        recent_panel = QFrame()
        recent_panel.setObjectName("SummaryPanel")
        recent_panel.setMinimumHeight(150)
        recent_layout = QVBoxLayout(recent_panel)
        recent_layout.setContentsMargins(22, 20, 22, 20)
        recent_layout.setSpacing(12)
        recent_title = QLabel("Recent folders")
        recent_title.setObjectName("SectionTitle")
        self.recent_list = QListWidget()
        self.recent_list.setMinimumHeight(124)
        self.recent_list.setMaximumHeight(180)
        self.recent_list.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.recent_list.itemDoubleClicked.connect(lambda _item: self._use_recent_folder())
        recent_layout.addWidget(recent_title)
        recent_layout.addWidget(self.recent_list)

        lower_grid.addWidget(summary_panel, 0, 0)
        lower_grid.addWidget(status_panel, 0, 1)
        lower_grid.addWidget(recent_panel, 1, 0, 1, 2)
        lower_grid.setColumnStretch(0, 1)
        lower_grid.setColumnStretch(1, 1)
        layout.addLayout(lower_grid)
        layout.addStretch(1)

        scroll.setWidget(page)
        return scroll

    def _build_results_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(14)

        layout.addWidget(
            self._page_header("Scan Results", "Review, filter, export, or delete safely.")
        )

        toolbar = QHBoxLayout()
        toolbar.setSpacing(10)

        self.search_box = QLineEdit()
        self.search_box.setPlaceholderText("Search by project or path")
        self.search_box.textChanged.connect(self._render_results)

        self.target_filter_combo = QComboBox()
        self.target_filter_combo.addItem("All targets", None)
        self.target_filter_combo.addItem(".venv", CleanupTarget.VENV.value)
        self.target_filter_combo.addItem("node_modules", CleanupTarget.NODE_MODULES.value)
        self.target_filter_combo.currentIndexChanged.connect(self._render_results)

        self.sort_combo = QComboBox()
        self.sort_combo.addItems(["Sort by size", "Sort by name", "Sort by modified date"])
        self.sort_combo.currentIndexChanged.connect(self._render_results)

        style = self.style()
        self.export_json_button = QPushButton("Export JSON")
        self.export_json_button.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        self.export_json_button.clicked.connect(lambda: self._export_results("json", True))
        self.export_csv_button = QPushButton("Export CSV")
        self.export_csv_button.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton)
        )
        self.export_csv_button.clicked.connect(lambda: self._export_results("csv", True))

        toolbar.addWidget(self.search_box, 1)
        toolbar.addWidget(self.target_filter_combo)
        toolbar.addWidget(self.sort_combo)
        toolbar.addWidget(self.export_json_button)
        toolbar.addWidget(self.export_csv_button)
        layout.addLayout(toolbar)

        bulk_bar = QHBoxLayout()
        bulk_bar.setSpacing(10)
        self.select_all_checkbox = QCheckBox("Select visible")
        self.select_all_checkbox.toggled.connect(self._toggle_select_visible)
        self.delete_selected_button = QPushButton("Delete selected")
        self.delete_selected_button.setObjectName("DangerButton")
        self.delete_selected_button.clicked.connect(self._delete_selected)
        self.delete_all_button = QPushButton("Delete visible")
        self.delete_all_button.setObjectName("DangerButton")
        self.delete_all_button.clicked.connect(self._delete_all)
        self.deletion_log_button = QPushButton("Deletion log")
        self.deletion_log_button.setIcon(
            style.standardIcon(QStyle.StandardPixmap.SP_FileDialogDetailedView)
        )
        self.deletion_log_button.clicked.connect(self._open_deletion_log)
        bulk_bar.addWidget(self.select_all_checkbox)
        bulk_bar.addStretch(1)
        bulk_bar.addWidget(self.deletion_log_button)
        bulk_bar.addWidget(self.delete_selected_button)
        bulk_bar.addWidget(self.delete_all_button)
        layout.addLayout(bulk_bar)

        self.results_scroll = QScrollArea()
        self.results_scroll.setWidgetResizable(True)
        self.results_container = QWidget()
        self.results_layout = QVBoxLayout(self.results_container)
        self.results_layout.setContentsMargins(0, 0, 0, 0)
        self.results_layout.setSpacing(12)
        self.results_scroll.setWidget(self.results_container)
        layout.addWidget(self.results_scroll, 1)

        self.empty_state = QFrame()
        self.empty_state.setObjectName("EmptyState")
        self.empty_state.setMinimumHeight(210)
        empty_layout = QVBoxLayout(self.empty_state)
        empty_layout.setContentsMargins(24, 34, 24, 34)
        empty_layout.setSpacing(8)
        empty_title = QLabel("No cleanup folders to show")
        empty_title.setObjectName("CardTitle")
        empty_text = QLabel("Choose a root folder and start a scan from the dashboard.")
        empty_text.setObjectName("MutedText")
        empty_text.setWordWrap(True)
        empty_layout.addStretch(1)
        empty_layout.addWidget(empty_title, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addWidget(empty_text, 0, Qt.AlignmentFlag.AlignCenter)
        empty_layout.addStretch(1)

        self._render_results()
        return page

    def _build_settings_page(self) -> QWidget:
        page = QWidget()
        page.setObjectName("Page")
        layout = QVBoxLayout(page)
        layout.setContentsMargins(28, 24, 28, 24)
        layout.setSpacing(18)

        layout.addWidget(self._page_header("Settings", "Tune scanning and appearance defaults."))

        panel = QFrame()
        panel.setObjectName("SettingsPanel")
        form = QGridLayout(panel)
        form.setContentsMargins(20, 18, 20, 18)
        form.setHorizontalSpacing(16)
        form.setVerticalSpacing(14)

        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["system", "light", "dark"])

        self.confirm_checkbox = QCheckBox("Confirm before deleting")
        self.confirm_checkbox.setChecked(True)
        self.confirm_checkbox.setEnabled(False)
        confirm_note = QLabel("Required for safety. DevCleaner never deletes without confirmation.")
        confirm_note.setObjectName("MutedText")
        confirm_note.setWordWrap(True)

        self.hidden_checkbox = QCheckBox("Show hidden folders while scanning")

        self.depth_checkbox = QCheckBox("Limit maximum scan depth")
        self.depth_checkbox.toggled.connect(self._max_depth_toggled)
        self.depth_spin = QSpinBox()
        self.depth_spin.setRange(0, 100)
        self.depth_spin.setEnabled(False)

        self.auto_refresh_checkbox = QCheckBox("Refresh result cards after deletion")
        self.animations_checkbox = QCheckBox("Enable UI animations")
        self.shortcut_hints_checkbox = QCheckBox("Show keyboard shortcut hints")

        self.exclude_edit = QTextEdit()
        self.exclude_edit.setPlaceholderText("One folder name per line")
        self.exclude_edit.setMinimumHeight(130)

        save_button = QPushButton("Save settings")
        save_button.setObjectName("PrimaryButton")
        save_button.clicked.connect(self._save_settings_from_controls)

        form.addWidget(QLabel("Theme mode"), 0, 0)
        form.addWidget(self.theme_combo, 0, 1)
        form.addWidget(QLabel("Deletion confirmation"), 1, 0)
        form.addWidget(self.confirm_checkbox, 1, 1)
        form.addWidget(confirm_note, 2, 1)
        form.addWidget(QLabel("Hidden folders"), 3, 0)
        form.addWidget(self.hidden_checkbox, 3, 1)
        form.addWidget(QLabel("Scan depth"), 4, 0)
        form.addWidget(self.depth_checkbox, 4, 1)
        form.addWidget(self.depth_spin, 5, 1)
        form.addWidget(QLabel("After deletion"), 6, 0)
        form.addWidget(self.auto_refresh_checkbox, 6, 1)
        form.addWidget(QLabel("Animations"), 7, 0)
        form.addWidget(self.animations_checkbox, 7, 1)
        form.addWidget(QLabel("Keyboard hints"), 8, 0)
        form.addWidget(self.shortcut_hints_checkbox, 8, 1)
        form.addWidget(QLabel("Excluded folder names"), 9, 0, Qt.AlignmentFlag.AlignTop)
        form.addWidget(self.exclude_edit, 9, 1)
        form.addWidget(save_button, 10, 1, Qt.AlignmentFlag.AlignRight)
        form.setColumnStretch(1, 1)

        layout.addWidget(panel)
        layout.addStretch(1)
        return page

    def _page_header(self, title: str, subtitle: str) -> QWidget:
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        title_label = QLabel(title)
        title_label.setObjectName("PageTitle")
        subtitle_label = QLabel(subtitle)
        subtitle_label.setObjectName("PageSubtitle")
        layout.addWidget(title_label)
        layout.addWidget(subtitle_label)
        return container

    def _add_summary_row(
        self,
        layout: QGridLayout,
        row: int,
        label: str,
        value: str,
    ) -> QLabel:
        label_widget = QLabel(label)
        label_widget.setObjectName("MetricLabel")
        label_widget.setMinimumHeight(20)
        value_widget = QLabel(value)
        value_widget.setObjectName("SummaryValue")
        value_widget.setMinimumHeight(22)
        value_widget.setWordWrap(True)
        value_widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        layout.addWidget(label_widget, row, 0)
        layout.addWidget(value_widget, row, 1)
        layout.setColumnStretch(1, 1)
        return value_widget

    def _create_actions(self) -> None:
        self._register_command(
            "choose-folder",
            "Choose folder",
            self._choose_root_folder,
            "Ctrl+O",
            "Select the root folder to scan.",
        )
        self._register_command(
            "start-scan",
            "Start scan",
            self._start_scan,
            "Ctrl+R",
            "Scan the selected root folder.",
            alternate_shortcuts=("F5",),
        )
        self._register_command(
            "cancel-scan",
            "Cancel scan",
            self._cancel_scan,
            "",
            "Stop the active background scan.",
        )
        self._register_command(
            "show-dashboard",
            "Go to Dashboard",
            lambda: self._navigate_to_page(0),
            "Ctrl+1",
            "Open the dashboard page.",
        )
        self._register_command(
            "show-results",
            "Go to Scan Results",
            lambda: self._navigate_to_page(1),
            "Ctrl+2",
            "Open the scan results page.",
        )
        self._register_command(
            "show-settings",
            "Go to Settings",
            lambda: self._navigate_to_page(2),
            "Ctrl+3",
            "Open the settings page.",
        )
        self._register_command(
            "focus-search",
            "Focus result search",
            self._focus_result_search,
            "Ctrl+F",
            "Move keyboard focus to result search.",
        )
        self._register_command(
            "select-visible",
            "Select visible results",
            self._select_visible_results,
            "Ctrl+A",
            "Select every result currently visible after filtering.",
        )
        self._register_command(
            "delete-selected",
            "Delete selected results",
            self._delete_selected,
            "Delete",
            "Review and permanently delete selected cleanup folders.",
        )
        self._register_command(
            "delete-visible",
            "Delete visible results",
            self._delete_all,
            "",
            "Review and permanently delete every visible cleanup folder.",
        )
        self._register_command(
            "export-visible",
            "Export visible results",
            lambda: self._export_results("csv", visible_only=True),
            "Ctrl+E",
            "Export the current filtered result set as CSV.",
        )
        self._register_command(
            "export-json",
            "Export visible results as JSON",
            lambda: self._export_results("json", visible_only=True),
            "",
            "Export the current filtered result set as JSON.",
        )
        self._register_command(
            "export-csv",
            "Export visible results as CSV",
            lambda: self._export_results("csv", visible_only=True),
            "",
            "Export the current filtered result set as CSV.",
        )
        self._register_command(
            "toggle-fullscreen",
            "Toggle fullscreen",
            self._toggle_fullscreen,
            "F11",
            "Enter or leave fullscreen.",
        )
        self._register_command(
            "command-palette",
            "Open command palette",
            self._open_command_palette,
            "Ctrl+K",
            "Search and run app commands.",
        )
        self._register_command(
            "shortcuts-help",
            "Show keyboard shortcuts",
            self._open_shortcut_help,
            "Ctrl+?",
            "Open the keyboard shortcut reference.",
            alternate_shortcuts=("Ctrl+/",),
        )
        self._register_command(
            "deletion-log",
            "Open deletion log",
            self._open_deletion_log,
            "",
            "Review deletions and failures from this session.",
        )

        self.escape_shortcut = QShortcut(QKeySequence("Esc"), self)
        self.escape_shortcut.setContext(Qt.ShortcutContext.WindowShortcut)
        self.escape_shortcut.activated.connect(self._escape_pressed)

    def _register_command(
        self,
        command_id: str,
        title: str,
        callback: Callable[[], None],
        shortcut: str,
        description: str,
        alternate_shortcuts: tuple[str, ...] = (),
    ) -> QAction:
        action = QAction(title, self)
        shortcuts = [QKeySequence(shortcut)] if shortcut else []
        shortcuts.extend(QKeySequence(item) for item in alternate_shortcuts)
        if shortcuts:
            action.setShortcuts(shortcuts)
            action.setShortcutContext(Qt.ShortcutContext.WindowShortcut)
        action.triggered.connect(lambda _checked=False: callback())
        self.addAction(action)
        self.actions_by_id[command_id] = action

        shortcut_label = shortcut
        if alternate_shortcuts:
            shortcut_label = " / ".join(filter(None, (shortcut, *alternate_shortcuts)))
        self.command_definitions.append(
            CommandDefinition(command_id, title, shortcut_label, description)
        )
        return action

    def _navigate_to_page(self, index: int) -> None:
        if not hasattr(self, "stack") or index == self.stack.currentIndex():
            return
        if index < 0 or index >= self.stack.count():
            return

        self.stack.setCurrentIndex(index)
        button = self.nav_group.button(index)
        if button is not None:
            button.setChecked(True)

        page = self.stack.currentWidget()
        animation = fade_slide_in(
            page,
            self.settings.animations_enabled,
            QPoint(14, 0),
            duration_ms=180,
        )
        if animation is not None:
            self.animations.append(animation)
            animation.finished.connect(lambda item=animation: self._forget_animation(item))

    def _run_command(self, command_id: str) -> None:
        action = self.actions_by_id.get(command_id)
        if action is None or not action.isEnabled():
            return
        action.trigger()

    def _open_command_palette(self) -> None:
        if self.command_palette is not None and self.command_palette.isVisible():
            self.command_palette.raise_()
            self.command_palette.activateWindow()
            return

        dialog = CommandPaletteDialog(self.command_definitions, self)
        dialog.command_requested.connect(self._run_command)
        dialog.finished.connect(lambda _result, popup=dialog: self._clear_command_palette(popup))
        self.command_palette = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _clear_command_palette(self, dialog: CommandPaletteDialog) -> None:
        if self.command_palette is dialog:
            self.command_palette = None

    def _open_shortcut_help(self) -> None:
        if self.shortcut_help_dialog is not None and self.shortcut_help_dialog.isVisible():
            self.shortcut_help_dialog.raise_()
            self.shortcut_help_dialog.activateWindow()
            return

        dialog = ShortcutHelpDialog(self.command_definitions, self)
        dialog.finished.connect(
            lambda _result, popup=dialog: self._clear_shortcut_help_dialog(popup)
        )
        self.shortcut_help_dialog = dialog
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _clear_shortcut_help_dialog(self, dialog: ShortcutHelpDialog) -> None:
        if self.shortcut_help_dialog is dialog:
            self.shortcut_help_dialog = None

    def _open_deletion_log(self) -> None:
        if not self.deletion_results:
            QMessageBox.information(
                self,
                "Deletion log",
                "No deletion attempts have been recorded in this session.",
            )
            return
        dialog = DeletionLogDialog(self.deletion_results, self)
        self.deletion_log_dialog = dialog
        dialog.finished.connect(lambda _result: setattr(self, "deletion_log_dialog", None))
        dialog.show()
        dialog.raise_()
        dialog.activateWindow()

    def _toggle_fullscreen(self) -> None:
        if self.isFullScreen():
            self.showNormal()
            if self.normal_window_geometry is not None:
                self.setGeometry(self.normal_window_geometry)
            return

        self.normal_window_geometry = self.geometry()
        self.showFullScreen()

    def _escape_pressed(self) -> None:
        if self.command_palette is not None and self.command_palette.isVisible():
            self.command_palette.reject()
            return
        if self.isFullScreen():
            self._toggle_fullscreen()

    def _focus_result_search(self) -> None:
        self._navigate_to_page(1)
        self.search_box.setFocus(Qt.FocusReason.ShortcutFocusReason)
        self.search_box.selectAll()

    def _select_visible_results(self) -> None:
        if self.stack.currentIndex() != 1:
            return
        visible_items = self._filtered_sorted_items()
        if not visible_items:
            return
        self.selected_ids.update(item.id for item in visible_items)
        self._sync_card_selection()
        self._update_metrics()

    def _choose_root_folder(self) -> None:
        start_dir = str(self.root_path or Path.home())
        selected = QFileDialog.getExistingDirectory(self, "Choose root folder", start_dir)
        if not selected:
            return
        self._set_root_path(Path(selected))

    def _set_root_path(self, root_path: Path) -> None:
        self.root_path = root_path
        self.root_path_label.setText(str(root_path))
        self.settings.remember_root(root_path)
        self.settings_store.save(self.settings)
        self._update_recent_roots()
        self._update_dashboard_summary()
        self._set_idle_status(f"Ready to scan {root_path}")

    def _start_scan(self) -> None:
        if self.root_path is None:
            QMessageBox.information(
                self,
                "Choose a folder",
                "Select a root folder before scanning.",
            )
            return

        selected_targets = self._selected_scan_targets()
        if not selected_targets:
            QMessageBox.information(
                self,
                "Choose scan targets",
                "Select at least one cleanup target before scanning.",
            )
            return

        self._save_settings_from_controls(show_message=False)
        self.items.clear()
        self.selected_ids.clear()
        self.cards.clear()
        self.last_scanned_count = 0
        self.last_scan_duration = 0.0
        self.last_scan_warning_count = 0
        self._render_results()
        self._update_metrics(scanned_count=0)

        options = ScanOptions(
            show_hidden=self.settings.show_hidden_folders,
            excluded_folder_names=self.settings.normalized_excluded_names(),
            max_depth=self.settings.max_scan_depth,
            targets=selected_targets,
        )

        self.scan_thread = QThread(self)
        self.scan_worker = ScanWorker(self.root_path, options)
        self.scan_worker.moveToThread(self.scan_thread)
        self.scan_thread.started.connect(self.scan_worker.run)
        self.scan_worker.item_found.connect(self._scan_item_found)
        self.scan_worker.progress.connect(self._scan_progress)
        self.scan_worker.failed.connect(self._scan_failed)
        self.scan_worker.finished.connect(self._scan_finished)
        self.scan_worker.finished.connect(lambda _result, thread=self.scan_thread: thread.quit())
        self.scan_worker.finished.connect(
            lambda _result, worker=self.scan_worker: worker.deleteLater()
        )
        self.scan_thread.finished.connect(self.scan_thread.deleteLater)
        self.scan_thread.finished.connect(self._clear_scan_thread)

        self.scan_button.setEnabled(False)
        self.cancel_scan_button.setEnabled(True)
        self.status_progress.setRange(0, 0)
        self.dashboard_progress.setRange(0, 0)
        self._set_worker_state(
            "Scanning",
            "Background scan worker is running. The interface remains responsive.",
        )
        self._set_idle_status("Scanning...")
        self.scan_thread.start()

    def _cancel_scan(self) -> None:
        if self.scan_worker is not None:
            self.scan_worker.cancel()
            self.cancel_scan_button.setEnabled(False)
            self._set_worker_state("Cancelling", "Waiting for the scan worker to stop safely.")
            self._set_idle_status("Cancelling scan...")

    def _scan_item_found(self, item: CleanupItem) -> None:
        if item.id in {existing.id for existing in self.items}:
            return
        self.items.append(item)
        self._update_metrics()
        self._render_results()
        self.results_nav.setText(f"Scan Results ({len(self.items)})")

    def _scan_progress(self, scanned_count: int, current_path: str) -> None:
        self.metric_numbers["scanned"] = scanned_count
        self.scanned_metric.set_value(str(scanned_count))
        self.last_scanned_count = scanned_count
        if hasattr(self, "summary_scanned_value"):
            self.summary_scanned_value.setText(str(scanned_count))
            self.worker_detail_value.setText(current_path)
        self.status_label.setText(f"Scanned {scanned_count} folders: {current_path}")

    def _scan_failed(self, message: str) -> None:
        self.dashboard_progress.setRange(0, 1)
        self.dashboard_progress.setValue(0)
        self._set_worker_state("Error", message)
        QMessageBox.critical(self, "Scan failed", message)

    def _scan_finished(self, result: ScanResult) -> None:
        self.scan_button.setEnabled(True)
        self.cancel_scan_button.setEnabled(False)
        self.status_progress.setRange(0, 1)
        self.status_progress.setValue(1)
        self.dashboard_progress.setRange(0, 1)
        self.dashboard_progress.setValue(1)

        self.items = list(result.items) if result.items else self.items
        self.last_scanned_count = result.scanned_directories
        self.last_scan_duration = result.elapsed_seconds
        self.last_scan_warning_count = len(result.errors)
        self._update_metrics(scanned_count=result.scanned_directories)
        self._render_results()
        self._update_scan_summary(result)

        if self.root_path is not None:
            self.settings.remember_root(self.root_path)
            self.settings_store.save(self.settings)
            self._update_recent_roots()

        state = "cancelled" if result.cancelled else "complete"
        self._set_worker_state(
            "Idle",
            f"Last scan {state}: {len(self.items)} cleanup folder(s) found.",
        )
        self._set_idle_status(f"Scan {state}: {len(self.items)} cleanup folders found.")
        self.results_nav.setText(f"Scan Results ({len(self.items)})")

    def _clear_scan_thread(self) -> None:
        self.scan_thread = None
        self.scan_worker = None

    def _delete_single(self, item: CleanupItem) -> None:
        if self.root_path is None:
            return
        self._review_and_delete([item])

    def _delete_selected(self) -> None:
        selected_items = [item for item in self.items if item.id in self.selected_ids]
        if not selected_items:
            QMessageBox.information(
                self,
                "No selection",
                "Select at least one cleanup folder first.",
            )
            return
        self._review_and_delete(selected_items)

    def _delete_all(self) -> None:
        visible_items = self._filtered_sorted_items()
        if not visible_items:
            QMessageBox.information(
                self,
                "Nothing to delete",
                "There are no visible cleanup folders.",
            )
            return
        self._review_and_delete(visible_items)

    def _review_and_delete(self, items: list[CleanupItem]) -> None:
        if self.root_path is None or not items:
            return
        if self.delete_thread is not None:
            QMessageBox.information(
                self,
                "Deletion in progress",
                "Wait for the current deletion to finish before starting another one.",
            )
            return

        dialog = DeletionReviewDialog(items, self)
        if dialog.exec() == DeletionReviewDialog.DialogCode.Accepted:
            self._start_deletion(items)

    def _start_deletion(self, items: list[CleanupItem]) -> None:
        if self.root_path is None:
            return

        self.delete_thread = QThread(self)
        self.delete_worker = DeleteWorker(self.root_path, items)
        self.delete_worker.moveToThread(self.delete_thread)
        self.delete_thread.started.connect(self.delete_worker.run)
        self.delete_worker.progress.connect(self._delete_progress)
        self.delete_worker.deleted.connect(self._delete_succeeded)
        self.delete_worker.failed_item.connect(self._delete_failed_item)
        self.delete_worker.finished.connect(self._delete_finished)
        self.delete_worker.finished.connect(
            lambda _results, thread=self.delete_thread: thread.quit()
        )
        self.delete_worker.finished.connect(
            lambda _results, worker=self.delete_worker: worker.deleteLater()
        )
        self.delete_thread.finished.connect(self.delete_thread.deleteLater)
        self.delete_thread.finished.connect(self._clear_delete_thread)

        self._set_delete_controls_enabled(False)
        self.status_progress.setRange(0, len(items))
        self.status_progress.setValue(0)
        self.dashboard_progress.setRange(0, len(items))
        self.dashboard_progress.setValue(0)
        self._set_worker_state(
            "Deleting",
            "Background deletion worker is removing confirmed cleanup folders.",
        )
        self._set_idle_status(f"Deleting {len(items)} cleanup folder(s)...")
        self.delete_thread.start()

    def _delete_progress(self, current: int, total: int) -> None:
        self.status_progress.setRange(0, total)
        self.status_progress.setValue(current)
        self.dashboard_progress.setRange(0, total)
        self.dashboard_progress.setValue(current)
        self.worker_detail_value.setText(f"Deleting {current} of {total} requested folders.")
        self.status_label.setText(f"Deleted {current} of {total} requested folders...")

    def _delete_succeeded(self, result: DeleteResult) -> None:
        self.reclaimed_size += result.size_bytes
        deleted_path_key = self._path_key(result.path)
        removed_ids = {
            item.id for item in self.items if self._path_key(item.cleanup_path) == deleted_path_key
        }
        self.items = [
            item for item in self.items if self._path_key(item.cleanup_path) != deleted_path_key
        ]
        self.selected_ids.difference_update(removed_ids)
        self._update_metrics()

    def _delete_failed_item(self, result: DeleteResult) -> None:
        path = str(result.path)
        self.status_label.setText(f"Could not delete {path}: {result.error}")

    def _delete_finished(self, results: list[DeleteResult]) -> None:
        self.deletion_results.extend(results)
        self._set_delete_controls_enabled(True)
        self.status_progress.setRange(0, 1)
        self.status_progress.setValue(1)
        self.dashboard_progress.setRange(0, 1)
        self.dashboard_progress.setValue(1)
        self._render_results()

        failures = [result for result in results if not result.success]
        deleted_count = len(results) - len(failures)
        self._set_idle_status(
            f"Deletion complete: {deleted_count} removed, {len(failures)} failed."
        )
        self._set_worker_state(
            "Idle",
            f"Deletion complete: {deleted_count} removed, {len(failures)} failed.",
        )

        if failures:
            details = "\n".join(
                f"{result.path}: {result.error}" for result in failures[:5]
            )
            QMessageBox.warning(
                self,
                "Some folders could not be deleted",
                f"{len(failures)} folder(s) failed to delete.\n\n{details}\n\n"
                "Open the deletion log for full details.",
            )

    def _clear_delete_thread(self) -> None:
        self.delete_thread = None
        self.delete_worker = None

    def _toggle_select_visible(self, selected: bool) -> None:
        visible_items = self._filtered_sorted_items()
        for item in visible_items:
            if selected:
                self.selected_ids.add(item.id)
            else:
                self.selected_ids.discard(item.id)

        self._sync_card_selection()
        self._update_metrics()

    def _sync_card_selection(self) -> None:
        for card in self.cards.values():
            card.blockSignals(True)
            card.set_selected(card.item.id in self.selected_ids)
            card.blockSignals(False)

    def _card_selection_changed(self, item: CleanupItem, selected: bool) -> None:
        if selected:
            self.selected_ids.add(item.id)
        else:
            self.selected_ids.discard(item.id)
        self._update_metrics()

    def _filtered_sorted_items(self) -> list[CleanupItem]:
        query = self.search_box.text().strip().casefold() if hasattr(self, "search_box") else ""
        target_filter = (
            self.target_filter_combo.currentData() if hasattr(self, "target_filter_combo") else None
        )
        if query:
            filtered = [
                item
                for item in self.items
                if query in item.project_name.casefold()
                or query in str(item.cleanup_path).casefold()
                or query in item.target.display_name.casefold()
            ]
        else:
            filtered = list(self.items)

        if target_filter is not None:
            filtered = [item for item in filtered if item.target.value == target_filter]

        sort_index = self.sort_combo.currentIndex() if hasattr(self, "sort_combo") else 0
        if sort_index == 1:
            filtered.sort(key=lambda item: item.project_name.casefold())
        elif sort_index == 2:
            filtered.sort(key=lambda item: item.modified_at, reverse=True)
        else:
            filtered.sort(key=lambda item: item.size_bytes, reverse=True)
        return filtered

    @staticmethod
    def _path_key(path: Path) -> str:
        return str(path.expanduser().resolve(strict=False)).casefold()

    def _render_results(self) -> None:
        if not hasattr(self, "results_layout"):
            return

        while self.results_layout.count():
            item = self.results_layout.takeAt(0)
            widget = item.widget()
            if widget is not None:
                if hasattr(self, "empty_state") and widget is self.empty_state:
                    widget.setParent(None)
                else:
                    widget.deleteLater()

        self.cards.clear()
        visible_items = self._filtered_sorted_items()

        if not visible_items:
            self.results_layout.addWidget(self.empty_state)
        else:
            for index, item in enumerate(visible_items):
                card = CleanupCard(item)
                card.set_selected(item.id in self.selected_ids)
                card.delete_requested.connect(self._delete_single)
                card.open_project_requested.connect(lambda info: open_folder(info.project_path))
                card.reveal_cleanup_requested.connect(
                    lambda info: reveal_in_file_manager(info.cleanup_path)
                )
                card.selection_changed.connect(self._card_selection_changed)
                self.cards[item.id] = card
                self.results_layout.addWidget(card)
                self._animate_card(card, index)

        self.results_layout.addStretch(1)
        self._update_bulk_buttons()

    def _animate_card(self, card: CleanupCard, index: int) -> None:
        animation = fade_in(
            card,
            self.settings.animations_enabled,
            duration_ms=170,
            delay_ms=min(index * 18, 160),
        )
        if animation is not None:
            self.animations.append(animation)
            animation.finished.connect(lambda item=animation: self._forget_animation(item))

    def _forget_animation(self, animation: object) -> None:
        if animation in self.animations:
            self.animations.remove(animation)

    def _export_results(self, file_type: str, visible_only: bool = False) -> None:
        export_items = self._filtered_sorted_items() if visible_only else list(self.items)
        if not export_items:
            QMessageBox.information(
                self,
                "Nothing to export",
                "Run a scan or adjust filters before exporting results.",
            )
            return

        extension = "json" if file_type == "json" else "csv"
        file_filter = "JSON Files (*.json)" if extension == "json" else "CSV Files (*.csv)"
        destination, _ = QFileDialog.getSaveFileName(
            self,
            "Export scan results",
            str(Path.home() / f"devcleaner-results.{extension}"),
            file_filter,
        )
        if not destination:
            return

        exporter = ScanResultExporter()
        try:
            if extension == "json":
                exporter.export_json(export_items, Path(destination))
            else:
                exporter.export_csv(export_items, Path(destination))
        except OSError as exc:
            QMessageBox.critical(self, "Export failed", str(exc))
            return

        QMessageBox.information(self, "Export complete", f"Saved results to:\n{destination}")

    def _load_settings_into_controls(self) -> None:
        self.theme_combo.setCurrentText(self.settings.theme_mode)
        self.hidden_checkbox.setChecked(self.settings.show_hidden_folders)
        self.auto_refresh_checkbox.setChecked(self.settings.auto_refresh_after_delete)
        self.animations_checkbox.setChecked(self.settings.animations_enabled)
        self.shortcut_hints_checkbox.setChecked(self.settings.show_shortcut_hints)
        self.exclude_edit.setPlainText("\n".join(self.settings.excluded_folder_names))
        selected_targets = self.settings.selected_targets()
        self.venv_target_checkbox.setChecked(CleanupTarget.VENV in selected_targets)
        self.node_target_checkbox.setChecked(CleanupTarget.NODE_MODULES in selected_targets)

        has_depth_limit = self.settings.max_scan_depth is not None
        self.depth_checkbox.setChecked(has_depth_limit)
        self.depth_spin.setEnabled(has_depth_limit)
        self.depth_spin.setValue(self.settings.max_scan_depth or 0)

    def _save_settings_from_controls(self, show_message: bool = True) -> None:
        excluded = [
            line.strip()
            for line in self.exclude_edit.toPlainText().splitlines()
            if line.strip()
        ]
        self.settings = AppSettings(
            theme_mode=self.theme_combo.currentText(),
            confirm_before_delete=True,
            show_hidden_folders=self.hidden_checkbox.isChecked(),
            excluded_folder_names=excluded,
            max_scan_depth=self.depth_spin.value() if self.depth_checkbox.isChecked() else None,
            auto_refresh_after_delete=self.auto_refresh_checkbox.isChecked(),
            animations_enabled=self.animations_checkbox.isChecked(),
            show_shortcut_hints=self.shortcut_hints_checkbox.isChecked(),
            selected_target_names=[target.value for target in self._selected_scan_targets()],
            recent_roots=self.settings.recent_roots,
        )
        self.settings_store.save(self.settings)
        self._apply_theme()
        self._apply_shortcut_hints()
        if show_message:
            QMessageBox.information(self, "Settings saved", "Your settings have been saved.")

    def _selected_scan_targets(self) -> frozenset[CleanupTarget]:
        targets: set[CleanupTarget] = set()
        if self.venv_target_checkbox.isChecked():
            targets.add(CleanupTarget.VENV)
        if self.node_target_checkbox.isChecked():
            targets.add(CleanupTarget.NODE_MODULES)
        return frozenset(targets)

    def _max_depth_toggled(self, enabled: bool) -> None:
        self.depth_spin.setEnabled(enabled)

    def _use_recent_folder(self) -> None:
        item = self.recent_list.currentItem()
        if item is None:
            return
        path = Path(item.text())
        if not path.exists():
            QMessageBox.warning(
                self,
                "Folder unavailable",
                f"This folder no longer exists:\n{path}",
            )
            return
        self._set_root_path(path)

    def _update_recent_roots(self) -> None:
        if not hasattr(self, "recent_list"):
            return
        self.recent_list.clear()
        self.recent_list.addItems(self.settings.recent_roots)

    def _update_metrics(self, scanned_count: int | None = None) -> None:
        total_size = sum(item.size_bytes for item in self.items)
        self._set_metric_number("detected", self.detected_metric, len(self.items), str)
        self._set_metric_number("total_size", self.total_size_metric, total_size, format_size)
        self._set_metric_number(
            "reclaimed",
            self.reclaimed_metric,
            self.reclaimed_size,
            format_size,
        )
        if scanned_count is not None:
            self._set_metric_number("scanned", self.scanned_metric, scanned_count, str)
            self.last_scanned_count = scanned_count
        self.detected_metric.set_helper(
            f"{len(self.selected_ids)} selected" if self.selected_ids else self._target_breakdown()
        )
        self.total_size_metric.set_helper("Across current results")
        self.reclaimed_metric.set_helper("This session")
        self.scanned_metric.set_helper("Last scan")
        self._update_dashboard_summary()
        self._update_bulk_buttons()

    def _set_metric_number(
        self,
        key: str,
        card: MetricCard,
        value: int,
        formatter: Callable[[int], str],
    ) -> None:
        start = self.metric_numbers.get(key, value)
        self.metric_numbers[key] = value
        animation = animate_number(
            card.value_label,
            start,
            value,
            formatter,
            self.settings.animations_enabled,
        )
        if animation is not None:
            self.animations.append(animation)
            animation.finished.connect(lambda item=animation: self._forget_animation(item))

    def _target_breakdown(self) -> str:
        if not self.items:
            return "Cleanup folders"
        parts: list[str] = []
        for target in CleanupTarget:
            count = sum(1 for item in self.items if item.target is target)
            if count:
                parts.append(f"{count} {target.short_label}")
        return " / ".join(parts) if parts else "Cleanup folders"

    def _update_bulk_buttons(self) -> None:
        if not hasattr(self, "delete_selected_button"):
            return
        self.delete_selected_button.setEnabled(bool(self.selected_ids))
        self.deletion_log_button.setEnabled(bool(self.deletion_results))

        visible_items = self._filtered_sorted_items()
        self.delete_all_button.setEnabled(bool(visible_items))
        visible_ids = {item.id for item in visible_items}
        all_visible_selected = bool(visible_ids) and visible_ids.issubset(self.selected_ids)
        self.select_all_checkbox.blockSignals(True)
        self.select_all_checkbox.setChecked(all_visible_selected)
        self.select_all_checkbox.blockSignals(False)

    def _update_scan_summary(self, result: ScanResult) -> None:
        self.last_scanned_count = result.scanned_directories
        self.last_scan_duration = result.elapsed_seconds
        self.last_scan_warning_count = len(result.errors)
        self._update_dashboard_summary()

    def _update_dashboard_summary(self) -> None:
        if not hasattr(self, "summary_root_value"):
            return

        total_size = sum(item.size_bytes for item in self.items)
        root_text = str(self.root_path) if self.root_path is not None else "No folder selected"
        duration = format_duration(self.last_scan_duration) if self.last_scan_duration else "-"

        self.summary_root_value.setText(root_text)
        self.summary_found_value.setText(str(len(self.items)))
        self.summary_total_value.setText(format_size(total_size))
        self.summary_scanned_value.setText(str(self.last_scanned_count))
        self.summary_duration_value.setText(duration)
        self.summary_warning_value.setText(str(self.last_scan_warning_count))

        if self.items:
            largest = max(self.items, key=lambda item: item.size_bytes)
            average_size = total_size // len(self.items)
            self.largest_venv_value.setText(
                f"{largest.project_name} {largest.target.short_label} "
                f"({format_size(largest.size_bytes)})"
            )
            self.average_size_value.setText(format_size(average_size))
        else:
            self.largest_venv_value.setText("-")
            self.average_size_value.setText("0.0 MB")

    def _set_delete_controls_enabled(self, enabled: bool) -> None:
        self.delete_selected_button.setEnabled(enabled and bool(self.selected_ids))
        self.delete_all_button.setEnabled(enabled and bool(self._filtered_sorted_items()))
        self.deletion_log_button.setEnabled(bool(self.deletion_results))
        self.scan_button.setEnabled(enabled)

    def _set_idle_status(self, message: str) -> None:
        self.status_label.setText(message)

    def _set_worker_state(self, state: str, detail: str) -> None:
        if not hasattr(self, "worker_status_pill"):
            return
        self.worker_status_pill.setText(state.upper())
        self.worker_state_value.setText(state)
        self.worker_detail_value.setText(detail)

    def _apply_shortcut_hints(self) -> None:
        if not hasattr(self, "choose_button"):
            return

        hint_map = {
            self.choose_button: ("choose-folder", "Choose folder"),
            self.scan_button: ("start-scan", "Start scan"),
            self.cancel_scan_button: ("cancel-scan", "Cancel scan"),
            self.export_json_button: ("export-json", "Export visible results as JSON"),
            self.export_csv_button: ("export-csv", "Export visible results as CSV"),
            self.delete_selected_button: ("delete-selected", "Delete selected results"),
            self.delete_all_button: ("delete-visible", "Delete visible results"),
            self.deletion_log_button: ("deletion-log", "Open deletion log"),
            self.dashboard_nav: ("show-dashboard", "Dashboard"),
            self.results_nav: ("show-results", "Scan Results"),
            self.settings_nav: ("show-settings", "Settings"),
        }

        for widget, (command_id, fallback) in hint_map.items():
            shortcut = self._shortcut_label(command_id)
            if self.settings.show_shortcut_hints and shortcut:
                widget.setToolTip(f"{fallback} ({shortcut})")
            else:
                widget.setToolTip(fallback if self.settings.show_shortcut_hints else "")

    def _shortcut_label(self, command_id: str) -> str:
        for command in self.command_definitions:
            if command.command_id == command_id:
                return command.shortcut
        return ""

    def _apply_theme(self) -> None:
        app = QApplication.instance()
        if app is not None:
            app.setStyleSheet(build_stylesheet(self.settings.theme_mode))
