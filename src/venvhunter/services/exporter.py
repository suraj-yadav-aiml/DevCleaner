from __future__ import annotations

import csv
import json
from pathlib import Path

from venvhunter.models import CleanupItem


class ScanResultExporter:
    def export_json(
        self,
        items: list[CleanupItem] | tuple[CleanupItem, ...],
        destination: Path,
    ) -> None:
        payload = [self._item_to_dict(item) for item in items]
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    def export_csv(
        self,
        items: list[CleanupItem] | tuple[CleanupItem, ...],
        destination: Path,
    ) -> None:
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8", newline="") as csv_file:
            writer = csv.DictWriter(
                csv_file,
                fieldnames=[
                    "target_type",
                    "target_name",
                    "project_name",
                    "project_path",
                    "cleanup_path",
                    "size_bytes",
                    "modified_at",
                    "file_count",
                    "folder_count",
                    "scan_errors",
                ],
            )
            writer.writeheader()
            for item in items:
                writer.writerow(self._item_to_dict(item))

    @staticmethod
    def _item_to_dict(item: CleanupItem) -> dict[str, object]:
        return {
            "target_type": item.target.display_name,
            "target_name": item.target.folder_name,
            "project_name": item.project_name,
            "project_path": str(item.project_path),
            "cleanup_path": str(item.cleanup_path),
            "size_bytes": item.size_bytes,
            "modified_at": item.modified_at.isoformat(timespec="seconds"),
            "file_count": item.file_count,
            "folder_count": item.folder_count,
            "scan_errors": " | ".join(item.scan_errors),
        }
