from __future__ import annotations

from datetime import datetime

MB = 1024 * 1024
GB = 1024 * MB


def format_size(size_bytes: int) -> str:
    if size_bytes >= GB:
        return f"{size_bytes / GB:.2f} GB"
    return f"{size_bytes / MB:.1f} MB"


def format_datetime(value: datetime) -> str:
    return value.strftime("%Y-%m-%d %H:%M")


def format_duration(seconds: float) -> str:
    if seconds < 1:
        return "< 1 sec"
    if seconds < 60:
        return f"{seconds:.1f} sec"
    minutes, remainder = divmod(seconds, 60)
    return f"{int(minutes)} min {int(remainder)} sec"


def pluralize(count: int, singular: str, plural: str | None = None) -> str:
    if count == 1:
        return f"1 {singular}"
    return f"{count} {plural or singular + 's'}"
