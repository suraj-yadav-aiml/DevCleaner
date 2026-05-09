from __future__ import annotations

from PySide6.QtGui import QPalette
from PySide6.QtWidgets import QApplication


def resolve_theme(theme_mode: str) -> str:
    if theme_mode in {"light", "dark"}:
        return theme_mode

    app = QApplication.instance()
    if app is None:
        return "light"

    window_color = app.palette().color(QPalette.ColorRole.Window)
    return "dark" if window_color.lightness() < 128 else "light"


def build_stylesheet(theme_mode: str) -> str:
    theme = resolve_theme(theme_mode)
    if theme == "dark":
        return _dark_stylesheet()
    return _light_stylesheet()


def _base_stylesheet() -> str:
    return """
* {
    font-family: "Segoe UI", Arial, sans-serif;
    font-size: 13px;
    letter-spacing: 0px;
}
QMainWindow {
    background: palette(window);
}
QDialog {
    background: palette(window);
}
QWidget#AppRoot, QWidget#Page {
    background: palette(window);
}
QLabel {
    background: transparent;
}
QScrollArea {
    border: none;
    background: transparent;
}
QScrollArea > QWidget > QWidget {
    background: transparent;
}
QStatusBar {
    border-top: 1px solid palette(mid);
    padding: 2px 8px;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit {
    min-height: 38px;
    border-radius: 10px;
    padding: 6px 12px;
    selection-background-color: #2f7df6;
}
QTextEdit, QPlainTextEdit {
    padding: 10px 12px;
}
QPushButton {
    min-height: 38px;
    border-radius: 10px;
    padding: 7px 15px;
    font-weight: 600;
}
QPushButton:disabled {
    opacity: 0.55;
}
QCheckBox {
    spacing: 8px;
}
QPushButton:focus, QCheckBox:focus, QListWidget:focus, QTableWidget:focus {
    outline: 0;
}
QCheckBox::indicator {
    width: 18px;
    height: 18px;
    border-radius: 5px;
}
QProgressBar {
    min-height: 8px;
    max-height: 8px;
    border-radius: 4px;
    text-align: center;
}
QListWidget {
    border-radius: 10px;
    padding: 6px;
    outline: 0;
}
QTableWidget {
    border-radius: 10px;
    gridline-color: palette(mid);
    padding: 4px;
}
QHeaderView::section {
    min-height: 28px;
    padding: 6px 8px;
    border: none;
    font-weight: 700;
}
QListWidget::item {
    min-height: 34px;
    padding: 8px 10px;
    border-radius: 8px;
}
#Sidebar {
    border-right: 1px solid palette(mid);
}
#SidebarHint {
    border-radius: 12px;
    padding: 12px;
}
#BrandPanel {
    border-radius: 14px;
    padding: 14px;
}
#AppTitle {
    font-size: 23px;
    font-weight: 800;
}
#PageTitle {
    font-size: 28px;
    font-weight: 800;
}
#PageSubtitle {
    font-size: 14px;
}
#NavButton {
    min-height: 46px;
    text-align: left;
    padding-left: 16px;
    border-radius: 12px;
}
#MetricCard, #CleanupCard, #SettingsPanel, #EmptyState, #SummaryPanel,
#ScanPanel, #StatusPanel, #ToolbarPanel {
    border-radius: 16px;
}
#MetricValue {
    font-size: 27px;
    font-weight: 800;
}
#MetricLabel {
    font-size: 12px;
    font-weight: 700;
    text-transform: uppercase;
}
#MetricHelper {
    font-size: 12px;
}
#CardTitle {
    font-size: 17px;
    font-weight: 800;
}
#CardPath {
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 12px;
}
#PathDisplay {
    font-family: Consolas, "Cascadia Mono", monospace;
    font-size: 12px;
    border-radius: 10px;
    padding: 11px 12px;
}
#SectionTitle {
    font-size: 16px;
    font-weight: 800;
}
#SummaryValue {
    font-weight: 700;
}
#StatusPill {
    border-radius: 999px;
    padding: 6px 12px;
    font-size: 12px;
    font-weight: 800;
}
#TargetBadge {
    border-radius: 999px;
    padding: 4px 9px;
    font-size: 11px;
    font-weight: 800;
}
#DetailPill {
    border-radius: 11px;
    padding: 10px 12px;
}
#DangerButton {
    font-weight: 800;
}
#ToolbarButton {
    min-height: 32px;
}
"""


def _light_stylesheet() -> str:
    return (
        _base_stylesheet()
        + """
QMainWindow, QWidget#AppRoot, QWidget#Page {
    background: #f6f8fb;
    color: #17212f;
}
#Sidebar {
    background: #ffffff;
}
#BrandPanel {
    background: #f4f7fb;
    border: 1px solid #e2e8f0;
}
#SidebarHint {
    background: #f4f7fb;
    border: 1px solid #e2e8f0;
    color: #687386;
}
#PageSubtitle, #MetricLabel, #MetricHelper, #MutedText {
    color: #687386;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit, QTableWidget {
    background: #ffffff;
    border: 1px solid #d7deea;
    color: #17212f;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus,
QPlainTextEdit:focus, QListWidget:focus, QTableWidget:focus {
    border: 1px solid #2f7df6;
}
QPushButton {
    background: #eef2f7;
    border: 1px solid #d8e0ec;
    color: #17212f;
}
QPushButton:hover {
    background: #e4ebf5;
}
QPushButton:focus {
    border: 1px solid #2f7df6;
}
QPushButton#PrimaryButton {
    background: #246bfe;
    border: 1px solid #246bfe;
    color: #ffffff;
}
QPushButton#PrimaryButton:hover {
    background: #1d5fdf;
}
QPushButton#DangerButton {
    background: #dc2f2f;
    border: 1px solid #dc2f2f;
    color: #ffffff;
}
QPushButton#DangerButton:hover {
    background: #bd2323;
}
QPushButton#NavButton {
    background: transparent;
    border: none;
    color: #334155;
}
QPushButton#NavButton:hover {
    background: #f1f5fb;
}
QPushButton#NavButton:checked {
    background: #e8f1ff;
    color: #135bd8;
}
#MetricCard, #CleanupCard, #SettingsPanel, #EmptyState, #SummaryPanel,
#ScanPanel, #StatusPanel, #ToolbarPanel {
    background: #ffffff;
    border: 1px solid #dfe7f2;
}
#MetricCard {
    border-left: 4px solid #246bfe;
}
#PathDisplay, #DetailPill {
    background: #f4f7fb;
    border: 1px solid #e0e7f1;
}
#CleanupCard[selected="true"] {
    border: 1px solid #246bfe;
    background: #f6f9ff;
}
QListWidget {
    background: #f8fafc;
    border: 1px solid #dfe7f2;
}
QTableWidget {
    background: #ffffff;
    alternate-background-color: #f8fafc;
}
QHeaderView::section {
    background: #f2f6fb;
    color: #334155;
}
QListWidget::item:hover {
    background: #eef4ff;
}
QListWidget::item:selected {
    background: #e8f1ff;
    color: #135bd8;
}
QCheckBox::indicator {
    border: 1px solid #b8c4d5;
    background: #ffffff;
}
QCheckBox::indicator:checked {
    background: #246bfe;
    border: 1px solid #246bfe;
}
#StatusPill {
    background: #e8f1ff;
    color: #135bd8;
}
#TargetBadge {
    background: #e8f1ff;
    color: #135bd8;
}
QProgressBar {
    background: #e3e8f0;
    border: none;
}
QProgressBar::chunk {
    background: #1f6feb;
    border-radius: 4px;
}
"""
    )


def _dark_stylesheet() -> str:
    return (
        _base_stylesheet()
        + """
QMainWindow, QWidget#AppRoot, QWidget#Page {
    background: #111315;
    color: #edf2f7;
}
#Sidebar {
    background: #0b0d10;
}
#BrandPanel {
    background: #15181d;
    border: 1px solid #242a34;
}
#SidebarHint {
    background: #15181d;
    border: 1px solid #242a34;
    color: #a7b0bd;
}
#PageSubtitle, #MetricLabel, #MetricHelper, #MutedText {
    color: #a7b0bd;
}
QLineEdit, QComboBox, QSpinBox, QTextEdit, QPlainTextEdit, QTableWidget {
    background: #171a20;
    border: 1px solid #2a303b;
    color: #edf2f7;
}
QLineEdit:focus, QComboBox:focus, QSpinBox:focus, QTextEdit:focus,
QPlainTextEdit:focus, QListWidget:focus, QTableWidget:focus {
    border: 1px solid #5aa7ff;
}
QPushButton {
    background: #22262e;
    border: 1px solid #343b47;
    color: #edf2f7;
}
QPushButton:hover {
    background: #2a303a;
}
QPushButton:focus {
    border: 1px solid #5aa7ff;
}
QPushButton#PrimaryButton {
    background: #2f7df6;
    border: 1px solid #2f7df6;
    color: #ffffff;
}
QPushButton#PrimaryButton:hover {
    background: #4f9cff;
}
QPushButton#DangerButton {
    background: #ef4444;
    border: 1px solid #ef4444;
    color: #ffffff;
}
QPushButton#DangerButton:hover {
    background: #dc2626;
}
QPushButton#NavButton {
    background: transparent;
    border: none;
    color: #d4dae3;
}
QPushButton#NavButton:hover {
    background: #171a20;
}
QPushButton#NavButton:checked {
    background: #1b2b43;
    color: #d8e9ff;
}
#MetricCard, #CleanupCard, #SettingsPanel, #EmptyState, #SummaryPanel,
#ScanPanel, #StatusPanel, #ToolbarPanel {
    background: #171a20;
    border: 1px solid #2a303b;
}
#MetricCard {
    border-left: 4px solid #5aa7ff;
}
#PathDisplay, #DetailPill {
    background: #111419;
    border: 1px solid #252b35;
}
#CleanupCard[selected="true"] {
    border: 1px solid #5aa7ff;
    background: #182231;
}
QListWidget {
    background: #111419;
    border: 1px solid #252b35;
}
QTableWidget {
    background: #171a20;
    alternate-background-color: #111419;
}
QHeaderView::section {
    background: #1d222a;
    color: #d4dae3;
}
QListWidget::item:hover {
    background: #1f2630;
}
QListWidget::item:selected {
    background: #1b2b43;
    color: #d8e9ff;
}
QCheckBox::indicator {
    border: 1px solid #5a6473;
    background: #111419;
}
QCheckBox::indicator:checked {
    background: #2f7df6;
    border: 1px solid #2f7df6;
}
#StatusPill {
    background: #1b2b43;
    color: #d8e9ff;
}
#TargetBadge {
    background: #1b2b43;
    color: #d8e9ff;
}
QProgressBar {
    background: #252b35;
    border: none;
}
QProgressBar::chunk {
    background: #2f7df6;
    border-radius: 4px;
}
"""
    )
