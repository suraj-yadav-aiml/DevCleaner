from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from venvhunter.models import CleanupTarget

DEFAULT_EXCLUDED_FOLDERS = [
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    "node_modules",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
]


@dataclass
class AppSettings:
    theme_mode: str = "system"
    confirm_before_delete: bool = True
    show_hidden_folders: bool = False
    excluded_folder_names: list[str] = field(
        default_factory=lambda: DEFAULT_EXCLUDED_FOLDERS.copy()
    )
    max_scan_depth: int | None = None
    auto_refresh_after_delete: bool = True
    animations_enabled: bool = True
    show_shortcut_hints: bool = True
    selected_target_names: list[str] = field(
        default_factory=lambda: [CleanupTarget.VENV.value, CleanupTarget.NODE_MODULES.value]
    )
    recent_roots: list[str] = field(default_factory=list)

    def normalized_excluded_names(self) -> frozenset[str]:
        return frozenset(
            name.strip().casefold() for name in self.excluded_folder_names if name.strip()
        )

    def remember_root(self, root_path: Path, limit: int = 8) -> None:
        root = str(root_path)
        self.recent_roots = [
            item for item in self.recent_roots if item.casefold() != root.casefold()
        ]
        self.recent_roots.insert(0, root)
        self.recent_roots = self.recent_roots[:limit]

    def selected_targets(self) -> frozenset[CleanupTarget]:
        targets = {
            CleanupTarget(name)
            for name in self.selected_target_names
            if name in {target.value for target in CleanupTarget}
        }
        return frozenset(targets) or CleanupTarget.defaults()


class SettingsStore:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path or self.default_path()

    @staticmethod
    def default_path() -> Path:
        return SettingsStore._settings_path("DevCleaner")

    @staticmethod
    def legacy_path() -> Path:
        return SettingsStore._settings_path("VenvHunter")

    @staticmethod
    def _settings_path(app_folder_name: str) -> Path:
        app_data = os.environ.get("APPDATA")
        base_path = Path(app_data) if app_data else Path.home() / "AppData" / "Roaming"
        return base_path / app_folder_name / "settings.json"

    def load(self) -> AppSettings:
        source_path = self.path
        if not source_path.exists() and source_path == self.default_path():
            legacy_path = self.legacy_path()
            if legacy_path.exists():
                source_path = legacy_path

        if not source_path.exists():
            return AppSettings()

        try:
            payload = json.loads(source_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return AppSettings()

        if not isinstance(payload, dict):
            return AppSettings()

        return self._settings_from_payload(payload)

    def save(self, settings: AppSettings) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = asdict(settings)
        self.path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def _settings_from_payload(self, payload: dict[str, Any]) -> AppSettings:
        defaults = AppSettings()
        recent_roots = payload.get("recent_roots", defaults.recent_roots)
        excluded = payload.get("excluded_folder_names", defaults.excluded_folder_names)
        selected_targets = payload.get("selected_target_names", defaults.selected_target_names)

        return AppSettings(
            theme_mode=self._string(payload.get("theme_mode"), defaults.theme_mode),
            confirm_before_delete=True,
            show_hidden_folders=self._bool(
                payload.get("show_hidden_folders"), defaults.show_hidden_folders
            ),
            excluded_folder_names=self._string_list(excluded, defaults.excluded_folder_names),
            max_scan_depth=self._optional_int(payload.get("max_scan_depth")),
            auto_refresh_after_delete=self._bool(
                payload.get("auto_refresh_after_delete"), defaults.auto_refresh_after_delete
            ),
            animations_enabled=self._bool(
                payload.get("animations_enabled"), defaults.animations_enabled
            ),
            show_shortcut_hints=self._bool(
                payload.get("show_shortcut_hints"), defaults.show_shortcut_hints
            ),
            selected_target_names=self._target_names(
                selected_targets,
                defaults.selected_target_names,
            ),
            recent_roots=self._string_list(recent_roots, defaults.recent_roots),
        )

    @staticmethod
    def _string(value: object, default: str) -> str:
        return value if isinstance(value, str) and value else default

    @staticmethod
    def _bool(value: object, default: bool) -> bool:
        return value if isinstance(value, bool) else default

    @staticmethod
    def _optional_int(value: object) -> int | None:
        if value is None:
            return None
        if isinstance(value, bool):
            return None
        if isinstance(value, int) and value >= 0:
            return value
        return None

    @staticmethod
    def _string_list(value: object, default: list[str]) -> list[str]:
        if not isinstance(value, list):
            return default.copy()
        return [item for item in value if isinstance(item, str)]

    @staticmethod
    def _target_names(value: object, default: list[str]) -> list[str]:
        names = SettingsStore._string_list(value, default)
        valid_names = {target.value for target in CleanupTarget}
        selected = [name for name in names if name in valid_names]
        return selected or default.copy()
